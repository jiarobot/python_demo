import sys
import math
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QTextEdit, 
                             QTabWidget, QGroupBox, QSpinBox, QComboBox,
                             QTableWidget, QTableWidgetItem, QGraphicsView,
                             QGraphicsScene, QGraphicsItem, QGraphicsEllipseItem,
                             QGraphicsTextItem, QSplitter, QMessageBox)
from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtGui import QFont, QPen, QBrush, QColor, QPainter

class HetuLuoshuSystem:
    """河图洛书核心算法类"""
    
    def __init__(self):
        self.hetu_numbers = {
            'north': [1, 6],   # 一六共宗为水居北
            'south': [2, 7],   # 二七同道为火居南
            'east': [3, 8],    # 三八为朋为木居东
            'west': [4, 9],    # 四九为友为金居西
            'center': [5, 10]  # 五十同途为土居中
        }
        
        self.luoshu_numbers = [
            [4, 9, 2],
            [3, 5, 7],
            [8, 1, 6]
        ]
        
        self.wuxing = {
            'wood': {'color': 'green', 'direction': 'east', 'numbers': [3, 8]},
            'fire': {'color': 'red', 'direction': 'south', 'numbers': [2, 7]},
            'earth': {'color': 'yellow', 'direction': 'center', 'numbers': [5, 10]},
            'metal': {'color': 'white', 'direction': 'west', 'numbers': [4, 9]},
            'water': {'color': 'black', 'direction': 'north', 'numbers': [1, 6]}
        }
    
    def get_hetu_sum(self, direction):
        """计算河图某方位的数字和"""
        return sum(self.hetu_numbers[direction])
    
    def get_luoshu_magic_sum(self):
        """计算洛书魔方和"""
        return 15  # 任何行、列、对角线的和都是15
    
    def get_wuxing_by_number(self, number):
        """根据数字获取五行属性"""
        for element, info in self.wuxing.items():
            if number in info['numbers']:
                return element
        return None
    
    def generate_hexagram(self, numbers):
        """根据数字生成卦象（简化版）"""
        # 这里简化处理，实际卦象生成更复杂
        if len(numbers) != 6:
            return "需要6个数字生成卦象"
        
        hexagram = ""
        for num in numbers:
            if num % 2 == 0:
                hexagram += "--"  # 阴爻
            else:
                hexagram += "-"   # 阳爻
            hexagram += "\n"
        
        return hexagram
    
    def calculate_bagua_positions(self):
        """计算八卦方位"""
        # 先天八卦方位
        bagua = {
            '乾': {'direction': 'south', 'number': 1},
            '兑': {'direction': 'southeast', 'number': 2},
            '离': {'direction': 'east', 'number': 3},
            '震': {'direction': 'northeast', 'number': 4},
            '巽': {'direction': 'southwest', 'number': 5},
            '坎': {'direction': 'west', 'number': 6},
            '艮': {'direction': 'northwest', 'number': 7},
            '坤': {'direction': 'north', 'number': 8}
        }
        return bagua


