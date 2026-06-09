import sys
import os
import json
import datetime
import shutil
import difflib
from typing import Dict, List, Optional, Any, Tuple

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QTreeView, QListView, QTableView, QTextEdit, QLineEdit,
                             QPushButton, QLabel, QSplitter, QToolBar, QStatusBar,
                             QFileSystemModel, QMessageBox, QDialog, QProgressBar,
                             QTabWidget, QToolButton, QMenu, QAction, QStyle,
                             QHeaderView, QAbstractItemView, QComboBox, QCheckBox,
                             QInputDialog, QFileDialog, QDialogButtonBox, QListWidget,
                             QListWidgetItem, QGroupBox, QTextBrowser, QSpinBox)
from PyQt5.QtCore import Qt, QDir, QModelIndex, QSize, pyqtSignal, QThread, QTimer, QUrl
from PyQt5.QtGui import QIcon, QStandardItemModel, QStandardItem, QFont, QColor, QTextCursor, QDesktopServices

# 导入其他可能需要的高级组件
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtPrintSupport import QPrintDialog, QPrinter


# ==================== 工具类 ====================

class FileManager:
    """文件管理工具类"""
    
    def __init__(self):
        self.current_path = QDir.homePath()
        self.favorite_paths = []
        self.recent_files = []
        
    def set_current_path(self, path: str) -> bool:
        if os.path.exists(path):
            self.current_path = path
            return True
        return False
    
    def add_favorite(self, path: str):
        if path not in self.favorite_paths:
            self.favorite_paths.append(path)
    
    def remove_favorite(self, path: str):
        if path in self.favorite_paths:
            self.favorite_paths.remove(path)
    
    def add_recent_file(self, file_path: str):
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)
        self.recent_files.insert(0, file_path)
        # 保持最近文件列表不超过10个
        if len(self.recent_files) > 10:
            self.recent_files = self.recent_files[:10]
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """获取文件的详细信息"""
        if not os.path.exists(file_path):
            return {}
        
        stat = os.stat(file_path)
        file_name = os.path.basename(file_path)
        file_size = stat.st_size
        created = datetime.datetime.fromtimestamp(stat.st_ctime)
        modified = datetime.datetime.fromtimestamp(stat.st_mtime)
        
        return {
            'name': file_name,
            'path': file_path,
            'size': file_size,
            'created': created,
            'modified': modified,
            'type': '文件夹' if os.path.isdir(file_path) else '文件'
        }


class VersionControl:
    """版本控制工具类"""
    
    def __init__(self):
        self.versions = {}  # 文件路径 -> 版本列表
        self.current_versions = {}  # 文件路径 -> 当前版本号
    
    def add_version(self, file_path: str, content: str, comment: str = ""):
        if file_path not in self.versions:
            self.versions[file_path] = []
            self.current_versions[file_path] = -1
        
        version_id = len(self.versions[file_path])
        timestamp = datetime.datetime.now().isoformat()
        
        version_data = {
            'id': version_id,
            'content': content,
            'timestamp': timestamp,
            'comment': comment
        }
        
        self.versions[file_path].append(version_data)
        self.current_versions[file_path] = version_id
        return version_id
    
    def get_version(self, file_path: str, version_id: int = None) -> Optional[Dict]:
        if file_path not in self.versions:
            return None
        
        if version_id is None:
            version_id = self.current_versions[file_path]
        
        if 0 <= version_id < len(self.versions[file_path]):
            return self.versions[file_path][version_id]
        
        return None
    
    def get_version_history(self, file_path: str) -> List[Dict]:
        return self.versions.get(file_path, [])
    
    def compare_versions(self, file_path: str, version_id1: int, version_id2: int) -> str:
        """比较两个版本的差异"""
        version1 = self.get_version(file_path, version_id1)
        version2 = self.get_version(file_path, version_id2)
        
        if not version1 or not version2:
            return "无法比较版本"
        
        content1 = version1['content'].splitlines()
        content2 = version2['content'].splitlines()
        
        # 使用difflib生成差异
        diff = difflib.unified_diff(
            content1, content2,
            f"版本 {version_id1}", f"版本 {version_id2}",
            lineterm=''
        )
        
        return '\n'.join(diff)


class CollaborationManager:
    """协作管理工具类"""
    
    def __init__(self):
        self.comments = {}  # 文件路径 -> 评论列表
        self.annotations = {}  # 文件路径 -> 注释列表
        self.tags = {}  # 文件路径 -> 标签列表
    
    def add_comment(self, file_path: str, text: str, author: str, position: tuple = None):
        if file_path not in self.comments:
            self.comments[file_path] = []
        
        comment_id = len(self.comments[file_path])
        timestamp = datetime.datetime.now().isoformat()
        
        comment_data = {
            'id': comment_id,
            'text': text,
            'author': author,
            'timestamp': timestamp,
            'position': position,
            'resolved': False
        }
        
        self.comments[file_path].append(comment_data)
        return comment_id
    
    def resolve_comment(self, file_path: str, comment_id: int):
        if file_path in self.comments and 0 <= comment_id < len(self.comments[file_path]):
            self.comments[file_path][comment_id]['resolved'] = True
    
    def add_annotation(self, file_path: str, annotation_type: str, content: str, position: tuple):
        if file_path not in self.annotations:
            self.annotations[file_path] = []
        
        annotation_id = len(self.annotations[file_path])
        timestamp = datetime.datetime.now().isoformat()
        
        annotation_data = {
            'id': annotation_id,
            'type': annotation_type,
            'content': content,
            'position': position,
            'timestamp': timestamp
        }
        
        self.annotations[file_path].append(annotation_data)
        return annotation_id
    
    def add_tag(self, file_path: str, tag: str, color: QColor = None):
        if file_path not in self.tags:
            self.tags[file_path] = []
        
        if tag not in self.tags[file_path]:
            tag_data = {
                'name': tag,
                'color': color or QColor('#007acc'),
                'added': datetime.datetime.now().isoformat()
            }
            self.tags[file_path].append(tag_data)
    
    def remove_tag(self, file_path: str, tag: str):
        if file_path in self.tags:
            self.tags[file_path] = [t for t in self.tags[file_path] if t['name'] != tag]
    
    def get_tags(self, file_path: str) -> List[Dict]:
        return self.tags.get(file_path, [])


