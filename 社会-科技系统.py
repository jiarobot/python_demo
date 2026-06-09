import sys
import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec
import networkx as nx
from scipy import stats

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTabWidget, QTableWidget,
                             QTableWidgetItem, QGroupBox, QPushButton, QComboBox,
                             QSpinBox, QDoubleSpinBox, QLabel, QTextEdit, QSlider,
                             QCheckBox, QFileDialog, QMessageBox, QProgressBar)
from PyQt5.QtCore import QTimer, Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor

# 智能体基类
class Agent:
    def __init__(self, agent_id, model):
        self.id = agent_id
        self.model = model
        self.attributes = {}
        
    def step(self):
        pass

# 家庭智能体
class Household(Agent):
    def __init__(self, agent_id, model, age, education, income, location):
        super().__init__(agent_id, model)
        self.attributes = {
            'age': age,
            'education': education,  # 0-1之间，表示教育水平
            'income': income,
            'location': location,  # (x, y)坐标
            'consumption': 0.7 * income,  # 消费占收入的70%
            'savings': random.uniform(1000, 10000),
            'health': random.uniform(0.7, 1.0),
            'happiness': random.uniform(0.5, 0.9),
            'skills': [random.uniform(0.1, 0.8) for _ in range(5)],  # 多种技能
            'employment_status': random.choice(['employed', 'unemployed', 'retired']),
            'energy_consumption': random.uniform(5, 20),  # 能源消耗
            'carbon_footprint': random.uniform(2, 10),  # 碳足迹
            'social_class': random.choice(['low', 'middle', 'high'])  # 社会阶层
        }
        
        # 根据年龄设置就业状态
        if age > 65:
            self.attributes['employment_status'] = 'retired'
        elif age < 18:
            self.attributes['employment_status'] = 'student'
            
    def step(self):
        # 简单的消费行为
        self.attributes['savings'] += self.attributes['income'] - self.attributes['consumption']
        
        # 收入和消费受经济环境影响
        economic_factor = self.model.economic_conditions.get('growth_rate', 0.03)
        inflation_factor = self.model.economic_conditions.get('inflation', 0.02)
        
        # 实际收入增长考虑通货膨胀
        real_income_growth = economic_factor - inflation_factor + random.uniform(-0.02, 0.02)
        self.attributes['income'] *= (1 + real_income_growth)
        self.attributes['consumption'] = 0.7 * self.attributes['income']
        
        # 幸福感受多种因素影响
        health_effect = (self.attributes['health'] - 0.8) * 0.3
        economic_effect = (economic_factor - 0.03) * 0.5
        env_effect = (self.model.environment_quality - 0.7) * 0.2
        
        # 社会阶层影响幸福度
        class_effect = 0
        if self.attributes['social_class'] == 'high':
            class_effect = 0.1
        elif self.attributes['social_class'] == 'low':
            class_effect = -0.1
            
        self.attributes['happiness'] += health_effect + economic_effect + env_effect + class_effect
        self.attributes['happiness'] = max(0.1, min(0.99, self.attributes['happiness']))
        
        # 健康受环境质量影响
        self.attributes['health'] += (self.model.environment_quality - 0.7) * 0.01
        self.attributes['health'] = max(0.1, min(1.0, self.attributes['health']))
        
        # 技能随时间提高（受教育和科技水平影响）
        for i in range(len(self.attributes['skills'])):
            self.attributes['skills'][i] += self.attributes['education'] * 0.001 + self.model.avg_tech_level * 0.0005
            self.attributes['skills'][i] = min(1.0, self.attributes['skills'][i])
            
        # 能源消耗和碳足迹受政策影响
        energy_efficiency = self.model.tech_policy * 0.5
        self.attributes['energy_consumption'] *= (1 - energy_efficiency * 0.01)
        self.attributes['carbon_footprint'] *= (1 - energy_efficiency * 0.01)
        
        # 年龄增长
        self.attributes['age'] += 1/12  # 每月增加年龄
        
        # 教育水平随时间提高（受政策影响）
        self.attributes['education'] += self.model.education_policy * 0.001
        self.attributes['education'] = min(1.0, self.attributes['education'])

