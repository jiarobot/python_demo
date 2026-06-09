import sys
import os
import json
import re
from datetime import datetime
from collections import Counter
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTextEdit, QPushButton, QLabel, 
                             QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
                             QTabWidget, QGroupBox, QFileDialog, QMessageBox,
                             QProgressBar, QSplitter, QListWidget, QListWidgetItem,
                             QTreeWidget, QTreeWidgetItem, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QToolBar, QAction,
                             QStatusBar, QMenuBar, QMenu, QDialog, QLineEdit,
                             QFormLayout, QDialogButtonBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QTextCursor, QSyntaxHighlighter, QTextCharFormat, QColor, QIcon, QPalette
import jieba
import jieba.posseg as pseg
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import numpy as np
from PIL import Image

class TextAnalyzer(QThread):
    """文本分析线程"""
    analysis_complete = pyqtSignal(dict)
    
    def __init__(self, text):
        super().__init__()
        self.text = text
    
    def run(self):
        # 分词和词性标注
        words = pseg.cut(self.text)
        word_list = []
        pos_list = []
        
        for word, pos in words:
            if len(word.strip()) > 0:
                word_list.append(word)
                pos_list.append(pos)
        
        # 词频统计
        word_freq = Counter(word_list)
        pos_freq = Counter(pos_list)
        
        # 文本统计
        char_count = len(self.text)
        word_count = len(word_list)
        sentence_count = len(re.split(r'[。！？!?]', self.text))
        paragraph_count = len(self.text.split('\n'))
        
        # 分析结果
        result = {
            'word_freq': dict(word_freq.most_common(50)),
            'pos_freq': dict(pos_freq),
            'stats': {
                'char_count': char_count,
                'word_count': word_count,
                'sentence_count': sentence_count,
                'paragraph_count': paragraph_count
            },
            'words': word_list,
            'pos_tags': pos_list
        }
        
        self.analysis_complete.emit(result)

class SyntaxHighlighter(QSyntaxHighlighter):
    """语法高亮器"""
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 定义高亮规则
        self.highlighting_rules = []
        
        # 关键字格式
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor(200, 0, 0))
        keyword_format.setFontWeight(QFont.Bold)
        
        keywords = ["如果", "否则", "循环", "函数", "返回", "导入", "类", "定义"]
        for word in keywords:
            pattern = r'\b' + word + r'\b'
            self.highlighting_rules.append((pattern, keyword_format))
        
        # 字符串格式
        string_format = QTextCharFormat()
        string_format.setForeground(QColor(0, 150, 0))
        self.highlighting_rules.append((r'\".*?\"', string_format))
        self.highlighting_rules.append((r'\'.*?\'', string_format))
        
        # 注释格式
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor(150, 150, 150))
        self.highlighting_rules.append((r'#.*', comment_format))
    
    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            expression = re.compile(pattern)
            for match in expression.finditer(text):
                start, end = match.span()
                self.setFormat(start, end - start, format)

