import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import yfinance as yf
import talib
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import QDate, Qt
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QSplitter, QComboBox, QPushButton, 
                             QLabel, QTableWidget, QTableWidgetItem, QHeaderView,
                             QTabWidget, QDateEdit, QGroupBox, QFormLayout, QCheckBox,
                             QSpinBox, QDoubleSpinBox, QTextEdit, QStatusBar)
from PyQt5.QtGui import QFont, QPalette, QColor

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from mpl_finance import candlestick_ohlc

plt.style.use('seaborn-v0_8')

class FinancialChartCanvas(FigureCanvas):
    def __init__(self, parent=None, width=10, height=8, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        
        # 创建子图
        self.ax1 = self.fig.add_subplot(3, 1, 1)  # 价格图表
        self.ax2 = self.fig.add_subplot(3, 1, 2)  # 成交量图表
        self.ax3 = self.fig.add_subplot(3, 1, 3)  # 技术指标图表
        
        # 调整子图间距
        self.fig.subplots_adjust(hspace=0.3)
        
        # 初始化数据
        self.data = None
        self.indicators = {}
        
    def plot_data(self, data, title="Financial Data"):
        """绘制金融数据"""
        if data is None or data.empty:
            return
            
        self.data = data
        self.fig.suptitle(title, fontsize=16, fontweight='bold')
        
        # 清除之前的图表
        self.ax1.clear()
        self.ax2.clear()
        self.ax3.clear()
        
        # 准备K线图数据
        ohlc_data = []
        for i, (index, row) in enumerate(data.iterrows()):
            date_num = mdates.date2num(index)
            ohlc_data.append((date_num, row['Open'], row['High'], row['Low'], row['Close'], row['Volume']))
        
        # 绘制K线图
        candlestick_ohlc(self.ax1, ohlc_data, width=0.6, colorup='g', colordown='r', alpha=0.8)
        
        # 设置价格图表
        self.ax1.set_ylabel('Price')
        self.ax1.grid(True, linestyle='--', alpha=0.7)
        self.ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        
        # 绘制成交量
        self.ax2.bar(data.index, data['Volume'], color=['g' if data['Close'].iloc[i] >= data['Open'].iloc[i] else 'r' for i in range(len(data))])
        self.ax2.set_ylabel('Volume')
        self.ax2.grid(True, linestyle='--', alpha=0.7)
        self.ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        
        # 绘制技术指标（如果有）
        if self.indicators:
            self.plot_indicators()
        else:
            self.ax3.text(0.5, 0.5, 'No indicators selected', horizontalalignment='center', 
                         verticalalignment='center', transform=self.ax3.transAxes)
            self.ax3.set_ylabel('Indicators')
        
        # 旋转x轴标签
        for ax in [self.ax1, self.ax2, self.ax3]:
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        
        self.draw()
    
    def add_indicator(self, name, values, color='blue', style='-'):
        """添加技术指标"""
        self.indicators[name] = {'values': values, 'color': color, 'style': style}
    
    def clear_indicators(self):
        """清除所有技术指标"""
        self.indicators = {}
    
    def plot_indicators(self):
        """绘制技术指标"""
        self.ax3.clear()
        
        for name, indicator in self.indicators.items():
            values = indicator['values']
            color = indicator['color']
            style = indicator['style']
            
            # 确保指标数据长度与价格数据一致
            if len(values) == len(self.data):
                self.ax3.plot(self.data.index, values, color=color, linestyle=style, label=name)
        
        self.ax3.set_ylabel('Indicators')
        self.ax3.legend(loc='upper left')
        self.ax3.grid(True, linestyle='--', alpha=0.7)
        self.ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))

class FinancialAnalysisApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("高级金融分析工具")
        self.setGeometry(100, 100, 1600, 900)
        
        # 初始化数据
        self.data = None
        self.symbol = "AAPL"
        self.end_date = datetime.now()
        self.start_date = self.end_date - timedelta(days=365)
        
        # 创建中央部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # 创建左侧控制面板
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel, 1)
        
        # 创建右侧图表区域
        chart_container = QWidget()
        chart_layout = QVBoxLayout(chart_container)
        
        # 创建图表画布
        self.chart_canvas = FinancialChartCanvas(self, width=10, height=8, dpi=100)
        
        # 添加Matplotlib工具栏
        self.toolbar = NavigationToolbar(self.chart_canvas, self)
        chart_layout.addWidget(self.toolbar)
        chart_layout.addWidget(self.chart_canvas)
        
        main_layout.addWidget(chart_container, 4)
        
        # 创建状态栏
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("就绪")
        
        # 初始加载数据
        self.load_data()
    
    def create_control_panel(self):
        """创建左侧控制面板"""
        panel = QWidget()
        panel.setMaximumWidth(350)
        layout = QVBoxLayout(panel)
        
        # 股票选择部分
        symbol_group = QGroupBox("股票选择")
        symbol_layout = QFormLayout(symbol_group)
        
        self.symbol_input = QComboBox()
        self.symbol_input.addItems(["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "SPY", "QQQ"])
        self.symbol_input.setCurrentText(self.symbol)
        self.symbol_input.currentTextChanged.connect(self.on_symbol_changed)
        symbol_layout.addRow("股票代码:", self.symbol_input)
        
        self.start_date_input = QDateEdit()
        self.start_date_input.setDate(QDate(self.start_date.year, self.start_date.month, self.start_date.day))
        self.start_date_input.dateChanged.connect(self.on_date_changed)
        symbol_layout.addRow("开始日期:", self.start_date_input)
        
        self.end_date_input = QDateEdit()
        self.end_date_input.setDate(QDate(self.end_date.year, self.end_date.month, self.end_date.day))
        self.end_date_input.dateChanged.connect(self.on_date_changed)
        symbol_layout.addRow("结束日期:", self.end_date_input)
        
        self.refresh_btn = QPushButton("刷新数据")
        self.refresh_btn.clicked.connect(self.load_data)
        symbol_layout.addRow(self.refresh_btn)
        
        layout.addWidget(symbol_group)
        
        # 技术指标部分
        indicators_group = QGroupBox("技术指标")
        indicators_layout = QVBoxLayout(indicators_group)
        
        # SMA
        sma_widget = QWidget()
        sma_layout = QHBoxLayout(sma_widget)
        self.sma_check = QCheckBox("SMA")
        self.sma_period = QSpinBox()
        self.sma_period.setRange(5, 200)
        self.sma_period.setValue(20)
        sma_layout.addWidget(self.sma_check)
        sma_layout.addWidget(QLabel("周期:"))
        sma_layout.addWidget(self.sma_period)
        sma_layout.addStretch()
        indicators_layout.addWidget(sma_widget)
        
        # EMA
        ema_widget = QWidget()
        ema_layout = QHBoxLayout(ema_widget)
        self.ema_check = QCheckBox("EMA")
        self.ema_period = QSpinBox()
        self.ema_period.setRange(5, 200)
        self.ema_period.setValue(20)
        ema_layout.addWidget(self.ema_check)
        ema_layout.addWidget(QLabel("周期:"))
        ema_layout.addWidget(self.ema_period)
        ema_layout.addStretch()
        indicators_layout.addWidget(ema_widget)
        
        # RSI
        rsi_widget = QWidget()
        rsi_layout = QHBoxLayout(rsi_widget)
        self.rsi_check = QCheckBox("RSI")
        self.rsi_period = QSpinBox()
        self.rsi_period.setRange(5, 50)
        self.rsi_period.setValue(14)
        rsi_layout.addWidget(self.rsi_check)
        rsi_layout.addWidget(QLabel("周期:"))
        rsi_layout.addWidget(self.rsi_period)
        rsi_layout.addStretch()
        indicators_layout.addWidget(rsi_widget)
        
        # MACD
        macd_widget = QWidget()
        macd_layout = QHBoxLayout(macd_widget)
        self.macd_check = QCheckBox("MACD")
        macd_layout.addWidget(self.macd_check)
        macd_layout.addStretch()
        indicators_layout.addWidget(macd_widget)
        
        # Bollinger Bands
        bb_widget = QWidget()
        bb_layout = QHBoxLayout(bb_widget)
        self.bb_check = QCheckBox("布林带")
        self.bb_period = QSpinBox()
        self.bb_period.setRange(5, 50)
        self.bb_period.setValue(20)
        bb_layout.addWidget(self.bb_check)
        bb_layout.addWidget(QLabel("周期:"))
        bb_layout.addWidget(self.bb_period)
        bb_layout.addStretch()
        indicators_layout.addWidget(bb_widget)
        
        # 应用指标按钮
        self.apply_indicators_btn = QPushButton("应用指标")
        self.apply_indicators_btn.clicked.connect(self.apply_indicators)
        indicators_layout.addWidget(self.apply_indicators_btn)
        
        # 清除指标按钮
        self.clear_indicators_btn = QPushButton("清除指标")
        self.clear_indicators_btn.clicked.connect(self.clear_indicators)
        indicators_layout.addWidget(self.clear_indicators_btn)
        
        layout.addWidget(indicators_group)
        
        # 分析部分
        analysis_group = QGroupBox("技术分析")
        analysis_layout = QVBoxLayout(analysis_group)
        
        self.analyze_btn = QPushButton("运行技术分析")
        self.analyze_btn.clicked.connect(self.run_analysis)
        analysis_layout.addWidget(self.analyze_btn)
        
        self.analysis_output = QTextEdit()
        self.analysis_output.setReadOnly(True)
        analysis_layout.addWidget(self.analysis_output)
        
        layout.addWidget(analysis_group)
        
        layout.addStretch()
        
        return panel
    
    def on_symbol_changed(self, symbol):
        """股票代码改变时的处理"""
        self.symbol = symbol
        self.load_data()
    
    def on_date_changed(self):
        """日期改变时的处理"""
        start_qdate = self.start_date_input.date()
        end_qdate = self.end_date_input.date()
        
        self.start_date = datetime(start_qdate.year(), start_qdate.month(), start_qdate.day())
        self.end_date = datetime(end_qdate.year(), end_qdate.month(), end_qdate.day())
        
        self.load_data()
    
    def load_data(self):
        """加载股票数据"""
        self.statusBar.showMessage("正在加载数据...")
        
        try:
            # 使用yfinance获取数据
            self.data = yf.download(
                self.symbol, 
                start=self.start_date, 
                end=self.end_date,
                progress=False
            )
            
            if self.data.empty:
                self.statusBar.showMessage("未能获取到数据")
                return
                
            # 绘制数据
            title = f"{self.symbol} - {self.start_date.strftime('%Y-%m-%d')} 至 {self.end_date.strftime('%Y-%m-%d')}"
            self.chart_canvas.plot_data(self.data, title)
            
            # 应用已选择的指标
            self.apply_indicators()
            
            self.statusBar.showMessage("数据加载完成")
            
        except Exception as e:
            self.statusBar.showMessage(f"错误: {str(e)}")
    
    def apply_indicators(self):
        """应用选定的技术指标"""
        if self.data is None or self.data.empty:
            return
            
        self.chart_canvas.clear_indicators()
        
        # 计算并添加选定的指标
        close_prices = self.data['Close'].values
        
        # SMA
        if self.sma_check.isChecked():
            period = self.sma_period.value()
            sma = talib.SMA(close_prices, timeperiod=period)
            self.chart_canvas.add_indicator(f"SMA({period})", sma, color='blue')
        
        # EMA
        if self.ema_check.isChecked():
            period = self.ema_period.value()
            ema = talib.EMA(close_prices, timeperiod=period)
            self.chart_canvas.add_indicator(f"EMA({period})", ema, color='orange')
        
        # RSI
        if self.rsi_check.isChecked():
            period = self.rsi_period.value()
            rsi = talib.RSI(close_prices, timeperiod=period)
            # RSI需要单独绘制在指标区域
            self.chart_canvas.ax3.clear()
            self.chart_canvas.ax3.plot(self.data.index, rsi, color='purple', label=f'RSI({period})')
            self.chart_canvas.ax3.axhline(70, color='r', linestyle='--', alpha=0.7)
            self.chart_canvas.ax3.axhline(30, color='g', linestyle='--', alpha=0.7)
            self.chart_canvas.ax3.set_ylabel('RSI')
            self.chart_canvas.ax3.legend(loc='upper left')
            self.chart_canvas.ax3.grid(True, linestyle='--', alpha=0.7)
        
        # MACD
        if self.macd_check.isChecked():
            macd, macd_signal, macd_hist = talib.MACD(close_prices)
            # MACD需要单独绘制在指标区域
            self.chart_canvas.ax3.clear()
            self.chart_canvas.ax3.plot(self.data.index, macd, color='blue', label='MACD')
            self.chart_canvas.ax3.plot(self.data.index, macd_signal, color='red', label='Signal')
            self.chart_canvas.ax3.bar(self.data.index, macd_hist, color=['g' if h >= 0 else 'r' for h in macd_hist], alpha=0.5, label='Histogram')
            self.chart_canvas.ax3.axhline(0, color='black', linestyle='-', alpha=0.3)
            self.chart_canvas.ax3.set_ylabel('MACD')
            self.chart_canvas.ax3.legend(loc='upper left')
            self.chart_canvas.ax3.grid(True, linestyle='--', alpha=0.7)
        
        # 布林带
        if self.bb_check.isChecked():
            period = self.bb_period.value()
            upper, middle, lower = talib.BBANDS(close_prices, timeperiod=period)
            self.chart_canvas.add_indicator(f"BB Upper({period})", upper, color='red', style='--')
            self.chart_canvas.add_indicator(f"BB Middle({period})", middle, color='blue')
            self.chart_canvas.add_indicator(f"BB Lower({period})", lower, color='red', style='--')
        
        # 重绘图表
        self.chart_canvas.draw()
    
    def clear_indicators(self):
        """清除所有技术指标"""
        self.chart_canvas.clear_indicators()
        self.chart_canvas.plot_data(self.data)
        
        # 取消所有复选框
        self.sma_check.setChecked(False)
        self.ema_check.setChecked(False)
        self.rsi_check.setChecked(False)
        self.macd_check.setChecked(False)
        self.bb_check.setChecked(False)
    
    def run_analysis(self):
        """运行技术分析"""
        if self.data is None or self.data.empty:
            self.analysis_output.setText("没有数据可供分析")
            return
            
        output = f"技术分析报告 - {self.symbol}\n"
        output += f"分析期间: {self.start_date.strftime('%Y-%m-%d')} 至 {self.end_date.strftime('%Y-%m-%d')}\n"
        output += "=" * 50 + "\n\n"
        
        close_prices = self.data['Close'].values
        
        # 计算基本统计
        returns = np.diff(close_prices) / close_prices[:-1]
        volatility = np.std(returns) * np.sqrt(252)  # 年化波动率
        
        output += f"期末价格: {close_prices[-1]:.2f}\n"
        output += f"期间收益率: {(close_prices[-1] - close_prices[0]) / close_prices[0] * 100:.2f}%\n"
        output += f"年化波动率: {volatility * 100:.2f}%\n\n"
        
        # 计算技术指标
        output += "技术指标:\n"
        
        # RSI
        rsi = talib.RSI(close_prices, timeperiod=14)[-1]
        output += f"RSI(14): {rsi:.2f} - "
        if rsi > 70:
            output += "超买\n"
        elif rsi < 30:
            output += "超卖\n"
        else:
            output += "中性\n"
        
        # MACD
        macd, macd_signal, _ = talib.MACD(close_prices)
        output += f"MACD: {macd[-1]:.2f}, Signal: {macd_signal[-1]:.2f} - "
        if macd[-1] > macd_signal[-1]:
            output += "看涨信号\n"
        else:
            output += "看跌信号\n"
        
        # 移动平均线
        sma_20 = talib.SMA(close_prices, timeperiod=20)[-1]
        sma_50 = talib.SMA(close_prices, timeperiod=50)[-1]
        
        output += f"SMA(20): {sma_20:.2f}, SMA(50): {sma_50:.2f} - "
        if sma_20 > sma_50:
            output += "短期趋势向上\n"
        else:
            output += "短期趋势向下\n"
        
        # 布林带
        upper_bb, middle_bb, lower_bb = talib.BBANDS(close_prices, timeperiod=20)
        current_price = close_prices[-1]
        bb_position = (current_price - lower_bb[-1]) / (upper_bb[-1] - lower_bb[-1])
        
        output += f"布林带位置: {bb_position * 100:.1f}% - "
        if bb_position > 0.8:
            output += "接近上轨，可能超买\n"
        elif bb_position < 0.2:
            output += "接近下轨，可能超卖\n"
        else:
            output += "在中轨附近\n"
        
        self.analysis_output.setText(output)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    main_window = FinancialAnalysisApp()
    main_window.show()
    
    sys.exit(app.exec_())