class HetuGraphicsView(QGraphicsView):
    """河图可视化组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.system = HetuLuoshuSystem()
        self.draw_hetu()
    
    def draw_hetu(self):
        """绘制河图"""
        self.scene.clear()
        
        # 设置场景大小
        self.scene.setSceneRect(0, 0, 400, 400)
        
        # 绘制中心圆
        center = QPointF(200, 200)
        center_circle = QGraphicsEllipseItem(QRectF(180, 180, 40, 40))
        center_circle.setBrush(QBrush(QColor(255, 255, 0)))  # 黄色代表土
        center_circle.setPen(QPen(Qt.black, 2))
        self.scene.addItem(center_circle)
        
        # 添加中心数字
        center_text = QGraphicsTextItem("5\n10")
        center_text.setFont(QFont("Arial", 10, QFont.Bold))
        center_text.setPos(190, 190)
        self.scene.addItem(center_text)
        
        # 绘制四个方向的圆和数字
        positions = [
            (200, 100, "1\n6", QColor(0, 0, 255)),  # 北 - 水 - 蓝色
            (200, 300, "2\n7", QColor(255, 0, 0)),  # 南 - 火 - 红色
            (100, 200, "3\n8", QColor(0, 255, 0)),  # 东 - 木 - 绿色
            (300, 200, "4\n9", QColor(255, 255, 255))  # 西 - 金 - 白色
        ]
        
        for x, y, text, color in positions:
            circle = QGraphicsEllipseItem(QRectF(x-20, y-20, 40, 40))
            circle.setBrush(QBrush(color))
            circle.setPen(QPen(Qt.black, 2))
            self.scene.addItem(circle)
            
            text_item = QGraphicsTextItem(text)
            text_item.setFont(QFont("Arial", 10, QFont.Bold))
            text_item.setPos(x-15, y-15)
            self.scene.addItem(text_item)
        
        # 绘制连接线
        lines = [
            (200, 100, 200, 180),  # 北到中心
            (200, 220, 200, 300),  # 中心到南
            (100, 200, 180, 200),  # 东到中心
            (220, 200, 300, 200)   # 中心到西
        ]
        
        for x1, y1, x2, y2 in lines:
            line = self.scene.addLine(x1, y1, x2, y2, QPen(Qt.black, 2))
        
        # 添加方位标签
        directions = [
            (200, 50, "北 (水)"),
            (200, 350, "南 (火)"),
            (50, 200, "东 (木)"),
            (350, 200, "西 (金)"),
            (200, 200, "中 (土)")
        ]
        
        for x, y, text in directions:
            label = QGraphicsTextItem(text)
            label.setFont(QFont("Arial", 12, QFont.Bold))
            label.setPos(x-30, y-10)
            self.scene.addItem(label)


class LuoshuGraphicsView(QGraphicsView):
    """洛书可视化组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.system = HetuLuoshuSystem()
        self.draw_luoshu()
    
    def draw_luoshu(self):
        """绘制洛书"""
        self.scene.clear()
        self.scene.setSceneRect(0, 0, 400, 400)
        
        # 绘制3x3网格
        cell_size = 100
        for i in range(4):
            # 垂直线
            self.scene.addLine(i * cell_size + 50, 50, i * cell_size + 50, 350, QPen(Qt.black, 2))
            # 水平线
            self.scene.addLine(50, i * cell_size + 50, 350, i * cell_size + 50, QPen(Qt.black, 2))
        
        # 填充数字
        luoshu = self.system.luoshu_numbers
        colors = [QColor(255, 255, 255), QColor(255, 255, 0), QColor(0, 0, 255)]  # 白,黄,蓝
        
        for i in range(3):
            for j in range(3):
                x = j * cell_size + 50
                y = i * cell_size + 50
                
                # 绘制背景圆
                circle = QGraphicsEllipseItem(QRectF(x+25, y+25, 50, 50))
                color_idx = (i + j) % len(colors)
                circle.setBrush(QBrush(colors[color_idx]))
                circle.setPen(QPen(Qt.black, 2))
                self.scene.addItem(circle)
                
                # 添加数字
                number = luoshu[i][j]
                text_item = QGraphicsTextItem(str(number))
                text_item.setFont(QFont("Arial", 16, QFont.Bold))
                text_item.setPos(x+40, y+40)
                self.scene.addItem(text_item)
        
        # 添加标题
        title = QGraphicsTextItem("洛书 - 戴九履一, 左三右七, 二四为肩, 六八为足, 五居中央")
        title.setFont(QFont("Arial", 12))
        title.setPos(50, 10)
        self.scene.addItem(title)