class WordCloudCanvas(FigureCanvas):
    """词云画布"""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig, self.ax = plt.subplots(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        
        self.ax.set_facecolor('white')
        self.fig.patch.set_facecolor('white')
    
    def generate_wordcloud(self, word_freq, max_words=100):
        self.ax.clear()
        
        # 生成词云
        if word_freq:
            wordcloud = WordCloud(
                font_path='simhei.ttf',
                background_color='white',
                max_words=max_words,
                width=800,
                height=600
            ).generate_from_frequencies(word_freq)
            
            self.ax.imshow(wordcloud, interpolation='bilinear')
            self.ax.axis('off')
            self.fig.tight_layout()
            self.draw()

class AdvancedTextEditor(QTextEdit):
    """高级文本编辑器"""
    def __init__(self):
        super().__init__()
        self.setFont(QFont("宋体", 12))
        self.syntax_highlighter = SyntaxHighlighter(self.document())
        
        # 设置自动换行
        self.setLineWrapMode(QTextEdit.WidgetWidth)
        self.setWordWrapMode(True)
    
    def keyPressEvent(self, event):
        # 自动缩进功能
        if event.key() == Qt.Key_Return:
            cursor = self.textCursor()
            current_block = cursor.block()
            current_text = current_block.text()
            
            # 查找前导空格
            leading_spaces = len(current_text) - len(current_text.lstrip())
            
            super().keyPressEvent(event)
            
            # 插入相同数量的空格
            if leading_spaces > 0:
                cursor.insertText(' ' * leading_spaces)
        else:
            super().keyPressEvent(event)

class StatsPanel(QWidget):
    """统计面板"""
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 统计信息组
        stats_group = QGroupBox("文本统计")
        stats_layout = QFormLayout()
        
        self.char_count_label = QLabel("0")
        self.word_count_label = QLabel("0")
        self.sentence_count_label = QLabel("0")
        self.paragraph_count_label = QLabel("0")
        
        stats_layout.addRow("字符数:", self.char_count_label)
        stats_layout.addRow("词数:", self.word_count_label)
        stats_layout.addRow("句子数:", self.sentence_count_label)
        stats_layout.addRow("段落数:", self.paragraph_count_label)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # 词频表格
        self.word_freq_table = QTableWidget()
        self.word_freq_table.setColumnCount(2)
        self.word_freq_table.setHorizontalHeaderLabels(["词语", "频率"])
        self.word_freq_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(QLabel("高频词语"))
        layout.addWidget(self.word_freq_table)
        
        self.setLayout(layout)
    
    def update_stats(self, stats, word_freq):
        # 更新统计信息
        self.char_count_label.setText(str(stats['char_count']))
        self.word_count_label.setText(str(stats['word_count']))
        self.sentence_count_label.setText(str(stats['sentence_count']))
        self.paragraph_count_label.setText(str(stats['paragraph_count']))
        
        # 更新词频表格
        self.word_freq_table.setRowCount(min(20, len(word_freq)))
        for i, (word, freq) in enumerate(word_freq.items()):
            if i >= 20:
                break
            self.word_freq_table.setItem(i, 0, QTableWidgetItem(word))
            self.word_freq_table.setItem(i, 1, QTableWidgetItem(str(freq)))

class FormatDialog(QDialog):
    """格式设置对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("文本格式化")
        self.init_ui()
    
    def init_ui(self):
        layout = QFormLayout()
        
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 72)
        self.font_size_spin.setValue(12)
        
        self.line_spacing_spin = QDoubleSpinBox()
        self.line_spacing_spin.setRange(1.0, 3.0)
        self.line_spacing_spin.setValue(1.2)
        self.line_spacing_spin.setSingleStep(0.1)
        
        self.justify_check = QCheckBox("两端对齐")
        
        self.indent_spin = QSpinBox()
        self.indent_spin.setRange(0, 10)
        self.indent_spin.setValue(2)
        self.indent_spin.setSuffix(" 字符")
        
        layout.addRow("字体大小:", self.font_size_spin)
        layout.addRow("行间距:", self.line_spacing_spin)
        layout.addRow("", self.justify_check)
        layout.addRow("段落缩进:", self.indent_spin)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        
        layout.addRow(buttons)
        self.setLayout(layout)
    
    def get_settings(self):
        return {
            'font_size': self.font_size_spin.value(),
            'line_spacing': self.line_spacing_spin.value(),
            'justify': self.justify_check.isChecked(),
            'indent': self.indent_spin.value()
        }

class SmartCangjieSystem(QMainWindow):
    """智能仓颉系统主窗口"""
    def __init__(self):
        super().__init__()
        self.current_file = None
        self.analysis_result = None
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("智能仓颉系统 - 高级文本工具")
        self.setGeometry(100, 100, 1400, 900)
        
        # 创建菜单栏
        self.create_menubar()
        
        # 创建工具栏
        self.create_toolbar()
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        
        # 分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # 左侧编辑区域
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_widget.setLayout(left_layout)
        
        # 文本编辑器
        self.text_editor = AdvancedTextEditor()
        left_layout.addWidget(QLabel("文本编辑器"))
        left_layout.addWidget(self.text_editor)
        
        # 右侧分析区域
        right_widget = QTabWidget()
        
        # 统计面板
        self.stats_panel = StatsPanel()
        right_widget.addTab(self.stats_panel, "统计分析")
        
        # 词云面板
        wordcloud_widget = QWidget()
        wordcloud_layout = QVBoxLayout()
        wordcloud_widget.setLayout(wordcloud_layout)
        
        self.word_count_spin = QSpinBox()
        self.word_count_spin.setRange(10, 200)
        self.word_count_spin.setValue(100)
        self.word_count_spin.valueChanged.connect(self.update_wordcloud)
        
        controls_layout = QHBoxLayout()
        controls_layout.addWidget(QLabel("最大词语数:"))
        controls_layout.addWidget(self.word_count_spin)
        controls_layout.addStretch()
        
        self.generate_wc_btn = QPushButton("生成词云")
        self.generate_wc_btn.clicked.connect(self.generate_wordcloud)
        controls_layout.addWidget(self.generate_wc_btn)
        
        wordcloud_layout.addLayout(controls_layout)
        
        self.wordcloud_canvas = WordCloudCanvas(wordcloud_widget, width=5, height=4, dpi=100)
        wordcloud_layout.addWidget(self.wordcloud_canvas)
        
        right_widget.addTab(wordcloud_widget, "词云分析")
        
        # 添加到分割器
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([700, 700])
        
        # 显示窗口
        self.show()
    
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
        
        save_as_action = QAction('另存为', self)
        save_as_action.setShortcut('Ctrl+Shift+S')
        save_as_action.triggered.connect(self.save_as_file)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        export_action = QAction('导出分析结果', self)
        export_action.triggered.connect(self.export_analysis)
        file_menu.addAction(export_action)
        
        # 编辑菜单
        edit_menu = menubar.addMenu('编辑')
        
        format_action = QAction('格式化文本', self)
        format_action.setShortcut('Ctrl+T')
        format_action.triggered.connect(self.format_text)
        edit_menu.addAction(format_action)
        
        analyze_action = QAction('分析文本', self)
        analyze_action.setShortcut('Ctrl+A')
        analyze_action.triggered.connect(self.analyze_text)
        edit_menu.addAction(analyze_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu('工具')
        
        word_count_action = QAction('字数统计', self)
        word_count_action.triggered.connect(self.show_word_count)
        tools_menu.addAction(word_count_action)
        
        readability_action = QAction('可读性分析', self)
        readability_action.triggered.connect(self.analyze_readability)
        tools_menu.addAction(readability_action)
    
    def create_toolbar(self):
        toolbar = QToolBar("主工具栏")
        self.addToolBar(toolbar)
        
        new_icon = QAction("新建", self)
        new_icon.triggered.connect(self.new_file)
        toolbar.addAction(new_icon)
        
        open_icon = QAction("打开", self)
        open_icon.triggered.connect(self.open_file)
        toolbar.addAction(open_icon)
        
        save_icon = QAction("保存", self)
        save_icon.triggered.connect(self.save_file)
        toolbar.addAction(save_icon)
        
        toolbar.addSeparator()
        
        analyze_icon = QAction("分析", self)
        analyze_icon.triggered.connect(self.analyze_text)
        toolbar.addAction(analyze_icon)
        
        format_icon = QAction("格式化", self)
        format_icon.triggered.connect(self.format_text)
        toolbar.addAction(format_icon)
    
    def new_file(self):
        self.text_editor.clear()
        self.current_file = None
        self.status_bar.showMessage("新建文档")
    
    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开文件", "", "文本文件 (*.txt);;所有文件 (*)")
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    self.text_editor.setPlainText(content)
                    self.current_file = file_path
                    self.status_bar.showMessage(f"已打开: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法打开文件: {str(e)}")
    
    def save_file(self):
        if self.current_file:
            try:
                with open(self.current_file, 'w', encoding='utf-8') as file:
                    file.write(self.text_editor.toPlainText())
                    self.status_bar.showMessage(f"已保存: {self.current_file}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法保存文件: {str(e)}")
        else:
            self.save_as_file()
    
    def save_as_file(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存文件", "", "文本文件 (*.txt);;所有文件 (*)")
        
        if file_path:
            self.current_file = file_path
            self.save_file()
    
    def analyze_text(self):
        text = self.text_editor.toPlainText()
        if not text.strip():
            QMessageBox.warning(self, "警告", "请输入文本进行分析")
            return
        
        self.status_bar.showMessage("正在分析文本...")
        
        # 创建分析线程
        self.analyzer = TextAnalyzer(text)
        self.analyzer.analysis_complete.connect(self.on_analysis_complete)
        self.analyzer.start()
    
    def on_analysis_complete(self, result):
        self.analysis_result = result
        self.stats_panel.update_stats(result['stats'], result['word_freq'])
        self.status_bar.showMessage("文本分析完成")
    
    def generate_wordcloud(self):
        if not self.analysis_result:
            QMessageBox.warning(self, "警告", "请先分析文本")
            return
        
        max_words = self.word_count_spin.value()
        self.wordcloud_canvas.generate_wordcloud(
            self.analysis_result['word_freq'], max_words)
    
    def update_wordcloud(self):
        if self.analysis_result:
            self.generate_wordcloud()
    
    def format_text(self):
        dialog = FormatDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            settings = dialog.get_settings()
            
            # 应用格式设置
            cursor = self.text_editor.textCursor()
            if not cursor.hasSelection():
                cursor.select(QTextCursor.Document)
            
            # 设置字体大小
            format = QTextCharFormat()
            format.setFontPointSize(settings['font_size'])
            cursor.mergeCharFormat(format)
            
            # 设置段落格式（简化实现）
            self.status_bar.showMessage("文本格式已应用")
    
    def export_analysis(self):
        if not self.analysis_result:
            QMessageBox.warning(self, "警告", "请先分析文本")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出分析结果", "", "JSON文件 (*.json);;所有文件 (*)")
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as file:
                    json.dump(self.analysis_result, file, ensure_ascii=False, indent=2)
                self.status_bar.showMessage(f"分析结果已导出: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")
    
    def show_word_count(self):
        text = self.text_editor.toPlainText()
        char_count = len(text)
        word_count = len(jieba.lcut(text))
        
        QMessageBox.information(
            self, "字数统计", 
            f"字符数: {char_count}\n词数: {word_count}")
    
    def analyze_readability(self):
        text = self.text_editor.toPlainText()
        if not text.strip():
            QMessageBox.warning(self, "警告", "请输入文本进行分析")
            return
        
        # 简化的可读性分析
        sentences = re.split(r'[。！？!?]', text)
        words = jieba.lcut(text)
        
        avg_sentence_length = len(words) / len(sentences) if sentences else 0
        avg_word_length = sum(len(word) for word in words) / len(words) if words else 0
        
        # 计算简单的可读性分数
        readability_score = max(0, 100 - avg_sentence_length - avg_word_length * 2)
        
        QMessageBox.information(
            self, "可读性分析",
            f"平均句子长度: {avg_sentence_length:.2f} 词\n"
            f"平均词长: {avg_word_length:.2f} 字\n"
            f"可读性分数: {readability_score:.2f}/100\n\n"
            f"解读:\n"
            f"- 分数越高，可读性越好\n"
            f"- 建议保持句子简洁，避免过长的词汇")

def main():
    # 初始化jieba分词
    jieba.initialize()
    
    # 创建应用
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle('Fusion')
    
    # 创建主窗口
    window = SmartCangjieSystem()
    
    # 运行应用
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()