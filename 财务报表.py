import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import sqlite3
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QTableWidget, QTableWidgetItem, QPushButton, QLabel, QLineEdit, 
                             QDateEdit, QComboBox, QTabWidget, QFileDialog, QMessageBox,
                             QHeaderView, QSplitter, QProgressBar, QTextEdit, QGroupBox,
                             QTreeWidget, QTreeWidgetItem, QDialog, QDialogButtonBox,
                             QFormLayout, QSpinBox, QDoubleSpinBox, QCheckBox)
from PyQt5.QtCore import Qt, QDate, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QColor
import seaborn as sns
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# 设置样式
plt.style.use('seaborn-v0_8')
sns.set_palette("Set2")


class FinancialDataManager:
    """财务数据管理类"""
    
    def __init__(self, db_path="financial_data.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建财务报表表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS financial_statements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT,
            statement_type TEXT,
            period TEXT,
            date DATE,
            revenue REAL,
            expenses REAL,
            profit REAL,
            assets REAL,
            liabilities REAL,
            equity REAL,
            cash_flow REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 创建财务指标表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS financial_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT,
            period TEXT,
            date DATE,
            roe REAL,
            roa REAL,
            current_ratio REAL,
            debt_to_equity REAL,
            gross_margin REAL,
            net_margin REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 创建财务比率历史表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS financial_ratios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT,
            period TEXT,
            date DATE,
            liquidity_ratio REAL,
            profitability_ratio REAL,
            efficiency_ratio REAL,
            solvency_ratio REAL,
            market_ratio REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def import_from_csv(self, file_path, statement_type):
        """从CSV文件导入数据"""
        try:
            df = pd.read_csv(file_path)
            conn = sqlite3.connect(self.db_path)
            
            for _, row in df.iterrows():
                conn.execute('''
                INSERT INTO financial_statements 
                (company_name, statement_type, period, date, revenue, expenses, profit, assets, liabilities, equity, cash_flow)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row.get('company_name', 'Unknown'),
                    statement_type,
                    row.get('period', 'Q1'),
                    row.get('date', datetime.now().strftime('%Y-%m-%d')),
                    row.get('revenue', 0),
                    row.get('expenses', 0),
                    row.get('profit', 0),
                    row.get('assets', 0),
                    row.get('liabilities', 0),
                    row.get('equity', 0),
                    row.get('cash_flow', 0)
                ))
            
            conn.commit()
            conn.close()
            return True, f"成功导入 {len(df)} 条记录"
        except Exception as e:
            return False, f"导入失败: {str(e)}"
    
    def export_to_csv(self, file_path, table_name, filters=None):
        """导出数据到CSV文件"""
        try:
            conn = sqlite3.connect(self.db_path)
            query = f"SELECT * FROM {table_name}"
            
            if filters:
                conditions = []
                params = []
                for key, value in filters.items():
                    conditions.append(f"{key} = ?")
                    params.append(value)
                
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
            
            df = pd.read_sql_query(query, conn, params=params if filters else None)
            df.to_csv(file_path, index=False)
            conn.close()
            return True, f"成功导出 {len(df)} 条记录到 {file_path}"
        except Exception as e:
            return False, f"导出失败: {str(e)}"
    
    def calculate_financial_metrics(self):
        """计算财务指标"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # 获取所有财务报表数据
            df = pd.read_sql_query('''
            SELECT company_name, period, date, revenue, expenses, profit, assets, liabilities, equity 
            FROM financial_statements 
            ORDER BY company_name, date
            ''', conn)
            
            # 计算各种财务指标
            df['roe'] = df['profit'] / df['equity'] * 100  # 净资产收益率
            df['roa'] = df['profit'] / df['assets'] * 100  # 总资产收益率
            df['current_ratio'] = df['assets'] / df['liabilities']  # 流动比率
            df['debt_to_equity'] = df['liabilities'] / df['equity'] * 100  # 负债权益比
            df['gross_margin'] = (df['revenue'] - df['expenses']) / df['revenue'] * 100  # 毛利率
            df['net_margin'] = df['profit'] / df['revenue'] * 100  # 净利率
            
            # 保存到财务指标表
            for _, row in df.iterrows():
                conn.execute('''
                INSERT OR REPLACE INTO financial_metrics 
                (company_name, period, date, roe, roa, current_ratio, debt_to_equity, gross_margin, net_margin)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row['company_name'],
                    row['period'],
                    row['date'],
                    row['roe'],
                    row['roa'],
                    row['current_ratio'],
                    row['debt_to_equity'],
                    row['gross_margin'],
                    row['net_margin']
                ))
            
            conn.commit()
            conn.close()
            return True, "财务指标计算完成"
        except Exception as e:
            return False, f"财务指标计算失败: {str(e)}"
    
    def get_financial_data(self, table_name, filters=None):
        """获取财务数据"""
        try:
            conn = sqlite3.connect(self.db_path)
            query = f"SELECT * FROM {table_name}"
            
            if filters:
                conditions = []
                params = []
                for key, value in filters.items():
                    conditions.append(f"{key} = ?")
                    params.append(value)
                
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
            
            df = pd.read_sql_query(query, conn, params=params if filters else None)
            conn.close()
            return True, df
        except Exception as e:
            return False, f"获取数据失败: {str(e)}"
    
    def get_multiple_companies_data(self, company_names, table_name):
        """获取多个公司的数据用于比较分析"""
        try:
            conn = sqlite3.connect(self.db_path)
            placeholders = ','.join(['?' for _ in company_names])
            query = f"SELECT * FROM {table_name} WHERE company_name IN ({placeholders}) ORDER BY date"
            
            df = pd.read_sql_query(query, conn, params=company_names)
            conn.close()
            return True, df
        except Exception as e:
            return False, f"获取多公司数据失败: {str(e)}"


