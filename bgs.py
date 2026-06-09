import sys
import json
import os
import random
import time
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, QComboBox, QPushButton, 
                            QTextEdit, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
                            QProgressBar, QFrame, QMessageBox, QListWidget, QListWidgetItem,
                            QStackedWidget, QLineEdit, QTabWidget, QDialog, QInputDialog,
                            QFileDialog, QAction, QMenu, QStyleFactory, QToolButton)
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QFont, QPalette, QColor, QPixmap, QIcon, QPainter, QBrush, QPen, QLinearGradient

class BaguaTherapyApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("八卦象数疗法")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建应用数据目录
        self.data_dir = "bagua_data"
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 加载数据
        self.load_data()
        
        # 设置应用样式
        self.setStyle()
        
        # 创建主界面
        self.init_ui()
        
        # 初始化状态
        self.current_prescription = ""
        self.current_index = 0
        self.is_playing = False
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_number)
        self.remaining_time = 0
        self.total_time = 0
        self.practice_records = []
        
    def setStyle(self):
        # 设置应用样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f5f5;
            }
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                border: 2px solid #8d9e8d;
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 15px;
                background-color: rgba(255, 255, 255, 180);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
                background-color: #d4e8d4;
            }
            QLabel {
                font-size: 14px;
            }
            QPushButton {
                background-color: #5c8d89;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 14px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #4a7a75;
            }
            QPushButton:pressed {
                background-color: #3a6a65;
            }
            QPushButton:disabled {
                background-color: #a0b0ae;
            }
            QComboBox {
                padding: 5px;
                border: 1px solid #8d9e8d;
                border-radius: 4px;
                background-color: white;
                min-height: 30px;
            }
            QTextEdit, QLineEdit {
                border: 1px solid #8d9e8d;
                border-radius: 4px;
                background-color: white;
                font-size: 14px;
                padding: 5px;
            }
            QProgressBar {
                border: 1px solid #8d9e8d;
                border-radius: 5px;
                text-align: center;
                background-color: #e0e0e0;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #5c8d89;
                width: 10px;
            }
            QListWidget {
                border: 1px solid #8d9e8d;
                border-radius: 4px;
                background-color: white;
                font-size: 14px;
            }
            QTabWidget::pane {
                border: 1px solid #8d9e8d;
                border-radius: 4px;
                background: white;
            }
            QTabBar::tab {
                background: #d4e8d4;
                border: 1px solid #8d9e8d;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #5c8d89;
                color: white;
            }
            QTabBar::tab:hover {
                background: #4a7a75;
                color: white;
            }
        """)
        
        # 设置应用图标
        self.setWindowIcon(QIcon(self.create_bagua_icon()))
        
    def create_bagua_icon(self):
        """创建八卦图标"""
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制八卦图
        painter.setPen(QPen(Qt.black, 2))
        painter.setBrush(QBrush(Qt.white))
        painter.drawEllipse(10, 10, 44, 44)
        
        # 绘制阴阳鱼
        painter.setBrush(QBrush(Qt.black))
        painter.drawChord(10, 10, 44, 44, 0, 180 * 16)
        painter.setBrush(QBrush(Qt.white))
        painter.drawChord(10, 10, 44, 44, 180 * 16, 180 * 16)
        
        # 绘制阴阳眼
        painter.setBrush(QBrush(Qt.white))
        painter.drawEllipse(24, 16, 8, 8)
        painter.setBrush(QBrush(Qt.black))
        painter.drawEllipse(24, 40, 8, 8)
        
        painter.end()
        return pixmap
    
    def load_data(self):
        """加载应用数据"""
        # 默认配方库
        self.default_therapy_data = {
            "头痛": ["030·720·60", "010·60·720", "030·820·60"],
            "失眠": ["030·820·60", "650·380", "820·030"],
            "咳嗽": ["070·020·60", "020·70", "260·50·70"],
            "胃痛": ["070·40·820", "70·40", "820·70"],
            "腰痛": ["060·050·070", "60·50·70", "70·60·50"],
            "便秘": ["080·160·40", "80·160·40", "40·80"],
            "高血压": ["010·640·380", "010·60·380", "640·010"],
            "糖尿病": ["070·260·430", "260·70", "430·70"],
            "肩周炎": ["050·070·030", "50·70·30", "030·50"],
            "月经不调": ["030·820·640", "640·30", "030·640"],
            "感冒": ["070·020·040", "70·20", "040·70"],
            "眼睛疲劳": ["030·040·060", "30·40·60", "003"],
            "焦虑": ["030·820·650", "650·30", "030·650"],
            "食欲不振": ["070·40·820", "70·820", "40·70"],
            "关节痛": ["060·050·070", "60·70", "050·070"],
            "疲劳": ["030·820·60", "820·030", "60·30"],
            "记忆力减退": ["010·640·380", "640·010", "380·010"],
            "皮肤问题": ["080·160·40", "80·40", "160·080"]
        }
        
        # 八卦对应关系
        self.bagua_info = {
            "乾": {"数字": "1", "五行": "金", "代表": "天、头部、父亲", "方向": "西北", "颜色": "金白", "季节": "秋冬"},
            "兑": {"数字": "2", "五行": "金", "代表": "泽、口、少女", "方向": "西", "颜色": "白", "季节": "秋"},
            "离": {"数字": "3", "五行": "火", "代表": "火、目、中女", "方向": "南", "颜色": "红", "季节": "夏"},
            "震": {"数字": "4", "五行": "木", "代表": "雷、足、长男", "方向": "东", "颜色": "绿", "季节": "春"},
            "巽": {"数字": "5", "五行": "木", "代表": "风、股、长女", "方向": "东南", "颜色": "绿", "季节": "春夏"},
            "坎": {"数字": "6", "五行": "水", "代表": "水、耳、中男", "方向": "北", "颜色": "黑", "季节": "冬"},
            "艮": {"数字": "7", "五行": "土", "代表": "山、手、少男", "方向": "东北", "颜色": "黄", "季节": "冬春"},
            "坤": {"数字": "8", "五行": "土", "代表": "地、腹、母亲", "方向": "西南", "颜色": "黄", "季节": "夏秋"}
        }
        
        # 加载用户自定义配方
        self.user_therapy_data = {}
        self.custom_file = os.path.join(self.data_dir, "custom_prescriptions.json")
        if os.path.exists(self.custom_file):
            try:
                with open(self.custom_file, 'r', encoding='utf-8') as f:
                    self.user_therapy_data = json.load(f)
            except:
                self.user_therapy_data = {}
        
        # 加载历史记录
        self.history_file = os.path.join(self.data_dir, "practice_history.json")
        self.practice_history = []
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.practice_history = json.load(f)
            except:
                self.practice_history = []
    
    def save_data(self):
        """保存应用数据"""
        # 保存自定义配方
        with open(self.custom_file, 'w', encoding='utf-8') as f:
            json.dump(self.user_therapy_data, f, ensure_ascii=False, indent=2)
        
        # 保存历史记录
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.practice_history, f, ensure_ascii=False, indent=2)
    
    def init_ui(self):
        """初始化用户界面"""
        # 创建主窗口部件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # 主布局
        main_layout = QVBoxLayout(main_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # 创建标题栏
        self.create_title_bar(main_layout)
        
        # 创建主选项卡
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # 添加选项卡
        self.create_therapy_tab()
        self.create_knowledge_tab()
        self.create_history_tab()
        self.create_custom_tab()
        
        # 添加底部信息
        self.create_footer(main_layout)
        
        # 创建菜单栏
        self.create_menus()
    
    def create_title_bar(self, layout):
        """创建标题栏"""
        title_layout = QHBoxLayout()
        
        # 标题标签
        title_label = QLabel("八卦象数疗法")
        title_label.setFont(QFont("微软雅黑", 28, QFont.Bold))
        title_label.setStyleSheet("color: #2a5a55; background: transparent;")
        
        # 八卦图标签
        bagua_label = QLabel()
        bagua_pixmap = self.create_bagua_icon().scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        bagua_label.setPixmap(bagua_pixmap)
        bagua_label.setAlignment(Qt.AlignCenter)
        
        title_layout.addWidget(bagua_label)
        title_layout.addWidget(title_label, 1)
        
        # 添加日期时间
        date_label = QLabel(datetime.now().strftime("%Y-%m-%d %H:%M"))
        date_label.setFont(QFont("Arial", 14))
        date_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        title_layout.addWidget(date_label)
        
        layout.addLayout(title_layout)
    
    def create_therapy_tab(self):
        """创建疗法主选项卡"""
        therapy_tab = QWidget()
        self.tab_widget.addTab(therapy_tab, "疗法实践")
        
        tab_layout = QVBoxLayout(therapy_tab)
        
        # 创建上半部分布局
        top_layout = QHBoxLayout()
        
        # 左侧症状选择区域
        symptom_group = QGroupBox("症状选择与配方")
        symptom_layout = QVBoxLayout()
        
        # 症状选择
        symptom_layout.addWidget(QLabel("选择症状:"))
        self.symptom_combo = QComboBox()
        self.symptom_combo.addItems(sorted(set(self.default_therapy_data.keys()) | set(self.user_therapy_data.keys())))
        symptom_layout.addWidget(self.symptom_combo)
        
        # 配方选择
        symptom_layout.addWidget(QLabel("可用配方:"))
        self.prescription_list = QListWidget()
        symptom_layout.addWidget(self.prescription_list)
        
        # 更新配方列表
        self.update_prescription_list()
        
        # 连接信号
        self.symptom_combo.currentTextChanged.connect(self.update_prescription_list)
        self.prescription_list.itemClicked.connect(self.select_prescription)
        
        # 控制按钮
        btn_layout = QHBoxLayout()
        self.select_btn = QPushButton("选择配方")
        self.select_btn.clicked.connect(self.select_current_prescription)
        self.select_btn.setEnabled(False)
        btn_layout.addWidget(self.select_btn)
        
        self.random_btn = QPushButton("随机配方")
        self.random_btn.clicked.connect(self.select_random_prescription)
        btn_layout.addWidget(self.random_btn)
        
        symptom_layout.addLayout(btn_layout)
        
        # 当前配方显示
        self.current_prescription_label = QLabel("当前配方: 无")
        self.current_prescription_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.current_prescription_label.setStyleSheet("color: #d35400; background-color: #fef9e7; padding: 10px; border-radius: 5px;")
        self.current_prescription_label.setAlignment(Qt.AlignCenter)
        symptom_layout.addWidget(self.current_prescription_label)
        
        symptom_group.setLayout(symptom_layout)
        top_layout.addWidget(symptom_group, 1)
        
        # 右侧八卦信息区域
        bagua_group = QGroupBox("八卦信息")
        bagua_layout = QVBoxLayout()
        
        self.bagua_display = QLabel()
        self.bagua_display.setAlignment(Qt.AlignCenter)
        self.bagua_display.setMinimumHeight(300)
        bagua_layout.addWidget(self.bagua_display)
        
        # 八卦选择
        bagua_layout.addWidget(QLabel("选择八卦查看详情:"))
        self.bagua_combo = QComboBox()
        self.bagua_combo.addItems(self.bagua_info.keys())
        self.bagua_combo.currentIndexChanged.connect(self.update_bagua_display)
        bagua_layout.addWidget(self.bagua_combo)
        
        # 八卦详情
        self.bagua_details = QTextEdit()
        self.bagua_details.setReadOnly(True)
        bagua_layout.addWidget(self.bagua_details)
        
        bagua_group.setLayout(bagua_layout)
        top_layout.addWidget(bagua_group, 1)
        
        tab_layout.addLayout(top_layout)
        
        # 默念练习区域
        practice_group = QGroupBox("象数默念练习")
        practice_layout = QVBoxLayout()
        
        # 当前数字显示
        self.current_number_label = QLabel()
        self.current_number_label.setFont(QFont("Arial", 48, QFont.Bold))
        self.current_number_label.setAlignment(Qt.AlignCenter)
        self.current_number_label.setStyleSheet("background-color: #e8f4f3; border-radius: 10px; padding: 30px;")
        self.current_number_label.setMinimumHeight(180)
        practice_layout.addWidget(self.current_number_label)
        
        # 控制按钮
        btn_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("开始默念")
        self.start_btn.clicked.connect(self.start_practice)
        btn_layout.addWidget(self.start_btn)
        
        self.pause_btn = QPushButton("暂停")
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self.pause_practice)
        btn_layout.addWidget(self.pause_btn)
        
        self.stop_btn = QPushButton("停止")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_practice)
        btn_layout.addWidget(self.stop_btn)
        
        practice_layout.addLayout(btn_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("准备开始")
        practice_layout.addWidget(self.progress_bar)
        
        # 计时设置
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("每个数字显示时间(秒):"))
        
        self.time_per_digit = QComboBox()
        self.time_per_digit.addItems(["1.0", "1.5", "2.0", "2.5", "3.0"])
        self.time_per_digit.setCurrentIndex(1)
        time_layout.addWidget(self.time_per_digit)
        
        time_layout.addStretch()
        practice_layout.addLayout(time_layout)
        
        practice_group.setLayout(practice_layout)
        tab_layout.addWidget(practice_group)
        
        # 初始化八卦显示
        self.update_bagua_display()
    
    def create_knowledge_tab(self):
        """创建知识库选项卡"""
        knowledge_tab = QWidget()
        self.tab_widget.addTab(knowledge_tab, "知识库")
        
        layout = QVBoxLayout(knowledge_tab)
        
        # 创建选项卡
        knowledge_tabs = QTabWidget()
        layout.addWidget(knowledge_tabs)
        
        # 基础理论
        theory_tab = QWidget()
        theory_layout = QVBoxLayout(theory_tab)
        
        theory_text = QTextEdit()
        theory_text.setReadOnly(True)
        theory_text.setHtml("""
            <h2 align="center">八卦象数疗法基础理论</h2>
            
            <h3>一、八卦象数疗法简介</h3>
            <p>八卦象数疗法是一种源自《易经》的自然疗法，通过默念特定的数字组合（象数配方）来调节身体能量，达到治疗疾病的目的。这种疗法将易经八卦理论与人体健康相结合，认为每个数字对应一个八卦，具有特定的五行属性和代表的身体部位。</p>
            
            <h3>二、基本原理</h3>
            <p>1. 八卦对应：乾(1)、兑(2)、离(3)、震(4)、巽(5)、坎(6)、艮(7)、坤(8)</p>
            <p>2. 五行属性：金(1,2)、木(4,5)、水(6)、火(3)、土(7,8)</p>
            <p>3. 人体对应：每个八卦对应人体的特定部位和器官</p>
            <p>4. 象数作用：默念数字组合可以调节相应部位的能量平衡</p>
            
            <h3>三、使用方法</h3>
            <p>1. 根据症状选择对应的象数配方</p>
            <p>2. 静心默念（无需出声），集中注意力</p>
            <p>3. 每日多次，每次15-30分钟</p>
            <p>4. 点号(·)表示停顿，应默念稍长时间</p>
            
            <h3>四、注意事项</h3>
            <p>1. 象数疗法作为辅助疗法，不能替代正规医疗</p>
            <p>2. 如有严重症状，请及时就医</p>
            <p>3. 默念时保持身心放松</p>
            <p>4. 注意观察身体反应，如有不适停止使用</p>
        """)
        theory_layout.addWidget(theory_text)
        knowledge_tabs.addTab(theory_tab, "基础理论")
        
        # 常见配方
        formula_tab = QWidget()
        formula_layout = QVBoxLayout(formula_tab)
        
        formula_text = QTextEdit()
        formula_text.setReadOnly(True)
        
        # 构建配方表格
        html = """
            <h2 align="center">常见症状象数配方</h2>
            <table border="1" cellpadding="8" style="border-collapse: collapse; width: 100%;">
                <tr style="background-color: #d4e8d4;">
                    <th width="20%">症状</th>
                    <th width="40%">配方</th>
                    <th width="40%">说明</th>
                </tr>
        """
        
        for symptom, formulas in self.default_therapy_data.items():
            html += f"""
                <tr>
                    <td>{symptom}</td>
                    <td>{'<br>'.join(formulas)}</td>
                    <td>根据症状选择适合的配方，可尝试不同配方效果</td>
                </tr>
            """
        
        html += "</table>"
        formula_text.setHtml(html)
        formula_layout.addWidget(formula_text)
        knowledge_tabs.addTab(formula_tab, "常见配方")
        
        # 五行理论
        wuxing_tab = QWidget()
        wuxing_layout = QVBoxLayout(wuxing_tab)
        
        wuxing_text = QTextEdit()
        wuxing_text.setReadOnly(True)
        wuxing_text.setHtml("""
            <h2 align="center">五行理论与健康</h2>
            
            <h3>一、五行相生相克</h3>
            <p>五行相生：木生火 → 火生土 → 土生金 → 金生水 → 水生木</p>
            <p>五行相克：木克土 → 土克水 → 水克火 → 火克金 → 金克木</p>
            
            <h3>二、五行与人体</h3>
            <p>1. 木：肝、胆、眼、筋</p>
            <p>2. 火：心、小肠、舌、脉</p>
            <p>3. 土：脾、胃、口、肉</p>
            <p>4. 金：肺、大肠、鼻、皮毛</p>
            <p>5. 水：肾、膀胱、耳、骨</p>
            
            <h3>三、五行与健康平衡</h3>
            <p>1. 五行平衡则身体健康</p>
            <p>2. 五行失衡则产生疾病</p>
            <p>3. 象数疗法通过数字组合调节五行平衡</p>
            
            <h3>四、五行与八卦对应</h3>
            <p>金：乾(1)、兑(2)</p>
            <p>木：震(4)、巽(5)</p>
            <p>水：坎(6)</p>
            <p>火：离(3)</p>
            <p>土：艮(7)、坤(8)</p>
        """)
        wuxing_layout.addWidget(wuxing_text)
        knowledge_tabs.addTab(wuxing_tab, "五行理论")
    
    def create_history_tab(self):
        """创建历史记录选项卡"""
        history_tab = QWidget()
        self.tab_widget.addTab(history_tab, "历史记录")
        
        layout = QVBoxLayout(history_tab)
        
        # 历史记录列表
        self.history_list = QListWidget()
        self.history_list.setIconSize(QSize(32, 32))
        self.update_history_list()
        layout.addWidget(self.history_list)
        
        # 控制按钮
        btn_layout = QHBoxLayout()
        
        self.view_btn = QPushButton("查看详情")
        self.view_btn.clicked.connect(self.view_history)
        btn_layout.addWidget(self.view_btn)
        
        self.delete_btn = QPushButton("删除记录")
        self.delete_btn.clicked.connect(self.delete_history)
        btn_layout.addWidget(self.delete_btn)
        
        self.clear_btn = QPushButton("清空历史")
        self.clear_btn.clicked.connect(self.clear_history)
        btn_layout.addWidget(self.clear_btn)
        
        self.export_btn = QPushButton("导出记录")
        self.export_btn.clicked.connect(self.export_history)
        btn_layout.addWidget(self.export_btn)
        
        layout.addLayout(btn_layout)
        
        # 历史详情
        self.history_details = QTextEdit()
        self.history_details.setReadOnly(True)
        layout.addWidget(self.history_details)
    
    def create_custom_tab(self):
        """创建自定义配方选项卡"""
        custom_tab = QWidget()
        self.tab_widget.addTab(custom_tab, "自定义配方")
        
        layout = QVBoxLayout(custom_tab)
        
        # 添加新配方
        add_group = QGroupBox("添加新配方")
        add_layout = QVBoxLayout()
        
        # 症状输入
        symptom_layout = QHBoxLayout()
        symptom_layout.addWidget(QLabel("症状名称:"))
        self.new_symptom_input = QLineEdit()
        symptom_layout.addWidget(self.new_symptom_input)
        add_layout.addLayout(symptom_layout)
        
        # 配方输入
        formula_layout = QHBoxLayout()
        formula_layout.addWidget(QLabel("象数配方:"))
        self.new_formula_input = QLineEdit()
        formula_layout.addWidget(self.new_formula_input)
        add_layout.addLayout(formula_layout)
        
        # 添加按钮
        self.add_btn = QPushButton("添加配方")
        self.add_btn.clicked.connect(self.add_custom_prescription)
        add_layout.addWidget(self.add_btn)
        
        add_group.setLayout(add_layout)
        layout.addWidget(add_group)
        
        # 自定义配方列表
        self.custom_list = QListWidget()
        self.update_custom_list()
        layout.addWidget(self.custom_list)
        
        # 控制按钮
        btn_layout = QHBoxLayout()
        
        self.edit_btn = QPushButton("编辑配方")
        self.edit_btn.clicked.connect(self.edit_custom_prescription)
        btn_layout.addWidget(self.edit_btn)
        
        self.remove_btn = QPushButton("删除配方")
        self.remove_btn.clicked.connect(self.remove_custom_prescription)
        btn_layout.addWidget(self.remove_btn)
        
        self.import_btn = QPushButton("导入配方")
        self.import_btn.clicked.connect(self.import_custom_prescription)
        btn_layout.addWidget(self.import_btn)
        
        layout.addLayout(btn_layout)
    
    def create_footer(self, layout):
        """创建底部信息"""
        footer_label = QLabel("八卦象数疗法 - 基于易经的自然疗法 | 注意：本程序仅供参考，不能替代专业医疗建议")
        footer_label.setAlignment(Qt.AlignCenter)
        footer_label.setStyleSheet("color: #7f8c8d; font-size: 12px; padding: 5px; background-color: #d4e8d4; border-radius: 5px;")
        layout.addWidget(footer_label)
    
    def create_menus(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        export_action = QAction("导出数据", self)
        export_action.triggered.connect(self.export_all_data)
        file_menu.addAction(export_action)
        
        import_action = QAction("导入数据", self)
        import_action.triggered.connect(self.import_data)
        file_menu.addAction(import_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def update_prescription_list(self):
        """更新配方列表"""
        symptom = self.symptom_combo.currentText()
        self.prescription_list.clear()
        
        # 添加默认配方
        if symptom in self.default_therapy_data:
            for formula in self.default_therapy_data[symptom]:
                item = QListWidgetItem(f"🔹 {formula} (默认)")
                item.setData(Qt.UserRole, formula)
                self.prescription_list.addItem(item)
        
        # 添加自定义配方
        if symptom in self.user_therapy_data:
            for formula in self.user_therapy_data[symptom]:
                item = QListWidgetItem(f"🔸 {formula} (自定义)")
                item.setData(Qt.UserRole, formula)
                self.prescription_list.addItem(item)
    
    def update_bagua_display(self):
        """更新八卦显示"""
        bagua = self.bagua_combo.currentText()
        info = self.bagua_info[bagua]
        
        # 创建八卦图
        pixmap = QPixmap(300, 300)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 设置背景
        gradient = QLinearGradient(0, 0, 300, 300)
        gradient.setColorAt(0, QColor(212, 232, 212))
        gradient.setColorAt(1, QColor(240, 245, 245))
        painter.setBrush(QBrush(gradient))
        painter.drawRect(0, 0, 300, 300)
        
        # 绘制八卦
        painter.setPen(QPen(Qt.black, 3))
        painter.setBrush(QBrush(Qt.white))
        painter.drawEllipse(50, 50, 200, 200)
        
        # 根据八卦类型绘制不同的符号
        if bagua == "乾":
            # 三实线
            for i in range(3):
                painter.drawLine(100, 70 + i*60, 200, 70 + i*60)
        elif bagua == "坤":
            # 三虚线
            for i in range(3):
                painter.drawLine(100, 70 + i*60, 130, 70 + i*60)
                painter.drawLine(170, 70 + i*60, 200, 70 + i*60)
        elif bagua == "坎":
            # 上下虚线，中间实线
            painter.drawLine(100, 70, 130, 70)
            painter.drawLine(170, 70, 200, 70)
            painter.drawLine(100, 130, 200, 130)
            painter.drawLine(100, 190, 130, 190)
            painter.drawLine(170, 190, 200, 190)
        elif bagua == "离":
            # 上下实线，中间虚线
            painter.drawLine(100, 70, 200, 70)
            painter.drawLine(100, 130, 130, 130)
            painter.drawLine(170, 130, 200, 130)
            painter.drawLine(100, 190, 200, 190)
        elif bagua == "震":
            # 上虚线，下两实线
            painter.drawLine(100, 70, 130, 70)
            painter.drawLine(170, 70, 200, 70)
            painter.drawLine(100, 130, 200, 130)
            painter.drawLine(100, 190, 200, 190)
        elif bagua == "艮":
            # 上实线，下两虚线
            painter.drawLine(100, 70, 200, 70)
            painter.drawLine(100, 130, 200, 130)
            painter.drawLine(100, 190, 130, 190)
            painter.drawLine(170, 190, 200, 190)
        elif bagua == "巽":
            # 上实线，中下虚线
            painter.drawLine(100, 70, 200, 70)
            painter.drawLine(100, 130, 130, 130)
            painter.drawLine(170, 130, 200, 130)
            painter.drawLine(100, 190, 130, 190)
            painter.drawLine(170, 190, 200, 190)
        elif bagua == "兑":
            # 上虚线，中下实线
            painter.drawLine(100, 70, 130, 70)
            painter.drawLine(170, 70, 200, 70)
            painter.drawLine(100, 130, 200, 130)
            painter.drawLine(100, 190, 200, 190)
        
        painter.end()
        self.bagua_display.setPixmap(pixmap)
        
        # 更新八卦详情
        details = f"""
            <h2 align="center">{bagua}卦</h2>
            <p><b>数字:</b> {info['数字']}</p>
            <p><b>五行:</b> {info['五行']}</p>
            <p><b>代表:</b> {info['代表']}</p>
            <p><b>方向:</b> {info['方向']}</p>
            <p><b>颜色:</b> {info['颜色']}</p>
            <p><b>季节:</b> {info['季节']}</p>
            <p><b>健康关联:</b> {self.get_bagua_health_info(bagua)}</p>
        """
        self.bagua_details.setHtml(details)
    
    def get_bagua_health_info(self, bagua):
        """获取八卦健康信息"""
        health_info = {
            "乾": "头部、大脑、神经系统、骨骼",
            "兑": "口腔、呼吸系统、皮肤",
            "离": "心脏、眼睛、血液循环",
            "震": "肝脏、神经系统、运动系统",
            "巽": "神经系统、呼吸系统、大腿",
            "坎": "肾脏、泌尿系统、耳朵",
            "艮": "脾胃、消化系统、手部",
            "坤": "腹部、消化系统、生殖系统"
        }
        return health_info.get(bagua, "")
    
    def select_prescription(self):
        """选择配方时启用选择按钮"""
        self.select_btn.setEnabled(self.prescription_list.currentItem() is not None)
    
    def select_current_prescription(self):
        """选择当前选中的配方"""
        item = self.prescription_list.currentItem()
        if item:
            formula = item.data(Qt.UserRole)
            self.current_prescription = formula
            self.current_prescription_label.setText(f"当前配方: {formula}")
    
    def select_random_prescription(self):
        """随机选择一个配方"""
        symptom = self.symptom_combo.currentText()
        formulas = []
        
        if symptom in self.default_therapy_data:
            formulas.extend(self.default_therapy_data[symptom])
        if symptom in self.user_therapy_data:
            formulas.extend(self.user_therapy_data[symptom])
        
        if formulas:
            formula = random.choice(formulas)
            self.current_prescription = formula
            self.current_prescription_label.setText(f"当前配方: {formula} (随机选择)")
        else:
            QMessageBox.warning(self, "警告", "该症状没有可用的配方")
    
    def start_practice(self):
        """开始默念练习"""
        if not self.current_prescription:
            QMessageBox.warning(self, "警告", "请先选择配方")
            return
            
        if not self.is_playing:
            # 过滤掉非数字字符（保留点和空格）
            self.practice_sequence = [char for char in self.current_prescription if char.isdigit() or char in ['.', '·', ' ']]
            self.current_index = 0
            self.is_playing = True
            self.start_btn.setEnabled(False)
            self.pause_btn.setEnabled(True)
            self.stop_btn.setEnabled(True)
            self.progress_bar.setValue(0)
            
            # 获取每个数字显示时间
            self.display_time = float(self.time_per_digit.currentText())
            
            # 计算总时间
            self.total_time = 0
            for char in self.practice_sequence:
                if char.isdigit():
                    self.total_time += self.display_time
                else:
                    self.total_time += self.display_time * 2  # 点号停顿时间加倍
            
            self.remaining_time = self.total_time
            self.timer.start(int(self.display_time * 1000))  # 根据设置的时间更新
            self.update_number()
            
            # 记录开始时间
            self.start_time = datetime.now()
    
    def pause_practice(self):
        """暂停/继续默念练习"""
        if self.is_playing:
            self.timer.stop()
            self.is_playing = False
            self.pause_btn.setText("继续")
        else:
            self.timer.start(int(self.display_time * 1000))
            self.is_playing = True
            self.pause_btn.setText("暂停")
    
    def stop_practice(self):
        """停止默念练习"""
        self.timer.stop()
        self.is_playing = False
        
        if hasattr(self, 'start_time'):
            # 记录练习历史
            end_time = datetime.now()
            duration = (end_time - self.start_time).seconds
            record = {
                "date": end_time.strftime("%Y-%m-%d %H:%M"),
                "symptom": self.symptom_combo.currentText(),
                "prescription": self.current_prescription,
                "duration": duration,
                "status": "完成" if self.current_index >= len(self.practice_sequence) else "中断"
            }
            self.practice_history.append(record)
            self.save_data()
            self.update_history_list()
        
        self.current_number_label.setText("默念已停止")
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("准备开始")
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setText("暂停")
    
    def update_number(self):
        """更新显示的数字"""
        if self.current_index < len(self.practice_sequence):
            char = self.practice_sequence[self.current_index]
            self.current_number_label.setText(char)
            
            # 根据字符类型设置不同的背景色
            if char.isdigit():
                self.current_number_label.setStyleSheet(
                    "background-color: #d4e8d4; font-size: 48px; font-weight: bold; border-radius: 10px; padding: 30px;"
                )
                display_time = self.display_time
            else:
                self.current_number_label.setStyleSheet(
                    "background-color: #f5e8d4; font-size: 48px; font-weight: bold; border-radius: 10px; padding: 30px;"
                )
                display_time = self.display_time * 2  # 点号停顿时间加倍
            
            # 更新进度
            progress = int((self.current_index + 1) / len(self.practice_sequence) * 100)
            self.progress_bar.setValue(progress)
            remaining = len(self.practice_sequence) - self.current_index - 1
            self.progress_bar.setFormat(f"默念进度: {progress}% (剩余: {remaining}个)")
            
            # 移动到下一个字符
            self.current_index += 1
            
            # 设置定时器根据字符类型调整时间
            self.timer.setInterval(int(display_time * 1000))
        else:
            self.stop_practice()
            self.current_number_label.setText("默念完成！")
            self.progress_bar.setValue(100)
            self.progress_bar.setFormat("默念完成")
    
    def add_custom_prescription(self):
        """添加自定义配方"""
        symptom = self.new_symptom_input.text().strip()
        formula = self.new_formula_input.text().strip()
        
        if not symptom or not formula:
            QMessageBox.warning(self, "输入错误", "症状和配方都不能为空")
            return
        
        # 验证配方格式
        if not all(c.isdigit() or c in ['.', '·', ' '] for c in formula):
            QMessageBox.warning(self, "格式错误", "配方只能包含数字、点和空格")
            return
        
        # 添加到自定义配方库
        if symptom not in self.user_therapy_data:
            self.user_therapy_data[symptom] = []
        
        if formula not in self.user_therapy_data[symptom]:
            self.user_therapy_data[symptom].append(formula)
            self.save_data()
            
            # 更新UI
            self.new_symptom_input.clear()
            self.new_formula_input.clear()
            self.update_custom_list()
            
            # 如果当前症状选择的是新添加的症状，更新配方列表
            if self.symptom_combo.currentText() == symptom:
                self.update_prescription_list()
            
            QMessageBox.information(self, "成功", "自定义配方添加成功")
        else:
            QMessageBox.warning(self, "重复", "该症状下已存在相同的配方")
    
    def update_custom_list(self):
        """更新自定义配方列表"""
        self.custom_list.clear()
        
        for symptom, formulas in self.user_therapy_data.items():
            for formula in formulas:
                item = QListWidgetItem(f"{symptom}: {formula}")
                item.setData(Qt.UserRole, (symptom, formula))
                self.custom_list.addItem(item)
    
    def edit_custom_prescription(self):
        """编辑自定义配方"""
        item = self.custom_list.currentItem()
        if not item:
            QMessageBox.warning(self, "选择错误", "请选择一个配方进行编辑")
            return
        
        symptom, formula = item.data(Qt.UserRole)
        
        # 获取新值
        new_symptom, ok1 = QInputDialog.getText(self, "编辑症状", "症状名称:", text=symptom)
        new_formula, ok2 = QInputDialog.getText(self, "编辑配方", "象数配方:", text=formula)
        
        if ok1 and ok2 and new_symptom.strip() and new_formula.strip():
            # 删除旧条目
            self.user_therapy_data[symptom].remove(formula)
            if not self.user_therapy_data[symptom]:
                del self.user_therapy_data[symptom]
            
            # 添加新条目
            if new_symptom not in self.user_therapy_data:
                self.user_therapy_data[new_symptom] = []
            self.user_therapy_data[new_symptom].append(new_formula)
            
            self.save_data()
            self.update_custom_list()
            QMessageBox.information(self, "成功", "配方编辑成功")
    
    def remove_custom_prescription(self):
        """删除自定义配方"""
        item = self.custom_list.currentItem()
        if not item:
            QMessageBox.warning(self, "选择错误", "请选择一个配方进行删除")
            return
        
        symptom, formula = item.data(Qt.UserRole)
        
        reply = QMessageBox.question(self, "确认删除", 
                                    f"确定要删除 '{symptom}' 的配方 '{formula}' 吗？",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.user_therapy_data[symptom].remove(formula)
            if not self.user_therapy_data[symptom]:
                del self.user_therapy_data[symptom]
            
            self.save_data()
            self.update_custom_list()
            QMessageBox.information(self, "成功", "配方已删除")
    
    def import_custom_prescription(self):
        """导入自定义配方"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "导入配方", "", "JSON文件 (*.json);;所有文件 (*)"
        )
        
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    imported_data = json.load(f)
                
                # 合并数据
                for symptom, formulas in imported_data.items():
                    if symptom not in self.user_therapy_data:
                        self.user_therapy_data[symptom] = []
                    
                    for formula in formulas:
                        if formula not in self.user_therapy_data[symptom]:
                            self.user_therapy_data[symptom].append(formula)
                
                self.save_data()
                self.update_custom_list()
                QMessageBox.information(self, "成功", f"成功导入 {len(imported_data)} 个症状的配方")
            except Exception as e:
                QMessageBox.critical(self, "导入错误", f"导入失败: {str(e)}")
    
    def update_history_list(self):
        """更新历史记录列表"""
        self.history_list.clear()
        
        for record in reversed(self.practice_history):
            item = QListWidgetItem()
            icon = QIcon(QPixmap(16, 16))
            if record['status'] == '完成':
                icon = QIcon(QPixmap(16, 16).fill(QColor(0, 128, 0)))
            else:
                icon = QIcon(QPixmap(16, 16).fill(QColor(255, 165, 0)))
            
            item.setIcon(icon)
            item.setText(f"{record['date']} - {record['symptom']}: {record['prescription']} ({record['duration']}秒)")
            item.setData(Qt.UserRole, record)
            self.history_list.addItem(item)
    
    def view_history(self):
        """查看历史记录详情"""
        item = self.history_list.currentItem()
        if not item:
            return
        
        record = item.data(Qt.UserRole)
        details = f"""
            <h2>练习详情</h2>
            <p><b>日期时间:</b> {record['date']}</p>
            <p><b>症状:</b> {record['symptom']}</p>
            <p><b>配方:</b> {record['prescription']}</p>
            <p><b>持续时间:</b> {record['duration']} 秒</p>
            <p><b>状态:</b> {record['status']}</p>
            <h3>配方解析:</h3>
            <p>{self.analyze_prescription(record['prescription'])}</p>
        """
        self.history_details.setHtml(details)
    
    def analyze_prescription(self, prescription):
        """解析配方"""
        analysis = []
        for char in prescription:
            if char.isdigit():
                for bagua, info in self.bagua_info.items():
                    if info['数字'] == char:
                        analysis.append(f"数字 {char} ({bagua}卦): {info['代表']}")
            elif char in ['.', '·']:
                analysis.append("点号: 表示停顿，应稍作停留")
        
        return "<br>".join(analysis) if analysis else "无法解析此配方"
    
    def delete_history(self):
        """删除选中的历史记录"""
        item = self.history_list.currentItem()
        if not item:
            return
        
        record = item.data(Qt.UserRole)
        
        reply = QMessageBox.question(self, "确认删除", 
                                    f"确定要删除 {record['date']} 的记录吗？",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.practice_history.remove(record)
            self.save_data()
            self.update_history_list()
            self.history_details.clear()
    
    def clear_history(self):
        """清空历史记录"""
        if not self.practice_history:
            return
        
        reply = QMessageBox.question(self, "确认清空", 
                                    "确定要清空所有历史记录吗？",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.practice_history = []
            self.save_data()
            self.update_history_list()
            self.history_details.clear()
    
    def export_history(self):
        """导出历史记录"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "导出历史记录", "", "JSON文件 (*.json);;文本文件 (*.txt);;所有文件 (*)"
        )
        
        if filename:
            try:
                if filename.endswith('.txt'):
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write("八卦象数疗法练习历史记录\n")
                        f.write("="*50 + "\n\n")
                        for record in self.practice_history:
                            f.write(f"日期: {record['date']}\n")
                            f.write(f"症状: {record['symptom']}\n")
                            f.write(f"配方: {record['prescription']}\n")
                            f.write(f"持续时间: {record['duration']}秒\n")
                            f.write(f"状态: {record['status']}\n")
                            f.write("-"*50 + "\n")
                else:
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(self.practice_history, f, ensure_ascii=False, indent=2)
                
                QMessageBox.information(self, "成功", "历史记录导出成功")
            except Exception as e:
                QMessageBox.critical(self, "导出错误", f"导出失败: {str(e)}")
    
    def export_all_data(self):
        """导出所有数据"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "导出所有数据", "", "JSON文件 (*.json)"
        )
        
        if filename:
            try:
                data = {
                    "custom_prescriptions": self.user_therapy_data,
                    "practice_history": self.practice_history
                }
                
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                QMessageBox.information(self, "成功", "所有数据导出成功")
            except Exception as e:
                QMessageBox.critical(self, "导出错误", f"导出失败: {str(e)}")
    
    def import_data(self):
        """导入数据"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "导入数据", "", "JSON文件 (*.json)"
        )
        
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 合并数据
                if "custom_prescriptions" in data:
                    for symptom, formulas in data["custom_prescriptions"].items():
                        if symptom not in self.user_therapy_data:
                            self.user_therapy_data[symptom] = []
                        for formula in formulas:
                            if formula not in self.user_therapy_data[symptom]:
                                self.user_therapy_data[symptom].append(formula)
                
                if "practice_history" in data:
                    self.practice_history.extend(data["practice_history"])
                
                self.save_data()
                self.update_custom_list()
                self.update_history_list()
                QMessageBox.information(self, "成功", "数据导入成功")
            except Exception as e:
                QMessageBox.critical(self, "导入错误", f"导入失败: {str(e)}")
    
    def show_about(self):
        """显示关于对话框"""
        about_text = """
            <h2>八卦象数疗法应用</h2>
            <p>版本: 2.0</p>
            <p>作者: DeepSeek AI</p>
            <p>发布日期: 2023-12-15</p>
            
            <h3>功能特点:</h3>
            <ul>
                <li>提供多种常见症状的八卦象数配方</li>
                <li>详细的八卦知识库和学习资料</li>
                <li>交互式默念练习功能</li>
                <li>自定义配方管理</li>
                <li>练习历史记录</li>
                <li>数据导入导出功能</li>
            </ul>
            
            <p>本软件基于PyQt5开发，仅供学习和研究使用。</p>
            <p>八卦象数疗法作为辅助疗法，不能替代正规医疗。</p>
        """
        QMessageBox.about(self, "关于", about_text)
    
    def closeEvent(self, event):
        """关闭应用时保存数据"""
        self.save_data()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create("Fusion"))
    window = BaguaTherapyApp()
    window.show()
    sys.exit(app.exec_())