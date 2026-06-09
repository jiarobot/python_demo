import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Button, Slider, RadioButtons
import pygame
import pygame.locals
import sys
import json
import random
import pandas as pd
from scipy.stats import norm
from collections import deque
from mpl_toolkits.mplot3d import Axes3D
import networkx as nx
import seaborn as sns
from textwrap import fill
import matplotlib.patches as mpatches
from matplotlib.collections import PatchCollection
from sklearn.preprocessing import MinMaxScaler
from scipy.integrate import odeint
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
# 初始化pygame
pygame.init()
pygame.mixer.init()

# 全局常量
SESSION_DURATION = 60  # 分钟
FPS = 30

class DietModel:
    """顾客饮食模型"""
    def __init__(self, diet_type="balanced"):
        # 饮食类型: balanced, carnivore, vegetarian, high_sugar, spicy_food
        self.diet_type = diet_type
        self.nutrient_balance = self._init_nutrient_balance()
        self.hydration_level = 0.7  # 水分摄入水平 (0-1)
        self.food_intake = self._generate_food_intake()
        self.toxins = 0.0  # 体内毒素积累
        
    def _init_nutrient_balance(self):
        """根据饮食类型初始化营养平衡"""
        if self.diet_type == "balanced":
            return {'protein': 0.7, 'carbs': 0.6, 'fats': 0.5, 'fiber': 0.7, 'vitamins': 0.8}
        elif self.diet_type == "carnivore":
            return {'protein': 0.9, 'carbs': 0.2, 'fats': 0.8, 'fiber': 0.3, 'vitamins': 0.5}
        elif self.diet_type == "vegetarian":
            return {'protein': 0.5, 'carbs': 0.7, 'fats': 0.4, 'fiber': 0.9, 'vitamins': 0.8}
        elif self.diet_type == "high_sugar":
            return {'protein': 0.4, 'carbs': 0.9, 'fats': 0.6, 'fiber': 0.4, 'vitamins': 0.5}
        else:  # spicy_food
            return {'protein': 0.6, 'carbs': 0.6, 'fats': 0.7, 'fiber': 0.6, 'vitamins': 0.6}
    
    def _generate_food_intake(self):
        """生成近期食物摄入"""
        food_db = {
            'protein': ['牛肉', '鸡肉', '鱼肉', '猪肉', '鸡蛋', '豆腐'],
            'carbs': ['米饭', '面条', '面包', '土豆', '玉米', '甜点'],
            'fats': ['油炸食品', '奶酪', '黄油', '坚果', '牛油果'],
            'fiber': ['蔬菜', '水果', '全谷物', '豆类'],
            'vitamins': ['柑橘类', '绿叶蔬菜', '胡萝卜', '浆果']
        }
        
        # 根据饮食类型选择食物
        intake = {}
        for nutrient in self.nutrient_balance:
            if self.nutrient_balance[nutrient] > 0.6:
                # 该营养素摄入充足
                intake[nutrient] = random.sample(food_db[nutrient], k=2)
            elif self.nutrient_balance[nutrient] < 0.4:
                # 该营养素摄入不足
                intake[nutrient] = random.sample(food_db[nutrient], k=1)
            else:
                intake[nutrient] = random.sample(food_db[nutrient], k=1)
        
        # 特殊饮食添加
        if self.diet_type == "spicy_food":
            intake['spices'] = ['辣椒', '花椒', '姜', '大蒜']
        elif self.diet_type == "high_sugar":
            intake['sweets'] = ['蛋糕', '冰淇淋', '巧克力', '碳酸饮料']
        
        return intake
    
    def calculate_skin_impact(self):
        """计算饮食对皮肤的影响"""
        # 水分影响
        hydration_effect = 0.8 if self.hydration_level > 0.7 else 0.5
        
        # 营养平衡影响
        nutrient_score = (self.nutrient_balance['protein'] * 0.2 +
                         self.nutrient_balance['fats'] * 0.15 +
                         self.nutrient_balance['vitamins'] * 0.3 +
                         self.nutrient_balance['fiber'] * 0.2 +
                         self.nutrient_balance['carbs'] * 0.15)
        
        # 毒素影响
        toxin_effect = 1.0 - min(0.5, self.toxins * 0.8)
        
        # 综合皮肤健康评分
        skin_health = hydration_effect * 0.4 + nutrient_score * 0.5 + toxin_effect * 0.1
        return max(0.3, min(0.95, skin_health))
    
    def calculate_body_odor_impact(self):
        """计算饮食对身体气味的影响"""
        odor_impact = 0.0
        
        # 辛辣食物影响
        if self.diet_type == "spicy_food":
            odor_impact += 0.4
        
        # 高蛋白饮食影响
        if self.nutrient_balance['protein'] > 0.8:
            odor_impact += 0.3
        
        # 高糖饮食影响
        if self.diet_type == "high_sugar":
            odor_impact += 0.3
        
        # 水分不足影响
        if self.hydration_level < 0.5:
            odor_impact += 0.2
        
        return min(1.0, odor_impact)
    
    def update_diet_effects(self, time_since_meal):
        """更新饮食效果"""
        # 随时间减少水分
        self.hydration_level = max(0.3, self.hydration_level - 0.01 * time_since_meal)
        
        # 随时间增加毒素
        if self.diet_type in ["carnivore", "high_sugar"]:
            self.toxins = min(0.8, self.toxins + 0.02 * time_since_meal)
        
        return {
            'skin_impact': self.calculate_skin_impact(),
            'odor_impact': self.calculate_body_odor_impact(),
            'hydration': self.hydration_level,
            'toxins': self.toxins
        }