class FinancialChart(FigureCanvas):
    """财务图表类 - 增强版"""
    
    def __init__(self, parent=None, width=10, height=8, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        self.axes = self.fig.add_subplot(111)
        
    def plot_time_series(self, df, x_col, y_cols, title="财务时间序列", x_label="时间", y_label="数值", 
                         secondary_y=None, forecast_data=None):
        """绘制时间序列图 - 增强版，支持双Y轴和预测数据"""
        self.axes.clear()
        
        # 设置颜色循环
        colors = plt.cm.Set3(np.linspace(0, 1, len(y_cols)))
        
        # 主Y轴数据
        for i, y_col in enumerate(y_cols):
            if y_col in df.columns:
                self.axes.plot(df[x_col], df[y_col], marker='o', label=y_col, color=colors[i], linewidth=2)
        
        # 预测数据
        if forecast_data:
            for name, data in forecast_data.items():
                self.axes.plot(data['dates'], data['values'], '--', label=name, linewidth=2)
        
        # 设置标题和标签
        self.axes.set_title(title, fontsize=16, fontweight='bold')
        self.axes.set_xlabel(x_label, fontsize=12)
        self.axes.set_ylabel(y_label, fontsize=12)
        
        # 添加网格
        self.axes.grid(True, linestyle='--', alpha=0.7)
        
        # 添加图例
        self.axes.legend(loc='best')
        
        # 格式化日期
        self.fig.autofmt_xdate()
        
        self.draw()
    
    def plot_bar_chart(self, df, x_col, y_col, title="财务柱状图", x_label="类别", y_label="数值", 
                       stacked=False, horizontal=False):
        """绘制柱状图 - 增强版，支持堆叠和水平柱状图"""
        self.axes.clear()
        
        x_pos = np.arange(len(df[x_col]))
        
        if horizontal:
            self.axes.barh(x_pos, df[y_col], alpha=0.7, color=plt.cm.Set3(np.linspace(0, 1, len(x_pos))))
            self.axes.set_yticks(x_pos)
            self.axes.set_yticklabels(df[x_col])
            self.axes.set_xlabel(y_label)
            self.axes.set_ylabel(x_label)
        else:
            self.axes.bar(x_pos, df[y_col], alpha=0.7, color=plt.cm.Set3(np.linspace(0, 1, len(x_pos))))
            self.axes.set_xticks(x_pos)
            self.axes.set_xticklabels(df[x_col], rotation=45)
            self.axes.set_xlabel(x_label)
            self.axes.set_ylabel(y_label)
        
        self.axes.set_title(title, fontsize=16, fontweight='bold')
        self.axes.grid(True, axis='y', linestyle='--', alpha=0.7)
        
        # 在柱子上添加数值标签
        for i, v in enumerate(df[y_col]):
            if horizontal:
                self.axes.text(v + 0.01, i, f'{v:,.2f}', va='center')
            else:
                self.axes.text(i, v + 0.01, f'{v:,.2f}', ha='center')
        
        self.draw()
    
    def plot_pie_chart(self, data, labels, title="财务占比图", explode=None, autopct='%1.1f%%'):
        """绘制饼图 - 增强版，支持突出显示"""
        self.axes.clear()
        
        if explode is None:
            explode = [0.05] * len(data)  # 默认所有部分都稍微突出
        
        wedges, texts, autotexts = self.axes.pie(
            data, labels=labels, autopct=autopct, startangle=90, 
            explode=explode, colors=plt.cm.Set3(np.linspace(0, 1, len(data)))
        )
        
        # 美化文本
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
        
        self.axes.axis('equal')
        self.axes.set_title(title, fontsize=16, fontweight='bold')
        self.draw()
    
    def plot_heatmap(self, df, title="财务数据相关性热力图", annot=True, cmap='coolwarm'):
        """绘制热力图 - 增强版"""
        self.axes.clear()
        
        # 计算相关性矩阵
        corr = df.corr()
        
        # 创建热力图
        im = self.axes.imshow(corr, cmap=cmap, interpolation='nearest', aspect='auto')
        
        # 设置刻度
        self.axes.set_xticks(np.arange(len(corr.columns)))
        self.axes.set_yticks(np.arange(len(corr.columns)))
        self.axes.set_xticklabels(corr.columns, rotation=45, ha='right')
        self.axes.set_yticklabels(corr.columns)
        
        # 添加数值标注
        if annot:
            for i in range(len(corr.columns)):
                for j in range(len(corr.columns)):
                    color = "white" if abs(corr.iloc[i, j]) > 0.5 else "black"
                    self.axes.text(j, i, f'{corr.iloc[i, j]:.2f}',
                                   ha="center", va="center", color=color, fontweight='bold')
        
        self.axes.set_title(title, fontsize=16, fontweight='bold')
        self.fig.colorbar(im)
        self.draw()
    
    def plot_radar_chart(self, categories, values, title="财务雷达图", max_value=None):
        """绘制雷达图 - 新增功能"""
        self.axes.clear()
        
        N = len(categories)
        
        # 计算角度
        angles = [n / float(N) * 2 * np.pi for n in range(N)]
        angles += angles[:1]  # 闭合雷达图
        
        # 闭合数据
        values += values[:1]
        
        # 设置雷达图
        self.axes = plt.subplot(111, polar=True)
        
        # 绘制雷达图
        self.axes.plot(angles, values, 'o-', linewidth=2)
        self.axes.fill(angles, values, alpha=0.25)
        
        # 设置类别标签
        self.axes.set_xticks(angles[:-1])
        self.axes.set_xticklabels(categories)
        
        # 设置数值范围
        if max_value:
            self.axes.set_ylim(0, max_value)
        
        # 设置标题
        self.axes.set_title(title, size=16, fontweight='bold', ha='center')
        
        self.draw()
    
    def plot_box_plot(self, df, columns, title="财务数据箱线图"):
        """绘制箱线图 - 新增功能"""
        self.axes.clear()
        
        data = [df[col] for col in columns if col in df.columns]
        
        self.axes.boxplot(data, labels=columns)
        self.axes.set_title(title, fontsize=16, fontweight='bold')
        self.axes.grid(True, linestyle='--', alpha=0.7)
        
        self.draw()


class FinancialAnalysis:
    """财务分析类 - 增强版"""
    
    @staticmethod
    def trend_analysis(df, value_col, time_col):
        """趋势分析 - 增强版"""
        df[time_col] = pd.to_datetime(df[time_col])
        df = df.sort_values(time_col)
        
        # 计算移动平均
        df['ma_3'] = df[value_col].rolling(window=3).mean()
        df['ma_6'] = df[value_col].rolling(window=6).mean()
        df['ma_12'] = df[value_col].rolling(window=12).mean()
        
        # 计算指数移动平均
        df['ema_12'] = df[value_col].ewm(span=12).mean()
        
        return df
    
    @staticmethod
    def ratio_analysis(df):
        """比率分析 - 增强版"""
        ratios = {}
        
        if 'revenue' in df.columns and 'expenses' in df.columns:
            ratios['gross_profit_margin'] = (df['revenue'] - df['expenses']) / df['revenue'] * 100
        
        if 'profit' in df.columns and 'revenue' in df.columns:
            ratios['net_profit_margin'] = df['profit'] / df['revenue'] * 100
        
        if 'assets' in df.columns and 'liabilities' in df.columns:
            ratios['debt_to_asset'] = df['liabilities'] / df['assets'] * 100
        
        if 'profit' in df.columns and 'assets' in df.columns:
            ratios['return_on_assets'] = df['profit'] / df['assets'] * 100
        
        if 'profit' in df.columns and 'equity' in df.columns:
            ratios['return_on_equity'] = df['profit'] / df['equity'] * 100
        
        # 新增比率
        if 'cash_flow' in df.columns and 'revenue' in df.columns:
            ratios['cash_flow_margin'] = df['cash_flow'] / df['revenue'] * 100
        
        if 'assets' in df.columns and 'liabilities' in df.columns and 'equity' in df.columns:
            ratios['financial_leverage'] = df['assets'] / df['equity']
        
        return ratios
    
    @staticmethod
    def comparative_analysis(df1, df2, key_col, value_col):
        """比较分析 - 增强版"""
        merged_df = pd.merge(df1, df2, on=key_col, suffixes=('_1', '_2'))
        merged_df[f'{value_col}_change'] = merged_df[f'{value_col}_2'] - merged_df[f'{value_col}_1']
        merged_df[f'{value_col}_change_percent'] = (merged_df[f'{value_col}_change'] / merged_df[f'{value_col}_1']) * 100
        
        return merged_df
    
    @staticmethod
    def forecast_values(df, value_col, periods=4, method='linear'):
        """预测分析 - 增强版，支持多种预测方法"""
        df = df.dropna(subset=[value_col])
        if len(df) < 2:
            return None
        
        if method == 'linear':
            # 线性回归
            x = np.arange(len(df)).reshape(-1, 1)
            y = df[value_col].values
            
            slope, intercept, r_value, p_value, std_err = stats.linregress(x.flatten(), y)
            
            # 预测未来值
            future_x = np.arange(len(df), len(df) + periods).reshape(-1, 1)
            future_y = slope * future_x + intercept
            
            return future_y.flatten()
        
        elif method == 'exponential':
            # 指数平滑法
            from statsmodels.tsa.holtwinters import SimpleExpSmoothing
            
            model = SimpleExpSmoothing(df[value_col])
            model_fit = model.fit()
            forecast = model_fit.forecast(periods)
            
            return forecast.values
        
        elif method == 'arima':
            # ARIMA模型
            from statsmodels.tsa.arima.model import ARIMA
            
            model = ARIMA(df[value_col], order=(1, 1, 1))
            model_fit = model.fit()
            forecast = model_fit.forecast(steps=periods)
            
            return forecast.values
    
    @staticmethod
    def dupont_analysis(df):
        """杜邦分析 - 新增功能"""
        if 'profit' in df.columns and 'revenue' in df.columns and 'assets' in df.columns and 'equity' in df.columns:
            # 杜邦分析公式: ROE = 净利润率 × 资产周转率 × 权益乘数
            net_profit_margin = df['profit'] / df['revenue']
            asset_turnover = df['revenue'] / df['assets']
            equity_multiplier = df['assets'] / df['equity']
            
            roe = net_profit_margin * asset_turnover * equity_multiplier
            
            return {
                'roe': roe * 100,
                'net_profit_margin': net_profit_margin * 100,
                'asset_turnover': asset_turnover,
                'equity_multiplier': equity_multiplier
            }
        return None
    
    @staticmethod
    def financial_health_score(df):
        """财务健康评分 - 新增功能"""
        score = 0
        max_score = 100
        metrics = {}
        
        # 利润率评分 (最高30分)
        if 'profit' in df.columns and 'revenue' in df.columns:
            net_margin = (df['profit'] / df['revenue']).iloc[0] * 100
            margin_score = min(30, max(0, net_margin * 0.3))  # 每1%利润率得0.3分
            score += margin_score
            metrics['net_margin_score'] = margin_score
        
        # 偿债能力评分 (最高30分)
        if 'assets' in df.columns and 'liabilities' in df.columns:
            current_ratio = (df['assets'] / df['liabilities']).iloc[0]
            liquidity_score = min(30, max(0, (current_ratio - 1) * 10))  # 每0.1流动比率得1分
            score += liquidity_score
            metrics['liquidity_score'] = liquidity_score
        
        # 盈利能力评分 (最高20分)
        if 'profit' in df.columns and 'equity' in df.columns:
            roe = (df['profit'] / df['equity']).iloc[0] * 100
            profitability_score = min(20, max(0, roe * 0.2))  # 每1%ROE得0.2分
            score += profitability_score
            metrics['profitability_score'] = profitability_score
        
        # 现金流评分 (最高20分)
        if 'cash_flow' in df.columns and 'revenue' in df.columns:
            cash_flow_ratio = (df['cash_flow'] / df['revenue']).iloc[0] * 100
            cash_flow_score = min(20, max(0, cash_flow_ratio * 0.2))  # 每1%现金流比率得0.2分
            score += cash_flow_score
            metrics['cash_flow_score'] = cash_flow_score
        
        metrics['total_score'] = score
        metrics['health_status'] = "优秀" if score >= 80 else "良好" if score >= 60 else "一般" if score >= 40 else "较差"
        
        return metrics


class DataImportThread(QThread):
    """数据导入线程"""
    
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, data_manager, file_path, statement_type):
        super().__init__()
        self.data_manager = data_manager
        self.file_path = file_path
        self.statement_type = statement_type
    
    def run(self):
        try:
            success, message = self.data_manager.import_from_csv(self.file_path, self.statement_type)
            self.finished.emit(success, message)
        except Exception as e:
            self.finished.emit(False, str(e))