# 企业智能体
class Firm(Agent):
    def __init__(self, agent_id, model, sector, size, location):
        super().__init__(agent_id, model)
        self.attributes = {
            'sector': sector,  # 行业类型
            'size': size,  # 企业规模
            'location': location,
            'revenue': size * random.uniform(100000, 500000),
            'employees': size * random.randint(10, 100),
            'productivity': random.uniform(0.8, 1.2),
            'tech_level': random.uniform(0.1, 0.5),  # 技术水平
            'r&d_budget': size * random.uniform(1000, 5000),  # 研发预算
            'energy_consumption': size * random.uniform(10, 50),  # 能源消耗
            'carbon_emissions': size * random.uniform(5, 25),  # 碳排放
            'market_share': random.uniform(0.01, 0.1),  # 市场份额
            'innovation_capability': random.uniform(0.1, 0.5)  # 创新能力
        }
        
    def step(self):
        # 收入受经济环境影响
        economic_factor = self.model.economic_conditions.get('growth_rate', 0.03)
        inflation_factor = self.model.economic_conditions.get('inflation', 0.02)
        tech_effect = self.attributes['tech_level'] * 0.1
        
        # 实际收入增长考虑通货膨胀
        real_revenue_growth = economic_factor + tech_effect - inflation_factor + random.uniform(-0.05, 0.05)
        self.attributes['revenue'] *= (1 + real_revenue_growth)
        
        # 技术水平的增长（受研发预算和政策影响）
        rd_effect = self.attributes['r&d_budget'] / 100000 * 0.01
        policy_effect = self.model.tech_policy * 0.02
        innovation_effect = self.attributes['innovation_capability'] * 0.01
        
        tech_growth = 0.01 + rd_effect + policy_effect + innovation_effect
        self.attributes['tech_level'] += tech_growth
        self.attributes['tech_level'] = min(1.0, self.attributes['tech_level'])
        
        # 生产率随技术提高
        self.attributes['productivity'] += tech_effect * 0.05
        
        # 研发预算随收入增加
        self.attributes['r&d_budget'] = self.attributes['revenue'] * 0.05 * (1 + self.model.tech_policy)
        
        # 能源效率和碳排放受技术水平和政策影响
        energy_efficiency = self.attributes['tech_level'] * 0.5 + self.model.env_policy * 0.3
        self.attributes['energy_consumption'] *= (1 - energy_efficiency * 0.01)
        self.attributes['carbon_emissions'] *= (1 - energy_efficiency * 0.01)
        
        # 创新能力随时间提高（受技术水平和政策影响）
        self.attributes['innovation_capability'] += self.attributes['tech_level'] * 0.001 + self.model.tech_policy * 0.001
        self.attributes['innovation_capability'] = min(1.0, self.attributes['innovation_capability'])
        
        # 市场份额变化（受生产率和创新能力影响）
        market_effect = (self.attributes['productivity'] - 1.0) * 0.01 + self.attributes['innovation_capability'] * 0.005
        self.attributes['market_share'] *= (1 + market_effect)
        self.attributes['market_share'] = min(0.5, self.attributes['market_share'])

# 政府智能体
class Government(Agent):
    def __init__(self, agent_id, model):
        super().__init__(agent_id, model)
        self.attributes = {
            'tax_rate': 0.3,  # 税率
            'tech_budget': 1000000,  # 科技预算
            'env_budget': 500000,  # 环境预算
            'edu_budget': 800000,  # 教育预算
            'infra_budget': 1200000,  # 基础设施预算
            'social_welfare_budget': 600000,  # 社会福利预算
            'approval_rating': 0.6  # 支持率
        }
        
    def step(self):
        # 政府收入来自税收
        total_income = sum(h.attributes['income'] for h in self.model.households)
        total_revenue = sum(f.attributes['revenue'] for f in self.model.firms)
        tax_income = (total_income + total_revenue * 0.2) * self.attributes['tax_rate']
        
        # 预算分配（简化模型）
        total_budget = tax_income
        self.attributes['tech_budget'] = total_budget * 0.2
        self.attributes['env_budget'] = total_budget * 0.15
        self.attributes['edu_budget'] = total_budget * 0.15
        self.attributes['infra_budget'] = total_budget * 0.25
        self.attributes['social_welfare_budget'] = total_budget * 0.25
        
        # 支持率受多种因素影响
        economic_effect = (self.model.economic_conditions.get('growth_rate', 0.03) - 0.03) * 2
        env_effect = (self.model.environment_quality - 0.7) * 0.5
        happiness_effect = (self.model.avg_happiness - 0.7) * 0.5
        
        self.attributes['approval_rating'] += economic_effect + env_effect + happiness_effect
        self.attributes['approval_rating'] = max(0.2, min(0.95, self.attributes['approval_rating']))