class MicrobiomeModel:
    """微生物群落模型（增强版，包含饮食影响）"""
    def __init__(self, hygiene_level, diet_impact):
        # 微生物种群初始状态
        self.populations = {
            'staphylococcus': max(0.1, hygiene_level * 0.5),  # 葡萄球菌
            'corynebacterium': max(0.1, (1 - hygiene_level) * 0.7),  # 棒状杆菌
            'micrococcus': max(0.1, hygiene_level * 0.3),  # 微球菌
            'propionibacterium': max(0.1, (1 - hygiene_level) * 0.4),  # 丙酸杆菌
            'dermatophytes': max(0.1, (1 - hygiene_level) * 0.6),  # 皮肤癣菌
            'candida': max(0.1, (1 - hygiene_level) * 0.5)  # 念珠菌
        }
        
        # 饮食影响
        self.diet_impact = diet_impact
        
        # 种群关系参数
        self.interaction_matrix = np.array([
            [1.0, -0.7, -0.5, 0.3, -0.8, -0.6],  # staphylococcus
            [-0.6, 1.0, -0.4, -0.5, 0.2, 0.4],   # corynebacterium
            [-0.4, -0.3, 1.0, 0.1, -0.5, -0.3],  # micrococcus
            [0.2, -0.4, 0.1, 1.0, -0.6, -0.4],   # propionibacterium
            [-0.7, 0.3, -0.6, -0.5, 1.0, 0.5],   # dermatophytes
            [-0.5, 0.4, -0.3, -0.4, 0.6, 1.0]     # candida
        ])
        
        # 代谢产物
        self.metabolites = {
            'isovaleric_acid': 0.0,  # 异戊酸 - 奶酪味
            'acetic_acid': 0.0,      # 乙酸 - 醋味
            'propionic_acid': 0.0,   # 丙酸 - 酸味
            'butyric_acid': 0.0,     # 丁酸 - 腐臭味
            'methanethiol': 0.0,     # 甲硫醇 - 烂白菜味
            'dimethyl_sulfide': 0.0  # 二甲基硫醚 - 海鲜味
        }
        
        # 环境因素
        self.temperature = 0.6  # 0-1 (冷-热)
        self.moisture = 0.5     # 0-1 (干-湿)
        self.ph = 5.8           # 皮肤pH值
        
        # 历史数据
        self.history = []

    def apply_treatment(self, treatment_type, strength):
        """应用抗菌处理"""
        treatment_effects = {
            'antifungal': {
                'dermatophytes': 0.8,
                'candida': 0.7,
                'staphylococcus': 0.2,
                'corynebacterium': 0.1
            },
            'antibacterial': {
                'staphylococcus': 0.9,
                'corynebacterium': 0.8,
                'micrococcus': 0.7,
                'propionibacterium': 0.6,
                'dermatophytes': 0.3,
                'candida': 0.2
            },
            'disinfectant': {
                'staphylococcus': 0.7,
                'corynebacterium': 0.7,
                'micrococcus': 0.7,
                'propionibacterium': 0.7,
                'dermatophytes': 0.5,
                'candida': 0.5
            }
        }
        
        # 应用处理效果
        for microbe, effect in treatment_effects[treatment_type].items():
            reduction = strength * effect
            self.populations[microbe] = max(0.01, self.populations[microbe] * (1 - reduction))
        
        # 更新代谢产物
        self.update_metabolites()
        
        return self.populations

    def get_odor_profile(self):
        """获取气味特征"""
        # 计算总体气味强度
        total_intensity = sum(self.metabolites.values()) / len(self.metabolites)
        
        # 确定主要气味成分
        primary_metabolite = max(self.metabolites, key=self.metabolites.get)
        
        # 气味描述
        odor_descriptions = {
            'isovaleric_acid': "奶酪味",
            'acetic_acid': "醋味",
            'propionic_acid': "酸臭味",
            'butyric_acid': "腐臭味",
            'methanethiol': "烂白菜味",
            'dimethyl_sulfide': "海鲜味"
        }
        
        # 气味类型聚类
        sweet_sour = self.metabolites['isovaleric_acid'] + self.metabolites['acetic_acid']
        rancid = self.metabolites['propionic_acid'] + self.metabolites['butyric_acid']
        sulfur = self.metabolites['methanethiol'] + self.metabolites['dimethyl_sulfide']
        
        # 确定主要气味类别
        odor_category = "其他"
        if max(sweet_sour, rancid, sulfur) == sweet_sour:
            odor_category = "酸甜味"
        elif max(sweet_sour, rancid, sulfur) == rancid:
            odor_category = "腐败味"
        else:
            odor_category = "硫磺味"
        
        return {
            'intensity': total_intensity,
            'primary_component': primary_metabolite,
            'description': odor_descriptions[primary_metabolite],
            'category': odor_category,
            'metabolites': self.metabolites.copy()
        }
    
    def update(self, dt, manipulation_intensity):
        """更新微生物群落状态"""
        # 更新环境参数（受操作影响）
        self.moisture = min(0.95, self.moisture + manipulation_intensity * 0.2)
        self.temperature = min(0.9, self.temperature + manipulation_intensity * 0.1)
        
        # 解微分方程
        t = np.linspace(0, dt, 10)
        pop_array = np.array(list(self.populations.values()))
        solution = odeint(self.derivative, pop_array, t)
        
        # 更新种群数量
        new_populations = solution[-1]
        for i, key in enumerate(self.populations.keys()):
            self.populations[key] = max(0.01, min(0.99, new_populations[i]))
        
        # 更新代谢产物
        self.update_metabolites()
        
        # 记录历史
        self.history.append({
            'time': t[-1],
            'populations': self.populations.copy(),
            'metabolites': self.metabolites.copy(),
            'environment': {
                'temperature': self.temperature,
                'moisture': self.moisture,
                'ph': self.ph
            }
        })
        
        return self.populations, self.metabolites

        
    def derivative(self, populations, t):
        """微生物种群动力学微分方程（包含饮食影响）"""
        # 环境因子
        temp_factor = 0.8 + 0.4 * self.temperature
        moisture_factor = 0.7 + 0.6 * self.moisture
        ph_factor = 1.2 - 0.4 * abs(self.ph - 5.5)
        
        # 饮食影响因子
        diet_factor = 1.0 + self.diet_impact['odor_impact'] * 0.5 - self.diet_impact['skin_impact'] * 0.3
        
        # 种群相互作用
        interactions = np.dot(self.interaction_matrix, populations)
        
        # 增长方程
        growth_rates = np.array([
            0.15,  # staphylococcus
            0.18,  # corynebacterium
            0.12,  # micrococcus
            0.10,  # propionibacterium
            0.20,  # dermatophytes
            0.16   # candida
        ])
        
        # 环境承载能力
        carrying_capacity = np.array([1.0, 0.9, 0.8, 0.7, 0.95, 0.85])
        
        # 微分方程
        dpdt = growth_rates * populations * (1 - populations / carrying_capacity) * interactions
        dpdt *= temp_factor * moisture_factor * ph_factor * diet_factor
        
        return dpdt
    
    # 其他方法保持不变...
    
    def update_metabolites(self):
        """更新微生物代谢产物（包含饮食影响）"""
        # 基础代谢产物产生
        production_rates = {
            'isovaleric_acid': self.populations['staphylococcus'] * 0.8 + self.populations['corynebacterium'] * 0.5,
            'acetic_acid': self.populations['corynebacterium'] * 0.7 + self.populations['propionibacterium'] * 0.6,
            'propionic_acid': self.populations['propionibacterium'] * 0.9,
            'butyric_acid': self.populations['staphylococcus'] * 0.6 + self.populations['dermatophytes'] * 0.4,
            'methanethiol': self.populations['corynebacterium'] * 0.5 + self.populations['micrococcus'] * 0.3,
            'dimethyl_sulfide': self.populations['dermatophytes'] * 0.7 + self.populations['candida'] * 0.5
        }
        
        # 饮食增强效应
        if self.diet_impact['odor_impact'] > 0.5:
            for metabolite in production_rates:
                production_rates[metabolite] *= 1.0 + self.diet_impact['odor_impact'] * 0.8
        
        # 代谢产物降解
        degradation_rates = 0.1  # 所有代谢产物的基础降解率
        
        # 更新代谢产物浓度
        for metabolite in self.metabolites:
            production = production_rates[metabolite]
            degradation = self.metabolites[metabolite] * degradation_rates
            self.metabolites[metabolite] = max(0, min(1, self.metabolites[metabolite] + production - degradation))
        
        return self.metabolites

