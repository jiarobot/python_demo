import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QSlider, QLabel, QPushButton, QGroupBox, QFormLayout, QSplitter,
                             QComboBox, QCheckBox, QTabWidget, QScrollArea)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QPen
plt.rc("font", family='Microsoft YaHei')
class SuccessSimulation(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("成功与努力关系的混沌理论模拟")
        self.setGeometry(100, 100, 1400, 900)
        self.timer = QTimer(self)
        
        # 模型参数
        self.initial_effort = 0.5
        self.talent = 0.6
        self.environment = 0.7
        self.luck_factor = 0.2
        self.social_capital = 0.5
        self.time_steps = 50
        self.agents = 5
        self.animation_speed = 200  # ms
        self.current_frame = 0
        self.is_animating = False
        
        # 初始化模拟数据
        self.agents_data = []
        
        # 创建UI
        self.init_ui()
        
        # 初始化模拟
        self.reset_simulation()
        
        # 设置定时器用于动画
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate_step)
    
    def init_ui(self):
        # 创建主控件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # 主布局
        main_layout = QHBoxLayout(main_widget)
        
        # 左侧控制面板
        control_panel = self.create_control_panel()
        
        # 右侧可视化区域
        visual_tabs = self.create_visual_tabs()
        
        # 分割器
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(control_panel)
        splitter.addWidget(visual_tabs)
        splitter.setSizes([300, 1100])
        
        main_layout.addWidget(splitter)
    
    def create_control_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setAlignment(Qt.AlignTop)
        
        # 标题
        title = QLabel("混沌理论模拟控制面板")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50; margin-bottom: 15px;")
        layout.addWidget(title)
        
        # 模型参数组
        params_group = QGroupBox("模型参数")
        params_layout = QFormLayout()
        
        # 努力程度滑块
        self.effort_slider = self.create_slider("努力程度:", 0.1, 1.0, self.initial_effort, 0.05, "#2196f3")
        params_layout.addRow(self.effort_slider["label"], self.effort_slider["slider"])
        
        # 天赋滑块
        self.talent_slider = self.create_slider("天赋:", 0.1, 1.0, self.talent, 0.05, "#4caf50")
        params_layout.addRow(self.talent_slider["label"], self.talent_slider["slider"])
        
        # 环境因素滑块
        self.env_slider = self.create_slider("环境因素:", 0.1, 1.0, self.environment, 0.05, "#ff9800")
        params_layout.addRow(self.env_slider["label"], self.env_slider["slider"])
        
        # 运气因素滑块
        self.luck_slider = self.create_slider("运气因素:", 0.0, 0.5, self.luck_factor, 0.01, "#9c27b0")
        params_layout.addRow(self.luck_slider["label"], self.luck_slider["slider"])
        
        # 社会资本滑块
        self.social_slider = self.create_slider("社会资本:", 0.0, 1.0, self.social_capital, 0.05, "#f44336")
        params_layout.addRow(self.social_slider["label"], self.social_slider["slider"])
        
        params_group.setLayout(params_layout)
        layout.addWidget(params_group)
        
        # 模拟控制组
        sim_group = QGroupBox("模拟控制")
        sim_layout = QVBoxLayout()
        
        # 代理数量选择
        agents_layout = QHBoxLayout()
        agents_layout.addWidget(QLabel("个体数量:"))
        self.agents_combo = QComboBox()
        self.agents_combo.addItems(["3", "5", "8", "10"])
        self.agents_combo.setCurrentText(str(self.agents))
        self.agents_combo.currentTextChanged.connect(self.change_agents)
        agents_layout.addWidget(self.agents_combo)
        sim_layout.addLayout(agents_layout)
        
        # 动画速度控制
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("动画速度:"))
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["慢速", "中速", "快速"])
        self.speed_combo.setCurrentIndex(1)
        self.speed_combo.currentTextChanged.connect(self.change_speed)
        speed_layout.addWidget(self.speed_combo)
        sim_layout.addLayout(speed_layout)
        
        # 显示选项
        self.show_attractors = QCheckBox("显示吸引子区域")
        self.show_attractors.setChecked(True)
        sim_layout.addWidget(self.show_attractors)
        
        self.show_bifurcations = QCheckBox("显示关键节点")
        self.show_bifurcations.setChecked(True)
        sim_layout.addWidget(self.show_bifurcations)
        
        # 按钮组
        btn_layout = QHBoxLayout()
        
        self.reset_btn = QPushButton("重置模拟")
        self.reset_btn.setStyleSheet("background-color: #e3f2fd; padding: 8px;")
        self.reset_btn.clicked.connect(self.reset_simulation)
        btn_layout.addWidget(self.reset_btn)
        
        # 修复：在这里创建 run_btn
        self.run_btn = QPushButton("开始动画")
        self.run_btn.setStyleSheet("background-color: #e8f5e9; padding: 8px;")
        self.run_btn.clicked.connect(self.toggle_animation)
        btn_layout.addWidget(self.run_btn)
        
        sim_layout.addLayout(btn_layout)
        sim_group.setLayout(sim_layout)
        layout.addWidget(sim_group)
        
        # 理论说明
        theory_group = QGroupBox("混沌理论解释")
        theory_layout = QVBoxLayout()
        
        explanation = QLabel(
            "<b>混沌理论</b>解释了为什么微小差异会导致巨大结果变化：<br><br>"
            "• <b>蝴蝶效应</b>: 初始条件微小变化导致长期轨迹巨大差异<br>"
            "• <b>分岔点</b>: 关键决策点可导向不同吸引子<br>"
            "• <b>吸引子</b>: 系统趋向的稳定状态(低/中/高成就)<br>"
            "• <b>非线性</b>: 努力与成功不是简单比例关系<br><br>"
            "<i>努力是成功的重要但不充分条件</i>"
        )
        explanation.setStyleSheet("font-size: 12px; padding: 10px;")
        explanation.setWordWrap(True)
        theory_layout.addWidget(explanation)
        
        theory_group.setLayout(theory_layout)
        layout.addWidget(theory_group)
        
        return panel
    
    def create_slider(self, label, min_val, max_val, init_val, step, color):
        slider_dict = {}
        
        slider_label = QLabel(label)
        slider_label.setStyleSheet("font-weight: bold;")
        
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(int(min_val * 100))
        slider.setMaximum(int(max_val * 100))
        slider.setValue(int(init_val * 100))
        slider.setSingleStep(int(step * 100))
        slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                height: 8px;
                background: #e0e0e0;
                margin: 2px 0;
                border-radius: 4px;
            }}
            QSlider::handle:horizontal {{
                background: {color};
                border: 2px solid white;
                width: 18px;
                height: 18px;
                margin: -6px 0;
                border-radius: 9px;
            }}
            QSlider::sub-page:horizontal {{
                background: {color};
                border-radius: 4px;
            }}
        """)
        
        value_label = QLabel(f"{init_val:.2f}")
        value_label.setMinimumWidth(40)
        value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        value_label.setStyleSheet("font-weight: bold; color: #333;")
        
        # 连接信号
        slider.valueChanged.connect(lambda value: self.slider_changed(slider, value_label, value))
        
        slider_layout = QHBoxLayout()
        slider_layout.addWidget(slider)
        slider_layout.addWidget(value_label)
        
        return {
            "label": slider_label,
            "slider": slider_layout,
            "value_label": value_label
        }
    
    def create_visual_tabs(self):
        tabs = QTabWidget()
        
        # 主轨迹图
        self.main_fig = Figure(figsize=(8, 6), dpi=100)
        self.main_canvas = FigureCanvas(self.main_fig)
        self.main_ax = self.main_fig.add_subplot(111)
        self.main_toolbar = NavigationToolbar(self.main_canvas, self)
        
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.addWidget(self.main_toolbar)
        main_layout.addWidget(self.main_canvas)
        
        tabs.addTab(main_widget, "主轨迹图")
        
        # 努力-成功关系图
        self.effort_fig = Figure(figsize=(8, 6), dpi=100)
        self.effort_canvas = FigureCanvas(self.effort_fig)
        self.effort_ax = self.effort_fig.add_subplot(111)
        self.effort_toolbar = NavigationToolbar(self.effort_canvas, self)
        
        effort_widget = QWidget()
        effort_layout = QVBoxLayout(effort_widget)
        effort_layout.addWidget(self.effort_toolbar)
        effort_layout.addWidget(self.effort_canvas)
        
        tabs.addTab(effort_widget, "努力-成功关系")
        
        # 成功分布图
        self.hist_fig = Figure(figsize=(8, 6), dpi=100)
        self.hist_canvas = FigureCanvas(self.hist_fig)
        self.hist_ax = self.hist_fig.add_subplot(111)
        self.hist_toolbar = NavigationToolbar(self.hist_canvas, self)
        
        hist_widget = QWidget()
        hist_layout = QVBoxLayout(hist_widget)
        hist_layout.addWidget(self.hist_toolbar)
        hist_layout.addWidget(self.hist_canvas)
        
        tabs.addTab(hist_widget, "成功分布")
        
        # 3D轨迹图
        self.three_d_fig = Figure(figsize=(8, 6), dpi=100)
        self.three_d_canvas = FigureCanvas(self.three_d_fig)
        self.three_d_ax = self.three_d_fig.add_subplot(111, projection='3d')
        self.three_d_toolbar = NavigationToolbar(self.three_d_canvas, self)
        
        three_d_widget = QWidget()
        three_d_layout = QVBoxLayout(three_d_widget)
        three_d_layout.addWidget(self.three_d_toolbar)
        three_d_layout.addWidget(self.three_d_canvas)
        
        tabs.addTab(three_d_widget, "3D轨迹")
        
        return tabs
    
    def slider_changed(self, slider, value_label, value):
        # 更新值标签
        float_value = value / 100.0
        value_label.setText(f"{float_value:.2f}")
        
        # 更新模型参数
        if slider == self.effort_slider["slider"].itemAt(0).widget():
            self.initial_effort = float_value
        elif slider == self.talent_slider["slider"].itemAt(0).widget():
            self.talent = float_value
        elif slider == self.env_slider["slider"].itemAt(0).widget():
            self.environment = float_value
        elif slider == self.luck_slider["slider"].itemAt(0).widget():
            self.luck_factor = float_value
        elif slider == self.social_slider["slider"].itemAt(0).widget():
            self.social_capital = float_value
        
        # 重置模拟
        self.reset_simulation()
    
    def change_agents(self, text):
        self.agents = int(text)
        self.reset_simulation()
    
    def change_speed(self, text):
        if text == "慢速":
            self.animation_speed = 400
        elif text == "中速":
            self.animation_speed = 200
        elif text == "快速":
            self.animation_speed = 100
        
        if self.is_animating:
            self.timer.setInterval(self.animation_speed)
    
    def toggle_animation(self):
        if self.is_animating:
            self.timer.stop()
            self.run_btn.setText("开始动画")
            self.is_animating = False
            self.current_frame = 0
            self.update_plots()
        else:
            self.timer.start(self.animation_speed)
            self.run_btn.setText("停止动画")
            self.is_animating = True
    
    def animate_step(self):
        if self.current_frame < self.time_steps:
            self.current_frame += 1
            self.update_plots()
        else:
            self.timer.stop()
            self.run_btn.setText("开始动画")
            self.is_animating = False
            self.current_frame = 0
    
    def logistic_map(self, x, r):
        """Logistic映射函数，用于模拟混沌行为"""
        return r * x * (1 - x)
    
    def simulate_agent(self, params):
        """模拟单个个体的成功轨迹"""
        effort, talent, environment, luck_factor, social_capital = params
        
        # 初始化数组
        success = np.zeros(self.time_steps)
        effort_level = np.zeros(self.time_steps)
        
        # 初始值
        effort_level[0] = effort
        success[0] = (effort * talent * environment) / 3.0
        
        # 模拟每个时间步
        for t in range(1, self.time_steps):
            # 努力程度变化（受环境和个人因素影响）
            effort_level[t] = self.logistic_map(effort_level[t-1], 
                                             0.8 + 0.4 * social_capital - 0.2 * (1 - environment))
            
            # 基础成功值（努力、天赋、环境）
            base_success = (effort_level[t] * talent * environment) / 3.0
            
            # 随机事件（运气）
            luck = luck_factor * (2 * np.random.random() - 1)
            
            # 关键节点（分岔点） - 在特定时间点有重大机遇
            if t == 10 or t == 20 or t == 30:
                # 高社会资本增加获得机遇的概率
                if np.random.random() < 0.3 + 0.4 * social_capital:
                    base_success += 0.2 * talent
            
            # 成功值计算（加入运气）
            success[t] = base_success + luck
            
            # 确保成功值在[0,1]范围内
            success[t] = np.clip(success[t], 0, 1)
        
        return success, effort_level
    
    def reset_simulation(self, event=None):
        """重置模拟"""
        self.agents_data = []
        self.current_frame = 0
        
        # 只有在UI初始化后才能访问按钮
        if hasattr(self, 'run_btn'):
            self.is_animating = False
            self.run_btn.setText("开始动画")
            self.timer.stop()
        
        # 创建多个不同初始条件的个体
        for i in range(self.agents):
            # 在初始努力值附近添加微小变化（蝴蝶效应）
            init_effort = self.initial_effort * (1 + 0.05 * (np.random.random() - 0.5))
            
            agent_params = (
                init_effort,
                self.talent * (1 + 0.1 * (np.random.random() - 0.5)),
                self.environment,
                self.luck_factor,
                self.social_capital
            )
            
            success, effort = self.simulate_agent(agent_params)
            self.agents_data.append({
                'success': success,
                'effort': effort,
                'params': agent_params
            })
        
        self.update_plots()
    
    def update_plots(self):
        """更新所有图表"""
        self.plot_main()
        self.plot_effort()
        self.plot_hist()
        self.plot_3d()
        
        # 更新画布
        self.main_canvas.draw()
        self.effort_canvas.draw()
        self.hist_canvas.draw()
        self.three_d_canvas.draw()
    
    def plot_main(self):
        """绘制主成功轨迹图"""
        self.main_ax.clear()
        time = np.arange(self.time_steps)
        
        # 绘制吸引子区域
        if self.show_attractors.isChecked():
            self.main_ax.add_patch(plt.Rectangle((0, 0), 15, 0.4, color='#ffcdd2', alpha=0.3, label='低成就区域'))
            self.main_ax.add_patch(plt.Rectangle((15, 0.4), 20, 0.3, color='#fff9c4', alpha=0.3, label='中等成就区域'))
            self.main_ax.add_patch(plt.Rectangle((35, 0.7), 15, 0.3, color='#c8e6c9', alpha=0.3, label='高成就区域'))
        
        # 绘制每个个体的轨迹
        for i, agent in enumerate(self.agents_data):
            success = agent['success']
            color = plt.cm.viridis(i / len(self.agents_data))
            
            # 绘制完整轨迹
            self.main_ax.plot(time, success, color=color, alpha=0.3)
            
            # 高亮显示当前帧（如果是动画）
            if self.current_frame < len(success):
                self.main_ax.plot(time[:self.current_frame+1], success[:self.current_frame+1], 
                                color=color, linewidth=2, label=f'个体 {i+1}')
                self.main_ax.scatter([self.current_frame], [success[self.current_frame]], 
                                   color=color, s=80, edgecolor='k', zorder=5)
        
        # 添加分岔点标记
        if self.show_bifurcations.isChecked():
            for point in [10, 20, 30]:
                self.main_ax.axvline(x=point, color='r', linestyle='--', alpha=0.5)
                self.main_ax.text(point, 1.05, '关键节点', fontsize=10, ha='center', color='r')
        
        self.main_ax.set_title('成功轨迹 (蝴蝶效应可视化)', fontsize=16, pad=15)
        self.main_ax.set_xlabel('时间 (发展阶段)', fontsize=12)
        self.main_ax.set_ylabel('成功程度', fontsize=12)
        self.main_ax.set_ylim(0, 1.1)
        self.main_ax.set_xlim(0, self.time_steps-1)
        self.main_ax.grid(True, linestyle='--', alpha=0.7)
        self.main_ax.legend(loc='upper left')
    
    def plot_effort(self):
        """绘制努力程度图"""
        self.effort_ax.clear()
        
        for i, agent in enumerate(self.agents_data):
            effort = agent['effort']
            success = agent['success']
            color = plt.cm.viridis(i / len(self.agents_data))
            
            if self.current_frame < len(effort):
                # 动画模式
                self.effort_ax.plot(effort[:self.current_frame+1], success[:self.current_frame+1], 
                                  color=color, linewidth=2)
                self.effort_ax.scatter([effort[self.current_frame]], [success[self.current_frame]], 
                                     color=color, s=50, edgecolor='k', zorder=5)
            else:
                # 静态模式
                self.effort_ax.plot(effort, success, color=color, alpha=0.7)
        
        self.effort_ax.set_title('努力 vs 成功', fontsize=14)
        self.effort_ax.set_xlabel('努力程度', fontsize=10)
        self.effort_ax.set_ylabel('成功程度', fontsize=10)
        self.effort_ax.set_xlim(0, 1)
        self.effort_ax.set_ylim(0, 1)
        self.effort_ax.grid(True, linestyle='--', alpha=0.5)
    
    def plot_hist(self):
        """绘制成功分布直方图"""
        self.hist_ax.clear()
        final_success = [agent['success'][-1] for agent in self.agents_data]
        
        # 绘制分布图
        n, bins, patches = self.hist_ax.hist(final_success, bins=15, color='#2196f3', alpha=0.7)
        
        # 添加密度曲线
        from scipy.stats import gaussian_kde
        if len(final_success) > 1:
            density = gaussian_kde(final_success)
            xs = np.linspace(0, 1, 200)
            self.hist_ax.plot(xs, density(xs) * len(final_success) * (bins[1]-bins[0]), 'r-', linewidth=2)
        
        self.hist_ax.set_title('最终成功分布', fontsize=14)
        self.hist_ax.set_xlabel('成功程度', fontsize=10)
        self.hist_ax.set_ylabel('个体数量', fontsize=10)
        self.hist_ax.set_xlim(0, 1)
        self.hist_ax.grid(True, linestyle='--', alpha=0.5)
        
        # 添加统计信息
        mean_success = np.mean(final_success)
        std_success = np.std(final_success)
        self.hist_ax.axvline(mean_success, color='r', linestyle='--')
        self.hist_ax.text(mean_success+0.05, self.hist_ax.get_ylim()[1]*0.8, 
                         f'均值: {mean_success:.2f}\n标准差: {std_success:.2f}', 
                         fontsize=10, color='r')
    
    def plot_3d(self):
        """绘制3D成功轨迹图"""
        self.three_d_ax.clear()
        
        for i, agent in enumerate(self.agents_data):
            success = agent['success']
            effort = agent['effort']
            time = np.arange(len(success))
            color = plt.cm.viridis(i / len(self.agents_data))
            
            if self.current_frame < len(success):
                # 动画模式
                self.three_d_ax.plot(time[:self.current_frame+1], effort[:self.current_frame+1], 
                                   success[:self.current_frame+1], color=color, linewidth=2)
                self.three_d_ax.scatter([time[self.current_frame]], [effort[self.current_frame]], 
                                      [success[self.current_frame]], color=color, s=50, edgecolor='k')
            else:
                # 静态模式
                self.three_d_ax.plot(time, effort, success, color=color, alpha=0.7)
        
        # 添加吸引子标记
        self.three_d_ax.scatter([0], [0.5], [0.3], s=200, c='r', marker='*', label='起始点')
        self.three_d_ax.scatter([50], [0.7], [0.9], s=200, c='g', marker='*', label='精英吸引子')
        self.three_d_ax.scatter([50], [0.6], [0.6], s=200, c='b', marker='*', label='中等吸引子')
        self.three_d_ax.scatter([50], [0.5], [0.3], s=200, c='m', marker='*', label='低成就吸引子')
        
        self.three_d_ax.set_title('成功轨迹 (时间-努力-成功)', fontsize=14, pad=20)
        self.three_d_ax.set_xlabel('时间', fontsize=10, labelpad=10)
        self.three_d_ax.set_ylabel('努力', fontsize=10, labelpad=10)
        self.three_d_ax.set_zlabel('成功', fontsize=10, labelpad=10)
        self.three_d_ax.xaxis.pane.fill = False
        self.three_d_ax.yaxis.pane.fill = False
        self.three_d_ax.zaxis.pane.fill = False
        self.three_d_ax.grid(True, linestyle='--', alpha=0.7)
        self.three_d_ax.legend()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # 设置应用样式
    app.setStyleSheet("""
        QMainWindow {
            background-color: #f5f7fa;
        }
        QGroupBox {
            font-size: 14px;
            font-weight: bold;
            border: 1px solid #d0d7de;
            border-radius: 8px;
            margin-top: 20px;
            padding-top: 15px;
            background-color: white;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
        }
        QPushButton {
            background-color: #e3f2fd;
            border: 1px solid #bbdefb;
            border-radius: 4px;
            padding: 6px 12px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #bbdefb;
        }
        QTabWidget::pane {
            border: 1px solid #d0d7de;
            border-radius: 4px;
            background: white;
        }
        QTabBar::tab {
            background: #e3f2fd;
            border: 1px solid #bbdefb;
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            padding: 6px 12px;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background: white;
            border-bottom: 1px solid white;
            margin-bottom: -1px;
        }
    """)
    
    window = SuccessSimulation()
    window.show()
    sys.exit(app.exec_())