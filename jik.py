import numpy as np
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.widgets import Button, Slider, RadioButtons
import seaborn as sns
import torch
import torch.nn as nn
import torch.optim as optim
from collections import deque
import random
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
import networkx as nx
from matplotlib.animation import FuncAnimation
from IPython.display import HTML

# 设置全局样式
plt.style.use('default')  # 或者使用其他可用样式
sns.set_style("darkgrid")  # 使用 seaborn 的 darkgrid 样式
sns.set_palette("Set2")
torch.manual_seed(42)
np.random.seed(42)

class MarketEnvironment:
    """动态市场环境模拟"""
    def __init__(self, n_firms=3):
        self.n_firms = n_firms
        self.reset()
        
    def reset(self):
        # 企业初始状态 [现金, 技术, 品牌, 市场份额, 成本]
        self.firms = np.zeros((self.n_firms, 5))
        self.firms[:, 0] = 1000000  # 初始资金
        self.firms[:, 1] = np.random.uniform(30, 50, self.n_firms)  # 初始技术
        self.firms[:, 2] = np.random.uniform(20, 40, self.n_firms)  # 初始品牌
        self.firms[:, 3] = 1 / self.n_firms  # 初始市场份额
        self.firms[:, 4] = 50  # 初始单位成本
        
        # 市场参数
        self.economic_cycle = 1.0  # 经济周期系数
        self.consumer_pref = np.random.rand(3)  # 消费者偏好[价格,质量,品牌]
        self.consumer_pref /= self.consumer_pref.sum()
        self.quarter = 0
        self.black_swan = 0  # 黑天鹅事件计数器
        
        # 历史记录
        self.history = {
            'market_share': [self.firms[:, 3].copy()],
            'profits': [np.zeros(self.n_firms)],
            'prices': [np.full(self.n_firms, 100)],
            'investments': [np.zeros((self.n_firms, 2))],  # [技术投资, 品牌投资]
            'cash': [self.firms[:, 0].copy()],
            'technology': [self.firms[:, 1].copy()],
            'brand': [self.firms[:, 2].copy()],
            'cost': [self.firms[:, 4].copy()]
        }
        return self.get_state()
    
    def get_state(self):
        """获取当前环境状态"""
        return np.concatenate((
            [self.economic_cycle, self.black_swan],
            self.consumer_pref,
            self.firms.flatten()
        ))
    
    def step(self, actions):
        """执行企业决策并更新市场"""
        # 解析动作 [价格策略, 技术投资, 品牌投资]
        prices = actions[:, 0] * 100 + 50  # 映射到50-150价格区间
        tech_invest = actions[:, 1] * 100  # 技术投资(0-100)
        brand_invest = actions[:, 2] * 100  # 品牌投资(0-100)
        
        # 更新企业状态
        self.firms[:, 0] -= tech_invest + brand_invest  # 扣除投资成本
        self.firms[:, 1] = self.firms[:, 1] * 0.95 + tech_invest * 0.15
        self.firms[:, 1] = np.clip(self.firms[:, 1], 0, 100)
        self.firms[:, 2] = self.firms[:, 2] * 0.9 + brand_invest * 0.2
        self.firms[:, 2] = np.clip(self.firms[:, 2], 0, 100)
        
        # 计算单位成本 (技术越高成本越低)
        self.firms[:, 4] = 40 + (100 - self.firms[:, 1]) * 0.2
        
        # 计算产品吸引力 (考虑黑天鹅事件)
        attractiveness = (
            (1 / (prices + 1e-5)) * self.consumer_pref[0] + 
            self.firms[:, 1] * self.consumer_pref[1] + 
            self.firms[:, 2] * self.consumer_pref[2]
        )
        
        # 黑天鹅事件影响
        if self.black_swan > 0:
            attractiveness *= np.random.uniform(0.5, 0.8, self.n_firms)
            self.black_swan -= 1
        
        # 计算市场份额
        total_attract = attractiveness.sum()
        market_share = attractiveness / (total_attract + 1e-5)
        
        # 计算利润
        profit = (prices - self.firms[:, 4]) * market_share * 1000 * self.economic_cycle
        
        # 更新企业现金和市场份额
        self.firms[:, 0] += profit
        self.firms[:, 3] = market_share
        
        # 更新市场环境
        self._update_market()
        
        # 记录历史
        self.history['market_share'].append(market_share.copy())
        self.history['profits'].append(profit.copy())
        self.history['prices'].append(prices.copy())
        self.history['investments'].append(np.column_stack((tech_invest, brand_invest)))
        self.history['cash'].append(self.firms[:, 0].copy())
        self.history['technology'].append(self.firms[:, 1].copy())
        self.history['brand'].append(self.firms[:, 2].copy())
        self.history['cost'].append(self.firms[:, 4].copy())
        
        # 计算奖励（利润增长）
        reward = profit - self.history['profits'][-2]
        
        # 检查企业破产
        done = any(self.firms[:, 0] < 0)
        
        return self.get_state(), reward, done
    
    def _update_market(self):
        """更新市场动态"""
        self.quarter += 1
        
        # 经济周期波动 (正弦波)
        self.economic_cycle = 0.8 + 0.2 * np.sin(self.quarter / 4)
        
        # 消费者偏好缓慢变化
        if self.quarter % 8 == 0:
            drift = np.random.normal(0, 0.1, 3)
            self.consumer_pref += drift
            self.consumer_pref = np.clip(self.consumer_pref, 0.1, 0.8)
            self.consumer_pref /= self.consumer_pref.sum()
        
        # 技术扩散效应
        if self.quarter % 12 == 0:
            avg_tech = self.firms[:, 1].mean()
            self.firms[:, 1] = 0.7 * self.firms[:, 1] + 0.3 * avg_tech
        
        # 随机黑天鹅事件 (5%概率)
        if np.random.random() < 0.05 and self.black_swan == 0:
            self.black_swan = 4  # 持续4个季度
            print(f"⚠️ 黑天鹅事件发生在第{self.quarter}季度!")

