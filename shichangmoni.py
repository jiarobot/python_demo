# -*- coding: utf-8 -*-
"""
Created on Mon Jun 16 22:56:35 2025

@author: 10166
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Slider, Button
from sklearn.cluster import KMeans
import pandas as pd
import time
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
# ======================
# 市场环境模拟
# ======================
class MarketEnvironment:
    def __init__(self, num_firms=20, market_size=1000):
        self.num_firms = num_firms
        self.market_size = market_size
        self.firms = self._initialize_firms()
        self.price_sensitivity = 0.8
        self.tech_sensitivity = 1.2
        self.market_sensitivity = 0.7
        
    def _initialize_firms(self):
        return [{
            'id': i,
            'price': np.random.uniform(50, 150),
            'tech': np.random.uniform(0.1, 0.5),
            'marketing': np.random.uniform(0.1, 0.5),
            'cost': np.random.uniform(30, 70),
            'profit': 0,
            'market_share': 1/self.num_firms,
            'strategy_history': []
        } for i in range(self.num_firms)]
    
    def calculate_demand(self, firm):
        # 市场需求函数（Logit模型）
        utility = (
            -self.price_sensitivity * firm['price'] 
            + self.tech_sensitivity * firm['tech']**0.7
            + self.market_sensitivity * firm['marketing']**0.5
        )
        return max(0.01, np.exp(utility))
    
    def update_market(self):
        total_demand = sum(self.calculate_demand(f) for f in self.firms)
        
        for firm in self.firms:
            demand = self.calculate_demand(firm)
            market_share = demand / total_demand
            revenue = firm['price'] * market_share * self.market_size
            cost = (firm['cost'] * market_share * self.market_size 
                    + 50 * firm['tech']**2 
                    + 30 * firm['marketing'])
            
            firm['profit'] = revenue - cost
            firm['market_share'] = market_share
            firm['strategy_history'].append((
                firm['price'], 
                firm['tech'], 
                firm['marketing']
            ))

# ======================
# 策略演化引擎
# ======================
class StrategyEvolver:
    def __init__(self, market):
        self.market = market
        self.innovation_rate = 0.15
        self.imitation_rate = 0.25
        
    def evolve_strategies(self):
        # 按利润排序企业
        sorted_firms = sorted(self.market.firms, 
                             key=lambda x: x['profit'], 
                             reverse=True)
        
        # 创新和模仿过程
        for i, firm in enumerate(self.market.firms):
            if np.random.random() < self.innovation_rate:
                # 创新：随机探索新策略
                firm['price'] *= np.random.uniform(0.9, 1.1)
                firm['tech'] = min(1.0, max(0.1, firm['tech'] * np.random.uniform(0.95, 1.2)))
                firm['marketing'] *= np.random.uniform(0.9, 1.1)
            elif i > self.market.num_firms//3:
                # 模仿：学习成功企业
                model = sorted_firms[np.random.randint(0, self.market.num_firms//3)]
                if np.random.random() < self.imitation_rate:
                    firm['price'] = model['price'] * np.random.uniform(0.98, 1.02)
                    firm['tech'] = model['tech'] * np.random.uniform(0.99, 1.01)
                    firm['marketing'] = model['marketing'] * np.random.uniform(0.98, 1.02)
                    
        # 市场环境动态变化
        self.market.price_sensitivity *= np.random.uniform(0.99, 1.01)
        self.market.tech_sensitivity *= np.random.uniform(0.99, 1.01)

# ======================
# 可视化系统
# ======================
class CompetitiveVisualizer:
    def __init__(self, market):
        self.market = market
        self.fig = plt.figure(figsize=(15, 10))
        self.setup_ui()
        
    def setup_ui(self):
        # 3D策略空间
        self.ax1 = self.fig.add_subplot(231, projection='3d')
        self.ax1.set_title('企业策略空间演化')
        self.ax1.set_xlabel('价格')
        self.ax1.set_ylabel('技术水平')
        self.ax1.set_zlabel('营销投入')
        
        # 市场份额分布
        self.ax2 = self.fig.add_subplot(232)
        self.ax2.set_title('市场份额分布')
        self.ax2.set_xlabel('企业ID')
        self.ax2.set_ylabel('市场份额(%)')
        
        # 利润趋势
        self.ax3 = self.fig.add_subplot(233)
        self.ax3.set_title('头部企业利润趋势')
        self.ax3.set_xlabel('时间周期')
        self.ax3.set_ylabel('利润')
        
        # 策略集群
        self.ax4 = self.fig.add_subplot(234)
        self.ax4.set_title('策略集群分析')
        self.ax4.set_xlabel('价格')
        self.ax4.set_ylabel('技术投入')
        
        # 市场敏感度
        self.ax5 = self.fig.add_subplot(235)
        self.ax5.set_title('市场敏感度变化')
        self.ax5.set_xlabel('时间周期')
        self.ax5.set_ylabel('敏感度系数')
        
        # 控制面板
        self.ax_slider = plt.axes([0.25, 0.05, 0.5, 0.03])
        self.speed_slider = Slider(
            ax=self.ax_slider,
            label='模拟速度',
            valmin=0.1,
            valmax=2.0,
            valinit=1.0
        )
        
        # 添加重置按钮
        reset_ax = plt.axes([0.8, 0.05, 0.1, 0.04])
        self.reset_button = Button(reset_ax, '重置市场')
        self.reset_button.on_clicked(self.reset_market)
        
        # 添加创新率控制
        self.innovation_ax = plt.axes([0.15, 0.01, 0.3, 0.03])
        self.innovation_slider = Slider(
            ax=self.innovation_ax,
            label='创新率',
            valmin=0.05,
            valmax=0.5,
            valinit=0.15
        )
        
        self.fig.tight_layout(pad=3.0)
        
    def reset_market(self, event):
        self.market = MarketEnvironment()
        
    def update(self, frame):
        # 更新市场状态
        for _ in range(int(self.speed_slider.val)):
            StrategyEvolver(self.market).evolve_strategies()
            self.market.update_market()
        
        self.update_plots()
        return []
    
    def update_plots(self):
        # 清除所有轴
        self.ax1.clear()
        self.ax2.clear()
        self.ax3.clear()
        self.ax4.clear()
        self.ax5.clear()
        
        # 重新设置标签
        self.setup_ui()
        
        # 提取当前数据
        prices = [f['price'] for f in self.market.firms]
        techs = [f['tech'] for f in self.market.firms]
        marketings = [f['marketing'] for f in self.market.firms]
        shares = [f['market_share']*100 for f in self.market.firms]
        profits = [f['profit'] for f in self.market.firms]
        
        # 1. 3D策略空间
        sc = self.ax1.scatter(prices, techs, marketings, 
                             c=profits, cmap='viridis', s=shares)
        self.fig.colorbar(sc, ax=self.ax1, label='企业利润')
        
        # 2. 市场份额分布
        sorted_firms = sorted(self.market.firms, key=lambda x: x['market_share'], reverse=True)
        self.ax2.bar(range(len(sorted_firms)), [f['market_share']*100 for f in sorted_firms])
        self.ax2.axhline(y=100/self.market.num_firms, color='r', linestyle='--', 
                         label='平均份额')
        self.ax2.legend()
        
        # 3. 利润趋势（仅显示前5名）
        for i, firm in enumerate(sorted_firms[:5]):
            profit_history = [p[0] for p in self.calculate_profit_history(firm)]
            self.ax3.plot(profit_history, label=f'企业 {firm["id"]}')
        self.ax3.legend()
        
        # 4. 策略集群分析
        strategy_matrix = np.array([prices, techs]).T
        kmeans = KMeans(n_clusters=3, random_state=0).fit(strategy_matrix)
        self.ax4.scatter(prices, techs, c=kmeans.labels_, cmap='tab10')
        
        # 5. 市场敏感度变化（模拟）
        cycles = len(self.market.firms[0]['strategy_history'])
        if cycles > 1:
            price_sens = [0.8]  # 初始值
            tech_sens = [1.2]   # 初始值
            for i in range(1, cycles):
                price_sens.append(price_sens[-1] * np.random.uniform(0.99, 1.01))
                tech_sens.append(tech_sens[-1] * np.random.uniform(0.99, 1.01))
            
            self.ax5.plot(price_sens, label='价格敏感度')
            self.ax5.plot(tech_sens, label='技术敏感度')
            self.ax5.legend()
        
        plt.suptitle(f'市场竞争模拟 - 周期 {cycles}', fontsize=16)
        
    def calculate_profit_history(self, firm):
        # 重建历史利润数据（简化版）
        history = []
        temp_market = MarketEnvironment(num_firms=1)  # 创建临时市场
        
        for strategy in firm['strategy_history']:
            temp_firm = temp_market.firms[0]
            temp_firm['price'], temp_firm['tech'], temp_firm['marketing'] = strategy
            temp_market.update_market()
            history.append((temp_firm['profit'], temp_firm['market_share']))
            
        return history
    
    def animate(self):
        self.animation = FuncAnimation(
            self.fig, 
            self.update, 
            frames=100,
            interval=200,
            blit=False
        )
        plt.show()

# ======================
# 主程序
# ======================
if __name__ == "__main__":
    print("启动市场竞争模拟系统...")
    market = MarketEnvironment(num_firms=20)
    visualizer = CompetitiveVisualizer(market)
    visualizer.animate()