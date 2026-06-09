import numpy as np
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import tkinter as tk
from tkinter import ttk
import time
from PIL import Image, ImageTk

# 易经64卦数据
hexagrams = {
    1: {"name": "䷀ 乾", "symbol": "111111", "meaning": "创造、刚健"},
    2: {"name": "䷁ 坤", "symbol": "000000", "meaning": "接受、柔顺"},
    3: {"name": "䷂ 屯", "symbol": "100010", "meaning": "初始困难"},
    4: {"name": "䷃ 蒙", "symbol": "010001", "meaning": "启蒙教育"},
    5: {"name": "䷄ 需", "symbol": "111010", "meaning": "等待时机"},
    6: {"name": "䷅ 讼", "symbol": "010111", "meaning": "争讼纠纷"},
    7: {"name": "䷆ 师", "symbol": "010000", "meaning": "统率军队"},
    8: {"name": "䷇ 比", "symbol": "000010", "meaning": "亲近依附"},
    9: {"name": "䷈ 小畜", "symbol": "111011", "meaning": "小有积蓄"},
    10: {"name": "䷉ 履", "symbol": "110111", "meaning": "谨慎行事"},
    11: {"name": "䷊ 泰", "symbol": "111000", "meaning": "天地交泰"},
    12: {"name": "䷋ 否", "symbol": "000111", "meaning": "闭塞不通"},
    13: {"name": "䷌ 同人", "symbol": "101111", "meaning": "志同道合"},
    14: {"name": "䷍ 大有", "symbol": "111101", "meaning": "大获所有"},
    15: {"name": "䷎ 谦", "symbol": "001000", "meaning": "谦虚谨慎"},
    16: {"name": "䷏ 豫", "symbol": "000100", "meaning": "愉悦安乐"},
    17: {"name": "䷐ 随", "symbol": "100110", "meaning": "随从适应"},
    18: {"name": "䷑ 蛊", "symbol": "011001", "meaning": "整治腐败"},
    19: {"name": "䷒ 临", "symbol": "110000", "meaning": "亲临督导"},
    20: {"name": "䷓ 观", "symbol": "000011", "meaning": "观察审视"},
    21: {"name": "䷔ 噬嗑", "symbol": "100101", "meaning": "排除障碍"},
    22: {"name": "䷕ 贲", "symbol": "101001", "meaning": "文饰美化"},
    23: {"name": "䷖ 剥", "symbol": "000001", "meaning": "剥落侵蚀"},
    24: {"name": "䷗ 复", "symbol": "100000", "meaning": "回复复兴"},
    25: {"name": "䷘ 无妄", "symbol": "100111", "meaning": "不妄为"},
    26: {"name": "䷙ 大畜", "symbol": "111001", "meaning": "大有积蓄"},
    27: {"name": "䷚ 颐", "symbol": "100001", "meaning": "颐养之道"},
    28: {"name": "䷛ 大过", "symbol": "011110", "meaning": "过度行动"},
    29: {"name": "䷜ 坎", "symbol": "010010", "meaning": "险难重重"},
    30: {"name": "䷝ 离", "symbol": "101101", "meaning": "光明美丽"},
    31: {"name": "䷞ 咸", "symbol": "001110", "meaning": "相互感应"},
    32: {"name": "䷟ 恒", "symbol": "011100", "meaning": "持之以恒"},
    33: {"name": "䷠ 遁", "symbol": "001111", "meaning": "退避隐遁"},
    34: {"name": "䷡ 大壮", "symbol": "111100", "meaning": "强盛壮大"},
    35: {"name": "䷢ 晋", "symbol": "000101", "meaning": "晋升发展"},
    36: {"name": "䷣ 明夷", "symbol": "101000", "meaning": "光明受损"},
    37: {"name": "䷤ 家人", "symbol": "101011", "meaning": "家庭伦理"},
    38: {"name": "䷥ 睽", "symbol": "110101", "meaning": "意见相左"},
    39: {"name": "䷦ 蹇", "symbol": "001010", "meaning": "艰难险阻"},
    40: {"name": "䷧ 解", "symbol": "010100", "meaning": "解除困难"},
    41: {"name": "䷨ 损", "symbol": "110001", "meaning": "减损之道"},
    42: {"name": "䷩ 益", "symbol": "100011", "meaning": "增益之道"},
    43: {"name": "䷪ 夬", "symbol": "111110", "meaning": "果断决策"},
    44: {"name": "䷫ 姤", "symbol": "011111", "meaning": "不期而遇"},
    45: {"name": "䷬ 萃", "symbol": "000110", "meaning": "聚集荟萃"},
    46: {"name": "䷭ 升", "symbol": "011000", "meaning": "上升发展"},
    47: {"name": "䷮ 困", "symbol": "010110", "meaning": "困顿受制"},
    48: {"name": "䷯ 井", "symbol": "011010", "meaning": "井养之道"},
    49: {"name": "䷰ 革", "symbol": "101110", "meaning": "变革创新"},
    50: {"name": "䷱ 鼎", "symbol": "011101", "meaning": "稳固更新"},
    51: {"name": "䷲ 震", "symbol": "100100", "meaning": "震动惊惧"},
    52: {"name": "䷳ 艮", "symbol": "001001", "meaning": "止于当止"},
    53: {"name": "䷴ 渐", "symbol": "001011", "meaning": "循序渐进"},
    54: {"name": "䷵ 归妹", "symbol": "110100", "meaning": "婚配归宿"},
    55: {"name": "䷶ 丰", "symbol": "101100", "meaning": "丰盛壮大"},
    56: {"name": "䷷ 旅", "symbol": "001101", "meaning": "旅行在外"},
    57: {"name": "䷸ 巽", "symbol": "011011", "meaning": "谦逊顺从"},
    58: {"name": "䷹ 兑", "symbol": "110110", "meaning": "喜悦沟通"},
    59: {"name": "䷺ 涣", "symbol": "010011", "meaning": "涣散分离"},
    60: {"name": "䷻ 节", "symbol": "110010", "meaning": "节制约束"},
    61: {"name": "䷼ 中孚", "symbol": "110011", "meaning": "诚信立身"},
    62: {"name": "䷽ 小过", "symbol": "001100", "meaning": "小有过越"},
    63: {"name": "䷾ 既济", "symbol": "101010", "meaning": "事已完成"},
    64: {"name": "䷿ 未济", "symbol": "010101", "meaning": "事未完成"}
}