class DQN(nn.Module):
    """深度Q网络决策模型"""
    def __init__(self, state_size, action_size, hidden_size=128):
        super(DQN, self).__init__()
        self.fc1 = nn.Linear(state_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.fc3 = nn.Linear(hidden_size, action_size)
        self.dropout = nn.Dropout(0.2)
        
    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = self.dropout(x)
        x = torch.relu(self.fc2(x))
        return self.fc3(x)

class MADQNAgent:
    """多智能体深度Q学习代理"""
    def __init__(self, env, learning_rate=0.001, gamma=0.95):
        self.env = env
        self.state_size = len(env.get_state())
        self.action_size = 3  # [价格策略, 技术投资, 品牌投资]
        
        # 为每个企业创建DQN
        self.dqns = [DQN(self.state_size, self.action_size) for _ in range(env.n_firms)]
        self.target_dqns = [DQN(self.state_size, self.action_size) for _ in range(env.n_firms)]
        for i in range(env.n_firms):
            self.target_dqns[i].load_state_dict(self.dqns[i].state_dict())
            
        self.optimizers = [optim.Adam(dqn.parameters(), lr=learning_rate) for dqn in self.dqns]
        
        self.gamma = gamma
        self.memory = deque(maxlen=5000)
        self.batch_size = 128
        self.epsilon = 1.0
        self.epsilon_min = 0.05
        self.epsilon_decay = 0.995
        self.update_freq = 10
        self.step_count = 0
        
    def act(self, state):
        """为每个企业生成动作"""
        actions = []
        state_tensor = torch.FloatTensor(state).unsqueeze(0)
        
        for i in range(self.env.n_firms):
            if np.random.rand() <= self.epsilon:
                # 随机探索
                actions.append(np.random.rand(3))
            else:
                # 使用DQN决策
                with torch.no_grad():
                    action_values = self.dqns[i](state_tensor)
                    # 使用sigmoid将输出映射到[0,1]
                    action = torch.sigmoid(action_values).squeeze(0).numpy()
                    actions.append(action)
                    
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
        return np.array(actions)
    
    def remember(self, state, actions, rewards, next_state, done):
        """存储经验"""
        self.memory.append((state, actions, rewards, next_state, done))
    
    def replay(self):
        """经验回放训练"""
        if len(self.memory) < self.batch_size:
            return
            
        batch = random.sample(self.memory, self.batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)
        
        states = torch.FloatTensor(np.array(states))
        next_states = torch.FloatTensor(np.array(next_states))
        
        for i in range(self.env.n_firms):
            # 获取当前企业的奖励
            firm_rewards = torch.FloatTensor([r[i] for r in rewards])
            firm_dones = torch.FloatTensor([d for d in dones])
            
            # 当前Q值
            current_q = self.dqns[i](states)
            
            # 目标Q值
            with torch.no_grad():
                next_q = self.target_dqns[i](next_states)
                max_next_q = next_q.max(1)[0]
                target_q = firm_rewards + self.gamma * max_next_q * (1 - firm_dones)
            
            # 计算损失
            loss = nn.MSELoss()(current_q, target_q.unsqueeze(1))
            
            # 反向传播
            self.optimizers[i].zero_grad()
            loss.backward()
            self.optimizers[i].step()
            
        # 定期更新目标网络
        self.step_count += 1
        if self.step_count % self.update_freq == 0:
            for i in range(self.env.n_firms):
                self.target_dqns[i].load_state_dict(self.dqns[i].state_dict())

class CompetitionSimulator:
    """企业竞争模拟器"""
    def __init__(self, n_firms=3, n_quarters=48):
        self.env = MarketEnvironment(n_firms)
        self.agent = MADQNAgent(self.env)
        self.n_quarters = n_quarters
        self.results = {}
        self.strategy_names = ["价格优先", "技术领先", "品牌建设", "平衡策略"]
        
    def run_simulation(self, strategy_override=None):
        """运行完整模拟"""
        state = self.env.reset()
        total_rewards = np.zeros(self.env.n_firms)
        
        for q in range(self.n_quarters):
            # 获取智能体决策
            actions = self.agent.act(state)
            
            # 策略覆盖（用于交互测试）
            if strategy_override is not None:
                firm_idx = strategy_override["firm"]
                strategy = strategy_override["strategy"]
                
                if strategy == "价格优先":
                    actions[firm_idx] = [0.1, 0.2, 0.2]  # 低价策略
                elif strategy == "技术领先":
                    actions[firm_idx] = [0.7, 0.8, 0.3]  # 高技术投入
                elif strategy == "品牌建设":
                    actions[firm_idx] = [0.7, 0.3, 0.8]  # 高品牌投入
                else:  # 平衡策略
                    actions[firm_idx] = [0.6, 0.5, 0.5]  # 平衡投入
            
            # 执行环境步骤
            next_state, rewards, done = self.env.step(actions)
            total_rewards += rewards
            
            # 存储经验
            self.agent.remember(state, actions, rewards, next_state, done)
            
            # 训练DQN
            self.agent.replay()
            
            state = next_state
            
            if done:
                print(f"企业破产发生在第{q}季度")
                break
        
        # 收集结果
        self.results = {
            'market_share': np.array(self.env.history['market_share']),
            'profits': np.array(self.env.history['profits']),
            'prices': np.array(self.env.history['prices']),
            'investments': np.array(self.env.history['investments']),
            'cash': np.array(self.env.history['cash']),
            'technology': np.array(self.env.history['technology']),
            'brand': np.array(self.env.history['brand']),
            'cost': np.array(self.env.history['cost']),
            'total_rewards': total_rewards,
            'consumer_pref': np.array([self.env.consumer_pref] * (self.n_quarters + 1)),
            'economic_cycle': np.array([self.env.economic_cycle] * (self.n_quarters + 1))
        }
        return self.results
    
    def plot_results(self):
        """可视化模拟结果"""
        fig = plt.figure(figsize=(18, 15))
        gs = gridspec.GridSpec(4, 3, figure=fig)
        
        quarters = range(len(self.results['market_share']))
        n_firms = self.env.n_firms
        
        # 市场份额变化
        ax1 = fig.add_subplot(gs[0, 0])
        for i in range(n_firms):
            ax1.plot(quarters, self.results['market_share'][:, i] * 100, 
                    label=f'企业 {i+1}', linewidth=2.5)
        ax1.set_title('市场份额变化', fontsize=14, fontweight='bold')
        ax1.set_xlabel('季度', fontsize=12)
        ax1.set_ylabel('市场份额 (%)', fontsize=12)
        ax1.legend(fontsize=10)
        ax1.grid(True, alpha=0.3)
        
        # 利润变化
        ax2 = fig.add_subplot(gs[0, 1])
        for i in range(n_firms):
            ax2.plot(quarters, self.results['profits'][:, i], linewidth=2.5)
        ax2.set_title('企业利润变化', fontsize=14, fontweight='bold')
        ax2.set_xlabel('季度', fontsize=12)
        ax2.set_ylabel('利润 ($)', fontsize=12)
        ax2.grid(True, alpha=0.3)
        
        # 价格策略
        ax3 = fig.add_subplot(gs[0, 2])
        for i in range(n_firms):
            ax3.plot(quarters, self.results['prices'][:, i], linewidth=2.5)
        ax3.set_title('产品价格策略', fontsize=14, fontweight='bold')
        ax3.set_xlabel('季度', fontsize=12)
        ax3.set_ylabel('价格 ($)', fontsize=12)
        ax3.grid(True, alpha=0.3)
        
        # 技术投资与水平
        ax4 = fig.add_subplot(gs[1, 0])
        tech_invest = self.results['investments'][:, :, 0]
        for i in range(n_firms):
            ax4.plot(quarters, tech_invest[:, i], label=f'企业 {i+1} 投资', linestyle='--')
            ax4.plot(quarters, self.results['technology'][:, i], label=f'企业 {i+1} 水平', linewidth=2.5)
        ax4.set_title('技术投资与水平', fontsize=14, fontweight='bold')
        ax4.set_xlabel('季度', fontsize=12)
        ax4.set_ylabel('投资/水平', fontsize=12)
        ax4.legend(fontsize=9)
        ax4.grid(True, alpha=0.3)
        
        # 品牌投资与价值
        ax5 = fig.add_subplot(gs[1, 1])
        brand_invest = self.results['investments'][:, :, 1]
        for i in range(n_firms):
            ax5.plot(quarters, brand_invest[:, i], label=f'企业 {i+1} 投资', linestyle='--')
            ax5.plot(quarters, self.results['brand'][:, i], label=f'企业 {i+1} 价值', linewidth=2.5)
        ax5.set_title('品牌投资与价值', fontsize=14, fontweight='bold')
        ax5.set_xlabel('季度', fontsize=12)
        ax5.set_ylabel('投资/价值', fontsize=12)
        ax5.grid(True, alpha=0.3)
        
        # 成本与利润率
        ax6 = fig.add_subplot(gs[1, 2])
        for i in range(n_firms):
            cost = self.results['cost'][:, i]
            price = self.results['prices'][:, i]
            margin = (price - cost) / price * 100
            ax6.plot(quarters, cost, label=f'企业 {i+1} 成本', linestyle='--')
            ax6.plot(quarters, margin, label=f'企业 {i+1} 利润率', linewidth=2.5)
        ax6.set_title('成本与利润率', fontsize=14, fontweight='bold')
        ax6.set_xlabel('季度', fontsize=12)
        ax6.set_ylabel('成本($)/利润率(%)', fontsize=12)
        ax6.grid(True, alpha=0.3)
        
        # 消费者偏好
        ax7 = fig.add_subplot(gs[2, 0])
        pref_data = self.results['consumer_pref']
        ax7.plot(quarters, pref_data[:, 0], label='价格敏感度', linewidth=2.5)
        ax7.plot(quarters, pref_data[:, 1], label='质量需求', linewidth=2.5)
        ax7.plot(quarters, pref_data[:, 2], label='品牌忠诚度', linewidth=2.5)
        ax7.set_title('消费者偏好变化', fontsize=14, fontweight='bold')
        ax7.set_xlabel('季度', fontsize=12)
        ax7.set_ylabel('偏好强度', fontsize=12)
        ax7.legend(fontsize=10)
        ax7.grid(True, alpha=0.3)
        
        # 经济周期
        ax8 = fig.add_subplot(gs[2, 1])
        ax8.plot(quarters, self.results['economic_cycle'], 'b-', linewidth=2.5)
        ax8.fill_between(quarters, self.results['economic_cycle'], 
                        alpha=0.2, color='blue')
        ax8.set_title('宏观经济周期', fontsize=14, fontweight='bold')
        ax8.set_xlabel('季度', fontsize=12)
        ax8.set_ylabel('经济景气指数', fontsize=12)
        ax8.grid(True, alpha=0.3)
        
        # 现金储备
        ax9 = fig.add_subplot(gs[2, 2])
        for i in range(n_firms):
            ax9.plot(quarters, self.results['cash'][:, i], linewidth=2.5)
        ax9.set_title('企业现金储备', fontsize=14, fontweight='bold')
        ax9.set_xlabel('季度', fontsize=12)
        ax9.set_ylabel('现金 ($)', fontsize=12)
        ax9.grid(True, alpha=0.3)
        
        # 最终市场份额饼图
        ax10 = fig.add_subplot(gs[3, 0])
        final_share = self.results['market_share'][-1]
        explode = [0.1 if i == np.argmax(final_share) else 0 for i in range(n_firms)]
        ax10.pie(final_share, 
                labels=[f'企业 {i+1}' for i in range(n_firms)],
                autopct='%1.1f%%', 
                explode=explode,
                shadow=True,
                startangle=90)
        ax10.set_title('最终市场份额', fontsize=14, fontweight='bold')
        
        # 竞争策略气泡图
        ax11 = fig.add_subplot(gs[3, 1])
        avg_price = self.results['prices'][-1].mean()
        avg_tech = self.results['investments'][-1, :, 0].mean()
        avg_brand = self.results['investments'][-1, :, 1].mean()
        
        for i in range(n_firms):
            price_agg = self.results['prices'][-1, i] / avg_price
            tech_agg = self.results['investments'][-1, i, 0] / avg_tech
            brand_agg = self.results['investments'][-1, i, 1] / avg_brand
            
            # 气泡大小表示市场份额
            size = self.results['market_share'][-1, i] * 5000
            
            # 气泡颜色表示利润率
            margin = (self.results['prices'][-1, i] - self.results['cost'][-1, i]) / self.results['prices'][-1, i]
            color = plt.cm.viridis(margin)
            
            ax11.scatter(tech_agg, brand_agg, s=size, 
                        c=[color], alpha=0.7,
                        label=f'企业 {i+1}')
            
            # 添加价格攻击性标记
            ax11.annotate(f'P:{price_agg:.1f}x', 
                         (tech_agg, brand_agg),
                         textcoords="offset points", 
                         xytext=(0,10), 
                         ha='center',
                         fontsize=9)
        
        ax11.set_xlabel('技术投入强度 (相对市场平均)')
        ax11.set_ylabel('品牌投入强度 (相对市场平均)')
        ax11.set_title('企业竞争策略定位', fontsize=14, fontweight='bold')
        ax11.axhline(1, color='gray', linestyle='--', alpha=0.3)
        ax11.axvline(1, color='gray', linestyle='--', alpha=0.3)
        ax11.legend(fontsize=9)
        ax11.grid(True, alpha=0.3)
        
        # 企业能力雷达图
        ax12 = fig.add_subplot(gs[3, 2], polar=True)
        labels = ['资金实力', '技术水平', '品牌价值', '成本控制', '市场份额']
        angles = np.linspace(0, 2*np.pi, len(labels), endpoint=False).tolist()
        
        for i in range(n_firms):
            values = [
                np.log10(self.results['cash'][-1, i] / 6),  # 资金实力
                self.results['technology'][-1, i] / 100,    # 技术水平
                self.results['brand'][-1, i] / 100,         # 品牌价值
                1 - (self.results['cost'][-1, i] - 30) / 50, # 成本控制
                self.results['market_share'][-1, i] * 5      # 市场份额
            ]
            values += values[:1]  # 闭合图形
            ax12.plot(angles + angles[:1], values, linewidth=2, 
                     label=f'企业 {i+1}')
            ax12.fill(angles + angles[:1], values, alpha=0.2)
        
        ax12.set_xticks(angles)
        ax12.set_xticklabels(labels, fontsize=10)
        ax12.set_title('企业能力雷达图 (最终季度)', fontsize=14, fontweight='bold')
        ax12.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
        
        plt.tight_layout()
        plt.savefig('enterprise_competition_results.png', dpi=300)
        plt.show()
    
    def create_interactive_dashboard(self):
        """创建交互式控制面板"""
        fig = plt.figure(figsize=(16, 12))
        fig.suptitle('企业竞争策略模拟器', fontsize=20, fontweight='bold')
        
        # 创建网格布局
        gs = gridspec.GridSpec(3, 3, figure=fig)
        
        # 主图表区域
        ax_main = fig.add_subplot(gs[0:2, 0:2])
        quarters = range(len(self.results['market_share']))
        n_firms = self.env.n_firms
        
        # 初始绘图 (市场份额)
        lines = []
        for i in range(n_firms):
            line, = ax_main.plot(quarters, self.results['market_share'][:, i] * 100, 
                               lw=2.5, label=f'企业 {i+1}')
            lines.append(line)
        
        ax_main.set_title('市场份额动态变化', fontsize=16)
        ax_main.set_xlabel('季度', fontsize=12)
        ax_main.set_ylabel('市场份额 (%)', fontsize=12)
        ax_main.legend(loc='upper left')
        ax_main.grid(True, alpha=0.3)
        
        # 添加控制区域
        ax_controls = fig.add_subplot(gs[2, :])
        ax_controls.axis('off')
        
        # 策略选择
        ax_strategy = plt.axes([0.05, 0.05, 0.15, 0.15])
        strategy_radio = RadioButtons(
            ax_strategy, self.strategy_names, 
            active=3, activecolor='#2ca02c'
        )
        
        # 企业选择
        ax_firm = plt.axes([0.25, 0.05, 0.1, 0.15])
        firm_radio = RadioButtons(
            ax_firm, [f'企业 {i+1}' for i in range(n_firms)], 
            active=0, activecolor='#1f77b4'
        )
        
        # 参数滑块
        ax_elasticity = plt.axes([0.4, 0.1, 0.15, 0.03])
        ax_tech_decay = plt.axes([0.4, 0.06, 0.15, 0.03])
        
        slider_elasticity = Slider(
            ax_elasticity, '需求弹性', 0.5, 3.0, 
            valinit=1.5, valstep=0.1,
            color='#ff7f0e'
        )
        slider_tech_decay = Slider(
            ax_tech_decay, '技术衰减率', 0.8, 0.99, 
            valinit=0.95, valstep=0.01,
            color='#17becf'
        )
        
        # 运行按钮
        ax_run = plt.axes([0.6, 0.08, 0.1, 0.05])
        button_run = Button(ax_run, '运行模拟', color='#d62728')
        
        # 重置按钮
        ax_reset = plt.axes([0.75, 0.08, 0.1, 0.05])
        button_reset = Button(ax_reset, '重置参数', color='#7f7f7f')
        
        # 图表类型选择
        ax_chart = plt.axes([0.6, 0.15, 0.25, 0.05])
        chart_radio = RadioButtons(
            ax_chart, ['市场份额', '企业利润', '现金储备', '技术水平'], 
            active=0
        )
        
        # 当前策略覆盖
        current_strategy = {"firm": 0, "strategy": "平衡策略"}
        
        def update_strategy(label):
            current_strategy["strategy"] = label
            print(f"策略更新为: {label}")
        
        def update_firm(label):
            firm_id = int(label.split(" ")[1]) - 1
            current_strategy["firm"] = firm_id
            print(f"目标企业更新为: {label}")
        
        def update_chart(label):
            """更新主图表显示内容"""
            for line in lines:
                line.remove()
            lines.clear()
            
            if label == '市场份额':
                data = self.results['market_share'] * 100
                ylabel = '市场份额 (%)'
            elif label == '企业利润':
                data = self.results['profits']
                ylabel = '利润 ($)'
            elif label == '现金储备':
                data = self.results['cash']
                ylabel = '现金 ($)'
            elif label == '技术水平':
                data = self.results['technology']
                ylabel = '技术水平'
            
            for i in range(n_firms):
                line, = ax_main.plot(quarters, data[:, i], 
                                   lw=2.5, label=f'企业 {i+1}')
                lines.append(line)
            
            ax_main.set_ylabel(ylabel, fontsize=12)
            ax_main.set_title(f'{label}动态变化', fontsize=16)
            ax_main.legend(loc='best')
            fig.canvas.draw_idle()
        
        def run_simulation(event):
            """重新运行模拟并更新图表"""
            # 设置策略覆盖
            strategy_override = current_strategy
            
            # 重新运行模拟
            self.env = MarketEnvironment(n_firms)
            self.agent = MADQNAgent(self.env)
            results = self.run_simulation(strategy_override)
            
            # 更新当前图表
            chart_type = chart_radio.value_selected
            update_chart(chart_type)
            
            print("模拟完成! 最终市场份额:")
            for i, share in enumerate(results['market_share'][-1]):
                print(f"企业 {i+1}: {share*100:.1f}%")
        
        def reset_params(event):
            """重置参数到默认值"""
            slider_elasticity.reset()
            slider_tech_decay.reset()
            current_strategy.update({"firm": 0, "strategy": "平衡策略"})
            strategy_radio.set_active(3)
            firm_radio.set_active(0)
            print("参数已重置")
        
        # 绑定事件
        strategy_radio.on_clicked(update_strategy)
        firm_radio.on_clicked(update_firm)
        chart_radio.on_clicked(update_chart)
        button_run.on_clicked(run_simulation)
        button_reset.on_clicked(reset_params)
        
        plt.tight_layout(rect=[0, 0.2, 1, 0.95])
        plt.show()

# 运行模拟并展示结果
if __name__ == "__main__":
    print("="*70)
    print("企业竞争模拟系统")
    print("基于多智能体强化学习的三维竞争模型")
    print("="*70)
    
    simulator = CompetitionSimulator(n_firms=3, n_quarters=48)
    results = simulator.run_simulation()
    
    print("\n模拟结果摘要:")
    print(f"最终市场份额: {results['market_share'][-1] * 100}")
    print(f"总利润: {results['profits'][-1].sum():,.2f} $")
    print(f"最高企业利润: {max(results['profits'][-1]):,.2f} $")
    
    # 可视化结果
    simulator.plot_results()
    
    # 启动交互式面板
    print("\n启动交互式控制面板...")
    simulator.create_interactive_dashboard()