class AdvancedSearch:
    """高级搜索工具类"""
    
    def __init__(self, file_manager: FileManager):
        self.file_manager = file_manager
        self.index = {}  # 简单的倒排索引：词 -> 文件路径列表
    
    def index_file(self, file_path: str, content: str):
        # 简单的分词和索引创建
        words = content.split()
        for word in words:
            word = word.lower().strip('.,!?;:"\'()[]{}')
            if len(word) > 2:  # 只索引长度大于2的词
                if word not in self.index:
                    self.index[word] = []
                if file_path not in self.index[word]:
                    self.index[word].append(file_path)
    
    def search(self, query: str, file_types: List[str] = None, 
               min_size: int = None, max_size: int = None) -> List[str]:
        words = query.split()
        results = []
        
        for word in words:
            word = word.lower().strip('.,!?;:"\'()[]{}')
            if word in self.index:
                results.extend(self.index[word])
        
        # 去重并排序（简单的相关性排序：出现次数多的排在前面）
        from collections import Counter
        result_count = Counter(results)
        sorted_results = [item[0] for item in result_count.most_common()]
        
        # 应用过滤器
        filtered_results = []
        for file_path in sorted_results:
            # 文件类型过滤
            if file_types and not any(file_path.endswith(ft) for ft in file_types):
                continue
            
            # 文件大小过滤
            if min_size is not None or max_size is not None:
                file_size = os.path.getsize(file_path)
                if min_size is not None and file_size < min_size:
                    continue
                if max_size is not None and file_size > max_size:
                    continue
            
            filtered_results.append(file_path)
        
        return filtered_results
    
    def search_in_directory(self, directory: str, query: str, 
                           recursive: bool = True) -> List[str]:
        """在指定目录中搜索内容"""
        results = []
        
        if not os.path.exists(directory):
            return results
        
        if recursive:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if query.lower() in content.lower():
                                results.append(file_path)
                    except:
                        continue
        else:
            for file in os.listdir(directory):
                file_path = os.path.join(directory, file)
                if os.path.isfile(file_path):
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if query.lower() in content.lower():
                                results.append(file_path)
                    except:
                        continue
        
        return results


class FileOperations:
    """文件操作工具类"""
    
    @staticmethod
    def copy_file(src: str, dst: str) -> bool:
        try:
            shutil.copy2(src, dst)
            return True
        except Exception as e:
            print(f"复制文件失败: {e}")
            return False
    
    @staticmethod
    def move_file(src: str, dst: str) -> bool:
        try:
            shutil.move(src, dst)
            return True
        except Exception as e:
            print(f"移动文件失败: {e}")
            return False
    
    @staticmethod
    def delete_file(path: str) -> bool:
        try:
            if os.path.isfile(path):
                os.remove(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)
            return True
        except Exception as e:
            print(f"删除文件失败: {e}")
            return False
    
    @staticmethod
    def create_directory(path: str, name: str) -> bool:
        try:
            new_dir = os.path.join(path, name)
            os.makedirs(new_dir, exist_ok=True)
            return True
        except Exception as e:
            print(f"创建目录失败: {e}")
            return False


# ==================== 自定义模型和视图 ====================

