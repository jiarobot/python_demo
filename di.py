import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.colors import LinearSegmentedColormap
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import ipywidgets as widgets
from IPython.display import display
import pandas as pd
from pylab import mpl
# 设置显示中文字体
mpl.rcParams["font.sans-serif"] = ["SimHei"]
# 创建模拟数据 - 大陆轮廓随时间变化
def generate_continental_data():
    # 大陆位置数据 (经度, 纬度, 时间)
    # 这里简化了真实的大陆漂移数据
    times = np.linspace(-250, 0, 100)  # 从250百万年前到现在
    
    # 各大陆的位置变化轨迹
    continents = {
        'Africa': {'path': lambda t: (20 - 0.02*t, 5 + 0.01*t)},
        'South America': {'path': lambda t: (-50 + 0.03*t, -20 - 0.005*t)},
        'North America': {'path': lambda t: (-100 + 0.04*t, 40 - 0.01*t)},
        'Eurasia': {'path': lambda t: (40 - 0.01*t, 50 + 0.005*t)},
        'India': {'path': lambda t: (60 - 0.05*t, -40 + 0.07*t)},
        'Australia': {'path': lambda t: (120 - 0.03*t, -50 + 0.02*t)},
        'Antarctica': {'path': lambda t: (20, -90)}
    }
    
    # 生成每个时间点的大陆轮廓
    continental_data = []
    for t in times:
        frame = []
        for name, data in continents.items():
            lon, lat = data['path'](t)
            # 创建简化的大陆轮廓
            lons = lon + 30 * np.cos(np.linspace(0, 2*np.pi, 50))
            lats = lat + 15 * np.sin(np.linspace(0, 2*np.pi, 50))
            frame.append({
                'name': name,
                'lons': lons,
                'lats': lats,
                'time': t
            })
        continental_data.append(frame)
    
    return continental_data, times

# 创建海平面数据 - 基于地质时期的海平面变化
def generate_sea_level_data(times):
    # 海平面变化模型 (简化)
    # 数据来源: Haq et al. (1987) 海平面曲线
    sea_levels = 50 * np.sin(0.05 * times) + 30 * np.sin(0.1 * times + 2)
    
    # 添加一些地质事件的影响
    for i, t in enumerate(times):
        if -65 < t < -60:  # K-T灭绝事件
            sea_levels[i] -= 20
        if -250 < t < -240:  # 二叠纪-三叠纪灭绝事件
            sea_levels[i] -= 30
        if -200 < t < -190:  # 三叠纪-侏罗纪灭绝事件
            sea_levels[i] -= 15
            
    return sea_levels

# 创建气候带数据 - 基于地球轨道参数和大陆位置
def generate_climate_zones(times, continental_data):
    climate_zones = []
    
    for idx, frame in enumerate(continental_data):
        t = times[idx]
        
        # 气候带受地球轨道参数影响
        eccentricity = 0.02 * np.sin(0.03 * t)  # 地球轨道偏心率
        obliquity = 23.5 + 2 * np.sin(0.04 * t)  # 黄赤交角
        
        # 计算气候带边界
        tropics = obliquity
        arctic_circle = 90 - obliquity
        
        # 大陆位置对气候的影响
        continent_effect = 0
        for continent in frame:
            # 大陆在高纬度地区会增加寒冷效应
            if np.max(np.abs(continent['lats'])) > 60:
                continent_effect -= 5
        
        # 创建气候带数据
        zones = {
            'equator': 0,
            'tropics': tropics,
            'temperate': arctic_circle - 15,
            'arctic': arctic_circle,
            'effect': continent_effect
        }
        climate_zones.append(zones)
    
    return climate_zones