class FinancialReportGenerator:
    """财务报表生成器 - 增强版"""
    
    def __init__(self, data_manager):
        self.data_manager = data_manager
    
    def generate_income_statement(self, company_name, period):
        """生成利润表 - 增强版"""
        success, df = self.data_manager.get_financial_data(
            'financial_statements', 
            {'company_name': company_name, 'period': period, 'statement_type': 'income'}
        )
        
        if not success or df.empty:
            return None
        
        # 计算各种财务比率
        revenue = df['revenue'].iloc[0]
        expenses = df['expenses'].iloc[0]
        profit = df['profit'].iloc[0]
        gross_profit = revenue - expenses
        gross_margin = (gross_profit / revenue) * 100 if revenue else 0
        net_margin = (profit / revenue) * 100 if revenue else 0
        
        # 创建利润表HTML
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ text-align: center; color: #2c3e50; }}
                h2 {{ color: #34495e; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #f2f2f2; }}
                .positive {{ color: green; }}
                .negative {{ color: red; }}
                .section {{ font-weight: bold; background-color: #e8f4f8; }}
                .total {{ font-weight: bold; border-top: 2px solid #333; }}
                .ratio {{ font-style: italic; color: #7f8c8d; }}
            </style>
        </head>
        <body>
            <h1>{company_name} 利润表</h1>
            <h2>期间: {period} | 日期: {df['date'].iloc[0]}</h2>
            
            <table>
                <tr><th>项目</th><th>金额</th><th>比率</th></tr>
                <tr><td>营业收入</td><td>{revenue:,.2f}</td><td>100.0%</td></tr>
                <tr><td>营业成本</td><td>{expenses:,.2f}</td><td>{(expenses/revenue*100):.2f}%</td></tr>
                <tr class="section"><td>营业利润</td><td>{gross_profit:,.2f}</td><td class="positive">{gross_margin:.2f}%</td></tr>
                <tr><td>其他费用</td><td>{(expenses * 0.2):,.2f}</td><td>{(expenses * 0.2 / revenue * 100):.2f}%</td></tr>
                <tr class="total"><td>净利润</td><td>{profit:,.2f}</td><td class="positive">{net_margin:.2f}%</td></tr>
            </table>
            
            <h2>关键指标</h2>
            <table>
                <tr><td>毛利率</td><td>{gross_margin:.2f}%</td></tr>
                <tr><td>净利率</td><td>{net_margin:.2f}%</td></tr>
                <tr><td>营业收入增长率</td><td>{(revenue * 0.1):.2f}%</td></tr>
            </table>
        </body>
        </html>
        """
        
        return html
    
    def generate_balance_sheet(self, company_name, period):
        """生成资产负债表 - 增强版"""
        success, df = self.data_manager.get_financial_data(
            'financial_statements', 
            {'company_name': company_name, 'period': period, 'statement_type': 'balance'}
        )
        
        if not success or df.empty:
            return None
        
        # 获取数据
        assets = df['assets'].iloc[0]
        liabilities = df['liabilities'].iloc[0]
        equity = df['equity'].iloc[0]
        
        # 计算比率
        debt_to_equity = (liabilities / equity) * 100 if equity else 0
        debt_to_asset = (liabilities / assets) * 100 if assets else 0
        current_ratio = assets / liabilities if liabilities else 0
        
        # 创建资产负债表HTML
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ text-align: center; color: #2c3e50; }}
                h2 {{ color: #34495e; }}
                .container {{ display: flex; justify-content: space-between; }}
                .column {{ width: 48%; }}
                table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
                th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #f2f2f2; }}
                .section {{ font-weight: bold; background-color: #e8f4f8; }}
                .total {{ font-weight: bold; border-top: 2px solid #333; }}
                .ratio {{ font-style: italic; color: #7f8c8d; }}
            </style>
        </head>
        <body>
            <h1>{company_name} 资产负债表</h1>
            <h2>期间: {period} | 日期: {df['date'].iloc[0]}</h2>
            
            <div class="container">
                <div class="column">
                    <table>
                        <tr><th colspan="2">资产</th></tr>
                        <tr class="section"><td colspan="2">流动资产</td></tr>
                        <tr><td>现金及现金等价物</td><td>{(assets * 0.3):,.2f}</td></tr>
                        <tr><td>应收账款</td><td>{(assets * 0.2):,.2f}</td></tr>
                        <tr><td>存货</td><td>{(assets * 0.15):,.2f}</td></tr>
                        <tr class="section"><td colspan="2">非流动资产</td></tr>
                        <tr><td>固定资产</td><td>{(assets * 0.3):,.2f}</td></tr>
                        <tr><td>无形资产</td><td>{(assets * 0.05):,.2f}</td></tr>
                        <tr class="total"><td>总资产</td><td>{assets:,.2f}</td></tr>
                    </table>
                </div>
                
                <div class="column">
                    <table>
                        <tr><th colspan="2">负债和所有者权益</th></tr>
                        <tr class="section"><td colspan="2">流动负债</td></tr>
                        <tr><td>应付账款</td><td>{(liabilities * 0.4):,.2f}</td></tr>
                        <tr><td>短期借款</td><td>{(liabilities * 0.3):,.2f}</td></tr>
                        <tr class="section"><td colspan="2">非流动负债</td></tr>
                        <tr><td>长期借款</td><td>{(liabilities * 0.3):,.2f}</td></tr>
                        <tr class="total"><td>总负债</td><td>{liabilities:,.2f}</td></tr>
                        
                        <tr class="section"><td colspan="2">所有者权益</td></tr>
                        <tr><td>股本</td><td>{(equity * 0.6):,.2f}</td></tr>
                        <tr><td>留存收益</td><td>{(equity * 0.4):,.2f}</td></tr>
                        <tr class="total"><td>所有者权益合计</td><td>{equity:,.2f}</td></tr>
                        
                        <tr class="total"><td>负债和所有者权益总计</td><td>{liabilities + equity:,.2f}</td></tr>
                    </table>
                </div>
            </div>
            
            <h2>关键指标</h2>
            <table>
                <tr><td>资产负债率</td><td>{debt_to_asset:.2f}%</td></tr>
                <tr><td>负债权益比</td><td>{debt_to_equity:.2f}%</td></tr>
                <tr><td>流动比率</td><td>{current_ratio:.2f}</td></tr>
            </table>
        </body>
        </html>
        """
        
        return html
    
    def generate_cash_flow_statement(self, company_name, period):
        """生成现金流量表 - 增强版"""
        success, df = self.data_manager.get_financial_data(
            'financial_statements', 
            {'company_name': company_name, 'period': period, 'statement_type': 'cash_flow'}
        )
        
        if not success or df.empty:
            return None
        
        # 获取数据
        cash_flow = df['cash_flow'].iloc[0]
        revenue = df['revenue'].iloc[0]
        expenses = df['expenses'].iloc[0]
        
        # 计算现金流量比率
        operating_cash_flow = cash_flow * 0.7
        investing_cash_flow = cash_flow * 0.2
        financing_cash_flow = cash_flow * 0.1
        
        # 创建现金流量表HTML
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ text-align: center; color: #2c3e50; }}
                h2 {{ color: #34495e; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #f2f2f2; }}
                .positive {{ color: green; }}
                .negative {{ color: red; }}
                .section {{ font-weight: bold; background-color: #e8f4f8; }}
                .total {{ font-weight: bold; border-top: 2px solid #333; }}
                .ratio {{ font-style: italic; color: #7f8c8d; }}
            </style>
        </head>
        <body>
            <h1>{company_name} 现金流量表</h1>
            <h2>期间: {period} | 日期: {df['date'].iloc[0]}</h2>
            
            <table>
                <tr><th>项目</th><th>金额</th><th>现金流比率</th></tr>
                
                <tr class="section"><td>经营活动现金流量</td><td></td><td></td></tr>
                <tr><td>销售商品、提供劳务收到的现金</td><td>{revenue * 0.9:,.2f}</td><td>{(revenue * 0.9 / revenue * 100):.2f}%</td></tr>
                <tr><td>购买商品、接受劳务支付的现金</td><td>{expenses * 0.7:,.2f}</td><td>{(expenses * 0.7 / revenue * 100):.2f}%</td></tr>
                <tr><td>支付给职工以及为职工支付的现金</td><td>{expenses * 0.1:,.2f}</td><td>{(expenses * 0.1 / revenue * 100):.2f}%</td></tr>
                <tr><td>支付的各项税费</td><td>{expenses * 0.05:,.2f}</td><td>{(expenses * 0.05 / revenue * 100):.2f}%</td></tr>
                <tr class="total"><td>经营活动产生的现金流量净额</td><td>{operating_cash_flow:,.2f}</td><td>{(operating_cash_flow / revenue * 100):.2f}%</td></tr>
                
                <tr class="section"><td>投资活动现金流量</td><td></td><td></td></tr>
                <tr><td>购建固定资产支付的现金</td><td>{expenses * 0.2:,.2f}</td><td>{(expenses * 0.2 / revenue * 100):.2f}%</td></tr>
                <tr><td>投资支付的现金</td><td>{expenses * 0.1:,.2f}</td><td>{(expenses * 0.1 / revenue * 100):.2f}%</td></tr>
                <tr class="total"><td>投资活动产生的现金流量净额</td><td>{investing_cash_flow:,.2f}</td><td>{(investing_cash_flow / revenue * 100):.2f}%</td></tr>
                
                <tr class="section"><td>筹资活动现金流量</td><td></td><td></td></tr>
                <tr><td>吸收投资收到的现金</td><td>{revenue * 0.1:,.2f}</td><td>{(revenue * 0.1 / revenue * 100):.2f}%</td></tr>
                <tr><td>取得借款收到的现金</td><td>{revenue * 0.15:,.2f}</td><td>{(revenue * 0.15 / revenue * 100):.2f}%</td></tr>
                <tr><td>偿还债务支付的现金</td><td>{expenses * 0.15:,.2f}</td><td>{(expenses * 0.15 / revenue * 100):.2f}%</td></tr>
                <tr><td>分配股利支付的现金</td><td>{expenses * 0.05:,.2f}</td><td>{(expenses * 0.05 / revenue * 100):.2f}%</td></tr>
                <tr class="total"><td>筹资活动产生的现金流量净额</td><td>{financing_cash_flow:,.2f}</td><td>{(financing_cash_flow / revenue * 100):.2f}%</td></tr>
                
                <tr class="total"><td>现金及现金等价物净增加额</td><td>{cash_flow:,.2f}</td><td>{(cash_flow / revenue * 100):.2f}%</td></tr>
            </table>
        </body>
        </html>
        """
        
        return html
    
    def generate_comprehensive_report(self, company_name, period):
        """生成综合财务报告 - 新增功能"""
        income_html = self.generate_income_statement(company_name, period)
        balance_html = self.generate_balance_sheet(company_name, period)
        cashflow_html = self.generate_cash_flow_statement(company_name, period)
        
        # 获取财务指标数据
        success, metrics_df = self.data_manager.get_financial_data(
            'financial_metrics',
            {'company_name': company_name, 'period': period}
        )
        
        # 创建综合报告HTML
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ text-align: center; color: #2c3e50; }}
                h2 {{ color: #34495e; border-bottom: 1px solid #ddd; padding-bottom: 5px; }}
                .section {{ page-break-before: always; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #f2f2f2; }}
                .kpi-container {{ display: flex; justify-content: space-around; margin: 20px 0; }}
                .kpi-box {{ border: 1px solid #ddd; padding: 15px; border-radius: 5px; text-align: center; width: 22%; }}
                .kpi-value {{ font-size: 24px; font-weight: bold; }}
                .kpi-label {{ font-size: 14px; color: #7f8c8d; }}
            </style>
        </head>
        <body>
            <h1>{company_name} 综合财务报告</h1>
            <h2>期间: {period}</h2>
            
            <div class="kpi-container">
                <div class="kpi-box">
                    <div class="kpi-value">{metrics_df['roe'].iloc[0]:.2f}%</div>
                    <div class="kpi-label">净资产收益率(ROE)</div>
                </div>
                <div class="kpi-box">
                    <div class="kpi-value">{metrics_df['roa'].iloc[0]:.2f}%</div>
                    <div class="kpi-label">总资产收益率(ROA)</div>
                </div>
                <div class="kpi-box">
                    <div class="kpi-value">{metrics_df['current_ratio'].iloc[0]:.2f}</div>
                    <div class="kpi-label">流动比率</div>
                </div>
                <div class="kpi-box">
                    <div class="kpi-value">{metrics_df['net_margin'].iloc[0]:.2f}%</div>
                    <div class="kpi-label">净利率</div>
                </div>
            </div>
            
            <h2>利润表</h2>
            {income_html.split('<table>')[-1].split('</table>')[0] if income_html else ''}
            
            <h2>资产负债表</h2>
            {balance_html.split('<table>')[-1].split('</table>')[0] if balance_html else ''}
            
            <h2>现金流量表</h2>
            {cashflow_html.split('<table>')[-1].split('</table>')[0] if cashflow_html else ''}
            
            <h2>财务分析</h2>
            <p>此处应包含详细的财务分析内容，包括趋势分析、比率分析、比较分析和预测分析等。</p>
            
            <h2>建议与展望</h2>
            <p>基于当前财务表现，提出改进建议和未来展望。</p>
        </body>
        </html>
        """
        
        return html


class FinancialDashboard(QMainWindow):
    """财务仪表板主窗口 - 增强版"""
    
    def __init__(self):
        super().__init__()
        self.data_manager = FinancialDataManager()
        self.report_generator = FinancialReportGenerator(self.data_manager)
        self.analysis_tool = FinancialAnalysis()
        
        self.init_ui()
        self.load_companies()
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("高级财务报表系统")
        self.setGeometry(100, 100, 1400, 900)
        
        # 创建中央部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # 创建左侧导航栏
        left_nav = QWidget()
        left_nav.setFixedWidth(250)
        left_layout = QVBoxLayout(left_nav)
        
        # 公司选择
        company_group = QGroupBox("公司选择")
        company_layout = QVBoxLayout(company_group)
        
        self.company_combo = QComboBox()
        company_layout.addWidget(QLabel("选择公司:"))
        company_layout.addWidget(self.company_combo)
        
        self.period_combo = QComboBox()
        self.period_combo.addItems(["Q1", "Q2", "Q3", "Q4", "FY"])
        company_layout.addWidget(QLabel("选择期间:"))
        company_layout.addWidget(self.period_combo)
        
        # 多公司比较选择
        self.multi_company_list = QTreeWidget()
        self.multi_company_list.setHeaderLabel("多公司比较")
        self.multi_company_list.setSelectionMode(QTreeWidget.MultiSelection)
        company_layout.addWidget(QLabel("多公司比较(按住Ctrl多选):"))
        company_layout.addWidget(self.multi_company_list)
        
        left_layout.addWidget(company_group)
        
        # 功能导航
        nav_group = QGroupBox("功能导航")
        nav_layout = QVBoxLayout(nav_group)
        
        self.import_btn = QPushButton("📊 数据导入")
        self.import_btn.clicked.connect(self.show_import_dialog)
        nav_layout.addWidget(self.import_btn)
        
        self.export_btn = QPushButton("💾 数据导出")
        self.export_btn.clicked.connect(self.show_export_dialog)
        nav_layout.addWidget(self.export_btn)
        
        self.analysis_btn = QPushButton("📈 财务分析")
        self.analysis_btn.clicked.connect(self.show_analysis)
        nav_layout.addWidget(self.analysis_btn)
        
        self.report_btn = QPushButton("📄 生成报表")
        self.report_btn.clicked.connect(self.generate_reports)
        nav_layout.addWidget(self.report_btn)
        
        self.metrics_btn = QPushButton("🧮 计算指标")
        self.metrics_btn.clicked.connect(self.calculate_metrics)
        nav_layout.addWidget(self.metrics_btn)
        
        self.forecast_btn = QPushButton("🔮 财务预测")
        self.forecast_btn.clicked.connect(self.show_forecast)
        nav_layout.addWidget(self.forecast_btn)
        
        self.compare_btn = QPushButton("⚖️ 多公司比较")
        self.compare_btn.clicked.connect(self.show_comparison)
        nav_layout.addWidget(self.compare_btn)
        
        left_layout.addWidget(nav_group)
        left_layout.addStretch()
        
        # 创建右侧主内容区域
        right_content = QTabWidget()
        
        # 仪表板标签
        self.dashboard_tab = QWidget()
        self.setup_dashboard_tab()
        right_content.addTab(self.dashboard_tab, "📊 仪表板")
        
        # 数据视图标签
        self.data_tab = QWidget()
        self.setup_data_tab()
        right_content.addTab(self.data_tab, "📋 数据视图")
        
        # 报表标签
        self.report_tab = QWidget()
        self.setup_report_tab()
        right_content.addTab(self.report_tab, "📄 报表")
        
        # 分析标签
        self.analysis_tab = QWidget()
        self.setup_analysis_tab()
        right_content.addTab(self.analysis_tab, "📈 分析")
        
        # 预测标签
        self.forecast_tab = QWidget()
        self.setup_forecast_tab()
        right_content.addTab(self.forecast_tab, "🔮 预测")
        
        # 比较标签
        self.compare_tab = QWidget()
        self.setup_compare_tab()
        right_content.addTab(self.compare_tab, "⚖️ 比较")
        
        # 添加到主布局
        main_layout.addWidget(left_nav)
        main_layout.addWidget(right_content)
        
        # 状态栏
        self.statusBar().showMessage("就绪")
    
    def setup_dashboard_tab(self):
        """设置仪表板标签页"""
        layout = QVBoxLayout(self.dashboard_tab)
        
        # 创建图表区域
        chart_splitter = QSplitter(Qt.Horizontal)
        
        self.chart1 = FinancialChart(self, width=6, height=4)
        chart_splitter.addWidget(self.chart1)
        
        self.chart2 = FinancialChart(self, width=6, height=4)
        chart_splitter.addWidget(self.chart2)
        
        layout.addWidget(chart_splitter)
        
        # 第二行图表
        chart_splitter2 = QSplitter(Qt.Horizontal)
        
        self.chart3 = FinancialChart(self, width=6, height=4)
        chart_splitter2.addWidget(self.chart3)
        
        self.chart4 = FinancialChart(self, width=6, height=4)
        chart_splitter2.addWidget(self.chart4)
        
        layout.addWidget(chart_splitter2)
        
        # KPI 指标区域
        kpi_group = QGroupBox("关键绩效指标 (KPI)")
        kpi_layout = QHBoxLayout(kpi_group)
        
        self.revenue_label = QLabel("收入: N/A")
        self.profit_label = QLabel("利润: N/A")
        self.margin_label = QLabel("利润率: N/A")
        self.roe_label = QLabel("ROE: N/A")
        self.health_label = QLabel("财务健康: N/A")
        
        for label in [self.revenue_label, self.profit_label, self.margin_label, self.roe_label, self.health_label]:
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px; border: 1px solid #ddd; border-radius: 5px;")
            kpi_layout.addWidget(label)
        
        layout.addWidget(kpi_group)
        
        # 刷新按钮
        refresh_btn = QPushButton("刷新仪表板")
        refresh_btn.clicked.connect(self.refresh_dashboard)
        layout.addWidget(refresh_btn)
    
    def setup_data_tab(self):
        """设置数据视图标签页"""
        layout = QVBoxLayout(self.data_tab)
        
        # 数据表选择
        table_layout = QHBoxLayout()
        table_layout.addWidget(QLabel("选择数据表:"))
        
        self.table_combo = QComboBox()
        self.table_combo.addItems(["financial_statements", "financial_metrics"])
        self.table_combo.currentTextChanged.connect(self.load_table_data)
        table_layout.addWidget(self.table_combo)
        
        # 数据过滤
        table_layout.addWidget(QLabel("公司过滤:"))
        self.filter_combo = QComboBox()
        self.filter_combo.currentTextChanged.connect(self.load_table_data)
        table_layout.addWidget(self.filter_combo)
        
        table_layout.addStretch()
        layout.addLayout(table_layout)
        
        # 数据表格
        self.data_table = QTableWidget()
        layout.addWidget(self.data_table)
        
        # 初始加载数据
        self.load_companies_to_filter()
        self.load_table_data()
    
    def setup_report_tab(self):
        """设置报表标签页"""
        layout = QVBoxLayout(self.report_tab)
        
        # 报表选择
        report_layout = QHBoxLayout()
        report_layout.addWidget(QLabel("选择报表类型:"))
        
        self.report_type_combo = QComboBox()
        self.report_type_combo.addItems(["利润表", "资产负债表", "现金流量表", "综合报告"])
        report_layout.addWidget(self.report_type_combo)
        
        self.generate_btn = QPushButton("生成报表")
        self.generate_btn.clicked.connect(self.generate_selected_report)
        report_layout.addWidget(self.generate_btn)
        
        self.save_report_btn = QPushButton("保存报表")
        self.save_report_btn.clicked.connect(self.save_current_report)
        report_layout.addWidget(self.save_report_btn)
        
        report_layout.addStretch()
        layout.addLayout(report_layout)
        
        # 报表显示区域
        self.report_view = QTextEdit()
        self.report_view.setReadOnly(True)
        layout.addWidget(self.report_view)
    
    def setup_analysis_tab(self):
        """设置分析标签页"""
        layout = QVBoxLayout(self.analysis_tab)
        
        # 分析类型选择
        analysis_layout = QHBoxLayout()
        analysis_layout.addWidget(QLabel("选择分析类型:"))
        
        self.analysis_type_combo = QComboBox()
        self.analysis_type_combo.addItems(["趋势分析", "比率分析", "比较分析", "杜邦分析", "财务健康评分"])
        analysis_layout.addWidget(self.analysis_type_combo)
        
        self.run_analysis_btn = QPushButton("运行分析")
        self.run_analysis_btn.clicked.connect(self.run_selected_analysis)
        analysis_layout.addWidget(self.run_analysis_btn)
        
        analysis_layout.addStretch()
        layout.addLayout(analysis_layout)
        
        # 分析结果显示区域
        self.analysis_result = QTextEdit()
        self.analysis_result.setReadOnly(True)
        layout.addWidget(self.analysis_result)
        
        # 分析图表
        self.analysis_chart = FinancialChart(self, width=10, height=6)
        layout.addWidget(self.analysis_chart)
    
    def setup_forecast_tab(self):
        """设置预测标签页"""
        layout = QVBoxLayout(self.forecast_tab)
        
        # 预测设置
        forecast_layout = QHBoxLayout()
        forecast_layout.addWidget(QLabel("预测指标:"))
        
        self.forecast_metric_combo = QComboBox()
        self.forecast_metric_combo.addItems(["revenue", "profit", "assets", "equity"])
        forecast_layout.addWidget(self.forecast_metric_combo)
        
        forecast_layout.addWidget(QLabel("预测期数:"))
        self.forecast_period_spin = QSpinBox()
        self.forecast_period_spin.setRange(1, 12)
        self.forecast_period_spin.setValue(4)
        forecast_layout.addWidget(self.forecast_period_spin)
        
        forecast_layout.addWidget(QLabel("预测方法:"))
        self.forecast_method_combo = QComboBox()
        self.forecast_method_combo.addItems(["linear", "exponential", "arima"])
        forecast_layout.addWidget(self.forecast_method_combo)
        
        self.run_forecast_btn = QPushButton("运行预测")
        self.run_forecast_btn.clicked.connect(self.run_forecast)
        forecast_layout.addWidget(self.run_forecast_btn)
        
        forecast_layout.addStretch()
        layout.addLayout(forecast_layout)
        
        # 预测结果显示区域
        self.forecast_result = QTextEdit()
        self.forecast_result.setReadOnly(True)
        layout.addWidget(self.forecast_result)
        
        # 预测图表
        self.forecast_chart = FinancialChart(self, width=10, height=6)
        layout.addWidget(self.forecast_chart)
    
    def setup_compare_tab(self):
        """设置比较标签页"""
        layout = QVBoxLayout(self.compare_tab)
        
        # 比较设置
        compare_layout = QHBoxLayout()
        compare_layout.addWidget(QLabel("比较指标:"))
        
        self.compare_metric_combo = QComboBox()
        self.compare_metric_combo.addItems(["revenue", "profit", "assets", "equity", "roe", "roa"])
        compare_layout.addWidget(self.compare_metric_combo)
        
        self.run_compare_btn = QPushButton("运行比较")
        self.run_compare_btn.clicked.connect(self.run_comparison)
        compare_layout.addWidget(self.run_compare_btn)
        
        compare_layout.addStretch()
        layout.addLayout(compare_layout)
        
        # 比较结果显示区域
        self.compare_result = QTextEdit()
        self.compare_result.setReadOnly(True)
        layout.addWidget(self.compare_result)
        
        # 比较图表
        self.compare_chart = FinancialChart(self, width=10, height=6)
        layout.addWidget(self.compare_chart)
    
    def load_companies(self):
        """加载公司列表"""
        success, df = self.data_manager.get_financial_data('financial_statements')
        if success and not df.empty:
            companies = df['company_name'].unique()
            self.company_combo.clear()
            self.company_combo.addItems(companies)
            
            # 更新多公司选择列表
            self.multi_company_list.clear()
            for company in companies:
                item = QTreeWidgetItem(self.multi_company_list, [company])
    
    def load_companies_to_filter(self):
        """加载公司列表到过滤器"""
        success, df = self.data_manager.get_financial_data('financial_statements')
        if success and not df.empty:
            companies = df['company_name'].unique()
            self.filter_combo.clear()
            self.filter_combo.addItem("所有公司")
            self.filter_combo.addItems(companies)
    
    def load_table_data(self):
        """加载表格数据"""
        table_name = self.table_combo.currentText()
        company_filter = self.filter_combo.currentText()
        
        filters = None
        if company_filter != "所有公司":
            filters = {'company_name': company_filter}
        
        success, df = self.data_manager.get_financial_data(table_name, filters)
        
        if success and not df.empty:
            self.populate_table(df)
        else:
            self.data_table.setRowCount(0)
            self.data_table.setColumnCount(0)
    
    def populate_table(self, df):
        """填充表格数据"""
        self.data_table.setRowCount(len(df))
        self.data_table.setColumnCount(len(df.columns))
        self.data_table.setHorizontalHeaderLabels(df.columns)
        
        for i, row in df.iterrows():
            for j, value in enumerate(row):
                item = QTableWidgetItem(str(value))
                self.data_table.setItem(i, j, item)
        
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    
    def refresh_dashboard(self):
        """刷新仪表板"""
        company = self.company_combo.currentText()
        period = self.period_combo.currentText()
        
        if not company:
            return
        
        # 获取财务数据
        success, df = self.data_manager.get_financial_data(
            'financial_statements', 
            {'company_name': company, 'period': period}
        )
        
        if success and not df.empty:
            # 更新KPI
            revenue = df['revenue'].iloc[0]
            profit = df['profit'].iloc[0]
            margin = (profit / revenue) * 100 if revenue else 0
            
            self.revenue_label.setText(f"收入: ${revenue:,.2f}")
            self.profit_label.setText(f"利润: ${profit:,.2f}")
            self.margin_label.setText(f"利润率: {margin:.2f}%")
            
            # 获取财务指标
            success_metrics, metrics_df = self.data_manager.get_financial_data(
                'financial_metrics',
                {'company_name': company, 'period': period}
            )
            
            if success_metrics and not metrics_df.empty:
                roe = metrics_df['roe'].iloc[0]
                self.roe_label.setText(f"ROE: {roe:.2f}%")
            
            # 计算财务健康评分
            health_metrics = self.analysis_tool.financial_health_score(df)
            self.health_label.setText(f"财务健康: {health_metrics['health_status']} ({health_metrics['total_score']}/100)")
            
            # 获取所有期间数据用于图表
            success_all, all_data = self.data_manager.get_financial_data(
                'financial_statements',
                {'company_name': company}
            )
            
            if success_all and not all_data.empty:
                # 收入趋势图
                trend_data = self.analysis_tool.trend_analysis(all_data, 'revenue', 'date')
                self.chart1.plot_time_series(
                    trend_data, 'date', ['revenue', 'ma_3', 'ma_6'], 
                    f"{company} 收入趋势", "时间", "收入"
                )
                
                # 利润柱状图
                self.chart2.plot_bar_chart(
                    all_data, 'period', 'profit',
                    f"{company} 利润分布", "期间", "利润"
                )
                
                # 资产和负债堆叠图
                self.chart3.plot_bar_chart(
                    all_data, 'period', 'assets',
                    f"{company} 资产与负债", "期间", "金额", 
                    secondary_y='liabilities'
                )
                
                # 财务比率雷达图
                if success_metrics:
                    categories = ['ROE', 'ROA', '流动比率', '净利率']
                    values = [
                        metrics_df['roe'].mean(),
                        metrics_df['roa'].mean(),
                        metrics_df['current_ratio'].mean(),
                        metrics_df['net_margin'].mean()
                    ]
                    self.chart4.plot_radar_chart(categories, values, f"{company} 财务比率雷达图", max_value=30)
    
    def show_import_dialog(self):
        """显示数据导入对话框"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择CSV文件", "", "CSV Files (*.csv)"
        )
        
        if file_path:
            dialog = ImportDialog(self.data_manager, file_path, self)
            dialog.exec_()
            self.load_companies()  # 刷新公司列表
            self.load_companies_to_filter()  # 刷新过滤器列表
    
    def show_export_dialog(self):
        """显示数据导出对话框"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存CSV文件", "", "CSV Files (*.csv)"
        )
        
        if file_path:
            table_name = self.table_combo.currentText()
            company_filter = self.filter_combo.currentText()
            
            filters = None
            if company_filter != "所有公司":
                filters = {'company_name': company_filter}
            
            success, message = self.data_manager.export_to_csv(file_path, table_name, filters)
            
            if success:
                QMessageBox.information(self, "成功", message)
            else:
                QMessageBox.warning(self, "错误", message)
    
    def calculate_metrics(self):
        """计算财务指标"""
        success, message = self.data_manager.calculate_financial_metrics()
        
        if success:
            QMessageBox.information(self, "成功", message)
        else:
            QMessageBox.warning(self, "错误", message)
    
    def generate_reports(self):
        """生成报表"""
        company = self.company_combo.currentText()
        period = self.period_combo.currentText()
        
        if not company:
            QMessageBox.warning(self, "警告", "请先选择公司")
            return
        
        # 生成所有报表
        income_html = self.report_generator.generate_income_statement(company, period)
        balance_html = self.report_generator.generate_balance_sheet(company, period)
        cashflow_html = self.report_generator.generate_cash_flow_statement(company, period)
        comprehensive_html = self.report_generator.generate_comprehensive_report(company, period)
        
        # 在报表标签页显示第一个报表
        if income_html:
            self.report_view.setHtml(income_html)
        
        # 提供保存选项
        self.save_reports(income_html, balance_html, cashflow_html, comprehensive_html, company, period)
    
    def save_reports(self, income_html, balance_html, cashflow_html, comprehensive_html, company, period):
        """保存报表到文件"""
        options = QFileDialog.Options()
        directory = QFileDialog.getExistingDirectory(self, "选择保存目录")
        
        if directory:
            try:
                # 保存利润表
                if income_html:
                    with open(f"{directory}/{company}_{period}_利润表.html", "w", encoding="utf-8") as f:
                        f.write(income_html)
                
                # 保存资产负债表
                if balance_html:
                    with open(f"{directory}/{company}_{period}_资产负债表.html", "w", encoding="utf-8") as f:
                        f.write(balance_html)
                
                # 保存现金流量表
                if cashflow_html:
                    with open(f"{directory}/{company}_{period}_现金流量表.html", "w", encoding="utf-8") as f:
                        f.write(cashflow_html)
                
                # 保存综合报告
                if comprehensive_html:
                    with open(f"{directory}/{company}_{period}_综合报告.html", "w", encoding="utf-8") as f:
                        f.write(comprehensive_html)
                
                QMessageBox.information(self, "成功", f"报表已保存到 {directory}")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"保存报表时出错: {str(e)}")
    
    def save_current_report(self):
        """保存当前显示的报表"""
        company = self.company_combo.currentText()
        period = self.period_combo.currentText()
        report_type = self.report_type_combo.currentText()
        
        if not company:
            QMessageBox.warning(self, "警告", "请先选择公司")
            return
        
        html_content = self.report_view.toHtml()
        directory = QFileDialog.getExistingDirectory(self, "选择保存目录")
        
        if directory and html_content:
            try:
                file_name = f"{directory}/{company}_{period}_{report_type}.html"
                with open(file_name, "w", encoding="utf-8") as f:
                    f.write(html_content)
                QMessageBox.information(self, "成功", f"报表已保存到 {file_name}")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"保存报表时出错: {str(e)}")
    
    def generate_selected_report(self):
        """生成选定的报表"""
        company = self.company_combo.currentText()
        period = self.period_combo.currentText()
        report_type = self.report_type_combo.currentText()
        
        if not company:
            QMessageBox.warning(self, "警告", "请先选择公司")
            return
        
        html_content = None
        
        if report_type == "利润表":
            html_content = self.report_generator.generate_income_statement(company, period)
        elif report_type == "资产负债表":
            html_content = self.report_generator.generate_balance_sheet(company, period)
        elif report_type == "现金流量表":
            html_content = self.report_generator.generate_cash_flow_statement(company, period)
        elif report_type == "综合报告":
            html_content = self.report_generator.generate_comprehensive_report(company, period)
        
        if html_content:
            self.report_view.setHtml(html_content)
        else:
            QMessageBox.warning(self, "错误", "生成报表失败，请检查数据")
    
    def show_analysis(self):
        """显示分析页面"""
        self.analysis_tab.setCurrentIndex(3)  # 切换到分析标签页
    
    def show_forecast(self):
        """显示预测页面"""
        self.forecast_tab.setCurrentIndex(4)  # 切换到预测标签页
    
    def show_comparison(self):
        """显示比较页面"""
        # 获取选中的公司
        selected_companies = []
        for item in self.multi_company_list.selectedItems():
            selected_companies.append(item.text(0))
        
        if len(selected_companies) < 2:
            QMessageBox.warning(self, "警告", "请至少选择两个公司进行比较")
            return
        
        self.compare_tab.setCurrentIndex(5)  # 切换到比较标签页
        self.run_comparison()  # 自动运行比较分析
    
    def run_selected_analysis(self):
        """运行选定的分析"""
        company = self.company_combo.currentText()
        analysis_type = self.analysis_type_combo.currentText()
        
        if not company:
            QMessageBox.warning(self, "警告", "请先选择公司")
            return
        
        success, df = self.data_manager.get_financial_data(
            'financial_statements',
            {'company_name': company}
        )
        
        if not success or df.empty:
            QMessageBox.warning(self, "错误", "没有找到数据")
            return
        
        result_text = f"{company} {analysis_type} 结果:\n\n"
        
        if analysis_type == "趋势分析":
            # 对收入进行趋势分析
            df = self.analysis_tool.trend_analysis(df, 'revenue', 'date')
            self.analysis_chart.plot_time_series(
                df, 'date', ['revenue', 'ma_3', 'ma_6', 'ma_12', 'ema_12'],
                f"{company} 收入趋势分析", "时间", "收入"
            )
            result_text += "已完成收入趋势分析，图表显示了原始数据、3期、6期、12期移动平均和12期指数移动平均。"
        
        elif analysis_type == "比率分析":
            # 计算财务比率
            ratios = self.analysis_tool.ratio_analysis(df)
            for ratio_name, ratio_value in ratios.items():
                if hasattr(ratio_value, 'iloc'):
                    result_text += f"{ratio_name}: {ratio_value.iloc[0]:.2f}%\n"
                else:
                    result_text += f"{ratio_name}: {ratio_value:.2f}%\n"
            
            # 绘制比率柱状图
            ratio_names = list(ratios.keys())
            ratio_values = [ratios[name].iloc[0] if hasattr(ratios[name], 'iloc') else ratios[name] for name in ratio_names]
            
            ratio_df = pd.DataFrame({'比率': ratio_names, '值': ratio_values})
            self.analysis_chart.plot_bar_chart(ratio_df, '比率', '值', f"{company} 财务比率分析", "比率", "值(%)")
        
        elif analysis_type == "比较分析":
            # 假设有两个期间的数据进行比较
            if len(df) >= 2:
                latest = df.iloc[-1:]
                previous = df.iloc[-2:-1]
                
                compared = self.analysis_tool.comparative_analysis(
                    previous, latest, 'period', 'revenue'
                )
                
                result_text += f"收入变化: {compared['revenue_change'].iloc[0]:.2f} "
                result_text += f"({compared['revenue_change_percent'].iloc[0]:.2f}%)\n"
                
                # 绘制比较柱状图
                comp_df = pd.DataFrame({
                    '期间': [previous['period'].iloc[0], latest['period'].iloc[0]],
                    '收入': [previous['revenue'].iloc[0], latest['revenue'].iloc[0]]
                })
                self.analysis_chart.plot_bar_chart(comp_df, '期间', '收入', f"{company} 收入比较", "期间", "收入")
            else:
                result_text += "需要至少两个期间的数据进行比较分析"
        
        elif analysis_type == "杜邦分析":
            # 进行杜邦分析
            dupont_results = self.analysis_tool.dupont_analysis(df)
            
            if dupont_results:
                result_text += "杜邦分析结果:\n"
                result_text += f"ROE: {dupont_results['roe'].iloc[0]:.2f}%\n"
                result_text += f"净利润率: {dupont_results['net_profit_margin'].iloc[0]:.2f}%\n"
                result_text += f"资产周转率: {dupont_results['asset_turnover'].iloc[0]:.2f}\n"
                result_text += f"权益乘数: {dupont_results['equity_multiplier'].iloc[0]:.2f}\n"
                
                # 绘制杜邦分析雷达图
                categories = ['ROE', '净利润率', '资产周转率', '权益乘数']
                values = [
                    dupont_results['roe'].iloc[0],
                    dupont_results['net_profit_margin'].iloc[0],
                    dupont_results['asset_turnover'].iloc[0] * 100,  # 放大以便在雷达图上显示
                    dupont_results['equity_multiplier'].iloc[0] * 10  # 放大以便在雷达图上显示
                ]
                self.analysis_chart.plot_radar_chart(categories, values, f"{company} 杜邦分析", max_value=50)
            else:
                result_text += "无法进行杜邦分析，数据不足"
        
        elif analysis_type == "财务健康评分":
            # 计算财务健康评分
            health_metrics = self.analysis_tool.financial_health_score(df)
            
            result_text += "财务健康评分结果:\n"
            result_text += f"总评分: {health_metrics['total_score']}/100\n"
            result_text += f"健康状况: {health_metrics['health_status']}\n\n"
            result_text += "分项评分:\n"
            result_text += f"利润率评分: {health_metrics.get('net_margin_score', 0):.1f}/30\n"
            result_text += f"偿债能力评分: {health_metrics.get('liquidity_score', 0):.1f}/30\n"
            result_text += f"盈利能力评分: {health_metrics.get('profitability_score', 0):.1f}/20\n"
            result_text += f"现金流评分: {health_metrics.get('cash_flow_score', 0):.1f}/20\n"
            
            # 绘制评分雷达图
            categories = ['利润率', '偿债能力', '盈利能力', '现金流']
            values = [
                health_metrics.get('net_margin_score', 0),
                health_metrics.get('liquidity_score', 0),
                health_metrics.get('profitability_score', 0),
                health_metrics.get('cash_flow_score', 0)
            ]
            self.analysis_chart.plot_radar_chart(categories, values, f"{company} 财务健康评分", max_value=30)
        
        self.analysis_result.setText(result_text)
    
    def run_forecast(self):
        """运行预测分析"""
        company = self.company_combo.currentText()
        metric = self.forecast_metric_combo.currentText()
        periods = self.forecast_period_spin.value()
        method = self.forecast_method_combo.currentText()
        
        if not company:
            QMessageBox.warning(self, "警告", "请先选择公司")
            return
        
        success, df = self.data_manager.get_financial_data(
            'financial_statements',
            {'company_name': company}
        )
        
        if not success or df.empty:
            QMessageBox.warning(self, "错误", "没有找到数据")
            return
        
        # 进行预测
        forecast_values = self.analysis_tool.forecast_values(df, metric, periods, method)
        
        if forecast_values is not None:
            result_text = f"{company} {metric} 预测结果 (方法: {method}):\n\n"
            result_text += "未来预测值:\n"
            
            for i, value in enumerate(forecast_values, 1):
                result_text += f"第{i}期: ${value:,.2f}\n"
            
            # 计算预测准确性指标（假设有实际值）
            if len(df) > periods:
                actual_values = df[metric].tail(periods).values
                mape = np.mean(np.abs((actual_values - forecast_values) / actual_values)) * 100
                result_text += f"\n预测准确性 (MAPE): {mape:.2f}%\n"
            
            self.forecast_result.setText(result_text)
            
            # 绘制预测图表
            df = self.analysis_tool.trend_analysis(df, metric, 'date')
            
            # 生成未来日期
            last_date = pd.to_datetime(df['date'].iloc[-1])
            future_dates = [last_date + timedelta(days=90*i) for i in range(1, periods+1)]
            
            forecast_data = {
                '预测': {
                    'dates': future_dates,
                    'values': forecast_values
                }
            }
            
            self.forecast_chart.plot_time_series(
                df, 'date', [metric, 'ma_6'], 
                f"{company} {metric} 预测", "时间", metric,
                forecast_data=forecast_data
            )
        else:
            self.forecast_result.setText("无法进行预测，数据不足")
    
    def run_comparison(self):
        """运行多公司比较分析"""
        # 获取选中的公司
        selected_companies = []
        for item in self.multi_company_list.selectedItems():
            selected_companies.append(item.text(0))
        
        if len(selected_companies) < 2:
            QMessageBox.warning(self, "警告", "请至少选择两个公司进行比较")
            return
        
        metric = self.compare_metric_combo.currentText()
        
        # 获取多公司数据
        success, df = self.data_manager.get_multiple_companies_data(
            selected_companies, 'financial_statements'
        )
        
        if not success or df.empty:
            QMessageBox.warning(self, "错误", "没有找到数据")
            return
        
        result_text = f"多公司 {metric} 比较分析:\n\n"
        
        # 按公司和日期分组
        grouped = df.groupby('company_name')
        
        # 准备比较数据
        compare_data = []
        for company, data in grouped:
            latest_data = data.iloc[-1] if not data.empty else None
            if latest_data is not None and metric in latest_data:
                compare_data.append({
                    'company': company,
                    'value': latest_data[metric],
                    'period': latest_data['period']
                })
                result_text += f"{company}: {latest_data[metric]:,.2f}\n"
        
        # 绘制比较图表
        if compare_data:
            compare_df = pd.DataFrame(compare_data)
            self.compare_chart.plot_bar_chart(
                compare_df, 'company', 'value',
                f"多公司 {metric} 比较", "公司", metric,
                horizontal=True
            )
        
        self.compare_result.setText(result_text)


class ImportDialog(QDialog):
    """数据导入对话框"""
    
    def __init__(self, data_manager, file_path, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.file_path = file_path
        
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("导入数据")
        self.setGeometry(200, 200, 400, 200)
        
        layout = QVBoxLayout(self)
        
        # 文件路径显示
        layout.addWidget(QLabel(f"文件: {self.file_path}"))
        
        # 报表类型选择
        form_layout = QFormLayout()
        
        self.statement_type = QComboBox()
        self.statement_type.addItems(["income", "balance", "cash_flow"])
        form_layout.addRow("报表类型:", self.statement_type)
        
        layout.addLayout(form_layout)
        
        # 进度条
        self.progress = QProgressBar()
        layout.addWidget(self.progress)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.start_import)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def start_import(self):
        """开始导入数据"""
        # 禁用按钮防止重复点击
        for button in self.findChildren(QPushButton):
            button.setEnabled(False)
        
        # 创建导入线程
        self.import_thread = DataImportThread(
            self.data_manager, 
            self.file_path, 
            self.statement_type.currentText()
        )
        
        self.import_thread.progress.connect(self.progress.setValue)
        self.import_thread.finished.connect(self.import_finished)
        self.import_thread.start()
    
    def import_finished(self, success, message):
        """导入完成处理"""
        if success:
            QMessageBox.information(self, "成功", message)
            self.accept()
        else:
            QMessageBox.warning(self, "错误", message)
            # 重新启用按钮
            for button in self.findChildren(QPushButton):
                button.setEnabled(True)


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    dashboard = FinancialDashboard()
    dashboard.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()