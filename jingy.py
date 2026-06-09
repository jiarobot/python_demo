import numpy as np
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.patches import Circle, Ellipse, Rectangle
import matplotlib.animation as animation
from scipy import integrate
import pandas as pd
from mpl_toolkits.mplot3d import Axes3D
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# 设置中文字体和样式


class SemenAnalysisVisualization:
    def __init__(self):
        self.composition_data = {
            '成分': ['精囊腺分泌物', '前列腺分泌物', '精子', '尿道球腺分泌物', '其他'],
            '百分比': [65, 25, 5, 4, 1],
            '颜色': ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7']
        }
        
        self.nutrient_data = {
            '营养物质': ['果糖', '前列腺素', '锌离子', '柠檬酸', '蛋白质', '抗氧化剂'],
            '浓度范围_min': [1.2, 0.08, 0.12, 20, 35, 0.05],
            '浓度范围_max': [5.0, 0.15, 0.25, 50, 60, 0.15],
            '单位': ['mg/mL', 'mg/mL', 'mg/mL', 'mg/mL', 'mg/mL', 'mg/mL']
        }
        
    def create_composition_pie_chart(self):
        """创建精液成分饼图"""
        fig, ax = plt.subplots(1, 2, figsize=(15, 6))
        
        # 饼图
        wedges, texts, autotexts = ax[0].pie(
            self.composition_data['百分比'],
            labels=self.composition_data['成分'],
            colors=self.composition_data['颜色'],
            autopct='%1.1f%%',
            startangle=90
        )
        
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
        
        ax[0].set_title('精液成分组成分析', fontsize=14, fontweight='bold')
        
        # 堆叠柱状图显示详细成分
        gland_components = {
            '精囊腺': ['果糖', '前列腺素', '凝固因子', '抗坏血酸'],
            '前列腺': ['PSA', '锌离子', '柠檬酸', '酸性磷酸酶'],
            '精子': ['头部(DNA)', '中部(线粒体)', '尾部(鞭毛)'],
            '尿道球腺': ['粘蛋白', '缓冲物质']
        }
        
        bottom = 0
        colors = ['#FF9999', '#66B3FF', '#99FF99', '#FFCC99']
        
        for i, (gland, components) in enumerate(gland_components.items()):
            values = [len(components)] * len(components)
            ax[1].bar(gland, values, bottom=bottom, color=colors[i], 
                     label=f'{gland}: {", ".join(components)}')
            bottom += len(components)
        
        ax[1].set_ylabel('成分数量')
        ax[1].set_title('各腺体主要分泌物组成')
        ax[1].legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax[1].tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        return fig

    def simulate_sperm_motility(self, num_sperm=50, duration=10):
        """模拟精子运动模式"""
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # 创建女性生殖道背景
        uterus = Ellipse((0, 0), 4, 6, fill=True, color='lightpink', alpha=0.3)
        fallopian_tubes = [Rectangle((-2.5, 2), 1, 0.5, color='lightcoral', alpha=0.4),
                          Rectangle((1.5, 2), 1, 0.5, color='lightcoral', alpha=0.4)]
        
        ax.add_patch(uterus)
        for tube in fallopian_tubes:
            ax.add_patch(tube)
        
        # 模拟精子运动
        np.random.seed(42)
        time_points = np.linspace(0, duration, 100)
        
        for i in range(num_sperm):
            # 不同的运动模式
            if i % 3 == 0:  # 直线运动
                x = 0.1 * time_points * np.cos(i * 0.1) + np.random.normal(0, 0.1)
                y = 0.15 * time_points * np.sin(i * 0.1) + np.random.normal(0, 0.1)
            elif i % 3 == 1:  # 曲线运动
                x = 0.08 * time_points * np.cos(i * 0.2) + 0.1 * np.sin(time_points)
                y = 0.12 * time_points * np.sin(i * 0.2) + 0.1 * np.cos(time_points)
            else:  # 超活化运动
                x = 0.05 * time_points + 0.2 * np.sin(time_points * 3)
                y = 0.1 * time_points + 0.2 * np.cos(time_points * 3)
            
            ax.plot(x, y, 'b-', alpha=0.6, linewidth=0.8)
            ax.plot(x[-1], y[-1], 'bo', markersize=3)
        
        ax.set_xlim(-3, 3)
        ax.set_ylim(-3, 5)
        ax.set_xlabel('位置 X')
        ax.set_ylabel('位置 Y')
        ax.set_title('精子在女性生殖道中的运动轨迹模拟', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        # 添加图例
        ax.text(-2.8, 4.5, '直线运动', color='blue', fontsize=10)
        ax.text(-2.8, 4.2, '曲线运动', color='green', fontsize=10)
        ax.text(-2.8, 3.9, '超活化运动', color='red', fontsize=10)
        
        return fig

    def create_biochemical_pathways(self):
        """创建精液生化途径图"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        
        # 能量代谢途径
        energy_steps = {
            '果糖摄入': ('GLUT5转运体', '#FF6B6B'),
            '糖酵解': ('ATP生成', '#4ECDC4'), 
            '鞭毛运动': ('动力蛋白激活', '#45B7D1')
        }
        
        y_pos = 0
        for i, (step, (process, color)) in enumerate(energy_steps.items()):
            ax1.add_patch(Rectangle((0.1, y_pos), 0.8, 0.3, color=color, alpha=0.7))
            ax1.text(0.5, y_pos + 0.15, f'{step}\n{process}', 
                    ha='center', va='center', fontweight='bold', fontsize=10)
            
            if i < len(energy_steps) - 1:
                ax1.arrow(0.5, y_pos - 0.1, 0, -0.2, head_width=0.05, head_length=0.05, fc='k')
            y_pos -= 0.5
        
        ax1.set_xlim(0, 1)
        ax1.set_ylim(-1.5, 0.5)
        ax1.set_title('精子能量代谢途径', fontsize=12, fontweight='bold')
        ax1.axis('off')
        
        # 液化凝固平衡
        time = np.linspace(0, 30, 100)
        coagulation = np.exp(-time/2)  # 凝固因子衰减
        liquefaction = 1 - np.exp(-time/5)  # 液化因子增加
        
        ax2.plot(time, coagulation, 'r-', linewidth=2, label='凝固因子活性')
        ax2.plot(time, liquefaction, 'b-', linewidth=2, label='液化因子活性')
        ax2.fill_between(time, coagulation, liquefaction, where=(coagulation > liquefaction), 
                        color='red', alpha=0.3, label='凝固期')
        ax2.fill_between(time, liquefaction, coagulation, where=(liquefaction > coagulation), 
                        color='blue', alpha=0.3, label='液化期')
        
        ax2.set_xlabel('时间 (分钟)')
        ax2.set_ylabel('相对活性')
        ax2.set_title('精液凝固-液化动态平衡', fontsize=12, fontweight='bold')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        return fig

    def simulate_environmental_effects(self):
        """模拟环境因素对精液质量的影响"""
        factors = ['温度升高', '氧化应激', '重金属暴露', '内分泌干扰物', '营养缺乏']
        
        # 模拟不同因素对各项参数的影响
        np.random.seed(42)
        data = []
        
        for factor in factors:
            effects = {
                '精子活力': max(0, 1 - np.random.beta(2, 5)),
                '正常形态率': max(0, 1 - np.random.beta(2, 6)), 
                'DNA完整性': max(0, 1 - np.random.beta(3, 8)),
                '浓度': max(0, 1 - np.random.beta(2, 7))
            }
            effects['综合影响'] = np.mean(list(effects.values()))
            effects['因素'] = factor
            data.append(effects)
        
        df = pd.DataFrame(data)
        
        # 创建雷达图
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, polar=True)
        
        categories = ['精子活力', '正常形态率', 'DNA完整性', '浓度', '综合影响']
        N = len(categories)
        
        angles = [n / float(N) * 2 * np.pi for n in range(N)]
        angles += angles[:1]
        
        colors = plt.cm.viridis(np.linspace(0, 1, len(factors)))
        
        for i, (idx, row) in enumerate(df.iterrows()):
            values = [row[cat] for cat in categories]
            values += values[:1]
            ax.plot(angles, values, 'o-', linewidth=2, label=row['因素'], color=colors[i])
            ax.fill(angles, values, alpha=0.1, color=colors[i])
        
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories)
        ax.set_ylim(0, 1)
        ax.set_title('环境因素对精液质量的影响模拟', size=14, fontweight='bold')
        ax.legend(bbox_to_anchor=(1.1, 1.0))
        
        return fig

    def create_3d_sperm_model(self):
        """创建3D精子模型"""
        fig = plt.figure(figsize=(12, 10))
        ax = fig.add_subplot(111, projection='3d')
        
        # 创建精子头部（椭球体）
        u = np.linspace(0, 2 * np.pi, 30)
        v = np.linspace(0, np.pi, 30)
        x_head = 0.5 * np.outer(np.cos(u), np.sin(v))
        y_head = 0.3 * np.outer(np.sin(u), np.sin(v)) 
        z_head = 0.4 * np.outer(np.ones(np.size(u)), np.cos(v))
        
        # 创建精子中部（圆柱体 + 线粒体）
        z_mid = np.linspace(-0.5, -1.0, 20)
        theta = np.linspace(0, 2*np.pi, 20)
        theta_grid, z_grid = np.meshgrid(theta, z_mid)
        x_mid = 0.15 * np.cos(theta_grid)
        y_mid = 0.15 * np.sin(theta_grid)
        
        # 创建尾部（螺旋线）
        t = np.linspace(-1, -4, 100)
        x_tail = 0.05 * np.sin(10 * t)
        y_tail = 0.05 * np.cos(10 * t)
        z_tail = t
        
        # 绘制
        ax.plot_surface(x_head, y_head, z_head, color='blue', alpha=0.7, label='头部')
        ax.plot_surface(x_mid, y_mid, z_grid, color='red', alpha=0.7, label='中部')
        ax.plot(x_tail, y_tail, z_tail, 'g-', linewidth=2, label='尾部')
        
        # 添加线粒体点
        mitochondria_z = np.linspace(-0.6, -0.9, 8)
        for mz in mitochondria_z:
            theta_m = np.linspace(0, 2*np.pi, 12)
            x_m = 0.1 * np.cos(theta_m)
            y_m = 0.1 * np.sin(theta_m)
            z_m = np.full_like(x_m, mz)
            ax.scatter(x_m, y_m, z_m, color='orange', s=20, alpha=0.6)
        
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Z')
        ax.set_title('精子3D结构模型', fontsize=14, fontweight='bold')
        ax.legend()
        
        return fig

    def create_interactive_fertility_dashboard(self):
        """创建交互式生育力分析仪表板"""
        # 模拟临床数据
        np.random.seed(42)
        n_patients = 200
        
        data = {
            '年龄': np.random.normal(35, 8, n_patients),
            '精子浓度(百万/mL)': np.random.gamma(2, 15, n_patients),
            '活力(%)': np.random.beta(8, 2, n_patients) * 100,
            '正常形态率(%)': np.random.beta(5, 10, n_patients) * 100,
            'DNA碎片指数(%)': np.random.gamma(3, 5, n_patients),
            '精液量(mL)': np.random.normal(3.5, 1.2, n_patients)
        }
        
        df = pd.DataFrame(data)
        df['生育力评分'] = (
            df['精子浓度(百万/mL)'] / 15 * 0.3 +
            df['活力(%)'] / 40 * 0.3 + 
            df['正常形态率(%)'] / 4 * 0.2 +
            (30 - df['DNA碎片指数(%)']) / 30 * 0.2
        )
        
        # 创建Plotly交互式图表
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('精子浓度 vs 活力', '年龄对精液参数的影响', 
                          'DNA碎片指数分布', '精液参数相关性热图'),
            specs=[[{"type": "scatter"}, {"type": "scatter"}],
                   [{"type": "histogram"}, {"type": "heatmap"}]]
        )
        
        # 散点图：浓度 vs 活力
        fig.add_trace(
            go.Scatter(
                x=df['精子浓度(百万/mL)'],
                y=df['活力(%)'],
                mode='markers',
                marker=dict(
                    size=8,
                    color=df['生育力评分'],
                    colorscale='Viridis',
                    showscale=True,
                    colorbar=dict(title="生育力评分")
                ),
                hovertemplate="<b>浓度</b>: %{x:.1f}百万/mL<br><b>活力</b>: %{y:.1f}%<br><b>评分</b>: %{marker.color:.2f}<extra></extra>"
            ),
            row=1, col=1
        )
        
        # 年龄影响
        age_bins = pd.cut(df['年龄'], bins=[20, 30, 40, 50, 60])
        age_grouped = df.groupby(age_bins).mean()
        
        fig.add_trace(
            go.Scatter(
                x=[25, 35, 45, 55],
                y=age_grouped['精子浓度(百万/mL)'],
                mode='lines+markers',
                name='浓度',
                line=dict(color='blue')
            ),
            row=1, col=2
        )
        
        fig.add_trace(
            go.Scatter(
                x=[25, 35, 45, 55],
                y=age_grouped['活力(%)'],
                mode='lines+markers', 
                name='活力',
                line=dict(color='red')
            ),
            row=1, col=2
        )
        
        # DNA碎片分布
        fig.add_trace(
            go.Histogram(
                x=df['DNA碎片指数(%)'],
                nbinsx=20,
                marker_color='lightcoral',
                opacity=0.7
            ),
            row=2, col=1
        )
        
        # 相关性热图
        corr_matrix = df[['精子浓度(百万/mL)', '活力(%)', '正常形态率(%)', 
                         'DNA碎片指数(%)', '精液量(mL)', '年龄']].corr()
        
        fig.add_trace(
            go.Heatmap(
                z=corr_matrix.values,
                x=corr_matrix.columns,
                y=corr_matrix.columns,
                colorscale='RdBu',
                zmin=-1, zmax=1,
                hoverongaps=False,
                colorbar=dict(title="相关系数")
            ),
            row=2, col=2
        )
        
        fig.update_layout(
            height=800,
            title_text="精液质量分析交互式仪表板",
            showlegend=True
        )
        
        return fig

    def animate_sperm_fertilization(self):
        """创建受精过程动画"""
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # 设置卵子
        egg = Circle((0, 0), 1, color='pink', alpha=0.7)
        ax.add_patch(egg)
        
        # 设置透明带
        zona = Circle((0, 0), 1.2, fill=False, color='gray', linestyle='--', alpha=0.5)
        ax.add_patch(zona)
        
        ax.set_xlim(-3, 3)
        ax.set_ylim(-3, 3)
        ax.set_aspect('equal')
        ax.set_title('精子受精过程模拟', fontsize=14, fontweight='bold')
        
        # 初始化精子
        sperm_dots = []
        sperm_tails = []
        n_sperm = 20
        
        for i in range(n_sperm):
            # 随机初始位置
            angle = np.random.uniform(0, 2*np.pi)
            distance = np.random.uniform(2, 2.8)
            x = distance * np.cos(angle)
            y = distance * np.sin(angle)
            
            dot, = ax.plot(x, y, 'bo', markersize=4)
            tail, = ax.plot([x, x-0.2], [y, y-0.2], 'b-', linewidth=1)
            
            sperm_dots.append(dot)
            sperm_tails.append(tail)
        
        def animate(frame):
            for i, (dot, tail) in enumerate(zip(sperm_dots, sperm_tails)):
                x, y = dot.get_data()
                
                # 计算到卵子的方向
                dx, dy = -x, -y
                dist = np.sqrt(dx**2 + dy**2)
                
                # 归一化并移动
                if dist > 1.2:  # 在透明带外
                    speed = 0.05
                    new_x = x + speed * dx/dist
                    new_y = y + speed * dy/dist
                else:  # 进入透明带，速度减慢
                    speed = 0.02
                    new_x = x + speed * dx/dist
                    new_y = y + speed * dy/dist
                
                # 更新位置
                dot.set_data([new_x], [new_y])
                tail.set_data([new_x, new_x-0.2*np.cos(frame*0.1)], 
                             [new_y, new_y-0.2*np.sin(frame*0.1)])
            
            return sperm_dots + sperm_tails
        
        anim = animation.FuncAnimation(fig, animate, frames=100, 
                                     interval=100, blit=True)
        
        plt.close()
        return anim

# 使用示例
def main():
    viz = SemenAnalysisVisualization()
    
    print("生成精液分析可视化...")
    
    # 1. 成分分析图
    fig1 = viz.create_composition_pie_chart()
    fig1.savefig('semen_composition.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    # 2. 精子运动模拟
    fig2 = viz.simulate_sperm_motility()
    fig2.savefig('sperm_motility.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    # 3. 生化途径图
    fig3 = viz.create_biochemical_pathways()
    fig3.savefig('biochemical_pathways.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    # 4. 环境因素影响
    fig4 = viz.simulate_environmental_effects()
    fig4.savefig('environmental_effects.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    # 5. 3D精子模型
    fig5 = viz.create_3d_sperm_model()
    fig5.savefig('3d_sperm_model.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    # 6. 交互式仪表板 (Plotly)
    fig6 = viz.create_interactive_fertility_dashboard()
    fig6.write_html("fertility_dashboard.html")
    
    # 7. 受精动画
    anim = viz.animate_sperm_fertilization()
    anim.save('fertilization_animation.gif', writer='pillow', fps=10)
    
    print("所有可视化已生成完成！")

if __name__ == "__main__":
    main()