class FootEcosystem:
    """脚部生态系统模型（增强版，包含饮食影响）"""
    def __init__(self, hygiene_level, diet_model):
        self.hygiene_level = hygiene_level
        self.diet_model = diet_model
        self.diet_impact = diet_model.update_diet_effects(0)
        self.microbiome = MicrobiomeModel(hygiene_level, self.diet_impact)
        self.skin_condition = self._determine_skin_condition()
        self.temperature = 0.6  # 初始温度
        self.moisture = 0.5     # 初始湿度
        
    def _determine_skin_condition(self):
        """根据卫生状况和饮食确定皮肤状态"""
        skin_health = self.diet_impact['skin_impact']
        
        if skin_health > 0.8:
            return "健康"
        elif skin_health > 0.6:
            return random.choice(["干燥", "轻微脱皮"])
        elif skin_health > 0.4:
            return random.choice(["多汗", "轻微角质化"])
        else:
            return random.choice(["严重角质化", "真菌感染", "裂纹"])
    
    def update(self, dt, manipulation_intensity, treatment=None):
        """更新脚部生态系统"""
        # 更新饮食影响
        self.diet_impact = self.diet_model.update_diet_effects(dt)
        
        # 更新微生物群落
        populations, metabolites = self.microbiome.update(dt, manipulation_intensity)
        
        # 应用处理（如果有）
        if treatment:
            self.microbiome.apply_treatment(treatment['type'], treatment['strength'])
        
        # 更新皮肤状况（受微生物和饮食影响）
        if self.microbiome.populations['dermatophytes'] > 0.7:
            self.skin_condition = "真菌感染"
        elif self.microbiome.populations['candida'] > 0.6:
            self.skin_condition = "酵母菌感染"
        elif self.diet_impact['skin_impact'] < 0.5:
            self.skin_condition = "干燥脱皮"
        
        # 更新环境参数
        self.temperature = self.microbiome.temperature
        self.moisture = self.microbiome.moisture
        
        return {
            'populations': populations,
            'metabolites': metabolites,
            'skin_condition': self.skin_condition,
            'odor': self.microbiome.get_odor_profile(),
            'diet_impact': self.diet_impact
        }

