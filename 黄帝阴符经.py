import sys
import random
import sqlite3
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTextEdit, QLineEdit, QPushButton, 
                             QLabel, QListWidget, QSplitter, QTabWidget,
                             QMessageBox, QProgressBar, QComboBox, QCheckBox,
                             QGroupBox, QFormLayout, QSpinBox, QFontComboBox,
                             QColorDialog, QAction, QMenu, QToolBar, QStatusBar)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QTextCursor, QPalette, QColor, QIcon, QTextCharFormat
import json
import os

# 黄帝阴符经经文数据
YIN_FU_JING_DATA = {
    "上篇": {
        "title": "上篇 - 神仙抱一演道章",
        "content": """
观天之道，执天之行，尽矣。故天有五贼，见之者昌。
五贼在心，施行于天。宇宙在乎手，万化生乎身。
天性，人也；人心，机也。立天之道，以定人也。
天发杀机，移星易宿；地发杀机，龙蛇起陆；人发杀机，天地反覆；天人合发，万化定基。
性有巧拙，可以伏藏。九窍之邪，在乎三要，可以动静。
火生于木，祸发必克；奸生于国，时动必溃。知之修炼，谓之圣人。
"""
    },
    "中篇": {
        "title": "中篇 - 富国安民演法章",
        "content": """
天生天杀，道之理也。天地，万物之盗；万物，人之盗；人，万物之盗。三盗既宜，三才既安。
故曰：食其时，百骸理；动其机，万化安。人知其神之神，不知不神之所以神也。
日月有数，大小有定，圣功生焉，神明出焉。其盗机也，天下莫能见，莫能知。君子得之固躬，小人得之轻命。
"""
    },
    "下篇": {
        "title": "下篇 - 强兵战胜演术章",
        "content": """
瞽者善听，聋者善视。绝利一源，用师十倍。三返昼夜，用师万倍。
心生于物，死于物，机在目。天之无恩而大恩生。迅雷烈风，莫不蠢然。
至乐性余，至静性廉。天之至私，用之至公。禽之制在气。
生者死之根，死者生之根。恩生于害，害生于恩。
愚人以天地文理圣，我以时物文理哲。人以愚虞圣，我以不愚虞圣；人以奇期圣，我以不奇期圣。
故曰：沉水入火，自取灭亡。自然之道静，故天地万物生。天地之道浸，故阴阳胜。阴阳相推，而变化顺矣。
是故圣人知自然之道不可违，因而制之至静之道，律历所不能契。
爰有奇器，是生万象，八卦甲子，神机鬼藏。阴阳相胜之术，昭昭乎进于象矣。
"""
    }
}

# 注释数据
ANNOTATIONS = {
    "观天之道": "观察天道的运行规律，理解宇宙的自然法则。",
    "执天之行": "把握天道的运行，顺应自然的变化。",
    "五贼": "指五行相克的关系，金木水火土相互制约。",
    "宇宙在乎手": "掌握了宇宙的规律，就如同掌握在自己手中。",
    "万化生乎身": "万物的变化都源于自身的修行和体悟。",
    "天发杀机": "自然界的变化和灾难，如星辰移动、气候变化。",
    "地发杀机": "大地的变动，如地震、洪水等自然灾害。",
    "人发杀机": "人类的行为对自然的影响，可能导致天地失衡。",
    "天人合发": "人与自然和谐共处，达到平衡状态。",
    "知之修炼": "通过学习和修炼，达到圣人的境界。"
}

