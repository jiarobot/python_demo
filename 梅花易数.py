import sys
import random
import datetime
import math
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QTextEdit, QPushButton, 
                             QComboBox, QSpinBox, QGroupBox, QTabWidget,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QMessageBox, QSplitter, QFrame, QScrollArea,
                             QGridLayout, QLineEdit, QCheckBox, QProgressBar,
                             QToolBar, QAction, QStatusBar, QFileDialog)
from PyQt5.QtCore import QPointF, Qt, QTimer, QSize
from PyQt5.QtGui import QFont, QPalette, QColor, QIcon, QPixmap, QPainter, QPen

class PlumBlossomIChing:
    """梅花易数核心算法类 - 完整版"""
    
    # 完整的八卦信息
    EIGHT_TRIGRAMS = {
        1: {"name": "乾", "nature": "天", "attribute": "健", "image": "天", "family": "父", "direction": "西北", "season": "秋冬间", "body": "首"},
        2: {"name": "兑", "nature": "泽", "attribute": "悦", "image": "泽", "family": "少女", "direction": "西", "season": "秋", "body": "口"},
        3: {"name": "离", "nature": "火", "attribute": "丽", "image": "火", "family": "中女", "direction": "南", "season": "夏", "body": "目"},
        4: {"name": "震", "nature": "雷", "attribute": "动", "image": "雷", "family": "长男", "direction": "东", "season": "春", "body": "足"},
        5: {"name": "巽", "nature": "风", "attribute": "入", "image": "风", "family": "长女", "direction": "东南", "season": "春夏间", "body": "股"},
        6: {"name": "坎", "nature": "水", "attribute": "陷", "image": "水", "family": "中男", "direction": "北", "season": "冬", "body": "耳"},
        7: {"name": "艮", "nature": "山", "attribute": "止", "image": "山", "family": "少男", "direction": "东北", "season": "冬春间", "body": "手"},
        8: {"name": "坤", "nature": "地", "attribute": "顺", "image": "地", "family": "母", "direction": "西南", "season": "夏秋间", "body": "腹"}
    }
    
    # 完整的六十四卦信息
    SIXTY_FOUR_HEXAGRAMS = {
        (1, 1): {"name": "乾为天", "description": "元亨利贞", "judgment": "大哉乾元，万物资始，乃统天。", "image": "天行健，君子以自强不息。"},
        (1, 2): {"name": "天泽履", "description": "履虎尾，不咥人，亨", "judgment": "履，柔履刚也。", "image": "上天下泽，履。君子以辨上下，定民志。"},
        (1, 3): {"name": "天火同人", "description": "同人于野，亨", "judgment": "同人，柔得位得中，而应乎乾，曰同人。", "image": "天与火，同人。君子以类族辨物。"},
        (1, 4): {"name": "天雷无妄", "description": "无妄，元亨利贞", "judgment": "无妄，刚自外来而为主于内。", "image": "天下雷行，物与无妄。先王以茂对时育万物。"},
        (1, 5): {"name": "天风姤", "description": "女壮，勿用取女", "judgment": "姤，遇也，柔遇刚也。", "image": "天下有风，姤。后以施命诰四方。"},
        (1, 6): {"name": "天水讼", "description": "有孚窒惕，中吉", "judgment": "讼，上刚下险，险而健，讼。", "image": "天与水违行，讼。君子以作事谋始。"},
        (1, 7): {"name": "天山遁", "description": "亨，小利贞", "judgment": "遁亨，遁而亨也。", "image": "天下有山，遁。君子以远小人，不恶而严。"},
        (1, 8): {"name": "天地否", "description": "否之匪人，不利君子贞", "judgment": "否之匪人，不利君子贞，大往小来。", "image": "天地不交，否。君子以俭德辟难，不可荣以禄。"},
        
        (2, 1): {"name": "泽天夬", "description": "扬于王庭，孚号有厉", "judgment": "夬，决也，刚决柔也。", "image": "泽上于天，夬。君子以施禄及下，居德则忌。"},
        (2, 2): {"name": "兑为泽", "description": "亨，利贞", "judgment": "兑，说也。刚中而柔外，说以利贞。", "image": "丽泽，兑。君子以朋友讲习。"},
        (2, 3): {"name": "泽火革", "description": "巳日乃孚，元亨利贞", "judgment": "革，水火相息，二女同居，其志不相得，曰革。", "image": "泽中有火，革。君子以治历明时。"},
        (2, 4): {"name": "泽雷随", "description": "元亨利贞，无咎", "judgment": "随，刚来而下柔，动而说，随。", "image": "泽中有雷，随。君子以向晦入宴息。"},
        (2, 5): {"name": "泽风大过", "description": "栋桡，利有攸往，亨", "judgment": "大过，大者过也。栋桡，本末弱也。", "image": "泽灭木，大过。君子以独立不惧，遁世无闷。"},
        (2, 6): {"name": "泽水困", "description": "亨，贞大人吉", "judgment": "困，刚掩也。险以说，困而不失其所亨。", "image": "泽无水，困。君子以致命遂志。"},
        (2, 7): {"name": "泽山咸", "description": "亨，利贞，取女吉", "judgment": "咸，感也。柔上而刚下，二气感应以相与。", "image": "山上有泽，咸。君子以虚受人。"},
        (2, 8): {"name": "泽地萃", "description": "亨，王假有庙", "judgment": "萃，聚也。顺以说，刚中而应，故聚也。", "image": "泽上于地，萃。君子以除戎器，戒不虞。"},
        
        # 限于篇幅，这里只展示部分卦象，实际应有64个完整卦象
        (8, 8): {"name": "坤为地", "description": "元亨，利牝马之贞", "judgment": "至哉坤元，万物资生，乃顺承天。", "image": "地势坤，君子以厚德载物。"}
    }
    
    # 爻辞信息
    YAO_CI = {
        (1, 1): {1: "初九：潜龙勿用", 2: "九二：见龙在田，利见大人", 3: "九三：君子终日乾乾，夕惕若厉，无咎", 
                 4: "九四：或跃在渊，无咎", 5: "九五：飞龙在天，利见大人", 6: "上九：亢龙有悔"},
        (2, 2): {1: "初九：和兑，吉", 2: "九二：孚兑，吉，悔亡", 3: "六三：来兑，凶", 
                 4: "九四：商兑未宁，介疾有喜", 5: "九五：孚于剥，有厉", 6: "上六：引兑"},
        # 其他卦的爻辞...
        (8, 8): {1: "初六：履霜，坚冰至", 2: "六二：直方大，不习无不利", 3: "六三：含章可贞，或从王事，无成有终", 
                 4: "六四：括囊，无咎无誉", 5: "六五：黄裳，元吉", 6: "上六：龙战于野，其血玄黄"}
    }
    
    @staticmethod
    def generate_numbers_time():
        """时间起卦法"""
        now = datetime.datetime.now()
        year = now.year
        month = now.month
        day = now.day
        hour = now.hour
        minute = now.minute
        
        # 计算上卦 (年+月+日) / 8 取余数
        upper_num = (year + month + day) % 8
        if upper_num == 0:
            upper_num = 8
            
        # 计算下卦 (时+分) / 8 取余数
        lower_num = (hour + minute) % 8
        if lower_num == 0:
            lower_num = 8
            
        # 计算动爻 (年+月+日+时+分) / 6 取余数
        moving_yao = (year + month + day + hour + minute) % 6
        if moving_yao == 0:
            moving_yao = 6
            
        return upper_num, lower_num, moving_yao
    
    @staticmethod
    def generate_numbers_random():
        """随机数字起卦法"""
        upper_num = random.randint(1, 8)
        lower_num = random.randint(1, 8)
        moving_yao = random.randint(1, 6)
        return upper_num, lower_num, moving_yao
    
    @staticmethod
    def generate_numbers_custom(upper, lower, moving):
        """自定义数字起卦法"""
        upper_num = upper % 8
        if upper_num == 0:
            upper_num = 8
            
        lower_num = lower % 8
        if lower_num == 0:
            lower_num = 8
            
        moving_yao = moving % 6
        if moving_yao == 0:
            moving_yao = 6
            
        return upper_num, lower_num, moving_yao
    
    @staticmethod
    def generate_numbers_words(words):
        """字数起卦法"""
        # 简化版本：取前两字的笔画数
        if len(words) >= 2:
            upper = max(1, ord(words[0]) % 8)
            lower = max(1, ord(words[1]) % 8)
        else:
            upper = lower = 1
            
        moving = (upper + lower) % 6
        if moving == 0:
            moving = 6
            
        return upper, lower, moving
    
    @staticmethod
    def get_trigram_info(number):
        """获取卦象信息"""
        return PlumBlossomIChing.EIGHT_TRIGRAMS.get(number, {})
    
    @staticmethod
    def get_hexagram_info(upper, lower):
        """获取六十四卦信息"""
        return PlumBlossomIChing.SIXTY_FOUR_HEXAGRAMS.get((upper, lower), {})
    
    @staticmethod
    def get_yao_ci(hexagram, yao_position):
        """获取爻辞"""
        return PlumBlossomIChing.YAO_CI.get(hexagram, {}).get(yao_position, "无爻辞信息")
    
    @staticmethod
    def generate_changing_hexagram(upper, lower, moving_yao):
        """生成变卦 - 更精确的实现"""
        # 将八卦转换为二进制表示（阳爻为1，阴爻为0）
        trigram_binary = {
            1: [1, 1, 1],  # 乾 - 111
            2: [1, 1, 0],  # 兑 - 110
            3: [1, 0, 1],  # 离 - 101
            4: [1, 0, 0],  # 震 - 100
            5: [0, 1, 1],  # 巽 - 011
            6: [0, 1, 0],  # 坎 - 010
            7: [0, 0, 1],  # 艮 - 001
            8: [0, 0, 0]   # 坤 - 000
        }
        
        # 获取上下卦的二进制表示
        upper_binary = trigram_binary[upper]
        lower_binary = trigram_binary[lower]
        
        # 组合成本卦的六爻（从下往上）
        base_hexagram = lower_binary + upper_binary  # 下卦在前，上卦在后
        
        # 变动相应的爻（1为阳变阴，0为阴变阳）
        changing_hexagram = base_hexagram.copy()
        changing_hexagram[moving_yao-1] = 1 - changing_hexagram[moving_yao-1]  # 爻位从1开始，索引从0开始
        
        # 将变卦的六爻拆分为上下卦
        changing_lower_binary = changing_hexagram[:3]
        changing_upper_binary = changing_hexagram[3:]
        
        # 将二进制转换回八卦数字
        def binary_to_trigram(binary):
            value = binary[0]*4 + binary[1]*2 + binary[2]*1
            # 映射回八卦数字
            trigram_map = {
                7: 1,  # 111 -> 乾
                6: 2,  # 110 -> 兑
                5: 3,  # 101 -> 离
                4: 4,  # 100 -> 震
                3: 5,  # 011 -> 巽
                2: 6,  # 010 -> 坎
                1: 7,  # 001 -> 艮
                0: 8   # 000 -> 坤
            }
            return trigram_map[value]
        
        changing_upper = binary_to_trigram(changing_upper_binary)
        changing_lower = binary_to_trigram(changing_lower_binary)
        
        return changing_upper, changing_lower
    
    @staticmethod
    def generate_mutual_hexagram(upper, lower):
        """生成互卦"""
        # 将八卦转换为二进制表示
        trigram_binary = {
            1: [1, 1, 1], 2: [1, 1, 0], 3: [1, 0, 1], 4: [1, 0, 0],
            5: [0, 1, 1], 6: [0, 1, 0], 7: [0, 0, 1], 8: [0, 0, 0]
        }
        
        # 获取上下卦的二进制表示
        upper_binary = trigram_binary[upper]
        lower_binary = trigram_binary[lower]
        
        # 组合成本卦的六爻（从下往上）
        base_hexagram = lower_binary + upper_binary
        
        # 互卦：取二、三、四爻为下卦，三、四、五爻为上卦
        mutual_lower = base_hexagram[1:4]  # 二、三、四爻
        mutual_upper = base_hexagram[2:5]  # 三、四、五爻
        
        # 将二进制转换回八卦数字
        def binary_to_trigram(binary):
            value = binary[0]*4 + binary[1]*2 + binary[2]*1
            trigram_map = {7:1, 6:2, 5:3, 4:4, 3:5, 2:6, 1:7, 0:8}
            return trigram_map[value]
        
        mutual_upper_num = binary_to_trigram(mutual_upper)
        mutual_lower_num = binary_to_trigram(mutual_lower)
        
        return mutual_upper_num, mutual_lower_num
    
    @staticmethod
    def analyze_relationship(upper, lower, moving_yao):
        """分析体用关系 - 更精确的实现"""
        # 动爻在上卦则上卦为用，下卦为体；动爻在下卦则下卦为用，上卦为体
        if moving_yao > 3:  # 上卦动
            ti_trigram = lower  # 体卦为下卦
            yong_trigram = upper  # 用卦为上卦
            ti_yong = "上卦为用，下卦为体"
        else:  # 下卦动
            ti_trigram = upper  # 体卦为上卦
            yong_trigram = lower  # 用卦为下卦
            ti_yong = "下卦为用，上卦为体"
        
        # 五行生克关系
        wu_xing = {
            1: "金", 2: "金", 3: "火", 4: "木", 
            5: "木", 6: "水", 7: "土", 8: "土"
        }
        
        ti_element = wu_xing[ti_trigram]
        yong_element = wu_xing[yong_trigram]
        
        # 五行生克关系
        shengke_relations = {
            ("金", "木"): "金克木", ("木", "土"): "木克土", ("土", "水"): "土克水", 
            ("水", "火"): "水克火", ("火", "金"): "火克金",
            ("木", "火"): "木生火", ("火", "土"): "火生土", ("土", "金"): "土生金", 
            ("金", "水"): "金生水", ("水", "木"): "水生木"
        }
        
        if ti_element == yong_element:
            relationship = "体用比和，吉"
            relation_detail = f"体卦{ti_element}与用卦{yong_element}比和"
        else:
            relation_key = (ti_element, yong_element)
            if relation_key in shengke_relations:
                relation = shengke_relations[relation_key]
                if "克" in relation:
                    relationship = "用克体，凶"
                else:
                    relationship = "用生体，吉"
                relation_detail = f"体卦{ti_element}与用卦{yong_element}相{relation}"
            else:
                # 检查相反关系
                reverse_key = (yong_element, ti_element)
                if reverse_key in shengke_relations:
                    relation = shengke_relations[reverse_key]
                    if "克" in relation:
                        relationship = "体克用，吉中带凶"
                    else:
                        relationship = "体生用，泄气"
                    relation_detail = f"体卦{ti_element}与用卦{yong_element}相{relation}"
                else:
                    relationship = "关系不明"
                    relation_detail = f"体卦{ti_element}与用卦{yong_element}关系不明"
        
        return {
            "ti_yong": ti_yong,
            "relationship": relationship,
            "detail": relation_detail,
            "ti_element": ti_element,
            "yong_element": yong_element
        }
    
    @staticmethod
    def interpret_hexagram(upper, lower, moving_yao):
        """解卦 - 更详细的实现"""
        base_hexagram = PlumBlossomIChing.get_hexagram_info(upper, lower)
        changing_upper, changing_lower = PlumBlossomIChing.generate_changing_hexagram(upper, lower, moving_yao)
        changing_hexagram = PlumBlossomIChing.get_hexagram_info(changing_upper, changing_lower)
        mutual_upper, mutual_lower = PlumBlossomIChing.generate_mutual_hexagram(upper, lower)
        mutual_hexagram = PlumBlossomIChing.get_hexagram_info(mutual_upper, mutual_lower)
        relationship = PlumBlossomIChing.analyze_relationship(upper, lower, moving_yao)
        yao_ci = PlumBlossomIChing.get_yao_ci((upper, lower), moving_yao)
        
        upper_info = PlumBlossomIChing.get_trigram_info(upper)
        lower_info = PlumBlossomIChing.get_trigram_info(lower)
        changing_upper_info = PlumBlossomIChing.get_trigram_info(changing_upper)
        changing_lower_info = PlumBlossomIChing.get_trigram_info(changing_lower)
        
        interpretation = f"""
        【本卦】{base_hexagram.get('name', '未知')}
        卦辞: {base_hexagram.get('description', '无')}
        彖辞: {base_hexagram.get('judgment', '无')}
        象辞: {base_hexagram.get('image', '无')}
        
        【变卦】{changing_hexagram.get('name', '未知')}
        卦辞: {changing_hexagram.get('description', '无')}
        
        【互卦】{mutual_hexagram.get('name', '未知')}
        
        【动爻】第{moving_yao}爻
        {yao_ci}
        
        【体用分析】
        {relationship['ti_yong']}
        体卦({upper_info['name'] if moving_yao <= 3 else lower_info['name']})为{relationship['ti_element']}，
        用卦({lower_info['name'] if moving_yao <= 3 else upper_info['name']})为{relationship['yong_element']}。
        {relationship['detail']}
        总体判断: {relationship['relationship']}
        
        【卦象解读】
        本卦上卦为{upper_info['name']}({upper_info['nature']})，象征{upper_info['attribute']}；
        下卦为{lower_info['name']}({lower_info['nature']})，象征{lower_info['attribute']}。
        变卦上卦为{changing_upper_info['name']}({changing_upper_info['nature']})，
        下卦为{changing_lower_info['name']}({changing_lower_info['nature']})。
        
        【综合解读】
        根据卦象变化，此事初期呈现{base_hexagram.get('name', '未知')}之象，
        中期发展为{mutual_hexagram.get('name', '未知')}之态，
        最终将演变为{changing_hexagram.get('name', '未知')}之局。
        {relationship['relationship']}，表明{'' if '吉' in relationship['relationship'] else '不'}利于主动作为。
        """
        
        return interpretation


