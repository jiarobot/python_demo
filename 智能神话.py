import sys
import json
import random
import sqlite3
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QTextEdit, QListWidget, 
                             QLabel, QLineEdit, QComboBox, QTabWidget, 
                             QSplitter, QProgressBar, QMessageBox, QFileDialog,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QTreeWidget, QTreeWidgetItem, QGroupBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QSyntaxHighlighter, QTextCharFormat, QColor, QPalette

# 神话数据库类
class MythDatabase:
    def __init__(self, db_path="myth_database.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建神话人物表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mythical_beings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                origin TEXT,
                powers TEXT,
                description TEXT,
                strength INTEGER,
                intelligence INTEGER,
                wisdom INTEGER
            )
        ''')
        
        # 创建神话故事表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                origin_culture TEXT,
                main_characters TEXT,
                plot TEXT,
                moral TEXT,
                tags TEXT
            )
        ''')
        
        # 创建神话物品表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS artifacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT,
                origin TEXT,
                powers TEXT,
                owner TEXT
            )
        ''')
        
        # 插入示例数据
        self.insert_sample_data(cursor)
        
        conn.commit()
        conn.close()
    
    def insert_sample_data(self, cursor):
        # 检查是否已有数据
        cursor.execute("SELECT COUNT(*) FROM mythical_beings")
        if cursor.fetchone()[0] == 0:
            # 插入神话人物示例数据
            beings = [
                ("宙斯", "神", "希腊神话", "雷电、天空统治", "众神之王，天空与雷电之神", 95, 90, 85),
                ("奥丁", "神", "北欧神话", "智慧、战争、魔法", "阿萨神族的主神", 90, 95, 90),
                ("孙悟空", "神猴", "中国神话", "七十二变、筋斗云", "齐天大圣，神通广大", 85, 80, 75),
                ("阿努比斯", "神", "埃及神话", "死亡审判、灵魂引导", "胡狼头神，负责死亡仪式", 80, 85, 90),
                ("洛基", "神", "北欧神话", "变形、诡计", "诡计之神，擅长变化和欺骗", 70, 95, 60)
            ]
            
            cursor.executemany('''
                INSERT INTO mythical_beings (name, type, origin, powers, description, strength, intelligence, wisdom)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', beings)
            
            # 插入神话故事示例数据
            stories = [
                ("诸神黄昏", "北欧神话", "奥丁,索尔,洛基", "一场导致世界毁灭的巨大灾难", "即使是最强大的存在也终将面临终结", "末日,战争,命运"),
                ("特洛伊战争", "希腊神话", "阿喀琉斯,赫克托耳,奥德修斯", "因金苹果引起的十年战争", "人类的骄傲会导致毁灭", "战争,英雄,命运"),
                ("大禹治水", "中国神话", "大禹", "大禹成功治理洪水灾害", "坚持不懈的努力可以克服任何困难", "洪水,英雄,毅力")
            ]
            
            cursor.executemany('''
                INSERT INTO stories (title, origin_culture, main_characters, plot, moral, tags)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', stories)
            
            # 插入神话物品示例数据
            artifacts = [
                ("雷神之锤", "武器", "北欧神话", "召唤雷电、飞行", "索尔"),
                ("金苹果", "宝物", "希腊神话", "引起争端、赋予不朽", "厄里斯"),
                ("定海神针", "武器", "中国神话", "随意变化大小、镇海", "孙悟空")
            ]
            
            cursor.executemany('''
                INSERT INTO artifacts (name, type, origin, powers, owner)
                VALUES (?, ?, ?, ?, ?)
            ''', artifacts)

# 神话生成器类
class MythGenerator:
    def __init__(self, database):
        self.db = database
    
    def generate_character(self, origin=None, type=None):
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        query = "SELECT name, type, origin, powers, description FROM mythical_beings WHERE 1=1"
        params = []
        
        if origin:
            query += " AND origin = ?"
            params.append(origin)
        if type:
            query += " AND type = ?"
            params.append(type)
        
        cursor.execute(query, params)
        beings = cursor.fetchall()
        conn.close()
        
        if beings:
            being = random.choice(beings)
            return {
                "name": being[0],
                "type": being[1],
                "origin": being[2],
                "powers": being[3],
                "description": being[4]
            }
        return None
    
    def generate_story(self, culture=None):
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        query = "SELECT title, origin_culture, main_characters, plot, moral FROM stories WHERE 1=1"
        params = []
        
        if culture:
            query += " AND origin_culture = ?"
            params.append(culture)
        
        cursor.execute(query, params)
        stories = cursor.fetchall()
        conn.close()
        
        if stories:
            story = random.choice(stories)
            return {
                "title": story[0],
                "origin": story[1],
                "characters": story[2],
                "plot": story[3],
                "moral": story[4]
            }
        return None
    
    def create_custom_myth(self, elements):
        # 基于输入元素创建自定义神话
        character = self.generate_character(elements.get('origin'), elements.get('type'))
        story = self.generate_story(elements.get('culture'))
        
        if character and story:
            custom_myth = f"""
            {story['title']} - 自定义版本
            
            在{story['origin']}的传说中，{character['name']}是一位{character['type']}。
            
            {story['plot']} 在这个过程中，{character['name']}展现了{character['powers']}的能力。
            
            故事的寓意是：{story['moral']}
            """
            return custom_myth
        return "无法生成神话，请检查输入条件。"

# 语法高亮类（用于神话文本）
class MythHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super(MythHighlighter, self).__init__(parent)
        
        self.highlighting_rules = []
        
        # 神话角色名称格式
        character_format = QTextCharFormat()
        character_format.setForeground(QColor(200, 50, 50))
        character_format.setFontWeight(QFont.Bold)
        self.highlighting_rules.append((r'\b(宙斯|奥丁|孙悟空|阿努比斯|洛基|阿喀琉斯|索尔)\b', character_format))
        
        # 神话地点格式
        location_format = QTextCharFormat()
        location_format.setForeground(QColor(50, 120, 200))
        self.highlighting_rules.append((r'\b(奥林匹斯|阿斯加德|天庭|冥界)\b', location_format))
        
        # 神话物品格式
        artifact_format = QTextCharFormat()
        artifact_format.setForeground(QColor(180, 100, 50))
        artifact_format.setFontItalic(True)
        self.highlighting_rules.append((r'\b(雷神之锤|金苹果|定海神针)\b', artifact_format))
    
    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            expression = QtCore.QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)

# 神话分析线程
class MythAnalysisThread(QThread):
    analysis_complete = pyqtSignal(dict)
    
    def __init__(self, text):
        super().__init__()
        self.text = text
    
    def run(self):
        # 模拟复杂的神话分析过程
        analysis_result = {
            "character_count": len([c for c in ["宙斯", "奥丁", "孙悟空", "阿努比斯", "洛基"] if c in self.text]),
            "power_mentions": len([p for p in ["雷电", "智慧", "变化", "魔法"] if p in self.text]),
            "origin_detected": self.detect_origin(self.text),
            "complexity_score": random.randint(50, 100)
        }
        
        # 模拟处理时间
        self.msleep(2000)
        
        self.analysis_complete.emit(analysis_result)
    
    def detect_origin(self, text):
        origins = ["希腊神话", "北欧神话", "中国神话", "埃及神话"]
        for origin in origins:
            if origin in text:
                return origin
        return "未知"

# 主窗口类
class MythSystemMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.database = MythDatabase()
        self.generator = MythGenerator(self.database)
        self.init_ui()
        
        # 定时器用于更新状态
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(5000)  # 每5秒更新一次
        
    def init_ui(self):
        self.setWindowTitle("智能神话实现系统")
        self.setGeometry(100, 100, 1200, 800)
        
        # 设置中心窗口
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 创建左侧面板
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel)
        
        # 创建右侧面板（标签页）
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel)
        
        # 创建状态栏
        self.statusBar().showMessage("系统就绪")
        
        # 应用样式
        self.apply_styles()
    
    def create_left_panel(self):
        panel = QWidget()
        panel.setMaximumWidth(300)
        layout = QVBoxLayout(panel)
        
        # 快速生成组
        quick_group = QGroupBox("快速生成")
        quick_layout = QVBoxLayout(quick_group)
        
        self.origin_combo = QComboBox()
        self.origin_combo.addItems(["全部", "希腊神话", "北欧神话", "中国神话", "埃及神话"])
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["全部", "神", "英雄", "怪物", "神兽"])
        
        generate_character_btn = QPushButton("生成神话角色")
        generate_character_btn.clicked.connect(self.generate_character)
        
        generate_story_btn = QPushButton("生成神话故事")
        generate_story_btn.clicked.connect(self.generate_story)
        
        quick_layout.addWidget(QLabel("神话起源:"))
        quick_layout.addWidget(self.origin_combo)
        quick_layout.addWidget(QLabel("角色类型:"))
        quick_layout.addWidget(self.type_combo)
        quick_layout.addWidget(generate_character_btn)
        quick_layout.addWidget(generate_story_btn)
        
        # 数据库操作组
        db_group = QGroupBox("数据库操作")
        db_layout = QVBoxLayout(db_group)
        
        search_edit = QLineEdit()
        search_edit.setPlaceholderText("搜索神话元素...")
        
        search_btn = QPushButton("搜索")
        search_btn.clicked.connect(self.search_database)
        
        view_all_btn = QPushButton("查看所有神话角色")
        view_all_btn.clicked.connect(self.view_all_characters)
        
        db_layout.addWidget(search_edit)
        db_layout.addWidget(search_btn)
        db_layout.addWidget(view_all_btn)
        
        # 系统状态组
        status_group = QGroupBox("系统状态")
        status_layout = QVBoxLayout(status_group)
        
        self.status_label = QLabel("系统运行正常")
        self.myth_count_label = QLabel("神话数据库: 加载中...")
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(100)
        
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.myth_count_label)
        status_layout.addWidget(self.progress_bar)
        
        # 添加到主布局
        layout.addWidget(quick_group)
        layout.addWidget(db_group)
        layout.addWidget(status_group)
        layout.addStretch()
        
        return panel
    
    def create_right_panel(self):
        tab_widget = QTabWidget()
        
        # 神话生成器标签
        generator_tab = QWidget()
        generator_layout = QVBoxLayout(generator_tab)
        
        self.myth_display = QTextEdit()
        self.myth_display.setPlaceholderText("生成的神话内容将显示在这里...")
        
        # 添加语法高亮
        self.highlighter = MythHighlighter(self.myth_document())
        
        analyze_btn = QPushButton("分析神话内容")
        analyze_btn.clicked.connect(self.analyze_myth)
        
        save_btn = QPushButton("保存神话")
        save_btn.clicked.connect(self.save_myth)
        
        generator_layout.addWidget(QLabel("神话内容:"))
        generator_layout.addWidget(self.myth_display)
        generator_layout.addWidget(analyze_btn)
        generator_layout.addWidget(save_btn)
        
        # 神话数据库标签
        database_tab = QWidget()
        database_layout = QVBoxLayout(database_tab)
        
        self.database_table = QTableWidget()
        self.database_table.setColumnCount(5)
        self.database_table.setHorizontalHeaderLabels(["名称", "类型", "起源", "能力", "描述"])
        self.database_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        database_layout.addWidget(QLabel("神话数据库:"))
        database_layout.addWidget(self.database_table)
        
        # 自定义神话标签
        custom_tab = QWidget()
        custom_layout = QVBoxLayout(custom_tab)
        
        custom_input = QTextEdit()
        custom_input.setPlaceholderText("输入神话元素，如：希腊神话中的英雄与怪物战斗...")
        
        generate_custom_btn = QPushButton("生成自定义神话")
        
        custom_layout.addWidget(QLabel("自定义神话生成:"))
        custom_layout.addWidget(custom_input)
        custom_layout.addWidget(generate_custom_btn)
        
        # 添加所有标签
        tab_widget.addTab(generator_tab, "神话生成器")
        tab_widget.addTab(database_tab, "神话数据库")
        tab_widget.addTab(custom_tab, "自定义神话")
        
        return tab_widget
    
    def myth_document(self):
        return self.myth_display.document()
    
    def generate_character(self):
        origin = self.origin_combo.currentText()
        type = self.type_combo.currentText()
        
        if origin == "全部":
            origin = None
        if type == "全部":
            type = None
            
        character = self.generator.generate_character(origin, type)
        if character:
            character_text = f"""
            【神话角色生成】
            
            名称：{character['name']}
            类型：{character['type']}
            起源：{character['origin']}
            能力：{character['powers']}
            描述：{character['description']}
            """
            self.myth_display.setPlainText(character_text)
        else:
            self.myth_display.setPlainText("未找到符合条件的神话角色。")
    
    def generate_story(self):
        origin = self.origin_combo.currentText()
        culture = origin if origin != "全部" else None
        
        story = self.generator.generate_story(culture)
        if story:
            story_text = f"""
            【神话故事生成】
            
            标题：{story['title']}
            文化起源：{story['origin']}
            主要角色：{story['characters']}
            情节：{story['plot']}
            寓意：{story['moral']}
            """
            self.myth_display.setPlainText(story_text)
        else:
            self.myth_display.setPlainText("未找到符合条件的神话故事。")
    
    def analyze_myth(self):
        text = self.myth_display.toPlainText()
        if not text.strip():
            QMessageBox.warning(self, "警告", "请先生成或输入神话内容进行分析。")
            return
        
        self.statusBar().showMessage("正在分析神话内容...")
        
        # 创建分析线程
        self.analysis_thread = MythAnalysisThread(text)
        self.analysis_thread.analysis_complete.connect(self.on_analysis_complete)
        self.analysis_thread.start()
    
    def on_analysis_complete(self, result):
        analysis_text = f"""
        【神话分析结果】
        
        角色数量：{result['character_count']}
        能力提及：{result['power_mentions']}次
        文化起源：{result['origin_detected']}
        复杂度评分：{result['complexity_score']}/100
        """
        
        self.myth_display.append(analysis_text)
        self.statusBar().showMessage("神话分析完成")
    
    def save_myth(self):
        text = self.myth_display.toPlainText()
        if not text.strip():
            QMessageBox.warning(self, "警告", "没有内容可保存。")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存神话", f"神话_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", 
            "文本文件 (*.txt);;所有文件 (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                QMessageBox.information(self, "成功", "神话内容已保存。")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存文件时出错：{str(e)}")
    
    def search_database(self):
        # 实现数据库搜索功能
        pass
    
    def view_all_characters(self):
        conn = sqlite3.connect(self.database.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name, type, origin, powers, description FROM mythical_beings")
        characters = cursor.fetchall()
        conn.close()
        
        self.database_table.setRowCount(len(characters))
        for row, character in enumerate(characters):
            for col, value in enumerate(character):
                self.database_table.setItem(row, col, QTableWidgetItem(str(value)))
    
    def update_status(self):
        conn = sqlite3.connect(self.database.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM mythical_beings")
        character_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM stories")
        story_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM artifacts")
        artifact_count = cursor.fetchone()[0]
        
        conn.close()
        
        self.myth_count_label.setText(f"神话数据库: {character_count}角色, {story_count}故事, {artifact_count}物品")
        self.status_label.setText(f"最后更新: {datetime.now().strftime('%H:%M:%S')}")
    
    def apply_styles(self):
        # 应用一些基本样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
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
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 8px 16px;
                text-align: center;
                text-decoration: none;
                font-size: 14px;
                margin: 4px 2px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QTextEdit {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 8px;
                font-size: 14px;
            }
            QTableWidget {
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: white;
            }
        """)

# 应用程序类
class MythSystemApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        
    def run(self):
        window = MythSystemMainWindow()
        window.show()
        return self.exec_()

# 主函数
def main():
    app = MythSystemApp(sys.argv)
    sys.exit(app.run())

if __name__ == "__main__":
    main()