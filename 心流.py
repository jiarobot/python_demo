import numpy as np
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.colors import LinearSegmentedColormap
import seaborn as sns
from scipy import stats
import pandas as pd
from collections import deque
import random

class TeamMember:
    """模拟团队成员的类"""
    def __init__(self, id, expertise_area, skill_level, openness):
        self.id = id
        self.expertise = expertise_area  # 专业领域
        self.skill = skill_level  # 技能水平 0-1
        self.openness = openness  # 开放度 0-1
        self.focus = 0.0  # 专注度 0-1
        self.understanding = {}  # 对其他成员观点的理解度
        self.contribution = 0.0  # 贡献度
        self.flow_state = 0.0  # 个人心流状态 0-1
        self.last_interaction_time = 0
        self.idea_connections = []  # 想法连接
        
    def update_focus(self, team_psych_safety, shared_clarity, current_time):
        """更新专注度"""
        # 专注度受心理安全感和目标清晰度影响
        base_focus = (self.skill * 0.3 + team_psych_safety * 0.4 + 
                     shared_clarity * 0.3)
        
        # 时间衰减效应
        time_since_interaction = current_time - self.last_interaction_time
        if time_since_interaction > 5:
            decay = 0.95 ** (time_since_interaction - 5)
            base_focus *= decay
            
        self.focus = np.clip(base_focus, 0, 1)
        return self.focus