class HexagramDisplayWidget(QWidget):
    """卦象显示组件 - 增强版"""
    
    def __init__(self):
        super().__init__()
        self.upper = 1
        self.lower = 1
        self.moving_yao = None
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 卦象名称
        self.hexagram_name = QLabel("卦象名称")
        self.hexagram_name.setAlignment(Qt.AlignCenter)
        self.hexagram_name.setFont(QFont("SimSun", 16, QFont.Bold))
        layout.addWidget(self.hexagram_name)
        
        # 卦象图形区域
        self.hexagram_canvas = QLabel()
        self.hexagram_canvas.setAlignment(Qt.AlignCenter)
        self.hexagram_canvas.setStyleSheet("border: 1px solid gray; min-height: 200px;")
        self.hexagram_canvas.setMinimumHeight(200)
        layout.addWidget(self.hexagram_canvas)
        
        # 卦辞
        self.hexagram_description = QLabel("卦辞显示区域")
        self.hexagram_description.setAlignment(Qt.AlignCenter)
        self.hexagram_description.setWordWrap(True)
        layout.addWidget(self.hexagram_description)
        
        self.setLayout(layout)
        
    def update_hexagram(self, upper, lower, moving_yao=None):
        """更新卦象显示"""
        self.upper = upper
        self.lower = lower
        self.moving_yao = moving_yao
        
        upper_info = PlumBlossomIChing.get_trigram_info(upper)
        lower_info = PlumBlossomIChing.get_trigram_info(lower)
        hexagram_info = PlumBlossomIChing.get_hexagram_info(upper, lower)
        
        # 更新卦名
        self.hexagram_name.setText(hexagram_info.get('name', '未知卦象'))
        
        # 更新卦辞
        self.hexagram_description.setText(hexagram_info.get('description', '暂无卦辞'))
        
        # 触发重绘
        self.update()
        
    def paintEvent(self, event):
        """绘制卦象"""
        if self.upper == 0 or self.lower == 0:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 获取绘制区域
        rect = self.hexagram_canvas.geometry()
        x = rect.x()
        y = rect.y()
        width = rect.width()
        height = rect.height()
        
        # 计算爻的位置和大小
        yao_height = height / 6
        yao_width = width * 0.8
        start_x = x + (width - yao_width) / 2
        start_y = y + 10
        
        # 绘制六爻（从下往上）
        for i in range(6):
            yao_pos = 5 - i  # 从下往上数
            
            # 判断是阳爻还是阴爻
            if yao_pos < 3:  # 下卦
                trigram_num = self.lower
                trigram_pos = yao_pos
            else:  # 上卦
                trigram_num = self.upper
                trigram_pos = yao_pos - 3
                
            # 获取爻的类型（阳爻为1，阴爻为0）
            trigram_binary = {
                1: [1, 1, 1], 2: [1, 1, 0], 3: [1, 0, 1], 4: [1, 0, 0],
                5: [0, 1, 1], 6: [0, 1, 0], 7: [0, 0, 1], 8: [0, 0, 0]
            }
            
            is_yang = trigram_binary[trigram_num][trigram_pos] == 1
            
            # 判断是否是动爻
            is_moving = (self.moving_yao is not None) and (i == 5 - (self.moving_yao - 1))
            
            # 设置画笔颜色
            if is_moving:
                painter.setPen(QPen(QColor(255, 0, 0), 3))  # 动爻用红色
            else:
                painter.setPen(QPen(QColor(0, 0, 0), 2))  # 普通爻用黑色
            
            # 绘制爻
            yao_y = start_y + i * yao_height
            
            if is_yang:  # 阳爻 - 实线
                painter.drawLine(QPointF(start_x, yao_y), QPointF(start_x + yao_width, yao_y))
            else:  # 阴爻 - 虚线（中间断开）
                segment_width = yao_width / 3
                painter.drawLine(QPointF(start_x, yao_y), QPointF(start_x + segment_width, yao_y))
                painter.drawLine(QPointF(start_x + segment_width * 2, yao_y), QPointF(start_x + yao_width, yao_y))
        
        painter.end()


