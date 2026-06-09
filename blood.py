import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.patches import Rectangle, Circle, Arrow
import seaborn as sns
import pandas as pd
import geopandas as gpd
import contextily as ctx
from matplotlib.colors import LinearSegmentedColormap

plt.rcParams['font.family'] = 'SimHei'  # 设置中文字体
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

# 1. ABO抗原合成生化途径可视化
def plot_biochemical_pathway():
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.axis('off')
    ax.set_title('ABO血型抗原合成生化途径', fontsize=16, pad=20)
    
    # 绘制前体物质
    ax.text(1, 8.5, "前体物质", fontsize=12, ha='center')
    ax.add_patch(Rectangle((0.5, 7.5), 1, 1, fill=True, color='#FFE4B5'))
    ax.text(1, 8, "Gal", ha='center', va='center')
    ax.text(1, 7.5, "GlcNAc", ha='center', va='center')
    
    # H抗原合成
    ax.text(3.5, 8.5, "FUT1基因编码的酶", fontsize=10, ha='center')
    ax.text(3.5, 8.1, "α-1,2-岩藻糖转移酶", fontsize=10, ha='center')
    ax.arrow(1.5, 8, 1.5, 0, head_width=0.2, head_length=0.2, fc='k', ec='k')
    
    ax.text(3, 8.5, "H抗原", fontsize=12, ha='center')
    ax.add_patch(Rectangle((2.5, 7.5), 1, 1, fill=True, color='#FFD700'))
    ax.text(3, 8, "Fuc-Gal", ha='center', va='center')
    ax.text(3, 7.5, "GlcNAc", ha='center', va='center')
    
    # 分支点
    ax.text(4.5, 8, "→", fontsize=20, ha='center')
    
    # A抗原路径
    ax.text(6, 9.5, "A等位基因编码的酶", fontsize=10, ha='center')
    ax.text(6, 9.1, "α-1,3-N-乙酰半乳糖胺转移酶", fontsize=10, ha='center')
    ax.arrow(4.5, 8, 1, 1, head_width=0.2, head_length=0.2, fc='b', ec='b')
    
    ax.text(7, 9.5, "A抗原", fontsize=12, ha='center')
    ax.add_patch(Rectangle((6.5, 8.5), 1, 1, fill=True, color='#87CEFA'))
    ax.text(7, 9, "GalNAc-Fuc-Gal", ha='center', va='center')
    ax.text(7, 8.5, "GlcNAc", ha='center', va='center')
    
    # B抗原路径
    ax.text(6, 6.5, "B等位基因编码的酶", fontsize=10, ha='center')
    ax.text(6, 6.1, "α-1,3-半乳糖转移酶", fontsize=10, ha='center')
    ax.arrow(4.5, 8, 1, -1, head_width=0.2, head_length=0.2, fc='r', ec='r')
    
    ax.text(7, 6.5, "B抗原", fontsize=12, ha='center')
    ax.add_patch(Rectangle((6.5, 5.5), 1, 1, fill=True, color='#FFB6C1'))
    ax.text(7, 6, "Gal-Fuc-Gal", ha='center', va='center')
    ax.text(7, 5.5, "GlcNAc", ha='center', va='center')
    
    # O型路径
    ax.text(9, 8, "O等位基因", fontsize=10, ha='center')
    ax.text(9, 7.6, "(无功能酶)", fontsize=10, ha='center')
    ax.arrow(4.5, 8, 4, 0, head_width=0.2, head_length=0.2, fc='g', ec='g')
    
    ax.text(10.5, 8, "H抗原保留", fontsize=12, ha='center')
    ax.add_patch(Rectangle((10, 7.5), 1, 1, fill=True, color='#98FB98'))
    ax.text(10.5, 8, "Fuc-Gal", ha='center', va='center')
    ax.text(10.5, 7.5, "GlcNAc", ha='center', va='center')
    
    # 添加图例
    ax.text(12, 9, "关键酶促反应", fontsize=12)
    ax.arrow(12, 8.5, 1, 0, head_width=0.1, head_length=0.2, fc='k', ec='k')
    ax.text(13.5, 8.5, "催化作用", fontsize=10)
    
    # 添加解释
    ax.text(1, 6, "生物进化视角:", fontsize=12, color='purple')
    ax.text(1, 5.5, "1. H抗原系统存在于大多数哺乳动物", fontsize=10)
    ax.text(1, 5.0, "2. A/B酶基因突变发生在灵长类祖先", fontsize=10)
    ax.text(1, 4.5, "3. O型突变(功能丧失)提供疟疾抗性", fontsize=10)
    ax.text(1, 4.0, "4. 多态性平衡增强群体适应性", fontsize=10)
    
    plt.tight_layout()
    plt.savefig('biochemical_pathway.png', dpi=300)
    plt.show()

