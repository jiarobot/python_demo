import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.dates import DateFormatter, MonthLocator
import seaborn as sns
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QTabWidget, QPushButton, QComboBox, QLabel, QSlider, QSplitter,
                             QGroupBox, QFormLayout, QSpinBox, QDoubleSpinBox, QCheckBox,
                             QFileDialog, QMessageBox, QTableWidget, QTableWidgetItem,
                             QHeaderView, QToolBar, QStatusBar, QAction, QDockWidget,
                             QTextEdit, QProgressBar, QTreeWidget, QTreeWidgetItem,
                             QListView, QListWidget, QListWidgetItem, QSizePolicy, QStyle)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QDateTime
from PyQt5.QtGui import QIcon, QFont, QColor, QPalette, QLinearGradient, QGradient, QPixmap
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from plotly.offline import plot
from sklearn.cluster import KMeans, DBSCAN
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import r2_score, mean_squared_error
from sklearn.decomposition import PCA
from sklearn.feature_selection import SelectKBest, f_regression
import scipy.stats as stats
from dateutil.relativedelta import relativedelta
import warnings
warnings.filterwarnings('ignore')

# 添加新的导入
import plotly.express as px
import networkx as nx
from wordcloud import WordCloud
from textblob import TextBlob
import requests
from io import StringIO
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.holtwinters import ExponentialSmoothing
import pmdarima as pm
from scipy import signal
from scipy.optimize import curve_fit


class DataManager(QThread):
    """数据管理线程，负责数据加载和处理"""
    progress_updated = pyqtSignal(int)
    data_loaded = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.data_sources = {}
        
    def run(self):
        """运行数据加载过程"""
        self.progress_updated.emit(0)
        
        # 模拟数据加载过程
        data_generator = AdvancedMarketingDataGenerator()
        
        self.progress_updated.emit(25)
        self.data_sources['customers'] = data_generator.generate_customer_data()
        
        self.progress_updated.emit(50)
        self.data_sources['transactions'] = data_generator.generate_transaction_data(
            self.data_sources['customers'])
        
        self.progress_updated.emit(75)
        self.data_sources['campaigns'] = data_generator.generate_campaign_data()
        
        self.progress_updated.emit(90)
        self.data_sources['social'] = data_generator.generate_social_media_data()
        
        self.progress_updated.emit(100)
        self.data_loaded.emit(self.data_sources)


class AdvancedMarketingDataGenerator:
    """增强版营销数据生成器"""
    
    def __init__(self):
        self.n_customers = 5000
        self.n_products = 8
        self.n_channels = 6
        self.n_campaigns = 6
        self.channels = ['Google Ads', 'Facebook', 'Email', 'Organic', 'Instagram', 'Referral']
        self.products = ['Product A', 'Product B', 'Product C', 'Product D', 
                         'Product E', 'Product F', 'Product G', 'Product H']
        self.locations = ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix',
                         'Philadelphia', 'San Antonio', 'San Diego', 'Dallas', 'San Jose']
        
    def generate_customer_data(self):
        """生成增强版客户数据"""
        np.random.seed(42)
        
        # 生成客户基本数据
        customer_ids = [f'CUST_{i:05d}' for i in range(1, self.n_customers + 1)]
        ages = np.random.normal(35, 12, self.n_customers).astype(int)
        ages = np.clip(ages, 18, 80)
        genders = np.random.choice(['Male', 'Female'], self.n_customers, p=[0.48, 0.52])
        locations = np.random.choice(self.locations, self.n_customers)
        
        # 生成客户价值数据 - 使用更复杂的分布
        segments = np.random.choice(['Low', 'Medium', 'High'], self.n_customers, p=[0.6, 0.3, 0.1])
        customer_value = np.zeros(self.n_customers)
        
        for i, segment in enumerate(segments):
            if segment == 'Low':
                customer_value[i] = np.random.lognormal(2.5, 0.7)
            elif segment == 'Medium':
                customer_value[i] = np.random.lognormal(3.5, 0.6)
            else:
                customer_value[i] = np.random.lognormal(4.5, 0.5)
                
        customer_value = np.round(customer_value * 100, 2)
        
        # 生成首次购买日期
        start_date = datetime(2021, 1, 1)
        end_date = datetime(2023, 12, 31)
        date_range = (end_date - start_date).days
        first_purchase_dates = [start_date + timedelta(days=np.random.randint(0, date_range)) 
                               for _ in range(self.n_customers)]
        
        # 生成客户生命周期状态
        tenure_days = [(datetime(2023, 12, 31) - date).days for date in first_purchase_dates]
        ltv_stage = []
        for tenure in tenure_days:
            if tenure < 90:
                ltv_stage.append('New')
            elif tenure < 365:
                ltv_stage.append('Growing')
            else:
                ltv_stage.append('Established')
        
        # 创建DataFrame
        df = pd.DataFrame({
            'customer_id': customer_ids,
            'age': ages,
            'gender': genders,
            'location': locations,
            'customer_value': customer_value,
            'first_purchase_date': first_purchase_dates,
            'segment': segments,
            'ltv_stage': ltv_stage
        })
        
        return df
    
    def generate_transaction_data(self, customer_df):
        """生成增强版交易数据"""
        transactions = []
        
        for _, customer in customer_df.iterrows():
            # 基于客户价值确定交易频率
            base_frequency = 5 + (customer['customer_value'] / 100)
            n_transactions = max(1, int(np.random.poisson(base_frequency)))
            
            for i in range(n_transactions):
                # 基于首次购买日期生成交易日期
                if customer['ltv_stage'] == 'New':
                    days_after_first = np.random.exponential(30)
                elif customer['ltv_stage'] == 'Growing':
                    days_after_first = np.random.exponential(90)
                else:
                    days_after_first = np.random.exponential(180)
                    
                days_after_first = min(days_after_first, 365 * 2)  # 不超过两年
                transaction_date = customer['first_purchase_date'] + timedelta(days=int(days_after_first))
                
                if transaction_date > datetime(2023, 12, 31):
                    continue  # 跳过2023年之后的日期
                
                # 选择产品和渠道 - 基于客户细分
                if customer['segment'] == 'High':
                    product_weights = [0.1, 0.1, 0.15, 0.15, 0.15, 0.1, 0.1, 0.15]
                    channel_weights = [0.2, 0.15, 0.1, 0.2, 0.2, 0.15]
                elif customer['segment'] == 'Medium':
                    product_weights = [0.15, 0.15, 0.2, 0.1, 0.1, 0.1, 0.1, 0.1]
                    channel_weights = [0.25, 0.2, 0.15, 0.15, 0.15, 0.1]
                else:
                    product_weights = [0.2, 0.2, 0.15, 0.1, 0.1, 0.1, 0.1, 0.05]
                    channel_weights = [0.3, 0.25, 0.1, 0.2, 0.1, 0.05]
                
                product = np.random.choice(self.products, p=product_weights)
                channel = np.random.choice(self.channels, p=channel_weights)
                
                # 生成交易金额（基于客户价值和产品）
                base_value = customer['customer_value'] / 20
                if product in ['Product A', 'Product H']:
                    base_value *= 1.5  # 高端产品
                elif product in ['Product F', 'Product G']:
                    base_value *= 0.8  # 低端产品
                    
                amount = np.random.lognormal(np.log(base_value), 0.5)
                amount = round(amount, 2)
                
                # 添加季节性影响
                month = transaction_date.month
                if month in [11, 12]:  # 假日季
                    amount *= 1.3
                elif month in [6, 7]:  # 夏季
                    amount *= 1.1
                
                transactions.append({
                    'customer_id': customer['customer_id'],
                    'transaction_date': transaction_date,
                    'product': product,
                    'channel': channel,
                    'amount': amount
                })
        
        return pd.DataFrame(transactions)
    
    def generate_campaign_data(self):
        """生成增强版营销活动数据"""
        campaigns = []
        campaign_names = [
            'Spring Sale 2022', 
            'Summer Promotion 2022',
            'Back to School 2022',
            'Holiday Special 2022',
            'New Year Kickoff 2023',
            'Spring Sale 2023', 
            'Summer Promotion 2023',
            'Back to School 2023',
            'Holiday Special 2023'
        ]
        
        for i, name in enumerate(campaign_names[:self.n_campaigns]):
            start_month = 3 + (i % 4) * 3
            start_year = 2022 if i < 4 else 2023
            start_date = datetime(start_year, start_month, 1)
            end_date = start_date + timedelta(days=30)
            
            # 生成本次活动的渠道支出
            channel_spend = {}
            total_budget = np.random.uniform(5000, 20000)
            
            # 分配渠道预算 - 随时间变化
            if start_year == 2022:
                channel_weights = [0.3, 0.25, 0.2, 0.15, 0.05, 0.05]  # 2022年权重
            else:
                channel_weights = [0.25, 0.2, 0.15, 0.15, 0.15, 0.1]  # 2023年权重
            
            for j, channel in enumerate(self.channels):
                channel_spend[channel] = round(total_budget * channel_weights[j], 2)
            
            # 添加活动效果指标
            expected_roi = np.random.uniform(1.5, 4.0)
            expected_conversion = np.random.uniform(0.02, 0.08)
            
            campaigns.append({
                'campaign_id': i + 1,
                'name': name,
                'start_date': start_date,
                'end_date': end_date,
                'total_budget': total_budget,
                'expected_roi': expected_roi,
                'expected_conversion': expected_conversion,
                **channel_spend
            })
        
        return pd.DataFrame(campaigns)
    
    def generate_social_media_data(self):
        """生成社交媒体数据"""
        # 生成日期范围
        dates = pd.date_range(start='2022-01-01', end='2023-12-31', freq='D')
        
        # 生成基本指标
        np.random.seed(42)
        n_days = len(dates)
        
        # 创建基本时间序列
        base_engagements = 1000
        engagements = base_engagements + np.random.poisson(200, n_days)
        
        # 添加趋势
        trend = np.linspace(0, 500, n_days)
        engagements = engagements + trend
        
        # 添加季节性
        day_of_week = dates.dayofweek
        weekly_seasonality = 100 * np.sin(2 * np.pi * day_of_week / 7)
        
        day_of_year = dates.dayofyear
        yearly_seasonality = 200 * np.sin(2 * np.pi * day_of_year / 365)
        
        engagements = engagements + weekly_seasonality + yearly_seasonality
        
        # 添加活动峰值
        campaign_weeks = [10, 25, 40, 55, 75, 90]  # 活动周
        engagements_values = engagements.values if hasattr(engagements, 'values') else engagements
        original_index = engagements.index if hasattr(engagements, 'index') else pd.RangeIndex(len(engagements))

        for week in campaign_weeks:
            idx = week * 7
            if idx < n_days:
                engagements_values[idx:idx+7] = engagements_values[idx:idx+7] * 1.5

        engagements = pd.Series(engagements_values, index=original_index)
        
        # 生成其他指标
        impressions = engagements * np.random.uniform(3, 5, n_days)
        clicks = engagements * np.random.uniform(0.1, 0.2, n_days)
        conversions = clicks * np.random.uniform(0.02, 0.05, n_days)
        
        # 生成情感分析数据
        sentiment = np.random.normal(0.6, 0.15, n_days)
        sentiment = np.clip(sentiment, 0.1, 0.95)
        
        # 创建DataFrame
        df = pd.DataFrame({
            'date': dates,
            'engagements': engagements.astype(int),
            'impressions': impressions.astype(int),
            'clicks': clicks.astype(int),
            'conversions': conversions.astype(int),
            'sentiment': sentiment
        })
        
        return df

