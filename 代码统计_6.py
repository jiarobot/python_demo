import os
import sys
import re
import ast
import time
import json
import tempfile
import webbrowser
from collections import defaultdict, Counter
from datetime import datetime, timedelta

# 修改导入部分为 PyQt6
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTreeWidget, QTreeWidgetItem, QPushButton,
                             QFileDialog, QLabel, QSplitter, QProgressBar, QMessageBox,
                             QHeaderView, QComboBox, QLineEdit, QCheckBox, QTabWidget,
                             QGroupBox, QTextEdit, QSpinBox, QDoubleSpinBox, QToolBar,
                              QMenu, QStatusBar, QDialog, QFormLayout, QDialogButtonBox,
                             QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem,
                             QSlider, QDateTimeEdit, QToolButton, QMenuBar, QSystemTrayIcon,
                             QStyle, QInputDialog, QGridLayout, QSizePolicy)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSettings, QSize, QTimer, QDateTime, QPoint, QRect
from PyQt6.QtGui import QFont, QBrush, QColor, QIcon, QPixmap, QPalette, QPainter, QLinearGradient, QPen, QAction, QActionEvent

import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
from pylint import epylint as lint
import pandas as pd
from scipy import stats
import seaborn as sns
import networkx as nx
from git import Repo, GitCommandError, InvalidGitRepositoryError
import xml.etree.ElementTree as ET
import sqlite3
import zipfile
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading
import concurrent.futures
from pathlib import Path

# 文件类型和对应的扩展名映射
FILE_TYPES = {
    "Python": [".py"],
    "JavaScript": [".js", ".jsx", ".ts", ".tsx"],
    "HTML": [".html", ".htm", ".xhtml"],
    "CSS": [".css", ".scss", ".less", ".sass"],
    "Java": [".java"],
    "C++": [".cpp", ".cxx", ".cc", ".c", ".h", ".hpp", ".hh", ".hxx"],
    "C#": [".cs"],
    "PHP": [".php", ".phtml"],
    "Ruby": [".rb", ".rbw"],
    "Go": [".go"],
    "Rust": [".rs"],
    "Swift": [".swift"],
    "Kotlin": [".kt", ".kts"],
    "Shell": [".sh", ".bash", ".zsh", ".fish"],
    "XML": [".xml", ".xsd", ".xsl", ".xslt"],
    "JSON": [".json"],
    "YAML": [".yaml", ".yml"],
    "Markdown": [".md", ".markdown"],
    "SQL": [".sql", ".psql"],
    "Dart": [".dart"],
    "Scala": [".scala"],
    "TypeScript": [".ts", ".tsx"],
    "Vue": [".vue"],
    "Svelte": [".svelte"],
    "R": [".r", ".R"],
    "MATLAB": [".m"],
    "Perl": [".pl", ".pm"],
    "Lua": [".lua"],
    "Haskell": [".hs"],
    "Erlang": [".erl", ".hrl"],
    "Elixir": [".ex", ".exs"],
    "Clojure": [".clj", ".cljs", ".cljc"],
    "Groovy": [".groovy"],
    "PowerShell": [".ps1"],
    "Batch": [".bat", ".cmd"],
    "TeX": [".tex", ".cls", ".sty"],
    "所有文件": ["*"]
}

# 注释符号映射
COMMENT_SYMBOLS = {
    ".py": "#",
    ".js": "//",
    ".jsx": "//",
    ".ts": "//",
    ".tsx": "//",
    ".java": "//",
    ".cpp": "//",
    ".cxx": "//",
    ".cc": "//",
    ".c": "//",
    ".h": "//",
    ".hpp": "//",
    ".hh": "//",
    ".hxx": "//",
    ".cs": "//",
    ".php": "//",
    ".rb": "#",
    ".go": "//",
    ".rs": "//",
    ".swift": "//",
    ".kt": "//",
    ".kts": "//",
    ".sh": "#",
    ".bash": "#",
    ".zsh": "#",
    ".fish": "#",
    ".dart": "//",
    ".scala": "//",
    ".r": "#",
    ".R": "#",
    ".m": "%",
    ".pl": "#",
    ".pm": "#",
    ".lua": "--",
    ".hs": "--",
    ".erl": "%",
    ".hrl": "%",
    ".ex": "#",
    ".exs": "#",
    ".clj": ";",
    ".cljs": ";",
    ".cljc": ";",
    ".groovy": "//",
    ".ps1": "#",
    ".bat": "REM",
    ".cmd": "REM",
    ".tex": "%",
    ".cls": "%",
    ".sty": "%"
}

# 多行注释符号映射
MULTILINE_COMMENT_SYMBOLS = {
    ".py": [('"""', '"""'), ("'''", "'''")],
    ".js": [("/*", "*/")],
    ".jsx": [("/*", "*/")],
    ".ts": [("/*", "*/")],
    ".tsx": [("/*", "*/")],
    ".java": [("/*", "*/"), ("/**", "*/")],
    ".cpp": [("/*", "*/"), ("/**", "*/")],
    ".cxx": [("/*", "*/"), ("/**", "*/")],
    ".cc": [("/*", "*/"), ("/**", "*/")],
    ".c": [("/*", "*/"), ("/**", "*/")],
    ".h": [("/*", "*/"), ("/**", "*/")],
    ".hpp": [("/*", "*/"), ("/**", "*/")],
    ".hh": [("/*", "*/"), ("/**", "*/")],
    ".hxx": [("/*", "*/"), ("/**", "*/")],
    ".cs": [("/*", "*/"), ("/**", "*/")],
    ".php": [("/*", "*/"), ("/**", "*/")],
    ".rb": [("=begin", "=end")],
    ".go": [("/*", "*/")],
    ".rs": [("/*", "*/")],
    ".swift": [("/*", "*/")],
    ".kt": [("/*", "*/")],
    ".kts": [("/*", "*/")],
    ".dart": [("/*", "*/")],
    ".scala": [("/*", "*/")],
    ".css": [("/*", "*/")],
    ".scss": [("/*", "*/")],
    ".less": [("/*", "*/")],
    ".sass": [("/*", "*/")],
}

# 代码质量规则
CODE_QUALITY_RULES = {
    "python": [
        {"name": "函数过长", "pattern": r"def\s+\w+\([^)]*\):\s*$(?:\n(?!\n).*){50,}", "description": "函数超过50行，建议拆分"},
        {"name": "类过长", "pattern": r"class\s+\w+[^}]*$(?:\n(?!\n).*){200,}", "description": "类超过200行，建议拆分"},
        {"name": "嵌套过深", "pattern": r"(\s*(?:if|for|while|with|try|except)\s*.+:\s*$\n\s*){5,}", "description": "代码嵌套超过5层，建议简化"},
        {"name": "魔法数字", "pattern": r"(?<!\w)([0-9]{3,})(?!\w)", "description": "代码中存在魔法数字，建议定义为常量"},
        {"name": "未使用的导入", "pattern": r"^import\s+\w+(?:\s*,\s*\w+)*\s*$|^from\s+[\w.]+\s+import\s+(?:\w+(?:\s*,\s*\w+)*)\s*$", "description": "可能存在未使用的导入"},
    ],
    "javascript": [
        {"name": "函数过长", "pattern": r"function\s+\w+\([^)]*\)\s*\{[^}]{500,}\}", "description": "函数超过500字符，建议拆分"},
        {"name": "回调地狱", "pattern": r"\.then\([^)]*function[^}]*\{[^}]*\.then\([^)]*function[^}]*\{[^}]*\.then", "description": "多层回调嵌套，建议使用async/await"},
        {"name": "var使用", "pattern": r"\bvar\b", "description": "建议使用let或const替代var"},
    ],
    "java": [
        {"name": "过长方法", "pattern": r"(public|private|protected)\s+[^{]+\{[^}]{300,}\}", "description": "方法过长，建议拆分"},
        {"name": "大类", "pattern": r"class\s+\w+[^}]*\{[^}]{1000,}\}", "description": "类过大，建议拆分"},
    ]
}

# 代码质量评分权重
QUALITY_WEIGHTS = {
    "comment_ratio": 0.2,
    "function_length": 0.15,
    "complexity": 0.25,
    "duplication": 0.2,
    "rule_violations": 0.2
}

