import numpy as np
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import matplotlib.animation as animation
from matplotlib.patches import Rectangle, Circle
import matplotlib.gridspec as gridspec
from scipy.integrate import odeint
import time

class BuildingStructureSimulator:
    def __init__(self):
        self.fig = plt.figure(figsize=(16, 12))
        self.setup_plots()
        self.animation = None
        
    def setup_plots(self):
        gs = gridspec.GridSpec(2, 3, figure=self.fig)
        
        # 金字塔结构图
        self.ax_pyramid = self.fig.add_subplot(gs[0, 0], projection='3d')
        self.ax_pyramid.set_title("金字塔结构 - 稳定性分析")
        
        # 高层建筑防风图
        self.ax_tower = self.fig.add_subplot(gs[0, 1])
        self.ax_tower.set_title("高层建筑防风设计")
        
        # 风荷载影响图
        self.ax_wind = self.fig.add_subplot(gs[0, 2])
        self.ax_wind.set_title("风荷载对建筑的影响")
        
        # 结构稳定性参数图
        self.ax_stability = self.fig.add_subplot(gs[1, 0])
        self.ax_stability.set_title("结构稳定性参数")
        
        # 建筑振动模拟图
        self.ax_vibration = self.fig.add_subplot(gs[1, 1])
        self.ax_vibration.set_title("建筑振动响应")
        
        # 材料强度分析图
        self.ax_material = self.fig.add_subplot(gs[1, 2])
        self.ax_material.set_title("材料强度与耐久性")
        
        plt.tight_layout()
    
    def pyramid_stability_analysis(self, base_size=10, height=15):
        """分析金字塔结构的稳定性"""
        self.ax_pyramid.clear()
        self.ax_pyramid.set_title("金字塔结构 - 稳定性分析")
        
        # 定义金字塔顶点
        vertices = np.array([
            [0, 0, 0],           # 底面点0
            [base_size, 0, 0],   # 底面点1
            [base_size, base_size, 0], # 底面点2
            [0, base_size, 0],   # 底面点3
            [base_size/2, base_size/2, height]  # 顶点
        ])
        
        # 定义金字塔的面
        faces = [
            [vertices[0], vertices[1], vertices[4]],  # 侧面1
            [vertices[1], vertices[2], vertices[4]],  # 侧面2
            [vertices[2], vertices[3], vertices[4]],  # 侧面3
            [vertices[3], vertices[0], vertices[4]],  # 侧面4
            [vertices[0], vertices[1], vertices[2], vertices[3]]  # 底面
        ]
        
        # 创建3D多边形集合
        poly3d = Poly3DCollection(faces, 
                                 facecolors=['gold', 'gold', 'gold', 'gold', 'orange'],
                                 alpha=0.7, linewidths=1, edgecolors='k')
        
        self.ax_pyramid.add_collection3d(poly3d)
        
        # 设置坐标轴
        self.ax_pyramid.set_xlabel('X (m)')
        self.ax_pyramid.set_ylabel('Y (m)')
        self.ax_pyramid.set_zlabel('Z (m)')
        self.ax_pyramid.set_xlim([0, base_size])
        self.ax_pyramid.set_ylim([0, base_size])
        self.ax_pyramid.set_zlim([0, height])
        
        # 计算稳定性指标
        base_area = base_size ** 2
        volume = (base_area * height) / 3
        center_of_mass_height = height / 4  # 金字塔重心高度
        stability_factor = base_area / center_of_mass_height
        
        # 添加文本信息
        self.ax_pyramid.text2D(0.05, 0.95, 
                              f"底面积: {base_area:.1f} m²\n"
                              f"体积: {volume:.1f} m³\n"
                              f"重心高度: {center_of_mass_height:.1f} m\n"
                              f"稳定系数: {stability_factor:.1f}", 
                              transform=self.ax_pyramid.transAxes,
                              bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8))
        
        # 添加重心标记
        self.ax_pyramid.scatter([base_size/2], [base_size/2], [center_of_mass_height], 
                               color='red', s=100, label='重心')
        self.ax_pyramid.legend()
        
        return stability_factor
    
    def tall_building_wind_resistance(self, height=300, width=50, damping_ratio=0.05):
        """模拟高层建筑的防风设计"""
        self.ax_tower.clear()
        self.ax_tower.set_title("高层建筑防风设计")
        
        # 绘制建筑轮廓
        building = Rectangle((0, 0), width, height, fill=True, 
                            color='lightblue', alpha=0.7, edgecolor='black', linewidth=2)
        self.ax_tower.add_patch(building)
        
        # 绘制建筑内部结构
        for i in range(10):
            floor_height = height * (i + 1) / 10
            self.ax_tower.plot([0, width], [floor_height, floor_height], 'gray', alpha=0.3)
        
        # 风荷载计算
        wind_strength = np.linspace(0, 150, 20)  # 风速范围 0-150 m/s
        wind_pressure = 0.5 * 1.225 * wind_strength**2  # 风压公式
        
        # 计算建筑在不同风速下的响应
        natural_frequency = 1 / (height / 50)
        responses = []
        
        for pressure in wind_pressure:
            # 简化的动力响应计算
            dynamic_response = pressure * height / (2 * np.pi * natural_frequency * damping_ratio)
            responses.append(min(dynamic_response, height * 0.3))  # 限制最大响应
        
        # 绘制风荷载
        wind_arrow_length = max(responses) / 8
        for i in range(5):
            h = height * (i + 1) / 6
            self.ax_tower.arrow(width + 5, h, wind_arrow_length, 0, 
                               head_width=5, head_length=3, fc='red', ec='red', alpha=0.7)
        
        # 添加调谐质量阻尼器
        damper_height = height * 0.85
        self.ax_tower.plot([width/2, width/2], [damper_height-15, damper_height+15], 
                          'k-', linewidth=4)
        damper = Circle((width/2, damper_height), 8, color='red', alpha=0.8)
        self.ax_tower.add_patch(damper)
        self.ax_tower.text(width/2 + 10, damper_height, '调谐质量阻尼器', va='center')
        
        # 添加抗风结构说明
        self.ax_tower.text(width/2, height*0.7, '核心筒结构', 
                          ha='center', va='center', rotation=90,
                          bbox=dict(boxstyle="round", facecolor="yellow", alpha=0.5))
        
        self.ax_tower.set_xlim([-20, width + 80])
        self.ax_tower.set_ylim([0, height + 20])
        self.ax_tower.set_xlabel('宽度 (m)')
        self.ax_tower.set_ylabel('高度 (m)')
        self.ax_tower.grid(True, alpha=0.3)
        self.ax_tower.set_aspect('equal')
        
        return wind_strength, responses
    
    def wind_effect_analysis(self, wind_speeds, responses):
        """分析风荷载对建筑的影响"""
        self.ax_wind.clear()
        self.ax_wind.set_title("风荷载对建筑的影响")
        
        # 绘制风速与建筑响应的关系
        self.ax_wind.plot(wind_speeds, responses, 'b-o', linewidth=2, markersize=6, 
                         label='建筑响应')
        
        # 绘制风压曲线
        wind_pressure = 0.5 * 1.225 * wind_speeds**2
        self.ax_wind.plot(wind_speeds, wind_pressure/100, 'g--', linewidth=2, 
                         label='风压/100')
        
        self.ax_wind.set_xlabel('风速 (m/s)')
        self.ax_wind.set_ylabel('建筑响应 (位移) / 风压 (Pa/100)')
        self.ax_wind.grid(True, alpha=0.3)
        
        # 标记不同风速区域
        self.ax_wind.axvspan(0, 25, alpha=0.2, color='green', label='安全区域')
        self.ax_wind.axvspan(25, 60, alpha=0.2, color='yellow', label='注意区域')
        self.ax_wind.axvspan(60, 150, alpha=0.2, color='red', label='危险区域')
        self.ax_wind.legend()
        
        # 添加临界点标记
        critical_indices = [5, 10, 15]  # 多个临界点
        for i, idx in enumerate(critical_indices):
            if idx < len(wind_speeds):
                self.ax_wind.plot([wind_speeds[idx], wind_speeds[idx]], [0, responses[idx]], 
                                 'r--', linewidth=1, alpha=0.7)
                self.ax_wind.annotate(f'P{i+1}\n({wind_speeds[idx]} m/s)', 
                                     xy=(wind_speeds[idx], responses[idx]),
                                     xytext=(10, 20*(i+1)), textcoords='offset points',
                                     bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8),
                                     arrowprops=dict(arrowstyle="->", color='red'))
    
    def structural_stability_parameters(self):
        """分析结构稳定性参数"""
        self.ax_stability.clear()
        self.ax_stability.set_title("结构稳定性参数分析")
        
        # 不同建筑形状的参数
        shapes = ['金字塔', '矩形建筑', '锥形', '圆柱', '倒金字塔', '拱形']
        stability_factors = [8.5, 3.2, 6.7, 5.1, 1.8, 7.2]
        wind_resistance = [9.2, 4.5, 7.8, 6.3, 2.1, 8.5]  # 抗风能力
        earthquake_resistance = [8.8, 3.8, 7.2, 5.8, 1.5, 6.9]  # 抗震能力
        
        x = np.arange(len(shapes))
        width = 0.25
        
        # 绘制多个参数
        bars1 = self.ax_stability.bar(x - width, stability_factors, width, 
                                     label='稳定系数', color='gold', alpha=0.7)
        bars2 = self.ax_stability.bar(x, wind_resistance, width, 
                                     label='抗风能力', color='lightblue', alpha=0.7)
        bars3 = self.ax_stability.bar(x + width, earthquake_resistance, width, 
                                     label='抗震能力', color='lightcoral', alpha=0.7)
        
        # 添加数值标签
        for bars in [bars1, bars2, bars3]:
            for bar in bars:
                height = bar.get_height()
                self.ax_stability.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                                      f'{height:.1f}', ha='center', va='bottom', fontsize=8)
        
        self.ax_stability.set_ylabel('性能评分 (0-10)')
        self.ax_stability.set_xticks(x)
        self.ax_stability.set_xticklabels(shapes, rotation=45)
        self.ax_stability.set_ylim(0, 12)
        self.ax_stability.legend()
        self.ax_stability.grid(True, alpha=0.3, axis='y')
        
        # 添加说明
        self.ax_stability.text(0.02, 0.98, 
                              "金字塔结构:\n- 低重心\n- 宽基底\n- 优异稳定性", 
                              transform=self.ax_stability.transAxes,
                              bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8))
    
    def building_vibration_simulation(self, duration=20):
        """模拟建筑振动响应 - 增强版本"""
        self.ax_vibration.clear()
        self.ax_vibration.set_title("建筑振动响应分析")
        
        # 建筑振动模型
        def building_vibration(y, t, m, c, k, f_func):
            dydt = [y[1], (f_func(t) - c*y[1] - k*y[0])/m]
            return dydt
        
        # 参数设置 - 不同建筑类型
        params = [
            {'m': 800, 'k': 8000, 'c': 400, 'label': '低层建筑', 'color': 'blue'},
            {'m': 1200, 'k': 12000, 'c': 600, 'label': '中层建筑', 'color': 'green'},
            {'m': 2000, 'k': 20000, 'c': 800, 'label': '高层建筑', 'color': 'red'}
        ]
        
        # 外力函数 - 组合激励（风荷载 + 地震）
        def force_combined(t):
            wind_force = 800 * np.sin(2*np.pi*0.3*t)  # 风荷载
            earthquake_force = 500 * np.sin(2*np.pi*2.0*t) * np.exp(-0.1*t)  # 地震荷载
            return wind_force + earthquake_force
        
        # 时间点
        t = np.linspace(0, duration, 1000)
        
        # 求解并绘制不同建筑的响应
        for param in params:
            sol = odeint(building_vibration, [0, 0], t, 
                        args=(param['m'], param['c'], param['k'], force_combined))
            
            # 绘制位移响应
            self.ax_vibration.plot(t, sol[:, 0], color=param['color'], 
                                 linewidth=2, label=param['label'])
        
        # 绘制外力（缩放）
        force_values = [force_combined(ti) for ti in t]
        self.ax_vibration.plot(t, np.array(force_values)/500, 'k--', 
                             linewidth=1, label='外力(缩放)', alpha=0.7)
        
        self.ax_vibration.set_xlabel('时间 (s)')
        self.ax_vibration.set_ylabel('位移 (m) / 力 (N/500)')
        self.ax_vibration.legend()
        self.ax_vibration.grid(True, alpha=0.3)
        
        # 添加共振频率信息
        info_text = "建筑振动特性:\n"
        for param in params:
            natural_freq = np.sqrt(param['k']/param['m']) / (2*np.pi)
            info_text += f"{param['label']}: {natural_freq:.2f} Hz\n"
        
        self.ax_vibration.text(0.02, 0.98, info_text, 
                              transform=self.ax_vibration.transAxes,
                              bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8))
    
    def material_strength_analysis(self):
        """分析材料强度与耐久性 - 增强版本"""
        self.ax_material.clear()
        self.ax_material.set_title("建筑材料性能综合分析")
        
        # 建筑材料性能数据库
        materials = ['花岗岩', '大理石', '混凝土', '钢材', '木材', '复合材料', '玻璃']
        compressive_strength = [200, 100, 40, 250, 5, 150, 50]  # 抗压强度 (MPa)
        tensile_strength = [10, 8, 5, 250, 3, 200, 7]  # 抗拉强度 (MPa)
        durability = [1000, 500, 100, 200, 50, 300, 100]  # 耐久性 (年)
        weight = [2700, 2600, 2400, 7800, 600, 1800, 2500]  # 密度 (kg/m³)
        cost = [80, 120, 30, 60, 20, 150, 40]  # 相对成本
        
        # 创建子图
        ax1 = self.ax_material
        ax2 = ax1.twinx()  # 创建第二个y轴
        
        x = np.arange(len(materials))
        width = 0.35
        
        # 绘制力学性能
        bars1 = ax1.bar(x - width/2, compressive_strength, width, 
                       label='抗压强度 (MPa)', color='lightcoral', alpha=0.7)
        bars2 = ax1.bar(x + width/2, tensile_strength, width, 
                       label='抗拉强度 (MPa)', color='lightblue', alpha=0.7)
        
        # 绘制耐久性曲线
        line = ax2.plot(x, durability, 'g-o', linewidth=3, markersize=8, 
                       label='耐久性 (年)', alpha=0.7)
        
        ax1.set_xlabel('建筑材料')
        ax1.set_ylabel('强度 (MPa)')
        ax2.set_ylabel('耐久性 (年)')
        ax1.set_xticks(x)
        ax1.set_xticklabels(materials, rotation=45)
        
        # 组合图例
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        
        ax1.grid(True, alpha=0.3)
        
        # 添加金字塔建筑材料说明
        self.ax_material.text(0.02, 0.98, 
                             "金字塔建筑材料:\n"
                             "• 花岗岩: 高抗压强度\n" 
                             "• 石灰石: 易于加工\n"
                             "• 耐久性: 4500+年", 
                             transform=self.ax_material.transAxes,
                             bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8))
    
    def create_real_time_animation(self):
        """创建实时振动动画"""
        fig_anim = plt.figure(figsize=(10, 6))
        ax_anim = fig_anim.add_subplot(111)
        
        # 初始化建筑位置
        building_width = 20
        building_height = 100
        x_building = [0, building_width, building_width, 0, 0]
        y_building = [0, 0, building_height, building_height, 0]
        
        building_line, = ax_anim.plot(x_building, y_building, 'b-', linewidth=3)
        
        # 设置动画范围
        ax_anim.set_xlim(-50, 100)
        ax_anim.set_ylim(0, 150)
        ax_anim.set_xlabel('位移')
        ax_anim.set_ylabel('高度')
        ax_anim.set_title('建筑振动实时模拟')
        ax_anim.grid(True, alpha=0.3)
        ax_anim.set_aspect('equal')
        
        def animate(frame):
            # 模拟振动位移
            time = frame * 0.1
            displacement = 10 * np.sin(2 * np.pi * 0.5 * time) * np.exp(-0.02 * time)
            
            # 更新建筑位置
            x_new = [d + displacement for d in x_building]
            building_line.set_data(x_new, y_building)
            
            return building_line,
        
        self.animation = animation.FuncAnimation(fig_anim, animate, frames=200, 
                                               interval=50, blit=True)
        plt.tight_layout()
        plt.show()
    
    def simulate_all(self):
        """执行所有模拟"""
        print("开始建筑结构分析...")
        
        # 金字塔稳定性分析
        print("1. 分析金字塔稳定性...")
        stability_factor = self.pyramid_stability_analysis()
        
        # 高层建筑防风设计
        print("2. 模拟高层建筑防风...")
        wind_speeds, responses = self.tall_building_wind_resistance()
        
        # 风荷载影响分析
        print("3. 分析风荷载影响...")
        self.wind_effect_analysis(wind_speeds, responses)
        
        # 结构稳定性参数
        print("4. 分析结构稳定性参数...")
        self.structural_stability_parameters()
        
        # 建筑振动模拟
        print("5. 模拟建筑振动...")
        self.building_vibration_simulation()
        
        # 材料强度分析
        print("6. 分析材料强度...")
        self.material_strength_analysis()
        
        plt.tight_layout()
        plt.show()
        
        # 询问是否查看动画
        response = input("是否查看实时振动动画? (y/n): ")
        if response.lower() == 'y':
            self.create_real_time_animation()
    
    def save_report(self, filename="建筑结构分析报告.txt"):
        """生成分析报告"""
        report = f"""
建筑结构分析报告
生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}

1. 金字塔结构分析:
   - 最稳定的古代建筑形式
   - 宽基底、低重心的设计
   - 抗风抗震性能优异

2. 现代高层建筑:
   - 需要综合考虑风荷载和地震作用
   - 采用核心筒结构和阻尼器
   - 材料选择至关重要

3. 关键发现:
   - 金字塔的稳定系数远高于其他形式
   - 钢材在抗拉强度方面表现最佳
   - 复合材料综合性能优异

4. 设计建议:
   - 重要建筑应考虑金字塔的稳定性原理
   - 高层建筑必须设置抗风阻尼系统
   - 材料选择应考虑耐久性和强度平衡
"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"分析报告已保存至: {filename}")

# 创建模拟器并运行模拟
if __name__ == "__main__":
    simulator = BuildingStructureSimulator()
    simulator.simulate_all()
    
    # 保存分析报告
    simulator.save_report()
    
    print("建筑结构分析完成!")