class AdvancedFileSystemModel(QFileSystemModel):
    """增强的文件系统模型，支持自定义数据"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.custom_data = {}  # 文件路径 -> 自定义数据
    
    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DecorationRole and index.column() == 0:
            file_path = self.filePath(index)
            if file_path in self.custom_data and 'icon' in self.custom_data[file_path]:
                return self.custom_data[file_path]['icon']
        
        if role == Qt.ToolTipRole:
            file_path = self.filePath(index)
            if file_path in self.custom_data and 'tooltip' in self.custom_data[file_path]:
                return self.custom_data[file_path]['tooltip']
        
        if role == Qt.ForegroundRole:
            file_path = self.filePath(index)
            if file_path in self.custom_data and 'color' in self.custom_data[file_path]:
                return self.custom_data[file_path]['color']
        
        if role == Qt.UserRole + 1:  # 自定义数据角色
            file_path = self.filePath(index)
            return self.custom_data.get(file_path, {})
        
        return super().data(index, role)
    
    def set_custom_data(self, file_path, key, value):
        if file_path not in self.custom_data:
            self.custom_data[file_path] = {}
        self.custom_data[file_path][key] = value
        # 触发视图更新
        index = self.index(file_path)
        self.dataChanged.emit(index, index)
    
    def get_custom_data(self, file_path, key, default=None):
        if file_path in self.custom_data and key in self.custom_data[file_path]:
            return self.custom_data[file_path][key]
        return default


class CustomTableView(QTableView):
    """自定义表格视图，支持右键菜单和其他高级功能"""
    
    item_right_clicked = pyqtSignal(QModelIndex)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setSortingEnabled(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.horizontalHeader().setStretchLastSection(True)
        self.setAlternatingRowColors(True)
    
    def contextMenuEvent(self, event):
        index = self.indexAt(event.pos())
        if index.isValid():
            self.item_right_clicked.emit(index)
            menu = self.create_context_menu(index)
            menu.exec_(event.globalPos())
    
    def create_context_menu(self, index):
        menu = QMenu(self)
        
        open_action = QAction("打开", self)
        open_action.triggered.connect(lambda: self.open_item(index))
        menu.addAction(open_action)
        
        menu.addSeparator()
        
        export_action = QAction("导出", self)
        export_action.triggered.connect(lambda: self.export_item(index))
        menu.addAction(export_action)
        
        return menu
    
    def open_item(self, index):
        # 在子类中实现具体打开逻辑
        pass
    
    def export_item(self, index):
        # 在子类中实现具体导出逻辑
        pass


class TagListWidget(QListWidget):
    """标签列表控件"""
    
    tag_clicked = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMaximumHeight(100)
        self.itemClicked.connect(self.on_item_clicked)
    
    def add_tag(self, name, color=None):
        item = QListWidgetItem(name)
        if color:
            item.setForeground(color)
        self.addItem(item)
    
    def on_item_clicked(self, item):
        self.tag_clicked.emit(item.text())


# ==================== 自定义对话框 ====================

class VersionHistoryDialog(QDialog):
    """版本历史对话框"""
    
    version_selected = pyqtSignal(int)
    
    def __init__(self, version_control: VersionControl, file_path: str, parent=None):
        super().__init__(parent)
        self.version_control = version_control
        self.file_path = file_path
        self.setWindowTitle(f"版本历史 - {os.path.basename(file_path)}")
        self.setGeometry(100, 100, 800, 600)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 版本列表
        self.version_list = QListView()
        self.version_model = QStandardItemModel()
        self.version_list.setModel(self.version_model)
        
        history = self.version_control.get_version_history(self.file_path)
        for version in history:
            item = QStandardItem(f"版本 {version['id']} - {version['timestamp']} - {version['comment']}")
            item.setData(version['id'], Qt.UserRole)
            self.version_model.appendRow(item)
        
        # 版本详情
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        self.restore_button = QPushButton("恢复到此版本")
        self.restore_button.clicked.connect(self.restore_version)
        button_layout.addWidget(self.restore_button)
        
        self.compare_button = QPushButton("比较版本")
        self.compare_button.clicked.connect(self.compare_versions)
        button_layout.addWidget(self.compare_button)
        
        button_layout.addStretch()
        
        self.close_button = QPushButton("关闭")
        self.close_button.clicked.connect(self.reject)
        button_layout.addWidget(self.close_button)
        
        # 布局
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.version_list)
        splitter.addWidget(self.detail_text)
        splitter.setSizes([200, 400])
        
        layout.addWidget(splitter)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # 连接信号
        self.version_list.selectionModel().selectionChanged.connect(self.show_version_details)
    
    def show_version_details(self):
        selected = self.version_list.selectedIndexes()
        if not selected:
            return
        
        index = selected[0]
        version_id = index.data(Qt.UserRole)
        version = self.version_control.get_version(self.file_path, version_id)
        
        if version:
            self.detail_text.setPlainText(version['content'])
    
    def restore_version(self):
        selected = self.version_list.selectedIndexes()
        if not selected:
            return
        
        index = selected[0]
        version_id = index.data(Qt.UserRole)
        
        reply = QMessageBox.question(self, "确认恢复", 
                                    f"确定要恢复到版本 {version_id} 吗？当前内容将被覆盖。",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.version_selected.emit(version_id)
            self.accept()
    
    def compare_versions(self):
        selected = self.version_list.selectedIndexes()
        if len(selected) != 2:
            QMessageBox.warning(self, "警告", "请选择两个版本进行比较")
            return
        
        version_id1 = selected[0].data(Qt.UserRole)
        version_id2 = selected[1].data(Qt.UserRole)
        
        diff = self.version_control.compare_versions(self.file_path, version_id1, version_id2)
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"版本比较: {version_id1} vs {version_id2}")
        dialog.setGeometry(150, 150, 900, 700)
        
        layout = QVBoxLayout()
        text_edit = QTextEdit()
        text_edit.setPlainText(diff)
        text_edit.setReadOnly(True)
        
        layout.addWidget(text_edit)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(dialog.accept)
        layout.addWidget(button_box)
        
        dialog.setLayout(layout)
        dialog.exec_()


class AdvancedSearchDialog(QDialog):
    """高级搜索对话框"""
    
    def __init__(self, search_tool: AdvancedSearch, parent=None):
        super().__init__(parent)
        self.search_tool = search_tool
        self.setWindowTitle("高级搜索")
        self.setGeometry(100, 100, 600, 500)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 搜索输入
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("搜索:"))
        
        self.search_input = QLineEdit()
        self.search_input.returnPressed.connect(self.do_search)
        search_layout.addWidget(self.search_input)
        
        self.search_button = QPushButton("搜索")
        self.search_button.clicked.connect(self.do_search)
        search_layout.addWidget(self.search_button)
        
        layout.addLayout(search_layout)
        
        # 搜索选项
        options_group = QGroupBox("搜索选项")
        options_layout = QVBoxLayout()
        
        # 文件类型过滤
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("文件类型:"))
        
        self.file_type_combo = QComboBox()
        self.file_type_combo.addItem("所有文件", None)
        self.file_type_combo.addItem("文本文件 (.txt)", [".txt"])
        self.file_type_combo.addItem("Python文件 (.py)", [".py"])
        self.file_type_combo.addItem("文档文件", [".doc", ".docx", ".pdf", ".rtf"])
        self.file_type_combo.addItem("图像文件", [".jpg", ".jpeg", ".png", ".gif", ".bmp"])
        type_layout.addWidget(self.file_type_combo)
        
        options_layout.addLayout(type_layout)
        
        # 文件大小过滤
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("文件大小:"))
        
        self.min_size_spin = QSpinBox()
        self.min_size_spin.setSuffix(" KB")
        self.min_size_spin.setRange(0, 999999)
        self.min_size_spin.setSpecialValueText("无限制")
        size_layout.addWidget(self.min_size_spin)
        
        size_layout.addWidget(QLabel("到"))
        
        self.max_size_spin = QSpinBox()
        self.max_size_spin.setSuffix(" KB")
        self.max_size_spin.setRange(0, 999999)
        self.max_size_spin.setSpecialValueText("无限制")
        size_layout.addWidget(self.max_size_spin)
        
        options_layout.addLayout(size_layout)
        
        # 搜索范围
        scope_layout = QHBoxLayout()
        scope_layout.addWidget(QLabel("搜索范围:"))
        
        self.scope_combo = QComboBox()
        self.scope_combo.addItem("当前目录", "current")
        self.scope_combo.addItem("整个项目", "project")
        self.scope_combo.addItem("自定义路径", "custom")
        scope_layout.addWidget(self.scope_combo)
        
        self.custom_path_edit = QLineEdit()
        self.custom_path_edit.setPlaceholderText("输入自定义搜索路径")
        scope_layout.addWidget(self.custom_path_edit)
        
        options_layout.addLayout(scope_layout)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # 结果列表
        self.results_list = QListView()
        self.results_model = QStandardItemModel()
        self.results_list.setModel(self.results_model)
        self.results_list.doubleClicked.connect(self.open_result)
        layout.addWidget(self.results_list)
        
        # 状态栏
        self.status_label = QLabel("就绪")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def do_search(self):
        query = self.search_input.text()
        if not query:
            return
        
        # 获取搜索选项
        file_types = self.file_type_combo.currentData()
        min_size = self.min_size_spin.value()
        max_size = self.max_size_spin.value()
        
        # 转换单位为字节
        min_size = min_size * 1024 if min_size > 0 else None
        max_size = max_size * 1024 if max_size > 0 else None
        
        # 执行搜索
        self.results_model.clear()
        results = self.search_tool.search(query, file_types, min_size, max_size)
        
        for result in results:
            item = QStandardItem(result)
            self.results_model.appendRow(item)
        
        self.status_label.setText(f"找到 {len(results)} 个结果")
    
    def open_result(self, index):
        file_path = index.data()
        if file_path and os.path.isfile(file_path):
            self.parent().open_file(file_path)


class FilePropertiesDialog(QDialog):
    """文件属性对话框"""
    
    def __init__(self, file_manager: FileManager, file_path: str, parent=None):
        super().__init__(parent)
        self.file_manager = file_manager
        self.file_path = file_path
        self.setWindowTitle(f"属性 - {os.path.basename(file_path)}")
        self.setGeometry(100, 100, 400, 500)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 获取文件信息
        file_info = self.file_manager.get_file_info(self.file_path)
        
        # 基本信息
        basic_group = QGroupBox("基本信息")
        basic_layout = QVBoxLayout()
        
        basic_layout.addWidget(QLabel(f"名称: {file_info.get('name', '')}"))
        basic_layout.addWidget(QLabel(f"类型: {file_info.get('type', '')}"))
        basic_layout.addWidget(QLabel(f"位置: {file_info.get('path', '')}"))
        
        size = file_info.get('size', 0)
        size_str = self.format_file_size(size)
        basic_layout.addWidget(QLabel(f"大小: {size_str}"))
        
        created = file_info.get('created', '')
        if created:
            basic_layout.addWidget(QLabel(f"创建时间: {created.strftime('%Y-%m-%d %H:%M:%S')}"))
        
        modified = file_info.get('modified', '')
        if modified:
            basic_layout.addWidget(QLabel(f"修改时间: {modified.strftime('%Y-%m-%d %H:%M:%S')}"))
        
        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def format_file_size(self, size_bytes):
        """格式化文件大小显示"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        size = size_bytes
        
        while size >= 1024 and i < len(size_names) - 1:
            size /= 1024.0
            i += 1
        
        return f"{size:.2f} {size_names[i]}"