class CustomerModel:
    """顾客模型（包含饮食模型）"""
    def __init__(self, customer_type):
        self.customer_type = customer_type
        
        # 饮食类型映射
        diet_types = {
            1: "balanced",      # 安静型 - 均衡饮食
            2: "spicy_food",    # 健谈型 - 喜欢辛辣食物
            3: "balanced",      # 挑剔型 - 均衡饮食
            4: "carnivore",     # 商务型 - 高蛋白饮食
            5: "vegetarian"     # 养生型 - 素食
        }
        
        self.hygiene_level = self._calculate_hygiene(customer_type)
        self.diet_model = DietModel(diet_types.get(customer_type, "balanced"))
        self.foot_ecosystem = FootEcosystem(self.hygiene_level, self.diet_model)
        self.preferences = self._generate_preferences()
        self.satisfaction = 0.7
        self.conversation_topics = self._generate_topics()
        
        # 顾客类型描述
        self.type_descriptions = {
            1: "安静内向型",
            2: "健谈外向型",
            3: "挑剔专业型",
            4: "商务人士型",
            5: "养生达人型"
        }
        
        # 脚部卫生描述
        self.hygiene_descriptions = {
            0.9: "非常干净",
            0.7: "比较干净",
            0.5: "一般卫生",
            0.3: "不太干净",
            0.1: "很不卫生"
        }
        
        # 随机生成卫生状况
        self.hygiene_level = random.uniform(0.4, 0.9)
    
    def _calculate_hygiene(self, customer_type):
        """计算卫生状况"""
        hygiene_base = {
            1: 0.85,  # 安静型
            2: 0.65,  # 健谈型
            3: 0.90,  # 挑剔型
            4: 0.75,  # 商务型
            5: 0.60   # 养生型
        }
        return max(0.1, min(0.99, hygiene_base.get(customer_type, 0.7) * random.uniform(0.8, 1.2)))
    
    def _generate_preferences(self):
        """生成顾客偏好"""
        return {
            'pressure': random.uniform(0.4, 0.9),
            'conversation': random.choice(['light', 'deep', 'none']),
            'focus_area': random.sample(['heel', 'arch', 'toes', 'ankle'], k=2),
            'sensitivity': random.uniform(0.3, 0.8),
            'odor_sensitivity': random.uniform(0.5, 1.0)  # 顾客对自己脚气敏感度
        }
    
    def _generate_topics(self):
        """生成话题库"""
        base_topics = {
            1: ["天气", "新闻", "旅行", "美食", "电影"],
            2: ["家庭", "工作", "育儿", "投资", "社会热点"],
            3: ["足疗技巧", "反射区", "健康养生", "中医理论"],
            4: ["商业趋势", "科技", "管理", "行业动态"],
            5: ["食疗", "运动养生", "心理健康", "传统疗法"]
        }
        return base_topics.get(self.customer_type, ["日常话题"])
    
    def provide_feedback(self, therapist_action, odor_level):
        """根据技师行为和气味提供反馈（考虑饮食）"""
        # 满意度变化模型
        feedback = 0
        
        # 行为匹配度
        if therapist_action['type'] == 'massage':
            pressure_diff = abs(therapist_action['pressure'] - self.preferences['pressure'])
            feedback += (0.6 - pressure_diff * 0.8)
            
            # 关注区域匹配
            if therapist_action['area'] in self.preferences['focus_area']:
                feedback += 0.15
        
        # 顾客对自己脚气的敏感度 (负向影响)
        if self.preferences['odor_sensitivity'] > 0.7 and odor_level > 0.4:
            feedback -= min(0.4, (odor_level - 0.4) * self.preferences['odor_sensitivity'])
        
        # 随机波动
        feedback += random.uniform(-0.1, 0.1)
        
        # 更新满意度 (带惯性)
        self.satisfaction = max(0.1, min(0.99, self.satisfaction * 0.8 + feedback * 0.2))
        
        return {
            'verbal': self._generate_verbal_feedback(self.satisfaction),
            'nonverbal': self._generate_nonverbal_feedback(self.satisfaction)
        }
    
    def get_hygiene_description(self):
        """获取卫生状况描述"""
        hygiene = self.hygiene_level
        for threshold, desc in sorted(self.hygiene_descriptions.items(), reverse=True):
            if hygiene >= threshold:
                return desc
        return "不卫生"
    
    def get_diet_description(self):
        """获取饮食描述"""
        diet_names = {
            "balanced": "均衡饮食",
            "carnivore": "高蛋白饮食",
            "vegetarian": "素食",
            "high_sugar": "高糖饮食",
            "spicy_food": "辛辣饮食"
        }
        return diet_names.get(self.diet_model.diet_type, "未知饮食")

class TherapistMind:
    """技师心理模型（包含饮食影响）"""
    def __init__(self, customer):
        # 核心心理状态
        self.states = {
            'physical_fatigue': 0.0,
            'mental_fatigue': 0.0,
            'focus': 0.85,
            'emotion': 0.7,
            'empathy': 0.5,
            'stress': 0.3,
            'self_efficacy': 0.8,
            'motivation': 0.75,
            'odor_distress': 0.0,
            'hygiene_concern': 0.0,
            'microbial_risk_perception': 0.0
        }
        
        # 外部系统
        self.customer = customer
        self.foot_ecosystem = customer.foot_ecosystem
        
        # 交互状态
        self.current_action = None
        self.last_feedback = None
        self.current_treatment = None
        self.history = []
        
        # 微生物知识库
        self.microbial_knowledge = self._load_microbial_knowledge()

    def _load_microbial_knowledge(self):
        """加载微生物知识库"""
        return {
            'staphylococcus': "常见皮肤细菌，可能引起感染",
            'corynebacterium': "产生脚臭的主要细菌",
            'micrococcus': "常见于皮肤表面，通常无害",
            'propionibacterium': "参与脂肪酸代谢，产生酸味",
            'dermatophytes': "皮肤癣菌，引起脚气",
            'candida': "念珠菌，可能引起酵母菌感染"
        }
        
    def perceive_environment(self, dt):
        """感知环境（包括微生物状态和饮食影响）"""
        # 更新脚部生态系统
        ecosystem_state = self.foot_ecosystem.update(dt, 
                                                   self.current_action.get('pressure', 0) if self.current_action else 0,
                                                   self.current_treatment)
        
        # 更新心理状态（基于微生物信息和饮食影响）
        odor_intensity = ecosystem_state['odor']['intensity']
        infection_risk = (ecosystem_state['populations']['dermatophytes'] + 
                         ecosystem_state['populations']['candida'])
        
        # 气味困扰度（饮食增强效应）
        diet_odor_boost = ecosystem_state['diet_impact']['odor_impact'] * 0.3
        self.states['odor_distress'] = min(1.0, odor_intensity * 0.8 + self.states['hygiene_concern'] * 0.3 + diet_odor_boost)
        
        # 卫生担忧
        self.states['hygiene_concern'] = max(0, min(1, (1 - self.customer.hygiene_level) * 0.7 + infection_risk * 0.5))
        
        # 微生物风险感知
        self.states['microbial_risk_perception'] = infection_risk * 0.9
        
        # 自我效能感（受风险感知影响）
        if self.states['microbial_risk_perception'] > 0.6:
            self.states['self_efficacy'] = max(0.5, self.states['self_efficacy'] - 0.1)
        elif self.current_treatment:
            self.states['self_efficacy'] = min(0.95, self.states['self_efficacy'] + 0.05)
        
        return ecosystem_state
    
    # 其他方法保持不变...