class EnhancedCodeAnalyzer:
    """增强版代码分析器，支持更多语言特性和质量分析"""
    
    def __init__(self):
        self.total_lines = 0
        self.code_lines = 0
        self.comment_lines = 0
        self.blank_lines = 0
        self.file_type = ""
        self.function_count = 0
        self.class_count = 0
        self.import_count = 0
        self.function_details = []
        self.class_details = []
        self.quality_issues = []
        self.quality_score = 100  # 初始质量分数
        
    def analyze_file(self, file_path):
        """分析单个文件，返回详细统计信息"""
        self.total_lines = 0
        self.code_lines = 0
        self.comment_lines = 0
        self.blank_lines = 0
        self.function_count = 0
        self.class_count = 0
        self.import_count = 0
        self.function_details = []
        self.class_details = []
        self.quality_issues = []
        self.quality_score = 100
        
        _, ext = os.path.splitext(file_path)
        self.file_type = ext.lower()
        
        # 获取注释符号
        single_comment = COMMENT_SYMBOLS.get(self.file_type, "")
        multi_comments = MULTILINE_COMMENT_SYMBOLS.get(self.file_type, [])
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
                
                in_multiline_comment = False
                current_multiline_end = None
                in_string = False
                string_char = None
                
                for line_num, line in enumerate(lines, 1):
                    self.total_lines += 1
                    stripped_line = line.strip()
                    
                    # 处理字符串状态
                    if not in_multiline_comment:
                        in_string, string_char = self._check_string_state(line, in_string, string_char)
                    
                    # 检查是否在多行注释中
                    if in_multiline_comment:
                        self.comment_lines += 1
                        if current_multiline_end and current_multiline_end in stripped_line and not in_string:
                            in_multiline_comment = False
                        continue
                    
                    # 检查是否开始多行注释
                    multiline_started = False
                    for start, end in multi_comments:
                        if start in stripped_line and not in_string:
                            # 确保多行注释符号不在字符串中
                            start_pos = stripped_line.find(start)
                            if not self._is_in_string(stripped_line, start_pos, start):
                                self.comment_lines += 1
                                in_multiline_comment = True
                                current_multiline_end = end
                                multiline_started = True
                                break
                    
                    if multiline_started:
                        continue
                    
                    # 检查单行注释
                    if single_comment and stripped_line.startswith(single_comment) and not in_string:
                        self.comment_lines += 1
                    # 检查空行
                    elif not stripped_line:
                        self.blank_lines += 1
                    else:
                        self.code_lines += 1
                
                # 语言特定分析
                if self.file_type == '.py':
                    self._analyze_python_file(content, file_path)
                elif self.file_type in ['.js', '.jsx', '.ts', '.tsx']:
                    self._analyze_javascript_file(content, file_path)
                elif self.file_type == '.java':
                    self._analyze_java_file(content, file_path)
                
                # 计算质量分数
                self._calculate_quality_score()
                        
        except Exception as e:
            print(f"Error analyzing {file_path}: {str(e)}")
            return None
            
        return {
            'total': self.total_lines,
            'code': self.code_lines,
            'comments': self.comment_lines,
            'blanks': self.blank_lines,
            'functions': self.function_count,
            'classes': self.class_count,
            'imports': self.import_count,
            'function_details': self.function_details,
            'class_details': self.class_details,
            'quality_issues': self.quality_issues,
            'quality_score': self.quality_score
        }
    
    def _analyze_python_file(self, content, file_path):
        """分析Python文件的特定元素"""
        try:
            tree = ast.parse(content)
            
            # 统计函数和类
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    self.function_count += 1
                    # 计算函数行数
                    func_lines = node.end_lineno - node.lineno + 1 if hasattr(node, 'end_lineno') else 0
                    self.function_details.append({
                        'name': node.name,
                        'line': node.lineno,
                        'lines': func_lines,
                        'type': 'function'
                    })
                    
                    # 检查函数是否过长
                    if func_lines > 50:
                        self.quality_issues.append({
                            'type': 'function_length',
                            'message': f"函数 '{node.name}' 过长 ({func_lines} 行)",
                            'line': node.lineno,
                            'severity': 'warning'
                        })
                        
                elif isinstance(node, ast.ClassDef):
                    self.class_count += 1
                    # 计算类行数
                    class_lines = node.end_lineno - node.lineno + 1 if hasattr(node, 'end_lineno') else 0
                    self.class_details.append({
                        'name': node.name,
                        'line': node.lineno,
                        'lines': class_lines,
                        'type': 'class'
                    })
                    
                    # 检查类是否过大
                    if class_lines > 200:
                        self.quality_issues.append({
                            'type': 'class_size',
                            'message': f"类 '{node.name}' 过大 ({class_lines} 行)",
                            'line': node.lineno,
                            'severity': 'warning'
                        })
                        
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    self.import_count += 1
                    
            # 检查代码质量规则
            self._check_quality_rules(content, 'python', file_path)
                    
        except Exception as e:
            print(f"Error in Python AST analysis: {e}")
    
    def _analyze_javascript_file(self, content, file_path):
        """分析JavaScript文件的特定元素"""
        # 统计函数
        function_pattern = r'(?:function\s+(\w+)|const\s+(\w+)\s*=\s*\([^)]*\)\s*=>|let\s+(\w+)\s*=\s*\([^)]*\)\s*=>|var\s+(\w+)\s*=\s*\([^)]*\)\s*=>|(\w+)\s*\([^)]*\)\s*\{)'
        functions = re.finditer(function_pattern, content)
        
        for match in functions:
            self.function_count += 1
            func_name = next((name for name in match.groups() if name), 'anonymous')
            self.function_details.append({
                'name': func_name,
                'line': content[:match.start()].count('\n') + 1,
                'lines': 0,  # 需要更复杂的逻辑来计算行数
                'type': 'function'
            })
        
        # 统计类
        class_pattern = r'class\s+(\w+)'
        classes = re.finditer(class_pattern, content)
        
        for match in classes:
            self.class_count += 1
            self.class_details.append({
                'name': match.group(1),
                'line': content[:match.start()].count('\n') + 1,
                'lines': 0,  # 需要更复杂的逻辑来计算行数
                'type': 'class'
            })
        
        # 检查代码质量规则
        self._check_quality_rules(content, 'javascript', file_path)
    
    def _analyze_java_file(self, content, file_path):
        """分析Java文件的特定元素"""
        # 统计方法
        method_pattern = r'(public|private|protected|static|\s) +[\w\<\>\[\]]+\s+(\w+) *\([^\)]*\) *(\{?|[^;])'
        methods = re.finditer(method_pattern, content)
        
        for match in methods:
            self.function_count += 1
            self.function_details.append({
                'name': match.group(2),
                'line': content[:match.start()].count('\n') + 1,
                'lines': 0,  # 需要更复杂的逻辑来计算行数
                'type': 'method'
            })
        
        # 统计类
        class_pattern = r'class\s+(\w+)'
        classes = re.finditer(class_pattern, content)
        
        for match in classes:
            self.class_count += 1
            self.class_details.append({
                'name': match.group(1),
                'line': content[:match.start()].count('\n') + 1,
                'lines': 0,  # 需要更复杂的逻辑来计算行数
                'type': 'class'
            })
        
        # 检查代码质量规则
        self._check_quality_rules(content, 'java', file_path)
    
    def _check_quality_rules(self, content, language, file_path):
        """检查代码质量规则"""
        if language not in CODE_QUALITY_RULES:
            return
            
        for rule in CODE_QUALITY_RULES[language]:
            pattern = re.compile(rule['pattern'], re.MULTILINE)
            matches = pattern.finditer(content)
            
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                self.quality_issues.append({
                    'type': 'rule_violation',
                    'message': f"{rule['name']}: {rule['description']}",
                    'line': line_num,
                    'severity': 'warning',
                    'rule': rule['name']
                })
    
    def _calculate_quality_score(self):
        """计算代码质量分数"""
        if self.total_lines == 0:
            self.quality_score = 100
            return
            
        # 注释比例
        comment_ratio = self.comment_lines / self.total_lines
        comment_score = min(100, comment_ratio * 200)  # 注释比例达到50%得100分
        
        # 函数长度扣分
        func_length_score = 100
        if self.function_details:
            avg_func_length = sum(f['lines'] for f in self.function_details) / len(self.function_details)
            if avg_func_length > 30:
                func_length_score = max(0, 100 - (avg_func_length - 30) * 2)
        
        # 质量问题扣分
        issue_score = 100
        if self.quality_issues:
            issue_score = max(0, 100 - len(self.quality_issues) * 5)
        
        # 综合评分
        self.quality_score = int(
            comment_score * QUALITY_WEIGHTS['comment_ratio'] +
            func_length_score * QUALITY_WEIGHTS['function_length'] +
            issue_score * QUALITY_WEIGHTS['rule_violations']
        )
    
    def _check_string_state(self, line, in_string, string_char):
        """检查字符串状态"""
        i = 0
        while i < len(line):
            if in_string:
                # 查找字符串结束
                end_pos = line.find(string_char, i)
                if end_pos == -1:
                    break
                # 检查是否是转义引号
                if end_pos > 0 and line[end_pos-1] == '\\':
                    i = end_pos + 1
                    continue
                in_string = False
                i = end_pos + 1
            else:
                # 查找字符串开始
                single_quote = line.find("'", i)
                double_quote = line.find('"', i)
                
                if single_quote == -1 and double_quote == -1:
                    break
                    
                if single_quote == -1:
                    quote_pos = double_quote
                    string_char = '"'
                elif double_quote == -1:
                    quote_pos = single_quote
                    string_char = "'"
                else:
                    if single_quote < double_quote:
                        quote_pos = single_quote
                        string_char = "'"
                    else:
                        quote_pos = double_quote
                        string_char = '"'
                
                in_string = True
                i = quote_pos + 1
        
        return in_string, string_char
    
    def _is_in_string(self, line, pos, symbol):
        """检查符号是否在字符串中"""
        # 简化实现，实际应用中可能需要更复杂的逻辑
        in_string = False
        quote_char = None
        
        for i, char in enumerate(line):
            if char in ('"', "'") and (i == 0 or line[i-1] != '\\'):
                if in_string and char == quote_char:
                    in_string = False
                    quote_char = None
                else:
                    in_string = True
                    quote_char = char
            
            if i == pos:
                return in_string
                
        return in_string