class TagManagerDialog(QDialog):
    """标签管理对话框"""
    
    def __init__(self, collaboration_manager: CollaborationManager, file_path: str, parent=None):
        super().__init__(parent)
        self.collaboration_manager = collaboration_manager
        self.file_path = file_path
        self.setWindowTitle(f"管理标签 - {os.path.basename(file_path)}")
        self.setGeometry(100, 100, 400, 300)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 现有标签
        existing_group = QGroupBox("现有标签")
        existing_layout = QVBoxLayout()
        
        self.tags_list = QListWidget()
        existing_layout.addWidget(self.tags_list)
        
        remove_button = QPushButton("移除选中标签")
        remove_button.clicked.connect(self.remove_tag)
        existing_layout.addWidget(remove_button)
        
        existing_group.setLayout(existing_layout)
        layout.addWidget(existing_group)
        
        # 添加新标签
        new_group = QGroupBox("添加新标签")
        new_layout = QVBoxLayout()
        
        tag_layout = QHBoxLayout()
        tag_layout.addWidget(QLabel("标签名:"))
        
        self.tag_input = QLineEdit()
        tag_layout.addWidget(self.tag_input)
        
        new_layout.addLayout(tag_layout)
        
        add_button = QPushButton("添加标签")
        add_button.clicked.connect(self.add_tag)
        new_layout.addWidget(add_button)
        
        new_group.setLayout(new_layout)
        layout.addWidget(new_group)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
        
        # 加载现有标签
        self.load_tags()
    
    def load_tags(self):
        """加载现有标签"""
        self.tags_list.clear()
        tags = self.collaboration_manager.get_tags(self.file_path)
        for tag in tags:
            item = QListWidgetItem(tag['name'])
            if 'color' in tag:
                item.setForeground(tag['color'])
            self.tags_list.addItem(item)
    
    def add_tag(self):
        """添加新标签"""
        tag_name = self.tag_input.text().strip()
        if not tag_name:
            QMessageBox.warning(self, "警告", "标签名不能为空")
            return
        
        self.collaboration_manager.add_tag(self.file_path, tag_name)
        self.load_tags()
        self.tag_input.clear()
    
    def remove_tag(self):
        """移除选中标签"""
        selected = self.tags_list.currentItem()
        if not selected:
            return
        
        tag_name = selected.text()
        self.collaboration_manager.remove_tag(self.file_path, tag_name)
        self.load_tags()