class CollectiveFlowSimulator:
    """集体心流模拟器"""
    
    def __init__(self, num_members=6, duration=200):
        self.num_members = num_members
        self.duration = duration
        self.time = 0
        self.members = []
        self.history = {
            'time': [],
            'collective_flow': [],
            'psych_safety': [],
            'shared_clarity': [],
            'interaction_fluency': [],
            'member_states': [],
            'breakthroughs': []
        }
        self.breakthrough_count = 0
        self.setup_team()
        
    def setup_team(self):
        """初始化团队"""
        expertise_areas = ['Engineering', 'Design', 'Research', 'Strategy', 'Data', 'Creative']
        for i in range(self.num_members):
            expertise = expertise_areas[i % len(expertise_areas)]
            skill = np.random.beta(2, 1.5)  # 偏向高技能
            openness = np.random.beta(1.5, 1.2)  # 偏向开放
            member = TeamMember(i, expertise, skill, openness)
            
            # 初始化理解度
            for j in range(self.num_members):
                if j != i:
                    member.understanding[j] = np.random.beta(1, 3)  # 初始理解度较低
                    
            self.members.append(member)
    
    def calculate_psych_safety(self):
        """计算团队心理安全感"""
        avg_openness = np.mean([m.openness for m in self.members])
        avg_focus = np.mean([m.focus for m in self.members])
        return (avg_openness * 0.6 + avg_focus * 0.4)
    
    def calculate_shared_clarity(self):
        """计算共享目标清晰度"""
        mutual_understanding = 0
        count = 0
        for i in range(self.num_members):
            for j in range(i+1, self.num_members):
                mutual_understanding += (self.members[i].understanding[j] + 
                                       self.members[j].understanding[i]) / 2
                count += 1
        avg_understanding = mutual_understanding / count if count > 0 else 0
        return avg_understanding
    
    def calculate_interaction_fluency(self):
        """计算互动流畅度"""
        # 基于最近的想法连接频率和质量
        recent_connections = []
        for member in self.members:
            recent_connections.extend([conn for conn in member.idea_connections 
                                     if conn['time'] > self.time - 10])
        
        if len(recent_connections) == 0:
            return 0.0
            
        avg_quality = np.mean([conn['quality'] for conn in recent_connections])
        frequency = min(1.0, len(recent_connections) / (self.num_members * 2))
        
        return (avg_quality * 0.7 + frequency * 0.3)
    
    def simulate_interaction(self, member1, member2):
        """模拟两个成员间的互动"""
        # 互动质量取决于专注度、开放度和技能匹配
        interaction_quality = (member1.focus * member2.focus * 
                             member1.openness * member2.openness *
                             (0.5 + 0.5 * (1 - abs(member1.skill - member2.skill))))
        
        # 更新相互理解度
        learning_rate = 0.1 * interaction_quality
        member1.understanding[member2.id] = np.clip(
            member1.understanding[member2.id] + learning_rate, 0, 1)
        member2.understanding[member1.id] = np.clip(
            member2.understanding[member1.id] + learning_rate, 0, 1)
        
        # 可能产生想法连接
        if interaction_quality > 0.3 and np.random.random() < 0.4:
            connection_quality = interaction_quality * (member1.skill + member2.skill) / 2
            idea_conn = {
                'members': (member1.id, member2.id),
                'quality': connection_quality,
                'time': self.time
            }
            member1.idea_connections.append(idea_conn)
            member2.idea_connections.append(idea_conn)
            
            return connection_quality
        return 0.0
    
    def check_breakthrough(self, collective_flow):
        """检查是否出现突破性洞见"""
        if collective_flow > 0.75 and np.random.random() < 0.02:
            # 高集体心流状态下更可能出现突破
            breakthrough_strength = collective_flow * np.random.beta(2, 3)
            if breakthrough_strength > 0.6:
                self.breakthrough_count += 1
                return breakthrough_strength
        return 0.0
    
    def step(self):
        """模拟一个时间步"""
        self.time += 1
        
        # 更新环境因素
        psych_safety = self.calculate_psych_safety()
        shared_clarity = self.calculate_shared_clarity()
        
        # 更新每个成员状态
        for member in self.members:
            member.update_focus(psych_safety, shared_clarity, self.time)
            
            # 基于专注度和技能计算个人心流
            challenge_level = 0.7  # 假设挑战水平适中
            flow_balance = 1 - abs(challenge_level - member.skill)
            member.flow_state = member.focus * flow_balance
        
        # 模拟互动
        interaction_fluency = self.calculate_interaction_fluency()
        
        # 选择部分成员进行互动（基于互动流畅度）
        num_interactions = int(interaction_fluency * self.num_members * 0.8) + 1
        for _ in range(num_interactions):
            i, j = np.random.choice(self.num_members, 2, replace=False)
            if i != j:
                connection_quality = self.simulate_interaction(self.members[i], self.members[j])
                self.members[i].last_interaction_time = self.time
                self.members[j].last_interaction_time = self.time
        
        # 计算集体心流
        avg_personal_flow = np.mean([m.flow_state for m in self.members])
        collective_flow = (avg_personal_flow * 0.3 + psych_safety * 0.25 + 
                          shared_clarity * 0.25 + interaction_fluency * 0.2)
        
        # 检查突破
        breakthrough = self.check_breakthrough(collective_flow)
        
        # 记录历史
        self.history['time'].append(self.time)
        self.history['collective_flow'].append(collective_flow)
        self.history['psych_safety'].append(psych_safety)
        self.history['shared_clarity'].append(shared_clarity)
        self.history['interaction_fluency'].append(interaction_fluency)
        self.history['member_states'].append([{
            'focus': m.focus,
            'flow_state': m.flow_state,
            'understanding': m.understanding.copy()
        } for m in self.members])
        self.history['breakthroughs'].append(breakthrough)
        
        return collective_flow

