import sys
import os
import json
import ast
import inspect
import importlib
import traceback
import threading
import time
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict, Counter, deque
from typing import Dict, List, Set, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import pickle
import sqlite3
from pathlib import Path

from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                            QWidget, QTextEdit, QListWidget, QSplitter, QTabWidget,
                            QPushButton, QLabel, QMessageBox, QFileDialog, QComboBox,
                            QLineEdit, QProgressBar, QTreeWidget, QTreeWidgetItem,
                            QDialog, QDialogButtonBox, QFormLayout, QSpinBox,
                            QGroupBox, QCheckBox, QRadioButton, QSlider, QTableWidget,
                            QTableWidgetItem, QHeaderView, QToolBar, QAction, QMenu,
                            QStatusBar, QToolButton, QDockWidget, QFrame, QScrollArea,
                            QSizePolicy, QGridLayout, QSpacerItem)
from PyQt5.QtCore import QSize, Qt, QThread, pyqtSignal, QTimer, QSettings, QDateTime, QUrl
from PyQt5.QtGui import (QFont, QSyntaxHighlighter, QTextCharFormat, QColor, 
                        QKeySequence, QIcon, QPalette, QTextCursor, QDesktopServices,
                        QPainter, QLinearGradient, QBrush)
from PyQt5.Qt import QShortcut

# ==================== 高级数据结构和枚举 ====================

class EvolutionLevel(Enum):
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    ADAPTIVE = "adaptive"

class CodePatternType(Enum):
    FUNCTION_CALL = "function_call"
    CLASS_USAGE = "class_usage"
    IMPORT_PATTERN = "import_pattern"
    CONTROL_FLOW = "control_flow"
    DATA_STRUCTURE = "data_structure"
    ALGORITHM = "algorithm"

@dataclass
class CodePattern:
    pattern_type: CodePatternType
    signature: str
    frequency: int = 0
    contexts: List[str] = field(default_factory=list)
    last_used: datetime = field(default_factory=datetime.now)
    complexity: float = 0.0
    usefulness: float = 0.0

@dataclass
class UserProfile:
    skill_level: str = "intermediate"
    preferred_patterns: List[str] = field(default_factory=list)
    coding_style: Dict[str, Any] = field(default_factory=dict)
    productivity_metrics: Dict[str, float] = field(default_factory=dict)
    learning_preferences: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EvolutionState:
    level: EvolutionLevel = EvolutionLevel.BASIC
    learning_rate: float = 0.1
    adaptation_speed: float = 1.0
    memory_decay: float = 0.95
    exploration_factor: float = 0.3
    last_evolution: datetime = field(default_factory=datetime.now)

class CodeAnalyzer:
    def __init__(self):
        self.function_usage = defaultdict(int)
        self.module_dependencies = defaultdict(set)
        self.code_patterns = defaultdict(list)
        self.user_behavior = defaultdict(lambda: defaultdict(int))
        
    def analyze_code(self, code: str, filename: str = "") -> Dict[str, Any]:
        """分析代码并提取特征"""
        try:
            tree = ast.parse(code)
            analysis_result = {
                'functions': [],
                'classes': [],
                'imports': [],
                'patterns': [],
                'complexity': 0,
                'line_count': len(code.splitlines())
            }
            
            # 分析导入
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        analysis_result['imports'].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        analysis_result['imports'].append(node.module)
            
            # 分析函数和类
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    analysis_result['functions'].append(node.name)
                    # 记录函数使用模式
                    self._analyze_function_pattern(node, analysis_result)
                elif isinstance(node, ast.ClassDef):
                    analysis_result['classes'].append(node.name)
            
            # 计算复杂度（简化版）
            analysis_result['complexity'] = self._calculate_complexity(tree)
            
            return analysis_result
        except SyntaxError:
            return {'error': 'Syntax error in code'}
    
    def _analyze_function_pattern(self, node: ast.FunctionDef, analysis_result: Dict):
        """分析函数内部模式"""
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    pattern = f"function_call:{child.func.id}"
                    analysis_result['patterns'].append(pattern)
                    self.code_patterns[pattern].append({
                        'context': node.name,
                        'timestamp': datetime.now()
                    })
    
    def _calculate_complexity(self, tree: ast.AST) -> int:
        """计算代码复杂度（简化版）"""
        complexity = 0
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.Try, ast.With)):
                complexity += 1
            elif isinstance(node, ast.FunctionDef):
                complexity += 1
        return complexity
    
    def record_usage(self, function_name: str, context: str = ""):
        """记录函数使用情况"""
        self.function_usage[function_name] += 1
        if context:
            self.user_behavior[context][function_name] += 1
    
    def get_recommendations(self, current_code: str, context: str = "") -> List[str]:
        """基于使用模式获取推荐"""
        analysis = self.analyze_code(current_code)
        recommendations = []
        
        # 基于频率推荐
        if analysis.get('functions'):
            for func in analysis['functions']:
                if func in self.function_usage:
                    # 推荐相关函数
                    related = self._find_related_functions(func)
                    recommendations.extend(related)
        
        # 基于模式推荐
        for pattern in analysis.get('patterns', []):
            if pattern in self.code_patterns:
                # 推荐相似模式
                similar = self._find_similar_patterns(pattern)
                recommendations.extend(similar)
        
        # 基于上下文推荐
        if context and context in self.user_behavior:
            context_usage = self.user_behavior[context]
            common_funcs = sorted(context_usage.items(), key=lambda x: x[1], reverse=True)[:5]
            recommendations.extend([f"context:{func}" for func, _ in common_funcs])
        
        return list(set(recommendations))[:10]  # 去重并限制数量
    
    def _find_related_functions(self, function_name: str) -> List[str]:
        """查找相关函数"""
        # 简化实现：基于共同使用模式
        related = []
        for pattern, usages in self.code_patterns.items():
            if any(usage['context'] == function_name for usage in usages):
                # 提取模式中的函数名
                if pattern.startswith('function_call:'):
                    related_func = pattern.split(':')[1]
                    if related_func != function_name:
                        related.append(f"related:{related_func}")
        return related
    
    def _find_similar_patterns(self, pattern: str) -> List[str]:
        """查找相似模式"""
        # 简化实现：返回相同类型的模式
        similar = []
        base_pattern = pattern.split(':')[0] if ':' in pattern else pattern
        for p in self.code_patterns:
            if p.startswith(base_pattern) and p != pattern:
                similar.append(f"pattern:{p}")
        return similar