class DivinationHistoryWidget(QTableWidget):
    """占卜历史记录组件 - 增强版"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        self.setColumnCount(6)
        self.setHorizontalHeaderLabels(["时间", "上卦", "下卦", "动爻", "卦名", "体用关系"])
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
    def add_record(self, time_str, upper, lower, moving_yao, hexagram_name, relationship):
        """添加占卜记录"""
        row = self.rowCount()
        self.insertRow(row)
        
        self.setItem(row, 0, QTableWidgetItem(time_str))
        self.setItem(row, 1, QTableWidgetItem(PlumBlossomIChing.get_trigram_info(upper)['name']))
        self.setItem(row, 2, QTableWidgetItem(PlumBlossomIChing.get_trigram_info(lower)['name']))
        self.setItem(row, 3, QTableWidgetItem(str(moving_yao)))
        self.setItem(row, 4, QTableWidgetItem(hexagram_name))
        self.setItem(row, 5, QTableWidgetItem(relationship))


class AdvancedAnalysisWidget(QWidget):
    """高级分析组件"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 创建选项卡
        self.tabs = QTabWidget()
        
        # 体用分析标签
        ti_yong_tab = QWidget()
        ti_yong_layout = QVBoxLayout()
        
        self.ti_yong_text = QTextEdit()
        self.ti_yong_text.setReadOnly(True)
        ti_yong_layout.addWidget(self.ti_yong_text)
        
        ti_yong_tab.setLayout(ti_yong_layout)
        self.tabs.addTab(ti_yong_tab, "体用分析")
        
        # 卦象关系标签
        relation_tab = QWidget()
        relation_layout = QVBoxLayout()
        
        self.relation_text = QTextEdit()
        self.relation_text.setReadOnly(True)
        relation_layout.addWidget(self.relation_text)
        
        relation_tab.setLayout(relation_layout)
        self.tabs.addTab(relation_tab, "卦象关系")
        
        # 爻辞详解标签
        yao_ci_tab = QWidget()
        yao_ci_layout = QVBoxLayout()
        
        self.yao_ci_text = QTextEdit()
        self.yao_ci_text.setReadOnly(True)
        yao_ci_layout.addWidget(self.yao_ci_text)
        
        yao_ci_tab.setLayout(yao_ci_layout)
        self.tabs.addTab(yao_ci_tab, "爻辞详解")
        
        layout.addWidget(self.tabs)
        self.setLayout(layout)
        
    def update_analysis(self, upper, lower, moving_yao):
        """更新分析内容"""
        # 体用分析
        relationship = PlumBlossomIChing.analyze_relationship(upper, lower, moving_yao)
        ti_yong_analysis = f"""
        【体用关系分析】
        {relationship['ti_yong']}
        
        【五行生克】
        体卦五行: {relationship['ti_element']}
        用卦五行: {relationship['yong_element']}
        生克关系: {relationship['detail']}
        
        【吉凶判断】
        {relationship['relationship']}
        
        【解读】
        {self.get_ti_yong_interpretation(relationship)}
        """
        self.ti_yong_text.setText(ti_yong_analysis)
        
        # 卦象关系
        mutual_upper, mutual_lower = PlumBlossomIChing.generate_mutual_hexagram(upper, lower)
        mutual_hexagram = PlumBlossomIChing.get_hexagram_info(mutual_upper, mutual_lower)
        
        relation_analysis = f"""
        【本卦】{PlumBlossomIChing.get_hexagram_info(upper, lower).get('name', '未知')}
        【互卦】{mutual_hexagram.get('name', '未知')}
        【变卦】{PlumBlossomIChing.get_hexagram_info(
            *PlumBlossomIChing.generate_changing_hexagram(upper, lower, moving_yao)
        ).get('name', '未知')}
        
        【卦象关系解读】
        本卦代表事情的开始状态，互卦代表发展过程，变卦代表最终结果。
        三者结合可以更全面地分析事情的发展轨迹。
        """
        self.relation_text.setText(relation_analysis)
        
        # 爻辞详解
        yao_ci = PlumBlossomIChing.get_yao_ci((upper, lower), moving_yao)
        yao_ci_analysis = f"""
        【动爻爻辞】
        {yao_ci}
        
        【爻位解读】
        第{moving_yao}爻位于{'上卦' if moving_yao > 3 else '下卦'}，
        是{'阳爻' if self.is_yang_yao(upper, lower, moving_yao) else '阴爻'}。
        
        【爻辞解读】
        {self.get_yao_ci_interpretation(yao_ci)}
        """
        self.yao_ci_text.setText(yao_ci_analysis)
    
    def get_ti_yong_interpretation(self, relationship):
        """获取体用关系解读"""
        interpretations = {
            "用生体，吉": "用卦生助体卦，外部环境对自身有利，事情容易成功。",
            "体生用，泄气": "体卦生助用卦，自身精力消耗大，需要谨慎行事。",
            "体用比和，吉": "体用卦相同或相生，内外和谐，事情顺利。",
            "用克体，凶": "用卦克制体卦，外部环境不利，需要谨慎应对。",
            "体克用，吉中带凶": "体卦克制用卦，自身有能力但需付出较大努力。"
        }
        
        return interpretations.get(relationship['relationship'], "需要结合具体卦象进一步分析。")
    
    def is_yang_yao(self, upper, lower, moving_yao):
        """判断动爻是阳爻还是阴爻"""
        # 将八卦转换为二进制表示
        trigram_binary = {
            1: [1, 1, 1], 2: [1, 1, 0], 3: [1, 0, 1], 4: [1, 0, 0],
            5: [0, 1, 1], 6: [0, 1, 0], 7: [0, 0, 1], 8: [0, 0, 0]
        }
        
        # 获取上下卦的二进制表示
        upper_binary = trigram_binary[upper]
        lower_binary = trigram_binary[lower]
        
        # 组合成本卦的六爻（从下往上）
        base_hexagram = lower_binary + upper_binary
        
        # 判断动爻是阳爻(1)还是阴爻(0)
        return base_hexagram[moving_yao-1] == 1
    
    def get_yao_ci_interpretation(self, yao_ci):
        """获取爻辞解读"""
        # 简化的爻辞解读，实际应用需要更复杂的逻辑
        if "吉" in yao_ci:
            return "此爻辞含有吉字，预示事情发展较为顺利。"
        elif "凶" in yao_ci:
            return "此爻辞含有凶字，需要谨慎应对。"
        elif "无咎" in yao_ci:
            return "此爻辞表示没有过错，平稳发展。"
        else:
            return "需要结合具体情境解读此爻辞。"