class ComplexityAnalyzer:
    """代码复杂度分析器"""
    
    def __init__(self):
        self.complexity_results = {}
        
    def analyze_complexity(self, file_path):
        """分析代码复杂度"""
        if not file_path.endswith('.py'):
            return None
            
        try:
            # 使用pylint分析Python代码复杂度
            pylint_stdout, pylint_stderr = lint.py_run(file_path, return_std=True)
            output = pylint_stdout.getvalue()
            
            # 提取复杂度信息
            complexity_match = re.search(r'complexity: (\d+\.?\d*)', output)
            if complexity_match:
                complexity = float(complexity_match.group(1))
                return complexity
                
        except Exception as e:
            print(f"Error in complexity analysis: {e}")
            
        return None


class DuplicateCodeDetector:
    """重复代码检测器"""
    
    def __init__(self, min_lines=5):
        self.min_lines = min_lines
        self.duplicates = []
        
    def find_duplicates(self, directory, file_extensions):
        """查找重复代码"""
        file_contents = {}
        
        # 读取所有文件内容
        for root, _, files in os.walk(directory):
            for file in files:
                _, ext = os.path.splitext(file)
                if ext in file_extensions:
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            file_contents[file_path] = content
                    except Exception as e:
                        print(f"Error reading {file_path}: {e}")
        
        # 查找重复代码块
        self.duplicates = self._find_duplicate_blocks(file_contents)
        return self.duplicates
    
    def _find_duplicate_blocks(self, file_contents):
        """查找重复代码块"""
        duplicates = []
        content_blocks = {}
        
        # 将每个文件分割成代码块
        for file_path, content in file_contents.items():
            lines = content.split('\n')
            for i in range(0, len(lines) - self.min_lines + 1):
                block = '\n'.join(lines[i:i+self.min_lines])
                if block.strip():  # 忽略空块
                    if block not in content_blocks:
                        content_blocks[block] = []
                    content_blocks[block].append((file_path, i+1))
        
        # 找出重复的代码块
        for block, occurrences in content_blocks.items():
            if len(occurrences) > 1:
                duplicates.append({
                    'block': block,
                    'occurrences': occurrences,
                    'count': len(occurrences)
                })
        
        return duplicates


class GitHistoryAnalyzer:
    """Git历史分析器"""
    
    def __init__(self):
        self.repo = None
        self.commits = []
        
    def analyze_repository(self, directory):
        """分析Git仓库"""
        try:
            self.repo = Repo(directory)
            self.commits = list(self.repo.iter_commits())
            return True
        except (GitCommandError, InvalidGitRepositoryError) as e:
            print(f"Error analyzing Git repository: {e}")
            return False
    
    def get_code_hotspots(self, file_extensions):
        """获取代码热点（经常修改的文件）"""
        if not self.repo:
            return {}
            
        file_changes = defaultdict(int)
        
        for commit in self.commits:
            for file in commit.stats.files:
                _, ext = os.path.splitext(file)
                if ext in file_extensions or "*" in file_extensions:
                    file_changes[file] += 1
        
        return dict(file_changes)
    
    def get_developer_stats(self):
        """获取开发者统计信息"""
        if not self.repo:
            return {}
            
        developer_stats = defaultdict(lambda: {'commits': 0, 'additions': 0, 'deletions': 0})
        
        for commit in self.commits:
            author = commit.author.email
            developer_stats[author]['commits'] += 1
            
            # 统计代码变更
            stats = commit.stats.total
            developer_stats[author]['additions'] += stats.get('insertions', 0)
            developer_stats[author]['deletions'] += stats.get('deletions', 0)
        
        return dict(developer_stats)
    
    def get_timeline_data(self, file_extensions):
        """获取时间线数据"""
        if not self.repo:
            return {}
            
        timeline_data = defaultdict(lambda: {'commits': 0, 'files': 0, 'additions': 0, 'deletions': 0})
        
        for commit in self.commits:
            date = commit.committed_datetime.date()
            date_str = date.isoformat()
            
            timeline_data[date_str]['commits'] += 1
            
            # 统计文件变更
            for file in commit.stats.files:
                _, ext = os.path.splitext(file)
                if ext in file_extensions or "*" in file_extensions:
                    timeline_data[date_str]['files'] += 1
            
            # 统计代码变更
            stats = commit.stats.total
            timeline_data[date_str]['additions'] += stats.get('insertions', 0)
            timeline_data[date_str]['deletions'] += stats.get('deletions', 0)
        
        return dict(timeline_data)


class RealTimeAnalyzer(QThread):
    """实时分析线程"""
    
    progress = pyqtSignal(int, str)
    result = pyqtSignal(dict)
    finished = pyqtSignal()
    
    def __init__(self, directory, file_extensions, interval=5):
        super().__init__()
        self.directory = directory
        self.file_extensions = file_extensions
        self.interval = interval
        self.is_running = True
        
    def run(self):
        """执行实时分析"""
        analyzer = EnhancedCodeAnalyzer()
        
        while self.is_running:
            results = defaultdict(lambda: {
                'files': 0, 'total': 0, 'code': 0, 'comments': 0, 'blanks': 0,
                'functions': 0, 'classes': 0, 'imports': 0, 'quality_score': 0
            })
            
            # 获取所有文件
            all_files = []
            for root, _, files in os.walk(self.directory):
                for file in files:
                    if file.startswith('.'):
                        continue
                        
                    _, ext = os.path.splitext(file)
                    if ext in self.file_extensions or "*" in self.file_extensions:
                        all_files.append(os.path.join(root, file))
            
            total_files = len(all_files)
            if total_files == 0:
                self.finished.emit()
                return
                
            # 分析每个文件
            for i, file_path in enumerate(all_files):
                if not self.is_running:
                    break
                    
                self.progress.emit(int((i + 1) / total_files * 100), f"实时分析: {os.path.basename(file_path)}")
                
                file_stats = analyzer.analyze_file(file_path)
                if file_stats:
                    _, ext = os.path.splitext(file_path)
                    file_type = ext.lower()
                    
                    results[file_type]['files'] += 1
                    results[file_type]['total'] += file_stats['total']
                    results[file_type]['code'] += file_stats['code']
                    results[file_type]['comments'] += file_stats['comments']
                    results[file_type]['blanks'] += file_stats['blanks']
                    results[file_type]['functions'] += file_stats['functions']
                    results[file_type]['classes'] += file_stats['classes']
                    results[file_type]['imports'] += file_stats['imports']
                    results[file_type]['quality_score'] = file_stats['quality_score']
            
            if self.is_running:
                self.result.emit(dict(results))
                
            # 等待下一次分析
            for i in range(self.interval * 10):
                if not self.is_running:
                    break
                time.sleep(0.1)
        
        self.finished.emit()
    
    def stop(self):
        """停止分析"""
        self.is_running = False