class AdvancedMplCanvas(FigureCanvas):
    """增强版Matplotlib画布类"""
    
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        
        # 设置样式
        self.fig.patch.set_facecolor('#F0F0F0')
        
        self.fig.tight_layout()


class AdvancedRevenueTrendWidget(AdvancedMplCanvas):
    """增强版收入趋势可视化组件"""
    
    def __init__(self, transaction_data, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.transaction_data = transaction_data
        self.axes = self.fig.subplots(2, 1, gridspec_kw={'height_ratios': [2, 1]})
        self.update_chart()
        
    def update_chart(self, frequency='M', product_filter='All', show_forecast=False):
        """更新图表"""
        for ax in self.axes:
            ax.clear()
        
        # 过滤数据
        data = self.transaction_data.copy()
        if product_filter != 'All':
            data = data[data['product'] == product_filter]
        
        # 按时间频率聚合数据
        data['transaction_date'] = pd.to_datetime(data['transaction_date'])
        data.set_index('transaction_date', inplace=True)
        
        if frequency == 'D':
            revenue = data['amount'].resample('D').sum()
            date_format = DateFormatter("%m/%d")
            title_suffix = "Daily"
        elif frequency == 'W':
            revenue = data['amount'].resample('W').sum()
            date_format = DateFormatter("%m/%d")
            title_suffix = "Weekly"
        else:  # 默认按月
            revenue = data['amount'].resample('M').sum()
            date_format = DateFormatter("%b %Y")
            title_suffix = "Monthly"
        
        # 绘制趋势线
        self.axes[0].plot(revenue.index, revenue.values, marker='o', linewidth=2, 
                         markersize=4, color='#2E86AB')
        self.axes[0].xaxis.set_major_formatter(date_format)
        self.axes[0].set_title(f"Revenue Trend ({title_suffix})")
        self.axes[0].set_ylabel("Revenue ($)")
        self.axes[0].grid(True, linestyle='--', alpha=0.7)
        
        # 添加移动平均线
        window_size = 3 if frequency == 'M' else 7
        moving_avg = revenue.rolling(window=window_size).mean()
        self.axes[0].plot(moving_avg.index, moving_avg.values, 'r--', linewidth=2, 
                         label=f'{window_size}-period MA')
        self.axes[0].legend()
        
        # 添加预测（如果启用）
        if show_forecast and len(revenue) > 12:
            self.add_forecast(revenue, frequency)
        
        # 在下方面板绘制YoY增长率
        yoy_growth = revenue.pct_change(periods=12) * 100  # 12个月/周期前的比较
        self.axes[1].bar(yoy_growth.index, yoy_growth.values, alpha=0.7, color='#A23B72')
        self.axes[1].axhline(y=0, color='k', linestyle='-', alpha=0.3)
        self.axes[1].set_ylabel("YoY Growth (%)")
        self.axes[1].grid(True, linestyle='--', alpha=0.7)
        self.axes[1].xaxis.set_major_formatter(date_format)
        
        # 旋转日期标签以避免重叠
        for ax in self.axes:
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        
        self.fig.tight_layout()
        self.draw()
    
    def add_forecast(self, revenue, frequency):
        """添加简单预测"""
        # 使用线性回归进行简单预测
        X = np.array(range(len(revenue))).reshape(-1, 1)
        y = revenue.values
        
        model = LinearRegression()
        model.fit(X, y)
        
        # 预测未来6个周期
        future_X = np.array(range(len(revenue), len(revenue) + 6)).reshape(-1, 1)
        future_y = model.predict(future_X)
        
        # 生成未来日期
        last_date = revenue.index[-1]
        if frequency == 'M':
            future_dates = [last_date + relativedelta(months=i+1) for i in range(6)]
        elif frequency == 'W':
            future_dates = [last_date + timedelta(weeks=i+1) for i in range(6)]
        else:
            future_dates = [last_date + timedelta(days=i+1) for i in range(6)]
        
        # 绘制预测
        self.axes[0].plot(future_dates, future_y, 'g--', linewidth=2, label='Forecast')
        self.axes[0].legend()


class AdvancedChannelPerformanceWidget(AdvancedMplCanvas):
    """增强版渠道性能可视化组件"""
    
    def __init__(self, transaction_data, campaign_data, *args, **kwargs):
        # 设置更大的图形尺寸
        kwargs['width'] = 12
        kwargs['height'] = 5
        super().__init__(*args, **kwargs)
        self.transaction_data = transaction_data
        self.campaign_data = campaign_data
        # 移除 figsize 参数
        self.axes = self.fig.subplots(1, 2)
        self.update_chart()
        
    def update_chart(self, metric='ROI', show_breakdown=False):
        """更新图表"""
        for ax in self.axes:
            ax.clear()
        
        # 计算每个渠道的收入
        channel_revenue = self.transaction_data.groupby('channel')['amount'].sum()
        channels = channel_revenue.index
        
        # 计算每个渠道的总支出
        channel_spend = {}
        for channel in channels:
            col_name = channel.lower().replace(' ', '_')
            if col_name in self.campaign_data.columns:
                channel_spend[channel] = self.campaign_data[col_name].sum()
            else:
                channel_spend[channel] = 0
        
        # 计算所选指标
        if metric == 'ROI':
            values = [(channel_revenue[channel] - channel_spend[channel]) / max(1, channel_spend[channel]) 
                     for channel in channels]
            ylabel = "Return on Investment (ROI)"
            formatter = lambda x: f'{x:.1%}'
        elif metric == 'Revenue':
            values = [channel_revenue[channel] for channel in channels]
            ylabel = "Revenue ($)"
            formatter = lambda x: f'${x:,.0f}'
        elif metric == 'Spend':
            values = [channel_spend[channel] for channel in channels]
            ylabel = "Spend ($)"
            formatter = lambda x: f'${x:,.0f}'
        else:  # CAC
            # 计算客户获取成本 - 简化版
            n_customers = self.transaction_data.groupby('channel')['customer_id'].nunique()
            values = [channel_spend[channel] / max(1, n_customers[channel]) for channel in channels]
            ylabel = "Customer Acquisition Cost ($)"
            formatter = lambda x: f'${x:,.0f}'
        
        # 创建条形图
        x_pos = np.arange(len(channels))
        colors = plt.cm.Set3(np.linspace(0, 1, len(channels)))
        bars = self.axes[0].bar(x_pos, values, color=colors)
        
        # 添加数值标签
        for bar, value in zip(bars, values):
            height = bar.get_height()
            label = formatter(value)
            self.axes[0].text(bar.get_x() + bar.get_width()/2., height + 0.01 * max(values),
                             label, ha='center', va='bottom', fontweight='bold')
        
        self.axes[0].set_xticks(x_pos)
        self.axes[0].set_xticklabels(channels, rotation=45, ha='right')
        self.axes[0].set_ylabel(ylabel)
        self.axes[0].set_title(f"Channel Performance - {metric}")
        self.axes[0].grid(True, axis='y', linestyle='--', alpha=0.7)
        
        # 在右侧添加ROI漏斗图
        if show_breakdown and metric == 'ROI':
            self.add_roi_breakdown(channel_revenue, channel_spend, channels)
        else:
            # 添加渠道随时间的变化趋势
            self.add_channel_trends()
        
        self.fig.tight_layout()
        self.draw()
    
    def add_roi_breakdown(self, channel_revenue, channel_spend, channels):
        """添加ROI分解图"""
        # 计算ROI组成部分
        net_profit = [channel_revenue[channel] - channel_spend[channel] for channel in channels]
        spend_values = [channel_spend[channel] for channel in channels]
        
        # 创建堆叠条形图
        x_pos = np.arange(len(channels))
        self.axes[1].bar(x_pos, spend_values, label='Spend', color='lightcoral')
        self.axes[1].bar(x_pos, net_profit, bottom=spend_values, label='Net Profit', color='lightgreen')
        
        self.axes[1].set_xticks(x_pos)
        self.axes[1].set_xticklabels(channels, rotation=45, ha='right')
        self.axes[1].set_ylabel("Amount ($)")
        self.axes[1].set_title("ROI Breakdown by Channel")
        self.axes[1].legend()
        self.axes[1].grid(True, axis='y', linestyle='--', alpha=0.7)
    
    def add_channel_trends(self):
        """添加渠道趋势图"""
        # 按月份和渠道分组数据
        data = self.transaction_data.copy()
        data['transaction_date'] = pd.to_datetime(data['transaction_date'])
        data['month'] = data['transaction_date'].dt.to_period('M')
        
        monthly_channel = data.groupby(['month', 'channel'])['amount'].sum().unstack(fill_value=0)
        
        # 计算月度增长率
        monthly_growth = monthly_channel.pct_change().iloc[1:] * 100
        
        # 绘制热图
        im = self.axes[1].imshow(monthly_growth.T, cmap='RdYlGn', aspect='auto', 
                               vmin=-50, vmax=50)
        
        # 设置标签
        self.axes[1].set_yticks(range(len(monthly_growth.columns)))
        self.axes[1].set_yticklabels(monthly_growth.columns)
        self.axes[1].set_xticks(range(len(monthly_growth.index)))
        self.axes[1].set_xticklabels([str(period) for period in monthly_growth.index], 
                                   rotation=45, ha='right')
        
        self.axes[1].set_title("Monthly Growth by Channel (%)")
        self.fig.colorbar(im, ax=self.axes[1])


class CustomerLTVWidget(AdvancedMplCanvas):
    """客户生命周期价值可视化组件"""
    
    def __init__(self, customer_data, transaction_data, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.customer_data = customer_data
        self.transaction_data = transaction_data
        self.axes = self.fig.subplots(2, 2)
        self.fig.set_size_inches(10, 8)
        self.update_chart()
        
    def update_chart(self, show_projection=False):
        """更新图表"""
        for ax in self.axes.flat:
            ax.clear()
        
        # 准备数据
        customer_ltv = self.calculate_ltv()
        
        # 1. LTV分布直方图
        self.axes[0, 0].hist(customer_ltv['ltv'], bins=30, alpha=0.7, color='skyblue', edgecolor='black')
        self.axes[0, 0].set_xlabel('Lifetime Value ($)')
        self.axes[0, 0].set_ylabel('Number of Customers')
        self.axes[0, 0].set_title('Customer LTV Distribution')
        self.axes[0, 0].grid(True, linestyle='--', alpha=0.7)
        
        # 2. 按细分市场的LTV箱线图
        segments = customer_ltv.groupby('segment')['ltv'].apply(list)
        segments_data = [segments.get(seg, []) for seg in ['Low', 'Medium', 'High']]
        
        self.axes[0, 1].boxplot(segments_data, labels=['Low', 'Medium', 'High'])
        self.axes[0, 1].set_xlabel('Customer Segment')
        self.axes[0, 1].set_ylabel('Lifetime Value ($)')
        self.axes[0, 1].set_title('LTV by Customer Segment')
        self.axes[0, 1].grid(True, linestyle='--', alpha=0.7)
        
        # 3. 按地区的LTV
        location_ltv = customer_ltv.groupby('location')['ltv'].mean().sort_values(ascending=False)
        self.axes[1, 0].bar(range(len(location_ltv)), location_ltv.values, color='lightgreen')
        self.axes[1, 0].set_xticks(range(len(location_ltv)))
        self.axes[1, 0].set_xticklabels(location_ltv.index, rotation=45, ha='right')
        self.axes[1, 0].set_xlabel('Location')
        self.axes[1, 0].set_ylabel('Average LTV ($)')
        self.axes[1, 0].set_title('Average LTV by Location')
        self.axes[1, 0].grid(True, axis='y', linestyle='--', alpha=0.7)
        
        # 4. LTV与客户年龄的关系
        self.axes[1, 1].scatter(customer_ltv['age'], customer_ltv['ltv'], alpha=0.6, color='purple')
        self.axes[1, 1].set_xlabel('Age')
        self.axes[1, 1].set_ylabel('Lifetime Value ($)')
        self.axes[1, 1].set_title('LTV vs Customer Age')
        
        # 添加趋势线
        z = np.polyfit(customer_ltv['age'], customer_ltv['ltv'], 1)
        p = np.poly1d(z)
        self.axes[1, 1].plot(customer_ltv['age'], p(customer_ltv['age']), "r--", alpha=0.8)
        
        self.axes[1, 1].grid(True, linestyle='--', alpha=0.7)
        
        self.fig.tight_layout()
        self.draw()
    
    def calculate_ltv(self):
        """计算客户生命周期价值"""
        # 计算每个客户的总支出
        customer_spend = self.transaction_data.groupby('customer_id')['amount'].sum().reset_index()
        customer_spend.rename(columns={'amount': 'ltv'}, inplace=True)
        
        # 合并客户数据
        ltv_data = pd.merge(customer_spend, self.customer_data, on='customer_id')
        
        return ltv_data


class PredictiveAnalyticsWidget(QWidget):
    """预测分析组件（使用多种模型）"""
    
    def __init__(self, transaction_data, social_data, parent=None):
        super().__init__(parent)
        self.transaction_data = transaction_data
        self.social_data = social_data
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        
        # 创建控制面板
        control_layout = QHBoxLayout()
        
        self.model_type = QComboBox()
        self.model_type.addItems(["Linear Regression", "Random Forest", "ARIMA", "Exponential Smoothing", "Gradient Boosting"])
        control_layout.addWidget(QLabel("Model:"))
        control_layout.addWidget(self.model_type)
        
        self.forecast_days = QSpinBox()
        self.forecast_days.setRange(30, 365)
        self.forecast_days.setValue(90)
        self.forecast_days.setSuffix(" days")
        control_layout.addWidget(QLabel("Forecast Period:"))
        control_layout.addWidget(self.forecast_days)
        
        self.confidence_level = QDoubleSpinBox()
        self.confidence_level.setRange(0.7, 0.99)
        self.confidence_level.setValue(0.95)
        self.confidence_level.setSingleStep(0.01)
        control_layout.addWidget(QLabel("Confidence Level:"))
        control_layout.addWidget(self.confidence_level)
        
        self.include_social = QCheckBox("Include Social Data")
        control_layout.addWidget(self.include_social)
        
        self.update_btn = QPushButton("Update Forecast")
        self.update_btn.clicked.connect(self.update_plot)
        control_layout.addWidget(self.update_btn)
        
        control_layout.addStretch()
        
        control_widget = QWidget()
        control_widget.setLayout(control_layout)
        
        self.layout.addWidget(control_widget)
        
        # 初始化图表
        self.update_plot()
    
    def update_plot(self):
        """更新预测图表"""
        # 准备数据
        data = self.transaction_data.copy()
        data['transaction_date'] = pd.to_datetime(data['transaction_date'])
        daily_revenue = data.set_index('transaction_date')['amount'].resample('D').sum()
        
        # 转换为DataFrame
        df = daily_revenue.reset_index()
        df.columns = ['ds', 'y']
        
        # 移除缺失值
        df = df.dropna()
        
        # 获取参数
        model_type = self.model_type.currentText()
        forecast_days = self.forecast_days.value()
        confidence = self.confidence_level.value()
        
        # 创建预测
        if model_type == "ARIMA":
            fig = self.arima_forecast(df, forecast_days, confidence)
        elif model_type == "Exponential Smoothing":
            fig = self.exponential_smoothing_forecast(df, forecast_days, confidence)
        elif model_type == "Gradient Boosting":
            fig = self.gradient_boosting_forecast(df, forecast_days, confidence)
        elif model_type == "Random Forest":
            fig = self.random_forest_forecast(df, forecast_days, confidence)
        else:
            fig = self.linear_forecast(df, forecast_days, confidence)
        
        # 将Plotly图表转换为HTML并显示
        plot_html = plot(fig, output_type='div', include_plotlyjs='cdn')
        
        # 清除现有内容并添加新图表
        for i in reversed(range(self.layout.count())):
            widget = self.layout.itemAt(i).widget()
            if widget and isinstance(widget, QLabel) and widget.text().startswith("<html>"):
                widget.setParent(None)
        
        plot_label = QLabel(plot_html)
        plot_label.setTextFormat(Qt.RichText)
        self.layout.addWidget(plot_label)
    
    def arima_forecast(self, df, periods, confidence):
        """使用ARIMA进行预测"""
        try:
            # 自动选择ARIMA参数
            model = pm.auto_arima(df['y'], seasonal=True, m=7, 
                                 stepwise=True, suppress_warnings=True)
            
            # 进行预测
            forecast, conf_int = model.predict(n_periods=periods, return_conf_int=True, alpha=1-confidence)
            
            # 生成未来日期
            last_date = df['ds'].max()
            future_dates = [last_date + timedelta(days=i) for i in range(1, periods+1)]
            
            # 创建图表
            fig = go.Figure()
            
            # 添加历史数据
            fig.add_trace(go.Scatter(
                x=df['ds'],
                y=df['y'],
                mode='lines',
                name='Historical Revenue',
                line=dict(color='#1f77b4', width=2)
            ))
            
            # 添加预测
            fig.add_trace(go.Scatter(
                x=future_dates,
                y=forecast,
                mode='lines',
                name='Forecast',
                line=dict(color='#2ca02c', width=2)
            ))
            
            # 添加置信区间
            fig.add_trace(go.Scatter(
                x=future_dates + future_dates[::-1],
                y=np.concatenate([conf_int[:, 1], conf_int[:, 0][::-1]]),
                fill='toself',
                fillcolor='rgba(44, 160, 44, 0.2)',
                line=dict(color='rgba(255, 255, 255, 0)'),
                name=f'{confidence:.0%} Confidence Interval'
            ))
            
            fig.update_layout(
                title='Revenue Forecast using ARIMA',
                xaxis_title='Date',
                yaxis_title='Revenue ($)',
                hovermode='x unified'
            )
            
            return fig
        except Exception as e:
            # 如果ARIMA失败，回退到线性回归
            print(f"ARIMA failed: {e}")
            return self.linear_forecast(df, periods, confidence)
    
    def exponential_smoothing_forecast(self, df, periods, confidence):
        """使用指数平滑进行预测"""
        try:
            # 准备数据
            ts_data = df.set_index('ds')['y']
            
            # 拟合指数平滑模型
            model = ExponentialSmoothing(ts_data, seasonal='add', seasonal_periods=7)
            fitted_model = model.fit()
            
            # 进行预测
            forecast = fitted_model.forecast(periods)
            
            # 生成未来日期
            last_date = df['ds'].max()
            future_dates = [last_date + timedelta(days=i) for i in range(1, periods+1)]
            
            # 创建图表
            fig = go.Figure()
            
            # 添加历史数据
            fig.add_trace(go.Scatter(
                x=df['ds'],
                y=df['y'],
                mode='lines',
                name='Historical Revenue',
                line=dict(color='#1f77b4', width=2)
            ))
            
            # 添加预测
            fig.add_trace(go.Scatter(
                x=future_dates,
                y=forecast,
                mode='lines',
                name='Forecast',
                line=dict(color='#2ca02c', width=2)
            ))
            
            fig.update_layout(
                title='Revenue Forecast using Exponential Smoothing',
                xaxis_title='Date',
                yaxis_title='Revenue ($)',
                hovermode='x unified'
            )
            
            return fig
        except Exception as e:
            print(f"Exponential Smoothing failed: {e}")
            return self.linear_forecast(df, periods, confidence)
    
    def gradient_boosting_forecast(self, df, periods, confidence):
        """使用梯度提升进行预测"""
        # 准备特征
        df['days'] = (df['ds'] - df['ds'].min()).dt.days
        df['day_of_week'] = df['ds'].dt.dayofweek
        df['month'] = df['ds'].dt.month
        df['quarter'] = df['ds'].dt.quarter
        
        X = df[['days', 'day_of_week', 'month', 'quarter']]
        y = df['y']
        
        # 训练模型
        model = GradientBoostingRegressor(n_estimators=100, random_state=42)
        model.fit(X, y)
        
        # 创建未来日期
        last_date = df['ds'].max()
        future_dates = [last_date + timedelta(days=i) for i in range(1, periods+1)]
        
        # 准备未来特征
        future_df = pd.DataFrame({'ds': future_dates})
        future_df['days'] = (future_df['ds'] - df['ds'].min()).dt.days
        future_df['day_of_week'] = future_df['ds'].dt.dayofweek
        future_df['month'] = future_df['ds'].dt.month
        future_df['quarter'] = future_df['ds'].dt.quarter
        
        X_future = future_df[['days', 'day_of_week', 'month', 'quarter']]
        
        # 进行预测
        future_y = model.predict(X_future)
        
        # 创建图表
        fig = go.Figure()
        
        # 添加历史数据
        fig.add_trace(go.Scatter(
            x=df['ds'],
            y=y,
            mode='lines',
            name='Historical Revenue',
            line=dict(color='#1f77b4', width=2)
        ))
        
        # 添加预测
        fig.add_trace(go.Scatter(
            x=future_dates,
            y=future_y,
            mode='lines',
            name='Forecast',
            line=dict(color='#2ca02c', width=2)
        ))
        
        fig.update_layout(
            title='Revenue Forecast using Gradient Boosting',
            xaxis_title='Date',
            yaxis_title='Revenue ($)',
            hovermode='x unified'
        )
        
        return fig
    
    def random_forest_forecast(self, df, periods, confidence):
        """使用随机森林进行预测"""
        # 准备特征
        df['days'] = (df['ds'] - df['ds'].min()).dt.days
        df['day_of_week'] = df['ds'].dt.dayofweek
        df['month'] = df['ds'].dt.month
        df['quarter'] = df['ds'].dt.quarter
        
        X = df[['days', 'day_of_week', 'month', 'quarter']]
        y = df['y']
        
        # 训练模型
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X, y)
        
        # 创建未来日期
        last_date = df['ds'].max()
        future_dates = [last_date + timedelta(days=i) for i in range(1, periods+1)]
        
        # 准备未来特征
        future_df = pd.DataFrame({'ds': future_dates})
        future_df['days'] = (future_df['ds'] - df['ds'].min()).dt.days
        future_df['day_of_week'] = future_df['ds'].dt.dayofweek
        future_df['month'] = future_df['ds'].dt.month
        future_df['quarter'] = future_df['ds'].dt.quarter
        
        X_future = future_df[['days', 'day_of_week', 'month', 'quarter']]
        
        # 进行预测
        future_y = model.predict(X_future)
        
        # 创建图表
        fig = go.Figure()
        
        # 添加历史数据
        fig.add_trace(go.Scatter(
            x=df['ds'],
            y=y,
            mode='lines',
            name='Historical Revenue',
            line=dict(color='#1f77b4', width=2)
        ))
        
        # 添加预测
        fig.add_trace(go.Scatter(
            x=future_dates,
            y=future_y,
            mode='lines',
            name='Forecast',
            line=dict(color='#2ca02c', width=2)
        ))
        
        fig.update_layout(
            title='Revenue Forecast using Random Forest',
            xaxis_title='Date',
            yaxis_title='Revenue ($)',
            hovermode='x unified'
        )
        
        return fig
    
    def linear_forecast(self, df, periods, confidence):
        """使用线性回归进行预测"""
        # 准备特征
        df['days'] = (df['ds'] - df['ds'].min()).dt.days
        
        X = df['days'].values.reshape(-1, 1)
        y = df['y'].values
        
        # 训练模型
        model = LinearRegression()
        model.fit(X, y)
        
        # 创建未来日期
        last_date = df['ds'].max()
        future_dates = [last_date + timedelta(days=i) for i in range(1, periods+1)]
        
        # 准备未来特征
        future_days = [(date - df['ds'].min()).days for date in future_dates]
        X_future = np.array(future_days).reshape(-1, 1)
        
        # 进行预测
        future_y = model.predict(X_future)
        
        # 计算置信区间
        y_pred = model.predict(X)
        residuals = y - y_pred
        stdev = np.std(residuals)
        
        z_score = stats.norm.ppf(confidence)
        margin_of_error = z_score * stdev
        
        upper_bound = future_y + margin_of_error
        lower_bound = future_y - margin_of_error
        
        # 创建图表
        fig = go.Figure()
        
        # 添加历史数据
        fig.add_trace(go.Scatter(
            x=df['ds'],
            y=y,
            mode='lines',
            name='Historical Revenue',
            line=dict(color='#1f77b4', width=2)
        ))
        
        # 添加预测
        fig.add_trace(go.Scatter(
            x=future_dates,
            y=future_y,
            mode='lines',
            name='Forecast',
            line=dict(color='#2ca02c', width=2)
        ))
        
        # 添加置信区间
        fig.add_trace(go.Scatter(
            x=future_dates + future_dates[::-1],
            y=np.concatenate([upper_bound, lower_bound[::-1]]),
            fill='toself',
            fillcolor='rgba(44, 160, 44, 0.2)',
            line=dict(color='rgba(255, 255, 255, 0)'),
            name=f'{confidence:.0%} Confidence Interval'
        ))
        
        fig.update_layout(
            title='Revenue Forecast using Linear Regression',
            xaxis_title='Date',
            yaxis_title='Revenue ($)',
            hovermode='x unified'
        )
        
        return fig


class SocialMediaAnalyticsWidget(QWidget):
    """社交媒体分析组件"""
    
    def __init__(self, social_data, parent=None):
        super().__init__(parent)
        self.social_data = social_data
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        
        # 创建控制面板
        control_layout = QHBoxLayout()
        
        self.metric_combo = QComboBox()
        self.metric_combo.addItems(["Engagements", "Impressions", "Clicks", "Conversions", "Sentiment"])
        control_layout.addWidget(QLabel("Metric:"))
        control_layout.addWidget(self.metric_combo)
        
        self.time_granularity = QComboBox()
        self.time_granularity.addItems(["Daily", "Weekly", "Monthly"])
        control_layout.addWidget(QLabel("Granularity:"))
        control_layout.addWidget(self.time_granularity)
        
        self.show_trend = QCheckBox("Show Trend")
        self.show_trend.setChecked(True)
        control_layout.addWidget(self.show_trend)
        
        self.update_btn = QPushButton("Update Chart")
        self.update_btn.clicked.connect(self.update_plot)
        control_layout.addWidget(self.update_btn)
        
        control_layout.addStretch()
        
        control_widget = QWidget()
        control_widget.setLayout(control_layout)
        
        self.layout.addWidget(control_widget)
        
        # 初始化图表
        self.update_plot()
    
    def update_plot(self):
        """更新社交媒体图表"""
        # 准备数据
        data = self.social_data.copy()
        metric = self.metric_combo.currentText().lower()
        granularity = self.time_granularity.currentText()
        
        # 按时间粒度重新采样
        if granularity == 'Weekly':
            resampled_data = data.resample('W', on='date').mean()
            time_label = "Week"
        elif granularity == 'Monthly':
            resampled_data = data.resample('M', on='date').mean()
            time_label = "Month"
        else:  # Daily
            resampled_data = data
            time_label = "Day"
        
        # 创建图表
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=(f"{metric.capitalize()} Over Time", "Correlation with Sentiment"),
            vertical_spacing=0.1,
            row_heights=[0.7, 0.3]
        )
        
        # 添加主指标线图
        fig.add_trace(
            go.Scatter(
                x=resampled_data['date'],
                y=resampled_data[metric],
                mode='lines',
                name=metric.capitalize(),
                line=dict(width=2)
            ),
            row=1, col=1
        )
        
        # 如果启用，添加趋势线
        if self.show_trend.isChecked():
            z = np.polyfit(range(len(resampled_data)), resampled_data[metric], 1)
            p = np.poly1d(z)
            trend_line = p(range(len(resampled_data)))
            
            fig.add_trace(
                go.Scatter(
                    x=resampled_data['date'],
                    y=trend_line,
                    mode='lines',
                    name='Trend',
                    line=dict(dash='dash', color='red')
                ),
                row=1, col=1
            )
        
        # 添加情感相关性散点图
        if metric != 'sentiment':
            fig.add_trace(
                go.Scatter(
                    x=resampled_data[metric],
                    y=resampled_data['sentiment'],
                    mode='markers',
                    name='Sentiment Correlation',
                    marker=dict(size=8, opacity=0.6)
                ),
                row=2, col=1
            )
            
            # 计算并显示相关系数
            correlation = resampled_data[metric].corr(resampled_data['sentiment'])
            fig.add_annotation(
                x=0.05, y=0.95,
                xref="paper", yref="paper",
                text=f"Correlation: {correlation:.2f}",
                showarrow=False,
                row=2, col=1
            )
        else:
            # 对于情感指标本身，显示分布直方图
            fig.add_trace(
                go.Histogram(
                    x=resampled_data[metric],
                    name='Sentiment Distribution',
                    nbinsx=20
                ),
                row=2, col=1
            )
        
        # 更新布局
        fig.update_layout(
            height=600,
            showlegend=True,
            title_text=f"Social Media Analytics - {metric.capitalize()}"
        )
        
        fig.update_xaxes(title_text="Date", row=1, col=1)
        fig.update_yaxes(title_text=metric.capitalize(), row=1, col=1)
        
        if metric != 'sentiment':
            fig.update_xaxes(title_text=metric.capitalize(), row=2, col=1)
            fig.update_yaxes(title_text="Sentiment", row=2, col=1)
        else:
            fig.update_xaxes(title_text="Sentiment", row=2, col=1)
            fig.update_yaxes(title_text="Count", row=2, col=1)
        
        # 将Plotly图表转换为HTML并显示
        plot_html = plot(fig, output_type='div', include_plotlyjs='cdn')
        
        # 清除现有内容并添加新图表
        for i in reversed(range(self.layout.count())):
            widget = self.layout.itemAt(i).widget()
            if widget and isinstance(widget, QLabel) and widget.text().startswith("<html>"):
                widget.setParent(None)
        
        plot_label = QLabel(plot_html)
        plot_label.setTextFormat(Qt.RichText)
        self.layout.addWidget(plot_label)


