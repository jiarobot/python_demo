# -*- coding: utf-8 -*-
"""
Created on Tue Jun 17 10:11:21 2025

@author: 10166
"""

import sys
import random
import math
import numpy as np
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QLineEdit, QTextEdit, QGroupBox, QTabWidget, QFrame,
    QListWidget, QStackedWidget, QProgressBar, QComboBox
)
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QLinearGradient, QRadialGradient,
    QPixmap, QFontMetrics, QPalette, QImage, QPainterPath
)
from PyQt6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis

# 八卦卦象数据 - 扩展到64卦
BAGUA = {
    "乾": ("111", "天", "创造", "金", "西北", "大吉", 
           "创新进取，领导力强。事业将迎来重大突破，但需注意刚愎自用。适宜决策和开拓新领域。"),
    "坤": ("000", "地", "接纳", "土", "西南", "吉", 
           "包容承载，厚德载物。人际关系和谐，但需避免优柔寡断。适宜合作和长期规划。"),
    "屯": ("100010", "水雷", "初创", "水", "北方", "中吉", 
           "万物初生，艰难创始。面临挑战但蕴含机遇，需坚韧不拔。适宜基础建设和团队组建。"),
    "蒙": ("010001", "山水", "启蒙", "水", "北方", "中平", 
           "启蒙教育，求知探索。需要寻求指导，避免盲目行动。适宜学习和技能提升。"),
    "需": ("111010", "水天", "等待", "水", "北方", "吉", 
           "耐心等待，时机将至。资源正在聚集，不宜急躁。适宜准备和资源积累。"),
    "讼": ("010111", "天水", "争讼", "水", "西北", "凶", 
           "争议纠纷，避免对抗。法律事务需谨慎，寻求和解为上。适宜调解和避免冲突。"),
    "师": ("010000", "地水", "军队", "水", "北方", "中吉", 
           "组织力量，集体行动。需要团队合作，明确领导关系。适宜项目管理和团队协作。"),
    "比": ("000010", "水地", "亲附", "水", "北方", "吉", 
           "亲密合作，相互支持。人际关系和谐，利于建立联盟。适宜合作和建立伙伴关系。"),
    "小畜": ("111011", "风天", "小蓄", "木", "东南", "小吉", 
           "小有积蓄，逐步积累。进展缓慢但稳定，需保持耐心。适宜储蓄和逐步发展。"),
    "履": ("110111", "天泽", "实践", "金", "西北", "中吉", 
           "谨慎实践，脚踏实地。风险与机遇并存，需细致执行。适宜具体实施和细节把控。"),
    "泰": ("111000", "地天", "通泰", "土", "西南", "大吉", 
           "天地交泰，通达顺利。最佳时机已到，大胆行动。适宜重大决策和项目启动。"),
    "否": ("000111", "天地", "阻塞", "土", "西南", "凶", 
           "阻塞不通，时运不济。需等待时机，避免重大决策。适宜反思和内部调整。"),
    "同人": ("111101", "天火", "同心", "火", "南方", "吉", 
           "志同道合，同心协力。团队凝聚力强，利于合作。适宜团队建设和社交活动。"),
    "大有": ("101111", "火天", "丰收", "火", "南方", "大吉", 
           "丰盛收获，成就显著。努力将获回报，享受成果。适宜庆祝和成果展示。"),
    "谦": ("001000", "地山", "谦虚", "土", "西南", "吉", 
           "谦虚谨慎，赢得尊重。低调行事反而获益。适宜请教他人和展现谦逊。"),
    "豫": ("000100", "雷地", "愉悦", "木", "东方", "吉", 
           "愉悦和谐，时机有利。适宜娱乐和社交活动。"),
    "随": ("100110", "泽雷", "跟随", "金", "西方", "中吉", 
           "随从大势，灵活变通。适应环境变化，顺势而为。适宜调整策略和跟随趋势。"),
    "蛊": ("011001", "山风", "腐败", "木", "东北", "凶", 
           "腐败混乱，需要整治。内部问题暴露，需大刀阔斧改革。适宜解决遗留问题和整顿。"),
    "临": ("110000", "地泽", "临近", "土", "西南", "吉", 
           "临近视察，掌握全局。需要亲力亲为，深入一线。适宜监督和管理控制。"),
    "观": ("000011", "风地", "观察", "木", "东南", "中平", 
           "观察分析，获取信息。需要更多数据支持决策。适宜调研和市场分析。"),
    "噬嗑": ("101001", "火雷", "咬合", "火", "南方", "中平", 
           "克服障碍，解决纠纷。需果断处理问题。适宜解决冲突和突破障碍。"),
    "贲": ("100101", "山火", "装饰", "火", "南方", "中吉", 
           "装饰美化，提升形象。注重外表和包装。适宜营销宣传和形象提升。"),
    "剥": ("000001", "山地", "剥落", "土", "西南", "凶", 
           "衰落剥落，根基不稳。需巩固基础，防止崩溃。适宜风险控制和保守策略。"),
    "复": ("100000", "地雷", "回复", "土", "西南", "吉", 
           "恢复生机，重新开始。失败后重振旗鼓。适宜二次尝试和修复关系。"),
    "无妄": ("111001", "天雷", "无妄", "木", "东方", "凶", 
           "意外变故，不可预测。需谨慎防范风险。适宜保险和应急预案。"),
    "大畜": ("001111", "山天", "大蓄", "土", "东北", "吉", 
           "大量积累，厚积薄发。资源丰富，为未来准备。适宜长期投资和资源储备。"),
    "颐": ("100001", "山雷", "颐养", "土", "东北", "中吉", 
           "养生修养，自我提升。关注健康和个人成长。适宜健康管理和技能学习。"),
    "大过": ("011110", "泽风", "大过", "木", "东南", "凶", 
           "过度冒险，危机四伏。需谨慎评估风险。适宜保守策略和避免冒险。"),
    "坎": ("010010", "水", "险陷", "水", "北方", "凶", 
           "险陷重重，挑战艰巨。需智慧和勇气应对。适宜寻求帮助和谨慎决策。"),
    "离": ("101101", "火", "光明", "火", "南方", "吉", 
           "光明照耀，前景明朗。创意和灵感迸发。适宜创新和艺术创作。")
}