# ==================== 主窗口 ====================

class ProductDeliverySystem(QMainWindow):
    """产品交付物系统主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("产品交付物系统")
        self.setGeometry(100, 50, 1400, 900)
        
        # 初始化工具类
        self.file_manager = FileManager()
        self.version_control = VersionControl()
        self.collaboration_manager = CollaborationManager()
        self.search_tool = AdvancedSearch(self.file_manager)
        self.file_operations = FileOperations()
        
        self.current_file = None
        self.init_ui()
    
    def init_ui(self):
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧文件浏览器
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # 文件操作按钮
        file_buttons_layout = QHBoxLayout()
        
        self.new_folder_button = QPushButton("新建文件夹")
        self.new_folder_button.clicked.connect(self.create_new_folder)
        file_buttons_layout.addWidget(self.new_folder_button)
        
        self.refresh_button = QPushButton("刷新")
        self.refresh_button.clicked.connect(self.refresh_file_view)
        file_buttons_layout.addWidget(self.refresh_button)
        
        left_layout.addLayout(file_buttons_layout)
        
        self.file_tree = QTreeView()
        self.file_model = AdvancedFileSystemModel()
        self.file_model.setRootPath(self.file_manager.current_path)
        self.file_tree.setModel(self.file_model)
        self.file_tree.setRootIndex(self.file_model.index(self.file_manager.current_path))
        self.file_tree.setColumnWidth(0, 250)
        self.file_tree.doubleClicked.connect(self.on_file_double_clicked)
        self.file_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_tree.customContextMenuRequested.connect(self.show_file_context_menu)
        
        left_layout.addWidget(self.file_tree)
        
        # 标签面板
        tags_group = QGroupBox("标签")
        tags_layout = QVBoxLayout()
        
        self.tags_list = TagListWidget()
        self.tags_list.tag_clicked.connect(self.filter_by_tag)
        tags_layout.addWidget(self.tags_list)
        
        manage_tags_button = QPushButton("管理标签")
        manage_tags_button.clicked.connect(self.manage_tags)
        tags_layout.addWidget(manage_tags_button)
        
        tags_group.setLayout(tags_layout)
        left_layout.addWidget(tags_group)
        
        # 右侧编辑区域
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # 标签页 widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        
        right_layout.addWidget(self.tab_widget)
        
        # 添加到主布局
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 1100])
        
        main_layout.addWidget(splitter)
        
        # 创建菜单栏
        self.create_menus()
        
        # 创建工具栏
        self.create_toolbars()
        
        # 创建状态栏
        self.statusBar().showMessage("就绪")
        
        # 加载常用标签
        self.load_common_tags()
    
    def create_menus(self):
        # 文件菜单
        file_menu = self.menuBar().addMenu("文件")
        
        new_action = QAction("新建", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_file)
        file_menu.addAction(new_action)
        
        open_action = QAction("打开", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_file_dialog)
        file_menu.addAction(open_action)
        
        save_action = QAction("保存", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)
        
        save_as_action = QAction("另存为", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_as_file)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        properties_action = QAction("属性", self)
        properties_action.triggered.connect(self.show_file_properties)
        file_menu.addAction(properties_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 编辑菜单
        edit_menu = self.menuBar().addMenu("编辑")
        
        undo_action = QAction("撤销", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(self.undo)
        edit_menu.addAction(undo_action)
        
        redo_action = QAction("重做", self)
        redo_action.setShortcut("Ctrl+Y")
        redo_action.triggered.connect(self.redo)
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        find_action = QAction("查找", self)
        find_action.setShortcut("Ctrl+F")
        find_action.triggered.connect(self.find)
        edit_menu.addAction(find_action)
        
        replace_action = QAction("替换", self)
        replace_action.setShortcut("Ctrl+H")
        replace_action.triggered.connect(self.replace)
        edit_menu.addAction(replace_action)
        
        # 视图菜单
        view_menu = self.menuBar().addMenu("视图")
        
        zoom_in_action = QAction("放大", self)
        zoom_in_action.setShortcut("Ctrl++")
        zoom_in_action.triggered.connect(self.zoom_in)
        view_menu.addAction(zoom_in_action)
        
        zoom_out_action = QAction("缩小", self)
        zoom_out_action.setShortcut("Ctrl+-")
        zoom_out_action.triggered.connect(self.zoom_out)
        view_menu.addAction(zoom_out_action)
        
        view_menu.addSeparator()
        
        fullscreen_action = QAction("全屏", self)
        fullscreen_action.setShortcut("F11")
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        view_menu.addAction(fullscreen_action)
        
        # 工具菜单
        tools_menu = self.menuBar().addMenu("工具")
        
        version_action = QAction("版本历史", self)
        version_action.triggered.connect(self.show_version_history)
        tools_menu.addAction(version_action)
        
        search_action = QAction("高级搜索", self)
        search_action.triggered.connect(self.show_advanced_search)
        tools_menu.addAction(search_action)
        
        # 帮助菜单
        help_menu = self.menuBar().addMenu("帮助")
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        docs_action = QAction("文档", self)
        docs_action.triggered.connect(self.show_documentation)
        help_menu.addAction(docs_action)
    
    def create_toolbars(self):
        # 主工具栏
        main_toolbar = QToolBar("主工具栏")
        main_toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(main_toolbar)
        
        new_icon = self.style().standardIcon(QStyle.SP_FileIcon)
        new_action = QAction(new_icon, "新建", self)
        new_action.triggered.connect(self.new_file)
        main_toolbar.addAction(new_action)
        
        open_icon = self.style().standardIcon(QStyle.SP_DirOpenIcon)
        open_action = QAction(open_icon, "打开", self)
        open_action.triggered.connect(self.open_file_dialog)
        main_toolbar.addAction(open_action)
        
        save_icon = self.style().standardIcon(QStyle.SP_DialogSaveButton)
        save_action = QAction(save_icon, "保存", self)
        save_action.triggered.connect(self.save_file)
        main_toolbar.addAction(save_action)
        
        main_toolbar.addSeparator()
        
        undo_icon = self.style().standardIcon(QStyle.SP_ArrowBack)
        undo_action = QAction(undo_icon, "撤销", self)
        undo_action.triggered.connect(self.undo)
        main_toolbar.addAction(undo_action)
        
        redo_icon = self.style().standardIcon(QStyle.SP_ArrowForward)
        redo_action = QAction(redo_icon, "重做", self)
        redo_action.triggered.connect(self.redo)
        main_toolbar.addAction(redo_action)
        
        main_toolbar.addSeparator()
        
        search_icon = self.style().standardIcon(QStyle.SP_FileDialogContentsView)
        search_action = QAction(search_icon, "搜索", self)
        search_action.triggered.connect(self.show_advanced_search)
        main_toolbar.addAction(search_action)
        
        # 文件操作工具栏
        file_toolbar = QToolBar("文件操作")
        self.addToolBar(file_toolbar)
        
        copy_icon = self.style().standardIcon(QStyle.SP_FileDialogBack)
        copy_action = QAction(copy_icon, "复制", self)
        copy_action.triggered.connect(self.copy_file)
        file_toolbar.addAction(copy_action)
        
        cut_icon = self.style().standardIcon(QStyle.SP_FileDialogStart)
        cut_action = QAction(cut_icon, "剪切", self)
        cut_action.triggered.connect(self.cut_file)
        file_toolbar.addAction(cut_action)
        
        paste_icon = self.style().standardIcon(QStyle.SP_FileDialogEnd)
        paste_action = QAction(paste_icon, "粘贴", self)
        paste_action.triggered.connect(self.paste_file)
        file_toolbar.addAction(paste_action)
        
        delete_icon = self.style().standardIcon(QStyle.SP_TrashIcon)
        delete_action = QAction(delete_icon, "删除", self)
        delete_action.triggered.connect(self.delete_file)
        file_toolbar.addAction(delete_action)
        
        # 协作工具栏
        collab_toolbar = QToolBar("协作工具栏")
        self.addToolBar(collab_toolbar)
        
        comment_icon = self.style().standardIcon(QStyle.SP_MessageBoxInformation)
        comment_action = QAction(comment_icon, "添加注释", self)
        comment_action.triggered.connect(self.add_comment)
        collab_toolbar.addAction(comment_action)
        
        tag_icon = self.style().standardIcon(QStyle.SP_FileLinkIcon)
        tag_action = QAction(tag_icon, "添加标签", self)
        tag_action.triggered.connect(self.add_tag)
        collab_toolbar.addAction(tag_action)
    
    def new_file(self):
        # 创建新文件
        tab_count = self.tab_widget.count()
        new_tab = QTextEdit()
        self.tab_widget.addTab(new_tab, f"未命名{tab_count + 1}")
        self.tab_widget.setCurrentIndex(tab_count)
        
        self.statusBar().showMessage("已创建新文件")
    
    def open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开文件", self.file_manager.current_path,
            "所有文件 (*);;文本文件 (*.txt);;Python文件 (*.py);;文档文件 (*.doc *.docx *.pdf)"
        )
        
        if file_path:
            self.open_file(file_path)
    
    def open_file(self, file_path=None):
        if not file_path:
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 创建新标签页显示文件内容
            tab_count = self.tab_widget.count()
            text_edit = QTextEdit()
            text_edit.setPlainText(content)
            
            file_name = os.path.basename(file_path)
            self.tab_widget.addTab(text_edit, file_name)
            self.tab_widget.setCurrentIndex(tab_count)
            
            # 更新文件管理器
            self.file_manager.add_recent_file(file_path)
            self.current_file = file_path
            
            # 索引文件内容以便搜索
            self.search_tool.index_file(file_path, content)
            
            self.statusBar().showMessage(f"已打开: {file_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法打开文件: {str(e)}")
    
    def save_file(self):
        current_index = self.tab_widget.currentIndex()
        if current_index < 0:
            return
        
        current_widget = self.tab_widget.currentWidget()
        if not isinstance(current_widget, QTextEdit):
            return
        
        content = current_widget.toPlainText()
        
        if self.current_file:
            try:
                with open(self.current_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                # 添加版本控制
                self.version_control.add_version(self.current_file, content, "自动保存")
                
                self.statusBar().showMessage(f"已保存: {self.current_file}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存文件失败: {str(e)}")
        else:
            self.save_as_file()
    
    def save_as_file(self):
        current_index = self.tab_widget.currentIndex()
        if current_index < 0:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "另存为", self.file_manager.current_path,
            "所有文件 (*);;文本文件 (*.txt);;Python文件 (*.py)"
        )
        
        if not file_path:
            return
        
        try:
            current_widget = self.tab_widget.currentWidget()
            content = current_widget.toPlainText()
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.current_file = file_path
            file_name = os.path.basename(file_path)
            self.tab_widget.setTabText(current_index, file_name)
            
            # 添加版本控制
            self.version_control.add_version(file_path, content, "初始保存")
            
            # 更新文件管理器
            self.file_manager.add_recent_file(file_path)
            
            self.statusBar().showMessage(f"已另存为: {file_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"另存为文件失败: {str(e)}")
    
    def close_tab(self, index):
        self.tab_widget.removeTab(index)
    
    def on_file_double_clicked(self, index):
        file_path = self.file_model.filePath(index)
        if os.path.isfile(file_path):
            self.open_file(file_path)
    
    def show_file_context_menu(self, position):
        index = self.file_tree.indexAt(position)
        if not index.isValid():
            return
        
        file_path = self.file_model.filePath(index)
        menu = QMenu()
        
        open_action = QAction("打开", self)
        open_action.triggered.connect(lambda: self.open_file(file_path))
        menu.addAction(open_action)
        
        if os.path.isfile(file_path):
            props_action = QAction("属性", self)
            props_action.triggered.connect(lambda: self.show_file_properties_for_path(file_path))
            menu.addAction(props_action)
            
            tag_action = QAction("管理标签", self)
            tag_action.triggered.connect(lambda: self.manage_tags_for_path(file_path))
            menu.addAction(tag_action)
        
        menu.addSeparator()
        
        copy_action = QAction("复制", self)
        copy_action.triggered.connect(lambda: self.copy_file_path(file_path))
        menu.addAction(copy_action)
        
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(lambda: self.delete_file_path(file_path))
        menu.addAction(delete_action)
        
        menu.exec_(self.file_tree.viewport().mapToGlobal(position))
    
    def show_file_properties(self):
        if not self.current_file:
            QMessageBox.information(self, "信息", "请先打开一个文件")
            return
        
        dialog = FilePropertiesDialog(self.file_manager, self.current_file, self)
        dialog.exec_()
    
    def show_file_properties_for_path(self, file_path):
        dialog = FilePropertiesDialog(self.file_manager, file_path, self)
        dialog.exec_()
    
    def show_version_history(self):
        if not self.current_file:
            QMessageBox.information(self, "信息", "请先打开一个文件")
            return
        
        dialog = VersionHistoryDialog(self.version_control, self.current_file, self)
        dialog.version_selected.connect(self.restore_version)
        dialog.exec_()
    
    def restore_version(self, version_id):
        version = self.version_control.get_version(self.current_file, version_id)
        if version:
            current_widget = self.tab_widget.currentWidget()
            if isinstance(current_widget, QTextEdit):
                current_widget.setPlainText(version['content'])
                self.statusBar().showMessage(f"已恢复到版本 {version_id}")
    
    def show_advanced_search(self):
        dialog = AdvancedSearchDialog(self.search_tool, self)
        dialog.exec_()
    
    def add_comment(self):
        current_index = self.tab_widget.currentIndex()
        if current_index < 0:
            return
        
        current_widget = self.tab_widget.currentWidget()
        if not isinstance(current_widget, QTextEdit):
            return
        
        # 获取当前光标位置
        cursor = current_widget.textCursor()
        position = (cursor.blockNumber(), cursor.columnNumber())
        
        # 在实际应用中，这里应该显示一个对话框来输入注释内容
        comment, ok = QInputDialog.getText(self, "添加注释", "输入注释内容:")
        if ok and comment:
            author = "当前用户"  # 在实际应用中应该获取当前登录用户
            self.collaboration_manager.add_comment(self.current_file, comment, author, position)
            
            # 更新UI显示注释标记
            self.file_model.set_custom_data(
                self.current_file, 
                'tooltip', 
                f"有{len(self.collaboration_manager.comments.get(self.current_file, []))}条注释"
            )
    
    def add_tag(self):
        if not self.current_file:
            QMessageBox.information(self, "信息", "请先打开一个文件")
            return
        
        tag, ok = QInputDialog.getText(self, "添加标签", "输入标签名称:")
        if ok and tag:
            self.collaboration_manager.add_tag(self.current_file, tag)
            self.load_common_tags()
            self.statusBar().showMessage(f"已添加标签: {tag}")
    
    def manage_tags(self):
        if not self.current_file:
            QMessageBox.information(self, "信息", "请先打开一个文件")
            return
        
        dialog = TagManagerDialog(self.collaboration_manager, self.current_file, self)
        dialog.exec_()
        self.load_common_tags()
    
    def manage_tags_for_path(self, file_path):
        dialog = TagManagerDialog(self.collaboration_manager, file_path, self)
        dialog.exec_()
        self.load_common_tags()
    
    def load_common_tags(self):
        """加载常用标签"""
        self.tags_list.clear()
        
        # 收集所有文件的标签
        all_tags = {}
        for file_path, tags in self.collaboration_manager.tags.items():
            for tag in tags:
                tag_name = tag['name']
                if tag_name not in all_tags:
                    all_tags[tag_name] = 0
                all_tags[tag_name] += 1
        
        # 按使用频率排序
        sorted_tags = sorted(all_tags.items(), key=lambda x: x[1], reverse=True)
        
        # 添加前10个常用标签
        for tag_name, count in sorted_tags[:10]:
            self.tags_list.add_tag(f"{tag_name} ({count})")
    
    def filter_by_tag(self, tag_name):
        """根据标签过滤文件"""
        # 提取纯标签名（去除计数部分）
        pure_tag_name = tag_name.split(' (')[0]
        
        # 查找带有该标签的文件
        matching_files = []
        for file_path, tags in self.collaboration_manager.tags.items():
            if any(tag['name'] == pure_tag_name for tag in tags):
                matching_files.append(file_path)
        
        # 在实际应用中，这里应该更新文件视图以显示匹配的文件
        if matching_files:
            message = f"找到 {len(matching_files)} 个带有标签 '{pure_tag_name}' 的文件"
            self.statusBar().showMessage(message)
        else:
            self.statusBar().showMessage(f"没有找到带有标签 '{pure_tag_name}' 的文件")
    
    def create_new_folder(self):
        folder_name, ok = QInputDialog.getText(self, "新建文件夹", "输入文件夹名称:")
        if ok and folder_name:
            success = self.file_operations.create_directory(self.file_manager.current_path, folder_name)
            if success:
                self.statusBar().showMessage(f"已创建文件夹: {folder_name}")
                self.refresh_file_view()
            else:
                QMessageBox.critical(self, "错误", "创建文件夹失败")
    
    def refresh_file_view(self):
        self.file_tree.setRootIndex(self.file_model.index(self.file_manager.current_path))
    
    def copy_file(self):
        index = self.file_tree.currentIndex()
        if index.isValid():
            self.copied_file_path = self.file_model.filePath(index)
            self.statusBar().showMessage(f"已复制: {os.path.basename(self.copied_file_path)}")
    
    def cut_file(self):
        index = self.file_tree.currentIndex()
        if index.isValid():
            self.cut_file_path = self.file_model.filePath(index)
            self.statusBar().showMessage(f"已剪切: {os.path.basename(self.cut_file_path)}")
    
    def paste_file(self):
        if hasattr(self, 'copied_file_path') and self.copied_file_path:
            dest_path = self.file_manager.current_path
            file_name = os.path.basename(self.copied_file_path)
            new_path = os.path.join(dest_path, file_name)
            
            success = self.file_operations.copy_file(self.copied_file_path, new_path)
            if success:
                self.statusBar().showMessage(f"已粘贴: {file_name}")
                self.refresh_file_view()
            else:
                QMessageBox.critical(self, "错误", "粘贴文件失败")
        
        elif hasattr(self, 'cut_file_path') and self.cut_file_path:
            dest_path = self.file_manager.current_path
            file_name = os.path.basename(self.cut_file_path)
            new_path = os.path.join(dest_path, file_name)
            
            success = self.file_operations.move_file(self.cut_file_path, new_path)
            if success:
                self.statusBar().showMessage(f"已移动: {file_name}")
                self.refresh_file_view()
                del self.cut_file_path
            else:
                QMessageBox.critical(self, "错误", "移动文件失败")
    
    def delete_file(self):
        index = self.file_tree.currentIndex()
        if index.isValid():
            file_path = self.file_model.filePath(index)
            file_name = os.path.basename(file_path)
            
            reply = QMessageBox.question(
                self, "确认删除", 
                f"确定要删除 '{file_name}' 吗？此操作不可恢复。",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                success = self.file_operations.delete_file(file_path)
                if success:
                    self.statusBar().showMessage(f"已删除: {file_name}")
                    self.refresh_file_view()
                else:
                    QMessageBox.critical(self, "错误", "删除文件失败")
    
    def copy_file_path(self, file_path):
        clipboard = QApplication.clipboard()
        clipboard.setText(file_path)
        self.statusBar().showMessage("已复制文件路径到剪贴板")
    
    def delete_file_path(self, file_path):
        file_name = os.path.basename(file_path)
        
        reply = QMessageBox.question(
            self, "确认删除", 
            f"确定要删除 '{file_name}' 吗？此操作不可恢复。",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success = self.file_operations.delete_file(file_path)
            if success:
                self.statusBar().showMessage(f"已删除: {file_name}")
                self.refresh_file_view()
            else:
                QMessageBox.critical(self, "错误", "删除文件失败")
    
    def undo(self):
        current_widget = self.tab_widget.currentWidget()
        if isinstance(current_widget, QTextEdit):
            current_widget.undo()
    
    def redo(self):
        current_widget = self.tab_widget.currentWidget()
        if isinstance(current_widget, QTextEdit):
            current_widget.redo()
    
    def find(self):
        current_widget = self.tab_widget.currentWidget()
        if isinstance(current_widget, QTextEdit):
            find_text, ok = QInputDialog.getText(self, "查找", "查找内容:")
            if ok and find_text:
                if current_widget.find(find_text):
                    self.statusBar().showMessage(f"找到: {find_text}")
                else:
                    self.statusBar().showMessage(f"未找到: {find_text}")
    
    def replace(self):
        current_widget = self.tab_widget.currentWidget()
        if isinstance(current_widget, QTextEdit):
            find_text, ok = QInputDialog.getText(self, "替换", "查找内容:")
            if ok and find_text:
                replace_text, ok = QInputDialog.getText(self, "替换", "替换为:")
                if ok:
                    # 简单的替换实现
                    text = current_widget.toPlainText()
                    new_text = text.replace(find_text, replace_text)
                    current_widget.setPlainText(new_text)
                    self.statusBar().showMessage(f"已替换 {find_text} 为 {replace_text}")
    
    def zoom_in(self):
        current_widget = self.tab_widget.currentWidget()
        if isinstance(current_widget, QTextEdit):
            current_font = current_widget.font()
            current_size = current_font.pointSize()
            current_font.setPointSize(current_size + 1)
            current_widget.setFont(current_font)
    
    def zoom_out(self):
        current_widget = self.tab_widget.currentWidget()
        if isinstance(current_widget, QTextEdit):
            current_font = current_widget.font()
            current_size = current_font.pointSize()
            if current_size > 1:
                current_font.setPointSize(current_size - 1)
                current_widget.setFont(current_font)
    
    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
    
    def show_about(self):
        QMessageBox.about(self, "关于", 
                         "产品交付物系统\n\n"
                         "一个强大的工具，用于管理产品交付物，支持版本控制、协作和高级搜索功能。")
    
    def show_documentation(self):
        # 在实际应用中，这里应该打开帮助文档
        QMessageBox.information(self, "文档", "帮助文档尚未完成。")


# ==================== 应用程序入口 ====================

def main():
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = ProductDeliverySystem()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()