# 2. 全球ABO血型分布热力图
def plot_global_distribution():
    # 创建模拟数据
    data = {
        'Country': ['China', 'India', 'USA', 'Brazil', 'Nigeria', 'Russia', 
                   'Japan', 'Germany', 'France', 'UK', 'Australia', 'Egypt'],
        'Latitude': [35, 20, 38, -15, 10, 60, 36, 51, 46, 54, -25, 27],
        'Longitude': [105, 78, -97, -55, 8, 100, 138, 10, 2, -2, 135, 30],
        'O_freq': [40, 35, 44, 47, 54, 33, 30, 41, 42, 48, 49, 52],
        'A_freq': [31, 22, 42, 41, 24, 36, 38, 43, 44, 42, 38, 28],
        'B_freq': [23, 33, 10, 9, 20, 23, 22, 11, 9, 8, 10, 16],
        'AB_freq': [6, 10, 4, 3, 2, 8, 10, 5, 5, 2, 3, 4]
    }
    df = pd.DataFrame(data)
    
    # 创建地图
    fig, ax = plt.subplots(figsize=(15, 10))
    ax.set_title('全球ABO血型分布 (O型频率)', fontsize=16)
    
    # 绘制散点图表示血型频率
    sc = ax.scatter(df['Longitude'], df['Latitude'], 
                   s=df['O_freq']*20, c=df['O_freq'], 
                   cmap='viridis', alpha=0.8)
    
    # 添加国家标签
    for i, row in df.iterrows():
        ax.text(row['Longitude']+1, row['Latitude']+1, row['Country'], fontsize=9)
    
    # 添加血型频率饼图
    for i, row in df.iterrows():
        sizes = [row['O_freq'], row['A_freq'], row['B_freq'], row['AB_freq']]
        colors = ['#98FB98', '#87CEFA', '#FFB6C1', '#DDA0DD']
        
        # 在位置点添加小饼图
        pie_x, pie_y = row['Longitude'], row['Latitude']
        pie_ax = fig.add_axes([0, 0, 0.1, 0.1])
        pie_ax.set_position([(pie_x + 180)/360 - 0.03, (pie_y + 90)/180 - 0.03, 0.06, 0.06])
        pie_ax.pie(sizes, colors=colors, startangle=90)
        pie_ax.axis('equal')
    
    # 添加图例
    legend_labels = ['O型', 'A型', 'B型', 'AB型']
    legend_colors = ['#98FB98', '#87CEFA', '#FFB6C1', '#DDA0DD']
    patches = [plt.Rectangle((0,0),1,1, color=c) for c in legend_colors]
    ax.legend(patches, legend_labels, loc='lower left')
    
    # 添加颜色条
    cbar = plt.colorbar(sc)
    cbar.set_label('O型血频率 (%)')
    
    # 设置地图背景
    ax.set_facecolor('#d4eaf0')
    ax.grid(color='gray', linestyle='--', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('global_distribution.png', dpi=300)
    plt.show()

# 3. 血型与疾病易感性关系图
def plot_disease_susceptibility():
    # 创建模拟数据
    diseases = ['疟疾', '霍乱', '诺如病毒', '天花', '胃癌', '血栓', '胰腺癌', 'COVID-19重症']
    blood_types = ['O', 'A', 'B', 'AB']
    
    # 相对风险 (1.0 = 平均风险)
    risk_data = {
        '疟疾': [0.7, 1.0, 1.1, 1.2],
        '霍乱': [1.3, 0.9, 1.0, 0.8],
        '诺如病毒': [1.4, 0.8, 0.9, 0.7],
        '天花': [0.8, 1.4, 0.9, 1.1],
        '胃癌': [1.2, 0.9, 1.1, 1.3],
        '血栓': [0.8, 1.1, 1.0, 1.5],
        '胰腺癌': [0.9, 1.2, 1.1, 1.0],
        'COVID-19重症': [0.9, 1.1, 1.0, 1.2]
    }
    
    df = pd.DataFrame(risk_data, index=blood_types).T
    
    # 创建热图
    plt.figure(figsize=(12, 8))
    sns.heatmap(df, annot=True, fmt=".1f", cmap="coolwarm", 
                linewidths=0.5, cbar_kws={'label': '相对风险'})
    
    plt.title('血型与疾病易感性关联', fontsize=16, pad=20)
    plt.xlabel('血型')
    plt.ylabel('疾病')
    
    plt.tight_layout()
    plt.savefig('disease_susceptibility.png', dpi=300)
    plt.show()

# 4. 血型进化模拟动画
def simulate_blood_type_evolution():
    # 初始化群体
    population_size = 500
    generations = 100
    
    # 初始基因频率 (A, B, O)
    freq = np.array([0.25, 0.25, 0.50])  # A, B, O
    
    # 存储每一代的频率
    history = np.zeros((generations, 3))
    
    # 模拟参数
    malaria_pressure = 0.3  # 疟疾选择压力强度
    cholera_pressure = 0.1  # 霍乱选择压力强度
    
    # 创建图形
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.set_xlim(0, generations)
    ax.set_ylim(0, 1)
    ax.set_xlabel('世代')
    ax.set_ylabel('基因频率')
    ax.set_title('ABO血型基因频率进化模拟', fontsize=16)
    
    # 初始化线条
    line_a, = ax.plot([], [], 'b-', lw=2, label='A基因')
    line_b, = ax.plot([], [], 'r-', lw=2, label='B基因')
    line_o, = ax.plot([], [], 'g-', lw=2, label='O基因')
    
    # 添加图例
    ax.legend(loc='upper right')
    
    # 添加文本框显示参数
    text_box = ax.text(0.7, 0.9, '', transform=ax.transAxes, 
                      bbox=dict(facecolor='white', alpha=0.8))
    
    # 添加事件标记
    ax.axvline(x=20, color='gray', linestyle='--', alpha=0.5)
    ax.text(20, 0.05, '疟疾流行开始', rotation=90, fontsize=10)
    
    ax.axvline(x=60, color='gray', linestyle='--', alpha=0.5)
    ax.text(60, 0.05, '霍乱流行开始', rotation=90, fontsize=10)
    
    # 初始化函数
    def init():
        line_a.set_data([], [])
        line_b.set_data([], [])
        line_o.set_data([], [])
        text_box.set_text('')
        return line_a, line_b, line_o, text_box
    
    # 更新函数
    def update(frame):
        nonlocal freq
        
        # 记录当前频率
        history[frame] = freq
        
        # 自然选择作用
        # O型在疟疾流行期有优势
        if frame > 20 and frame < 50:
            fitness = np.array([
                1.0 - malaria_pressure * 0.2,  # A
                1.0 - malaria_pressure * 0.1,  # B
                1.0 + malaria_pressure * 0.3    # O
            ])
            freq = freq * fitness
            freq /= freq.sum()
        
        # A型在霍乱流行期有劣势
        if frame > 60:
            fitness = np.array([
                1.0 - cholera_pressure * 0.4,  # A
                1.0 - cholera_pressure * 0.1,  # B
                1.0 + cholera_pressure * 0.2    # O
            ])
            freq = freq * fitness
            freq /= freq.sum()
        
        # 随机遗传漂变
        drift = np.random.normal(0, 0.02, 3)
        freq += drift
        freq = np.clip(freq, 0.05, 0.9)
        freq /= freq.sum()
        
        # 添加小扰动
        mutation = np.random.choice([-0.01, 0, 0.01], 3, p=[0.1, 0.8, 0.1])
        freq += mutation
        freq = np.clip(freq, 0.05, 0.9)
        freq /= freq.sum()
        
        # 更新数据
        x = np.arange(frame+1)
        line_a.set_data(x, history[:frame+1, 0])
        line_b.set_data(x, history[:frame+1, 1])
        line_o.set_data(x, history[:frame+1, 2])
        
        # 更新文本框
        text_box.set_text(f'世代: {frame}\nA频率: {freq[0]:.2f}\nB频率: {freq[1]:.2f}\nO频率: {freq[2]:.2f}')
        
        return line_a, line_b, line_o, text_box
    
    # 创建动画
    ani = FuncAnimation(fig, update, frames=generations,
                        init_func=init, blit=True, interval=100)
    
    plt.tight_layout()
    plt.show()
    
    # 保存动画 (可选)
    # ani.save('blood_type_evolution.gif', writer='pillow', fps=10)

# 执行所有可视化
plot_biochemical_pathway()
plot_global_distribution()
plot_disease_susceptibility()
simulate_blood_type_evolution()