# 仿真模型
class SocietyModel:
    def __init__(self):
        self.households = []
        self.firms = []
        self.government = None
        self.current_step = 0
        self.date = datetime(2020, 1, 1)
        
        # 环境参数
        self.environment_quality = 0.8  # 0-1之间，表示环境质量
        self.natural_resources = 1.0  # 0-1之间，表示自然资源丰富度
        self.carbon_concentration = 0.5  # 0-1之间，表示大气碳浓度
        
        # 经济参数
        self.economic_conditions = {
            'growth_rate': 0.03,
            'inflation': 0.02,
            'unemployment': 0.05,
            'interest_rate': 0.04,
            'gini_coefficient': 0.35  # 基尼系数
        }
        
        # 政策参数
        self.tech_policy = 0.5  # 0-1之间，表示科技政策支持度
        self.env_policy = 0.5   # 0-1之间，表示环境政策严格度
        self.education_policy = 0.5  # 0-1之间，表示教育政策支持度
        self.tax_policy = 0.3  # 税率
        
        # 全局指标
        self.total_population = 0
        self.total_gdp = 0
        self.avg_income = 0
        self.avg_happiness = 0
        self.avg_tech_level = 0
        self.total_carbon_emissions = 0
        self.total_energy_consumption = 0
        
        # 历史数据记录
        self.history = {
            'date': [],
            'gdp': [],
            'population': [],
            'environment': [],
            'avg_income': [],
            'avg_happiness': [],
            'tech_level': [],
            'carbon_emissions': [],
            'energy_consumption': [],
            'natural_resources': [],
            'gini_coefficient': [],
            'unemployment': [],
            'inflation': [],
            'government_approval': []
        }
        
    def initialize(self, num_households=100, num_firms=20):
        # 创建家庭智能体
        for i in range(num_households):
            age = random.randint(20, 80)
            education = random.uniform(0.2, 1.0)
            income = random.uniform(20000, 100000)
            location = (random.uniform(0, 100), random.uniform(0, 100))
            household = Household(i, self, age, education, income, location)
            self.households.append(household)
        
        # 创建企业智能体
        sectors = ['Agriculture', 'Manufacturing', 'Services', 'Technology', 'Energy', 'Finance']
        for i in range(num_firms):
            sector = random.choice(sectors)
            size = random.randint(1, 5)  # 企业规模等级
            location = (random.uniform(0, 100), random.uniform(0, 100))
            firm = Firm(i, self, sector, size, location)
            self.firms.append(firm)
            
        # 创建政府
        self.government = Government(0, self)
        
        # 计算初始指标
        self.calculate_metrics()
    
    def calculate_metrics(self):
        # 计算总人口
        self.total_population = len(self.households)
        
        # 计算总收入和企业收入
        total_income = sum(h.attributes['income'] for h in self.households)
        total_revenue = sum(f.attributes['revenue'] for f in self.firms)
        
        # 计算GDP（简化模型）
        self.total_gdp = total_income + total_revenue * 0.3
        
        # 计算平均收入
        self.avg_income = total_income / len(self.households) if self.households else 0
        
        # 计算平均幸福度
        self.avg_happiness = sum(h.attributes['happiness'] for h in self.households) / len(self.households) if self.households else 0
        
        # 计算平均技术水平
        self.avg_tech_level = sum(f.attributes['tech_level'] for f in self.firms) / len(self.firms) if self.firms else 0
        
        # 计算总碳排放
        household_emissions = sum(h.attributes['carbon_footprint'] for h in self.households)
        firm_emissions = sum(f.attributes['carbon_emissions'] for f in self.firms)
        self.total_carbon_emissions = household_emissions + firm_emissions
        
        # 计算总能源消耗
        household_energy = sum(h.attributes['energy_consumption'] for h in self.households)
        firm_energy = sum(f.attributes['energy_consumption'] for f in self.firms)
        self.total_energy_consumption = household_energy + firm_energy
        
        # 计算基尼系数（简化）
        incomes = [h.attributes['income'] for h in self.households]
        if incomes:
            sorted_incomes = sorted(incomes)
            n = len(incomes)
            cum_income = np.cumsum(sorted_incomes)
            self.economic_conditions['gini_coefficient'] = (n + 1 - 2 * np.sum(cum_income) / cum_income[-1]) / n
        
        # 计算失业率（简化）
        employed = sum(1 for h in self.households if h.attributes['employment_status'] == 'employed')
        workforce = sum(1 for h in self.households if h.attributes['age'] >= 18 and h.attributes['age'] <= 65)
        self.economic_conditions['unemployment'] = 1 - (employed / workforce) if workforce > 0 else 0.05
    
    def step(self):
        self.current_step += 1
        self.date += timedelta(days=30)  # 每月一步
        
        # 更新所有智能体
        for household in self.households:
            household.step()
            
        for firm in self.firms:
            firm.step()
            
        if self.government:
            self.government.step()
            
        # 环境质量变化
        pollution = self.total_carbon_emissions * 0.0001
        env_improvement = self.env_policy * 0.02 + (self.government.attributes['env_budget'] / 1000000) * 0.001
        self.environment_quality += env_improvement - pollution
        self.environment_quality = max(0.1, min(1.0, self.environment_quality))
        
        # 自然资源消耗
        resource_consumption = self.total_energy_consumption * 0.00005
        self.natural_resources -= resource_consumption
        self.natural_resources = max(0.1, self.natural_resources)
        
        # 碳浓度变化
        carbon_addition = self.total_carbon_emissions * 0.00002
        carbon_absorption = self.environment_quality * 0.01
        self.carbon_concentration += carbon_addition - carbon_absorption
        self.carbon_concentration = max(0.1, min(1.0, self.carbon_concentration))
        
        # 通货膨胀受多种因素影响
        demand_pull = (self.economic_conditions['growth_rate'] - 0.03) * 0.1
        cost_push = (1 - self.natural_resources) * 0.05
        self.economic_conditions['inflation'] = 0.02 + demand_pull + cost_push + random.uniform(-0.01, 0.01)
        self.economic_conditions['inflation'] = max(0.01, min(0.2, self.economic_conditions['inflation']))
        
        # 重新计算所有指标
        self.calculate_metrics()
        
        # 记录历史数据
        self.history['date'].append(self.date)
        self.history['gdp'].append(self.total_gdp)
        self.history['population'].append(self.total_population)
        self.history['environment'].append(self.environment_quality)
        self.history['avg_income'].append(self.avg_income)
        self.history['avg_happiness'].append(self.avg_happiness)
        self.history['tech_level'].append(self.avg_tech_level)
        self.history['carbon_emissions'].append(self.total_carbon_emissions)
        self.history['energy_consumption'].append(self.total_energy_consumption)
        self.history['natural_resources'].append(self.natural_resources)
        self.history['gini_coefficient'].append(self.economic_conditions['gini_coefficient'])
        self.history['unemployment'].append(self.economic_conditions['unemployment'])
        self.history['inflation'].append(self.economic_conditions['inflation'])
        self.history['government_approval'].append(self.government.attributes['approval_rating'] if self.government else 0.5)
        
        # 人口自然变化
        birth_prob = 0.01 - (self.avg_income / 100000) * 0.005  # 收入越高，生育率越低
        if random.random() < birth_prob:  # 新增人口
            age = 0
            education = 0.1
            income = 0
            location = (random.uniform(0, 100), random.uniform(0, 100))
            new_household = Household(len(self.households), self, age, education, income, location)
            self.households.append(new_household)
            
        # 人口减少（死亡）
        for household in self.households[:]:
            death_prob = 0.001
            if household.attributes['age'] > 75:
                death_prob = 0.05
            elif household.attributes['age'] > 65:
                death_prob = 0.02
                
            # 健康影响死亡概率
            death_prob *= (1.5 - household.attributes['health'])
            
            if random.random() < death_prob:
                self.households.remove(household)
                
        # 企业创建和破产
        if random.random() < 0.02:  # 新企业创建
            sectors = ['Agriculture', 'Manufacturing', 'Services', 'Technology', 'Energy', 'Finance']
            sector = random.choice(sectors)
            size = random.randint(1, 3)
            location = (random.uniform(0, 100), random.uniform(0, 100))
            new_firm = Firm(len(self.firms), self, sector, size, location)
            self.firms.append(new_firm)
            
        for firm in self.firms[:]:
            bankruptcy_prob = 0.01
            if firm.attributes['revenue'] < firm.attributes['size'] * 50000:
                bankruptcy_prob = 0.1
                
            if random.random() < bankruptcy_prob:
                self.firms.remove(firm)