class AnalysisWorker(QThread):
    """后台分析线程"""
    
    # 定义信号
    progress = pyqtSignal(int, str)
    result = pyqtSignal(dict)
    finished = pyqtSignal()
    error = pyqtSignal(str)
    complexity_result = pyqtSignal(dict)
    duplicates_result = pyqtSignal(list)
    quality_issues_result = pyqtSignal(dict)
    git_stats_result = pyqtSignal(dict)
    timeline_data_result = pyqtSignal(dict)
    
    def __init__(self, directory, file_types, exclude_dirs=None, exclude_files=None, 
                 analyze_complexity=False, detect_duplicates=False, min_duplicate_lines=5,
                 analyze_git=False, realtime_analysis=False):
        super().__init__()
        self.directory = directory
        self.file_types = file_types
        self.exclude_dirs = exclude_dirs or []
        self.exclude_files = exclude_files or []
        self.analyze_complexity = analyze_complexity
        self.detect_duplicates = detect_duplicates
        self.min_duplicate_lines = min_duplicate_lines
        self.analyze_git = analyze_git
        self.realtime_analysis = realtime_analysis
        self.is_running = True
        
    def run(self):
        """执行分析"""
        analyzer = EnhancedCodeAnalyzer()
        complexity_analyzer = ComplexityAnalyzer()
        duplicate_detector = DuplicateCodeDetector(self.min_duplicate_lines)
        git_analyzer = GitHistoryAnalyzer()
        
        results = defaultdict(lambda: {
            'files': 0, 'total': 0, 'code': 0, 'comments': 0, 'blanks': 0,
            'functions': 0, 'classes': 0, 'imports': 0, 'quality_score': 0
        })
        
        quality_issues = defaultdict(list)
        complexity_results = {}
        git_stats = {}
        timeline_data = {}
        
        # 获取所有文件
        all_files = []
        for root, dirs, files in os.walk(self.directory):
            # 排除目录
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs and not d.startswith('.')]
            
            for file in files:
                if file in self.exclude_files or file.startswith('.'):
                    continue
                    
                _, ext = os.path.splitext(file)
                if ext in self.file_types or "*" in self.file_types:
                    all_files.append(os.path.join(root, file))
        
        total_files = len(all_files)
        if total_files == 0:
            self.error.emit("在选定的目录中未找到匹配的文件。")
            return
            
        # 分析Git历史
        if self.analyze_git:
            self.progress.emit(0, "分析Git历史...")
            if git_analyzer.analyze_repository(self.directory):
                git_stats = git_analyzer.get_developer_stats()
                timeline_data = git_analyzer.get_timeline_data(self.file_types)
                self.git_stats_result.emit(git_stats)
                self.timeline_data_result.emit(timeline_data)
        
        # 分析每个文件
        for i, file_path in enumerate(all_files):
            if not self.is_running:
                break
                
            self.progress.emit(int((i + 1) / total_files * 100), f"分析中: {os.path.basename(file_path)}")
            
            file_stats = analyzer.analyze_file(file_path)
            if file_stats:
                _, ext = os.path.splitext(file_path)
                file_type = ext.lower()
                
                results[file_type]['files'] += 1
                results[file_type]['total'] += file_stats['total']
                results[file_type]['code'] += file_stats['code']
                results[file_type]['comments'] += file_stats['comments']
                results[file_type]['blanks'] += file_stats['blanks']
                results[file_type]['functions'] += file_stats['functions']
                results[file_type]['classes'] += file_stats['classes']
                results[file_type]['imports'] += file_stats['imports']
                results[file_type]['quality_score'] = file_stats['quality_score']
                
                # 收集质量问题
                if file_stats['quality_issues']:
                    quality_issues[file_path] = file_stats['quality_issues']
            
            # 分析代码复杂度
            if self.analyze_complexity and file_path.endswith('.py'):
                complexity = complexity_analyzer.analyze_complexity(file_path)
                if complexity is not None:
                    complexity_results[file_path] = complexity
        
        # 检测重复代码
        duplicates = []
        if self.detect_duplicates and self.is_running:
            self.progress.emit(100, "检测重复代码...")
            duplicates = duplicate_detector.find_duplicates(self.directory, self.file_types)
        
        if self.is_running:
            self.result.emit(dict(results))
            self.quality_issues_result.emit(dict(quality_issues))
            if self.analyze_complexity:
                self.complexity_result.emit(complexity_results)
            if self.detect_duplicates:
                self.duplicates_result.emit(duplicates)
        
        self.finished.emit()
    
    def stop(self):
        """停止分析"""
        self.is_running = False


class MplCanvas(FigureCanvas):
    """Matplotlib画布"""
    
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)


