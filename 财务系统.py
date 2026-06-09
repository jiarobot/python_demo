import sys
import numpy as np
import pandas as pd
import scipy.optimize as sco
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.gridspec as gridspec
import yfinance as yf
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QTabWidget, QPushButton, QLabel, QLineEdit, QTableWidget, 
                             QTableWidgetItem, QComboBox, QDateEdit, QHeaderView, QMessageBox,
                             QGroupBox, QFormLayout, QSpinBox, QDoubleSpinBox, QSplitter,
                             QTextEdit, QProgressBar, QFileDialog, QCheckBox, QSlider,
                             QListWidget, QListWidgetItem, QDialog, QDialogButtonBox)
from PyQt5.QtCore import Qt, QDate, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPalette, QColor, QIcon


class FinancialCalculator:
    """增强的财务计算工具类"""
    
    @staticmethod
    def calculate_npv(cash_flows, discount_rate):
        """计算净现值(NPV)"""
        npv = 0
        for t, cf in enumerate(cash_flows):
            npv += cf / (1 + discount_rate) ** t
        return npv
    
    @staticmethod
    def calculate_irr(cash_flows, iterations=100):
        """计算内部收益率(IRR)"""
        if len(cash_flows) == 0:
            return 0
        
        # 使用牛顿迭代法近似计算IRR
        x = 0.1  # 初始猜测值
        for i in range(iterations):
            f = FinancialCalculator.calculate_npv(cash_flows, x)
            f_prime = 0
            for t, cf in enumerate(cash_flows):
                f_prime -= t * cf / (1 + x) ** (t + 1)
            
            if f_prime == 0:
                break
                
            x = x - f / f_prime
            
        return x
    
    @staticmethod
    def calculate_payback_period(cash_flows):
        """计算投资回收期"""
        cumulative = 0
        for period, cash_flow in enumerate(cash_flows):
            cumulative += cash_flow
            if cumulative >= 0:
                return period
        return len(cash_flows)  # 未能在投资期内回收
    
    @staticmethod
    def calculate_roi(initial_investment, final_value):
        """计算投资回报率(ROI)"""
        return (final_value - initial_investment) / initial_investment * 100
    
    @staticmethod
    def calculate_amortization(principal, annual_rate, years):
        """计算等额本息还款计划"""
        monthly_rate = annual_rate / 12 / 100
        n_payments = years * 12
        monthly_payment = principal * monthly_rate * (1 + monthly_rate) ** n_payments / ((1 + monthly_rate) ** n_payments - 1)
        
        schedule = []
        balance = principal
        
        for month in range(1, n_payments + 1):
            interest = balance * monthly_rate
            principal_payment = monthly_payment - interest
            balance -= principal_payment
            
            schedule.append({
                'month': month,
                'payment': monthly_payment,
                'principal': principal_payment,
                'interest': interest,
                'balance': balance
            })
            
        return schedule
    
    @staticmethod
    def calculate_future_value(present_value, rate, periods):
        """计算未来值"""
        return present_value * (1 + rate) ** periods
    
    @staticmethod
    def calculate_present_value(future_value, rate, periods):
        """计算现值"""
        return future_value / (1 + rate) ** periods
    
    @staticmethod
    def black_scholes_call(S, K, T, r, sigma):
        """Black-Scholes期权定价模型（看涨期权）"""
        if T <= 0:
            return max(0, S - K)
        
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        call_price = S * stats.norm.cdf(d1) - K * np.exp(-r * T) * stats.norm.cdf(d2)
        return call_price
    
    @staticmethod
    def black_scholes_put(S, K, T, r, sigma):
        """Black-Scholes期权定价模型（看跌期权）"""
        if T <= 0:
            return max(0, K - S)
        
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        put_price = K * np.exp(-r * T) * stats.norm.cdf(-d2) - S * stats.norm.cdf(-d1)
        return put_price
    
    @staticmethod
    def monte_carlo_simulation(S0, mu, sigma, T, num_simulations, num_steps):
        """蒙特卡洛模拟股票价格路径"""
        dt = T / num_steps
        stock_prices = np.zeros((num_simulations, num_steps + 1))
        stock_prices[:, 0] = S0
        
        for i in range(1, num_steps + 1):
            z = np.random.standard_normal(num_simulations)
            stock_prices[:, i] = stock_prices[:, i-1] * np.exp((mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * z)
        
        return stock_prices
    
    @staticmethod
    def calculate_var(returns, confidence_level=0.95):
        """计算风险价值(VaR)"""
        if len(returns) == 0:
            return 0
        return np.percentile(returns, (1 - confidence_level) * 100)
    
    @staticmethod
    def calculate_cvar(returns, confidence_level=0.95):
        """计算条件风险价值(CVaR)"""
        if len(returns) == 0:
            return 0
        var = FinancialCalculator.calculate_var(returns, confidence_level)
        return returns[returns <= var].mean()
    
    @staticmethod
    def portfolio_performance(weights, mean_returns, cov_matrix):
        """计算投资组合的预期回报和波动率"""
        returns = np.sum(mean_returns * weights)
        std = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        return returns, std
    
    @staticmethod
    def negative_sharpe_ratio(weights, mean_returns, cov_matrix, risk_free_rate=0):
        """计算负夏普比率（用于优化）"""
        p_ret, p_std = FinancialCalculator.portfolio_performance(weights, mean_returns, cov_matrix)
        return -(p_ret - risk_free_rate) / p_std
    
    @staticmethod
    def portfolio_variance(weights, mean_returns, cov_matrix):
        """计算投资组合方差（用于优化）"""
        return FinancialCalculator.portfolio_performance(weights, mean_returns, cov_matrix)[1]
    
    @staticmethod
    def optimize_portfolio(mean_returns, cov_matrix, risk_free_rate=0, constraint_set=(0, 1)):
        """优化投资组合以最大化夏普比率"""
        num_assets = len(mean_returns)
        args = (mean_returns, cov_matrix, risk_free_rate)
        constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
        bounds = tuple(constraint_set for _ in range(num_assets))
        
        result = sco.minimize(FinancialCalculator.negative_sharpe_ratio, num_assets*[1./num_assets], 
                             args=args, method='SLSQP', bounds=bounds, constraints=constraints)
        return result
    
    @staticmethod
    def efficient_frontier(mean_returns, cov_matrix, returns_range):
        """计算有效前沿"""
        efficients = []
        for ret in returns_range:
            constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1},
                          {'type': 'eq', 'fun': lambda x: FinancialCalculator.portfolio_performance(x, mean_returns, cov_matrix)[0] - ret})
            bounds = tuple((0, 1) for _ in range(len(mean_returns)))
            result = sco.minimize(FinancialCalculator.portfolio_variance, len(mean_returns)*[1./len(mean_returns)], 
                                 args=(mean_returns, cov_matrix), method='SLSQP', bounds=bounds, constraints=constraints)
            efficients.append(result['fun'])
        return efficients