class YinFuJingDatabase:
    """黄帝阴符经数据库管理类"""
    
    def __init__(self, db_path="yinfujing.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建阅读记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reading_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chapter TEXT NOT NULL,
                read_time TEXT NOT NULL,
                duration INTEGER DEFAULT 0
            )
        ''')
        
        # 创建书签表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chapter TEXT NOT NULL,
                position INTEGER DEFAULT 0,
                note TEXT,
                created_time TEXT NOT NULL
            )
        ''')
        
        # 创建笔记表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chapter TEXT NOT NULL,
                content TEXT NOT NULL,
                created_time TEXT NOT NULL,
                updated_time TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_reading_record(self, chapter, duration=0):
        """添加阅读记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO reading_history (chapter, read_time, duration) VALUES (?, ?, ?)",
            (chapter, datetime.now().isoformat(), duration)
        )
        conn.commit()
        conn.close()
    
    def get_reading_history(self, limit=10):
        """获取阅读历史"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT chapter, read_time, duration FROM reading_history ORDER BY read_time DESC LIMIT ?",
            (limit,)
        )
        records = cursor.fetchall()
        conn.close()
        return records
    
    def add_bookmark(self, chapter, position, note=""):
        """添加书签"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO bookmarks (chapter, position, note, created_time) VALUES (?, ?, ?, ?)",
            (chapter, position, note, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
    
    def get_bookmarks(self):
        """获取所有书签"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT chapter, position, note, created_time FROM bookmarks ORDER BY created_time DESC")
        bookmarks = cursor.fetchall()
        conn.close()
        return bookmarks
    
    def delete_bookmark(self, bookmark_id):
        """删除书签"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM bookmarks WHERE id = ?", (bookmark_id,))
        conn.commit()
        conn.close()

class AnnotationHighlighter:
    """注释高亮器"""
    
    def __init__(self, text_edit):
        self.text_edit = text_edit
        self.highlight_format = QTextCharFormat()
        self.highlight_format.setBackground(QColor(255, 255, 0))  # 黄色背景
        self.highlight_format.setForeground(QColor(0, 0, 0))  # 黑色文字
    
    def highlight_keyword(self, keyword):
        """高亮关键字"""
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.Start)
        
        # 清除之前的高亮
        self.clear_highlights()
        
        # 查找并高亮所有匹配的关键字
        while True:
            cursor = self.text_edit.document().find(keyword, cursor)
            if cursor.isNull():
                break
            
            # 保存当前光标位置
            saved_position = cursor.position()
            
            # 应用高亮格式
            cursor.mergeCharFormat(self.highlight_format)
            
            # 恢复光标位置
            cursor.setPosition(saved_position)
    
    def clear_highlights(self):
        """清除所有高亮"""
        cursor = self.text_edit.textCursor()
        cursor.select(QTextCursor.Document)
        default_format = QTextCharFormat()
        cursor.setCharFormat(default_format)
        cursor.clearSelection()

class YinFuJingReader(QMainWindow):
    """黄帝阴符经阅读器主窗口"""
    
    def __init__(self):
        super().__init__()
        self.db = YinFuJingDatabase()
        self.current_chapter = "上篇"
        self.reading_timer = QTimer()
        self.reading_time = 0
        self.init_ui()
        self.init_connections()
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("黄帝阴符经系统工具库")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 创建左侧面板
        left_panel = self.create_left_panel()
        
        # 创建右侧面板
        right_panel = self.create_right_panel()
        
        # 使用分割器
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 900])
        
        main_layout.addWidget(splitter)
        
        # 创建菜单栏
        self.create_menubar()
        
        # 创建工具栏
        self.create_toolbar()
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")
        
        # 显示初始内容
        self.display_chapter(self.current_chapter)
    
    def create_left_panel(self):
        """创建左侧面板"""
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # 章节选择
        chapter_group = QGroupBox("章节选择")
        chapter_layout = QVBoxLayout(chapter_group)
        
        self.chapter_list = QListWidget()
        self.chapter_list.addItems(["上篇", "中篇", "下篇"])
        self.chapter_list.currentItemChanged.connect(self.on_chapter_changed)
        chapter_layout.addWidget(self.chapter_list)
        
        # 搜索框
        search_group = QGroupBox("搜索")
        search_layout = QVBoxLayout(search_group)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入关键字搜索...")
        search_layout.addWidget(self.search_input)
        
        search_btn = QPushButton("搜索")
        search_btn.clicked.connect(self.on_search)
        search_layout.addWidget(search_btn)
        
        # 书签列表
        bookmark_group = QGroupBox("书签")
        bookmark_layout = QVBoxLayout(bookmark_group)
        
        self.bookmark_list = QListWidget()
        self.refresh_bookmarks()
        bookmark_layout.addWidget(self.bookmark_list)
        
        add_bookmark_btn = QPushButton("添加书签")
        add_bookmark_btn.clicked.connect(self.on_add_bookmark)
        bookmark_layout.addWidget(add_bookmark_btn)
        
        # 添加到左侧布局
        left_layout.addWidget(chapter_group)
        left_layout.addWidget(search_group)
        left_layout.addWidget(bookmark_group)
        
        return left_widget
    
    def create_right_panel(self):
        """创建右侧面板"""
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 创建选项卡
        self.tab_widget = QTabWidget()
        
        # 经文阅读选项卡
        self.reading_tab = QWidget()
        reading_layout = QVBoxLayout(self.reading_tab)
        
        # 经文标题
        self.title_label = QLabel()
        self.title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        reading_layout.addWidget(self.title_label)
        
        # 经文内容
        self.content_text = QTextEdit()
        self.content_text.setReadOnly(True)
        content_font = QFont()
        content_font.setPointSize(12)
        self.content_text.setFont(content_font)
        reading_layout.addWidget(self.content_text)
        
        # 高亮器
        self.highlighter = AnnotationHighlighter(self.content_text)
        
        # 控制按钮
        control_layout = QHBoxLayout()
        
        self.prev_btn = QPushButton("上一篇")
        self.prev_btn.clicked.connect(self.on_prev_chapter)
        control_layout.addWidget(self.prev_btn)
        
        self.random_btn = QPushButton("随机阅读")
        self.random_btn.clicked.connect(self.on_random_chapter)
        control_layout.addWidget(self.random_btn)
        
        self.next_btn = QPushButton("下一篇")
        self.next_btn.clicked.connect(self.on_next_chapter)
        control_layout.addWidget(self.next_btn)
        
        reading_layout.addLayout(control_layout)
        
        # 注释选项卡
        self.annotation_tab = QWidget()
        annotation_layout = QVBoxLayout(self.annotation_tab)
        
        self.annotation_text = QTextEdit()
        self.annotation_text.setReadOnly(True)
        annotation_layout.addWidget(self.annotation_text)
        
        # 笔记选项卡
        self.note_tab = QWidget()
        note_layout = QVBoxLayout(self.note_tab)
        
        self.note_text = QTextEdit()
        self.note_text.setPlaceholderText("在此处添加您的笔记...")
        note_layout.addWidget(self.note_text)
        
        note_btn_layout = QHBoxLayout()
        save_note_btn = QPushButton("保存笔记")
        save_note_btn.clicked.connect(self.on_save_note)
        note_btn_layout.addWidget(save_note_btn)
        
        note_btn_layout.addStretch()
        note_layout.addLayout(note_btn_layout)
        
        # 设置选项卡
        self.settings_tab = QWidget()
        settings_layout = QVBoxLayout(self.settings_tab)
        
        # 字体设置
        font_group = QGroupBox("字体设置")
        font_layout = QFormLayout(font_group)
        
        self.font_combo = QFontComboBox()
        self.font_combo.currentFontChanged.connect(self.on_font_changed)
        font_layout.addRow("选择字体:", self.font_combo)
        
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 24)
        self.font_size.setValue(12)
        self.font_size.valueChanged.connect(self.on_font_size_changed)
        font_layout.addRow("字体大小:", self.font_size)
        
        settings_layout.addWidget(font_group)
        
        # 主题设置
        theme_group = QGroupBox("主题设置")
        theme_layout = QVBoxLayout(theme_group)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["默认", "暗色", "护眼"])
        self.theme_combo.currentTextChanged.connect(self.on_theme_changed)
        theme_layout.addWidget(self.theme_combo)
        
        settings_layout.addWidget(theme_group)
        
        # 阅读统计
        stats_group = QGroupBox("阅读统计")
        stats_layout = QVBoxLayout(stats_group)
        
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        stats_layout.addWidget(self.stats_text)
        
        refresh_stats_btn = QPushButton("刷新统计")
        refresh_stats_btn.clicked.connect(self.refresh_stats)
        stats_layout.addWidget(refresh_stats_btn)
        
        settings_layout.addWidget(stats_group)
        
        settings_layout.addStretch()
        
        # 添加选项卡
        self.tab_widget.addTab(self.reading_tab, "经文阅读")
        self.tab_widget.addTab(self.annotation_tab, "注释解析")
        self.tab_widget.addTab(self.note_tab, "个人笔记")
        self.tab_widget.addTab(self.settings_tab, "设置")
        
        right_layout.addWidget(self.tab_widget)
        
        return right_widget
    
    def create_menubar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        export_action = QAction("导出经文", self)
        export_action.triggered.connect(self.on_export)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 视图菜单
        view_menu = menubar.addMenu("视图")
        
        fullscreen_action = QAction("全屏", self)
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        view_menu.addAction(fullscreen_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar("主工具栏")
        self.addToolBar(toolbar)
        
        # 添加工具栏按钮
        prev_action = QAction("上一篇", self)
        prev_action.triggered.connect(self.on_prev_chapter)
        toolbar.addAction(prev_action)
        
        next_action = QAction("下一篇", self)
        next_action.triggered.connect(self.on_next_chapter)
        toolbar.addAction(next_action)
        
        toolbar.addSeparator()
        
        random_action = QAction("随机阅读", self)
        random_action.triggered.connect(self.on_random_chapter)
        toolbar.addAction(random_action)
        
        toolbar.addSeparator()
        
        bookmark_action = QAction("添加书签", self)
        bookmark_action.triggered.connect(self.on_add_bookmark)
        toolbar.addAction(bookmark_action)
    
    def init_connections(self):
        """初始化信号连接"""
        # 阅读计时器
        self.reading_timer.timeout.connect(self.update_reading_time)
        self.reading_timer.start(1000)  # 每秒更新一次
    
    def update_reading_time(self):
        """更新阅读时间"""
        self.reading_time += 1
        self.status_bar.showMessage(f"正在阅读: {self.current_chapter} - 阅读时间: {self.reading_time}秒")
    
    def display_chapter(self, chapter):
        """显示指定章节"""
        if chapter in YIN_FU_JING_DATA:
            self.current_chapter = chapter
            data = YIN_FU_JING_DATA[chapter]
            
            # 更新标题和内容
            self.title_label.setText(data["title"])
            self.content_text.setText(data["content"])
            
            # 更新注释
            self.update_annotations()
            
            # 重置阅读时间
            self.reading_time = 0
            
            # 更新状态栏
            self.status_bar.showMessage(f"正在阅读: {chapter}")
            
            # 记录阅读历史
            self.db.add_reading_record(chapter)
    
    def update_annotations(self):
        """更新注释内容"""
        annotations_text = ""
        for keyword, annotation in ANNOTATIONS.items():
            if keyword in YIN_FU_JING_DATA[self.current_chapter]["content"]:
                annotations_text += f"<b>{keyword}:</b> {annotation}<br><br>"
        
        if not annotations_text:
            annotations_text = "当前章节没有相关注释。"
        
        self.annotation_text.setText(annotations_text)
    
    def on_chapter_changed(self, current, previous):
        """章节选择改变"""
        if current:
            self.display_chapter(current.text())
    
    def on_prev_chapter(self):
        """上一篇"""
        chapters = list(YIN_FU_JING_DATA.keys())
        current_index = chapters.index(self.current_chapter)
        if current_index > 0:
            self.display_chapter(chapters[current_index - 1])
            self.chapter_list.setCurrentRow(current_index - 1)
    
    def on_next_chapter(self):
        """下一篇"""
        chapters = list(YIN_FU_JING_DATA.keys())
        current_index = chapters.index(self.current_chapter)
        if current_index < len(chapters) - 1:
            self.display_chapter(chapters[current_index + 1])
            self.chapter_list.setCurrentRow(current_index + 1)
    
    def on_random_chapter(self):
        """随机阅读"""
        chapter = random.choice(list(YIN_FU_JING_DATA.keys()))
        self.display_chapter(chapter)
        self.chapter_list.setCurrentRow(list(YIN_FU_JING_DATA.keys()).index(chapter))
    
    def on_search(self):
        """搜索关键字"""
        keyword = self.search_input.text().strip()
        if keyword:
            self.highlighter.highlight_keyword(keyword)
            self.status_bar.showMessage(f"已高亮显示关键字: {keyword}")
        else:
            self.highlighter.clear_highlights()
            self.status_bar.showMessage("已清除高亮")
    
    def on_add_bookmark(self):
        """添加书签"""
        note, ok = QInputDialog.getText(self, "添加书签", "请输入书签备注:")
        if ok:
            self.db.add_bookmark(self.current_chapter, 0, note)
            self.refresh_bookmarks()
            self.status_bar.showMessage("书签添加成功")
    
    def refresh_bookmarks(self):
        """刷新书签列表"""
        self.bookmark_list.clear()
        bookmarks = self.db.get_bookmarks()
        for bookmark in bookmarks:
            chapter, position, note, created_time = bookmark
            item_text = f"{chapter} - {created_time[:10]}"
            if note:
                item_text += f" - {note}"
            self.bookmark_list.addItem(item_text)
    
    def on_save_note(self):
        """保存笔记"""
        note_content = self.note_text.toPlainText()
        if note_content:
            # 这里可以添加保存笔记到数据库的逻辑
            QMessageBox.information(self, "保存成功", "笔记已保存")
        else:
            QMessageBox.warning(self, "保存失败", "笔记内容不能为空")
    
    def on_font_changed(self, font):
        """字体改变"""
        self.content_text.setFont(font)
    
    def on_font_size_changed(self, size):
        """字体大小改变"""
        font = self.content_text.font()
        font.setPointSize(size)
        self.content_text.setFont(font)
    
    def on_theme_changed(self, theme):
        """主题改变"""
        if theme == "默认":
            self.apply_default_theme()
        elif theme == "暗色":
            self.apply_dark_theme()
        elif theme == "护眼":
            self.apply_eye_protection_theme()
    
    def apply_default_theme(self):
        """应用默认主题"""
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(240, 240, 240))
        palette.setColor(QPalette.WindowText, Qt.black)
        palette.setColor(QPalette.Base, Qt.white)
        palette.setColor(QPalette.Text, Qt.black)
        self.setPalette(palette)
    
    def apply_dark_theme(self):
        """应用暗色主题"""
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.Text, Qt.white)
        self.setPalette(palette)
    
    def apply_eye_protection_theme(self):
        """应用护眼主题"""
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(199, 237, 204))
        palette.setColor(QPalette.WindowText, Qt.black)
        palette.setColor(QPalette.Base, QColor(220, 245, 225))
        palette.setColor(QPalette.Text, Qt.black)
        self.setPalette(palette)
    
    def refresh_stats(self):
        """刷新阅读统计"""
        history = self.db.get_reading_history(limit=20)
        stats_text = "最近阅读记录:\n\n"
        for record in history:
            chapter, read_time, duration = record
            stats_text += f"{read_time[:16]} - {chapter} - 阅读{duration}秒\n"
        
        self.stats_text.setText(stats_text)
    
    def on_export(self):
        """导出经文"""
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(
            self, "导出经文", "黄帝阴符经.txt", "Text Files (*.txt)", options=options
        )
        
        if file_name:
            try:
                with open(file_name, 'w', encoding='utf-8') as f:
                    for chapter, data in YIN_FU_JING_DATA.items():
                        f.write(data["title"] + "\n")
                        f.write(data["content"] + "\n\n")
                QMessageBox.information(self, "导出成功", f"经文已导出到: {file_name}")
            except Exception as e:
                QMessageBox.critical(self, "导出失败", f"导出失败: {str(e)}")
    
    def toggle_fullscreen(self):
        """切换全屏模式"""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
    
    def show_about(self):
        """显示关于对话框"""
        about_text = """
        <h2>黄帝阴符经系统工具库</h2>
        <p>版本 1.0</p>
        <p>基于PyQt5开发的黄帝阴符经阅读和研究工具。</p>
        <p>功能包括：</p>
        <ul>
            <li>经文阅读与导航</li>
            <li>关键字搜索与高亮</li>
            <li>注释解析</li>
            <li>个人笔记</li>
            <li>阅读统计</li>
            <li>书签管理</li>
        </ul>
        <p>© 2023 黄帝阴符经研究团队</p>
        """
        QMessageBox.about(self, "关于", about_text)
    
    def closeEvent(self, event):
        """关闭事件处理"""
        # 保存最后的阅读记录
        self.db.add_reading_record(self.current_chapter, self.reading_time)
        event.accept()

# 运行应用
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用信息
    app.setApplicationName("黄帝阴符经系统工具库")
    app.setApplicationVersion("1.0")
    
    # 创建并显示主窗口
    window = YinFuJingReader()
    window.show()
    
    sys.exit(app.exec_())