class DietVisualizer:
    """饮食模型可视化系统"""
    def __init__(self, therapist):
        self.therapist = therapist
        self.fig = plt.figure(figsize=(18, 12), facecolor='#f8f9fa')
        self.fig.suptitle("足疗技师心理与饮食影响模拟系统", fontsize=22, color='#2c3e50')
        
        # 使用GridSpec创建复杂布局
        self.gs = gridspec.GridSpec(4, 4, figure=self.fig, 
                           width_ratios=[1.2, 1, 1, 1], 
                           height_ratios=[1, 1, 1.2, 0.4])
        
        # 创建子图
        self.ax_diet = self.fig.add_subplot(self.gs[0, 0])  # 饮食成分分析
        self.ax_nutrients = self.fig.add_subplot(self.gs[0, 1])  # 营养平衡
        self.ax_odor_impact = self.fig.add_subplot(self.gs[0, 2])  # 气味影响
        self.ax_skin_impact = self.fig.add_subplot(self.gs[0, 3])  # 皮肤影响
        
        self.ax_microbiome = self.fig.add_subplot(self.gs[1, 0])  # 微生物种群
        self.ax_metabolites = self.fig.add_subplot(self.gs[1, 1])  # 代谢产物
        self.ax_odor = self.fig.add_subplot(self.gs[1, 2])  # 气味分析
        self.ax_foot = self.fig.add_subplot(self.gs[1, 3])  # 脚部状态
        
        self.ax_psych = self.fig.add_subplot(self.gs[2, 0])  # 心理状态
        self.ax_stress = self.fig.add_subplot(self.gs[2, 1])  # 压力分析
        self.ax_timeline = self.fig.add_subplot(self.gs[2, 2:])  # 时间线
        self.history = []

        # 初始化所有组件
        self._init_diet_view()
        self._init_nutrient_view()
        self._init_odor_impact_view()
        self._init_skin_impact_view()
        self._init_microbiome_view()
        self._init_metabolites_view()
        self._init_odor_analysis_view()
        self._init_foot_view()
        self._init_psych_view()
        self._init_stress_view()
        self._init_timeline()
        
        # 添加控制面板
        self._add_control_panel()
        
        # 动画控制
        self.current_minute = 0
        self.is_paused = False
        self.animation = FuncAnimation(self.fig, self.update, frames=SESSION_DURATION*10, 
                                      interval=1000//FPS, blit=False)
    
    def _init_diet_view(self):
        """初始化饮食成分视图"""
        self.ax_diet.set_title('饮食成分分析', fontsize=14, color='#2c3e50')
        self.ax_diet.set_axis_off()
        
        # 创建食物图标
        self.food_icons = []
        self.food_labels = []
        
        # 饮食类型
        self.diet_type_text = self.ax_diet.text(0.5, 0.9, "", ha='center', fontsize=12,
                                              bbox=dict(facecolor='#e8f4f8', alpha=0.7))
        
        # 食物摄入
        self.food_intake_text = self.ax_diet.text(0.1, 0.7, "近期摄入:", fontsize=10)
        
        # 创建食物图标区域
        self.food_icon_area = self.ax_diet.inset_axes([0.1, 0.1, 0.8, 0.5])
        self.food_icon_area.set_axis_off()
    
    def _update_diet_view(self, food_intake, diet_type):
        """更新饮食成分视图"""
        # 更新饮食类型
        diet_names = {
            "balanced": "均衡饮食",
            "carnivore": "高蛋白饮食",
            "vegetarian": "素食",
            "high_sugar": "高糖饮食",
            "spicy_food": "辛辣饮食"
        }
        self.diet_type_text.set_text(diet_names.get(diet_type, "未知饮食"))
        
        # 清除旧图标
        for icon in self.food_icons:
            icon.remove()
        self.food_icons = []
        
        # 清除旧标签
        for label in self.food_labels:
            label.remove()
        self.food_labels = []
        
        # 显示食物摄入
        all_foods = []
        for category, foods in food_intake.items():
            all_foods.extend(foods)
        
        # 随机排列食物
        random.shuffle(all_foods)
        
        # 显示食物图标（最多8个）
        num_foods = min(8, len(all_foods))
        for i, food in enumerate(all_foods[:num_foods]):
            x = (i % 4) * 0.25 + 0.1
            y = 0.8 - (i // 4) * 0.4
            
            # 创建食物图标（使用文本代替）
            icon = self.food_icon_area.text(x, y, "🍎" if "水果" in food else 
                                          "🍖" if "肉" in food else 
                                          "🍰" if "甜" in food else 
                                          "🌶️" if "辣" in food else "🍽️", 
                                          fontsize=20)
            self.food_icons.append(icon)
            
            # 添加食物标签
            label = self.food_icon_area.text(x, y-0.15, food[:2], ha='center', fontsize=8)
            self.food_labels.append(label)
    
    def _init_nutrient_view(self):
        """初始化营养平衡视图"""
        self.ax_nutrients.set_title('营养平衡', fontsize=14, color='#2c3e50')
        self.ax_nutrients.set_ylim(0, 1)
        self.ax_nutrients.set_xlim(0, 5)
        
        # 创建营养条
        self.nutrient_bars = {}
        nutrients = ['protein', 'carbs', 'fats', 'fiber', 'vitamins']
        labels = ['蛋白质', '碳水', '脂肪', '纤维', '维生素']
        colors = ['#e74c3c', '#3498db', '#f1c40f', '#2ecc71', '#9b59b6']
        
        for i, (nutrient, label, color) in enumerate(zip(nutrients, labels, colors)):
            bar = self.ax_nutrients.bar(i, 0, color=color, width=0.6)
            self.ax_nutrients.text(i, -0.1, label, ha='center', fontsize=9)
            self.nutrient_bars[nutrient] = bar
    
    def _update_nutrient_view(self, nutrient_balance):
        """更新营养平衡视图"""
        for nutrient, bar in self.nutrient_bars.items():
            value = nutrient_balance.get(nutrient, 0)
            bar[0].set_height(value)
            
            # 设置颜色
            if value > 0.8:
                bar[0].set_color('#c0392b' if nutrient == 'protein' else 
                                '#2980b9' if nutrient == 'carbs' else 
                                '#d35400' if nutrient == 'fats' else 
                                '#27ae60' if nutrient == 'fiber' else '#8e44ad')
            else:
                bar[0].set_color('#e74c3c' if nutrient == 'protein' else 
                                '#3498db' if nutrient == 'carbs' else 
                                '#f39c12' if nutrient == 'fats' else 
                                '#2ecc71' if nutrient == 'fiber' else '#9b59b6')
    
    def _init_odor_impact_view(self):
        """初始化气味影响视图"""
        self.ax_odor_impact.set_title('饮食对气味的影响', fontsize=14, color='#2c3e50')
        self.ax_odor_impact.set_ylim(0, 1)
        self.ax_odor_impact.set_xlim(0, 1)
        self.ax_odor_impact.set_axis_off()
        
        # 创建气味影响计
        self.odor_impact_gauge = self.ax_odor_impact.add_patch(plt.Circle((0.5, 0.5), 0.3, fill=True, color='#f8c471'))
        self.odor_impact_text = self.ax_odor_impact.text(0.5, 0.5, "0.0", ha='center', va='center', fontsize=16)
        self.ax_odor_impact.text(0.5, 0.15, "气味影响", ha='center', fontsize=12)
    
    def _update_odor_impact_view(self, odor_impact):
        """更新气味影响视图"""
        # 更新仪表
        color_intensity = min(1.0, odor_impact * 1.5)
        self.odor_impact_gauge.set_color((1.0, 0.8 - color_intensity*0.3, 0.4 - color_intensity*0.2))
        self.odor_impact_text.set_text(f"{odor_impact:.2f}")
        
        # 添加影响描述
        if odor_impact > 0.7:
            impact_desc = "强烈影响"
        elif odor_impact > 0.4:
            impact_desc = "中度影响"
        else:
            impact_desc = "轻微影响"
        self.ax_odor_impact.text(0.5, 0.9, impact_desc, ha='center', fontsize=12, color='#2c3e50')
    
    def _init_skin_impact_view(self):
        """初始化皮肤影响视图"""
        self.ax_skin_impact.set_title('饮食对皮肤的影响', fontsize=14, color='#2c3e50')
        self.ax_skin_impact.set_ylim(0, 1)
        self.ax_skin_impact.set_xlim(0, 1)
        self.ax_skin_impact.set_axis_off()
        
        # 创建皮肤状态指示器
        self.skin_gauge = self.ax_skin_impact.add_patch(plt.Circle((0.5, 0.5), 0.3, fill=True, color='#f9e79f'))
        self.skin_text = self.ax_skin_impact.text(0.5, 0.5, "0.0", ha='center', va='center', fontsize=16)
        self.skin_condition_text = self.ax_skin_impact.text(0.5, 0.15, "", ha='center', fontsize=12)
    
    def _update_skin_impact_view(self, skin_impact, skin_condition):
        """更新皮肤影响视图"""
        # 更新仪表
        self.skin_gauge.set_color((1.0 - skin_impact*0.5, 1.0 - skin_impact*0.2, 0.8 - skin_impact*0.3))
        self.skin_text.set_text(f"{skin_impact:.2f}")
        self.skin_condition_text.set_text(skin_condition)
        
        # 根据皮肤状态设置颜色
        if "感染" in skin_condition:
            self.skin_gauge.set_color('#f5b7b1')
        elif "干燥" in skin_condition or "脱皮" in skin_condition:
            self.skin_gauge.set_color('#f9e79f')
        else:
            self.skin_gauge.set_color('#d5f5e3')
    
    def _init_microbiome_view(self):
        """初始化微生物视图"""
        self.ax_microbiome.set_title('微生物种群动态', fontsize=14, color='#2c3e50')
        self.ax_microbiome.set_ylim(0, 1)
        self.ax_microbiome.set_xlabel('时间 (分钟)')
        self.ax_microbiome.set_ylabel('种群比例')
        self.ax_microbiome.grid(True, alpha=0.3)
        
        # 创建种群曲线
        self.microbe_lines = {}
        colors = ['#3498db', '#e74c3c', '#2ecc71', '#f1c40f', '#9b59b6', '#1abc9c']
        microbes = ['staphylococcus', 'corynebacterium', 'micrococcus', 'propionibacterium', 'dermatophytes', 'candida']
        
        for i, microbe in enumerate(microbes):
            line, = self.ax_microbiome.plot([], [], lw=2, color=colors[i], label=microbe[:10])
            self.microbe_lines[microbe] = line
        
        self.ax_microbiome.legend(loc='upper right', fontsize=8)
    
    def _update_microbiome_view(self, history):
        """更新微生物视图"""
        times = [h['minute'] for h in history]
        
        for microbe, line in self.microbe_lines.items():
            populations = [h['ecosystem']['populations'][microbe] for h in history]
            line.set_data(times, populations)
        
        if times:
            self.ax_microbiome.set_xlim(0, max(times))
            self.ax_microbiome.set_ylim(0, 1.0)
    
    def _init_metabolites_view(self):
        """初始化代谢产物视图"""
        self.ax_metabolites.set_title('代谢产物分析', fontsize=14, color='#2c3e50')
        self.ax_metabolites.set_xticks([])
        self.ax_metabolites.set_yticks([])
        
        # 创建代谢产物雷达图
        self.metabolite_radar, = self.ax_metabolites.plot([], [], 'o-', color='#e67e22', lw=2)
        
        # 添加标签
        metabolites = ['isovaleric_acid', 'acetic_acid', 'propionic_acid', 'butyric_acid', 'methanethiol', 'dimethyl_sulfide']
        angles = np.linspace(0, 2*np.pi, len(metabolites), endpoint=False)
        
        for i, (angle, metabolite) in enumerate(zip(angles, metabolites)):
            x = 0.5 + 0.4 * np.cos(angle)
            y = 0.5 + 0.4 * np.sin(angle)
            self.ax_metabolites.text(x, y, metabolite.split('_')[0], 
                                    ha='center', va='center', fontsize=8, color='#2c3e50')
    
    def _update_metabolites_view(self, metabolites):
        """更新代谢产物视图"""
        metabolite_names = list(metabolites.keys())
        values = list(metabolites.values())
        
        angles = np.linspace(0, 2*np.pi, len(metabolite_names), endpoint=False)
        angles = np.concatenate((angles, [angles[0]]))
        values = np.concatenate((values, [values[0]]))
        
        x = 0.5 + 0.35 * np.cos(angles) * values
        y = 0.5 + 0.35 * np.sin(angles) * values
        
        self.metabolite_radar.set_data(x, y)
    
    def _init_odor_analysis_view(self):
        """初始化气味分析视图"""
        self.ax_odor.set_title('气味特征分析', fontsize=14, color='#2c3e50')
        self.ax_odor.set_xticks([])
        self.ax_odor.set_yticks([])
        
        # 创建气味类别指示器
        self.odor_category = self.ax_odor.text(0.5, 0.7, "", ha='center', fontsize=12,
                                             bbox=dict(facecolor='#d5f5e3', alpha=0.7))
        
        # 创建气味描述
        self.odor_description = self.ax_odor.text(0.5, 0.5, "", ha='center', fontsize=10)
        
        # 创建气味强度条
        self.odor_intensity = self.ax_odor.barh(0.3, 0, color='#f5b7b1', height=0.1)
        self.ax_odor.text(0.1, 0.35, "气味强度", fontsize=9)
    
    def _update_odor_analysis_view(self, odor_profile):
        """更新气味分析视图"""
        self.odor_category.set_text(odor_profile['category'])
        self.odor_description.set_text(f"主要成分: {odor_profile['description']}")
        
        # 更新气味强度条
        self.odor_intensity[0].set_width(odor_profile['intensity'])
        color = '#f5b7b1' if odor_profile['intensity'] > 0.6 else '#f9e79f' if odor_profile['intensity'] > 0.3 else '#d5f5e3'
        self.odor_intensity[0].set_color(color)
    
    def _init_foot_view(self):
        """初始化脚部状态视图"""
        self.ax_foot.set_title('脚部皮肤状态', fontsize=14, color='#2c3e50')
        self.ax_foot.set_axis_off()
        
        # 创建脚部轮廓
        x = np.linspace(-1, 1, 100)
        y = np.sqrt(1 - x**2) * 0.5
        self.foot_outline, = self.ax_foot.plot(x, y, 'k-', lw=2)
        
        # 皮肤状态文本
        self.skin_text = self.ax_foot.text(0, 0.2, "", ha='center', fontsize=12,
                                         bbox=dict(facecolor='#f9e79f', alpha=0.7))
    
    def _update_foot_view(self, skin_condition, hygiene):
        """更新脚部状态视图"""
        # 更新皮肤状态文本
        self.skin_text.set_text(f"{skin_condition}\n卫生: {hygiene}")
        
        # 根据皮肤状态设置颜色
        if "感染" in skin_condition:
            self.foot_outline.set_color('#e74c3c')
        elif "干燥" in skin_condition or "脱皮" in skin_condition:
            self.foot_outline.set_color('#f39c12')
        else:
            self.foot_outline.set_color('#2ecc71')
    
    def _init_psych_view(self):
        """初始化心理状态视图"""
        self.ax_psych.set_title('技师心理状态', fontsize=14, color='#2c3e50')
        self.ax_psych.set_ylim(0, 1)
        self.ax_psych.set_xlim(0, 3)
        self.ax_psych.set_xticks([])
        
        # 创建心理状态条
        self.psych_bars = {}
        states = ['odor_distress', 'hygiene_concern', 'microbial_risk_perception']
        labels = ['气味困扰', '卫生担忧', '感染风险感知']
        colors = ['#e74c3c', '#f39c12', '#8e44ad']
        
        for i, (state, label, color) in enumerate(zip(states, labels, colors)):
            bar = self.ax_psych.bar(i, 0, color=color, width=0.6)
            self.ax_psych.text(i, -0.1, label, ha='center', fontsize=9)
            self.psych_bars[state] = bar
    
    def _update_psych_view(self, states):
        """更新心理状态视图"""
        for state, bar in self.psych_bars.items():
            bar[0].set_height(states.get(state, 0))
    
    def _init_stress_view(self):
        """初始化压力分析视图"""
        self.ax_stress.set_title('压力构成分析', fontsize=14, color='#2c3e50')
        self.ax_stress.set_axis_off()
        
        # 创建饼图
        self.stress_pie = self.ax_stress.pie([], labels=[], autopct='%1.1f%%', 
                                           colors=['#e74c3c', '#3498db', '#f1c40f', '#2ecc71', '#9b59b6', '#1abc9c'])
        
        # 添加标题
        self.stress_title = self.ax_stress.text(0.5, 1.1, "总体压力: 0.0", 
                                              ha='center', fontsize=12, color='#2c3e50')
    
    def _update_stress_view(self, factors, total_stress):
        """更新压力分析视图"""
        # 压力构成
        components = {
            '气味困扰': factors.get('odor_distress', 0) * 0.4,
            '卫生担忧': factors.get('hygiene_concern', 0) * 0.3,
            '感染风险': factors.get('microbial_risk_perception', 0) * 0.3
        }
        
        # 清除旧饼图
        for wedge in self.stress_pie[0]:
            wedge.remove()
        for text in self.stress_pie[1] + self.stress_pie[2]:
            text.remove()
        
        # 创建新饼图
        labels = list(components.keys())
        sizes = list(components.values())
        colors = ['#e74c3c', '#f39c12', '#8e44ad']
        
        self.stress_pie = self.ax_stress.pie(sizes, labels=labels, autopct='%1.1f%%', 
                                           colors=colors, startangle=90)
        
        # 更新标题
        self.stress_title.set_text(f"总体压力: {total_stress:.2f}")
    
    def _init_timeline(self):
        """初始化时间线分析"""
        self.ax_timeline.set_title('时间线分析', fontsize=14, color='#2c3e50')
        self.ax_timeline.set_ylim(0, 1)
        self.ax_timeline.set_xlabel('时间 (分钟)')
        self.ax_timeline.set_ylabel('状态值')
        self.ax_timeline.grid(True, alpha=0.3)
        
        # 创建时间线
        self.timeline_lines = {
            'odor': self.ax_timeline.plot([], [], 'r-', label='气味强度')[0],
            'stress': self.ax_timeline.plot([], [], 'b-', label='压力水平')[0],
            'diet_impact': self.ax_timeline.plot([], [], 'g-', label='饮食影响')[0]
        }
        self.ax_timeline.legend(loc='upper right', fontsize=10)
    
    def _update_timeline(self, history):
        """更新时间线分析"""
        if not history:
            return
        
        times = [h['minute'] for h in history]
        odor = [h['ecosystem']['odor']['intensity'] for h in history]
        stress = [h['states']['stress'] for h in history]
        diet_impact = [h['ecosystem']['diet_impact']['odor_impact'] for h in history]
        
        self.timeline_lines['odor'].set_data(times, odor)
        self.timeline_lines['stress'].set_data(times, stress)
        self.timeline_lines['diet_impact'].set_data(times, diet_impact)
        
        if times:
            self.ax_timeline.set_xlim(0, max(times))
            self.ax_timeline.set_ylim(0, 1.0)
    
    def _add_control_panel(self):
        """添加控制面板"""
        control_gs = gridspec.GridSpecFromSubplotSpec(1, 4, subplot_spec=self.gs[3, :])
        
        # 添加暂停/继续按钮
        ax_pause = self.fig.add_subplot(control_gs[0, 0])
        self.btn_pause = Button(ax_pause, '暂停/继续', color='#3498db', hovercolor='#2980b9')
        self.btn_pause.on_clicked(self.toggle_pause)
        
        # 添加速度滑块
        ax_speed = self.fig.add_subplot(control_gs[0, 1])
        self.slider_speed = Slider(ax_speed, '速度', 0.5, 3.0, valinit=1.0, 
                                 color='#3498db', track_color='#2980b9')
        self.slider_speed.on_changed(self.change_speed)
        
        # 添加干预按钮
        ax_intervene = self.fig.add_subplot(control_gs[0, 2])
        self.btn_intervene = Button(ax_intervene, '应用除臭', color='#2ecc71', hovercolor='#27ae60')
        self.btn_intervene.on_clicked(self.apply_deodorize)
        
        # 添加重置按钮
        ax_reset = self.fig.add_subplot(control_gs[0, 3])
        self.btn_reset = Button(ax_reset, '重置模拟', color='#e74c3c', hovercolor='#c0392b')
        self.btn_reset.on_clicked(self.reset_simulation)
    
    def toggle_pause(self, event):
        """暂停/继续动画"""
        self.is_paused = not self.is_paused
        if not self.is_paused:
            self.animation.event_source.start()
    
    def change_speed(self, val):
        """改变动画速度"""
        self.animation.event_source.interval = 1000 / (val * FPS)
    
    def apply_deodorize(self, event):
        """应用除臭干预"""
        # 应用除臭处理
        self.therapist.current_treatment = {
            'type': 'disinfectant',
            'strength': 0.8
        }
        print("已应用除臭处理")
    
    def reset_simulation(self, event):
        """重置模拟"""
        self.current_minute = 0
        customer = CustomerModel(random.randint(1, 5))
        self.therapist = TherapistMind(customer)
        self.history = []
    
    def update(self, frame):
        """更新可视化界面"""
        if self.is_paused:
            return
        
        # 模拟会话进度
        self.current_minute += 0.1
        
        # 更新系统状态
        ecosystem_state = self.therapist.perceive_environment(0.1)
        state_snapshot = {
            'minute': self.current_minute,
            'states': dict(self.therapist.states),
            'ecosystem': ecosystem_state
        }
        self.history.append(state_snapshot)
        
        # 更新所有视图
        self._update_diet_view(self.therapist.customer.diet_model.food_intake, 
                              self.therapist.customer.diet_model.diet_type)
        self._update_nutrient_view(self.therapist.customer.diet_model.nutrient_balance)
        self._update_odor_impact_view(ecosystem_state['diet_impact']['odor_impact'])
        self._update_skin_impact_view(ecosystem_state['diet_impact']['skin_impact'],
                                     ecosystem_state['skin_condition'])
        self._update_microbiome_view(self.history)
        self._update_metabolites_view(ecosystem_state['metabolites'])
        self._update_odor_analysis_view(ecosystem_state['odor'])
        self._update_foot_view(ecosystem_state['skin_condition'],
                              self.therapist.customer.get_hygiene_description())
        self._update_psych_view(state_snapshot['states'])
        self._update_stress_view(state_snapshot['states'], state_snapshot['states']['stress'])
        self._update_timeline(self.history)
        
        return []

# 主程序
def main():
    # 创建顾客模型
    customer = CustomerModel(random.randint(1, 5))
    
    # 创建技师心理模型
    therapist = TherapistMind(customer)
    
    # 创建可视化系统
    print("启动足疗技师心理与饮食影响模拟系统...")
    print(f"顾客类型: {customer.type_descriptions[customer.customer_type]}")
    print(f"饮食类型: {customer.get_diet_description()}")
    visualizer = DietVisualizer(therapist)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.show()
    
    # 保存数据
    print("\n模拟结束! 保存饮食影响数据...")
    diet_data = []
    for state in therapist.history:
        diet_data.append({
            'minute': state['minute'],
            'diet_impact': state['ecosystem']['diet_impact'],
            'odor': state['ecosystem']['odor'],
            'skin_condition': state['ecosystem']['skin_condition'],
            'stress': state['states']['stress']
        })
    
    df = pd.DataFrame(diet_data)
    df.to_csv('diet_impact_data.csv', index=False)
    
    print("数据已保存到 diet_impact_data.csv")

if __name__ == "__main__":
    main()