class CustomerSegmentationWidget(QWidget):
    """客户细分分析组件"""
    
    def __init__(self, customer_data, transaction_data, parent=None):
        super().__init__(parent)
        self.customer_data = customer_data
        self.transaction_data = transaction_data
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        
        # 创建控制面板
        control_layout = QHBoxLayout()
        
        control_layout.addWidget(QLabel("Segmentation Method:"))
        self.segmentation_method = QComboBox()
        self.segmentation_method.addItems(["K-Means", "RFM Analysis", "Demographic"])
        control_layout.addWidget(self.segmentation_method)
        
        control_layout.addWidget(QLabel("Number of Clusters:"))
        self.n_clusters = QSpinBox()
        self.n_clusters.setRange(2, 10)
        self.n_clusters.setValue(4)
        control_layout.addWidget(self.n_clusters)
        
        self.update_btn = QPushButton("Update Segmentation")
        self.update_btn.clicked.connect(self.update_plot)
        control_layout.addWidget(self.update_btn)
        
        control_layout.addStretch()
        
        control_widget = QWidget()
        control_widget.setLayout(control_layout)
        
        self.layout.addWidget(control_widget)
        
        # 初始化图表
        self.update_plot()
    
    def update_plot(self):
        """更新客户细分图表"""
        method = self.segmentation_method.currentText()
        n_clusters = self.n_clusters.value()
        
        if method == "K-Means":
            fig = self.kmeans_segmentation(n_clusters)
        elif method == "RFM Analysis":
            fig = self.rfm_analysis(n_clusters)
        else:
            fig = self.demographic_segmentation(n_clusters)
        
        # 将Plotly图表转换为HTML并显示
        plot_html = plot(fig, output_type='div', include_plotlyjs='cdn')
        
        # 清除现有内容并添加新图表
        for i in reversed(range(self.layout.count())):
            widget = self.layout.itemAt(i).widget()
            if widget and isinstance(widget, QLabel) and widget.text().startswith("<html>"):
                widget.setParent(None)
        
        plot_label = QLabel(plot_html)
        plot_label.setTextFormat(Qt.RichText)
        self.layout.addWidget(plot_label)
    
    def kmeans_segmentation(self, n_clusters):
        """使用K-Means进行客户细分"""
        # 准备特征数据
        features = self.prepare_customer_features()
        
        # 标准化数据
        scaler = StandardScaler()
        scaled_features = scaler.fit_transform(features)
        
        # 应用K-Means聚类
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        clusters = kmeans.fit_predict(scaled_features)
        
        # 应用PCA进行降维可视化
        pca = PCA(n_components=2)
        pca_features = pca.fit_transform(scaled_features)
        
        # 创建散点图
        fig = px.scatter(
            x=pca_features[:, 0], 
            y=pca_features[:, 1],
            color=clusters,
            title=f"Customer Segmentation using K-Means ({n_clusters} clusters)",
            labels={'x': 'PCA Component 1', 'y': 'PCA Component 2'},
            color_continuous_scale=px.colors.sequential.Viridis
        )
        
        return fig
    
    def rfm_analysis(self, n_clusters):
        """使用RFM分析进行客户细分"""
        # 计算RFM指标
        rfm_df = self.calculate_rfm()
        
        # 对RFM指标进行对数变换
        rfm_log = rfm_df[['recency', 'frequency', 'monetary']].apply(np.log1p)
        
        # 标准化数据
        scaler = StandardScaler()
        scaled_rfm = scaler.fit_transform(rfm_log)
        
        # 应用K-Means聚类
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        clusters = kmeans.fit_predict(scaled_rfm)
        
        # 创建3D散点图
        fig = px.scatter_3d(
            rfm_df, 
            x='recency', 
            y='frequency', 
            z='monetary',
            color=clusters,
            title=f"RFM Analysis with {n_clusters} segments",
            labels={
                'recency': 'Recency (days)',
                'frequency': 'Frequency',
                'monetary': 'Monetary Value ($)'
            },
            color_continuous_scale=px.colors.sequential.Viridis
        )
        
        return fig
    
    def demographic_segmentation(self, n_clusters):
        """基于人口统计数据进行客户细分"""
        # 准备人口统计特征
        demo_features = self.prepare_demographic_features()
        
        # 标准化数据
        scaler = StandardScaler()
        scaled_features = scaler.fit_transform(demo_features)
        
        # 应用K-Means聚类
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        clusters = kmeans.fit_predict(scaled_features)
        
        # 创建条形图显示每个群组的平均特征
        demo_features['cluster'] = clusters
        cluster_means = demo_features.groupby('cluster').mean()
        
        fig = px.bar(
            cluster_means.T,
            title="Average Demographic Characteristics by Cluster",
            labels={'value': 'Average Value', 'variable': 'Cluster'},
            barmode='group'
        )
        
        return fig
    
    def prepare_customer_features(self):
        """准备客户特征数据"""
        # 计算RFM指标
        rfm_df = self.calculate_rfm()
        
        # 合并人口统计信息
        customer_features = self.customer_data.merge(rfm_df, on='customer_id')
        
        # 选择特征列
        features = customer_features[['age', 'recency', 'frequency', 'monetary']]
        
        return features
    
    def calculate_rfm(self):
        """计算RFM指标"""
        # 计算最近一次购买日期
        max_date = self.transaction_data['transaction_date'].max()
        
        # 按客户分组计算RFM
        rfm = self.transaction_data.groupby('customer_id').agg({
            'transaction_date': lambda x: (max_date - x.max()).days,  # Recency
            'customer_id': 'count',  # Frequency
            'amount': 'sum'  # Monetary
        }).rename(columns={
            'transaction_date': 'recency',
            'customer_id': 'frequency',
            'amount': 'monetary'
        }).reset_index()
        
        return rfm
    
    def prepare_demographic_features(self):
        """准备人口统计特征"""
        # 选择人口统计列
        demo_features = self.customer_data[['age', 'customer_value']].copy()
        
        # 添加性别编码
        demo_features['gender'] = self.customer_data['gender'].map({'Male': 0, 'Female': 1})
        
        return demo_features