class HeatmapCanvas(FigureCanvas):
    """热力图画布"""
    
    def __init__(self, parent=None, width=8, height=6, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
    
    def create_heatmap(self, data, title="代码热点图"):
        """创建热力图"""
        self.fig.clear()
        
        if not data:
            ax = self.fig.add_subplot(111)
            ax.text(0.5, 0.5, "无数据可用", ha='center', va='center')
            self.draw()
            return
            
        # 准备数据
        files = list(data.keys())
        values = list(data.values())
        
        # 创建热力图
        ax = self.fig.add_subplot(111)
        y_pos = np.arange(len(files))
        
        colors = plt.cm.Reds(np.linspace(0.4, 1, len(files)))
        bars = ax.barh(y_pos, values, align='center', color=colors)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(files)
        ax.invert_yaxis()
        ax.set_xlabel('修改次数')
        ax.set_title(title)
        
        # 添加数值标签
        for i, bar in enumerate(bars):
            width = bar.get_width()
            ax.text(width + 0.1, bar.get_y() + bar.get_height()/2, 
                   f'{int(width)}', ha='left', va='center')
        
        self.fig.tight_layout()
        self.draw()


class TimelineCanvas(FigureCanvas):
    """时间线画布"""
    
    def __init__(self, parent=None, width=10, height=6, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
    
    def create_timeline(self, data, title="代码提交时间线"):
        """创建时间线图"""
        self.fig.clear()
        
        if not data:
            ax = self.fig.add_subplot(111)
            ax.text(0.5, 0.5, "无数据可用", ha='center', va='center')
            self.draw()
            return
            
        # 准备数据
        dates = sorted(data.keys())
        commits = [data[date]['commits'] for date in dates]
        files = [data[date]['files'] for date in dates]
        additions = [data[date]['additions'] for date in dates]
        deletions = [data[date]['deletions'] for date in dates]
        
        # 转换日期
        x = [datetime.strptime(date, "%Y-%m-%d") for date in dates]
        
        # 创建图表
        ax = self.fig.add_subplot(111)
        
        # 绘制提交次数
        ax.plot(x, commits, 'o-', label='提交次数', linewidth=2)
        
        # 绘制文件修改数
        ax.bar(x, files, alpha=0.3, label='文件修改数')
        
        ax.set_xlabel('日期')
        ax.set_ylabel('数量')
        ax.set_title(title)
        ax.legend()
        
        # 格式化日期显示
        self.fig.autofmt_xdate()
        self.fig.tight_layout()
        self.draw()


class SettingsDialog(QDialog):
    """设置对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setModal(True)
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        layout = QFormLayout()
        
        self.min_duplicate_lines = QSpinBox()
        self.min_duplicate_lines.setRange(3, 20)
        self.min_duplicate_lines.setValue(5)
        layout.addRow("最小重复行数:", self.min_duplicate_lines)
        
        self.complexity_threshold = QDoubleSpinBox()
        self.complexity_threshold.setRange(1, 50)
        self.complexity_threshold.setValue(10)
        self.complexity_threshold.setSingleStep(0.5)
        layout.addRow("复杂度阈值:", self.complexity_threshold)
        
        self.realtime_interval = QSpinBox()
        self.realtime_interval.setRange(1, 60)
        self.realtime_interval.setValue(5)
        self.realtime_interval.setSuffix(" 秒")
        layout.addRow("实时分析间隔:", self.realtime_interval)
        
        self.email_notifications = QCheckBox()
        layout.addRow("邮件通知:", self.email_notifications)
        
        self.email_server = QLineEdit()
        self.email_server.setPlaceholderText("SMTP服务器地址")
        layout.addRow("SMTP服务器:", self.email_server)
        
        self.email_port = QSpinBox()
        self.email_port.setRange(1, 65535)
        self.email_port.setValue(587)
        layout.addRow("SMTP端口:", self.email_port)
        
        self.email_user = QLineEdit()
        self.email_user.setPlaceholderText("邮箱用户名")
        layout.addRow("邮箱用户名:", self.email_user)
        
        self.email_password = QLineEdit()
        self.email_password.setPlaceholderText("邮箱密码")
        self.email_password.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow("邮箱密码:", self.email_password)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        
        self.setLayout(layout)
    
    def get_settings(self):
        """获取设置"""
        return {
            'min_duplicate_lines': self.min_duplicate_lines.value(),
            'complexity_threshold': self.complexity_threshold.value(),
            'realtime_interval': self.realtime_interval.value(),
            'email_notifications': self.email_notifications.isChecked(),
            'email_server': self.email_server.text(),
            'email_port': self.email_port.value(),
            'email_user': self.email_user.text(),
            'email_password': self.email_password.text()
        }


class CodeMetricsTool(QMainWindow):
    """主界面类"""
    
    def __init__(self):
        super().__init__()
        self.worker = None
        self.realtime_worker = None
        self.results = {}
        self.complexity_results = {}
        self.duplicates = []
        self.quality_issues = {}
        self.git_stats = {}
        self.timeline_data = {}
        self.settings = QSettings("CodeMetrics", "CodeMetricsTool")
        self.init_ui()
        self.load_settings()
        
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle('高级代码量量化工具')
        self.setGeometry(100, 100, 1600, 1000)
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 创建工具栏
        self.create_toolbar()
        
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 顶部控制区域
        control_layout = QHBoxLayout()
        
        self.dir_label = QLabel("目录: 未选择")
        control_layout.addWidget(self.dir_label)
        
        self.select_btn = QPushButton("选择目录")
        self.select_btn.clicked.connect(self.select_directory)
        control_layout.addWidget(self.select_btn)
        
        self.file_type_combo = QComboBox()
        self.file_type_combo.addItems(FILE_TYPES.keys())
        control_layout.addWidget(QLabel("文件类型:"))
        control_layout.addWidget(self.file_type_combo)
        
        self.exclude_dirs_edit = QLineEdit()
        self.exclude_dirs_edit.setPlaceholderText("排除目录，用逗号分隔 (如: node_modules, .git)")
        control_layout.addWidget(QLabel("排除目录:"))
        control_layout.addWidget(self.exclude_dirs_edit)
        
        main_layout.addLayout(control_layout)
        
        # 选项区域
        options_layout = QHBoxLayout()
        
        self.complexity_check = QCheckBox("分析代码复杂度 (仅Python)")
        options_layout.addWidget(self.complexity_check)
        
        self.duplicates_check = QCheckBox("检测重复代码")
        options_layout.addWidget(self.duplicates_check)
        
        self.git_check = QCheckBox("分析Git历史")
        options_layout.addWidget(self.git_check)
        
        self.realtime_check = QCheckBox("实时分析")
        options_layout.addWidget(self.realtime_check)
        
        self.settings_btn = QPushButton("设置")
        self.settings_btn.clicked.connect(self.show_settings)
        options_layout.addWidget(self.settings_btn)
        
        options_layout.addStretch()
        
        self.analyze_btn = QPushButton("开始分析")
        self.analyze_btn.clicked.connect(self.start_analysis)
        self.analyze_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; }")
        options_layout.addWidget(self.analyze_btn)
        
        self.export_btn = QPushButton("导出结果")
        self.export_btn.clicked.connect(self.export_results)
        self.export_btn.setEnabled(False)
        options_layout.addWidget(self.export_btn)
        
        main_layout.addLayout(options_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel()
        self.progress_label.setVisible(False)
        main_layout.addWidget(self.progress_label)
        
        # 标签页
        self.tabs = QTabWidget()
        
        # 统计结果标签页
        stats_tab = QWidget()
        stats_layout = QVBoxLayout(stats_tab)
        
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # 结果树形视图
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["文件类型", "文件数", "总行数", "代码行", "注释行", "空行", "函数数", "类数", "导入数", "代码/总行比例", "质量分数"])
        self.tree_widget.header().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        splitter.addWidget(self.tree_widget)
        
        # 详细信息区域
        detail_widget = QWidget()
        detail_layout = QVBoxLayout(detail_widget)
        
        self.detail_label = QLabel("详细信息将在这里显示")
        self.detail_label.setWordWrap(True)
        self.detail_label.setStyleSheet("background-color: #f0f0f0; padding: 10px;")
        detail_layout.addWidget(self.detail_label)
        
        splitter.addWidget(detail_widget)
        splitter.setSizes([600, 200])
        
        stats_layout.addWidget(splitter)
        self.tabs.addTab(stats_tab, "统计结果")
        
        # 图表标签页
        chart_tab = QWidget()
        chart_layout = QVBoxLayout(chart_tab)
        
        self.chart_canvas = MplCanvas(self, width=10, height=8, dpi=100)
        chart_layout.addWidget(self.chart_canvas)
        
        self.tabs.addTab(chart_tab, "图表")
        
        # 复杂度标签页
        complexity_tab = QWidget()
        complexity_layout = QVBoxLayout(complexity_tab)
        
        self.complexity_tree = QTreeWidget()
        self.complexity_tree.setHeaderLabels(["文件", "复杂度分数", "状态"])
        complexity_layout.addWidget(self.complexity_tree)
        
        self.tabs.addTab(complexity_tab, "代码复杂度")
        
        # 重复代码标签页
        duplicates_tab = QWidget()
        duplicates_layout = QVBoxLayout(duplicates_tab)
        
        self.duplicates_tree = QTreeWidget()
        self.duplicates_tree.setHeaderLabels(["重复代码", "出现次数", "位置"])
        duplicates_layout.addWidget(self.duplicates_tree)
        
        self.tabs.addTab(duplicates_tab, "重复代码")
        
        # 质量问题标签页
        quality_tab = QWidget()
        quality_layout = QVBoxLayout(quality_tab)
        
        self.quality_tree = QTreeWidget()
        self.quality_tree.setHeaderLabels(["文件", "问题类型", "描述", "行号", "严重性"])
        quality_layout.addWidget(self.quality_tree)
        
        self.tabs.addTab(quality_tab, "质量问题")
        
        # Git统计标签页
        git_tab = QWidget()
        git_layout = QVBoxLayout(git_tab)
        
        self.git_tree = QTreeWidget()
        self.git_tree.setHeaderLabels(["开发者", "提交数", "添加行数", "删除行数", "净变化"])
        git_layout.addWidget(self.git_tree)
        
        self.tabs.addTab(git_tab, "Git统计")
        
        # 时间线标签页
        timeline_tab = QWidget()
        timeline_layout = QVBoxLayout(timeline_tab)
        
        self.timeline_canvas = TimelineCanvas(self, width=10, height=6, dpi=100)
        timeline_layout.addWidget(self.timeline_canvas)
        
        self.tabs.addTab(timeline_tab, "时间线")
        
        # 热点图标签页
        heatmap_tab = QWidget()
        heatmap_layout = QVBoxLayout(heatmap_tab)
        
        self.heatmap_canvas = HeatmapCanvas(self, width=10, height=6, dpi=100)
        heatmap_layout.addWidget(self.heatmap_canvas)
        
        self.tabs.addTab(heatmap_tab, "热点图")
        
        main_layout.addWidget(self.tabs)
        
        # 状态栏
        self.status_bar = self.statusBar()
        self.status_label = QLabel("就绪")
        self.status_bar.addWidget(self.status_label)
        
        # 连接信号
        self.tree_widget.itemSelectionChanged.connect(self.show_detail)
        
    def create_menu_bar(self):
        """创建菜单栏"""
        menu_bar = self.menuBar()
        
        # 文件菜单
        file_menu = menu_bar.addMenu("文件")
        
        open_action = QAction("打开目录", self)
        open_action.triggered.connect(self.select_directory)
        file_menu.addAction(open_action)
        
        export_action = QAction("导出结果", self)
        export_action.triggered.connect(self.export_results)
        file_menu.addAction(export_action)
        
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 分析菜单
        analysis_menu = menu_bar.addMenu("分析")
        
        start_action = QAction("开始分析", self)
        start_action.triggered.connect(self.start_analysis)
        analysis_menu.addAction(start_action)
        
        stop_action = QAction("停止分析", self)
        stop_action.triggered.connect(self.stop_analysis)
        analysis_menu.addAction(stop_action)
        
        # 视图菜单
        view_menu = menu_bar.addMenu("视图")
        
        realtime_action = QAction("实时分析", self, checkable=True)
        realtime_action.triggered.connect(self.toggle_realtime_analysis)
        view_menu.addAction(realtime_action)
        
        # 工具菜单
        tools_menu = menu_bar.addMenu("工具")
        
        settings_action = QAction("设置", self)
        settings_action.triggered.connect(self.show_settings)
        tools_menu.addAction(settings_action)
        
        # 帮助菜单
        help_menu = menu_bar.addMenu("帮助")
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar("主工具栏")
        toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(toolbar)
        
        # 添加动作
        open_action = QAction("打开目录", self)
        open_action.triggered.connect(self.select_directory)
        toolbar.addAction(open_action)
        
        analyze_action = QAction("开始分析", self)
        analyze_action.triggered.connect(self.start_analysis)
        toolbar.addAction(analyze_action)
        
        stop_action = QAction("停止分析", self)
        stop_action.triggered.connect(self.stop_analysis)
        toolbar.addAction(stop_action)
        
        export_action = QAction("导出结果", self)
        export_action.triggered.connect(self.export_results)
        toolbar.addAction(export_action)
        
        toolbar.addSeparator()
        
        settings_action = QAction("设置", self)
        settings_action.triggered.connect(self.show_settings)
        toolbar.addAction(settings_action)
    
    def show_settings(self):
        """显示设置对话框"""
        dialog = SettingsDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.settings_values = dialog.get_settings()
            self.save_settings()
    
    def load_settings(self):
        """加载设置"""
        self.settings_values = {
            'min_duplicate_lines': self.settings.value('min_duplicate_lines', 5, type=int),
            'complexity_threshold': self.settings.value('complexity_threshold', 10.0, type=float),
            'realtime_interval': self.settings.value('realtime_interval', 5, type=int),
            'email_notifications': self.settings.value('email_notifications', False, type=bool),
            'email_server': self.settings.value('email_server', '', type=str),
            'email_port': self.settings.value('email_port', 587, type=int),
            'email_user': self.settings.value('email_user', '', type=str),
            'email_password': self.settings.value('email_password', '', type=str)
        }
    
    def save_settings(self):
        """保存设置"""
        for key, value in self.settings_values.items():
            self.settings.setValue(key, value)
            
    def select_directory(self):
        """选择目录"""
        directory = QFileDialog.getExistingDirectory(self, "选择要分析的目录")
        if directory:
            self.directory = directory
            self.dir_label.setText(f"目录: {directory}")
            
    def start_analysis(self):
        """开始分析"""
        if not hasattr(self, 'directory'):
            QMessageBox.warning(self, "警告", "请先选择要分析的目录")
            return
            
        # 获取选定的文件类型
        selected_type = self.file_type_combo.currentText()
        file_extensions = FILE_TYPES[selected_type]
        
        # 获取排除目录
        exclude_dirs = [d.strip() for d in self.exclude_dirs_edit.text().split(',') if d.strip()]
        
        # 禁用按钮
        self.analyze_btn.setEnabled(False)
        self.select_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 创建并启动工作线程
        self.worker = AnalysisWorker(
            self.directory, 
            file_extensions, 
            exclude_dirs,
            analyze_complexity=self.complexity_check.isChecked(),
            detect_duplicates=self.duplicates_check.isChecked(),
            min_duplicate_lines=self.settings_values['min_duplicate_lines'],
            analyze_git=self.git_check.isChecked(),
            realtime_analysis=self.realtime_check.isChecked()
        )
        self.worker.progress.connect(self.update_progress)
        self.worker.result.connect(self.handle_results)
        self.worker.complexity_result.connect(self.handle_complexity_results)
        self.worker.duplicates_result.connect(self.handle_duplicates_results)
        self.worker.quality_issues_result.connect(self.handle_quality_issues_results)
        self.worker.git_stats_result.connect(self.handle_git_stats_results)
        self.worker.timeline_data_result.connect(self.handle_timeline_data_results)
        self.worker.finished.connect(self.analysis_finished)
        self.worker.error.connect(self.handle_error)
        self.worker.start()
        
        # 启动实时分析
        if self.realtime_check.isChecked():
            self.start_realtime_analysis()
        
    def start_realtime_analysis(self):
        """启动实时分析"""
        if not hasattr(self, 'directory'):
            return
            
        # 获取选定的文件类型
        selected_type = self.file_type_combo.currentText()
        file_extensions = FILE_TYPES[selected_type]
        
        # 停止现有的实时分析
        if self.realtime_worker:
            self.realtime_worker.stop()
            self.realtime_worker.wait()
        
        # 创建并启动实时分析线程
        self.realtime_worker = RealTimeAnalyzer(
            self.directory,
            file_extensions,
            interval=self.settings_values['realtime_interval']
        )
        self.realtime_worker.progress.connect(self.update_progress)
        self.realtime_worker.result.connect(self.handle_realtime_results)
        self.realtime_worker.finished.connect(self.realtime_analysis_finished)
        self.realtime_worker.start()
    
    def stop_analysis(self):
        """停止分析"""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
            
        if self.realtime_worker and self.realtime_worker.isRunning():
            self.realtime_worker.stop()
            self.realtime_worker.wait()
            
        self.analysis_finished()
    
    def toggle_realtime_analysis(self, checked):
        """切换实时分析状态"""
        if checked:
            self.start_realtime_analysis()
        else:
            if self.realtime_worker and self.realtime_worker.isRunning():
                self.realtime_worker.stop()
                self.realtime_worker.wait()
    
    def update_progress(self, value, message):
        """更新进度条"""
        self.progress_bar.setValue(value)
        self.progress_label.setText(message)
        self.status_label.setText(message)
        
    def handle_results(self, results):
        """处理分析结果"""
        self.results = results
        self.display_results()
        self.create_chart()
        self.export_btn.setEnabled(True)
        
    def handle_realtime_results(self, results):
        """处理实时分析结果"""
        self.results = results
        self.display_results()
        self.create_chart()
        
    def handle_complexity_results(self, results):
        """处理复杂度结果"""
        self.complexity_results = results
        self.display_complexity_results()
        
    def handle_duplicates_results(self, results):
        """处理重复代码结果"""
        self.duplicates = results
        self.display_duplicates_results()
        
    def handle_quality_issues_results(self, results):
        """处理质量问题结果"""
        self.quality_issues = results
        self.display_quality_issues()
        
    def handle_git_stats_results(self, results):
        """处理Git统计结果"""
        self.git_stats = results
        self.display_git_stats()
        
    def handle_timeline_data_results(self, results):
        """处理时间线数据结果"""
        self.timeline_data = results
        self.display_timeline_data()
        
    def handle_error(self, error_msg):
        """处理错误"""
        QMessageBox.critical(self, "错误", error_msg)
        
    def analysis_finished(self):
        """分析完成"""
        self.analyze_btn.setEnabled(True)
        self.select_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.status_label.setText("分析完成")
        
    def realtime_analysis_finished(self):
        """实时分析完成"""
        self.status_label.setText("实时分析已停止")
        
    def display_results(self):
        """显示结果"""
        self.tree_widget.clear()
        
        total_files = 0
        total_lines = 0
        total_code = 0
        total_comments = 0
        total_blanks = 0
        total_functions = 0
        total_classes = 0
        total_imports = 0
        total_quality = 0
        type_count = 0
        
        # 添加每种文件类型的结果
        for file_type, stats in self.results.items():
            if stats['files'] == 0:
                continue
                
            total_files += stats['files']
            total_lines += stats['total']
            total_code += stats['code']
            total_comments += stats['comments']
            total_blanks += stats['blanks']
            total_functions += stats['functions']
            total_classes += stats['classes']
            total_imports += stats['imports']
            total_quality += stats['quality_score']
            type_count += 1
            
            # 计算代码比例
            code_ratio = stats['code'] / stats['total'] * 100 if stats['total'] > 0 else 0
            
            item = QTreeWidgetItem([
                file_type, 
                str(stats['files']), 
                str(stats['total']),
                str(stats['code']),
                str(stats['comments']),
                str(stats['blanks']),
                str(stats['functions']),
                str(stats['classes']),
                str(stats['imports']),
                f"{code_ratio:.2f}%",
                f"{stats['quality_score']}/100"
            ])
            
            # 根据代码比例设置颜色
            if code_ratio > 80:
                item.setForeground(9, QBrush(QColor(0, 128, 0)))  # 绿色
            elif code_ratio > 60:
                item.setForeground(9, QBrush(QColor(0, 0, 255)))  # 蓝色
            else:
                item.setForeground(9, QBrush(QColor(255, 0, 0)))  # 红色
                
            # 根据质量分数设置颜色
            if stats['quality_score'] > 80:
                item.setForeground(10, QBrush(QColor(0, 128, 0)))  # 绿色
            elif stats['quality_score'] > 60:
                item.setForeground(10, QBrush(QColor(255, 165, 0)))  # 橙色
            else:
                item.setForeground(10, QBrush(QColor(255, 0, 0)))  # 红色
                
            self.tree_widget.addTopLevelItem(item)
        
        # 添加总计行
        total_ratio = total_code / total_lines * 100 if total_lines > 0 else 0
        avg_quality = total_quality / type_count if type_count > 0 else 0
        
        total_item = QTreeWidgetItem([
            "总计", 
            str(total_files), 
            str(total_lines),
            str(total_code),
            str(total_comments),
            str(total_blanks),
            str(total_functions),
            str(total_classes),
            str(total_imports),
            f"{total_ratio:.2f}%",
            f"{avg_quality:.1f}/100"
        ])
        
        # 设置总计行的字体加粗
        font = QFont()
        font.setBold(True)
        for i in range(11):
            total_item.setFont(i, font)
            
        self.tree_widget.addTopLevelItem(total_item)
        
        # 调整列宽
        for i in range(11):
            self.tree_widget.resizeColumnToContents(i)
            
    def display_complexity_results(self):
        """显示复杂度结果"""
        self.complexity_tree.clear()
        
        threshold = self.settings_values['complexity_threshold']
        
        for file_path, complexity in self.complexity_results.items():
            status = "正常" if complexity <= threshold else "过高"
            color = QColor(0, 128, 0) if complexity <= threshold else QColor(255, 0, 0)
            
            item = QTreeWidgetItem([
                os.path.basename(file_path),
                f"{complexity:.2f}",
                status
            ])
            
            item.setForeground(2, QBrush(color))
            self.complexity_tree.addTopLevelItem(item)
        
        self.complexity_tree.resizeColumnToContents(0)
        self.complexity_tree.resizeColumnToContents(1)
        self.complexity_tree.resizeColumnToContents(2)
        
    def display_duplicates_results(self):
        """显示重复代码结果"""
        self.duplicates_tree.clear()
        
        if not self.duplicates:
            item = QTreeWidgetItem(["未检测到重复代码", "", ""])
            self.duplicates_tree.addTopLevelItem(item)
            return
            
        for duplicate in self.duplicates:
            # 只显示前50个字符的预览
            preview = duplicate['block'][:50] + "..." if len(duplicate['block']) > 50 else duplicate['block']
            
            parent_item = QTreeWidgetItem([
                preview,
                str(duplicate['count']),
                ""
            ])
            
            for file_path, line_num in duplicate['occurrences']:
                child_item = QTreeWidgetItem([
                    "",
                    "",
                    f"{os.path.basename(file_path)}:第{line_num}行"
                ])
                parent_item.addChild(child_item)
            
            self.duplicates_tree.addTopLevelItem(parent_item)
            parent_item.setExpanded(True)
        
        self.duplicates_tree.resizeColumnToContents(0)
        self.duplicates_tree.resizeColumnToContents(1)
        self.duplicates_tree.resizeColumnToContents(2)
    
    def display_quality_issues(self):
        """显示质量问题"""
        self.quality_tree.clear()
        
        if not self.quality_issues:
            item = QTreeWidgetItem(["未检测到质量问题", "", "", "", ""])
            self.quality_tree.addTopLevelItem(item)
            return
            
        for file_path, issues in self.quality_issues.items():
            for issue in issues:
                item = QTreeWidgetItem([
                    os.path.basename(file_path),
                    issue.get('type', '未知'),
                    issue.get('message', ''),
                    str(issue.get('line', '')),
                    issue.get('severity', '未知')
                ])
                
                # 根据严重性设置颜色
                if issue.get('severity') == 'error':
                    item.setForeground(4, QBrush(QColor(255, 0, 0)))
                elif issue.get('severity') == 'warning':
                    item.setForeground(4, QBrush(QColor(255, 165, 0)))
                
                self.quality_tree.addTopLevelItem(item)
        
        self.quality_tree.resizeColumnToContents(0)
        self.quality_tree.resizeColumnToContents(1)
        self.quality_tree.resizeColumnToContents(2)
        self.quality_tree.resizeColumnToContents(3)
        self.quality_tree.resizeColumnToContents(4)
    
    def display_git_stats(self):
        """显示Git统计"""
        self.git_tree.clear()
        
        if not self.git_stats:
            item = QTreeWidgetItem(["无Git统计信息", "", "", "", ""])
            self.git_tree.addTopLevelItem(item)
            return
            
        for developer, stats in self.git_stats.items():
            net_change = stats['additions'] - stats['deletions']
            
            item = QTreeWidgetItem([
                developer,
                str(stats['commits']),
                str(stats['additions']),
                str(stats['deletions']),
                str(net_change)
            ])
            
            # 根据净变化设置颜色
            if net_change > 0:
                item.setForeground(4, QBrush(QColor(0, 128, 0)))
            elif net_change < 0:
                item.setForeground(4, QBrush(QColor(255, 0, 0)))
                
            self.git_tree.addTopLevelItem(item)
        
        self.git_tree.resizeColumnToContents(0)
        self.git_tree.resizeColumnToContents(1)
        self.git_tree.resizeColumnToContents(2)
        self.git_tree.resizeColumnToContents(3)
        self.git_tree.resizeColumnToContents(4)
    
    def display_timeline_data(self):
        """显示时间线数据"""
        self.timeline_canvas.create_timeline(self.timeline_data)
    
    def create_chart(self):
        """创建图表"""
        # 清除现有图表
        self.chart_canvas.axes.clear()
        
        if not self.results:
            return
            
        # 准备数据
        labels = []
        code_values = []
        comment_values = []
        blank_values = []
        
        for file_type, stats in self.results.items():
            if stats['files'] > 0:  # 只显示有文件的类型
                labels.append(file_type)
                code_values.append(stats['code'])
                comment_values.append(stats['comments'])
                blank_values.append(stats['blanks'])
        
        if not labels:
            return
            
        x = np.arange(len(labels))
        width = 0.25
        
        # 创建堆叠柱状图
        self.chart_canvas.axes.bar(x - width, code_values, width, label='代码行', color='green')
        self.chart_canvas.axes.bar(x, comment_values, width, label='注释行', color='blue')
        self.chart_canvas.axes.bar(x + width, blank_values, width, label='空行', color='gray')
        
        self.chart_canvas.axes.set_xlabel('文件类型')
        self.chart_canvas.axes.set_ylabel('行数')
        self.chart_canvas.axes.set_title('代码统计')
        self.chart_canvas.axes.set_xticks(x)
        self.chart_canvas.axes.set_xticklabels(labels, rotation=45, ha='right')
        self.chart_canvas.axes.legend()
        
        # 调整布局
        self.chart_canvas.fig.tight_layout()
        
        # 刷新画布
        self.chart_canvas.draw()
        
    def show_detail(self):
        """显示详细信息"""
        selected_items = self.tree_widget.selectedItems()
        if not selected_items:
            return
            
        item = selected_items[0]
        file_type = item.text(0)
        
        if file_type == "总计":
            detail_text = f"<b>所有文件统计:</b><br>"
            detail_text += f"文件总数: {item.text(1)}<br>"
            detail_text += f"总行数: {item.text(2)}<br>"
            detail_text += f"代码行数: {item.text(3)}<br>"
            detail_text += f"注释行数: {item.text(4)}<br>"
            detail_text += f"空行数: {item.text(5)}<br>"
            detail_text += f"函数数: {item.text(6)}<br>"
            detail_text += f"类数: {item.text(7)}<br>"
            detail_text += f"导入数: {item.text(8)}<br>"
            detail_text += f"代码比例: {item.text(9)}<br>"
            detail_text += f"平均质量分数: {item.text(10)}"
        else:
            detail_text = f"<b>{file_type} 文件统计:</b><br>"
            detail_text += f"文件数: {item.text(1)}<br>"
            detail_text += f"总行数: {item.text(2)}<br>"
            detail_text += f"代码行数: {item.text(3)}<br>"
            detail_text += f"注释行数: {item.text(4)}<br>"
            detail_text += f"空行数: {item.text(5)}<br>"
            detail_text += f"函数数: {item.text(6)}<br>"
            detail_text += f"类数: {item.text(7)}<br>"
            detail_text += f"导入数: {item.text(8)}<br>"
            detail_text += f"代码比例: {item.text(9)}<br>"
            detail_text += f"质量分数: {item.text(10)}"
            
        self.detail_label.setText(detail_text)
        
    def export_results(self):
        """导出结果"""
        if not self.results:
            QMessageBox.warning(self, "警告", "没有可导出的结果")
            return
            
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self, "保存结果", f"code_metrics_{time.strftime('%Y%m%d_%H%M%S')}", 
            "CSV Files (*.csv);;JSON Files (*.json);;Excel Files (*.xlsx);;HTML Report (*.html)"
        )
        
        if not file_path:
            return
            
        try:
            if selected_filter == "CSV Files (*.csv)":
                if not file_path.endswith('.csv'):
                    file_path += '.csv'
                self.export_to_csv(file_path)
            elif selected_filter == "JSON Files (*.json)":
                if not file_path.endswith('.json'):
                    file_path += '.json'
                self.export_to_json(file_path)
            elif selected_filter == "Excel Files (*.xlsx)":
                if not file_path.endswith('.xlsx'):
                    file_path += '.xlsx'
                self.export_to_excel(file_path)
            elif selected_filter == "HTML Report (*.html)":
                if not file_path.endswith('.html'):
                    file_path += '.html'
                self.export_to_html(file_path)
                
            QMessageBox.information(self, "成功", f"结果已导出到 {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")
    
    def export_to_csv(self, file_path):
        """导出为CSV"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("文件类型,文件数,总行数,代码行,注释行,空行,函数数,类数,导入数,代码/总行比例,质量分数\n")
            
            for file_type, stats in self.results.items():
                code_ratio = stats['code'] / stats['total'] * 100 if stats['total'] > 0 else 0
                f.write(f"{file_type},{stats['files']},{stats['total']},{stats['code']},"
                       f"{stats['comments']},{stats['blanks']},{stats['functions']},"
                       f"{stats['classes']},{stats['imports']},{code_ratio:.2f}%,{stats['quality_score']}\n")
    
    def export_to_json(self, file_path):
        """导出为JSON"""
        data = {
            'analysis_date': datetime.now().isoformat(),
            'directory': self.directory if hasattr(self, 'directory') else '',
            'results': self.results,
            'complexity_results': self.complexity_results,
            'quality_issues': self.quality_issues,
            'duplicates_count': len(self.duplicates),
            'git_stats': self.git_stats,
            'timeline_data': self.timeline_data
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def export_to_excel(self, file_path):
        """导出为Excel"""
        try:
            import pandas as pd
            
            # 准备数据
            data = []
            for file_type, stats in self.results.items():
                code_ratio = stats['code'] / stats['total'] * 100 if stats['total'] > 0 else 0
                data.append({
                    '文件类型': file_type,
                    '文件数': stats['files'],
                    '总行数': stats['total'],
                    '代码行': stats['code'],
                    '注释行': stats['comments'],
                    '空行': stats['blanks'],
                    '函数数': stats['functions'],
                    '类数': stats['classes'],
                    '导入数': stats['imports'],
                    '代码比例': f"{code_ratio:.2f}%",
                    '质量分数': stats['quality_score']
                })
            
            # 创建DataFrame并保存
            df = pd.DataFrame(data)
            df.to_excel(file_path, index=False, engine='openpyxl')
            
        except ImportError:
            QMessageBox.warning(self, "警告", "导出Excel需要安装pandas和openpyxl库")
    
    def export_to_html(self, file_path):
        """导出为HTML报告"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('<!DOCTYPE html>\n<html>\n<head>\n')
                f.write('<meta charset="UTF-8">\n')
                f.write('<title>代码分析报告</title>\n')
                f.write('<style>\n')
                f.write('body { font-family: Arial, sans-serif; margin: 20px; }\n')
                f.write('h1 { color: #333; }\n')
                f.write('table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }\n')
                f.write('th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }\n')
                f.write('th { background-color: #f2f2f2; }\n')
                f.write('.good { color: green; }\n')
                f.write('.warning { color: orange; }\n')
                f.write('.bad { color: red; }\n')
                f.write('</style>\n')
                f.write('</head>\n<body>\n')
                
                f.write('<h1>代码分析报告</h1>\n')
                f.write(f'<p>生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>\n')
                f.write(f'<p>分析目录: {self.directory if hasattr(self, "directory") else "N/A"}</p>\n')
                
                # 汇总统计
                f.write('<h2>汇总统计</h2>\n')
                f.write('<table>\n')
                f.write('<tr><th>文件类型</th><th>文件数</th><th>总行数</th><th>代码行</th><th>注释行</th><th>空行</th><th>函数数</th><th>类数</th><th>导入数</th><th>代码比例</th><th>质量分数</th></tr>\n')
                
                for file_type, stats in self.results.items():
                    code_ratio = stats['code'] / stats['total'] * 100 if stats['total'] > 0 else 0
                    quality_class = "good" if stats['quality_score'] > 80 else "warning" if stats['quality_score'] > 60 else "bad"
                    
                    f.write(f'<tr><td>{file_type}</td><td>{stats["files"]}</td><td>{stats["total"]}</td><td>{stats["code"]}</td>')
                    f.write(f'<td>{stats["comments"]}</td><td>{stats["blanks"]}</td><td>{stats["functions"]}</td>')
                    f.write(f'<td>{stats["classes"]}</td><td>{stats["imports"]}</td><td>{code_ratio:.2f}%</td>')
                    f.write(f'<td class="{quality_class}">{stats["quality_score"]}/100</td></tr>\n')
                
                f.write('</table>\n')
                
                # 质量问题
                if self.quality_issues:
                    f.write('<h2>质量问题</h2>\n')
                    f.write('<table>\n')
                    f.write('<tr><th>文件</th><th>问题类型</th><th>描述</th><th>行号</th><th>严重性</th></tr>\n')
                    
                    for file_path, issues in self.quality_issues.items():
                        for issue in issues:
                            severity_class = "bad" if issue.get('severity') == 'error' else "warning"
                            f.write(f'<tr><td>{os.path.basename(file_path)}</td><td>{issue.get("type", "未知")}</td>')
                            f.write(f'<td>{issue.get("message", "")}</td><td>{issue.get("line", "")}</td>')
                            f.write(f'<td class="{severity_class}">{issue.get("severity", "未知")}</td></tr>\n')
                    
                    f.write('</table>\n')
                
                # Git统计
                if self.git_stats:
                    f.write('<h2>Git贡献统计</h2>\n')
                    f.write('<table>\n')
                    f.write('<tr><th>开发者</th><th>提交数</th><th>添加行数</th><th>删除行数</th><th>净变化</th></tr>\n')
                    
                    for developer, stats in self.git_stats.items():
                        net_change = stats['additions'] - stats['deletions']
                        net_class = "good" if net_change > 0 else "bad" if net_change < 0 else ""
                        
                        f.write(f'<tr><td>{developer}</td><td>{stats["commits"]}</td><td>{stats["additions"]}</td>')
                        f.write(f'<td>{stats["deletions"]}</td><td class="{net_class}">{net_change}</td></tr>\n')
                    
                    f.write('</table>\n')
                
                f.write('</body>\n</html>\n')
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"生成HTML报告失败: {str(e)}")
                
    def show_about(self):
        """显示关于对话框"""
        about_text = """
        <h2>高级代码量量化工具</h2>
        <p>版本: 2.0</p>
        <p>这是一个功能强大的代码分析工具，支持多种编程语言的代码统计、质量分析和可视化。</p>
        <p>功能包括:</p>
        <ul>
            <li>多语言代码统计</li>
            <li>代码质量分析</li>
            <li>重复代码检测</li>
            <li>Git历史分析</li>
            <li>实时分析</li>
            <li>可视化图表</li>
        </ul>
        <p>© 2025 代码分析工具团队</p>
        """
        
        QMessageBox.about(self, "关于", about_text)
                
    def closeEvent(self, event):
        """关闭事件"""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
            
        if self.realtime_worker and self.realtime_worker.isRunning():
            self.realtime_worker.stop()
            self.realtime_worker.wait()
            
        self.save_settings()
        event.accept()


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = CodeMetricsTool()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()