class StockDataFetcher(QThread):
    """增强的股票数据获取线程"""
    data_fetched = pyqtSignal(object, str)
    progress_updated = pyqtSignal(int)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, symbols, start_date, end_date, interval='1d'):
        super().__init__()
        self.symbols = symbols if isinstance(symbols, list) else [symbols]
        self.start_date = start_date
        self.end_date = end_date
        self.interval = interval
        
    def run(self):
        try:
            self.progress_updated.emit(10)
            all_data = {}
            
            for i, symbol in enumerate(self.symbols):
                self.progress_updated.emit(10 + int(70 * i / len(self.symbols)))
                stock = yf.Ticker(symbol)
                hist = stock.history(start=self.start_date, end=self.end_date, interval=self.interval)
                
                # 计算技术指标
                hist['SMA_20'] = hist['Close'].rolling(window=20).mean()
                hist['SMA_50'] = hist['Close'].rolling(window=50).mean()
                hist['EMA_12'] = hist['Close'].ewm(span=12).mean()
                hist['EMA_26'] = hist['Close'].ewm(span=26).mean()
                hist['MACD'] = hist['EMA_12'] - hist['EMA_26']
                hist['MACD_Signal'] = hist['MACD'].ewm(span=9).mean()
                hist['MACD_Histogram'] = hist['MACD'] - hist['MACD_Signal']
                hist['RSI'] = self.calculate_rsi(hist['Close'])
                
                # 计算布林带
                hist['BB_Middle'] = hist['Close'].rolling(window=20).mean()
                bb_std = hist['Close'].rolling(window=20).std()
                hist['BB_Upper'] = hist['BB_Middle'] + 2 * bb_std
                hist['BB_Lower'] = hist['BB_Middle'] - 2 * bb_std
                
                all_data[symbol] = hist
            
            self.progress_updated.emit(90)
            self.data_fetched.emit(all_data, self.interval)
            self.progress_updated.emit(100)
            
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def calculate_rsi(self, prices, period=14):
        """计算相对强弱指数(RSI)"""
        deltas = np.diff(prices)
        seed = deltas[:period+1]
        up = seed[seed >= 0].sum() / period
        down = -seed[seed < 0].sum() / period
        rs = up / down
        rsi = np.zeros_like(prices)
        rsi[:period] = 100. - 100. / (1. + rs)
        
        for i in range(period, len(prices)):
            delta = deltas[i-1]
            if delta > 0:
                up_val = delta
                down_val = 0.
            else:
                up_val = 0.
                down_val = -delta
                
            up = (up * (period - 1) + up_val) / period
            down = (down * (period - 1) + down_val) / period
            
            rs = up / down
            rsi[i] = 100. - 100. / (1. + rs)
            
        return rsi