# 代码高亮器
class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.highlighting_rules = []
        
        # 关键字格式
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor(200, 120, 50))
        keyword_format.setFontWeight(QFont.Bold)
        keywords = [
            'and', 'as', 'assert', 'break', 'class', 'continue', 'def', 'del',
            'elif', 'else', 'except', 'False', 'finally', 'for', 'from', 'global',
            'if', 'import', 'in', 'is', 'lambda', 'None', 'nonlocal', 'not', 'or',
            'pass', 'raise', 'return', 'True', 'try', 'while', 'with', 'yield'
        ]
        for word in keywords:
            pattern = r'\b' + word + r'\b'
            self.highlighting_rules.append((pattern, keyword_format))
        
        # 字符串格式
        string_format = QTextCharFormat()
        string_format.setForeground(QColor(50, 150, 50))
        self.highlighting_rules.append((r'\".*\"', string_format))
        self.highlighting_rules.append((r'\'.*\'', string_format))
        
        # 注释格式
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor(150, 150, 150))
        self.highlighting_rules.append((r'#.*', comment_format))
    
    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)
# ==================== 高级代码分析器 ====================

class AdvancedCodeAnalyzer:
    def __init__(self):
        self.function_usage = defaultdict(int)
        self.module_dependencies = defaultdict(set)
        self.code_patterns: Dict[str, CodePattern] = {}
        self.user_behavior = defaultdict(lambda: defaultdict(int))
        self.user_profile = UserProfile()
        self.evolution_state = EvolutionState()
        self.code_similarity_cache = {}
        self.pattern_relationships = defaultdict(set)
        self.performance_metrics = defaultdict(list)
        
        # 加载预训练的模式
        self._load_preset_patterns()
        
    def _load_preset_patterns(self):
        """加载预定义的代码模式"""
        preset_patterns = {
            "list_comprehension": CodePattern(
                CodePatternType.CONTROL_FLOW, 
                "[x for x in iterable if condition]",
                complexity=2.0,
                usefulness=8.0
            ),
            "context_manager": CodePattern(
                CodePatternType.CONTROL_FLOW,
                "with open() as f:",
                complexity=1.5,
                usefulness=9.0
            ),
            "decorator_usage": CodePattern(
                CodePatternType.FUNCTION_CALL,
                "@decorator",
                complexity=3.0,
                usefulness=7.0
            ),
            "generator_expression": CodePattern(
                CodePatternType.DATA_STRUCTURE,
                "(x for x in iterable)",
                complexity=2.5,
                usefulness=8.5
            )
        }
        self.code_patterns.update(preset_patterns)
    
    def analyze_code_advanced(self, code: str, context: str = "") -> Dict[str, Any]:
        """高级代码分析"""
        basic_analysis = self.analyze_code(code)
        
        # 高级分析
        advanced_analysis = {
            **basic_analysis,
            'quality_metrics': self._calculate_quality_metrics(code),
            'pattern_matches': self._find_pattern_matches(code),
            'optimization_opportunities': self._find_optimizations(code),
            'style_suggestions': self._analyze_coding_style(code),
            'complexity_analysis': self._analyze_complexity(code),
            'security_checks': self._check_security_issues(code)
        }
        
        # 更新用户画像
        self._update_user_profile(advanced_analysis, context)
        
        return advanced_analysis
    
    def _calculate_quality_metrics(self, code: str) -> Dict[str, float]:
        """计算代码质量指标"""
        try:
            tree = ast.parse(code)
            metrics = {
                'maintainability': 0.0,
                'readability': 0.0,
                'efficiency': 0.0,
                'modularity': 0.0
            }
            
            # 计算各种指标（简化实现）
            lines = code.splitlines()
            non_empty_lines = [l for l in lines if l.strip()]
            
            # 可维护性：基于注释密度和函数长度
            comment_lines = len([l for l in lines if l.strip().startswith('#')])
            metrics['maintainability'] = min(10.0, (comment_lines / len(non_empty_lines)) * 20 if non_empty_lines else 5.0)
            
            # 可读性：基于命名规范和代码结构
            avg_line_length = np.mean([len(l) for l in non_empty_lines]) if non_empty_lines else 0
            metrics['readability'] = max(0.0, 10.0 - (avg_line_length - 40) / 10)  # 假设40字符为理想长度
            
            return metrics
        except:
            return {'maintainability': 5.0, 'readability': 5.0, 'efficiency': 5.0, 'modularity': 5.0}
    
    def _find_pattern_matches(self, code: str) -> List[Dict[str, Any]]:
        """查找代码模式匹配"""
        matches = []
        for pattern_name, pattern in self.code_patterns.items():
            if pattern.signature in code:
                matches.append({
                    'pattern': pattern_name,
                    'type': pattern.pattern_type.value,
                    'confidence': 0.8,  # 简化置信度计算
                    'suggestion': f"检测到模式: {pattern_name}"
                })
        return matches
    
    def _find_optimizations(self, code: str) -> List[str]:
        """查找优化机会"""
        optimizations = []
        
        # 简单的优化建议
        if 'for i in range(len(' in code and '[i]' in code:
            optimizations.append("考虑使用enumerate()替代range(len())")
        
        if 'import *' in code:
            optimizations.append("避免使用from module import *，建议显式导入")
        
        if 'eval(' in code or 'exec(' in code:
            optimizations.append("谨慎使用eval/exec，可能存在安全风险")
            
        return optimizations
    
    def _analyze_coding_style(self, code: str) -> Dict[str, Any]:
        """分析编码风格"""
        style_analysis = {
            'naming_conventions': {},
            'formatting_issues': [],
            'best_practices': []
        }
        
        # 检查命名规范
        if 'def ' in code:
            functions = [line for line in code.split('\n') if 'def ' in line]
            for func in functions:
                if not any(c.islower() for c in func.split('def ')[1].split('(')[0]):
                    style_analysis['naming_conventions']['function_names'] = "函数名应使用小写字母和下划线"
        
        return style_analysis
    
    def _analyze_complexity(self, code: str) -> Dict[str, Any]:
        """分析代码复杂度"""
        try:
            tree = ast.parse(code)
            complexity = {
                'cyclomatic': 0,
                'cognitive': 0,
                'nesting_depth': 0
            }
            
            # 计算圈复杂度
            complexity['cyclomatic'] = self._calculate_cyclomatic_complexity(tree)
            
            return complexity
        except:
            return {'cyclomatic': 1, 'cognitive': 1, 'nesting_depth': 1}
    
    def _calculate_cyclomatic_complexity(self, tree: ast.AST) -> int:
        """计算圈复杂度"""
        complexity = 1
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.And, ast.Or)):
                complexity += 1
            elif isinstance(node, ast.Try):
                complexity += len(node.handlers)
        return complexity
    
    def _check_security_issues(self, code: str) -> List[str]:
        """检查安全问题"""
        security_issues = []
        
        # 简单的安全检查
        security_patterns = {
            'subprocess.call': "使用subprocess.call可能存在命令注入风险",
            'pickle.loads': "反序列化数据可能存在安全风险",
            'input()': "在敏感环境中使用input()可能存在风险",
            'os.system': "使用os.system执行系统命令需谨慎"
        }
        
        for pattern, warning in security_patterns.items():
            if pattern in code:
                security_issues.append(warning)
                
        return security_issues
    
    def _update_user_profile(self, analysis: Dict[str, Any], context: str):
        """更新用户画像"""
        # 基于分析结果更新用户技能水平等
        complexity = analysis.get('complexity', 0)
        if complexity > 10:
            self.user_profile.skill_level = "advanced"
        elif complexity > 5:
            self.user_profile.skill_level = "intermediate"
        else:
            self.user_profile.skill_level = "beginner"
    
    def evolve_patterns(self):
        """模式进化"""
        current_time = datetime.now()
        time_since_evolution = (current_time - self.evolution_state.last_evolution).days
        
        if time_since_evolution >= 7:  # 每周进化一次
            self._perform_evolution()
            self.evolution_state.last_evolution = current_time
    
    def _perform_evolution(self):
        """执行进化算法"""
        # 基于使用频率和效果进化模式
        for pattern_name, pattern in self.code_patterns.items():
            # 调整模式的有用性
            usage_frequency = self.function_usage.get(pattern_name, 0)
            pattern.usefulness = pattern.usefulness * 0.9 + usage_frequency * 0.1
            
            # 如果模式很少使用，降低其优先级
            if usage_frequency < 3:
                pattern.usefulness *= 0.8
        
        # 根据进化状态调整参数
        if self.evolution_state.level == EvolutionLevel.ADAPTIVE:
            self.evolution_state.learning_rate = min(0.5, self.evolution_state.learning_rate * 1.1)
    
    def get_personalized_recommendations(self, code: str, context: str = "") -> List[Dict[str, Any]]:
        """获取个性化推荐"""
        analysis = self.analyze_code_advanced(code, context)
        base_recommendations = self.get_recommendations(code, context)
        
        personalized_recs = []
        
        for rec in base_recommendations:
            # 基于用户画像个性化推荐
            rec_dict = {
                'type': 'pattern',
                'content': rec,
                'confidence': 0.7,
                'reason': f"基于您的编码风格推荐",
                'priority': 'medium'
            }
            
            # 根据用户技能水平调整优先级
            if self.user_profile.skill_level == "beginner" and 'advanced' in rec.lower():
                rec_dict['priority'] = 'low'
            elif self.user_profile.skill_level == "advanced" and 'basic' in rec.lower():
                rec_dict['priority'] = 'low'
            else:
                rec_dict['priority'] = 'high'
            
            personalized_recs.append(rec_dict)
        
        # 添加基于分析的特殊推荐
        if analysis.get('quality_metrics', {}).get('readability', 0) < 5:
            personalized_recs.append({
                'type': 'improvement',
                'content': '提高代码可读性',
                'confidence': 0.9,
                'reason': '代码可读性较低',
                'priority': 'high'
            })
        
        return personalized_recs

    # 保留原有方法
    def analyze_code(self, code: str, filename: str = "") -> Dict[str, Any]:
        """分析代码并提取特征"""
        try:
            tree = ast.parse(code)
            analysis_result = {
                'functions': [],
                'classes': [],
                'imports': [],
                'patterns': [],
                'complexity': 0,
                'line_count': len(code.splitlines())
            }
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        analysis_result['imports'].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        analysis_result['imports'].append(node.module)
                elif isinstance(node, ast.FunctionDef):
                    analysis_result['functions'].append(node.name)
                elif isinstance(node, ast.ClassDef):
                    analysis_result['classes'].append(node.name)
            
            analysis_result['complexity'] = self._calculate_complexity(tree)
            return analysis_result
        except SyntaxError:
            return {'error': 'Syntax error in code'}
    
    def _calculate_complexity(self, tree: ast.AST) -> int:
        complexity = 0
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.Try, ast.With)):
                complexity += 1
            elif isinstance(node, ast.FunctionDef):
                complexity += 1
        return complexity
    
    def record_usage(self, function_name: str, context: str = ""):
        self.function_usage[function_name] += 1
        if context:
            self.user_behavior[context][function_name] += 1
    
    def get_recommendations(self, current_code: str, context: str = "") -> List[str]:
        analysis = self.analyze_code(current_code)
        recommendations = []
        
        if analysis.get('functions'):
            for func in analysis['functions']:
                if func in self.function_usage:
                    related = self._find_related_functions(func)
                    recommendations.extend(related)
        
        for pattern in analysis.get('patterns', []):
            if pattern in self.code_patterns:
                similar = self._find_similar_patterns(pattern)
                recommendations.extend(similar)
        
        if context and context in self.user_behavior:
            context_usage = self.user_behavior[context]
            common_funcs = sorted(context_usage.items(), key=lambda x: x[1], reverse=True)[:5]
            recommendations.extend([f"context:{func}" for func, _ in common_funcs])
        
        return list(set(recommendations))[:10]
    
    def _find_related_functions(self, function_name: str) -> List[str]:
        related = []
        for pattern, usages in self.code_patterns.items():
            if any(usage['context'] == function_name for usage in usages):
                if pattern.startswith('function_call:'):
                    related_func = pattern.split(':')[1]
                    if related_func != function_name:
                        related.append(f"related:{related_func}")
        return related
    
    def _find_similar_patterns(self, pattern: str) -> List[str]:
        similar = []
        base_pattern = pattern.split(':')[0] if ':' in pattern else pattern
        for p in self.code_patterns:
            if p.startswith(base_pattern) and p != pattern:
                similar.append(f"pattern:{p}")
        return similar

