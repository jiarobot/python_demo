import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Button, Slider, RadioButtons, CheckButtons
import matplotlib.patches as patches
import matplotlib.gridspec as gridspec
from matplotlib.animation import FuncAnimation
from matplotlib.colors import LinearSegmentedColormap
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import time
import random
import math
from matplotlib import font_manager as fm
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
# 添加中文支持
try:
    font_path = 'SimHei.ttf'  # 请确保系统中存在中文字体
    zh_font = fm.FontProperties(fname=font_path)
    plt.rcParams['font.family'] = zh_font.get_name()
except:
    print("中文支持初始化失败，将使用默认字体")

class SunTzuSimulatorPro:
    def __init__(self):
        self.fig = plt.figure(figsize=(18, 14), facecolor='#0a0a1a')
        self.fig.suptitle('《孙子兵法》高级策略模拟器：虚实篇', fontsize=28, color='#e6b800', fontweight='bold')
        
        # 设置网格布局
        gs = gridspec.GridSpec(3, 3, width_ratios=[1.5, 1, 1], height_ratios=[1, 1, 1])
        gs.update(left=0.05, right=0.95, bottom=0.05, top=0.92, wspace=0.25, hspace=0.3)
        
        # 创建子图
        self.ax_map = plt.subplot(gs[:, 0])
        self.ax_strategy = plt.subplot(gs[0, 1])
        self.ax_ai = plt.subplot(gs[0, 2])
        self.ax_results = plt.subplot(gs[1, 1])
        self.ax_philosophy = plt.subplot(gs[1, 2])
        self.ax_timeline = plt.subplot(gs[2, 1:])
        
        # 初始化变量
        self.strategy = "以正合，以奇胜"
        self.terrain = "平原"
        self.force_ratio = 0.5
        self.morale = 0.7
        self.surprise = 0.5
        self.weather = "晴朗"
        self.time_of_day = "白天"
        self.troop_quality = 0.6
        self.supply_lines = 0.8
        self.sun_tzu_quotes = [
            "兵者，诡道也。",
            "知己知彼，百战不殆。",
            "攻其无备，出其不意。",
            "凡战者，以正合，以奇胜。",
            "兵无常势，水无常形。",
            "上兵伐谋，其次伐交，其次伐兵，其下攻城。",
            "不战而屈人之兵，善之善者也。",
            "善战者，致人而不致于人。",
            "胜兵先胜而后求战，败兵先战而后求胜。",
            "兵贵胜，不贵久。"
        ]
        self.current_quote = self.sun_tzu_quotes[0]
        self.history = []
        self.outcome = ""
        self.victory_chance = 0.5
        self.battle_phase = "准备阶段"
        self.turn = 0
        self.max_turns = 20
        self.battle_active = False
        self.animation = None
        self.ai_advice = ""
        self.ai_confidence = 0.0
        self.ai_reasoning = ""
        self.historical_battles = {
            "赤壁之战": {"strategy": "火攻", "terrain": "河川", "force_ratio": 0.3, "result": "胜利"},
            "巨鹿之战": {"strategy": "破釜沉舟", "terrain": "平原", "force_ratio": 0.2, "result": "胜利"},
            "淝水之战": {"strategy": "疑兵之计", "terrain": "河川", "force_ratio": 0.25, "result": "胜利"},
            "长平之战": {"strategy": "围歼", "terrain": "山地", "force_ratio": 0.7, "result": "胜利"},
            "官渡之战": {"strategy": "火烧粮草", "terrain": "平原", "force_ratio": 0.4, "result": "胜利"},
            "马拉松战役": {"strategy": "两翼包抄", "terrain": "平原", "force_ratio": 0.3, "result": "胜利"},
            "坎尼会战": {"strategy": "双重包围", "terrain": "平原", "force_ratio": 0.4, "result": "胜利"},
            "滑铁卢战役": {"strategy": "中央突破", "terrain": "丘陵", "force_ratio": 0.9, "result": "失败"}
        }
        
        # 创建热力图的颜色映射
        self.cmap = LinearSegmentedColormap.from_list('war_cmap', ['#003366', '#0066cc', '#66ccff', '#ffffff', '#ffcc66', '#ff6600', '#cc0000'])
        
        # 设置各子图样式
        self.setup_map_axis()
        self.setup_strategy_axis()
        self.setup_ai_axis()
        self.setup_results_axis()
        self.setup_philosophy_axis()
        self.setup_timeline_axis()
        
        # 添加控件
        self.add_controls()
        
        # 训练AI模型
        self.ai_model = self.train_ai_model()
        
        # 初始模拟
        self.simulate_battle()
    
    def setup_map_axis(self):
        self.ax_map.set_title('动态战场态势图', fontsize=18, color='white')
        self.ax_map.set_facecolor('#0a0a2a')
        self.ax_map.set_xticks([])
        self.ax_map.set_yticks([])
        self.ax_map.set_xlim(0, 10)
        self.ax_map.set_ylim(0, 10)
        
        # 添加《孙子兵法》文本
        self.ax_map.text(5, 0.5, "《孙子兵法》核心思想：", 
                        fontsize=14, color='#e6b800', ha='center', va='center')
        self.ax_map.text(5, 0.2, "• 兵者，诡道也 • 知己知彼 • 以正合，以奇胜 • 攻其无备 • 致人而不致于人", 
                        fontsize=10, color='#cccccc', ha='center', va='center')
        
        # 初始化热力图数据
        self.heatmap_data = np.zeros((10, 10))
        self.heatmap = self.ax_map.imshow(self.heatmap_data, cmap=self.cmap, alpha=0.6, 
                                        extent=[0, 10, 0, 10], origin='lower')
    
    def setup_strategy_axis(self):
        self.ax_strategy.set_title('兵法策略选择', fontsize=16, color='white')
        self.ax_strategy.set_facecolor('#0a1a0a')
        self.ax_strategy.set_xticks([])
        self.ax_strategy.set_yticks([])
        
        # 策略说明
        strategies = [
            "以正合，以奇胜 - 正兵迎敌，奇兵取胜",
            "攻其无备 - 攻击敌人没有防备的地方",
            "以逸待劳 - 以我方的安逸对待敌人的疲劳",
            "声东击西 - 佯攻东面，实击西面",
            "围魏救赵 - 攻击敌人要害以解围",
            "擒贼擒王 - 直接攻击敌人首领",
            "十面埋伏 - 设置多重埋伏圈",
            "火攻 - 利用火势攻击敌军",
            "水攻 - 利用水势攻击敌军",
            "疑兵之计 - 制造假象迷惑敌军",
            "空城计 - 虚张声势迷惑敌军",
            "连环计 - 多计并用环环相扣"
        ]
        
        for i, s in enumerate(strategies):
            self.ax_strategy.text(0.05, 0.90 - i*0.08, s, 
                                 fontsize=10, color='#aaffaa', ha='left', va='center',
                                 transform=self.ax_strategy.transAxes)
    
    def setup_ai_axis(self):
        self.ax_ai.set_title('AI策略分析', fontsize=16, color='white')
        self.ax_ai.set_facecolor('#1a0a2a')
        self.ax_ai.set_xticks([])
        self.ax_ai.set_yticks([])
        
        # AI分析文本
        self.ai_title = self.ax_ai.text(0.5, 0.9, "AI分析结果", fontsize=14, color='#66ccff', 
                                      ha='center', va='center', transform=self.ax_ai.transAxes)
        self.ai_advice_text = self.ax_ai.text(0.5, 0.7, "", fontsize=12, color='#ffcc00', 
                                            ha='center', va='center', transform=self.ax_ai.transAxes)
        self.ai_confidence_text = self.ax_ai.text(0.5, 0.5, "", fontsize=12, color='#66ff66', 
                                                ha='center', va='center', transform=self.ax_ai.transAxes)
        self.ai_reasoning_text = self.ax_ai.text(0.5, 0.3, "", fontsize=10, color='#cccccc', 
                                               ha='center', va='top', transform=self.ax_ai.transAxes,
                                               wrap=True)
    
    def setup_results_axis(self):
        self.ax_results.set_title('战略态势分析', fontsize=16, color='white')
        self.ax_results.set_facecolor('#1a0a1a')
        self.ax_results.set_xticks([])
        self.ax_results.set_yticks([])
        
        # 创建能力雷达图
        self.categories = ['兵力对比', '士气', '奇袭效果', '地形优势', '天气', '时间', '部队素质', '后勤']
        self.values = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        
        # 初始雷达图
        angles = np.linspace(0, 2*np.pi, len(self.categories), endpoint=False).tolist()
        self.values += self.values[:1]
        angles += angles[:1]
        
        # 保存填充对象以便后续更新
        self.radar_line, = self.ax_results.plot(angles, self.values, linewidth=2, linestyle='solid', 
                                              color='#ff6600', marker='o', markersize=8)
        self.radar_fill = self.ax_results.fill(angles, self.values, alpha=0.25, color='#ff6600')
        
        # 设置雷达图标签
        self.ax_results.set_xticks(angles[:-1])
        self.ax_results.set_xticklabels(self.categories, color='white', fontsize=8)
        self.ax_results.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
        self.ax_results.set_yticklabels(['20%', '40%', '60%', '80%', '100%'], color='lightgray', fontsize=8)
        self.ax_results.set_ylim(0, 1.1)
        
        # 添加结果文本
        self.result_text = self.ax_results.text(0.5, 0.1, "", fontsize=12, color='yellow',
                                              ha='center', va='center', transform=self.ax_results.transAxes)
    
    def setup_philosophy_axis(self):
        self.ax_philosophy.set_title('《孙子兵法》哲学', fontsize=16, color='white')
        self.ax_philosophy.set_facecolor('#1a1a0a')
        self.ax_philosophy.set_xticks([])
        self.ax_philosophy.set_yticks([])
        
        # 添加《孙子兵法》引言
        self.quote_text = self.ax_philosophy.text(0.5, 0.7, self.current_quote, 
                                                fontsize=18, color='#e6b800', ha='center', va='center',
                                                transform=self.ax_philosophy.transAxes)
        
        # 添加解释文本
        explanation = (
            "《孙子兵法》核心思想：\n\n"
            "• 虚实：避实击虚，集中优势攻击敌人弱点\n"
            "• 奇正：正兵当敌，奇兵取胜\n"
            "• 形势：创造有利态势，掌握战争主动权\n"
            "• 谋攻：上兵伐谋，不战而屈人之兵\n"
            "• 先知：知己知彼，百战不殆\n"
            "• 专分：集中兵力，分散敌人\n"
            "• 速久：速战速决，避免持久战"
        )
        self.ax_philosophy.text(0.5, 0.3, explanation, fontsize=10, color='#cccccc',
                               ha='center', va='top', transform=self.ax_philosophy.transAxes)
    
    def setup_timeline_axis(self):
        self.ax_timeline.set_title('战役时间线', fontsize=16, color='white')
        self.ax_timeline.set_facecolor('#0a1a1a')
        self.ax_timeline.set_xlabel('时间', color='white')
        self.ax_timeline.set_ylabel('我军优势', color='white')
        self.ax_timeline.tick_params(colors='white')
        self.ax_timeline.grid(True, color='#333333', linestyle='--')
        self.ax_timeline.set_xlim(0, self.max_turns)
        self.ax_timeline.set_ylim(0, 1.0)
        
        # 初始化时间线数据
        self.time_data = []
        self.advantage_data = []
        self.timeline, = self.ax_timeline.plot([], [], 'o-', color='#ff6600', linewidth=2)
        self.critical_points = []
        
        # 添加阶段标记
        self.phase_markers = []
    
    def add_controls(self):
        # 为策略选择添加按钮
        strategy_ax = plt.axes([0.75, 0.85, 0.2, 0.05], facecolor='#2a2a2a')
        self.strategy_button = Button(strategy_ax, '更换策略', color='#005500', hovercolor='#008800')
        self.strategy_button.on_clicked(self.change_strategy)
        
        # 为地形选择添加单选按钮
        terrain_ax = plt.axes([0.75, 0.75, 0.2, 0.1], facecolor='#1a1a1a')
        self.terrain_radio = RadioButtons(terrain_ax, ('平原', '山地', '城池', '河川', '林地', '丘陵', '沙漠'), 
                                        active=0, activecolor='#e6b800')
        self.terrain_radio.on_clicked(self.change_terrain)
        
        # 添加兵力对比滑块
        force_ax = plt.axes([0.75, 0.65, 0.2, 0.03], facecolor='#1a1a1a')
        self.force_slider = Slider(force_ax, '兵力对比', 0.0, 1.0, valinit=self.force_ratio, 
                                  valstep=0.05, color='#0066cc')
        self.force_slider.on_changed(self.update_force)
        
        # 添加士气滑块
        morale_ax = plt.axes([0.75, 0.58, 0.2, 0.03], facecolor='#1a1a1a')
        self.morale_slider = Slider(morale_ax, '我军士气', 0.0, 1.0, valinit=self.morale, 
                                   valstep=0.05, color='#cc0000')
        self.morale_slider.on_changed(self.update_morale)
        
        # 添加奇袭效果滑块
        surprise_ax = plt.axes([0.75, 0.51, 0.2, 0.03], facecolor='#1a1a1a')
        self.surprise_slider = Slider(surprise_ax, '奇袭效果', 0.0, 1.0, valinit=self.surprise, 
                                     valstep=0.05, color='#00cc00')
        self.surprise_slider.on_changed(self.update_surprise)
        
        # 添加部队素质滑块
        quality_ax = plt.axes([0.75, 0.44, 0.2, 0.03], facecolor='#1a1a1a')
        self.quality_slider = Slider(quality_ax, '部队素质', 0.0, 1.0, valinit=self.troop_quality, 
                                   valstep=0.05, color='#cc00cc')
        self.quality_slider.on_changed(self.update_quality)
        
        # 添加后勤滑块
        supply_ax = plt.axes([0.75, 0.37, 0.2, 0.03], facecolor='#1a1a1a')
        self.supply_slider = Slider(supply_ax, '后勤保障', 0.0, 1.0, valinit=self.supply_lines, 
                                   valstep=0.05, color='#00cccc')
        self.supply_slider.on_changed(self.update_supply)
        
        # 天气选择
        weather_ax = plt.axes([0.75, 0.28, 0.2, 0.05], facecolor='#1a1a1a')
        self.weather_radio = RadioButtons(weather_ax, ('晴朗', '雨天', '大风', '浓雾', '大雪', '沙暴'), 
                                        active=0, activecolor='#e6b800')
        self.weather_radio.on_clicked(self.change_weather)
        
        # 时间选择
        time_ax = plt.axes([0.75, 0.20, 0.2, 0.05], facecolor='#1a1a1a')
        self.time_radio = RadioButtons(time_ax, ('白天', '夜晚', '黎明', '黄昏'), 
                                     active=0, activecolor='#e6b800')
        self.time_radio.on_clicked(self.change_time)
        
        # 添加模拟按钮
        simulate_ax = plt.axes([0.75, 0.10, 0.09, 0.05], facecolor='#2a2a2a')
        self.simulate_button = Button(simulate_ax, '模拟战役', color='#aa0000', hovercolor='#ff0000')
        self.simulate_button.on_clicked(self.simulate_battle)
        
        # 添加动态模拟按钮
        animate_ax = plt.axes([0.86, 0.10, 0.09, 0.05], facecolor='#2a2a2a')
        self.animate_button = Button(animate_ax, '动态模拟', color='#00aa00', hovercolor='#00ff00')
        self.animate_button.on_clicked(self.start_animation)
        
        # 添加历史记录按钮
        history_ax = plt.axes([0.75, 0.03, 0.09, 0.05], facecolor='#2a2a2a')
        self.history_button = Button(history_ax, '查看历史', color='#5555aa', hovercolor='#7777ff')
        self.history_button.on_clicked(self.show_history)
        
        # 添加历史战役按钮
        historical_ax = plt.axes([0.86, 0.03, 0.09, 0.05], facecolor='#2a2a2a')
        self.historical_button = Button(historical_ax, '历史战役', color='#aa55aa', hovercolor='#cc77cc')
        self.historical_button.on_clicked(self.show_historical_battles)
    
    def change_strategy(self, event):
        strategies = [
            "以正合，以奇胜",
            "攻其无备",
            "以逸待劳",
            "声东击西",
            "围魏救赵",
            "擒贼擒王",
            "十面埋伏",
            "火攻",
            "水攻",
            "疑兵之计",
            "空城计",
            "连环计"
        ]
        current_idx = strategies.index(self.strategy)
        self.strategy = strategies[(current_idx + 1) % len(strategies)]
        self.update_strategy_display()
    
    def change_terrain(self, label):
        self.terrain = label
        self.simulate_battle()
    
    def change_weather(self, label):
        self.weather = label
        self.simulate_battle()
    
    def change_time(self, label):
        self.time_of_day = label
        self.simulate_battle()
    
    def update_force(self, val):
        self.force_ratio = val
    
    def update_morale(self, val):
        self.morale = val
    
    def update_surprise(self, val):
        self.surprise = val
    
    def update_quality(self, val):
        self.troop_quality = val
    
    def update_supply(self, val):
        self.supply_lines = val
    
    def update_strategy_display(self):
        self.ax_strategy.clear()
        self.setup_strategy_axis()
        
        strategies = [
            "以正合，以奇胜 - 正兵迎敌，奇兵取胜",
            "攻其无备 - 攻击敌人没有防备的地方",
            "以逸待劳 - 以我方的安逸对待敌人的疲劳",
            "声东击西 - 佯攻东面，实击西面",
            "围魏救赵 - 攻击敌人要害以解围",
            "擒贼擒王 - 直接攻击敌人首领",
            "十面埋伏 - 设置多重埋伏圈",
            "火攻 - 利用火势攻击敌军",
            "水攻 - 利用水势攻击敌军",
            "疑兵之计 - 制造假象迷惑敌军",
            "空城计 - 虚张声势迷惑敌军",
            "连环计 - 多计并用环环相扣"
        ]
        
        current_strat_idx = [
            "以正合，以奇胜",
            "攻其无备",
            "以逸待劳",
            "声东击西",
            "围魏救赵",
            "擒贼擒王",
            "十面埋伏",
            "火攻",
            "水攻",
            "疑兵之计",
            "空城计",
            "连环计"
        ].index(self.strategy)
        
        for i, s in enumerate(strategies):
            color = '#aaffaa' if i == current_strat_idx else '#55aa55'
            weight = 'bold' if i == current_strat_idx else 'normal'
            self.ax_strategy.text(0.05, 0.90 - i*0.08, s, 
                                 fontsize=10, color=color, ha='left', va='center',
                                 fontweight=weight, transform=self.ax_strategy.transAxes)
        
        self.fig.canvas.draw_idle()
    
    def train_ai_model(self):
        # 生成训练数据
        np.random.seed(42)
        n_samples = 2000  # 增加样本量
        strategies = ["以正合，以奇胜", "攻其无备", "以逸待劳", "声东击西", "围魏救赵", 
                     "擒贼擒王", "十面埋伏", "火攻", "水攻", "疑兵之计", "空城计", "连环计"]
        terrains = ["平原", "山地", "城池", "河川", "林地", "丘陵", "沙漠"]
        weathers = ["晴朗", "雨天", "大风", "浓雾", "大雪", "沙暴"]
        times = ["白天", "夜晚", "黎明", "黄昏"]
        
        data = {
            'strategy': np.random.choice(strategies, n_samples),
            'terrain': np.random.choice(terrains, n_samples),
            'force_ratio': np.random.uniform(0.1, 0.9, n_samples),
            'morale': np.random.uniform(0.3, 0.9, n_samples),
            'surprise': np.random.uniform(0.1, 0.9, n_samples),
            'weather': np.random.choice(weathers, n_samples),
            'time_of_day': np.random.choice(times, n_samples),
            'troop_quality': np.random.uniform(0.4, 0.95, n_samples),
            'supply_lines': np.random.uniform(0.5, 1.0, n_samples)
        }
        
        # 计算胜率（简化模型）
        def calculate_victory_chance(row):
            base = 0.5
            
            # 策略影响
            strategy_impact = {
                "以正合，以奇胜": 0.75,
                "攻其无备": 0.85,
                "以逸待劳": 0.65,
                "声东击西": 0.80,
                "围魏救赵": 0.70,
                "擒贼擒王": 0.95,
                "十面埋伏": 0.90,
                "火攻": 0.80,
                "水攻": 0.75,
                "疑兵之计": 0.70,
                "空城计": 0.60,
                "连环计": 0.85
            }[row['strategy']]
            
            # 地形影响
            terrain_impact = {
                "平原": 0.65,
                "山地": 0.75,
                "城池": 0.55,
                "河川": 0.70,
                "林地": 0.80,
                "丘陵": 0.70,
                "沙漠": 0.50
            }[row['terrain']]
            
            # 天气影响
            weather_impact = {
                "晴朗": 1.0,
                "雨天": 0.75,
                "大风": 0.65,
                "浓雾": 0.55,
                "大雪": 0.45,
                "沙暴": 0.40
            }[row['weather']]
            
            # 时间影响
            time_impact = {
                "白天": 1.0,
                "夜晚": 0.65,
                "黎明": 0.85,
                "黄昏": 0.75
            }[row['time_of_day']]
            
            victory_chance = base
            victory_chance += (row['force_ratio'] - 0.5) * 0.4
            victory_chance += (row['morale'] - 0.5) * 0.35
            victory_chance += (row['surprise'] - 0.5) * 0.55
            victory_chance *= strategy_impact
            victory_chance *= terrain_impact
            victory_chance *= weather_impact
            victory_chance *= time_impact
            victory_chance *= row['troop_quality']
            victory_chance *= row['supply_lines']
            
            return max(0.05, min(0.98, victory_chance))  # 确保胜率在合理范围内
        
        # 创建DataFrame
        df = pd.DataFrame(data)
        df['victory_chance'] = df.apply(calculate_victory_chance, axis=1)
        df['victory'] = df['victory_chance'].apply(lambda x: 1 if x > 0.5 else 0)
        
        # 特征编码
        df_encoded = pd.get_dummies(df, columns=['strategy', 'terrain', 'weather', 'time_of_day'])
        
        # 划分训练集和测试集
        X = df_encoded.drop(['victory_chance', 'victory'], axis=1)
        y = df_encoded['victory']
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # 训练随机森林模型
        ai_model = RandomForestClassifier(n_estimators=150, random_state=42, class_weight='balanced')
        ai_model.fit(X_train, y_train)
        
        # 评估模型
        accuracy = ai_model.score(X_test, y_test)
        print(f"AI模型训练完成，准确率: {accuracy:.2f}")
        
        return ai_model
    
    def get_ai_advice(self):
        # 准备输入数据
        input_data = {
            'strategy': [self.strategy],
            'terrain': [self.terrain],
            'force_ratio': [self.force_ratio],
            'morale': [self.morale],
            'surprise': [self.surprise],
            'weather': [self.weather],
            'time_of_day': [self.time_of_day],
            'troop_quality': [self.troop_quality],
            'supply_lines': [self.supply_lines]
        }
        
        df = pd.DataFrame(input_data)
        df_encoded = pd.get_dummies(df)
        
        # 确保所有训练时的列都存在
        train_columns = self.ai_model.feature_names_in_
        for col in train_columns:
            if col not in df_encoded.columns:
                df_encoded[col] = 0
        df_encoded = df_encoded[train_columns]
        
        # 预测胜率
        proba = self.ai_model.predict_proba(df_encoded)
        
        # 修复：处理单类别情况
        if len(proba[0]) == 2:
            victory_prob = proba[0][1]  # 胜利的概率
        else:
            # 如果只有一个类别，检查是胜利还是失败
            if self.ai_model.classes_[0] == 1:
                victory_prob = 1.0
            else:
                victory_prob = 0.0
        
        # 生成建议
        if victory_prob > 0.8:
            advice = "绝对优势！建议立即执行当前策略"
            reasoning = "当前策略与战场条件完美匹配，胜算极高"
        elif victory_prob > 0.7:
            advice = "高胜算！建议立即执行当前策略"
            reasoning = "当前策略与战场条件高度匹配，优势明显"
        elif victory_prob > 0.6:
            advice = "优势明显！建议按计划推进"
            reasoning = "当前策略可行，具有明显优势"
        elif victory_prob > 0.55:
            advice = "略有优势！建议微调战术"
            reasoning = "当前策略可行，但可优化兵力部署以扩大优势"
        elif victory_prob > 0.45:
            advice = "势均力敌！建议调整策略"
            reasoning = "战局胶着，考虑改变战术或等待有利时机"
        elif victory_prob > 0.3:
            advice = "劣势明显！建议撤退或改变策略"
            reasoning = "当前策略与战场条件不匹配，风险过高"
        else:
            advice = "极度危险！建议立即撤退"
            reasoning = "当前策略完全不适合战场条件，继续作战将导致惨败"
        
        # 根据参数提供具体建议
        if self.force_ratio < 0.4:
            reasoning += "。兵力不足，建议采用奇袭或伏击战术。"
        if self.morale < 0.5:
            reasoning += "。士气低落，建议鼓舞士气或进行休整。"
        if self.surprise > 0.7:
            reasoning += "。奇袭效果显著，可充分利用这一优势。"
        if self.weather in ["浓雾", "大雪", "沙暴"]:
            reasoning += f"。{self.weather}天气下，建议谨慎行动。"
        if self.time_of_day == "夜晚":
            reasoning += "。夜间作战需要特别注意部队协调。"
        
        # 添加策略特定建议
        if "火" in self.strategy:
            reasoning += "。火攻需要特别注意风向和易燃物分布。"
        if "水" in self.strategy:
            reasoning += "。水攻需确保我方部队位于高地。"
        if "奇" in self.strategy:
            reasoning += "。奇兵需要隐蔽行动和精确的时机把握。"
        
        return advice, victory_prob, reasoning
    
    def update_ai_display(self):
        advice, confidence, reasoning = self.get_ai_advice()
        self.ai_advice = advice
        self.ai_confidence = confidence
        self.ai_reasoning = reasoning
        
        self.ai_advice_text.set_text(f"建议: {advice}")
        self.ai_confidence_text.set_text(f"胜率预测: {confidence*100:.1f}%")
        self.ai_reasoning_text.set_text(f"分析: {reasoning}")
        
        # 根据置信度设置颜色
        if confidence > 0.7:
            color = '#00ff00'
        elif confidence > 0.6:
            color = '#aaff00'
        elif confidence > 0.55:
            color = '#ffff00'
        elif confidence > 0.45:
            color = '#ff9900'
        else:
            color = '#ff0000'
        
        self.ai_confidence_text.set_color(color)
        self.fig.canvas.draw_idle()
    
    def simulate_battle(self, event=None):
        # 基于策略和参数计算战斗结果
        base_score = 0.5
        
        # 策略影响
        strategy_impact = {
            "以正合，以奇胜": 0.75,
            "攻其无备": 0.85,
            "以逸待劳": 0.65,
            "声东击西": 0.80,
            "围魏救赵": 0.70,
            "擒贼擒王": 0.95,
            "十面埋伏": 0.90,
            "火攻": 0.80,
            "水攻": 0.75,
            "疑兵之计": 0.70,
            "空城计": 0.60,
            "连环计": 0.85
        }[self.strategy]
        
        # 地形影响
        terrain_impact = {
            "平原": 0.65,
            "山地": 0.75,
            "城池": 0.55,
            "河川": 0.70,
            "林地": 0.80,
            "丘陵": 0.70,
            "沙漠": 0.50
        }[self.terrain]
        
        # 天气影响
        weather_impact = {
            "晴朗": 1.0,
            "雨天": 0.75,
            "大风": 0.65,
            "浓雾": 0.55,
            "大雪": 0.45,
            "沙暴": 0.40
        }[self.weather]
        
        # 时间影响
        time_impact = {
            "白天": 1.0,
            "夜晚": 0.65,
            "黎明": 0.85,
            "黄昏": 0.75
        }[self.time_of_day]
        
        # 计算胜率
        victory_chance = base_score
        victory_chance += (self.force_ratio - 0.5) * 0.4
        victory_chance += (self.morale - 0.5) * 0.35
        victory_chance += (self.surprise - 0.5) * 0.55
        victory_chance *= strategy_impact
        victory_chance *= terrain_impact
        victory_chance *= weather_impact
        victory_chance *= time_impact
        victory_chance *= self.troop_quality
        victory_chance *= self.supply_lines
        
        # 确保胜率在0-1之间
        victory_chance = max(0.05, min(0.95, victory_chance))
        self.victory_chance = victory_chance
        
        # 随机决定胜负（基于胜率）
        victory = np.random.random() < victory_chance
        
        # 确定结果描述
        if victory:
            outcomes = [
                "大获全胜！敌军溃不成军",
                "战略胜利！敌军被迫撤退",
                "战术胜利！我军占据优势",
                "巧妙取胜！敌军指挥系统瘫痪",
                "不战而胜！敌军士气崩溃投降",
                "完美实施！敌军被完全包围歼灭",
                "以少胜多！成为经典战役范例"
            ]
            self.outcome = np.random.choice(outcomes)
        else:
            outcomes = [
                "战略失误！我军陷入包围",
                "情报错误！我军中伏损失惨重",
                "指挥失利！阵型被敌军突破",
                "后勤不足！被迫撤退",
                "敌援军至！我军攻势受阻",
                "天气突变！作战计划被打乱",
                "内部叛乱！导致战线崩溃"
            ]
            self.outcome = np.random.choice(outcomes)
        
        # 更新雷达图
        self.values = [
            self.force_ratio,
            self.morale,
            self.surprise,
            terrain_impact,
            weather_impact,
            time_impact,
            self.troop_quality,
            self.supply_lines
        ]
        
        angles = np.linspace(0, 2*np.pi, len(self.categories), endpoint=False).tolist()
        values = self.values + [self.values[0]]
        angles += angles[:1]
        
        # 更新雷达图数据
        self.radar_line.set_data(angles, values)
        
        # 更新填充区域（先移除旧的填充）
        for fill in self.radar_fill:
            fill.remove()
        self.radar_fill = self.ax_results.fill(angles, values, alpha=0.25, color='#ff6600')
        
        # 更新结果文本
        result_color = '#00ff00' if victory else '#ff0000'
        result_text = f"战果: {self.outcome}\n胜率: {victory_chance*100:.1f}%"
        self.result_text.set_text(result_text)
        self.result_text.set_color(result_color)
        
        # 随机选择一条孙子兵法引言
        self.current_quote = np.random.choice(self.sun_tzu_quotes)
        self.quote_text.set_text(f"《孙子兵法》:\n\n{self.current_quote}")
        
        # 更新战场态势图
        self.update_battle_map(victory)
        
        # 更新AI分析
        self.update_ai_display()
        
        # 记录历史
        self.history.append({
            'strategy': self.strategy,
            'terrain': self.terrain,
            'force_ratio': self.force_ratio,
            'morale': self.morale,
            'surprise': self.surprise,
            'weather': self.weather,
            'time_of_day': self.time_of_day,
            'troop_quality': self.troop_quality,
            'supply_lines': self.supply_lines,
            'victory': victory,
            'victory_chance': victory_chance,
            'outcome': self.outcome
        })
        
        self.fig.canvas.draw_idle()
    
    def update_battle_map(self, victory):
        self.ax_map.clear()
        self.setup_map_axis()
        
        # 绘制地形
        if self.terrain == "平原":
            self.ax_map.add_patch(patches.Rectangle((0, 0), 10, 10, color='#2a5a2a', alpha=0.3))
            self.ax_map.text(5, 5, '平原地形', fontsize=20, color='#aaaaaa', 
                           ha='center', va='center', alpha=0.5)
        elif self.terrain == "山地":
            self.ax_map.add_patch(patches.Rectangle((0, 0), 10, 10, color='#5a3a1a', alpha=0.3))
            # 绘制山脉
            for x, y in [(2, 6), (4, 7), (6, 5), (8, 8)]:
                self.ax_map.plot([x, x+1, x+0.5], [y, y, y+1], color='#7a5a3a', lw=2)
            self.ax_map.text(5, 5, '山地地形', fontsize=20, color='#aaaaaa', 
                           ha='center', va='center', alpha=0.5)
        elif self.terrain == "城池":
            self.ax_map.add_patch(patches.Rectangle((0, 0), 10, 10, color='#5a5a7a', alpha=0.3))
            # 绘制城墙
            self.ax_map.add_patch(patches.Rectangle((3, 3), 4, 4, fill=False, 
                                              ec='#aaaaaa', lw=2, ls='-'))
            self.ax_map.text(5, 5, '城池攻防', fontsize=20, color='#aaaaaa', 
                           ha='center', va='center', alpha=0.5)
        elif self.terrain == "河川":
            self.ax_map.add_patch(patches.Rectangle((0, 0), 10, 10, color='#1a3a7a', alpha=0.3))
            # 绘制河流
            self.ax_map.plot([1, 3, 5, 7, 9], [9, 5, 7, 3, 8], color='#3a7aaa', lw=4, alpha=0.6)
            self.ax_map.text(5, 5, '河川地形', fontsize=20, color='#aaaaaa', 
                           ha='center', va='center', alpha=0.5)
        elif self.terrain == "林地":
            self.ax_map.add_patch(patches.Rectangle((0, 0), 10, 10, color='#1a5a1a', alpha=0.3))
            # 绘制树木
            for x, y in [(1, 1), (3, 2), (5, 1), (7, 3), (2, 7), (4, 8), (6, 6), (8, 7)]:
                self.ax_map.plot([x, x], [y, y+1], color='#3a5a1a', lw=3)
                self.ax_map.scatter(x, y+1.5, s=100, color='#2a7a2a', alpha=0.7)
            self.ax_map.text(5, 5, '林地地形', fontsize=20, color='#aaaaaa', 
                           ha='center', va='center', alpha=0.5)
        elif self.terrain == "丘陵":
            self.ax_map.add_patch(patches.Rectangle((0, 0), 10, 10, color='#5a4a2a', alpha=0.3))
            # 绘制丘陵
            for x, y in [(2, 3), (4, 5), (6, 4), (8, 6)]:
                self.ax_map.add_patch(patches.Ellipse((x, y), width=2, height=1, 
                                                color='#7a6a4a', alpha=0.6))
            self.ax_map.text(5, 5, '丘陵地形', fontsize=20, color='#aaaaaa', 
                           ha='center', va='center', alpha=0.5)
        else:  # 沙漠
            self.ax_map.add_patch(patches.Rectangle((0, 0), 10, 10, color='#e6b800', alpha=0.2))
            # 绘制沙丘
            for x, y in [(3, 4), (6, 5), (2, 7), (7, 3)]:
                self.ax_map.add_patch(patches.Ellipse((x, y), width=1.5, height=0.8, 
                                                color='#d0a040', alpha=0.7))
            self.ax_map.text(5, 5, '沙漠地形', fontsize=20, color='#aaaaaa', 
                           ha='center', va='center', alpha=0.5)
        
        # 绘制我军和敌军
        if victory:
            # 胜利布局
            self.ax_map.scatter([2, 2.5, 3, 2.5], [7, 7.5, 7, 6.5], s=100, color='red', marker='o')
            self.ax_map.text(2.5, 7.8, '我军主力', color='red', fontsize=10, ha='center')
            
            # 奇兵位置取决于策略
            if "奇" in self.strategy:
                self.ax_map.scatter([7.5], [3.5], s=150, color='red', marker='*')
                self.ax_map.text(7.5, 4.0, '奇兵部队', color='red', fontsize=10, ha='center')
            
            # 敌军败退
            self.ax_map.scatter([6, 7, 8, 7], [3, 2.5, 3, 3.5], s=80, color='blue', marker='x')
            self.ax_map.text(7, 1.8, '溃败敌军', color='blue', fontsize=10, ha='center')
            
            # 胜利箭头
            self.ax_map.arrow(3, 6.5, 2, -2, head_width=0.3, head_length=0.5, fc='red', ec='red')
            if "奇" in self.strategy:
                self.ax_map.arrow(7.5, 3, -1, 1, head_width=0.3, head_length=0.5, fc='red', ec='red')
            
            # 胜利文本
            self.ax_map.text(5, 8.5, f"《孙子兵法》策略: {self.strategy}", 
                            fontsize=14, color='red', ha='center')
            self.ax_map.text(5, 0.8, f"结果: {self.outcome}", 
                            fontsize=14, color='red', ha='center')
        else:
            # 失败布局
            self.ax_map.scatter([3, 4, 5], [6, 7, 6], s=100, color='red', marker='o')
            self.ax_map.text(4, 7.5, '我军主力', color='red', fontsize=10, ha='center')
            
            # 敌军包围
            self.ax_map.scatter([2, 3, 4, 5, 6, 7], [4, 3, 4, 3, 4, 3], s=80, color='blue', marker='o')
            self.ax_map.text(4.5, 2.5, '敌军包围', color='blue', fontsize=10, ha='center')
            
            # 失败箭头
            self.ax_map.arrow(4, 6, 0, -1, head_width=0.3, head_length=0.5, fc='blue', ec='blue')
            self.ax_map.arrow(5, 6, 1, -1, head_width=0.3, head_length=0.5, fc='blue', ec='blue')
            self.ax_map.arrow(3, 6, -1, -1, head_width=0.3, head_length=0.5, fc='blue', ec='blue')
            
            # 失败文本
            self.ax_map.text(5, 8.5, f"《孙子兵法》策略: {self.strategy}", 
                            fontsize=14, color='yellow', ha='center')
            self.ax_map.text(5, 0.8, f"结果: {self.outcome}", 
                            fontsize=14, color='yellow', ha='center')
        
        # 添加战术标记
        if self.strategy == "声东击西":
            self.ax_map.text(1, 1, '佯攻部队', color='#ff6666', fontsize=10)
            self.ax_map.arrow(1.5, 1.5, 1, 1, head_width=0.2, head_length=0.3, fc='#ff6666', ec='#ff6666')
            self.ax_map.text(8, 8, '主攻方向', color='#66ff66', fontsize=10)
        
        elif self.strategy == "十面埋伏":
            for angle in np.linspace(0, 2*np.pi, 8, endpoint=False):
                x, y = 5 + 3*np.cos(angle), 5 + 3*np.sin(angle)
                self.ax_map.scatter(x, y, s=30, color='#ff6600', marker='^')
                self.ax_map.text(x, y-0.5, '伏兵', color='#ff6600', fontsize=8, ha='center')
        
        elif self.strategy == "围魏救赵":
            self.ax_map.text(8, 8, '围魏', color='#ff6600', fontsize=12, ha='center')
            self.ax_map.text(3, 3, '救赵', color='#66ff66', fontsize=12, ha='center')
            self.ax_map.plot([8, 3], [8, 3], '--', color='#66ff66', lw=1, alpha=0.7)
        
        elif self.strategy == "火攻":
            self.ax_map.text(7, 7, '火攻部队', color='#ff3300', fontsize=12, ha='center')
            for i in range(5):
                x, y = 6 + np.random.rand(), 6 + np.random.rand()
                self.ax_map.scatter(x, y, s=50, color='#ff3300', marker='*')
        
        elif self.strategy == "水攻":
            self.ax_map.text(7, 7, '水攻部队', color='#3366ff', fontsize=12, ha='center')
            self.ax_map.plot([6, 8], [6, 8], color='#3366ff', lw=2, alpha=0.7)
        
        # 添加天气标记
        if self.weather == "雨天":
            for i in range(20):
                x, y = np.random.uniform(0, 10), np.random.uniform(0, 10)
                self.ax_map.plot([x, x], [y, y-0.3], color='#66ccff', lw=1, alpha=0.5)
            self.ax_map.text(9, 9, '雨天', color='#66ccff', fontsize=10, ha='right')
        
        elif self.weather == "大风":
            self.ax_map.text(9, 9, '大风', color='#cccccc', fontsize=10, ha='right')
            for i in range(10):
                x, y = np.random.uniform(0, 10), np.random.uniform(0, 10)
                self.ax_map.arrow(x, y, 0.5, 0, head_width=0.1, head_length=0.2, fc='#cccccc', ec='#cccccc', alpha=0.7)
        
        elif self.weather == "浓雾":
            self.ax_map.add_patch(patches.Rectangle((0, 0), 10, 10, color='#dddddd', alpha=0.3))
            self.ax_map.text(9, 9, '浓雾', color='#ffffff', fontsize=10, ha='right')
        
        elif self.weather == "大雪":
            self.ax_map.add_patch(patches.Rectangle((0, 0), 10, 10, color='#ffffff', alpha=0.2))
            for i in range(30):
                x, y = np.random.uniform(0, 10), np.random.uniform(0, 10)
                self.ax_map.scatter(x, y, s=10, color='white', alpha=0.7)
            self.ax_map.text(9, 9, '大雪', color='#ffffff', fontsize=10, ha='right')
        
        elif self.weather == "沙暴":
            self.ax_map.add_patch(patches.Rectangle((0, 0), 10, 10, color='#d0a040', alpha=0.3))
            for i in range(20):
                x, y = np.random.uniform(0, 10), np.random.uniform(0, 10)
                self.ax_map.arrow(x, y, 0.7, 0, head_width=0.2, head_length=0.3, fc='#d0a040', ec='#d0a040', alpha=0.5)
            self.ax_map.text(9, 9, '沙暴', color='#d0a040', fontsize=10, ha='right')
        
        # 添加时间标记
        if self.time_of_day == "夜晚":
            self.ax_map.add_patch(patches.Rectangle((0, 0), 10, 10, color='#000033', alpha=0.4))
            self.ax_map.text(9, 9, '夜晚', color='#ffff00', fontsize=10, ha='right')
            for i in range(20):
                x, y = np.random.uniform(0, 10), np.random.uniform(0, 10)
                self.ax_map.scatter(x, y, s=3, color='white', alpha=0.7)
        
        elif self.time_of_day == "黎明":
            self.ax_map.add_patch(patches.Rectangle((0, 0), 10, 10, color='#ffcc66', alpha=0.2))
            self.ax_map.text(9, 9, '黎明', color='#ff9900', fontsize=10, ha='right')
        
        elif self.time_of_day == "黄昏":
            self.ax_map.add_patch(patches.Rectangle((0, 0), 10, 10, color='#cc6600', alpha=0.2))
            self.ax_map.text(9, 9, '黄昏', color='#ff6600', fontsize=10, ha='right')
    
    def start_animation(self, event):
        if self.animation is not None:
            self.animation.event_source.stop()
        
        self.battle_active = True
        self.turn = 0
        self.time_data = []
        self.advantage_data = []
        self.critical_points = []
        self.phase_markers = []
        self.battle_phase = "准备阶段"
        
        # 清除时间线
        self.ax_timeline.clear()
        self.setup_timeline_axis()
        
        # 开始动画
        self.animation = FuncAnimation(self.fig, self.animate_battle, frames=self.max_turns, 
                                      interval=500, blit=False)
        plt.draw()
    
    def animate_battle(self, frame):
        self.turn = frame
        phase_changed = False
        
        # 根据回合数改变战斗阶段
        if frame < 5:
            new_phase = "准备阶段"
        elif frame < 10:
            new_phase = "接触阶段"
        elif frame < 15:
            new_phase = "决战阶段"
        else:
            new_phase = "收尾阶段"
        
        if new_phase != self.battle_phase:
            self.battle_phase = new_phase
            phase_changed = True
        
        # 模拟战场动态变化
        time_factor = frame / self.max_turns
        
        # 计算当前优势（基于初始参数和回合数）
        advantage = self.victory_chance * (1 - 0.1 * time_factor)  # 优势随时间递减
        advantage += np.random.normal(0, 0.05)  # 随机波动
        
        # 策略在特定阶段效果增强
        if "奇" in self.strategy and frame > 7 and frame < 12:
            advantage += 0.15
            if phase_changed:
                self.critical_points.append((frame, advantage, "奇兵出击!"))
        
        if "火" in self.strategy and frame > 5 and frame < 8:
            advantage += 0.2
            if phase_changed:
                self.critical_points.append((frame, advantage, "火攻生效!"))
        
        # 随机事件
        if frame > 3 and np.random.rand() < 0.2:
            event_type = np.random.choice(['增援', '士气', '天气', '情报', '补给'])
            if event_type == '增援':
                advantage += 0.1
                self.critical_points.append((frame, advantage, "援军到达!"))
            elif event_type == '士气':
                change = np.random.choice([0.15, -0.15])
                if change > 0:
                    self.critical_points.append((frame, advantage, "士气高涨!"))
                else:
                    self.critical_points.append((frame, advantage, "士气低落!"))
                advantage += change
            elif event_type == '天气':
                new_weather = np.random.choice(['晴朗', '雨天', '大风', '浓雾', '大雪'])
                if new_weather != self.weather:
                    self.weather = new_weather
                    self.critical_points.append((frame, advantage, f"天气突变: {self.weather}"))
                    if self.weather in ['浓雾', '大雪']:
                        advantage -= 0.1
            elif event_type == '情报':
                advantage += 0.1
                self.critical_points.append((frame, advantage, "获取敌军情报!"))
            elif event_type == '补给':
                advantage += 0.05
                self.critical_points.append((frame, advantage, "补给到达!"))
        
        # 记录数据
        self.time_data.append(frame)
        self.advantage_data.append(advantage)
        
        # 更新热力图
        self.update_heatmap(frame)
        
        # 更新时间线
        self.timeline.set_data(self.time_data, self.advantage_data)
        
        # 添加阶段标记
        if phase_changed:
            marker = self.ax_timeline.axvline(x=frame, color='#66ccff', linestyle='--', alpha=0.7)
            self.phase_markers.append(marker)
            self.ax_timeline.text(frame, 0.05, self.battle_phase, color='#66ccff', 
                                ha='center', va='bottom', fontsize=10, rotation=90)
        
        # 添加关键点标记
        for point in self.critical_points:
            if point[0] == frame:
                self.ax_timeline.annotate(point[2], xy=(point[0], point[1]), 
                                        xytext=(point[0], point[1] + 0.1),
                                        arrowprops=dict(facecolor='red', shrink=0.05),
                                        fontsize=10, color='red')
        
        # 更新战场地图标题
        self.ax_map.set_title(f'动态战场态势图 - 回合: {frame+1}/{self.max_turns} - 阶段: {self.battle_phase}', 
                            fontsize=18, color='white')
        
        # 最后一回合显示结果
        if frame == self.max_turns - 1:
            victory = advantage > 0.5
            if victory:
                outcomes = [
                    "经过激烈战斗，我军取得最终胜利！",
                    "敌军全线溃败，我军大获全胜！",
                    "战术完美执行，敌军投降！"
                ]
                self.outcome = np.random.choice(outcomes)
                result_color = '#00ff00'
            else:
                outcomes = [
                    "经过激烈战斗，我军未能突破敌军防线！",
                    "战局逆转，我军被迫撤退！",
                    "损失惨重，我军战败！"
                ]
                self.outcome = np.random.choice(outcomes)
                result_color = '#ff0000'
            
            self.ax_map.text(5, 0.8, f"结果: {self.outcome}", 
                            fontsize=14, color=result_color, ha='center')
        
        return self.timeline,
    
    def update_heatmap(self, frame):
        # 根据战斗阶段更新热力图
        self.heatmap_data = np.zeros((10, 10))
        
        # 基础分布
        for i in range(10):
            for j in range(10):
                dist_to_center = np.sqrt((i-5)**2 + (j-5)**2)
                value = max(0, 1 - dist_to_center / 7)
                self.heatmap_data[i, j] = value
        
        # 随时间变化的战斗热点
        time_factor = frame / self.max_turns
        
        # 添加随机战斗热点
        for _ in range(5 + int(frame * 0.5)):
            x, y = np.random.randint(2, 8, 2)
            intensity = np.random.uniform(0.5, 1.0) * (1 + time_factor)
            radius = np.random.uniform(1.0, 3.0)
            
            for i in range(10):
                for j in range(10):
                    dist = np.sqrt((i-x)**2 + (j-y)**2)
                    if dist < radius:
                        self.heatmap_data[i, j] += intensity * max(0, 1 - dist/radius)
        
        # 根据策略添加特定热点
        if "奇" in self.strategy and frame > 7:
            # 奇兵从侧翼进攻
            for i in range(3, 7):
                for j in range(7, 10):
                    dist = np.sqrt((i-5)**2 + (j-8.5)**2)
                    self.heatmap_data[i, j] += 0.8 * max(0, 1 - dist/3)
        
        if "火" in self.strategy and frame > 5 and frame < 10:
            # 火攻区域
            for i in range(4, 7):
                for j in range(4, 7):
                    dist = np.sqrt((i-5.5)**2 + (j-5.5)**2)
                    self.heatmap_data[i, j] += 1.0 * max(0, 1 - dist/2)
        
        # 更新热力图
        self.heatmap.set_array(self.heatmap_data)
    
    def show_history(self, event):
        # 创建历史记录窗口
        if not self.history:
            return
            
        history_fig = plt.figure(figsize=(12, 8), facecolor='#1a1a1a')
        history_fig.suptitle('战役历史记录', fontsize=20, color='#e6b800')
        
        # 创建子图
        ax = plt.subplot(111, facecolor='#0a0a1a')
        ax.set_title('历史战役结果', fontsize=16, color='white')
        ax.set_xlabel('战役序号', color='white')
        ax.set_ylabel('胜率(%)', color='white')
        ax.tick_params(colors='white')
        ax.grid(True, color='#333333', linestyle='--')
        
        # 准备数据
        indices = range(1, len(self.history) + 1)
        victory_chances = [h['victory_chance'] * 100 for h in self.history]
        outcomes = [h['victory'] for h in self.history]
        colors = ['#00ff00' if v else '#ff0000' for v in outcomes]
        
        # 绘制条形图
        bars = ax.bar(indices, victory_chances, color=colors, edgecolor='white')
        
        # 添加标签
        for i, bar in enumerate(bars):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f"{self.history[i]['strategy']}\n{self.history[i]['outcome']}",
                    ha='center', va='bottom', fontsize=8, color='white')
        
        # 添加图例
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='#00ff00', edgecolor='white', label='胜利'),
            Patch(facecolor='#ff0000', edgecolor='white', label='失败')
        ]
        ax.legend(handles=legend_elements, loc='upper right', facecolor='#1a1a1a', edgecolor='white')
        
        plt.tight_layout()
        plt.show()
    
    def show_historical_battles(self, event):
        # 创建历史战役窗口
        hist_fig = plt.figure(figsize=(12, 8), facecolor='#1a1a1a')
        hist_fig.suptitle('著名历史战役', fontsize=24, color='#e6b800')
        
        # 创建子图
        ax = plt.subplot(111, facecolor='#0a0a1a')
        ax.set_title('《孙子兵法》经典战例分析', fontsize=18, color='white')
        ax.set_xticks([])
        ax.set_yticks([])
        
        # 显示历史战役信息
        y_pos = 0.9
        for battle, info in self.historical_battles.items():
            color = '#00ff00' if info['result'] == '胜利' else '#ff0000'
            text = f"{battle}: {info['strategy']} - 兵力对比: {info['force_ratio']*100:.0f}% - 结果: {info['result']}"
            ax.text(0.05, y_pos, text, fontsize=14, color=color, 
                   ha='left', va='center', transform=ax.transAxes)
            y_pos -= 0.1
            
            # 添加战役说明
            if battle == "赤壁之战":
                desc = "周瑜采用火攻，以少胜多击败曹操大军"
            elif battle == "巨鹿之战":
                desc = "项羽破釜沉舟，激发士气，大败秦军"
            elif battle == "淝水之战":
                desc = "谢玄采用疑兵之计，使前秦军队自乱阵脚"
            elif battle == "长平之战":
                desc = "白起采用围歼战术，歼灭赵军主力"
            elif battle == "官渡之战":
                desc = "曹操火烧乌巢粮草，击败袁绍"
            elif battle == "马拉松战役":
                desc = "雅典军队采用两翼包抄战术击败波斯大军"
            elif battle == "坎尼会战":
                desc = "汉尼拔采用双重包围战术歼灭罗马军团"
            elif battle == "滑铁卢战役":
                desc = "拿破仑在恶劣天气下战败，结束拿破仑时代"
            
            ax.text(0.1, y_pos, f"• {desc}", fontsize=12, color='#cccccc', 
                   ha='left', va='center', transform=ax.transAxes)
            y_pos -= 0.07
        
        # 添加孙子兵法引用
        ax.text(0.5, 0.1, "故善战者，致人而不致于人。", fontsize=16, color='#e6b800',
               ha='center', va='center', transform=ax.transAxes)
        ax.text(0.5, 0.05, "《孙子兵法·虚实篇》", fontsize=14, color='#cccccc',
               ha='center', va='center', transform=ax.transAxes)
        
        plt.tight_layout()
        plt.show()
    
    def show(self):
        plt.tight_layout()
        plt.show()

# 创建并运行模拟器
if __name__ == "__main__":
    simulator = SunTzuSimulatorPro()
    simulator.show()