class MplCanvas(FigureCanvas):
    """增强的Matplotlib画布"""
    
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        
    def plot_stock_data(self, data, symbol, indicators=None):
        """绘制股票数据"""
        self.fig.clear()
        
        if data is None or len(data) == 0:
            self.draw()
            return
        
        # 创建网格布局
        gs = gridspec.GridSpec(3, 1, height_ratios=[3, 1, 1])
        
        # 价格图表
        ax1 = self.fig.add_subplot(gs[0])
        ax1.plot(data.index, data['Close'], label='Close Price', linewidth=1)
        
        if indicators:
            if 'SMA_20' in indicators and 'SMA_20' in data.columns:
                ax1.plot(data.index, data['SMA_20'], label='20-Day SMA', alpha=0.7)
            if 'SMA_50' in indicators and 'SMA_50' in data.columns:
                ax1.plot(data.index, data['SMA_50'], label='50-Day SMA', alpha=0.7)
            if 'BB_Upper' in indicators and 'BB_Upper' in data.columns:
                ax1.plot(data.index, data['BB_Upper'], label='Bollinger Upper', alpha=0.5, linestyle='--')
                ax1.plot(data.index, data['BB_Middle'], label='Bollinger Middle', alpha=0.5)
                ax1.plot(data.index, data['BB_Lower'], label='Bollinger Lower', alpha=0.5, linestyle='--')
                ax1.fill_between(data.index, data['BB_Lower'], data['BB_Upper'], alpha=0.1)
        
        ax1.set_title(f'{symbol} Stock Price')
        ax1.set_ylabel('Price ($)')
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)
        
        # 成交量图表
        ax2 = self.fig.add_subplot(gs[1])
        ax2.bar(data.index, data['Volume'], alpha=0.3, color='blue')
        ax2.set_ylabel('Volume')
        ax2.grid(True, alpha=0.3)
        
        # 技术指标图表
        ax3 = self.fig.add_subplot(gs[2])
        
        if indicators:
            if 'RSI' in indicators and 'RSI' in data.columns:
                ax3.plot(data.index, data['RSI'], label='RSI', color='purple')
                ax3.axhline(70, color='r', linestyle='--', alpha=0.3)
                ax3.axhline(30, color='g', linestyle='--', alpha=0.3)
                ax3.set_ylim(0, 100)
                ax3.set_ylabel('RSI')
            
            if 'MACD' in indicators and 'MACD' in data.columns:
                ax4 = ax3.twinx()
                ax4.plot(data.index, data['MACD'], label='MACD', color='red')
                ax4.plot(data.index, data['MACD_Signal'], label='Signal', color='blue')
                ax4.bar(data.index, data['MACD_Histogram'], label='Histogram', alpha=0.3, color='gray')
                ax4.set_ylabel('MACD')
                ax4.legend(loc='upper right')
        
        ax3.set_xlabel('Date')
        ax3.grid(True, alpha=0.3)
        ax3.legend(loc='upper left')
        
        self.fig.tight_layout()
        self.draw()
    
    def plot_portfolio_analysis(self, returns, benchmark_returns=None):
        """绘制投资组合分析"""
        self.fig.clear()
        
        if returns is None or len(returns) == 0:
            self.draw()
            return
        
        # 创建网格布局
        gs = gridspec.GridSpec(2, 1, height_ratios=[2, 1])
        
        # 累积回报图表
        ax1 = self.fig.add_subplot(gs[0])
        cumulative_returns = (1 + returns).cumprod() - 1
        ax1.plot(cumulative_returns.index, cumulative_returns * 100, label='Portfolio', linewidth=2)
        
        if benchmark_returns is not None:
            benchmark_cumulative = (1 + benchmark_returns).cumprod() - 1
            ax1.plot(benchmark_cumulative.index, benchmark_cumulative * 100, label='Benchmark', alpha=0.7)
        
        ax1.set_title('Portfolio Performance')
        ax1.set_ylabel('Cumulative Return (%)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 回撤图表
        ax2 = self.fig.add_subplot(gs[1])
        peak = cumulative_returns.expanding(min_periods=1).max()
        drawdown = (cumulative_returns - peak) / (peak + 1e-10) * 100
        ax2.fill_between(drawdown.index, drawdown, 0, alpha=0.3, color='red')
        ax2.plot(drawdown.index, drawdown, color='red', linewidth=1)
        ax2.set_ylabel('Drawdown (%)')
        ax2.set_xlabel('Date')
        ax2.grid(True, alpha=0.3)
        
        self.fig.tight_layout()
        self.draw()
    
    def plot_efficient_frontier(self, mean_returns, cov_matrix, risk_free_rate=0):
        """绘制有效前沿"""
        self.fig.clear()
        
        if mean_returns is None or cov_matrix is None:
            self.draw()
            return
        
        ax = self.fig.add_subplot(111)
        
        # 生成随机投资组合
        num_portfolios = 10000
        results = np.zeros((3, num_portfolios))
        weights_record = []
        
        for i in range(num_portfolios):
            weights = np.random.random(len(mean_returns))
            weights /= np.sum(weights)
            weights_record.append(weights)
            portfolio_return, portfolio_std = FinancialCalculator.portfolio_performance(weights, mean_returns, cov_matrix)
            results[0,i] = portfolio_std
            results[1,i] = portfolio_return
            results[2,i] = (portfolio_return - risk_free_rate) / portfolio_std
        
        # 找到最大夏普比率的投资组合
        max_sharpe_idx = np.argmax(results[2])
        sdp, rp = results[0, max_sharpe_idx], results[1, max_sharpe_idx]
        max_sharpe_allocation = weights_record[max_sharpe_idx]
        
        # 找到最小方差的投资组合
        min_vol_idx = np.argmin(results[0])
        sdp_min, rp_min = results[0, min_vol_idx], results[1, min_vol_idx]
        min_vol_allocation = weights_record[min_vol_idx]
        
        # 绘制随机投资组合
        ax.scatter(results[0,:], results[1,:], c=results[2,:], cmap='viridis', marker='o', s=10, alpha=0.3)
        ax.scatter(sdp, rp, marker='*', color='r', s=500, label='Maximum Sharpe ratio')
        ax.scatter(sdp_min, rp_min, marker='*', color='g', s=500, label='Minimum volatility')
        
        # 计算并绘制有效前沿
        frontier_returns = np.linspace(rp_min, np.max(results[1,:]), 50)
        frontier_volatility = FinancialCalculator.efficient_frontier(mean_returns, cov_matrix, frontier_returns)
        
        ax.plot(frontier_volatility, frontier_returns, 'b--', linewidth=2, label='Efficient Frontier')
        
        ax.set_title('Efficient Frontier')
        ax.set_xlabel('Volatility')
        ax.set_ylabel('Expected Returns')
        ax.legend(labelspacing=0.8)
        ax.grid(True, alpha=0.3)
        
        self.fig.tight_layout()
        self.draw()
        
        return max_sharpe_allocation, min_vol_allocation
    
    def plot_monte_carlo_simulation(self, simulation_results, initial_price):
        """绘制蒙特卡洛模拟结果"""
        self.fig.clear()
        
        if simulation_results is None or len(simulation_results) == 0:
            self.draw()
            return
        
        ax = self.fig.add_subplot(111)
        
        # 绘制模拟路径
        for i in range(min(100, len(simulation_results))):  # 限制绘制路径数量
            ax.plot(simulation_results[i], lw=1, alpha=0.1, color='blue')
        
        # 计算并绘制平均路径和置信区间
        mean_path = np.mean(simulation_results, axis=0)
        upper_95 = np.percentile(simulation_results, 95, axis=0)
        lower_5 = np.percentile(simulation_results, 5, axis=0)
        
        ax.plot(mean_path, color='red', lw=2, label='Mean Path')
        ax.plot(upper_95, color='green', linestyle='--', lw=2, label='95% Confidence')
        ax.plot(lower_5, color='green', linestyle='--', lw=2, label='5% Confidence')
        
        ax.axhline(y=initial_price, color='black', linestyle='-', alpha=0.5, label='Initial Price')
        
        ax.set_title('Monte Carlo Simulation of Stock Prices')
        ax.set_xlabel('Time Steps')
        ax.set_ylabel('Stock Price ($)')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        self.fig.tight_layout()
        self.draw()
        
        return mean_path[-1], upper_95[-1], lower_5[-1]


class NPVCalculatorWidget(QWidget):
    """净现值计算器"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 输入表单
        form_layout = QFormLayout()
        
        self.discount_rate_input = QDoubleSpinBox()
        self.discount_rate_input.setRange(0, 100)
        self.discount_rate_input.setValue(10)
        self.discount_rate_input.setSuffix("%")
        
        self.cash_flow_count = QSpinBox()
        self.cash_flow_count.setRange(1, 20)
        self.cash_flow_count.setValue(5)
        self.cash_flow_count.valueChanged.connect(self.update_cash_flow_inputs)
        
        form_layout.addRow("Discount Rate:", self.discount_rate_input)
        form_layout.addRow("Number of Periods:", self.cash_flow_count)
        
        # 现金流输入区域
        self.cash_flow_layout = QVBoxLayout()
        self.cash_flow_inputs = []
        
        self.update_cash_flow_inputs()
        
        # 计算按钮和结果
        self.calculate_btn = QPushButton("Calculate NPV")
        self.calculate_btn.clicked.connect(self.calculate_npv)
        
        self.result_label = QLabel("NPV: ")
        self.result_label.setFont(QFont("Arial", 12, QFont.Bold))
        
        layout.addLayout(form_layout)
        layout.addLayout(self.cash_flow_layout)
        layout.addWidget(self.calculate_btn)
        layout.addWidget(self.result_label)
        layout.addStretch()
        
        self.setLayout(layout)
    
    def update_cash_flow_inputs(self):
        """更新现金流输入字段"""
        # 清除现有输入
        for i in reversed(range(self.cash_flow_layout.count())):
            self.cash_flow_layout.itemAt(i).widget().setParent(None)
        
        self.cash_flow_inputs = []
        periods = self.cash_flow_count.value()
        
        for i in range(periods):
            input_field = QDoubleSpinBox()
            input_field.setRange(-1000000, 1000000)
            input_field.setValue(1000 if i > 0 else -5000)
            input_field.setPrefix("$")
            
            self.cash_flow_inputs.append(input_field)
            self.cash_flow_layout.addWidget(QLabel(f"Period {i} Cash Flow:"))
            self.cash_flow_layout.addWidget(input_field)
    
    def calculate_npv(self):
        """计算净现值"""
        try:
            cash_flows = [input_field.value() for input_field in self.cash_flow_inputs]
            discount_rate = self.discount_rate_input.value() / 100
            
            npv = FinancialCalculator.calculate_npv(cash_flows, discount_rate)
            irr = FinancialCalculator.calculate_irr(cash_flows)
            payback = FinancialCalculator.calculate_payback_period(cash_flows)
            
            self.result_label.setText(f"NPV: ${npv:,.2f} | IRR: {irr*100:.2f}% | Payback: {payback} periods")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")


class OptionPricingWidget(QWidget):
    """期权定价工具"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 输入表单
        form_layout = QFormLayout()
        
        self.option_type = QComboBox()
        self.option_type.addItems(["Call", "Put"])
        
        self.stock_price = QDoubleSpinBox()
        self.stock_price.setRange(0, 10000)
        self.stock_price.setValue(100)
        self.stock_price.setPrefix("$")
        
        self.strike_price = QDoubleSpinBox()
        self.strike_price.setRange(0, 10000)
        self.strike_price.setValue(100)
        self.strike_price.setPrefix("$")
        
        self.time_to_expiry = QDoubleSpinBox()
        self.time_to_expiry.setRange(0, 10)
        self.time_to_expiry.setValue(1)
        self.time_to_expiry.setSuffix(" years")
        
        self.risk_free_rate = QDoubleSpinBox()
        self.risk_free_rate.setRange(0, 20)
        self.risk_free_rate.setValue(5)
        self.risk_free_rate.setSuffix("%")
        
        self.volatility = QDoubleSpinBox()
        self.volatility.setRange(0, 100)
        self.volatility.setValue(20)
        self.volatility.setSuffix("%")
        
        form_layout.addRow("Option Type:", self.option_type)
        form_layout.addRow("Stock Price:", self.stock_price)
        form_layout.addRow("Strike Price:", self.strike_price)
        form_layout.addRow("Time to Expiry:", self.time_to_expiry)
        form_layout.addRow("Risk-Free Rate:", self.risk_free_rate)
        form_layout.addRow("Volatility:", self.volatility)
        
        # 计算按钮
        self.calculate_btn = QPushButton("Calculate Option Price")
        self.calculate_btn.clicked.connect(self.calculate_option_price)
        
        # 结果标签
        self.result_label = QLabel("Option Price: ")
        self.result_label.setFont(QFont("Arial", 12, QFont.Bold))
        
        # 希腊值标签
        self.greeks_label = QLabel("Greeks: ")
        
        layout.addLayout(form_layout)
        layout.addWidget(self.calculate_btn)
        layout.addWidget(self.result_label)
        layout.addWidget(self.greeks_label)
        layout.addStretch()
        
        self.setLayout(layout)
    
    def calculate_option_price(self):
        """计算期权价格"""
        try:
            S = self.stock_price.value()
            K = self.strike_price.value()
            T = self.time_to_expiry.value()
            r = self.risk_free_rate.value() / 100
            sigma = self.volatility.value() / 100
            
            if self.option_type.currentText() == "Call":
                price = FinancialCalculator.black_scholes_call(S, K, T, r, sigma)
            else:
                price = FinancialCalculator.black_scholes_put(S, K, T, r, sigma)
            
            self.result_label.setText(f"Option Price: ${price:.2f}")
            
            # 计算希腊值（简化版）
            if T > 0:
                d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
                
                if self.option_type.currentText() == "Call":
                    delta = stats.norm.cdf(d1)
                    gamma = stats.norm.pdf(d1) / (S * sigma * np.sqrt(T))
                    theta = (-S * stats.norm.pdf(d1) * sigma / (2 * np.sqrt(T)) - 
                            r * K * np.exp(-r * T) * stats.norm.cdf(d1 - sigma * np.sqrt(T)))
                    vega = S * stats.norm.pdf(d1) * np.sqrt(T) / 100
                    rho = K * T * np.exp(-r * T) * stats.norm.cdf(d1 - sigma * np.sqrt(T)) / 100
                else:
                    delta = stats.norm.cdf(d1) - 1
                    gamma = stats.norm.pdf(d1) / (S * sigma * np.sqrt(T))
                    theta = (-S * stats.norm.pdf(d1) * sigma / (2 * np.sqrt(T)) + 
                            r * K * np.exp(-r * T) * stats.norm.cdf(-d1 + sigma * np.sqrt(T)))
                    vega = S * stats.norm.pdf(d1) * np.sqrt(T) / 100
                    rho = -K * T * np.exp(-r * T) * stats.norm.cdf(-d1 + sigma * np.sqrt(T)) / 100
                
                self.greeks_label.setText(
                    f"Greeks: Delta: {delta:.4f}, Gamma: {gamma:.6f}, Theta: {theta:.4f}, "
                    f"Vega: {vega:.4f}, Rho: {rho:.4f}"
                )
            else:
                self.greeks_label.setText("Greeks: N/A (Expired)")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")


class MonteCarloWidget(QWidget):
    """蒙特卡洛模拟工具"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 输入表单
        form_layout = QFormLayout()
        
        self.initial_price = QDoubleSpinBox()
        self.initial_price.setRange(0, 10000)
        self.initial_price.setValue(100)
        self.initial_price.setPrefix("$")
        
        self.expected_return = QDoubleSpinBox()
        self.expected_return.setRange(-100, 100)
        self.expected_return.setValue(10)
        self.expected_return.setSuffix("%")
        
        self.volatility = QDoubleSpinBox()
        self.volatility.setRange(0, 100)
        self.volatility.setValue(20)
        self.volatility.setSuffix("%")
        
        self.time_horizon = QDoubleSpinBox()
        self.time_horizon.setRange(0, 50)
        self.time_horizon.setValue(1)
        self.time_horizon.setSuffix(" years")
        
        self.num_simulations = QSpinBox()
        self.num_simulations.setRange(10, 10000)
        self.num_simulations.setValue(1000)
        
        self.num_steps = QSpinBox()
        self.num_steps.setRange(10, 1000)
        self.num_steps.setValue(252)
        
        form_layout.addRow("Initial Price:", self.initial_price)
        form_layout.addRow("Expected Return:", self.expected_return)
        form_layout.addRow("Volatility:", self.volatility)
        form_layout.addRow("Time Horizon:", self.time_horizon)
        form_layout.addRow("Number of Simulations:", self.num_simulations)
        form_layout.addRow("Number of Steps:", self.num_steps)
        
        # 计算按钮
        self.simulate_btn = QPushButton("Run Simulation")
        self.simulate_btn.clicked.connect(self.run_simulation)
        
        # 图表
        self.chart = MplCanvas(self, width=8, height=6, dpi=100)
        
        # 结果标签
        self.result_label = QLabel("Simulation Results: ")
        self.result_label.setFont(QFont("Arial", 12, QFont.Bold))
        
        layout.addLayout(form_layout)
        layout.addWidget(self.simulate_btn)
        layout.addWidget(self.chart)
        layout.addWidget(self.result_label)
        
        self.setLayout(layout)
    
    def run_simulation(self):
        """运行蒙特卡洛模拟"""
        try:
            S0 = self.initial_price.value()
            mu = self.expected_return.value() / 100
            sigma = self.volatility.value() / 100
            T = self.time_horizon.value()
            num_simulations = self.num_simulations.value()
            num_steps = self.num_steps.value()
            
            simulation_results = FinancialCalculator.monte_carlo_simulation(
                S0, mu, sigma, T, num_simulations, num_steps
            )
            
            mean_final, upper_95, lower_5 = self.chart.plot_monte_carlo_simulation(simulation_results, S0)
            
            self.result_label.setText(
                f"Simulation Results: Mean Final Price: ${mean_final:.2f}, "
                f"95% Confidence: ${upper_95:.2f}, 5% Confidence: ${lower_5:.2f}"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")


class PortfolioOptimizerWidget(QWidget):
    """投资组合优化工具"""
    
    def __init__(self):
        super().__init__()
        self.returns_data = None
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 输入区域
        input_layout = QHBoxLayout()
        
        self.symbol_input = QLineEdit()
        self.symbol_input.setPlaceholderText("Enter symbols (e.g., AAPL,MSFT,GOOGL)")
        
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addYears(-3))
        self.start_date.setCalendarPopup(True)
        
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        
        self.fetch_btn = QPushButton("Fetch Data")
        self.fetch_btn.clicked.connect(self.fetch_data)
        
        input_layout.addWidget(QLabel("Symbols:"))
        input_layout.addWidget(self.symbol_input)
        input_layout.addWidget(QLabel("Start Date:"))
        input_layout.addWidget(self.start_date)
        input_layout.addWidget(QLabel("End Date:"))
        input_layout.addWidget(self.end_date)
        input_layout.addWidget(self.fetch_btn)
        
        # 优化按钮
        self.optimize_btn = QPushButton("Optimize Portfolio")
        self.optimize_btn.clicked.connect(self.optimize_portfolio)
        self.optimize_btn.setEnabled(False)
        
        # 图表
        self.chart = MplCanvas(self, width=8, height=6, dpi=100)
        
        # 结果表格
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(4)
        self.result_table.setHorizontalHeaderLabels(["Symbol", "Weight", "Expected Return", "Volatility"])
        
        # 风险指标
        risk_layout = QHBoxLayout()
        
        self.portfolio_return_label = QLabel("Expected Return: ")
        self.portfolio_volatility_label = QLabel("Volatility: ")
        self.sharpe_ratio_label = QLabel("Sharpe Ratio: ")
        self.var_label = QLabel("VaR (95%): ")
        self.cvar_label = QLabel("CVaR (95%): ")
        
        risk_layout.addWidget(self.portfolio_return_label)
        risk_layout.addWidget(self.portfolio_volatility_label)
        risk_layout.addWidget(self.sharpe_ratio_label)
        risk_layout.addWidget(self.var_label)
        risk_layout.addWidget(self.cvar_label)
        
        layout.addLayout(input_layout)
        layout.addWidget(self.optimize_btn)
        layout.addWidget(self.chart)
        layout.addWidget(self.result_table)
        layout.addLayout(risk_layout)
        
        self.setLayout(layout)
    
    def fetch_data(self):
        """获取股票数据"""
        symbols = [s.strip() for s in self.symbol_input.text().split(',')]
        if not symbols:
            QMessageBox.warning(self, "Warning", "Please enter at least one stock symbol")
            return
        
        start_date = self.start_date.date().toString("yyyy-MM-dd")
        end_date = self.end_date.date().toString("yyyy-MM-dd")
        
        self.worker = StockDataFetcher(symbols, start_date, end_date)
        self.worker.data_fetched.connect(self.on_data_fetched)
        self.worker.error_occurred.connect(self.on_error)
        self.worker.start()
    
    def on_data_fetched(self, data, interval):
        """处理获取到的数据"""
        self.returns_data = {}
        
        for symbol, hist in data.items():
            # 计算日回报率
            returns = hist['Close'].pct_change().dropna()
            self.returns_data[symbol] = returns
        
        self.optimize_btn.setEnabled(True)
        QMessageBox.information(self, "Success", "Data fetched successfully")
    
    def on_error(self, error_msg):
        """处理错误"""
        QMessageBox.critical(self, "Error", f"Failed to fetch data: {error_msg}")
    
    def optimize_portfolio(self):
        """优化投资组合"""
        try:
            if not self.returns_data:
                QMessageBox.warning(self, "Warning", "Please fetch data first")
                return
            
            # 准备数据
            returns_df = pd.DataFrame(self.returns_data)
            mean_returns = returns_df.mean()
            cov_matrix = returns_df.cov()
            
            # 优化投资组合
            risk_free_rate = 0.02  # 假设无风险利率为2%
            result = FinancialCalculator.optimize_portfolio(mean_returns, cov_matrix, risk_free_rate)
            optimal_weights = result.x
            
            # 绘制有效前沿
            max_sharpe_allocation, min_vol_allocation = self.chart.plot_efficient_frontier(
                mean_returns, cov_matrix, risk_free_rate
            )
            
            # 更新结果表格
            symbols = list(self.returns_data.keys())
            self.result_table.setRowCount(len(symbols))
            
            for i, symbol in enumerate(symbols):
                self.result_table.setItem(i, 0, QTableWidgetItem(symbol))
                self.result_table.setItem(i, 1, QTableWidgetItem(f"{optimal_weights[i]*100:.2f}%"))
                self.result_table.setItem(i, 2, QTableWidgetItem(f"{mean_returns[i]*252*100:.2f}%"))
                self.result_table.setItem(i, 3, QTableWidgetItem(f"{np.sqrt(cov_matrix.iloc[i,i])*np.sqrt(252)*100:.2f}%"))
            
            # 计算投资组合绩效
            portfolio_return = np.sum(mean_returns * optimal_weights) * 252
            portfolio_volatility = np.sqrt(np.dot(optimal_weights.T, np.dot(cov_matrix, optimal_weights))) * np.sqrt(252)
            sharpe_ratio = (portfolio_return - risk_free_rate) / portfolio_volatility
            
            # 计算投资组合回报
            portfolio_returns = (returns_df * optimal_weights).sum(axis=1)
            
            # 计算风险指标
            var = FinancialCalculator.calculate_var(portfolio_returns)
            cvar = FinancialCalculator.calculate_cvar(portfolio_returns)
            
            # 更新风险指标标签
            self.portfolio_return_label.setText(f"Expected Return: {portfolio_return*100:.2f}%")
            self.portfolio_volatility_label.setText(f"Volatility: {portfolio_volatility*100:.2f}%")
            self.sharpe_ratio_label.setText(f"Sharpe Ratio: {sharpe_ratio:.2f}")
            self.var_label.setText(f"VaR (95%): {var*100:.2f}%")
            self.cvar_label.setText(f"CVaR (95%): {cvar*100:.2f}%")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")


class RiskAnalysisWidget(QWidget):
    """风险分析工具"""
    
    def __init__(self):
        super().__init__()
        self.returns_data = None
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 输入区域
        input_layout = QHBoxLayout()
        
        self.symbol_input = QLineEdit()
        self.symbol_input.setPlaceholderText("Enter symbols (e.g., AAPL,MSFT,GOOGL)")
        
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addYears(-3))
        self.start_date.setCalendarPopup(True)
        
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        
        self.fetch_btn = QPushButton("Fetch Data")
        self.fetch_btn.clicked.connect(self.fetch_data)
        
        input_layout.addWidget(QLabel("Symbols:"))
        input_layout.addWidget(self.symbol_input)
        input_layout.addWidget(QLabel("Start Date:"))
        input_layout.addWidget(self.start_date)
        input_layout.addWidget(QLabel("End Date:"))
        input_layout.addWidget(self.end_date)
        input_layout.addWidget(self.fetch_btn)
        
        # 分析按钮
        self.analyze_btn = QPushButton("Analyze Risk")
        self.analyze_btn.clicked.connect(self.analyze_risk)
        self.analyze_btn.setEnabled(False)
        
        # 置信水平选择
        confidence_layout = QHBoxLayout()
        confidence_layout.addWidget(QLabel("Confidence Level:"))
        
        self.confidence_slider = QSlider(Qt.Horizontal)
        self.confidence_slider.setRange(90, 99)
        self.confidence_slider.setValue(95)
        self.confidence_slider.valueChanged.connect(self.update_confidence_label)
        
        self.confidence_label = QLabel("95%")
        
        confidence_layout.addWidget(self.confidence_slider)
        confidence_layout.addWidget(self.confidence_label)
        
        # 结果表格
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(5)
        self.result_table.setHorizontalHeaderLabels(["Symbol", "Volatility", "VaR", "CVaR", "Beta"])
        
        layout.addLayout(input_layout)
        layout.addLayout(confidence_layout)
        layout.addWidget(self.analyze_btn)
        layout.addWidget(self.result_table)
        
        self.setLayout(layout)
    
    def update_confidence_label(self):
        """更新置信水平标签"""
        self.confidence_label.setText(f"{self.confidence_slider.value()}%")
    
    def fetch_data(self):
        """获取股票数据"""
        symbols = [s.strip() for s in self.symbol_input.text().split(',')]
        if not symbols:
            QMessageBox.warning(self, "Warning", "Please enter at least one stock symbol")
            return
        
        start_date = self.start_date.date().toString("yyyy-MM-dd")
        end_date = self.end_date.date().toString("yyyy-MM-dd")
        
        self.worker = StockDataFetcher(symbols, start_date, end_date)
        self.worker.data_fetched.connect(self.on_data_fetched)
        self.worker.error_occurred.connect(self.on_error)
        self.worker.start()
    
    def on_data_fetched(self, data, interval):
        """处理获取到的数据"""
        self.returns_data = {}
        
        for symbol, hist in data.items():
            # 计算日回报率
            returns = hist['Close'].pct_change().dropna()
            self.returns_data[symbol] = returns
        
        self.analyze_btn.setEnabled(True)
        QMessageBox.information(self, "Success", "Data fetched successfully")
    
    def on_error(self, error_msg):
        """处理错误"""
        QMessageBox.critical(self, "Error", f"Failed to fetch data: {error_msg}")
    
    def analyze_risk(self):
        """分析风险"""
        try:
            if not self.returns_data:
                QMessageBox.warning(self, "Warning", "Please fetch data first")
                return
            
            confidence_level = self.confidence_slider.value() / 100
            
            # 准备数据
            returns_df = pd.DataFrame(self.returns_data)
            
            # 计算市场指数（假设第一个股票作为市场代理）
            market_symbol = list(self.returns_data.keys())[0]
            market_returns = returns_df[market_symbol]
            
            # 更新结果表格
            symbols = list(self.returns_data.keys())
            self.result_table.setRowCount(len(symbols))
            
            for i, symbol in enumerate(symbols):
                returns = returns_df[symbol]
                
                # 计算年化波动率
                volatility = returns.std() * np.sqrt(252)
                
                # 计算VaR和CVaR
                var = FinancialCalculator.calculate_var(returns, confidence_level)
                cvar = FinancialCalculator.calculate_cvar(returns, confidence_level)
                
                # 计算Beta（如果有多只股票）
                if len(symbols) > 1 and symbol != market_symbol:
                    cov = returns.cov(market_returns)
                    market_var = market_returns.var()
                    beta = cov / market_var
                else:
                    beta = 1.0
                
                self.result_table.setItem(i, 0, QTableWidgetItem(symbol))
                self.result_table.setItem(i, 1, QTableWidgetItem(f"{volatility*100:.2f}%"))
                self.result_table.setItem(i, 2, QTableWidgetItem(f"{var*100:.2f}%"))
                self.result_table.setItem(i, 3, QTableWidgetItem(f"{cvar*100:.2f}%"))
                self.result_table.setItem(i, 4, QTableWidgetItem(f"{beta:.2f}"))
            
            # 调整列宽
            header = self.result_table.horizontalHeader()
            for i in range(5):
                header.setSectionResizeMode(i, QHeaderView.Stretch)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")


class FinancialToolsApp(QMainWindow):
    """财务工具主应用"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Advanced Financial Tools")
        self.setGeometry(100, 100, 1400, 900)
        
        # 创建标签页
        self.tabs = QTabWidget()
        
        # 添加各个工具标签页
        self.npv_calculator = NPVCalculatorWidget()
        self.option_pricing = OptionPricingWidget()
        self.monte_carlo = MonteCarloWidget()
        self.portfolio_optimizer = PortfolioOptimizerWidget()
        self.risk_analysis = RiskAnalysisWidget()
        
        self.tabs.addTab(self.npv_calculator, "NPV Calculator")
        self.tabs.addTab(self.option_pricing, "Option Pricing")
        self.tabs.addTab(self.monte_carlo, "Monte Carlo Simulation")
        self.tabs.addTab(self.portfolio_optimizer, "Portfolio Optimizer")
        self.tabs.addTab(self.risk_analysis, "Risk Analysis")
        
        self.setCentralWidget(self.tabs)
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 创建状态栏
        self.statusBar().showMessage("Ready")
        
        # 创建定时器更新市场数据
        self.market_timer = QTimer()
        self.market_timer.timeout.connect(self.update_market_data)
        self.market_timer.start(60000)  # 每分钟更新一次
        
    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('File')
        
        export_action = file_menu.addAction('Export Data')
        export_action.triggered.connect(self.export_data)
        
        exit_action = file_menu.addAction('Exit')
        exit_action.triggered.connect(self.close)
        
        # 工具菜单
        tools_menu = menubar.addMenu('Tools')
        
        update_action = tools_menu.addAction('Update Market Data')
        update_action.triggered.connect(self.update_market_data)
        
        # 帮助菜单
        help_menu = menubar.addMenu('Help')
        
        about_action = help_menu.addAction('About')
        about_action.triggered.connect(self.show_about)
    
    def export_data(self):
        """导出数据"""
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Export Data", "", "CSV Files (*.csv);;Excel Files (*.xlsx)", options=options
        )
        
        if file_name:
            # 这里可以根据当前激活的标签页导出相应的数据
            current_tab = self.tabs.currentWidget()
            if hasattr(current_tab, 'export_data'):
                current_tab.export_data(file_name)
            else:
                QMessageBox.information(self, "Info", "Export functionality not implemented for this tab")
    
    def update_market_data(self):
        """更新市场数据"""
        # 这里可以添加实时市场数据更新的逻辑
        self.statusBar().showMessage(f"Market data updated at {datetime.now().strftime('%H:%M:%S')}")
    
    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(self, "About Financial Tools", 
                         "Advanced Financial Tools\n\n"
                         "A comprehensive financial analysis toolkit built with PyQt5.\n\n"
                         "Features include:\n"
                         "- NPV and IRR calculations\n"
                         "- Option pricing with Black-Scholes model\n"
                         "- Monte Carlo simulations\n"
                         "- Portfolio optimization\n"
                         "- Risk analysis (VaR, CVaR, Beta)\n"
                         "- Technical analysis indicators\n\n"
                         "Version 2.0")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle("Fusion")
    
    # 自定义调色板
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(240, 240, 240))
    palette.setColor(QPalette.WindowText, QColor(0, 0, 0))
    app.setPalette(palette)
    
    window = FinancialToolsApp()
    window.show()
    
    sys.exit(app.exec_())