def create_collective_flow_visualization(simulator):
    """创建集体心流可视化"""
    fig = plt.figure(figsize=(16, 12))
    
    # 创建自定义颜色映射
    flow_cmap = LinearSegmentedColormap.from_list('flow', ['#2E86AB', '#A23B72', '#F18F01'])
    
    # 1. 主指标时间序列
    ax1 = plt.subplot2grid((3, 3), (0, 0), colspan=3)
    time = simulator.history['time']
    
    ax1.plot(time, simulator.history['collective_flow'], 
             label='集体心流', linewidth=3, color='#A23B72', alpha=0.8)
    ax1.plot(time, simulator.history['psych_safety'], 
             label='心理安全感', linestyle='--', alpha=0.7)
    ax1.plot(time, simulator.history['shared_clarity'], 
             label='目标清晰度', linestyle='--', alpha=0.7)
    ax1.plot(time, simulator.history['interaction_fluency'], 
             label='互动流畅度', linestyle='--', alpha=0.7)
    
    # 标记突破点
    breakthroughs = [(t, f) for t, f in zip(time, simulator.history['breakthroughs']) if f > 0]
    if breakthroughs:
        breakthrough_times, breakthrough_strengths = zip(*breakthroughs)
        ax1.scatter(breakthrough_times, breakthrough_strengths, 
                   color='#F18F01', s=100, zorder=5, label='突破性洞见')
    
    ax1.set_ylabel('指标值')
    ax1.set_ylim(0, 1)
    ax1.legend()
    ax1.set_title('集体心流状态演变', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    
    # 2. 网络连接图（团队成员理解度）
    ax2 = plt.subplot2grid((3, 3), (1, 0))
    
    # 计算当前理解度矩阵
    current_states = simulator.history['member_states'][-1]
    understanding_matrix = np.zeros((simulator.num_members, simulator.num_members))
    
    for i in range(simulator.num_members):
        for j in range(simulator.num_members):
            if i != j:
                understanding_matrix[i, j] = current_states[i]['understanding'].get(j, 0)
    
    # 绘制热图
    im = ax2.imshow(understanding_matrix, cmap='YlOrRd', vmin=0, vmax=1)
    ax2.set_xticks(range(simulator.num_members))
    ax2.set_yticks(range(simulator.num_members))
    ax2.set_xticklabels([f'M{i}' for i in range(simulator.num_members)])
    ax2.set_yticklabels([f'M{i}' for i in range(simulator.num_members)])
    ax2.set_title('成员间理解度矩阵', fontsize=12)
    plt.colorbar(im, ax=ax2, shrink=0.8)
    
    # 3. 雷达图 - 影响因素
    ax3 = plt.subplot2grid((3, 3), (1, 1), polar=True)
    
    categories = ['心理安全', '目标清晰', '互动流畅', '技能匹配', '专注度', '开放度']
    N = len(categories)
    
    # 计算当前各项指标
    values = [
        simulator.history['psych_safety'][-1],
        simulator.history['shared_clarity'][-1],
        simulator.history['interaction_fluency'][-1],
        np.mean([m.skill for m in simulator.members]),  # 平均技能
        np.mean([m.focus for m in simulator.members]),  # 平均专注度
        np.mean([m.openness for m in simulator.members])  # 平均开放度
    ]
    
    # 完成雷达图
    angles = np.linspace(0, 2*np.pi, N, endpoint=False).tolist()
    values += values[:1]
    angles += angles[:1]
    
    ax3.plot(angles, values, 'o-', linewidth=2, label='当前状态')
    ax3.fill(angles, values, alpha=0.25)
    ax3.set_xticks(angles[:-1])
    ax3.set_xticklabels(categories)
    ax3.set_ylim(0, 1)
    ax3.set_title('影响因素雷达图', fontsize=12)
    ax3.grid(True)
    
    # 4. 成员状态条形图
    ax4 = plt.subplot2grid((3, 3), (1, 2))
    
    member_ids = range(simulator.num_members)
    focus_levels = [simulator.members[i].focus for i in member_ids]
    flow_levels = [simulator.members[i].flow_state for i in member_ids]
    
    x = np.arange(len(member_ids))
    width = 0.35
    
    ax4.bar(x - width/2, focus_levels, width, label='专注度', alpha=0.7)
    ax4.bar(x + width/2, flow_levels, width, label='个人心流', alpha=0.7)
    
    ax4.set_xlabel('成员ID')
    ax4.set_ylabel('水平')
    ax4.set_xticks(x)
    ax4.set_xticklabels([f'M{i}' for i in member_ids])
    ax4.legend()
    ax4.set_title('成员状态分布', fontsize=12)
    ax4.grid(True, alpha=0.3)
    
    # 5. 相位图 - 展示集体心流演变路径
    ax5 = plt.subplot2grid((3, 3), (2, 0), colspan=3)
    
    # 使用心理安全感和目标清晰度作为相位空间
    psych_safety = simulator.history['psych_safety']
    shared_clarity = simulator.history['shared_clarity']
    collective_flow = simulator.history['collective_flow']
    
    scatter = ax5.scatter(psych_safety, shared_clarity, c=collective_flow, 
                         cmap=flow_cmap, s=50, alpha=0.7)
    
    # 添加轨迹线
    for i in range(1, len(psych_safety)):
        ax5.plot(psych_safety[i-1:i+1], shared_clarity[i-1:i+1], 
                color='gray', alpha=0.3, linewidth=1)
    
    ax5.set_xlabel('心理安全感')
    ax5.set_ylabel('目标清晰度')
    ax5.set_title('集体心流相位空间 (颜色表示心流强度)', fontsize=12)
    plt.colorbar(scatter, ax=ax5, label='集体心流强度')
    
    # 标记心流区域
    flow_zone = plt.Rectangle((0.6, 0.6), 0.4, 0.4, fill=False, 
                             edgecolor='green', linestyle='--', linewidth=2)
    ax5.add_patch(flow_zone)
    ax5.text(0.65, 0.65, '心流区域', fontsize=10, color='green')
    
    plt.tight_layout()
    return fig

def run_simulation_with_events(simulator):
    """运行模拟并添加关键事件"""
    print("开始集体心流模拟...")
    
    # 模拟过程中的关键事件
    events = [
        (20, "团队建立初步信任", 0.1),  # 增加心理安全
        (50, "明确共享目标", 0.15),     # 增加目标清晰度
        (80, "深度讨论突破", 0.2),      # 增加互动流畅度
        (120, "外部干扰", -0.3),        # 负面事件
        (150, "恢复协作节奏", 0.1),     # 恢复
        (180, "达到集体心流巅峰", 0.25) # 巅峰状态
    ]
    
    for step in range(simulator.duration):
        # 检查是否有事件发生
        for event_time, event_desc, impact in events:
            if step == event_time:
                print(f"时间 {event_time}: {event_desc}")
                # 应用事件影响
                if impact > 0:
                    # 正面事件：提升成员状态
                    for member in simulator.members:
                        member.focus = np.clip(member.focus + impact * 0.5, 0, 1)
                        member.openness = np.clip(member.openness + impact * 0.3, 0, 1)
                else:
                    # 负面事件：降低状态
                    for member in simulator.members:
                        member.focus = np.clip(member.focus + impact * 0.7, 0, 1)
        
        collective_flow = simulator.step()
        
        # 实时输出重要状态
        if step % 30 == 0:
            print(f"时间 {step}: 集体心流 = {collective_flow:.3f}")
    
    print(f"模拟完成！共产生 {simulator.breakthrough_count} 个突破性洞见")

# 运行模拟
if __name__ == "__main__":
    # 设置随机种子以便复现
    np.random.seed(42)
    random.seed(42)
    
    # 创建模拟器
    simulator = CollectiveFlowSimulator(num_members=6, duration=200)
    
    # 运行模拟
    run_simulation_with_events(simulator)
    
    # 创建可视化
    print("生成可视化...")
    fig = create_collective_flow_visualization(simulator)
    
    # 保存结果
    plt.savefig('collective_flow_simulation.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    # 输出统计分析
    print("\n=== 模拟统计 ===")
    final_flow = simulator.history['collective_flow'][-1]
    max_flow = max(simulator.history['collective_flow'])
    avg_flow = np.mean(simulator.history['collective_flow'])
    
    print(f"最终集体心流: {final_flow:.3f}")
    print(f"最大集体心流: {max_flow:.3f}")
    print(f"平均集体心流: {avg_flow:.3f}")
    print(f"突破性洞见数量: {simulator.breakthrough_count}")
    
    # 计算心流持续时间
    flow_duration = sum(1 for flow in simulator.history['collective_flow'] if flow > 0.7)
    print(f"高心流状态持续时间: {flow_duration} 时间步")