# ==================== 机器学习增强模块 ====================

class MLEnhancementModule:
    def __init__(self):
        self.pattern_classifier = self._create_pattern_classifier()
        self.recommendation_engine = self._create_recommendation_engine()
        self.performance_predictor = self._create_performance_predictor()
    
    def _create_pattern_classifier(self):
        """创建模式分类器（简化实现）"""
        return {"type": "pattern_classifier", "status": "initialized"}
    
    def _create_recommendation_engine(self):
        """创建推荐引擎（简化实现）"""
        return {"type": "recommendation_engine", "status": "initialized"}
    
    def _create_performance_predictor(self):
        """创建性能预测器（简化实现）"""
        return {"type": "performance_predictor", "status": "initialized"}
    
    def predict_code_quality(self, code_metrics: Dict[str, Any]) -> float:
        """预测代码质量"""
        # 简化实现：基于复杂度和其他指标
        complexity = code_metrics.get('complexity', 1)
        line_count = code_metrics.get('line_count', 1)
        
        # 简单的质量评分公式
        quality_score = max(0, 10 - (complexity * 0.5 + line_count * 0.01))
        return min(10.0, quality_score)
    
    def optimize_recommendations(self, recommendations: List[Dict], user_profile: UserProfile) -> List[Dict]:
        """优化推荐排序"""
        # 基于用户画像和机器学习模型优化推荐
        optimized = sorted(recommendations, 
                          key=lambda x: self._calculate_recommendation_score(x, user_profile),
                          reverse=True)
        return optimized
    
    def _calculate_recommendation_score(self, recommendation: Dict, user_profile: UserProfile) -> float:
        """计算推荐得分"""
        base_score = recommendation.get('confidence', 0.5)
        
        # 基于用户技能水平调整
        if user_profile.skill_level == "beginner" and recommendation.get('complexity', 0) > 5:
            base_score *= 0.5
        elif user_profile.skill_level == "advanced" and recommendation.get('complexity', 0) < 3:
            base_score *= 0.8
        
        return base_score