class AdvancedCMOAnalyticsDashboard(QMainWindow):
    """增强版CMO分析仪表板主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Advanced CMO Analytics Dashboard")
        self.setGeometry(100, 100, 1600, 1000)
        
        # 初始化数据
        self.data_loaded = False
        self.data_sources = {}
        
        # 设置中心部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 创建加载界面
        self.loading_widget = QWidget()
        loading_layout = QVBoxLayout(self.loading_widget)
        
        loading_label = QLabel("Loading data...")
        loading_label.setAlignment(Qt.AlignCenter)
        loading_label.setFont(QFont("Arial", 16))
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        
        loading_layout.addWidget(loading_label)
        loading_layout.addWidget(self.progress_bar)
        
        main_layout.addWidget(self.loading_widget)
        
        # 创建数据管理线程
        self.data_manager = DataManager()
        self.data_manager.progress_updated.connect(self.update_progress)
        self.data_manager.data_loaded.connect(self.on_data_loaded)
        self.data_manager.start()
        
        # 应用样式
        self.apply_styles()
    
    def update_progress(self, value):
        """更新进度条"""
        self.progress_bar.setValue(value)
    
    def on_data_loaded(self, data_sources):
        """数据加载完成后的回调"""
        self.data_sources = data_sources
        self.data_loaded = True
        
        # 移除加载界面
        self.centralWidget().layout().removeWidget(self.loading_widget)
        self.loading_widget.setParent(None)
        
        # 创建主界面
        self.setup_main_interface()
    
    def setup_main_interface(self):
        """设置主界面"""
        # 创建选项卡式界面
        self.tabs = QTabWidget()
        self.centralWidget().layout().addWidget(self.tabs)
        
        # 创建各个选项卡
        self.setup_overview_tab()
        self.setup_channel_tab()
        self.setup_customer_tab()
        self.setup_predictive_tab()
        self.setup_social_tab()
        self.setup_segmentation_tab()
        self.setup_data_tab()
        
        # 创建工具栏
        self.setup_toolbar()
        
        # 创建状态栏
        self.statusBar().showMessage("Ready")
    
    def setup_toolbar(self):
        """设置工具栏"""
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)
        
        # 添加工具栏动作
        refresh_action = QAction("Refresh Data", self)
        refresh_action.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        refresh_action.triggered.connect(self.refresh_data)
        toolbar.addAction(refresh_action)
        
        export_action = QAction("Export Report", self)
        export_action.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        export_action.triggered.connect(self.export_report)
        toolbar.addAction(export_action)
        
        toolbar.addSeparator()
        
        settings_action = QAction("Settings", self)
        settings_action.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        toolbar.addAction(settings_action)
        
        # 添加数据源选择
        toolbar.addWidget(QLabel("Data Source:"))
        self.source_combo = QComboBox()
        self.source_combo.addItems(["Synthetic", "CSV Import", "API Connection"])
        toolbar.addWidget(self.source_combo)
    
    def setup_overview_tab(self):
        """设置概览选项卡"""
        overview_tab = QWidget()
        layout = QVBoxLayout(overview_tab)
        
        # 创建控制面板
        control_panel = QWidget()
        control_layout = QHBoxLayout(control_panel)
        
        # 时间频率选择
        control_layout.addWidget(QLabel("Time Frequency:"))
        self.frequency_combo = QComboBox()
        self.frequency_combo.addItems(["Daily", "Weekly", "Monthly"])
        self.frequency_combo.setCurrentText("Monthly")
        control_layout.addWidget(self.frequency_combo)
        
        # 产品筛选
        control_layout.addWidget(QLabel("Product:"))
        self.product_combo = QComboBox()
        self.product_combo.addItems(["All"] + list(self.data_sources['transactions']['product'].unique()))
        control_layout.addWidget(self.product_combo)
        
        # 预测复选框
        self.forecast_checkbox = QCheckBox("Show Forecast")
        control_layout.addWidget(self.forecast_checkbox)
        
        # 更新按钮
        self.update_btn = QPushButton("Update Charts")
        control_layout.addWidget(self.update_btn)
        
        control_layout.addStretch()
        
        layout.addWidget(control_panel)
        
        # 创建分割器以容纳多个图表
        splitter = QSplitter(Qt.Vertical)
        
        # 收入趋势图
        self.revenue_chart = AdvancedRevenueTrendWidget(self.data_sources['transactions'], splitter)
        splitter.addWidget(self.revenue_chart)
        
        # KPI面板
        kpi_widget = QWidget()
        kpi_layout = QHBoxLayout(kpi_widget)
        
        # 计算关键指标
        total_revenue = self.data_sources['transactions']['amount'].sum()
        avg_order_value = self.data_sources['transactions']['amount'].mean()
        customers_count = self.data_sources['customers']['customer_id'].nunique()
        avg_ltv = self.data_sources['transactions'].groupby('customer_id')['amount'].sum().mean()
        
        # 创建KPI卡片
        kpi_layout.addWidget(self.create_kpi_card("Total Revenue", f"${total_revenue:,.0f}", "$", "#2ecc71"))
        kpi_layout.addWidget(self.create_kpi_card("Avg Order Value", f"${avg_order_value:,.2f}", "AOV", "#3498db"))
        kpi_layout.addWidget(self.create_kpi_card("Total Customers", f"{customers_count:,}", "👥", "#9b59b6"))
        kpi_layout.addWidget(self.create_kpi_card("Avg LTV", f"${avg_ltv:,.0f}", "📈", "#e74c3c"))
        
        splitter.addWidget(kpi_widget)
        splitter.setSizes([700, 150])
        
        layout.addWidget(splitter)
        
        # 连接信号
        self.update_btn.clicked.connect(self.update_overview_charts)
        self.frequency_combo.currentTextChanged.connect(self.update_overview_charts)
        self.product_combo.currentTextChanged.connect(self.update_overview_charts)
        self.forecast_checkbox.stateChanged.connect(self.update_overview_charts)
        
        self.tabs.addTab(overview_tab, "📊 Overview")
    
    def create_kpi_card(self, title, value, icon, color):
        """创建KPI卡片"""
        card = QGroupBox(title)
        card_layout = QVBoxLayout(card)
        
        # 设置卡片样式
        card.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                border: 2px solid {color};
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 10px;
                background-color: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #FFFFFF, stop: 1 {color}20
                );
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: {color};
            }}
        """)
        
        # 值标签
        value_label = QLabel(value)
        value_label.setAlignment(Qt.AlignCenter)
        value_label.setFont(QFont("Arial", 16, QFont.Bold))
        value_label.setStyleSheet(f"color: {color};")
        
        # 图标
        icon_label = QLabel(icon)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setFont(QFont("Arial", 24))
        
        card_layout.addWidget(icon_label)
        card_layout.addWidget(value_label)
        
        return card
    
    def setup_channel_tab(self):
        """设置渠道分析选项卡"""
        channel_tab = QWidget()
        layout = QVBoxLayout(channel_tab)
        
        # 控制面板
        control_panel = QWidget()
        control_layout = QHBoxLayout(control_panel)
        
        control_layout.addWidget(QLabel("Metric:"))
        self.metric_combo = QComboBox()
        self.metric_combo.addItems(["ROI", "Revenue", "Spend", "CAC"])
        control_layout.addWidget(self.metric_combo)
        
        self.breakdown_checkbox = QCheckBox("Show ROI Breakdown")
        control_layout.addWidget(self.breakdown_checkbox)
        
        self.update_channel_btn = QPushButton("Update Chart")
        control_layout.addWidget(self.update_channel_btn)
        
        control_layout.addStretch()
        
        layout.addWidget(control_panel)
        
        # 渠道性能图表
        self.channel_chart = AdvancedChannelPerformanceWidget(
            self.data_sources['transactions'], self.data_sources['campaigns'])
        layout.addWidget(self.channel_chart)
        
        # 连接信号
        self.update_channel_btn.clicked.connect(self.update_channel_chart)
        self.metric_combo.currentTextChanged.connect(self.update_channel_chart)
        self.breakdown_checkbox.stateChanged.connect(self.update_channel_chart)
        
        self.tabs.addTab(channel_tab, "📢 Channel Analysis")
    
    def setup_customer_tab(self):
        """设置客户分析选项卡"""
        customer_tab = QWidget()
        layout = QVBoxLayout(customer_tab)
        
        # 控制面板
        control_panel = QWidget()
        control_layout = QHBoxLayout(control_panel)
        
        control_layout.addWidget(QLabel("Analysis Type:"))
        self.analysis_combo = QComboBox()
        self.analysis_combo.addItems(["LTV Analysis", "Segmentation", "Geographic Distribution"])
        control_layout.addWidget(self.analysis_combo)
        
        self.update_customer_btn = QPushButton("Update Analysis")
        control_layout.addWidget(self.update_customer_btn)
        
        control_layout.addStretch()
        
        layout.addWidget(control_panel)
        
        # 客户分析图表
        self.customer_chart = CustomerLTVWidget(
            self.data_sources['customers'], self.data_sources['transactions'])
        layout.addWidget(self.customer_chart)
        
        # 连接信号
        self.update_customer_btn.clicked.connect(self.update_customer_analysis)
        self.analysis_combo.currentTextChanged.connect(self.update_customer_analysis)
        
        self.tabs.addTab(customer_tab, "👥 Customer Analysis")
    
    def setup_predictive_tab(self):
        """设置预测分析选项卡"""
        predictive_tab = QWidget()
        layout = QVBoxLayout(predictive_tab)
        
        # 预测组件
        self.predictive_widget = PredictiveAnalyticsWidget(
            self.data_sources['transactions'], self.data_sources['social'])
        layout.addWidget(self.predictive_widget)
        
        self.tabs.addTab(predictive_tab, "🔮 Predictive Analytics")
    
    def setup_social_tab(self):
        """设置社交媒体分析选项卡"""
        social_tab = QWidget()
        layout = QVBoxLayout(social_tab)
        
        # 社交媒体分析组件
        self.social_widget = SocialMediaAnalyticsWidget(self.data_sources['social'])
        layout.addWidget(self.social_widget)
        
        self.tabs.addTab(social_tab, "💬 Social Media")
    
    def setup_segmentation_tab(self):
        """设置客户细分选项卡"""
        segmentation_tab = QWidget()
        layout = QVBoxLayout(segmentation_tab)
        
        # 客户细分组件
        self.segmentation_widget = CustomerSegmentationWidget(
            self.data_sources['customers'], self.data_sources['transactions'])
        layout.addWidget(self.segmentation_widget)
        
        self.tabs.addTab(segmentation_tab, "🔍 Customer Segmentation")
    
    def setup_data_tab(self):
        """设置数据查看选项卡"""
        data_tab = QWidget()
        layout = QVBoxLayout(data_tab)
        
        # 数据表选择
        table_select_layout = QHBoxLayout()
        table_select_layout.addWidget(QLabel("Select Dataset:"))
        self.dataset_combo = QComboBox()
        self.dataset_combo.addItems(["Customers", "Transactions", "Campaigns", "Social Media"])
        table_select_layout.addWidget(self.dataset_combo)
        
        self.load_data_btn = QPushButton("Load Data")
        table_select_layout.addWidget(self.load_data_btn)
        
        self.export_data_btn = QPushButton("Export Data")
        table_select_layout.addWidget(self.export_data_btn)
        
        table_select_layout.addStretch()
        
        layout.addLayout(table_select_layout)
        
        # 数据表格
        self.data_table = QTableWidget()
        layout.addWidget(self.data_table)
        
        # 连接信号
        self.load_data_btn.clicked.connect(self.load_dataset)
        self.dataset_combo.currentTextChanged.connect(self.load_dataset)
        self.export_data_btn.clicked.connect(self.export_dataset)
        
        self.tabs.addTab(data_tab, "📋 Data View")
    
    def update_overview_charts(self):
        """更新概览选项卡中的图表"""
        frequency_map = {
            "Daily": "D",
            "Weekly": "W",
            "Monthly": "M"
        }
        frequency = frequency_map.get(self.frequency_combo.currentText(), "M")
        product_filter = self.product_combo.currentText()
        show_forecast = self.forecast_checkbox.isChecked()
        
        self.revenue_chart.update_chart(frequency, product_filter, show_forecast)
    
    def update_channel_chart(self):
        """更新渠道分析图表"""
        metric = self.metric_combo.currentText()
        show_breakdown = self.breakdown_checkbox.isChecked()
        self.channel_chart.update_chart(metric, show_breakdown)
    
    def update_customer_analysis(self):
        """更新客户分析图表"""
        analysis_type = self.analysis_combo.currentText()
        # 这里可以根据不同的分析类型切换不同的可视化
        self.customer_chart.update_chart()
    
    def load_dataset(self):
        """加载选定的数据集到表格中"""
        dataset = self.dataset_combo.currentText()
        
        if dataset == "Customers":
            data = self.data_sources['customers']
        elif dataset == "Transactions":
            data = self.data_sources['transactions']
        elif dataset == "Campaigns":
            data = self.data_sources['campaigns']
        else:  # Social Media
            data = self.data_sources['social']
        
        # 配置表格
        self.data_table.setRowCount(len(data))
        self.data_table.setColumnCount(len(data.columns))
        self.data_table.setHorizontalHeaderLabels(data.columns)
        
        # 填充数据
        for row_idx, row in data.iterrows():
            for col_idx, value in enumerate(row):
                item = QTableWidgetItem(str(value))
                self.data_table.setItem(row_idx, col_idx, item)
        
        # 调整列宽
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    
    def export_dataset(self):
        """导出当前数据集"""
        dataset = self.dataset_combo.currentText()
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, f"Export {dataset} Data", "", "CSV Files (*.csv)"
        )
        
        if file_path:
            if dataset == "Customers":
                data = self.data_sources['customers']
            elif dataset == "Transactions":
                data = self.data_sources['transactions']
            elif dataset == "Campaigns":
                data = self.data_sources['campaigns']
            else:  # Social Media
                data = self.data_sources['social']
            
            data.to_csv(file_path, index=False)
            QMessageBox.information(self, "Export Successful", 
                                   f"{dataset} data has been exported to {file_path}")
    
    def refresh_data(self):
        """刷新数据"""
        reply = QMessageBox.question(self, "Refresh Data", 
                                    "Are you sure you want to refresh all data?",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # 显示加载界面
            self.centralWidget().layout().addWidget(self.loading_widget)
            self.tabs.setParent(None)
            
            # 重新启动数据加载线程
            self.data_manager = DataManager()
            self.data_manager.progress_updated.connect(self.update_progress)
            self.data_manager.data_loaded.connect(self.on_data_loaded)
            self.data_manager.start()
    
    def export_report(self):
        """导出报告"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Report", "", "PDF Files (*.pdf);;HTML Files (*.html)"
        )
        
        if file_path:
            # 在实际应用中，这里会实现导出功能
            QMessageBox.information(self, "Export Report", 
                                   f"Report would be exported to {file_path} in a real application")
    
    def apply_styles(self):
        """应用样式表"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F5F5F5;
            }
            QTabWidget::pane {
                border: 1px solid #CCCCCC;
                background: white;
            }
            QTabBar::tab {
                background: #E0E0E0;
                border: 1px solid #CCCCCC;
                padding: 8px 12px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: white;
                border-bottom-color: white;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QTableView {
                gridline-color: #E0E0E0;
                background-color: white;
                alternate-background-color: #F5F5F5;
            }
            QHeaderView::section {
                background-color: #3498db;
                color: white;
                padding: 4px;
                border: 1px solid #2980b9;
            }
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                width: 10px;
            }
        """)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    dashboard = AdvancedCMOAnalyticsDashboard()
    dashboard.show()
    
    sys.exit(app.exec_())