# 仿真线程（用于后台运行仿真）
class SimulationThread(QThread):
    update_signal = pyqtSignal()
    finished_signal = pyqtSignal()
    
    def __init__(self, model, steps):
        super().__init__()
        self.model = model
        self.steps = steps
        self.is_running = True
        
    def run(self):
        for i in range(self.steps):
            if not self.is_running:
                break
            self.model.step()
            self.update_signal.emit()
            self.msleep(100)  # 稍微延迟，避免界面卡死
        self.finished_signal.emit()
        
    def stop(self):
        self.is_running = False

# 可视化画布
class SimulationCanvas(FigureCanvas):
    def __init__(self, parent=None, width=8, height=6, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        
        # 创建多个子图
        self.gs = GridSpec(2, 2, figure=self.fig)
        self.ax1 = self.fig.add_subplot(self.gs[0, 0])  # 经济指标
        self.ax2 = self.fig.add_subplot(self.gs[0, 1])  # 社会指标
        self.ax3 = self.fig.add_subplot(self.gs[1, 0])  # 环境指标
        self.ax4 = self.fig.add_subplot(self.gs[1, 1])  # 技术指标
        
        self.model = None
        
    def set_model(self, model):
        self.model = model
        
    def update_plot(self):
        if not self.model or not self.model.history['date']:
            return
            
        dates = self.model.history['date']
        
        # 清除所有子图
        self.ax1.clear()
        self.ax2.clear()
        self.ax3.clear()
        self.ax4.clear()
        
        # 子图1: 经济指标
        gdp = self.model.history['gdp']
        income = self.model.history['avg_income']
        inflation = self.model.history['inflation']
        unemployment = self.model.history['unemployment']
        
        # 标准化数据
        gdp_norm = [x / max(gdp) for x in gdp] if max(gdp) > 0 else gdp
        income_norm = [x / max(income) for x in income] if max(income) > 0 else income
        
        self.ax1.plot(dates, gdp_norm, label='GDP (标准化)', linewidth=2)
        self.ax1.plot(dates, income_norm, label='平均收入 (标准化)', linewidth=2)
        self.ax1.plot(dates, inflation, label='通货膨胀率', linewidth=2)
        self.ax1.plot(dates, unemployment, label='失业率', linewidth=2)
        self.ax1.set_title('经济指标')
        self.ax1.legend()
        self.ax1.grid(True, alpha=0.3)
        
        # 子图2: 社会指标
        happiness = self.model.history['avg_happiness']
        population = self.model.history['population']
        gini = self.model.history['gini_coefficient']
        approval = self.model.history['government_approval']
        
        # 标准化人口数据
        pop_norm = [x / max(population) for x in population] if max(population) > 0 else population
        
        self.ax2.plot(dates, happiness, label='平均幸福度', linewidth=2)
        self.ax2.plot(dates, pop_norm, label='人口 (标准化)', linewidth=2)
        self.ax2.plot(dates, gini, label='基尼系数', linewidth=2)
        self.ax2.plot(dates, approval, label='政府支持率', linewidth=2)
        self.ax2.set_title('社会指标')
        self.ax2.legend()
        self.ax2.grid(True, alpha=0.3)
        
        # 子图3: 环境指标
        environment = self.model.history['environment']
        carbon = self.model.history['carbon_emissions']
        resources = self.model.history['natural_resources']
        energy = self.model.history['energy_consumption']
        
        # 标准化碳排放和能源消耗数据
        carbon_norm = [x / max(carbon) for x in carbon] if max(carbon) > 0 else carbon
        energy_norm = [x / max(energy) for x in energy] if max(energy) > 0 else energy
        
        self.ax3.plot(dates, environment, label='环境质量', linewidth=2)
        self.ax3.plot(dates, carbon_norm, label='碳排放 (标准化)', linewidth=2)
        self.ax3.plot(dates, resources, label='自然资源', linewidth=2)
        self.ax3.plot(dates, energy_norm, label='能源消耗 (标准化)', linewidth=2)
        self.ax3.set_title('环境指标')
        self.ax3.legend()
        self.ax3.grid(True, alpha=0.3)
        
        # 子图4: 技术指标
        tech = self.model.history['tech_level']
        
        self.ax4.plot(dates, tech, label='技术水平', linewidth=2, color='purple')
        self.ax4.set_title('技术发展')
        self.ax4.legend()
        self.ax4.grid(True, alpha=0.3)
        
        # 格式化日期显示
        for ax in [self.ax1, self.ax2, self.ax3, self.ax4]:
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        
        self.fig.tight_layout()
        self.draw()

# 智能体分布画布
class AgentDistributionCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        
        self.axes = self.fig.add_subplot(111)
        self.model = None
        
    def set_model(self, model):
        self.model = model
        
    def update_plot(self):
        if not self.model or not self.model.households:
            return
            
        self.axes.clear()
        
        # 提取家庭收入数据
        incomes = [h.attributes['income'] for h in self.model.households]
        
        # 绘制收入分布直方图
        self.axes.hist(incomes, bins=20, alpha=0.7, color='blue', edgecolor='black')
        self.axes.set_xlabel('收入')
        self.axes.set_ylabel('频数')
        self.axes.set_title('家庭收入分布')
        self.axes.grid(True, alpha=0.3)
        
        # 添加平均线
        avg_income = np.mean(incomes)
        self.axes.axvline(avg_income, color='red', linestyle='--', label=f'平均收入: ${avg_income:,.0f}')
        self.axes.legend()
        
        self.draw()

# 网络可视化画布
class NetworkCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        
        self.axes = self.fig.add_subplot(111)
        self.model = None
        
    def set_model(self, model):
        self.model = model
        
    def update_plot(self):
        if not self.model or not self.model.firms:
            return
            
        self.axes.clear()
        
        # 创建行业网络图
        G = nx.Graph()
        
        # 按行业分组企业
        sectors = {}
        for firm in self.model.firms:
            sector = firm.attributes['sector']
            if sector not in sectors:
                sectors[sector] = []
            sectors[sector].append(firm)
        
        # 添加节点（行业）
        for sector in sectors:
            G.add_node(sector, size=len(sectors[sector]))
        
        # 添加边（行业间的关联，简化模型）
        sector_list = list(sectors.keys())
        for i, sector1 in enumerate(sector_list):
            for sector2 in sector_list[i+1:]:
                # 随机添加边，实际应用中应根据实际关联性
                if random.random() < 0.5:
                    G.add_edge(sector1, sector2, weight=random.uniform(0.1, 1.0))
        
        # 绘制网络图
        pos = nx.spring_layout(G)
        node_sizes = [G.nodes[node]['size'] * 100 for node in G.nodes()]
        edge_widths = [G[u][v]['weight'] * 2 for u, v in G.edges()]
        
        nx.draw_networkx_nodes(G, pos, node_size=node_sizes, node_color='lightblue', alpha=0.7, ax=self.axes)
        nx.draw_networkx_edges(G, pos, width=edge_widths, alpha=0.5, edge_color='gray', ax=self.axes)
        nx.draw_networkx_labels(G, pos, font_size=10, ax=self.axes)
        
        self.axes.set_title('行业关联网络')
        self.axes.axis('off')
        
        self.draw()

# 主界面
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.model = SocietyModel()
        self.initUI()
        self.timer = QTimer()
        self.timer.timeout.connect(self.step_simulation)
        self.simulation_speed = 500  # 毫秒
        self.simulation_thread = None
        
    def initUI(self):
        self.setWindowTitle('增强版社会-科技系统仿真平台')
        self.setGeometry(100, 100, 1400, 900)
        
        # 中央部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧控制面板
        control_panel = QWidget()
        control_layout = QVBoxLayout(control_panel)
        control_panel.setMaximumWidth(350)
        
        # 仿真控制组
        control_group = QGroupBox("仿真控制")
        control_group_layout = QVBoxLayout(control_group)
        
        self.start_button = QPushButton("开始")
        self.start_button.clicked.connect(self.start_simulation)
        control_group_layout.addWidget(self.start_button)
        
        self.pause_button = QPushButton("暂停")
        self.pause_button.clicked.connect(self.pause_simulation)
        control_group_layout.addWidget(self.pause_button)
        
        self.reset_button = QPushButton("重置")
        self.reset_button.clicked.connect(self.reset_simulation)
        control_group_layout.addWidget(self.reset_button)
        
        self.fast_forward_check = QCheckBox("快速模式（无界面更新）")
        control_group_layout.addWidget(self.fast_forward_check)
        
        steps_label = QLabel("快速模式步数:")
        control_group_layout.addWidget(steps_label)
        
        self.steps_spin = QSpinBox()
        self.steps_spin.setRange(10, 1000)
        self.steps_spin.setValue(100)
        control_group_layout.addWidget(self.steps_spin)
        
        self.fast_forward_button = QPushButton("执行快速仿真")
        self.fast_forward_button.clicked.connect(self.fast_forward_simulation)
        control_group_layout.addWidget(self.fast_forward_button)
        
        speed_label = QLabel("仿真速度:")
        control_group_layout.addWidget(speed_label)
        
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setMinimum(100)
        self.speed_slider.setMaximum(2000)
        self.speed_slider.setValue(500)
        self.speed_slider.valueChanged.connect(self.change_speed)
        control_group_layout.addWidget(self.speed_slider)
        
        control_layout.addWidget(control_group)
        
        # 参数设置组
        params_group = QGroupBox("系统参数")
        params_layout = QVBoxLayout(params_group)
        
        tech_policy_label = QLabel("科技政策支持度:")
        params_layout.addWidget(tech_policy_label)
        
        self.tech_policy_spin = QDoubleSpinBox()
        self.tech_policy_spin.setRange(0.0, 1.0)
        self.tech_policy_spin.setSingleStep(0.1)
        self.tech_policy_spin.setValue(0.5)
        self.tech_policy_spin.valueChanged.connect(self.update_parameters)
        params_layout.addWidget(self.tech_policy_spin)
        
        env_policy_label = QLabel("环境政策严格度:")
        params_layout.addWidget(env_policy_label)
        
        self.env_policy_spin = QDoubleSpinBox()
        self.env_policy_spin.setRange(0.0, 1.0)
        self.env_policy_spin.setSingleStep(0.1)
        self.env_policy_spin.setValue(0.5)
        self.env_policy_spin.valueChanged.connect(self.update_parameters)
        params_layout.addWidget(self.env_policy_spin)
        
        education_policy_label = QLabel("教育政策支持度:")
        params_layout.addWidget(education_policy_label)
        
        self.education_policy_spin = QDoubleSpinBox()
        self.education_policy_spin.setRange(0.0, 1.0)
        self.education_policy_spin.setSingleStep(0.1)
        self.education_policy_spin.setValue(0.5)
        self.education_policy_spin.valueChanged.connect(self.update_parameters)
        params_layout.addWidget(self.education_policy_spin)
        
        tax_policy_label = QLabel("税率:")
        params_layout.addWidget(tax_policy_label)
        
        self.tax_policy_spin = QDoubleSpinBox()
        self.tax_policy_spin.setRange(0.1, 0.5)
        self.tax_policy_spin.setSingleStep(0.05)
        self.tax_policy_spin.setValue(0.3)
        self.tax_policy_spin.valueChanged.connect(self.update_parameters)
        params_layout.addWidget(self.tax_policy_spin)
        
        economic_growth_label = QLabel("初始经济增长率:")
        params_layout.addWidget(economic_growth_label)
        
        self.economic_growth_spin = QDoubleSpinBox()
        self.economic_growth_spin.setRange(-0.1, 0.2)
        self.economic_growth_spin.setSingleStep(0.01)
        self.economic_growth_spin.setValue(0.03)
        self.economic_growth_spin.valueChanged.connect(self.update_parameters)
        params_layout.addWidget(self.economic_growth_spin)
        
        control_layout.addWidget(params_group)
        
        # 数据操作组
        data_group = QGroupBox("数据操作")
        data_layout = QVBoxLayout(data_group)
        
        self.export_button = QPushButton("导出数据到CSV")
        self.export_button.clicked.connect(self.export_data)
        data_layout.addWidget(self.export_button)
        
        self.import_button = QPushButton("从CSV导入数据")
        self.import_button.clicked.connect(self.import_data)
        data_layout.addWidget(self.import_button)
        
        self.save_button = QPushButton("保存当前状态")
        self.save_button.clicked.connect(self.save_state)
        data_layout.addWidget(self.save_button)
        
        self.load_button = QPushButton("加载已保存状态")
        self.load_button.clicked.connect(self.load_state)
        data_layout.addWidget(self.load_button)
        
        control_layout.addWidget(data_group)
        
        # 状态信息组
        status_group = QGroupBox("当前状态")
        status_layout = QVBoxLayout(status_group)
        
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        status_layout.addWidget(self.status_text)
        
        # 进度条
        self.progress_bar = QProgressBar()
        status_layout.addWidget(self.progress_bar)
        
        control_layout.addWidget(status_group)
        control_layout.addStretch()
        
        # 右侧可视化区域
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        
        # 指标标签页
        indicator_tab = QWidget()
        indicator_layout = QVBoxLayout(indicator_tab)
        self.canvas = SimulationCanvas(self, width=10, height=8, dpi=100)
        self.canvas.set_model(self.model)
        indicator_layout.addWidget(self.canvas)
        self.tab_widget.addTab(indicator_tab, "综合指标")
        
        # 分布标签页
        distribution_tab = QWidget()
        distribution_layout = QVBoxLayout(distribution_tab)
        self.distribution_canvas = AgentDistributionCanvas(self, width=10, height=6, dpi=100)
        self.distribution_canvas.set_model(self.model)
        distribution_layout.addWidget(self.distribution_canvas)
        self.tab_widget.addTab(distribution_tab, "收入分布")
        
        # 网络标签页
        network_tab = QWidget()
        network_layout = QVBoxLayout(network_tab)
        self.network_canvas = NetworkCanvas(self, width=10, height=6, dpi=100)
        self.network_canvas.set_model(self.model)
        network_layout.addWidget(self.network_canvas)
        self.tab_widget.addTab(network_tab, "行业网络")
        
        right_layout.addWidget(self.tab_widget)
        
        # 数据表格区域
        self.data_table = QTableWidget()
        self.data_table.setColumnCount(8)
        self.data_table.setHorizontalHeaderLabels(['日期', 'GDP', '人口', '环境', '平均收入', '幸福度', '技术', '支持率'])
        right_layout.addWidget(self.data_table)
        
        # 添加到主布局
        main_layout.addWidget(control_panel)
        main_layout.addWidget(right_widget)
        
        # 初始化模型
        self.model.initialize()
        self.update_parameters()
        self.update_status()
        
    def start_simulation(self):
        if self.fast_forward_check.isChecked():
            self.fast_forward_simulation()
        else:
            self.timer.start(self.simulation_speed)
        
    def pause_simulation(self):
        if self.simulation_thread and self.simulation_thread.isRunning():
            self.simulation_thread.stop()
        else:
            self.timer.stop()
        
    def reset_simulation(self):
        self.pause_simulation()
        self.model = SocietyModel()
        self.model.initialize()
        self.canvas.set_model(self.model)
        self.distribution_canvas.set_model(self.model)
        self.network_canvas.set_model(self.model)
        self.update_parameters()
        self.update_status()
        self.canvas.update_plot()
        self.distribution_canvas.update_plot()
        self.network_canvas.update_plot()
        self.update_table()
        
    def step_simulation(self):
        self.model.step()
        self.update_status()
        self.canvas.update_plot()
        self.distribution_canvas.update_plot()
        self.network_canvas.update_plot()
        self.update_table()
        
    def fast_forward_simulation(self):
        steps = self.steps_spin.value()
        self.progress_bar.setMaximum(steps)
        self.progress_bar.setValue(0)
        
        # 使用线程进行快速仿真
        self.simulation_thread = SimulationThread(self.model, steps)
        self.simulation_thread.update_signal.connect(self.update_progress)
        self.simulation_thread.finished_signal.connect(self.simulation_finished)
        self.simulation_thread.start()
        
    def update_progress(self):
        self.progress_bar.setValue(self.progress_bar.value() + 1)
        
    def simulation_finished(self):
        self.update_status()
        self.canvas.update_plot()
        self.distribution_canvas.update_plot()
        self.network_canvas.update_plot()
        self.update_table()
        self.progress_bar.setValue(0)
        
    def change_speed(self, value):
        self.simulation_speed = value
        if self.timer.isActive():
            self.timer.start(self.simulation_speed)
            
    def update_parameters(self):
        self.model.tech_policy = self.tech_policy_spin.value()
        self.model.env_policy = self.env_policy_spin.value()
        self.model.education_policy = self.education_policy_spin.value()
        self.model.tax_policy = self.tax_policy_spin.value()
        self.model.economic_conditions['growth_rate'] = self.economic_growth_spin.value()
        
        if self.model.government:
            self.model.government.attributes['tax_rate'] = self.model.tax_policy
        
    def update_status(self):
        gov = self.model.government
        approval_rating = gov.attributes['approval_rating']*100 if gov else 0
        tech_budget = gov.attributes['tech_budget'] if gov else 0
        env_budget = gov.attributes['env_budget'] if gov else 0
        edu_budget = gov.attributes['edu_budget'] if gov else 0

        status_text = f"""
        仿真步数: {self.model.current_step}
        当前日期: {self.model.date.strftime('%Y-%m-%d')}

        人口统计:
        总人口: {len(self.model.households)}
        平均年龄: {sum(h.attributes['age'] for h in self.model.households) / len(self.model.households) if self.model.households else 0:.1f}
        平均收入: ${sum(h.attributes['income'] for h in self.model.households) / len(self.model.households) if self.model.households else 0:,.0f}
        平均幸福度: {sum(h.attributes['happiness'] for h in self.model.households) / len(self.model.households) if self.model.households else 0:.3f}
        失业率: {self.model.economic_conditions['unemployment']*100:.1f}%
        基尼系数: {self.model.economic_conditions['gini_coefficient']:.3f}

        经济指标:
        企业数量: {len(self.model.firms)}
        GDP: ${self.model.total_gdp:,.0f}
        通货膨胀率: {self.model.economic_conditions['inflation']*100:.1f}%
        平均技术水平: {self.model.avg_tech_level:.3f}

        环境指标:
        环境质量: {self.model.environment_quality:.3f}
        自然资源: {self.model.natural_resources:.3f}
        碳排放: {self.model.total_carbon_emissions:,.1f}
        能源消耗: {self.model.total_energy_consumption:,.1f}

        政府指标:
        支持率: {approval_rating:.1f}%
        科技预算: ${tech_budget:,.0f}
        环境预算: ${env_budget:,.0f}
        教育预算: ${edu_budget:,.0f}
        """

        self.status_text.setPlainText(status_text)
        
    def update_table(self):
        if not self.model.history['date']:
            return
            
        # 只显示最后20行数据
        start_idx = max(0, len(self.model.history['date']) - 20)
        rows = len(self.model.history['date']) - start_idx
        
        self.data_table.setRowCount(rows)
        
        for i in range(rows):
            idx = start_idx + i
            date_item = QTableWidgetItem(self.model.history['date'][idx].strftime('%Y-%m-%d'))
            gdp_item = QTableWidgetItem(f"${self.model.history['gdp'][idx]:,.0f}")
            population_item = QTableWidgetItem(str(self.model.history['population'][idx]))
            environment_item = QTableWidgetItem(f"{self.model.history['environment'][idx]:.3f}")
            income_item = QTableWidgetItem(f"${self.model.history['avg_income'][idx]:,.0f}")
            happiness_item = QTableWidgetItem(f"{self.model.history['avg_happiness'][idx]:.3f}")
            tech_item = QTableWidgetItem(f"{self.model.history['tech_level'][idx]:.3f}")
            approval_item = QTableWidgetItem(f"{self.model.history['government_approval'][idx]:.3f}")
            
            self.data_table.setItem(i, 0, date_item)
            self.data_table.setItem(i, 1, gdp_item)
            self.data_table.setItem(i, 2, population_item)
            self.data_table.setItem(i, 3, environment_item)
            self.data_table.setItem(i, 4, income_item)
            self.data_table.setItem(i, 5, happiness_item)
            self.data_table.setItem(i, 6, tech_item)
            self.data_table.setItem(i, 7, approval_item)
            
    def export_data(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "导出数据", "", "CSV文件 (*.csv)")
        if file_path:
            try:
                # 将历史数据转换为DataFrame
                df = pd.DataFrame(self.model.history)
                df.to_csv(file_path, index=False)
                QMessageBox.information(self, "成功", "数据已成功导出")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出数据时出错: {str(e)}")
                
    def import_data(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "导入数据", "", "CSV文件 (*.csv)")
        if file_path:
            try:
                # 从CSV文件读取数据
                df = pd.read_csv(file_path)
                # 转换日期列
                df['date'] = pd.to_datetime(df['date'])
                # 更新模型历史数据
                for col in df.columns:
                    if col in self.model.history:
                        self.model.history[col] = df[col].tolist()
                
                # 更新当前状态
                if self.model.history['date']:
                    self.model.date = self.model.history['date'][-1]
                    self.model.current_step = len(self.model.history['date'])
                
                QMessageBox.information(self, "成功", "数据已成功导入")
                self.update_status()
                self.canvas.update_plot()
                self.update_table()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导入数据时出错: {str(e)}")
                
    def save_state(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "保存状态", "", "NPZ文件 (*.npz)")
        if file_path:
            try:
                # 保存模型状态
                np.savez(file_path, 
                         current_step=self.model.current_step,
                         date=self.model.date,
                         environment_quality=self.model.environment_quality,
                         natural_resources=self.model.natural_resources,
                         carbon_concentration=self.model.carbon_concentration,
                         economic_conditions=self.model.economic_conditions,
                         tech_policy=self.model.tech_policy,
                         env_policy=self.model.env_policy,
                         education_policy=self.model.education_policy,
                         tax_policy=self.model.tax_policy)
                QMessageBox.information(self, "成功", "状态已成功保存")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存状态时出错: {str(e)}")
                
    def load_state(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "加载状态", "", "NPZ文件 (*.npz)")
        if file_path:
            try:
                # 加载模型状态
                data = np.load(file_path, allow_pickle=True)
                self.model.current_step = data['current_step'].item()
                self.model.date = data['date'].item()
                self.model.environment_quality = data['environment_quality'].item()
                self.model.natural_resources = data['natural_resources'].item()
                self.model.carbon_concentration = data['carbon_concentration'].item()
                self.model.economic_conditions = data['economic_conditions'].item()
                self.model.tech_policy = data['tech_policy'].item()
                self.model.env_policy = data['env_policy'].item()
                self.model.education_policy = data['education_policy'].item()
                self.model.tax_policy = data['tax_policy'].item()
                
                QMessageBox.information(self, "成功", "状态已成功加载")
                self.update_status()
                self.canvas.update_plot()
                self.update_table()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载状态时出错: {str(e)}")

# 运行应用
if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())