# ==================== 高级代码编辑器 ====================

class AdvancedCodeEditor(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFont(QFont("Consolas", 11))
        self.setTabStopWidth(40)
        
        # 语法高亮
        self.highlighter = PythonHighlighter(self.document())
        
        # 代码完成
        self.completion_list = []
        self.completion_prefix = ""
        self.completion_pos = 0
        
        # 智能感知
        self.smart_indent_enabled = True
        self.auto_completion_enabled = True
        
        # 代码历史
        self.code_history = deque(maxlen=100)
        self.current_history_index = -1
        
        # 设置样式
        self.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                selection-background-color: #264f78;
            }
        """)
    
    def keyPressEvent(self, event):
        # 智能缩进
        if event.key() == Qt.Key_Return and self.smart_indent_enabled:
            self.handle_smart_indent()
        # 代码完成
        elif event.key() == Qt.Key_Tab and self.auto_completion_enabled:
            self.handle_auto_completion()
        else:
            super().keyPressEvent(event)
            
            # 触发代码分析（防抖）
            QTimer.singleShot(300, self.trigger_analysis)
    
    def handle_smart_indent(self):
        """智能缩进处理"""
        cursor = self.textCursor()
        current_block = cursor.block()
        previous_text = current_block.previous().text()
        
        # 计算缩进
        indent = len(previous_text) - len(previous_text.lstrip())
        if previous_text.rstrip().endswith(':'):
            indent += 4
        
        # 插入换行和缩进
        cursor.insertText('\n' + ' ' * max(0, indent))
    
    def handle_auto_completion(self):
        """自动完成处理"""
        cursor = self.textCursor()
        cursor.select(QTextCursor.WordUnderCursor)
        self.completion_prefix = cursor.selectedText()
        
        if self.completion_prefix:
            # 显示完成列表（简化实现）
            pass
    
    def trigger_analysis(self):
        """触发代码分析"""
        current_code = self.toPlainText()
        if hasattr(self.parent(), 'trigger_analysis'):
            self.parent().trigger_analysis(current_code)
    
    def save_to_history(self):
        """保存到历史记录"""
        current_code = self.toPlainText()
        if self.code_history and self.code_history[-1] == current_code:
            return
        self.code_history.append(current_code)
        self.current_history_index = len(self.code_history) - 1
    
    def undo_code(self):
        """撤销代码更改"""
        if self.current_history_index > 0:
            self.current_history_index -= 1
            self.setPlainText(self.code_history[self.current_history_index])
    
    def redo_code(self):
        """重做代码更改"""
        if self.current_history_index < len(self.code_history) - 1:
            self.current_history_index += 1
            self.setPlainText(self.code_history[self.current_history_index])

# ==================== 高级推荐面板 ====================

class AdvancedRecommendationPanel(QWidget):
    recommendation_selected = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # 标题和过滤选项
        header_layout = QHBoxLayout()
        self.title_label = QLabel("智能推荐引擎")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 16px; color: #2c3e50;")
        header_layout.addWidget(self.title_label)
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["全部", "高优先级", "模式", "优化", "安全"])
        self.filter_combo.currentTextChanged.connect(self.filter_recommendations)
        header_layout.addWidget(QLabel("过滤:"))
        header_layout.addWidget(self.filter_combo)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # 推荐表格
        self.recommendation_table = QTableWidget()
        self.recommendation_table.setColumnCount(5)
        self.recommendation_table.setHorizontalHeaderLabels(["类型", "内容", "置信度", "优先级", "操作"])
        self.recommendation_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.recommendation_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.recommendation_table.doubleClicked.connect(self.apply_selected_recommendation)
        layout.addWidget(self.recommendation_table)
        
        # 分析结果
        self.analysis_group = QGroupBox("代码分析结果")
        analysis_layout = QVBoxLayout()
        
        self.quality_metrics_widget = QualityMetricsWidget()
        analysis_layout.addWidget(self.quality_metrics_widget)
        
        self.analysis_text = QTextEdit()
        self.analysis_text.setMaximumHeight(120)
        self.analysis_text.setReadOnly(True)
        analysis_layout.addWidget(self.analysis_text)
        
        self.analysis_group.setLayout(analysis_layout)
        layout.addWidget(self.analysis_group)
        
        self.setLayout(layout)
    
    def update_recommendations(self, recommendations: List[Dict[str, Any]]):
        """更新推荐列表"""
        self.recommendation_table.setRowCount(0)
        
        for i, rec in enumerate(recommendations):
            self.recommendation_table.insertRow(i)
            
            # 类型
            self.recommendation_table.setItem(i, 0, QTableWidgetItem(rec.get('type', 'unknown')))
            
            # 内容
            self.recommendation_table.setItem(i, 1, QTableWidgetItem(rec.get('content', '')))
            
            # 置信度
            confidence_item = QTableWidgetItem(f"{rec.get('confidence', 0):.2f}")
            confidence_item.setData(Qt.UserRole, rec.get('confidence', 0))
            self.recommendation_table.setItem(i, 2, confidence_item)
            
            # 优先级
            priority_item = QTableWidgetItem(rec.get('priority', 'medium'))
            self.recommendation_table.setItem(i, 3, priority_item)
            
            # 操作按钮
            apply_btn = QPushButton("应用")
            apply_btn.clicked.connect(lambda checked, r=rec: self.apply_recommendation(r))
            self.recommendation_table.setCellWidget(i, 4, apply_btn)
        
        # 根据优先级和置信度排序
        self.recommendation_table.sortByColumn(3, Qt.DescendingOrder)
        self.recommendation_table.sortByColumn(2, Qt.DescendingOrder)
    
    def update_analysis(self, analysis: Dict[str, Any]):
        """更新分析结果"""
        # 更新质量指标
        self.quality_metrics_widget.update_metrics(analysis.get('quality_metrics', {}))
        
        # 更新文本分析
        text = ""
        if 'error' in analysis:
            text = f"错误: {analysis['error']}"
        else:
            text = f"函数: {', '.join(analysis.get('functions', []))}\n"
            text += f"类: {', '.join(analysis.get('classes', []))}\n"
            text += f"复杂度: {analysis.get('complexity', 0)}\n"
            
            # 添加模式匹配信息
            patterns = analysis.get('pattern_matches', [])
            if patterns:
                text += f"\n检测到模式: {', '.join([p['pattern'] for p in patterns])}"
            
            # 添加优化建议
            optimizations = analysis.get('optimization_opportunities', [])
            if optimizations:
                text += f"\n优化建议: {', '.join(optimizations)}"
        
        self.analysis_text.setText(text)
    
    def filter_recommendations(self, filter_text):
        """过滤推荐"""
        # 简化实现：在实际应用中需要维护完整列表并进行过滤
        pass
    
    def apply_recommendation(self, recommendation):
        """应用推荐"""
        self.recommendation_selected.emit(recommendation)
    
    def apply_selected_recommendation(self, index):
        """应用选中的推荐"""
        row = index.row()
        if 0 <= row < self.recommendation_table.rowCount():
            content_item = self.recommendation_table.item(row, 1)
            if content_item:
                recommendation = {
                    'type': self.recommendation_table.item(row, 0).text(),
                    'content': content_item.text(),
                    'confidence': float(self.recommendation_table.item(row, 2).text()),
                    'priority': self.recommendation_table.item(row, 3).text()
                }
                self.apply_recommendation(recommendation)

# ==================== 质量指标组件 ====================

class QualityMetricsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QHBoxLayout()
        
        self.metrics = {}
        metric_names = ['可维护性', '可读性', '效率', '模块化']
        
        for name in metric_names:
            metric_frame = QFrame()
            metric_frame.setFrameStyle(QFrame.Box)
            metric_layout = QVBoxLayout()
            
            metric_label = QLabel(name)
            metric_value = QLabel("0.0")
            metric_value.setStyleSheet("font-weight: bold; font-size: 14px;")
            metric_bar = QProgressBar()
            metric_bar.setMaximum(10)
            metric_bar.setTextVisible(False)
            
            metric_layout.addWidget(metric_label)
            metric_layout.addWidget(metric_value)
            metric_layout.addWidget(metric_bar)
            metric_frame.setLayout(metric_layout)
            
            layout.addWidget(metric_frame)
            
            self.metrics[name] = {
                'value': metric_value,
                'bar': metric_bar
            }
        
        self.setLayout(layout)
    
    def update_metrics(self, metrics: Dict[str, float]):
        """更新质量指标"""
        metric_mapping = {
            'maintainability': '可维护性',
            'readability': '可读性',
            'efficiency': '效率',
            'modularity': '模块化'
        }
        
        for eng_name, chi_name in metric_mapping.items():
            value = metrics.get(eng_name, 0)
            if chi_name in self.metrics:
                self.metrics[chi_name]['value'].setText(f"{value:.1f}")
                self.metrics[chi_name]['bar'].setValue(int(value))
                
                # 设置颜色基于值
                color = "#e74c3c" if value < 4 else "#f39c12" if value < 7 else "#2ecc71"
                self.metrics[chi_name]['bar'].setStyleSheet(f"""
                    QProgressBar::chunk {{
                        background-color: {color};
                    }}
                """)

# ==================== 进化控制面板 ====================

class EvolutionControlPanel(QDockWidget):
    def __init__(self, parent=None):
        super().__init__("进化控制面板", parent)
        self.setup_ui()
    
    def setup_ui(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 进化状态显示
        self.status_group = QGroupBox("进化状态")
        status_layout = QFormLayout()
        
        self.level_label = QLabel("基础")
        self.learning_rate_label = QLabel("0.1")
        self.adaptation_label = QLabel("正常")
        
        status_layout.addRow("进化级别:", self.level_label)
        status_layout.addRow("学习速率:", self.learning_rate_label)
        status_layout.addRow("适应速度:", self.adaptation_label)
        
        self.status_group.setLayout(status_layout)
        layout.addWidget(self.status_group)
        
        # 进化控制
        self.control_group = QGroupBox("进化控制")
        control_layout = QVBoxLayout()
        
        self.evolution_slider = QSlider(Qt.Horizontal)
        self.evolution_slider.setRange(1, 4)
        self.evolution_slider.setValue(1)
        self.evolution_slider.valueChanged.connect(self.change_evolution_level)
        
        control_layout.addWidget(QLabel("进化级别:"))
        control_layout.addWidget(self.evolution_slider)
        
        self.accelerate_btn = QPushButton("加速进化")
        self.accelerate_btn.clicked.connect(self.accelerate_evolution)
        control_layout.addWidget(self.accelerate_btn)
        
        self.control_group.setLayout(control_layout)
        layout.addWidget(self.control_group)
        
        # 统计信息
        self.stats_group = QGroupBox("统计信息")
        stats_layout = QVBoxLayout()
        
        self.patterns_label = QLabel("已学习模式: 0")
        self.recommendations_label = QLabel("推荐成功率: 0%")
        self.usage_label = QLabel("使用分析: 正常")
        
        stats_layout.addWidget(self.patterns_label)
        stats_layout.addWidget(self.recommendations_label)
        stats_layout.addWidget(self.usage_label)
        
        self.stats_group.setLayout(stats_layout)
        layout.addWidget(self.stats_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        self.setWidget(widget)
    
    def change_evolution_level(self, level):
        """改变进化级别"""
        levels = {1: "基础", 2: "中级", 3: "高级", 4: "自适应"}
        self.level_label.setText(levels.get(level, "未知"))
    
    def accelerate_evolution(self):
        """加速进化"""
        QMessageBox.information(self, "进化加速", "已启动加速进化进程")
    
    def update_stats(self, analyzer: AdvancedCodeAnalyzer):
        """更新统计信息"""
        self.patterns_label.setText(f"已学习模式: {len(analyzer.code_patterns)}")
        
        # 计算推荐成功率（简化）
        total_usage = sum(analyzer.function_usage.values())
        if total_usage > 0:
            success_rate = (analyzer.function_usage.get('recommendation_applied', 0) / total_usage) * 100
            self.recommendations_label.setText(f"推荐成功率: {success_rate:.1f}%")

# ==================== 主应用程序 ====================

class SelfEvolvingAIIDE(QMainWindow):
    def __init__(self):
        super().__init__()
        self.analyzer = AdvancedCodeAnalyzer()
        self.ml_module = MLEnhancementModule()
        self.setup_ui()
        self.setup_connections()
        self.load_settings()
        
        # 启动后台进化线程
        self.evolution_timer = QTimer()
        self.evolution_timer.timeout.connect(self.run_evolution_cycle)
        self.evolution_timer.start(60000)  # 每分钟检查一次进化
    
    def setup_ui(self):
        self.setWindowTitle("功能自进化AI研发智能系统")
        self.setGeometry(100, 50, 1600, 1000)
        
        # 设置应用图标和样式
        #self.setApplicationDisplayName("AI代码助手")
        self.setStyleSheet("""
            QMainWindow {
                background-color: #ecf0f1;
            }
            QMenuBar {
                background-color: #34495e;
                color: white;
            }
            QMenuBar::item:selected {
                background-color: #3498db;
            }
        """)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        
        # 创建分割器
        main_splitter = QSplitter(Qt.Horizontal)
        
        # 左侧代码编辑区域
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_widget.setLayout(left_layout)
        
        # 代码编辑器标签页
        self.editor_tabs = QTabWidget()
        self.editor_tabs.setTabsClosable(True)
        self.editor_tabs.tabCloseRequested.connect(self.close_editor_tab)
        
        # 添加默认编辑器
        self.add_editor_tab("新建文件.py")
        
        left_layout.addWidget(self.editor_tabs)
        
        # 编辑器工具栏
        editor_toolbar = QToolBar()
        editor_toolbar.setIconSize(QSize(16, 16))
        
        new_action = QAction("新建", self)
        new_action.triggered.connect(self.new_file)
        editor_toolbar.addAction(new_action)
        
        save_action = QAction("保存", self)
        save_action.triggered.connect(self.save_file)
        editor_toolbar.addAction(save_action)
        
        left_layout.addWidget(editor_toolbar)
        
        # 右侧面板
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_widget.setLayout(right_layout)
        
        # 推荐面板
        self.recommendation_panel = AdvancedRecommendationPanel()
        right_layout.addWidget(self.recommendation_panel)
        
        # 添加到分割器
        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(right_widget)
        main_splitter.setSizes([1000, 600])
        
        main_layout.addWidget(main_splitter)
        
        # 添加进化控制面板
        self.evolution_panel = EvolutionControlPanel()
        self.addDockWidget(Qt.RightDockWidgetArea, self.evolution_panel)
        
        # 设置菜单栏
        self.setup_menu()
        
        # 状态栏
        self.statusBar().showMessage("就绪 - 功能自进化AI系统已启动")
    
    def setup_menu(self):
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        new_action = QAction("新建", self)
        new_action.setShortcut(QKeySequence.New)
        new_action.triggered.connect(self.new_file)
        file_menu.addAction(new_action)
        
        open_action = QAction("打开", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        save_action = QAction("保存", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 编辑菜单
        edit_menu = menubar.addMenu("编辑")
        
        analyze_action = QAction("分析代码", self)
        analyze_action.setShortcut(QKeySequence("Ctrl+Shift+A"))
        analyze_action.triggered.connect(self.manual_analysis)
        edit_menu.addAction(analyze_action)
        
        # 进化菜单
        evolution_menu = menubar.addMenu("进化")
        
        evolve_action = QAction("启动进化", self)
        evolve_action.triggered.connect(self.start_evolution)
        evolution_menu.addAction(evolve_action)
        
        stats_action = QAction("查看统计", self)
        stats_action.triggered.connect(self.show_statistics)
        evolution_menu.addAction(stats_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def setup_connections(self):
        # 连接推荐面板信号
        self.recommendation_panel.recommendation_selected.connect(self.apply_recommendation)
    
    def add_editor_tab(self, title: str):
        """添加编辑器标签页"""
        editor = AdvancedCodeEditor()
        tab_index = self.editor_tabs.addTab(editor, title)
        self.editor_tabs.setCurrentIndex(tab_index)
        return editor
    
    def close_editor_tab(self, index):
        """关闭编辑器标签页"""
        self.editor_tabs.removeTab(index)
    
    def get_current_editor(self) -> AdvancedCodeEditor:
        """获取当前编辑器"""
        return self.editor_tabs.currentWidget()
    
    def trigger_analysis(self, code):
        """触发代码分析"""
        # 使用线程进行异步分析
        analysis_thread = threading.Thread(target=self.perform_analysis, args=(code,))
        analysis_thread.daemon = True
        analysis_thread.start()
    
    def perform_analysis(self, code):
        """执行代码分析"""
        try:
            # 高级分析
            analysis = self.analyzer.analyze_code_advanced(code, "editor")
            
            # 获取个性化推荐
            recommendations = self.analyzer.get_personalized_recommendations(code, "editor")
            
            # 使用机器学习优化推荐
            optimized_recommendations = self.ml_module.optimize_recommendations(
                recommendations, self.analyzer.user_profile
            )
            
            # 更新UI（需要在主线程中执行）
            self.update_analysis_display(analysis, optimized_recommendations)
            
        except Exception as e:
            print(f"分析错误: {e}")
    
    def update_analysis_display(self, analysis, recommendations):
        """更新分析显示（在主线程中调用）"""
        QTimer.singleShot(0, lambda: self._update_ui(analysis, recommendations))
    
    def _update_ui(self, analysis, recommendations):
        """更新UI"""
        self.recommendation_panel.update_analysis(analysis)
        self.recommendation_panel.update_recommendations(recommendations)
        
        # 更新进化面板统计
        self.evolution_panel.update_stats(self.analyzer)
    
    def apply_recommendation(self, recommendation):
        """应用推荐"""
        editor = self.get_current_editor()
        if editor:
            current_text = editor.toPlainText()
            new_text = current_text + f"\n# 应用推荐: {recommendation['content']}\n"
            editor.setPlainText(new_text)
            
            # 记录使用
            self.analyzer.record_usage(recommendation['content'], "editor")
            
            self.statusBar().showMessage(f"已应用推荐: {recommendation['content']}")
    
    def manual_analysis(self):
        """手动分析"""
        editor = self.get_current_editor()
        if editor:
            code = editor.toPlainText()
            if code:
                self.trigger_analysis(code)
                self.statusBar().showMessage("代码分析完成")
            else:
                self.statusBar().showMessage("没有代码可分析")
    
    def start_evolution(self):
        """启动进化过程"""
        self.analyzer.evolve_patterns()
        self.statusBar().showMessage("进化过程已启动")
    
    def run_evolution_cycle(self):
        """运行进化周期"""
        # 检查是否需要进化
        self.analyzer.evolve_patterns()
    
    def show_statistics(self):
        """显示统计信息"""
        stats_dialog = QDialog(self)
        stats_dialog.setWindowTitle("系统统计")
        stats_dialog.resize(400, 300)
        
        layout = QVBoxLayout()
        
        # 显示各种统计信息
        stats_text = QTextEdit()
        stats_text.setReadOnly(True)
        
        stats_info = f"""
        系统统计信息:
        - 已学习模式: {len(self.analyzer.code_patterns)}
        - 用户技能水平: {self.analyzer.user_profile.skill_level}
        - 总代码分析次数: {sum(len(v) for v in self.analyzer.user_behavior.values())}
        - 进化级别: {self.analyzer.evolution_state.level.value}
        - 学习速率: {self.analyzer.evolution_state.learning_rate}
        """
        
        stats_text.setText(stats_info)
        layout.addWidget(stats_text)
        
        stats_dialog.setLayout(layout)
        stats_dialog.exec_()
    
    def new_file(self):
        """新建文件"""
        self.add_editor_tab("新建文件.py")
        self.statusBar().showMessage("已创建新文件")
    
    def open_file(self):
        """打开文件"""
        filename, _ = QFileDialog.getOpenFileName(self, "打开文件", "", "Python文件 (*.py);;所有文件 (*)")
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                editor = self.add_editor_tab(os.path.basename(filename))
                editor.setPlainText(content)
                self.statusBar().showMessage(f"已打开: {filename}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法打开文件: {str(e)}")
    
    def save_file(self):
        """保存文件"""
        editor = self.get_current_editor()
        if editor:
            filename, _ = QFileDialog.getSaveFileName(self, "保存文件", "", "Python文件 (*.py);;所有文件 (*)")
            if filename:
                try:
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(editor.toPlainText())
                    self.statusBar().showMessage(f"已保存: {filename}")
                except Exception as e:
                    QMessageBox.critical(self, "错误", f"无法保存文件: {str(e)}")
    
    def load_settings(self):
        """加载设置"""
        self.settings = QSettings("SelfEvolvingAI", "IDE")
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
    
    def closeEvent(self, event):
        """关闭事件"""
        # 保存设置
        self.settings.setValue("geometry", self.saveGeometry())
        
        # 确认退出
        reply = QMessageBox.question(self, "确认退出", 
                                   "确定要退出功能自进化AI系统吗？",
                                   QMessageBox.Yes | QMessageBox.No,
                                   QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()
    
    def show_about(self):
        """显示关于信息"""
        about_text = """
        <h2>功能自进化AI研发智能系统</h2>
        <p>版本 2.0</p>
        <p>这是一个基于人工智能的代码开发环境，具有以下特性：</p>
        <ul>
            <li>智能代码分析与推荐</li>
            <li>个性化学习与适应</li>
            <li>自进化代码模式识别</li>
            <li>高级质量指标评估</li>
            <li>机器学习优化</li>
        </ul>
        <p>© 2023 自进化AI实验室</p>
        """
        
        QMessageBox.about(self, "关于", about_text)

# ==================== 应用程序启动 ====================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用程序属性
    app.setApplicationName("SelfEvolvingAI-IDE")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("SelfEvolvingAI-Lab")
    
    # 设置样式
    app.setStyle("Fusion")
    
    # 创建并显示主窗口
    ide = SelfEvolvingAIIDE()
    ide.show()
    
    sys.exit(app.exec_())