# 五行颜色映射
ELEMENT_COLORS = {
    "金": QColor(192, 192, 192),  # 金属
    "木": QColor(34, 139, 34),    # 木
    "水": QColor(30, 144, 255),   # 水
    "火": QColor(255, 69, 0),     # 火
    "土": QColor(139, 69, 19)     # 土
}

# 时间运势分析
TIME_ANALYSIS = {
    "乾": {"近期": "吉", "中期": "大吉", "长期": "吉"},
    "坤": {"近期": "平", "中期": "吉", "长期": "大吉"},
    "屯": {"近期": "凶", "中期": "中吉", "长期": "吉"},
    "蒙": {"近期": "平", "中期": "中吉", "长期": "吉"},
    "需": {"近期": "中吉", "中期": "吉", "长期": "大吉"},
    "讼": {"近期": "凶", "中期": "凶", "长期": "中平"},
    "师": {"近期": "中吉", "中期": "吉", "长期": "中吉"},
    "比": {"近期": "吉", "中期": "中吉", "长期": "吉"},
    "小畜": {"近期": "中平", "中期": "中吉", "长期": "吉"},
    "履": {"近期": "中吉", "中期": "吉", "长期": "中吉"},
    "泰": {"近期": "大吉", "中期": "大吉", "长期": "吉"},
    "否": {"近期": "凶", "中期": "中凶", "长期": "平"},
    "同人": {"近期": "吉", "中期": "大吉", "长期": "吉"},
    "大有": {"近期": "大吉", "中期": "大吉", "long": "吉"},
    "谦": {"近期": "中平", "中期": "吉", "long": "大吉"},
    "豫": {"近期": "吉", "中期": "中吉", "long": "中平"},
    "随": {"近期": "中吉", "中期": "吉", "long": "中吉"},
    "蛊": {"近期": "凶", "中期": "中凶", "long": "平"},
    "临": {"近期": "中吉", "中期": "吉", "long": "中吉"},
    "观": {"近期": "中平", "中期": "中平", "long": "中吉"},
    "噬嗑": {"近期": "中平", "中期": "中吉", "long": "吉"},
    "贲": {"近期": "中吉", "中期": "中吉", "long": "平"},
    "剥": {"近期": "凶", "中期": "凶", "long": "中凶"},
    "复": {"近期": "中平", "中期": "中吉", "long": "吉"},
    "无妄": {"近期": "凶", "中期": "中凶", "long": "平"},
    "大畜": {"近期": "中吉", "中期": "吉", "long": "大吉"},
    "颐": {"近期": "中平", "中期": "中吉", "long": "吉"},
    "大过": {"近期": "凶", "中期": "凶", "long": "中凶"},
    "坎": {"近期": "凶", "中期": "中凶", "long": "平"},
    "离": {"近期": "吉", "中期": "大吉", "long": "中吉"}
}