# 创建可视化
def create_visualization():
    # 生成数据
    continental_data, times = generate_continental_data()
    sea_levels = generate_sea_level_data(times)
    climate_zones = generate_climate_zones(times, continental_data)
    
    # 设置地图投影
    projection = ccrs.Orthographic(central_longitude=0, central_latitude=0)
    transform = ccrs.PlateCarree()
    
    # 创建图形
    fig = plt.figure(figsize=(15, 12), facecolor='#1a1a1a')
    fig.suptitle('地理变迁模拟：大陆漂移与海平面变化', 
                fontsize=20, color='white', fontweight='bold', y=0.95)
    
    # 创建三个子图
    ax1 = fig.add_subplot(2, 2, 1, projection=projection)
    ax2 = fig.add_subplot(2, 2, 2)
    ax3 = fig.add_subplot(2, 2, (3, 4))
    
    # 设置图形背景色
    for ax in [ax1, ax2, ax3]:
        ax.set_facecolor('#1a1a1a')
    
    # 配置地图
    ax1.set_global()
    ax1.add_feature(cfeature.OCEAN, color='#0a3d62', zorder=0)
    ax1.add_feature(cfeature.LAND, color='#3a5a40', zorder=1)
    ax1.add_feature(cfeature.COASTLINE, linewidth=0.5, zorder=2)
    ax1.gridlines(color='gray', linestyle='--', alpha=0.3)
    
    # 海平面图配置
    ax2.set_title('海平面变化 (相对于现代)', color='white', fontsize=14)
    ax2.set_xlabel('时间 (百万年前)', color='white')
    ax2.set_ylabel('海平面变化 (米)', color='white')
    ax2.set_xlim(-250, 0)
    ax2.set_ylim(-150, 150)
    ax2.grid(color='gray', linestyle='--', alpha=0.3)
    ax2.tick_params(colors='white')
    ax2.spines['bottom'].set_color('white')
    ax2.spines['top'].set_color('white')
    ax2.spines['left'].set_color('white')
    ax2.spines['right'].set_color('white')
    
    # 气候带图配置
    ax3.set_title('气候带分布', color='white', fontsize=14)
    ax3.set_xlabel('纬度', color='white')
    ax3.set_ylabel('温度 (°C)', color='white')
    ax3.set_xlim(-90, 90)
    ax3.set_ylim(-30, 40)
    ax3.grid(color='gray', linestyle='--', alpha=0.3)
    ax3.tick_params(colors='white')
    ax3.spines['bottom'].set_color('white')
    ax3.spines['top'].set_color('white')
    ax3.spines['left'].set_color('white')
    ax3.spines['right'].set_color('white')
    
    # 初始化大陆绘图元素
    continent_plots = []
    for continent in continental_data[0]:
        plot, = ax1.plot([], [], transform=transform, 
                        linewidth=1.5, zorder=3)
        continent_plots.append(plot)
    
    # 初始化海平面图
    sea_level_line, = ax2.plot([], [], 'c-', linewidth=2, label='海平面')
    sea_level_point, = ax2.plot([], [], 'co', markersize=8)
    ax2.legend(loc='upper right', facecolor='#2a2a2a', labelcolor='white')
    
    # 初始化气候带图
    climate_fill = ax3.fill_between([], [], [], color='yellow', alpha=0.3, label='热带')
    climate_lines = []
    for _ in range(4):
        line, = ax3.plot([], [], 'w--', alpha=0.7)
        climate_lines.append(line)
    ax3.legend(loc='lower right', facecolor='#2a2a2a', labelcolor='white')
    
    # 时间文本
    time_text = ax1.text(0.5, -0.1, '', transform=ax1.transAxes, 
                        color='white', fontsize=16, ha='center')
    
    # 添加地质时期标签
    periods = [
        {'name': '二叠纪', 'start': -299, 'end': -252},
        {'name': '三叠纪', 'start': -252, 'end': -201},
        {'name': '侏罗纪', 'start': -201, 'end': -145},
        {'name': '白垩纪', 'start': -145, 'end': -66},
        {'name': '古近纪', 'start': -66, 'end': -23},
        {'name': '新近纪', 'start': -23, 'end': -2.6},
        {'name': '第四纪', 'start': -2.6, 'end': 0}
    ]
    
    # 在时间轴上标记地质时期
    for period in periods:
        mid = (period['start'] + period['end']) / 2
        ax2.text(mid, 130, period['name'], color='white', 
                ha='center', fontsize=9, alpha=0.7)
        ax2.axvspan(period['start'], period['end'], 
                   color='gray', alpha=0.1)
    
    # 添加重大地质事件标记
    events = [
        {'time': -252, 'name': '二叠纪-三叠纪\n大灭绝', 'y': 120},
        {'time': -201, 'name': '三叠纪-侏罗纪\n大灭绝', 'y': 110},
        {'time': -66, 'name': '白垩纪-古近纪\n大灭绝', 'y': 100},
        {'time': -2.6, 'name': '第四纪\n大冰期', 'y': 90}
    ]
    
    for event in events:
        ax2.plot([event['time'], event['time']], [-150, event['y']-10], 
                'r--', alpha=0.5)
        ax2.text(event['time'], event['y'], event['name'], 
                color='red', ha='center', fontsize=8)
    
    # 创建自定义颜色映射表示海平面变化
    cmap = LinearSegmentedColormap.from_list('sea_level', 
                                           ['#a83232', '#1a1a1a', '#326ba8'])
    
    # 动画更新函数
    def update(frame_idx):
        # 更新时间文本
        time_val = times[frame_idx]
        time_text.set_text(f'{abs(time_val):.1f} 百万年前')
        
        # 更新大陆位置
        frame = continental_data[frame_idx]
        for i, continent in enumerate(frame):
            continent_plots[i].set_data(continent['lons'], continent['lats'])
        
        # 更新海平面图
        current_time = times[frame_idx]
        sea_level_line.set_data(times[:frame_idx+1], sea_levels[:frame_idx+1])
        sea_level_point.set_data([current_time], [sea_levels[frame_idx]])
        
        # 更新背景色表示海平面变化
        norm_level = (sea_levels[frame_idx] + 150) / 300
        bg_color = cmap(norm_level)
        ax1.add_feature(cfeature.OCEAN, color=bg_color, zorder=0)
        
        # 更新气候带
        zones = climate_zones[frame_idx]
        tropics = zones['tropics']
        arctic = zones['arctic']
        
        # 更新气候带填充区域
        lats = np.linspace(-90, 90, 100)
        temps = 30 * np.cos(np.deg2rad(lats)) + zones['effect']
        
        # 清除旧填充
        for collection in ax3.collections:
            collection.remove()
        
        # 绘制新气候带
        ax3.fill_between(lats, -30, 40, where=(np.abs(lats) < tropics), 
                        color='yellow', alpha=0.3, label='热带')
        ax3.fill_between(lats, -30, 40, where=(np.abs(lats) > arctic), 
                        color='lightblue', alpha=0.4, label='极地')
        ax3.fill_between(lats, -30, 40, 
                        where=((lats > tropics) & (lats < arctic)) | 
                              ((lats < -tropics) & (lats > -arctic)), 
                        color='green', alpha=0.3, label='温带')
        
        # 更新气候带边界线
        for line, lat in zip(climate_lines, 
                           [-tropics, tropics, -arctic, arctic]):
            line.set_data([lat, lat], [-30, 40])
        
        # 更新温度曲线
        if 'temp_curve' in locals():
            temp_curve.remove()
        temp_curve = ax3.plot(lats, temps, 'w-', linewidth=2, label='地表温度')[0]
        ax3.legend(loc='lower right', facecolor='#2a2a2a', labelcolor='white')
        
        return continent_plots + [sea_level_line, sea_level_point, time_text, temp_curve]
    
    # 创建动画
    ani = FuncAnimation(fig, update, frames=len(times), 
                        interval=100, blit=True)
    
    # 添加控制面板
    control_panel = widgets.VBox([
        widgets.Label('地理变迁模拟控制器', style={'description_width': 'initial'}),
        widgets.IntSlider(value=50, min=0, max=99, step=1, 
                         description='时间点:', style={'description_width': 'initial'})
    ])
    
    # 显示动画
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.show()
    
    return ani

# 运行可视化
if __name__ == "__main__":
    animation = create_visualization()