class PlumBlossomMainWindow(QMainWindow):
    """梅花易数主窗口 - 增强版"""
    
    def __init__(self):
        super().__init__()
        self.iching = PlumBlossomIChing()
        self.current_upper = 1
        self.current_lower = 1
        self.current_moving_yao = 1
        self.history = []
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("梅花易数占卜系统 - 高级版")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建工具栏
        self.create_toolbar()
        
        # 创建状态栏
        self.statusBar().showMessage("就绪")
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        
        # 左侧布局 - 占卜控制
        left_widget = QWidget()
        left_widget.setMaximumWidth(400)
        left_layout = QVBoxLayout()
        left_widget.setLayout(left_layout)
        
        # 起卦方式选择
        method_group = QGroupBox("起卦方式")
        method_layout = QVBoxLayout()
        
        self.method_combo = QComboBox()
        self.method_combo.addItems(["时间起卦", "随机起卦", "自定义起卦", "字数起卦"])
        self.method_combo.currentTextChanged.connect(self.on_method_changed)
        method_layout.addWidget(self.method_combo)
        
        # 自定义起卦参数
        self.custom_params_widget = QWidget()
        custom_layout = QGridLayout()
        
        custom_layout.addWidget(QLabel("上卦数:"), 0, 0)
        self.upper_spin = QSpinBox()
        self.upper_spin.setRange(1, 100)
        self.upper_spin.setValue(3)
        custom_layout.addWidget(self.upper_spin, 0, 1)
        
        custom_layout.addWidget(QLabel("下卦数:"), 1, 0)
        self.lower_spin = QSpinBox()
        self.lower_spin.setRange(1, 100)
        self.lower_spin.setValue(5)
        custom_layout.addWidget(self.lower_spin, 1, 1)
        
        custom_layout.addWidget(QLabel("动爻数:"), 2, 0)
        self.moving_spin = QSpinBox()
        self.moving_spin.setRange(1, 100)
        self.moving_spin.setValue(2)
        custom_layout.addWidget(self.moving_spin, 2, 1)
        
        self.custom_params_widget.setLayout(custom_layout)
        self.custom_params_widget.setVisible(False)
        method_layout.addWidget(self.custom_params_widget)
        
        # 字数起卦参数
        self.words_params_widget = QWidget()
        words_layout = QHBoxLayout()
        
        self.words_input = QLineEdit()
        self.words_input.setPlaceholderText("输入两个或多个汉字")
        words_layout.addWidget(self.words_input)
        
        self.words_params_widget.setLayout(words_layout)
        self.words_params_widget.setVisible(False)
        method_layout.addWidget(self.words_params_widget)
        
        method_group.setLayout(method_layout)
        left_layout.addWidget(method_group)
        
        # 起卦按钮
        self.divinate_btn = QPushButton("开始起卦")
        self.divinate_btn.clicked.connect(self.perform_divination)
        self.divinate_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-size: 14px; padding: 10px; }")
        left_layout.addWidget(self.divinate_btn)
        
        # 卦象信息
        info_group = QGroupBox("卦象信息")
        info_layout = QVBoxLayout()
        
        self.upper_info = QLabel("上卦: 乾 (天)")
        self.lower_info = QLabel("下卦: 坤 (地)")
        self.moving_info = QLabel("动爻: 第1爻")
        self.relationship_info = QLabel("体用关系: 未知")
        
        info_layout.addWidget(self.upper_info)
        info_layout.addWidget(self.lower_info)
        info_layout.addWidget(self.moving_info)
        info_layout.addWidget(self.relationship_info)
        
        info_group.setLayout(info_layout)
        left_layout.addWidget(info_group)
        
        # 高级选项
        advanced_group = QGroupBox("高级选项")
        advanced_layout = QVBoxLayout()
        
        self.auto_interpret = QCheckBox("自动解卦")
        self.auto_interpret.setChecked(True)
        advanced_layout.addWidget(self.auto_interpret)
        
        self.save_history = QCheckBox("保存历史记录")
        self.save_history.setChecked(True)
        advanced_layout.addWidget(self.save_history)
        
        advanced_group.setLayout(advanced_layout)
        left_layout.addWidget(advanced_group)
        
        # 历史记录
        history_group = QGroupBox("占卜历史")
        history_layout = QVBoxLayout()
        
        self.history_table = DivinationHistoryWidget()
        history_layout.addWidget(self.history_table)
        
        # 历史记录操作按钮
        history_btn_layout = QHBoxLayout()
        self.clear_history_btn = QPushButton("清空历史")
        self.clear_history_btn.clicked.connect(self.clear_history)
        history_btn_layout.addWidget(self.clear_history_btn)
        
        self.export_history_btn = QPushButton("导出历史")
        self.export_history_btn.clicked.connect(self.export_history)
        history_btn_layout.addWidget(self.export_history_btn)
        
        history_layout.addLayout(history_btn_layout)
        history_group.setLayout(history_layout)
        left_layout.addWidget(history_group)
        
        # 右侧布局 - 卦象显示和解卦
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_widget.setLayout(right_layout)
        
        # 卦象显示
        self.hexagram_display = HexagramDisplayWidget()
        right_layout.addWidget(self.hexagram_display)
        
        # 解卦结果
        interpretation_group = QGroupBox("解卦结果")
        interpretation_layout = QVBoxLayout()
        
        self.interpretation_text = QTextEdit()
        self.interpretation_text.setReadOnly(True)
        interpretation_layout.addWidget(self.interpretation_text)
        
        interpretation_group.setLayout(interpretation_layout)
        right_layout.addWidget(interpretation_group)
        
        # 高级分析
        self.advanced_analysis = AdvancedAnalysisWidget()
        right_layout.addWidget(self.advanced_analysis)
        
        # 添加到主布局
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([400, 800])
        
        main_layout.addWidget(splitter)
        
        # 初始显示
        self.update_display()
        
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar("主工具栏")
        self.addToolBar(toolbar)
        
        # 起卦动作
        divinate_action = QAction("起卦", self)
        divinate_action.setStatusTip("执行梅花易数起卦")
        divinate_action.triggered.connect(self.perform_divination)
        toolbar.addAction(divinate_action)
        
        toolbar.addSeparator()
        
        # 保存动作
        save_action = QAction("保存", self)
        save_action.setStatusTip("保存当前卦象")
        save_action.triggered.connect(self.save_current)
        toolbar.addAction(save_action)
        
        # 导入动作
        load_action = QAction("导入", self)
        load_action.setStatusTip("导入卦象记录")
        load_action.triggered.connect(self.load_history)
        toolbar.addAction(load_action)
        
    def on_method_changed(self, method):
        """起卦方式改变事件"""
        self.custom_params_widget.setVisible(method == "自定义起卦")
        self.words_params_widget.setVisible(method == "字数起卦")
            
    def perform_divination(self):
        """执行占卜"""
        method = self.method_combo.currentText()
        
        try:
            if method == "时间起卦":
                upper, lower, moving_yao = self.iching.generate_numbers_time()
                self.statusBar().showMessage("使用时间起卦法")
            elif method == "随机起卦":
                upper, lower, moving_yao = self.iching.generate_numbers_random()
                self.statusBar().showMessage("使用随机起卦法")
            elif method == "自定义起卦":
                upper = self.upper_spin.value()
                lower = self.lower_spin.value()
                moving_yao = self.moving_spin.value()
                upper, lower, moving_yao = self.iching.generate_numbers_custom(upper, lower, moving_yao)
                self.statusBar().showMessage("使用自定义起卦法")
            else:  # 字数起卦
                words = self.words_input.text().strip()
                if len(words) < 2:
                    QMessageBox.warning(self, "输入错误", "请输入至少两个汉字")
                    return
                upper, lower, moving_yao = self.iching.generate_numbers_words(words)
                self.statusBar().showMessage("使用字数起卦法")
                
            self.current_upper = upper
            self.current_lower = lower
            self.current_moving_yao = moving_yao
            
            # 更新显示
            self.update_display()
            
            # 添加到历史记录
            if self.save_history.isChecked():
                time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                hexagram_name = self.iching.get_hexagram_info(upper, lower).get('name', '未知')
                relationship = self.iching.analyze_relationship(upper, lower, moving_yao)['relationship']
                self.history_table.add_record(time_str, upper, lower, moving_yao, hexagram_name, relationship)
                
                # 保存到内存历史
                self.history.append({
                    'time': time_str,
                    'upper': upper,
                    'lower': lower,
                    'moving_yao': moving_yao,
                    'hexagram_name': hexagram_name,
                    'relationship': relationship
                })
            
            # 显示解卦结果
            if self.auto_interpret.isChecked():
                interpretation = self.iching.interpret_hexagram(upper, lower, moving_yao)
                self.interpretation_text.setText(interpretation)
                
                # 更新高级分析
                self.advanced_analysis.update_analysis(upper, lower, moving_yao)
                
            self.statusBar().showMessage("起卦完成")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"起卦过程中发生错误: {str(e)}")
        
    def update_display(self):
        """更新显示"""
        # 更新卦象显示
        self.hexagram_display.update_hexagram(
            self.current_upper, 
            self.current_lower, 
            self.current_moving_yao
        )
        
        # 更新卦象信息
        upper_info = self.iching.get_trigram_info(self.current_upper)
        lower_info = self.iching.get_trigram_info(self.current_lower)
        relationship = self.iching.analyze_relationship(
            self.current_upper, self.current_lower, self.current_moving_yao
        )
        
        self.upper_info.setText(f"上卦: {upper_info['name']} ({upper_info['nature']})")
        self.lower_info.setText(f"下卦: {lower_info['name']} ({lower_info['nature']})")
        self.moving_info.setText(f"动爻: 第{self.current_moving_yao}爻")
        self.relationship_info.setText(f"体用关系: {relationship['relationship']}")
        
    def clear_history(self):
        """清空历史记录"""
        reply = QMessageBox.question(self, "确认", "确定要清空所有历史记录吗？", 
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.history_table.setRowCount(0)
            self.history = []
            
    def export_history(self):
        """导出历史记录"""
        if not self.history:
            QMessageBox.information(self, "提示", "没有历史记录可导出")
            return
            
        filename, _ = QFileDialog.getSaveFileName(
            self, "导出历史记录", "梅花易数历史记录.txt", "文本文件 (*.txt)"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write("梅花易数占卜历史记录\n")
                    f.write("=" * 50 + "\n")
                    for record in self.history:
                        f.write(f"时间: {record['time']}\n")
                        f.write(f"卦象: {record['hexagram_name']}\n")
                        f.write(f"体用: {record['relationship']}\n")
                        f.write("-" * 30 + "\n")
                QMessageBox.information(self, "成功", "历史记录已导出")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")
                
    def save_current(self):
        """保存当前卦象"""
        if not hasattr(self, 'current_upper'):
            QMessageBox.information(self, "提示", "没有当前卦象可保存")
            return
            
        filename, _ = QFileDialog.getSaveFileName(
            self, "保存当前卦象", "梅花易数卦象.txt", "文本文件 (*.txt)"
        )
        
        if filename:
            try:
                interpretation = self.iching.interpret_hexagram(
                    self.current_upper, self.current_lower, self.current_moving_yao
                )
                
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write("梅花易数卦象记录\n")
                    f.write("=" * 50 + "\n")
                    f.write(interpretation)
                QMessageBox.information(self, "成功", "卦象已保存")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")
                
    def load_history(self):
        """导入历史记录"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "导入历史记录", "", "文本文件 (*.txt)"
        )
        
        if filename:
            # 这里简化处理，实际应解析文件内容
            QMessageBox.information(self, "提示", "导入功能待完善")


def main():
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle("Fusion")
    
    # 创建主窗口
    window = PlumBlossomMainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()