class QuantumParticle:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.size = random.uniform(2.0, 6.0)
        self.color = QColor(
            random.randint(100, 255),
            random.randint(100, 255),
            random.randint(200, 255)
        )
        self.speed = random.uniform(0.5, 3.0)
        self.angle = random.uniform(0, 2 * math.pi)
        self.energy = random.uniform(0.1, 1.0)
        self.orbit_radius = random.randint(30, 180)
        self.orbit_speed = random.uniform(0.005, 0.03)
        self.phase = random.uniform(0, 2 * math.pi)
        self.charge = random.choice([-1, 1])
        self.target_x = x
        self.target_y = y
        self.forming = False
        self.formation_progress = 0
        self.trail = []
        self.max_trail = 20
        self.life = random.uniform(100, 200)
        self.age = 0

    def update(self, mouse_pos, forming=False, time_factor=1.0):
        self.age += 1
        
        if self.age > self.life and not forming:
            # 粒子重生
            self.x = random.randint(0, 1000)
            self.y = random.randint(0, 700)
            self.age = 0
            self.trail = []
        
        if forming:
            self.forming = True
            self.formation_progress += 0.01 * time_factor
            if self.formation_progress > 1:
                self.formation_progress = 1
                
            # 移动到目标位置
            dx = self.target_x - self.x
            dy = self.target_y - self.y
            dist = max(0.1, math.sqrt(dx*dx + dy*dy))
            
            if dist > 2:
                self.x += dx * 0.08 * time_factor
                self.y += dy * 0.08 * time_factor
            else:
                self.x = self.target_x
                self.y = self.target_y
        else:
            # 量子波动运动
            self.phase += self.orbit_speed * time_factor
            dx = math.cos(self.phase) * self.orbit_radius
            dy = math.sin(self.phase) * self.orbit_radius * 0.7
            
            # 对鼠标的响应
            mx, my = mouse_pos
            dist_to_mouse = max(1, math.sqrt((mx - self.x)**2 + (my - self.y)**2))
            
            if dist_to_mouse < 250:
                force = min(20, 3000 / (dist_to_mouse**1.5))
                angle_to_mouse = math.atan2(my - self.y, mx - self.x)
                self.x -= math.cos(angle_to_mouse) * force * time_factor
                self.y -= math.sin(angle_to_mouse) * force * time_factor
            else:
                self.x = 500 + dx
                self.y = 350 + dy
        
        # 更新轨迹
        if random.random() < 0.7:
            self.trail.append((self.x, self.y))
            if len(self.trail) > self.max_trail:
                self.trail.pop(0)

    def draw(self, painter):
        # 绘制轨迹
        for i, (x, y) in enumerate(self.trail):
            alpha = int(255 * i / len(self.trail))
            size = max(1, self.size * i / len(self.trail))
            
            color = QColor(self.color)
            color.setAlpha(alpha)
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(x, y), size, size)
        
        # 绘制粒子
        if self.forming:
            size = self.size * (1 + 0.5 * math.sin(datetime.now().timestamp() * 0.01))
            color = QColor(255, 223, 0)  # 高亮
        else:
            size = self.size
            color = self.color
        
        alpha = min(255, int(self.energy * 255))
        color.setAlpha(alpha)
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(self.x, self.y), size * 1.5, size * 1.5)