class IChingSystem:
    def __init__(self, root):
        self.root = root
        self.root.title("易经卦象演化系统")
        self.root.geometry("1200x800")
        self.root.configure(bg="#f0f0f0")
        
        # 设置易经主题颜色
        self.colors = {
            "bg": "#f9f5e8",
            "dark": "#3d2b1f",
            "light": "#e6d3b3",
            "yang": "#e74c3c",
            "yin": "#3498db"
        }
        
        # 创建主框架
        self.main_frame = tk.Frame(root, bg=self.colors["bg"])
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 创建标题
        title_frame = tk.Frame(self.main_frame, bg=self.colors["bg"])
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.title_label = tk.Label(
            title_frame, 
            text="易经卦象演化系统", 
            font=("SimSun", 24, "bold"),
            fg=self.colors["dark"],
            bg=self.colors["bg"]
        )
        self.title_label.pack(side=tk.LEFT)
        
        self.subtitle_label = tk.Label(
            title_frame, 
            text="变易 · 简易 · 不易",
            font=("SimSun", 16),
            fg="#7d6608",
            bg=self.colors["bg"]
        )
        self.subtitle_label.pack(side=tk.RIGHT)
        
        # 创建控制面板
        control_frame = tk.LabelFrame(
            self.main_frame, 
            text="控制面板", 
            font=("SimSun", 12),
            bg=self.colors["bg"],
            fg=self.colors["dark"],
            padx=10,
            pady=10
        )
        control_frame.pack(fill=tk.X, pady=(0, 20))
        
        # 添加控制元素
        tk.Label(
            control_frame, 
            text="演化速度:", 
            bg=self.colors["bg"],
            font=("SimSun", 11)
        ).grid(row=0, column=0, padx=5, pady=5, sticky="e")
        
        self.speed_var = tk.DoubleVar(value=0.5)
        speed_scale = tk.Scale(
            control_frame, 
            from_=0.1, 
            to=2.0, 
            resolution=0.1,
            orient=tk.HORIZONTAL,
            variable=self.speed_var,
            length=200,
            bg=self.colors["bg"],
            highlightthickness=0,
            showvalue=True
        )
        speed_scale.grid(row=0, column=1, padx=5, pady=5)
        
        tk.Label(
            control_frame, 
            text="卦象复杂度:", 
            bg=self.colors["bg"],
            font=("SimSun", 11)
        ).grid(row=0, column=2, padx=5, pady=5, sticky="e")
        
        self.complexity_var = tk.IntVar(value=3)
        complexity_scale = tk.Scale(
            control_frame, 
            from_=1, 
            to=5, 
            orient=tk.HORIZONTAL,
            variable=self.complexity_var,
            length=200,
            bg=self.colors["bg"],
            highlightthickness=0,
            showvalue=True
        )
        complexity_scale.grid(row=0, column=3, padx=5, pady=5)
        
        self.start_button = tk.Button(
            control_frame, 
            text="开始演化", 
            command=self.start_evolution,
            bg="#2ecc71",
            fg="white",
            font=("SimSun", 11, "bold"),
            padx=10
        )
        self.start_button.grid(row=0, column=4, padx=20, pady=5)
        
        self.stop_button = tk.Button(
            control_frame, 
            text="停止", 
            command=self.stop_evolution,
            bg="#e74c3c",
            fg="white",
            font=("SimSun", 11),
            padx=10,
            state=tk.DISABLED
        )
        self.stop_button.grid(row=0, column=5, padx=5, pady=5)
        
        # 创建主显示区域
        display_frame = tk.Frame(self.main_frame, bg=self.colors["bg"])
        display_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左侧卦象信息面板
        info_frame = tk.LabelFrame(
            display_frame, 
            text="卦象信息", 
            font=("SimSun", 12),
            bg=self.colors["bg"],
            fg=self.colors["dark"],
            padx=10,
            pady=10,
            width=300
        )
        info_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 20))
        
        self.current_hexagram = tk.StringVar(value="䷀ 乾")
        self.current_symbol = tk.StringVar(value="111111")
        self.current_meaning = tk.StringVar(value="创造、刚健")
        
        tk.Label(
            info_frame, 
            text="当前卦象:", 
            bg=self.colors["bg"],
            font=("SimSun", 11, "bold")
        ).pack(anchor="w", pady=(5, 0))
        
        tk.Label(
            info_frame, 
            textvariable=self.current_hexagram,
            font=("SimSun", 24),
            bg=self.colors["bg"],
            fg=self.colors["dark"]
        ).pack(anchor="w", pady=5)
        
        tk.Label(
            info_frame, 
            text="卦符:", 
            bg=self.colors["bg"],
            font=("SimSun", 11, "bold")
        ).pack(anchor="w", pady=(10, 0))
        
        tk.Label(
            info_frame, 
            textvariable=self.current_symbol,
            font=("SimSun", 18),
            bg=self.colors["bg"],
            fg=self.colors["dark"]
        ).pack(anchor="w", pady=5)
        
        tk.Label(
            info_frame, 
            text="卦义:", 
            bg=self.colors["bg"],
            font=("SimSun", 11, "bold")
        ).pack(anchor="w", pady=(10, 0))
        
        meaning_label = tk.Label(
            info_frame, 
            textvariable=self.current_meaning,
            font=("SimSun", 11),
            bg=self.colors["bg"],
            fg=self.colors["dark"],
            wraplength=280,
            justify="left"
        )
        meaning_label.pack(anchor="w", pady=5, fill=tk.X)
        
        # 卦象图像
        self.hexagram_canvas = tk.Canvas(
            info_frame, 
            width=180, 
            height=180,
            bg=self.colors["light"],
            highlightthickness=0
        )
        self.hexagram_canvas.pack(pady=20)
        
        # 右侧图形显示区域
        graph_frame = tk.Frame(display_frame, bg=self.colors["bg"])
        graph_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # 创建分形图
        fractal_frame = tk.LabelFrame(
            graph_frame, 
            text="卦象分形演化", 
            font=("SimSun", 12),
            bg=self.colors["bg"],
            fg=self.colors["dark"],
            padx=10,
            pady=10
        )
        fractal_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        self.fig1 = Figure(figsize=(6, 4), dpi=100, facecolor=self.colors["bg"])
        self.ax1 = self.fig1.add_subplot(111)
        self.ax1.set_facecolor(self.colors["light"])
        self.canvas1 = FigureCanvasTkAgg(self.fig1, master=fractal_frame)
        self.canvas1.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # 创建变化曲线
        curve_frame = tk.LabelFrame(
            graph_frame, 
            text="卦象变化曲线", 
            font=("SimSun", 12),
            bg=self.colors["bg"],
            fg=self.colors["dark"],
            padx=10,
            pady=10
        )
        curve_frame.pack(fill=tk.BOTH, expand=True)
        
        self.fig2 = Figure(figsize=(6, 3), dpi=100, facecolor=self.colors["bg"])
        self.ax2 = self.fig2.add_subplot(111)
        self.ax2.set_facecolor(self.colors["light"])
        self.canvas2 = FigureCanvasTkAgg(self.fig2, master=curve_frame)
        self.canvas2.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # 状态栏
        self.status_var = tk.StringVar(value="系统准备就绪")
        status_bar = tk.Label(
            root, 
            textvariable=self.status_var,
            bd=1, 
            relief=tk.SUNKEN, 
            anchor=tk.W,
            font=("SimSun", 10),
            bg=self.colors["light"],
            fg=self.colors["dark"]
        )
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 初始化变量
        self.running = False
        self.history = []
        self.current_index = 1
        self.update_hexagram(1)
        
    def draw_hexagram(self, symbol):
        """在画布上绘制卦象"""
        self.hexagram_canvas.delete("all")
        
        width = 180
        height = 180
        line_height = 20
        line_spacing = 25
        start_y = (height - 6 * line_spacing) / 2
        
        for i, bit in enumerate(symbol):
            y = start_y + i * line_spacing
            if bit == '1':  # 阳爻
                self.hexagram_canvas.create_line(
                    40, y, width-40, y, 
                    width=4, 
                    fill=self.colors["yang"],
                    capstyle=tk.ROUND
                )
            else:  # 阴爻
                self.hexagram_canvas.create_line(
                    40, y, 90, y, 
                    width=4, 
                    fill=self.colors["yin"],
                    capstyle=tk.ROUND
                )
                self.hexagram_canvas.create_line(
                    width-90, y, width-40, y, 
                    width=4, 
                    fill=self.colors["yin"],
                    capstyle=tk.ROUND
                )
    
    def update_hexagram(self, index):
        """更新卦象信息"""
        hexagram = hexagrams[index]
        self.current_hexagram.set(hexagram["name"])
        self.current_symbol.set(hexagram["symbol"])
        self.current_meaning.set(hexagram["meaning"])
        self.draw_hexagram(hexagram["symbol"])
        self.current_index = index
        
        # 添加到历史
        self.history.append(index)
        if len(self.history) > 100:
            self.history.pop(0)
    
    def generate_fractal(self, symbol):
        """根据卦象生成分形图案"""
        self.ax1.clear()
        
        # 将卦象转换为参数
        params = [int(bit) for bit in symbol]
        
        # 生成分形数据
        x = np.linspace(-2, 2, 800)
        y = np.linspace(-2, 2, 800)
        X, Y = np.meshgrid(x, y)
        Z = np.zeros_like(X)
        
        # 使用卦象参数控制分形
        c = complex(
            -0.7 + 0.2 * (params[0] - params[3]),
            0.2 + 0.2 * (params[1] - params[4])
        )
        
        iterations = 20 + 20 * params[2]
        
        for i in range(iterations):
            Z = Z**2 + c
        
        # 绘制分形
        img = self.ax1.imshow(
            np.abs(Z), 
            cmap='magma', 
            extent=[-2, 2, -2, 2],
            origin='lower'
        )
        
        # 添加卦象符号作为标题
        self.ax1.set_title(
            f"卦象分形: {hexagrams[self.current_index]['name']}", 
            fontsize=12,
            fontname='SimSun'
        )
        self.ax1.set_xticks([])
        self.ax1.set_yticks([])
        
        self.fig1.tight_layout()
        self.canvas1.draw()
    
    def plot_history(self):
        """绘制卦象历史变化曲线"""
        self.ax2.clear()
        
        if len(self.history) < 2:
            return
            
        # 创建时间序列
        t = np.arange(len(self.history))
        
        # 绘制曲线
        self.ax2.plot(t, self.history, 'o-', color=self.colors["yang"], linewidth=2, markersize=4)
        
        # 标记当前点
        self.ax2.plot(t[-1], self.history[-1], 'o', markersize=8, 
                      markerfacecolor=self.colors["yin"], markeredgecolor=self.colors["dark"])
        
        # 设置图表属性
        self.ax2.set_title("卦象演化历史", fontsize=12, fontname='SimSun')
        self.ax2.set_xlabel("时间步", fontsize=10)
        self.ax2.set_ylabel("卦象编号", fontsize=10)
        self.ax2.grid(True, linestyle='--', alpha=0.7)
        
        self.fig2.tight_layout()
        self.canvas2.draw()
    
    def evolve_hexagram(self):
        """演化到下一个卦象"""
        if not self.running:
            return
            
        # 基于当前卦象和复杂度生成新卦象
        complexity = self.complexity_var.get()
        new_index = self.current_index
        
        # 根据复杂度决定变化程度
        for _ in range(complexity):
            # 随机选择变化方式
            change_type = np.random.choice(["flip", "shift", "reverse", "complement"], p=[0.4, 0.3, 0.2, 0.1])
            current_symbol = hexagrams[new_index]["symbol"]
            
            if change_type == "flip":
                # 随机翻转一位
                pos = np.random.randint(0, 6)
                new_symbol = list(current_symbol)
                new_symbol[pos] = '1' if new_symbol[pos] == '0' else '0'
                new_symbol = ''.join(new_symbol)
                
            elif change_type == "shift":
                # 循环移位
                shift = np.random.choice([1, 2])
                new_symbol = current_symbol[-shift:] + current_symbol[:-shift]
                
            elif change_type == "reverse":
                # 反转卦象
                new_symbol = current_symbol[::-1]
                
            else:  # complement
                # 取反
                new_symbol = ''.join(['1' if b == '0' else '0' for b in current_symbol])
            
            # 查找新卦象对应的编号
            for idx, data in hexagrams.items():
                if data["symbol"] == new_symbol:
                    new_index = idx
                    break
        
        # 更新卦象
        self.update_hexagram(new_index)
        self.generate_fractal(hexagrams[new_index]["symbol"])
        self.plot_history()
        
        # 设置下一次更新
        delay = int(1000 / self.speed_var.get())
        self.root.after(delay, self.evolve_hexagram)
    
    def start_evolution(self):
        """开始演化过程"""
        if not self.running:
            self.running = True
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.status_var.set("系统运行中...")
            self.evolve_hexagram()
    
    def stop_evolution(self):
        """停止演化"""
        if self.running:
            self.running = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.status_var.set("系统已停止")

# 创建主窗口并运行应用
if __name__ == "__main__":
    root = tk.Tk()
    app = IChingSystem(root)
    root.mainloop()