class AnalysisWidget(QWidget):
    """分析工具组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.system = HetuLuoshuSystem()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 输入区域
        input_group = QGroupBox("数字分析")
        input_layout = QHBoxLayout()
        
        self.number_input = QSpinBox()
        self.number_input.setRange(1, 10)
        self.number_input.setValue(5)
        
        self.analyze_btn = QPushButton("分析数字")
        self.analyze_btn.clicked.connect(self.analyze_number)
        
        input_layout.addWidget(QLabel("输入数字 (1-10):"))
        input_layout.addWidget(self.number_input)
        input_layout.addWidget(self.analyze_btn)
        input_layout.addStretch()
        input_group.setLayout(input_layout)
        
        # 结果显示区域
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        
        # 五行关系表
        table_group = QGroupBox("五行关系")
        table_layout = QVBoxLayout()
        
        self.wuxing_table = QTableWidget()
        self.wuxing_table.setRowCount(5)
        self.wuxing_table.setColumnCount(5)
        self.wuxing_table.setHorizontalHeaderLabels(["木", "火", "土", "金", "水"])
        self.wuxing_table.setVerticalHeaderLabels(["木", "火", "土", "金", "水"])
        
        # 填充五行关系
        relationships = [
            ["同", "生", "克", "被克", "被生"],
            ["被生", "同", "生", "克", "被克"],
            ["被克", "被生", "同", "生", "克"],
            ["克", "被克", "被生", "同", "生"],
            ["生", "克", "被克", "被生", "同"]
        ]
        
        for i in range(5):
            for j in range(5):
                item = QTableWidgetItem(relationships[i][j])
                self.wuxing_table.setItem(i, j, item)
        
        table_layout.addWidget(self.wuxing_table)
        table_group.setLayout(table_layout)
        
        # 添加到主布局
        layout.addWidget(input_group)
        layout.addWidget(self.result_text)
        layout.addWidget(table_group)
        
        self.setLayout(layout)
    
    def analyze_number(self):
        """分析数字的五行属性"""
        number = self.number_input.value()
        element = self.system.get_wuxing_by_number(number)
        
        if element:
            info = self.system.wuxing[element]
            result = f"数字 {number} 的五行属性:\n\n"
            result += f"五行: {element}\n"
            result += f"颜色: {info['color']}\n"
            result += f"方位: {info['direction']}\n"
            result += f"同组数字: {info['numbers']}\n\n"
            
            # 添加相生相克关系
            result += "五行关系:\n"
            if element == 'wood':
                result += "木生火，木克土，被金克，被水生"
            elif element == 'fire':
                result += "火生土，火克金，被水克，被木生"
            elif element == 'earth':
                result += "土生金，土克水，被木克，被火生"
            elif element == 'metal':
                result += "金生水，金克木，被火克，被土生"
            elif element == 'water':
                result += "水生木，水克火，被土克，被金生"
        else:
            result = f"数字 {number} 没有对应的五行属性"
        
        self.result_text.setText(result)


class HexagramWidget(QWidget):
    """卦象生成组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.system = HetuLuoshuSystem()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 卦象生成区域
        hexagram_group = QGroupBox("卦象生成")
        hexagram_layout = QVBoxLayout()
        
        # 数字输入区域
        input_layout = QHBoxLayout()
        self.number_inputs = []
        
        for i in range(6):
            spinbox = QSpinBox()
            spinbox.setRange(1, 10)
            spinbox.setValue(i+1)
            self.number_inputs.append(spinbox)
            input_layout.addWidget(spinbox)
        
        self.generate_btn = QPushButton("生成卦象")
        self.generate_btn.clicked.connect(self.generate_hexagram)
        input_layout.addWidget(self.generate_btn)
        
        hexagram_layout.addLayout(input_layout)
        
        # 卦象显示区域
        self.hexagram_display = QTextEdit()
        self.hexagram_display.setReadOnly(True)
        self.hexagram_display.setFont(QFont("Arial", 16))
        hexagram_layout.addWidget(self.hexagram_display)
        
        hexagram_group.setLayout(hexagram_layout)
        
        # 八卦方位显示
        bagua_group = QGroupBox("八卦方位")
        bagua_layout = QVBoxLayout()
        
        self.bagua_text = QTextEdit()
        self.bagua_text.setReadOnly(True)
        self.show_bagua_positions()
        
        bagua_layout.addWidget(self.bagua_text)
        bagua_group.setLayout(bagua_layout)
        
        layout.addWidget(hexagram_group)
        layout.addWidget(bagua_group)
        
        self.setLayout(layout)
    
    def generate_hexagram(self):
        """生成卦象"""
        numbers = [sb.value() for sb in self.number_inputs]
        hexagram = self.system.generate_hexagram(numbers)
        self.hexagram_display.setText(hexagram)
    
    def show_bagua_positions(self):
        """显示八卦方位"""
        bagua = self.system.calculate_bagua_positions()
        text = "先天八卦方位:\n\n"
        
        for name, info in bagua.items():
            text += f"{name}卦: 方位-{info['direction']}, 数-{info['number']}\n"
        
        self.bagua_text.setText(text)


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.system = HetuLuoshuSystem()
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("河图洛书系统高级工具库")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中央部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧标签页（图形显示）
        left_tabs = QTabWidget()
        
        # 河图标签页
        hetu_tab = QWidget()
        hetu_layout = QVBoxLayout(hetu_tab)
        hetu_view = HetuGraphicsView()
        hetu_layout.addWidget(hetu_view)
        
        # 添加河图说明
        hetu_desc = QTextEdit()
        hetu_desc.setReadOnly(True)
        hetu_desc.setText("河图说明:\n\n"
                         "一六共宗为水居北\n"
                         "二七同道为火居南\n"
                         "三八为朋为木居东\n"
                         "四九为友为金居西\n"
                         "五十同途为土居中央")
        hetu_layout.addWidget(hetu_desc)
        
        left_tabs.addTab(hetu_tab, "河图")
        
        # 洛书标签页
        luoshu_tab = QWidget()
        luoshu_layout = QVBoxLayout(luoshu_tab)
        luoshu_view = LuoshuGraphicsView()
        luoshu_layout.addWidget(luoshu_view)
        
        # 添加洛书说明
        luoshu_desc = QTextEdit()
        luoshu_desc.setReadOnly(True)
        luoshu_desc.setText("洛书说明:\n\n"
                           "戴九履一\n"
                           "左三右七\n"
                           "二四为肩\n"
                           "六八为足\n"
                           "五居中央")
        luoshu_layout.addWidget(luoshu_desc)
        
        left_tabs.addTab(luoshu_tab, "洛书")
        
        # 右侧标签页（工具）
        right_tabs = QTabWidget()
        
        # 分析工具标签页
        analysis_tab = AnalysisWidget()
        right_tabs.addTab(analysis_tab, "数字分析")
        
        # 卦象工具标签页
        hexagram_tab = HexagramWidget()
        right_tabs.addTab(hexagram_tab, "卦象生成")
        
        # 添加到分割器
        splitter.addWidget(left_tabs)
        splitter.addWidget(right_tabs)
        splitter.setSizes([600, 600])
        
        main_layout.addWidget(splitter)
        
        # 添加菜单栏
        self.create_menu()
    
    def create_menu(self):
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        exit_action = file_menu.addAction('退出')
        exit_action.triggered.connect(self.close)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        
        about_action = help_menu.addAction('关于')
        about_action.triggered.connect(self.show_about)
    
    def show_about(self):
        QMessageBox.about(self, "关于河图洛书系统",
                         "河图洛书系统高级工具库\n\n"
                         "基于PyQt5开发的河图洛书分析工具，"
                         "包含可视化、数字分析、五行计算和卦象生成等功能。")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())