class GuaSymbol:
    def __init__(self, name, binary):
        self.name = name
        self.binary = binary
        self.lines = []
        self.position = (500, 470)
        self.size = 220
        self.rotation = 0
        self.rotation_speed = random.uniform(-0.02, 0.02)
        self.generate_lines()
        
    def generate_lines(self):
        line_count = len(self.binary)
        line_height = self.size / line_count
        y_start = self.position[1] - self.size//2
        
        for i, bit in enumerate(self.binary):
            y_pos = y_start + i * line_height
            if bit == '1':  # 阳爻（实线）
                self.lines.append(('yang', (self.position[0] - self.size//2, y_pos, self.size, line_height/3)))
            else:  # 阴爻（虚线）
                self.lines.append(('yin', (self.position[0] - self.size//2, y_pos, self.size, line_height/3)))
    
    def draw(self, painter, progress=1.0):
        self.rotation += self.rotation_speed
        
        # 绘制光晕
        if progress > 0.5:
            glow_alpha = min(255, int(200 * (progress - 0.5) * 2))
            radial_grad = QRadialGradient(self.position[0], self.position[1], self.size*0.9)
            radial_grad.setColorAt(0, QColor(255, 223, 0, glow_alpha))
            radial_grad.setColorAt(1, QColor(255, 223, 0, 0))
            
            painter.setBrush(QBrush(radial_grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(self.position[0], self.position[1]), 
                            self.size*0.9, self.size*0.9)
        
        # 保存当前状态
        painter.save()
        painter.translate(self.position[0], self.position[1])
        painter.rotate(self.rotation * 10)
        
        # 绘制卦象
        for i, (line_type, rect) in enumerate(self.lines):
            if progress > i / len(self.lines):
                x, y, width, height = rect
                x -= self.position[0] - self.size//2
                y -= self.position[1] - self.size//2
                
                # Convert coordinates to integers for drawRoundedRect
                x_int = int(x)
                y_int = int(y)
                width_int = int(width)
                height_int = int(height)
                
                if line_type == 'yang':
                    painter.setBrush(QBrush(QColor(255, 223, 0)))  # 阳爻高亮
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawRoundedRect(x_int, y_int, width_int, height_int, 5, 5)
                else:
                    painter.setBrush(QBrush(QColor(190, 70, 230)))  # 阴爻紫色
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawRoundedRect(x_int, y_int, width_int, height_int, 5, 5)
                    
                    # 绘制中间的空白
                    painter.setBrush(QBrush(QColor(8, 12, 24)))  # 背景色
                    painter.drawRoundedRect(
                        int(x + width/3), y_int, 
                        int(width/3), height_int, 
                        3, 3
                    )
        
        # 恢复状态
        painter.restore()
        
        # 绘制卦名
        painter.setPen(QColor(220, 240, 255))
        painter.setFont(QFont("SimHei", 16))
        text = f"{self.name}卦"
        text_width = painter.fontMetrics().horizontalAdvance(text)
        painter.drawText(self.position[0] - text_width//2, self.position[1] + self.size//2 + 30, text)

class DivinationWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(1000, 700)
        self.setStyleSheet("background-color: #080c18;")
        
        self.particles = [QuantumParticle(random.randint(0, 1000), random.randint(0, 700)) 
                         for _ in range(150)]
        self.current_gua = None
        self.forming = False
        self.formation_progress = 0
        self.formation_time = datetime.now().timestamp()
        self.result_shown = False
        self.interpretation = ""
        self.time_analysis = {}
        self.history = []
        self.advice = []
        self.related_gua = []
        self.time_factor = 1.0
        self.user_question = ""
        self.energy_graph = None
        self.five_elements = {"金": 0, "木": 0, "水": 0, "火": 0, "土": 0}
        self.element_balance = []
        
        # 设置定时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(20)  # 50 FPS
        
    def perform_divination(self, question=""):
        if self.forming:
            return
            
        self.user_question = question
        self.forming = True
        self.formation_progress = 0
        self.formation_time = datetime.now().timestamp()
        self.result_shown = False
        self.advice = []
        self.related_gua = []
        
        # 根据问题选择卦象
        if question:
            # 简单的情感分析
            positive_words = ["成功", "机会", "爱情", "健康", "财富", "快乐", "成长"]
            negative_words = ["问题", "困难", "失败", "风险", "损失", "疾病", "冲突"]
            
            positive_count = sum(1 for word in positive_words if word in question)
            negative_count = sum(1 for word in negative_words if word in question)
            
            if positive_count > negative_count:
                # 倾向于吉卦
                candidates = [k for k, v in BAGUA.items() if "吉" in v[5]]
            elif negative_count > positive_count:
                # 倾向于凶卦
                candidates = [k for k, v in BAGUA.items() if "凶" in v[5]]
            else:
                candidates = list(BAGUA.keys())
        else:
            candidates = list(BAGUA.keys())
        
        # 随机选择一个卦象
        gua_name = random.choice(candidates)
        self.current_gua = GuaSymbol(gua_name, BAGUA[gua_name][0])
        self.interpretation = BAGUA[gua_name][6]
        self.time_analysis = TIME_ANALYSIS[gua_name]
        
        # 更新五行平衡
        self.update_five_elements(gua_name)
        
        # 生成建议
        self.generate_advice(gua_name)
        
        # 生成相关卦象
        self.generate_related_gua(gua_name)
        
        # 为粒子分配目标位置
        for particle in self.particles:
            particle.forming = True
            particle.formation_progress = 0
            particle.target_x = self.current_gua.position[0] + random.randint(-120, 120)
            particle.target_y = self.current_gua.position[1] + random.randint(-70, 70)
        
        # 添加到历史记录
        self.history.append({
            "gua": gua_name,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "question": question
        })
        if len(self.history) > 5:
            self.history.pop(0)
    
    def update_five_elements(self, gua_name):
        # 重置五行
        self.five_elements = {"金": 0, "木": 0, "水": 0, "火": 0, "土": 0}
        
        # 主卦象的五行
        main_element = BAGUA[gua_name][3]
        self.five_elements[main_element] += 3
        
        # 相关卦象的五行
        for gua in self.related_gua:
            element = BAGUA[gua][3]
            self.five_elements[element] += 1
        
        # 生成五行平衡分析
        self.element_balance = []
        total = sum(self.five_elements.values())
        
        for element, value in self.five_elements.items():
            percentage = (value / total) * 100
            status = ""
            if percentage > 30:
                status = "过旺"
            elif percentage < 15:
                status = "不足"
            else:
                status = "平衡"
            
            self.element_balance.append({
                "element": element,
                "value": value,
                "percentage": percentage,
                "status": status,
                "color": ELEMENT_COLORS[element]
            })
    
    def generate_advice(self, gua_name):
        # 根据卦象生成建议
        advice_map = {
            "乾": ["大胆决策", "展现领导力", "开拓新领域", "相信自己"],
            "坤": ["加强合作", "耐心等待", "巩固基础", "倾听他人"],
            "需": ["耐心等待时机", "做好充分准备", "储备资源", "保持警觉"],
            "讼": ["避免冲突", "寻求和解", "咨询法律意见", "保持冷静"],
            "泰": ["把握良机", "积极行动", "扩大影响", "分享成功"],
            "否": ["谨慎决策", "保存实力", "等待转机", "自我反思"],
            "同人": ["加强团队合作", "建立人脉", "寻求共识", "培养信任"],
            "大有": ["庆祝成果", "分享收获", "规划下一步", "感恩回馈"],
            "谦": ["保持谦逊", "学习他人长处", "低调行事", "尊重传统"],
            "豫": ["享受生活", "社交活动", "放松心情", "寻找乐趣"],
            "蛊": ["整顿内部", "解决遗留问题", "改革更新", "清除障碍"],
            "复": ["重新开始", "从失败中学习", "修复关系", "坚持不懈"],
            "坎": ["寻求帮助", "谨慎行事", "准备应急预案", "培养勇气"],
            "离": ["发挥创意", "艺术创作", "分享想法", "传播光明"]
        }
        
        self.advice = advice_map.get(gua_name, ["保持积极心态", "顺势而为", "平衡各方关系", "关注健康"])
        
        # 添加通用建议
        if "吉" in BAGUA[gua_name][5]:
            self.advice.append("把握机遇")
        elif "凶" in BAGUA[gua_name][5]:
            self.advice.append("谨慎行事")
    
    def generate_related_gua(self, gua_name):
        # 生成相关卦象
        all_gua = list(BAGUA.keys())
        all_gua.remove(gua_name)
        self.related_gua = random.sample(all_gua, 3)
    
    def update_animation(self):
        # 更新时间因子
        current_time = datetime.now().timestamp()
        self.time_factor = 1.0 + 0.5 * math.sin(current_time * 0.0005)
        
        # 更新粒子
        mouse_pos = (self.mapFromGlobal(self.cursor().pos()).x(), 
                     self.mapFromGlobal(self.cursor().pos()).y())
        
        for particle in self.particles:
            particle.update(mouse_pos, self.forming, self.time_factor)
        
        # 更新形成进度
        if self.forming:
            elapsed = current_time - self.formation_time
            self.formation_progress = min(1.0, elapsed / 3)  # 3秒完成
            
            if self.formation_progress >= 1.0 and not self.result_shown:
                self.result_shown = True
                
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制背景
        self.draw_background(painter)
        
        # 绘制粒子
        for particle in self.particles:
            particle.draw(painter)
        
        # 绘制卦象
        if self.current_gua and self.forming:
            if self.formation_progress > 0.3:
                line_progress = min(1.0, (self.formation_progress - 0.3) / 0.7)
                self.current_gua.draw(painter, line_progress)
        
        # 绘制结果
        if self.result_shown:
            self.draw_result(painter)
        
        # 绘制UI元素
        self.draw_ui(painter)
    
    def draw_background(self, painter):
        # 绘制深色背景
        painter.fillRect(self.rect(), QColor(8, 12, 24))
        
        # 绘制星空
        painter.setPen(Qt.PenStyle.NoPen)
        for _ in range(200):
            x = random.randint(0, self.width())
            y = random.randint(0, self.height())
            size = random.randint(1, 3)
            brightness = random.randint(100, 255)
            color = QColor(brightness, brightness, brightness)
            painter.setBrush(QBrush(color))
            painter.drawEllipse(QPointF(x, y), size, size)
        
        # 绘制银河
        for y in range(0, self.height(), 4):
            for x in range(0, self.width(), 4):
                if random.random() < 0.2:
                    brightness = random.randint(50, 150)
                    color = QColor(brightness, brightness, 255)
                    painter.setBrush(QBrush(color))
                    painter.drawEllipse(QPointF(x, y), 1, 1)
    
    def draw_ui(self, painter):
        # 标题
        painter.setPen(QColor(0, 210, 255))
        font = QFont("SimHei", 36, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(self.width()//2 - 200, 50, "多维时空卜卦仪")
        
        # 副标题
        painter.setPen(QColor(190, 70, 230))
        font = QFont("SimHei", 18)
        painter.setFont(font)
        painter.drawText(self.width()//2 - 150, 85, "量子场论与易经智慧的融合系统")
    
    def draw_result(self, painter):
        if not self.current_gua:
            return
            
        # 结果框
        result_rect = QRectF(self.width()//2 - 340, 150, 680, 500)
        painter.setBrush(QBrush(QColor(15, 25, 45, 220)))
        painter.setPen(QPen(QColor(255, 223, 0), 3))
        painter.drawRoundedRect(result_rect, 15, 15)
        
        # 卦名
        luck_color = QColor(100, 255, 150) if "吉" in BAGUA[self.current_gua.name][5] else QColor(255, 100, 100)
        font = QFont("SimHei", 24)
        painter.setFont(font)
        painter.setPen(luck_color)
        gua_name = f"{self.current_gua.name}卦 · {BAGUA[self.current_gua.name][5]}"
        painter.drawText(self.width()//2 - painter.fontMetrics().horizontalAdvance(gua_name)//2, 190, gua_name)
        
        # 卦象属性
        attributes = BAGUA[self.current_gua.name]
        props = [
            f"结构: {attributes[0]}",
            f"自然象征: {attributes[1]}",
            f"核心特性: {attributes[2]}",
            f"五行属性: {attributes[3]}",
            f"方位: {attributes[4]}"
        ]
        
        painter.setPen(QColor(220, 240, 255))
        font = QFont("SimHei", 16)
        painter.setFont(font)
        
        for i, prop in enumerate(props):
            painter.drawText(self.width()//2 - 300, 240 + i*40, prop)
        
        # 解读
        painter.setPen(QColor(0, 210, 255))
        painter.drawText(self.width()//2 - 300, 420, "卦象深度解读:")
        
        painter.setPen(QColor(220, 240, 255))
        wrapped_text = self.wrap_text(self.interpretation, 60)
        for i, line in enumerate(wrapped_text):
            painter.drawText(self.width()//2 - 300, 460 + i*30, line)
    
    def wrap_text(self, text, width):
        """将文本换行以适应宽度"""
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            if len(test_line) <= width:
                current_line.append(word)
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("多维时空卜卦仪")
        self.setGeometry(100, 100, 1200, 800)
        
        # 设置主窗口样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #080c18;
            }
            QWidget {
                color: #dce0ff;
                font-family: 'SimHei';
            }
            QPushButton {
                background-color: #00d2ff;
                color: #080c18;
                border-radius: 10px;
                padding: 10px 20px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #00b8e6;
            }
            QPushButton:pressed {
                background-color: #0099cc;
            }
            QLineEdit, QTextEdit {
                background-color: #1e2840;
                color: #dce0ff;
                border: 2px solid #00d2ff;
                border-radius: 8px;
                padding: 8px;
                font-size: 14px;
            }
            QGroupBox {
                border: 2px solid #be46e6;
                border-radius: 10px;
                margin-top: 1ex;
                font-size: 16px;
                color: #be46e6;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QTabWidget::pane {
                border: 1px solid #2a3a5a;
                border-radius: 5px;
            }
            QTabBar::tab {
                background: #1a2438;
                color: #dce0ff;
                padding: 8px 20px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                border: 1px solid #2a3a5a;
            }
            QTabBar::tab:selected {
                background: #00d2ff;
                color: #080c18;
                border-bottom: 2px solid #00d2ff;
            }
            QListWidget {
                background-color: #0e1424;
                border: 1px solid #2a3a5a;
                border-radius: 5px;
                font-size: 14px;
            }
        """)
        
        # 创建主布局
        main_widget = QWidget()
        main_layout = QHBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # 左侧卜卦区域
        divination_widget = DivinationWidget()
        main_layout.addWidget(divination_widget, 7)  # 70%宽度
        
        # 右侧控制面板
        control_panel = QWidget()
        control_layout = QVBoxLayout()
        control_panel.setLayout(control_layout)
        main_layout.addWidget(control_panel, 3)  # 30%宽度
        
        # 创建选项卡
        tab_widget = QTabWidget()
        control_layout.addWidget(tab_widget)
        
        # 卜卦控制标签页
        divination_tab = QWidget()
        tab_widget.addTab(divination_tab, "卜卦控制")
        divination_layout = QVBoxLayout(divination_tab)
        
        # 问题输入
        question_group = QGroupBox("输入您的问题")
        question_layout = QVBoxLayout()
        question_group.setLayout(question_layout)
        
        self.question_input = QLineEdit()
        self.question_input.setPlaceholderText("输入您的问题...")
        question_layout.addWidget(self.question_input)
        
        divination_layout.addWidget(question_group)
        
        # 卜卦按钮
        self.divination_button = QPushButton("量子卜卦")
        self.divination_button.clicked.connect(self.perform_divination)
        divination_layout.addWidget(self.divination_button)
        
        # 历史记录
        history_group = QGroupBox("历史记录")
        history_layout = QVBoxLayout()
        history_group.setLayout(history_layout)
        
        self.history_list = QListWidget()
        history_layout.addWidget(self.history_list)
        divination_layout.addWidget(history_group)
        
        # 卦象详情标签页
        details_tab = QWidget()
        tab_widget.addTab(details_tab, "卦象详情")
        details_layout = QVBoxLayout(details_tab)
        
        # 卦象属性
        attributes_group = QGroupBox("卦象属性")
        attributes_layout = QVBoxLayout()
        attributes_group.setLayout(attributes_layout)
        
        self.attributes_text = QTextEdit()
        self.attributes_text.setReadOnly(True)
        attributes_layout.addWidget(self.attributes_text)
        
        details_layout.addWidget(attributes_group)
        
        # 时间运势
        time_group = QGroupBox("时间运势")
        time_layout = QVBoxLayout()
        time_group.setLayout(time_layout)
        
        self.time_text = QTextEdit()
        self.time_text.setReadOnly(True)
        time_layout.addWidget(self.time_text)
        
        details_layout.addWidget(time_group)
        
        # 五行平衡标签页
        elements_tab = QWidget()
        tab_widget.addTab(elements_tab, "五行平衡")
        elements_layout = QVBoxLayout(elements_tab)
        
        # 五行图表
        self.elements_chart = QChart()
        self.elements_chart.setTheme(QChart.ChartTheme.ChartThemeDark)
        self.elements_chart.setBackgroundBrush(QBrush(QColor(8, 12, 24)))
        self.elements_chart.setTitle("五行平衡分析")
        self.elements_chart.setTitleBrush(QBrush(QColor(220, 240, 255)))
        
        chart_view = QChartView(self.elements_chart)
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        elements_layout.addWidget(chart_view)
        self.divination_widget = divination_widget
        # 设置初始值
        self.update_elements_chart()
        
        # 建议标签页
        advice_tab = QWidget()
        tab_widget.addTab(advice_tab, "行动建议")
        advice_layout = QVBoxLayout(advice_tab)
        
        self.advice_text = QTextEdit()
        self.advice_text.setReadOnly(True)
        self.advice_text.setFont(QFont("SimHei", 14))
        advice_layout.addWidget(self.advice_text)
        
        # 设置初始文本
        self.advice_text.setText("请先进行卜卦以获取建议...")
        
        # 底部状态栏
        status_bar = self.statusBar()
        self.status_label = QLabel("系统就绪 | 等待卜卦指令")
        status_bar.addWidget(self.status_label)
        
        # 保存DivinationWidget引用
        self.divination_widget = divination_widget
    
    def perform_divination(self):
        question = self.question_input.text()
        self.divination_widget.perform_divination(question)
        self.status_label.setText("卜卦进行中...量子场正在计算卦象")
        
        # 清空输入框
        self.question_input.clear()
        
        # 更新UI
        QTimer.singleShot(3500, self.update_results)  # 3.5秒后更新结果
    
    def update_results(self):
        if not self.divination_widget.current_gua:
            return
            
        gua_name = self.divination_widget.current_gua.name
        attributes = BAGUA[gua_name]
        time_analysis = self.divination_widget.time_analysis
        
        # 更新卦象属性
        attributes_text = f"""
        <b>{gua_name}卦</b> - {attributes[5]}
        <p><b>结构:</b> {attributes[0]}</p>
        <p><b>自然象征:</b> {attributes[1]}</p>
        <p><b>核心特性:</b> {attributes[2]}</p>
        <p><b>五行属性:</b> <span style="color:{ELEMENT_COLORS[attributes[3]].name()}">{attributes[3]}</span></p>
        <p><b>方位:</b> {attributes[4]}</p>
        <p><b>解读:</b> {attributes[6]}</p>
        """
        self.attributes_text.setHtml(attributes_text)
        
        # 更新时间运势
        time_text = f"""
        <p><b>近期运势 ({time_analysis['近期']}):</b> 未来7天</p>
        <p><b>中期运势 ({time_analysis['中期']}):</b> 未来1-3个月</p>
        <p><b>长期运势 ({time_analysis['长期']}):</b> 未来6-12个月</p>
        """
        self.time_text.setHtml(time_text)
        
        # 更新五行平衡图
        self.update_elements_chart()
        
        # 更新建议
        advice_text = "<h3>行动建议:</h3><ul>"
        for item in self.divination_widget.advice:
            advice_text += f"<li>{item}</li>"
        advice_text += "</ul>"
        self.advice_text.setHtml(advice_text)
        
        # 更新历史记录
        self.history_list.clear()
        for record in self.divination_widget.history:
            self.history_list.addItem(f"{record['time']} - {record['gua']}卦: {record['question'][:20]}{'...' if len(record['question']) > 20 else ''}")
        
        # 更新状态
        self.status_label.setText(f"卜卦完成 | {gua_name}卦 | {attributes[5]}")
    
    def update_elements_chart(self):
        self.elements_chart.removeAllSeries()
        
        # 创建系列
        series = QLineSeries()
        
        # 添加五行数据
        elements = ["金", "木", "水", "火", "土"]
        values = [self.divination_widget.five_elements[element] for element in elements]
        
        for i, value in enumerate(values):
            series.append(i, value)
        
        # 设置系列样式
        pen = QPen(QColor(0, 210, 255))
        pen.setWidth(3)
        series.setPen(pen)
        
        # 添加系列到图表
        self.elements_chart.addSeries(series)
        
        # 创建X轴
        axis_x = QValueAxis()
        axis_x.setRange(0, 4)
        axis_x.setTickCount(5)
        axis_x.setLabelFormat("%s")
        axis_x.setTitleText("五行")
        axis_x.setLabelsColor(QColor(220, 240, 255))
        axis_x.setTitleBrush(QBrush(QColor(220, 240, 255)))
        
        # 创建Y轴
        axis_y = QValueAxis()
        axis_y.setRange(0, max(values) + 1)
        axis_y.setLabelFormat("%d")
        axis_y.setTitleText("强度")
        axis_y.setLabelsColor(QColor(220, 240, 255))
        axis_y.setTitleBrush(QBrush(QColor(220, 240, 255)))
        
        # 添加轴到图表
        self.elements_chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        self.elements_chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        
        # 将系列附加到轴
        series.attachAxis(axis_x)
        series.attachAxis(axis_y)
        
        # 设置点样式
        for i, element in enumerate(elements):
            color = ELEMENT_COLORS[element]
            series.setMarkerSize(12)
            series.setPointLabelsVisible(True)
            series.setPointLabelsFormat(f"{element} ({values[i]})")
            series.setPointLabelsColor(color)
            series.setPointLabelsFont(QFont("SimHei", 10))
        
        # 更新图表
        self.elements_chart.update()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用字体
    font = QFont("SimHei", 10)
    app.setFont(font)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())