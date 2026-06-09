import sys
import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from scipy import stats
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import sqlite3
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
                             QLabel, QLineEdit, QComboBox, QDateEdit, QTextEdit,
                             QTabWidget, QFileDialog, QMessageBox, QProgressBar,
                             QGroupBox, QSplitter, QHeaderView, QCheckBox,
                             QSpinBox, QDoubleSpinBox, QSlider)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QDate, QTimer
from PyQt5.QtGui import QFont, QPalette, QColor
import folium
from folium.plugins import HeatMap
import webbrowser
import tempfile


class PollutionDataManager:
    """污染数据管理器"""
    
    def __init__(self, db_path="pollution_data.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建监测点表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS monitoring_stations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                type TEXT NOT NULL,
                description TEXT
            )
        ''')
        
        # 创建污染数据表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pollution_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                station_id INTEGER,
                timestamp DATETIME NOT NULL,
                pm25 REAL,
                pm10 REAL,
                so2 REAL,
                no2 REAL,
                co REAL,
                o3 REAL,
                aqi INTEGER,
                temperature REAL,
                humidity REAL,
                wind_speed REAL,
                wind_direction REAL,
                FOREIGN KEY (station_id) REFERENCES monitoring_stations (id)
            )
        ''')
        
        # 创建评估结果表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS assessment_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                station_id INTEGER,
                assessment_date DATE NOT NULL,
                assessment_type TEXT NOT NULL,
                score REAL,
                grade TEXT,
                details TEXT,
                FOREIGN KEY (station_id) REFERENCES monitoring_stations (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_station(self, name, latitude, longitude, station_type, description=""):
        """添加监测点"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO monitoring_stations (name, latitude, longitude, type, description)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, latitude, longitude, station_type, description))
        conn.commit()
        station_id = cursor.lastrowid
        conn.close()
        return station_id
    
    def add_pollution_data(self, station_id, timestamp, pm25=None, pm10=None, 
                          so2=None, no2=None, co=None, o3=None, aqi=None,
                          temperature=None, humidity=None, wind_speed=None, wind_direction=None):
        """添加污染数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO pollution_data 
            (station_id, timestamp, pm25, pm10, so2, no2, co, o3, aqi, temperature, humidity, wind_speed, wind_direction)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (station_id, timestamp, pm25, pm10, so2, no2, co, o3, aqi, 
              temperature, humidity, wind_speed, wind_direction))
        conn.commit()
        conn.close()
    
    def get_station_data(self, station_id, start_date=None, end_date=None):
        """获取监测点数据"""
        conn = sqlite3.connect(self.db_path)
        
        query = '''
            SELECT timestamp, pm25, pm10, so2, no2, co, o3, aqi, temperature, humidity, wind_speed, wind_direction
            FROM pollution_data
            WHERE station_id = ?
        '''
        params = [station_id]
        
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)
        
        query += " ORDER BY timestamp"
        
        df = pd.read_sql_query(query, conn, params=params, parse_dates=['timestamp'])
        conn.close()
        return df
    
    def get_all_stations(self):
        """获取所有监测点"""
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query('SELECT * FROM monitoring_stations', conn)
        conn.close()
        return df


class PollutionAnalyzer:
    """污染数据分析器"""
    
    @staticmethod
    def calculate_aqi(pm25, pm10, so2, no2, co, o3):
        """计算空气质量指数(AQI)"""
        # 简化版AQI计算，实际应用需根据国家标准实现
        aqi_values = []
        
        if pm25 is not None:
            aqi_pm25 = PollutionAnalyzer._calculate_pollutant_aqi(pm25, 'pm25')
            aqi_values.append(aqi_pm25)
        
        if pm10 is not None:
            aqi_pm10 = PollutionAnalyzer._calculate_pollutant_aqi(pm10, 'pm10')
            aqi_values.append(aqi_pm10)
        
        if so2 is not None:
            aqi_so2 = PollutionAnalyzer._calculate_pollutant_aqi(so2, 'so2')
            aqi_values.append(aqi_so2)
        
        if no2 is not None:
            aqi_no2 = PollutionAnalyzer._calculate_pollutant_aqi(no2, 'no2')
            aqi_values.append(aqi_no2)
        
        if co is not None:
            aqi_co = PollutionAnalyzer._calculate_pollutant_aqi(co, 'co')
            aqi_values.append(aqi_co)
        
        if o3 is not None:
            aqi_o3 = PollutionAnalyzer._calculate_pollutant_aqi(o3, 'o3')
            aqi_values.append(aqi_o3)
        
        return max(aqi_values) if aqi_values else None
    
    @staticmethod
    def _calculate_pollutant_aqi(concentration, pollutant):
        """计算单个污染物的AQI"""
        # AQI分级限值 (根据中国标准简化)
        breakpoints = {
            'pm25': [(0, 35), (35, 75), (75, 115), (115, 150), (150, 250), (250, 350), (350, 500)],
            'pm10': [(0, 50), (50, 150), (150, 250), (250, 350), (350, 420), (420, 500), (500, 600)],
            'so2': [(0, 50), (50, 150), (150, 475), (475, 800), (800, 1600), (1600, 2100), (2100, 2620)],
            'no2': [(0, 40), (40, 80), (80, 180), (180, 280), (280, 565), (565, 750), (750, 940)],
            'co': [(0, 2), (2, 4), (4, 14), (14, 24), (24, 36), (36, 48), (48, 60)],
            'o3': [(0, 100), (100, 160), (160, 215), (215, 265), (265, 800), (800, 1000), (1000, 1200)]
        }
        
        aqi_ranges = [(0, 50), (51, 100), (101, 150), (151, 200), (201, 300), (301, 400), (401, 500)]
        
        if pollutant not in breakpoints or concentration < 0:
            return None
        
        # 找到浓度所在的区间
        for i, (low, high) in enumerate(breakpoints[pollutant]):
            if low <= concentration <= high:
                aqi_low, aqi_high = aqi_ranges[i]
                # 线性插值计算AQI
                aqi = ((aqi_high - aqi_low) / (high - low)) * (concentration - low) + aqi_low
                return round(aqi)
        
        # 如果浓度超过最高限值，返回500
        return 500
    
    @staticmethod
    def assess_pollution_level(aqi):
        """根据AQI评估污染等级"""
        if aqi <= 50:
            return "优", "green"
        elif aqi <= 100:
            return "良", "lightgreen"
        elif aqi <= 150:
            return "轻度污染", "yellow"
        elif aqi <= 200:
            return "中度污染", "orange"
        elif aqi <= 300:
            return "重度污染", "red"
        else:
            return "严重污染", "darkred"
    
    @staticmethod
    def trend_analysis(data, pollutant='pm25', window=7):
        """趋势分析"""
        if pollutant not in data.columns or data[pollutant].isna().all():
            return None, None, None
        
        # 移动平均平滑
        smoothed = data[pollutant].rolling(window=window, min_periods=1).mean()
        
        # 线性趋势
        x = np.arange(len(smoothed.dropna()))
        y = smoothed.dropna().values
        
        if len(y) < 2:
            return None, None, None
        
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        
        # 趋势判断
        if p_value < 0.05:
            if slope > 0:
                trend = "上升"
            else:
                trend = "下降"
        else:
            trend = "稳定"
        
        return trend, slope, r_value**2
    
    @staticmethod
    def correlation_analysis(data, pollutants):
        """相关性分析"""
        valid_pollutants = [p for p in pollutants if p in data.columns and data[p].notna().sum() > 10]
        
        if len(valid_pollutants) < 2:
            return None
        
        correlation_matrix = data[valid_pollutants].corr()
        return correlation_matrix
    
    @staticmethod
    def predict_pollution(data, pollutant='pm25', days=7):
        """污染预测（使用随机森林）"""
        if pollutant not in data.columns or data[pollutant].isna().all():
            return None
        
        # 准备特征数据
        df = data[['timestamp', pollutant]].copy()
        df = df.dropna()
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['day_of_year'] = df['timestamp'].dt.dayofyear
        df['month'] = df['timestamp'].dt.month
        df['year'] = df['timestamp'].dt.year
        
        # 创建滞后特征
        for i in range(1, 8):
            df[f'lag_{i}'] = df[pollutant].shift(i)
        
        df = df.dropna()
        
        if len(df) < 14:
            return None
        
        # 准备训练数据
        X = df.drop(['timestamp', pollutant], axis=1)
        y = df[pollutant]
        
        # 训练模型
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)
        
        # 评估模型
        y_pred = model.predict(X_test)
        mse = mean_squared_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        # 预测未来
        last_data = df.iloc[-1]
        future_predictions = []
        
        for i in range(days):
            # 创建未来时间点特征
            future_date = df['timestamp'].iloc[-1] + timedelta(days=i+1)
            features = {
                'day_of_week': future_date.dayofweek,
                'day_of_year': future_date.dayofyear,
                'month': future_date.month,
                'year': future_date.year
            }
            
            # 添加滞后特征
            for j in range(1, 8):
                if i + 1 - j < 0:
                    features[f'lag_{j}'] = df[pollutant].iloc[-j+i+1] if -j+i+1 >= 0 else df[pollutant].mean()
                else:
                    features[f'lag_{j}'] = future_predictions[i-j] if i-j >= 0 else df[pollutant].iloc[-1]
            
            # 转换为DataFrame
            features_df = pd.DataFrame([features])
            
            # 预测
            prediction = model.predict(features_df)[0]
            future_predictions.append(max(0, prediction))  # 确保预测值非负
        
        return {
            'predictions': future_predictions,
            'mse': mse,
            'r2': r2,
            'feature_importance': dict(zip(X.columns, model.feature_importances_))
        }


class PollutionVisualizer:
    """污染数据可视化"""
    
    def __init__(self):
        self.fig = Figure(figsize=(10, 8))
        self.canvas = FigureCanvas(self.fig)
    
    def clear_figure(self):
        """清除图形"""
        self.fig.clear()
    
    def plot_pollution_trend(self, data, pollutants, title="污染趋势图"):
        """绘制污染趋势图"""
        self.clear_figure()
        ax = self.fig.add_subplot(111)
        
        for pollutant in pollutants:
            if pollutant in data.columns and data[pollutant].notna().sum() > 0:
                ax.plot(data['timestamp'], data[pollutant], label=pollutant, marker='o', markersize=2)
        
        ax.set_title(title)
        ax.set_xlabel('时间')
        ax.set_ylabel('浓度 (μg/m³)')
        ax.legend()
        ax.grid(True, linestyle='--', alpha=0.7)
        
        # 格式化x轴日期显示
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.WeekdayLocator())
        self.fig.autofmt_xdate()
        
        self.canvas.draw()
    
    def plot_aqi_timeseries(self, data, title="AQI时间序列"):
        """绘制AQI时间序列图"""
        if 'aqi' not in data.columns or data['aqi'].isna().all():
            return
        
        self.clear_figure()
        ax = self.fig.add_subplot(111)
        
        # 根据AQI值设置颜色
        colors = []
        for aqi in data['aqi']:
            if aqi <= 50:
                colors.append('green')
            elif aqi <= 100:
                colors.append('lightgreen')
            elif aqi <= 150:
                colors.append('yellow')
            elif aqi <= 200:
                colors.append('orange')
            elif aqi <= 300:
                colors.append('red')
            else:
                colors.append('darkred')
        
        ax.scatter(data['timestamp'], data['aqi'], c=colors, alpha=0.7)
        ax.plot(data['timestamp'], data['aqi'], 'k-', alpha=0.3)
        
        ax.set_title(title)
        ax.set_xlabel('时间')
        ax.set_ylabel('AQI')
        ax.grid(True, linestyle='--', alpha=0.7)
        
        # 添加AQI等级参考线
        ax.axhline(y=50, color='green', linestyle='--', alpha=0.5, label='优')
        ax.axhline(y=100, color='lightgreen', linestyle='--', alpha=0.5, label='良')
        ax.axhline(y=150, color='yellow', linestyle='--', alpha=0.5, label='轻度污染')
        ax.axhline(y=200, color='orange', linestyle='--', alpha=0.5, label='中度污染')
        ax.axhline(y=300, color='red', linestyle='--', alpha=0.5, label='重度污染')
        
        ax.legend()
        
        # 格式化x轴日期显示
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.WeekdayLocator())
        self.fig.autofmt_xdate()
        
        self.canvas.draw()
    
    def plot_correlation_heatmap(self, correlation_matrix, title="污染物相关性热图"):
        """绘制相关性热图"""
        if correlation_matrix is None or correlation_matrix.empty:
            return
        
        self.clear_figure()
        ax = self.fig.add_subplot(111)
        
        im = ax.imshow(correlation_matrix.values, cmap='coolwarm', vmin=-1, vmax=1)
        
        # 设置刻度
        ax.set_xticks(np.arange(len(correlation_matrix.columns)))
        ax.set_yticks(np.arange(len(correlation_matrix.index)))
        ax.set_xticklabels(correlation_matrix.columns)
        ax.set_yticklabels(correlation_matrix.index)
        
        # 旋转x轴标签
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
        
        # 添加数值标注
        for i in range(len(correlation_matrix.index)):
            for j in range(len(correlation_matrix.columns)):
                text = ax.text(j, i, f'{correlation_matrix.iloc[i, j]:.2f}',
                              ha="center", va="center", color="black", fontsize=10)
        
        ax.set_title(title)
        self.fig.colorbar(im, ax=ax)
        self.canvas.draw()
    
    def plot_prediction(self, historical_data, predictions, days, title="污染预测"):
        """绘制预测结果"""
        if not historical_data or not predictions:
            return
        
        self.clear_figure()
        ax = self.fig.add_subplot(111)
        
        # 绘制历史数据
        ax.plot(historical_data['timestamp'], historical_data['pm25'], 
                'b-', label='历史数据', alpha=0.7)
        
        # 绘制预测数据
        last_date = historical_data['timestamp'].iloc[-1]
        future_dates = [last_date + timedelta(days=i+1) for i in range(days)]
        
        ax.plot(future_dates, predictions, 'r--', label='预测数据', marker='o')
        
        ax.set_title(title)
        ax.set_xlabel('时间')
        ax.set_ylabel('PM2.5浓度 (μg/m³)')
        ax.legend()
        ax.grid(True, linestyle='--', alpha=0.7)
        
        # 格式化x轴日期显示
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.WeekdayLocator())
        self.fig.autofmt_xdate()
        
        self.canvas.draw()


class MapVisualizer:
    """地图可视化"""
    
    @staticmethod
    def create_heatmap(stations_data, pollutant='pm25', output_file="pollution_heatmap.html"):
        """创建污染热力图"""
        # 创建地图
        m = folium.Map(location=[39.9042, 116.4074], zoom_start=10)  # 默认北京中心
        
        # 准备热力图数据
        heat_data = []
        for _, station in stations_data.iterrows():
            if pd.notna(station[pollutant]):
                heat_data.append([station['latitude'], station['longitude'], station[pollutant]])
        
        # 添加热力图
        if heat_data:
            HeatMap(heat_data, min_opacity=0.2, max_zoom=18, 
                   radius=15, blur=10, gradient={0.4: 'blue', 0.65: 'lime', 1: 'red'}).add_to(m)
        
        # 添加监测点标记
        for _, station in stations_data.iterrows():
            # 根据污染物浓度设置颜色
            concentration = station.get(pollutant, 0)
            if concentration <= 35:
                color = 'green'
            elif concentration <= 75:
                color = 'lightgreen'
            elif concentration <= 115:
                color = 'yellow'
            elif concentration <= 150:
                color = 'orange'
            elif concentration <= 250:
                color = 'red'
            else:
                color = 'darkred'
            
            folium.Marker(
                [station['latitude'], station['longitude']],
                popup=f"{station['name']}<br>{pollutant}: {concentration}",
                tooltip=station['name'],
                icon=folium.Icon(color=color, icon='info-sign')
            ).add_to(m)
        
        # 保存地图
        m.save(output_file)
        return output_file


class DataImportExport:
    """数据导入导出工具"""
    
    @staticmethod
    def import_from_csv(file_path, data_manager):
        """从CSV导入数据"""
        try:
            df = pd.read_csv(file_path)
            
            # 假设CSV包含以下列：station_name, latitude, longitude, timestamp, pm25, pm10, etc.
            for _, row in df.iterrows():
                # 检查监测点是否存在，不存在则创建
                stations = data_manager.get_all_stations()
                station_match = stations[stations['name'] == row['station_name']]
                
                if station_match.empty:
                    station_id = data_manager.add_station(
                        name=row['station_name'],
                        latitude=row['latitude'],
                        longitude=row['longitude'],
                        station_type="自动监测站"
                    )
                else:
                    station_id = station_match.iloc[0]['id']
                
                # 添加污染数据
                data_manager.add_pollution_data(
                    station_id=station_id,
                    timestamp=row['timestamp'],
                    pm25=row.get('pm25'),
                    pm10=row.get('pm10'),
                    so2=row.get('so2'),
                    no2=row.get('no2'),
                    co=row.get('co'),
                    o3=row.get('o3'),
                    temperature=row.get('temperature'),
                    humidity=row.get('humidity'),
                    wind_speed=row.get('wind_speed'),
                    wind_direction=row.get('wind_direction')
                )
            
            return True, f"成功导入 {len(df)} 条数据"
        except Exception as e:
            return False, f"导入失败: {str(e)}"
    
    @staticmethod
    def export_to_csv(data_manager, station_id, start_date, end_date, output_path):
        """导出数据到CSV"""
        try:
            data = data_manager.get_station_data(station_id, start_date, end_date)
            data.to_csv(output_path, index=False)
            return True, f"数据已导出到 {output_path}"
        except Exception as e:
            return False, f"导出失败: {str(e)}"
    
    @staticmethod
    def export_report(data_manager, station_id, start_date, end_date, output_path):
        """导出评估报告"""
        try:
            data = data_manager.get_station_data(station_id, start_date, end_date)
            
            # 生成报告内容
            report = {
                "station_id": station_id,
                "period": f"{start_date} 到 {end_date}",
                "data_points": len(data),
                "summary": {}
            }
            
            # 计算各污染物统计信息
            pollutants = ['pm25', 'pm10', 'so2', 'no2', 'co', 'o3', 'aqi']
            for pollutant in pollutants:
                if pollutant in data.columns and data[pollutant].notna().sum() > 0:
                    report["summary"][pollutant] = {
                        "mean": data[pollutant].mean(),
                        "max": data[pollutant].max(),
                        "min": data[pollutant].min(),
                        "std": data[pollutant].std()
                    }
            
            # 保存报告
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            return True, f"报告已导出到 {output_path}"
        except Exception as e:
            return False, f"报告导出失败: {str(e)}"


class AnalysisWorker(QThread):
    """分析工作线程"""
    progress_updated = pyqtSignal(int)
    analysis_completed = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, data, analysis_type, parameters):
        super().__init__()
        self.data = data
        self.analysis_type = analysis_type
        self.parameters = parameters
    
    def run(self):
        try:
            if self.analysis_type == "trend":
                self.progress_updated.emit(20)
                result = self.analyze_trend()
            elif self.analysis_type == "correlation":
                self.progress_updated.emit(20)
                result = self.analyze_correlation()
            elif self.analysis_type == "prediction":
                result = self.analyze_prediction()
            else:
                self.error_occurred.emit("未知的分析类型")
                return
            
            self.progress_updated.emit(100)
            self.analysis_completed.emit(result)
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def analyze_trend(self):
        """趋势分析"""
        pollutant = self.parameters.get('pollutant', 'pm25')
        window = self.parameters.get('window', 7)
        
        trend, slope, r_squared = PollutionAnalyzer.trend_analysis(
            self.data, pollutant, window)
        
        return {
            'type': 'trend',
            'pollutant': pollutant,
            'trend': trend,
            'slope': slope,
            'r_squared': r_squared
        }
    
    def analyze_correlation(self):
        """相关性分析"""
        pollutants = self.parameters.get('pollutants', ['pm25', 'pm10', 'so2', 'no2', 'co', 'o3'])
        
        correlation_matrix = PollutionAnalyzer.correlation_analysis(
            self.data, pollutants)
        
        return {
            'type': 'correlation',
            'matrix': correlation_matrix.to_dict() if correlation_matrix is not None else None
        }
    
    def analyze_prediction(self):
        """预测分析"""
        pollutant = self.parameters.get('pollutant', 'pm25')
        days = self.parameters.get('days', 7)
        
        prediction_result = PollutionAnalyzer.predict_pollution(
            self.data, pollutant, days)
        
        return {
            'type': 'prediction',
            'pollutant': pollutant,
            'predictions': prediction_result['predictions'] if prediction_result else None,
            'mse': prediction_result.get('mse') if prediction_result else None,
            'r2': prediction_result.get('r2') if prediction_result else None,
            'feature_importance': prediction_result.get('feature_importance') if prediction_result else None
        }


class PollutionAssessmentSystem(QMainWindow):
    """污染评估系统主界面"""
    
    def __init__(self):
        super().__init__()
        self.data_manager = PollutionDataManager()
        self.analyzer = PollutionAnalyzer()
        self.visualizer = PollutionVisualizer()
        self.current_station_id = None
        self.current_data = None
        
        self.init_ui()
        self.load_initial_data()
    
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("污染评估管理系统")
        self.setGeometry(100, 100, 1400, 900)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧面板
        left_panel = QWidget()
        left_panel.setMaximumWidth(300)
        left_layout = QVBoxLayout(left_panel)
        
        # 监测点选择
        station_group = QGroupBox("监测点管理")
        station_layout = QVBoxLayout(station_group)
        
        self.station_combo = QComboBox()
        self.station_combo.currentIndexChanged.connect(self.on_station_changed)
        station_layout.addWidget(QLabel("选择监测点:"))
        station_layout.addWidget(self.station_combo)
        
        self.add_station_btn = QPushButton("添加监测点")
        self.add_station_btn.clicked.connect(self.add_station)
        station_layout.addWidget(self.add_station_btn)
        
        left_layout.addWidget(station_group)
        
        # 日期选择
        date_group = QGroupBox("时间范围")
        date_layout = QVBoxLayout(date_group)
        
        date_layout.addWidget(QLabel("开始日期:"))
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setDate(QDate.currentDate().addDays(-30))
        self.start_date_edit.dateChanged.connect(self.load_data)
        date_layout.addWidget(self.start_date_edit)
        
        date_layout.addWidget(QLabel("结束日期:"))
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setDate(QDate.currentDate())
        self.end_date_edit.dateChanged.connect(self.load_data)
        date_layout.addWidget(self.end_date_edit)
        
        self.load_data_btn = QPushButton("加载数据")
        self.load_data_btn.clicked.connect(self.load_data)
        date_layout.addWidget(self.load_data_btn)
        
        left_layout.addWidget(date_group)
        
        # 分析工具
        analysis_group = QGroupBox("分析工具")
        analysis_layout = QVBoxLayout(analysis_group)
        
        self.trend_btn = QPushButton("趋势分析")
        self.trend_btn.clicked.connect(lambda: self.run_analysis("trend"))
        analysis_layout.addWidget(self.trend_btn)
        
        self.correlation_btn = QPushButton("相关性分析")
        self.correlation_btn.clicked.connect(lambda: self.run_analysis("correlation"))
        analysis_layout.addWidget(self.correlation_btn)
        
        self.prediction_btn = QPushButton("预测分析")
        self.prediction_btn.clicked.connect(lambda: self.run_analysis("prediction"))
        analysis_layout.addWidget(self.prediction_btn)
        
        # 预测天数设置
        prediction_layout = QHBoxLayout()
        prediction_layout.addWidget(QLabel("预测天数:"))
        self.prediction_days = QSpinBox()
        self.prediction_days.setRange(1, 30)
        self.prediction_days.setValue(7)
        prediction_layout.addWidget(self.prediction_days)
        analysis_layout.addLayout(prediction_layout)
        
        left_layout.addWidget(analysis_group)
        
        # 数据管理
        data_group = QGroupBox("数据管理")
        data_layout = QVBoxLayout(data_group)
        
        self.import_btn = QPushButton("导入数据")
        self.import_btn.clicked.connect(self.import_data)
        data_layout.addWidget(self.import_btn)
        
        self.export_btn = QPushButton("导出数据")
        self.export_btn.clicked.connect(self.export_data)
        data_layout.addWidget(self.export_btn)
        
        self.report_btn = QPushButton("生成报告")
        self.report_btn.clicked.connect(self.generate_report)
        data_layout.addWidget(self.report_btn)
        
        left_layout.addWidget(data_group)
        
        # 地图可视化
        map_group = QGroupBox("地图可视化")
        map_layout = QVBoxLayout(map_group)
        
        self.heatmap_btn = QPushButton("生成热力图")
        self.heatmap_btn.clicked.connect(self.generate_heatmap)
        map_layout.addWidget(self.heatmap_btn)
        
        left_layout.addWidget(map_group)
        
        left_layout.addStretch()
        
        # 右侧主区域
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # 选项卡
        self.tabs = QTabWidget()
        
        # 数据表选项卡
        self.data_tab = QWidget()
        data_tab_layout = QVBoxLayout(self.data_tab)
        self.data_table = QTableWidget()
        data_tab_layout.addWidget(self.data_table)
        self.tabs.addTab(self.data_tab, "数据表")
        
        # 图表选项卡
        self.chart_tab = QWidget()
        chart_tab_layout = QVBoxLayout(self.chart_tab)
        chart_tab_layout.addWidget(self.visualizer.canvas)
        self.tabs.addTab(self.chart_tab, "图表")
        
        # 分析结果选项卡
        self.analysis_tab = QWidget()
        analysis_tab_layout = QVBoxLayout(self.analysis_tab)
        self.analysis_text = QTextEdit()
        self.analysis_text.setReadOnly(True)
        analysis_tab_layout.addWidget(self.analysis_text)
        self.tabs.addTab(self.analysis_tab, "分析结果")
        
        right_layout.addWidget(self.tabs)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        right_layout.addWidget(self.progress_bar)
        
        # 状态标签
        self.status_label = QLabel("就绪")
        right_layout.addWidget(self.status_label)
        
        # 添加左右面板到主布局
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 1100])
        
        main_layout.addWidget(splitter)
    
    def load_initial_data(self):
        """加载初始数据"""
        # 加载监测点
        self.update_station_combo()
        
        # 加载默认数据
        if self.station_combo.count() > 0:
            self.current_station_id = self.station_combo.currentData()
            self.load_data()
    
    def update_station_combo(self):
        """更新监测点下拉框"""
        self.station_combo.clear()
        stations = self.data_manager.get_all_stations()
        
        for _, station in stations.iterrows():
            self.station_combo.addItem(station['name'], station['id'])
    
    def on_station_changed(self):
        """监测点变更事件"""
        if self.station_combo.currentIndex() >= 0:
            self.current_station_id = self.station_combo.currentData()
            self.load_data()
    
    def load_data(self):
        """加载数据"""
        if not self.current_station_id:
            return
        
        start_date = self.start_date_edit.date().toString("yyyy-MM-dd")
        end_date = self.end_date_edit.date().toString("yyyy-MM-dd")
        
        self.current_data = self.data_manager.get_station_data(
            self.current_station_id, start_date, end_date)
        
        self.display_data_table()
        
        # 自动计算AQI（如果不存在）
        if 'aqi' not in self.current_data.columns or self.current_data['aqi'].isna().all():
            self.calculate_aqi()
        
        # 显示基本图表
        self.visualizer.plot_pollution_trend(
            self.current_data, ['pm25', 'pm10'], "PM2.5和PM10趋势")
    
    def calculate_aqi(self):
        """计算AQI"""
        if self.current_data is None:
            return
        
        aqi_values = []
        for _, row in self.current_data.iterrows():
            aqi = self.analyzer.calculate_aqi(
                row.get('pm25'), row.get('pm10'), row.get('so2'),
                row.get('no2'), row.get('co'), row.get('o3')
            )
            aqi_values.append(aqi)
        
        self.current_data['aqi'] = aqi_values
        
        # 更新数据库中的AQI值
        conn = sqlite3.connect(self.data_manager.db_path)
        cursor = conn.cursor()
        
        for i, (_, row) in enumerate(self.current_data.iterrows()):
            cursor.execute('''
                UPDATE pollution_data SET aqi = ? 
                WHERE station_id = ? AND timestamp = ?
            ''', (aqi_values[i], self.current_station_id, row['timestamp']))
        
        conn.commit()
        conn.close()
    
    def display_data_table(self):
        """显示数据表格"""
        if self.current_data is None or self.current_data.empty:
            self.data_table.setRowCount(0)
            self.data_table.setColumnCount(0)
            return
        
        # 设置表格行列数
        self.data_table.setRowCount(len(self.current_data))
        self.data_table.setColumnCount(len(self.current_data.columns))
        
        # 设置表头
        self.data_table.setHorizontalHeaderLabels(self.current_data.columns)
        
        # 填充数据
        for i, row in self.current_data.iterrows():
            for j, col in enumerate(self.current_data.columns):
                value = row[col]
                if pd.isna(value):
                    display_value = ""
                elif isinstance(value, (float, np.float64)):
                    display_value = f"{value:.2f}"
                elif isinstance(value, datetime):
                    display_value = value.strftime("%Y-%m-%d %H:%M")
                else:
                    display_value = str(value)
                
                item = QTableWidgetItem(display_value)
                self.data_table.setItem(i, j, item)
        
        # 调整列宽
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
    
    def run_analysis(self, analysis_type):
        """运行分析"""
        if self.current_data is None or self.current_data.empty:
            QMessageBox.warning(self, "警告", "没有可分析的数据")
            return
        
        # 设置参数
        parameters = {}
        if analysis_type == "prediction":
            parameters['days'] = self.prediction_days.value()
        
        # 创建并启动工作线程
        self.analysis_worker = AnalysisWorker(
            self.current_data, analysis_type, parameters)
        self.analysis_worker.progress_updated.connect(self.update_progress)
        self.analysis_worker.analysis_completed.connect(self.on_analysis_completed)
        self.analysis_worker.error_occurred.connect(self.on_analysis_error)
        
        self.progress_bar.setVisible(True)
        self.analysis_worker.start()
    
    def update_progress(self, value):
        """更新进度条"""
        self.progress_bar.setValue(value)
    
    def on_analysis_completed(self, result):
        """分析完成"""
        self.progress_bar.setVisible(False)
        self.display_analysis_result(result)
    
    def on_analysis_error(self, error_msg):
        """分析错误"""
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "错误", f"分析过程中发生错误: {error_msg}")
    
    def display_analysis_result(self, result):
        """显示分析结果"""
        self.tabs.setCurrentIndex(2)  # 切换到分析结果选项卡
        
        if result['type'] == 'trend':
            output = f"""
            === 趋势分析结果 ===
            污染物: {result['pollutant']}
            趋势: {result['trend']}
            斜率: {result['slope']:.4f}
            R平方: {result['r_squared']:.4f}
            """
            
            # 更新图表
            self.visualizer.plot_pollution_trend(
                self.current_data, [result['pollutant']], 
                f"{result['pollutant']}趋势分析")
        
        elif result['type'] == 'correlation':
            if result['matrix'] is None:
                output = "无法进行相关性分析：数据不足"
            else:
                matrix = pd.DataFrame(result['matrix'])
                output = "=== 污染物相关性矩阵 ===\n"
                output += matrix.to_string()
                
                # 更新图表
                self.visualizer.plot_correlation_heatmap(matrix)
        
        elif result['type'] == 'prediction':
            if result['predictions'] is None:
                output = "无法进行预测：数据不足"
            else:
                output = f"""
                === 预测分析结果 ===
                污染物: {result['pollutant']}
                预测天数: {len(result['predictions'])}
                模型性能:
                  - 均方误差 (MSE): {result['mse']:.4f}
                  - R平方: {result['r2']:.4f}
                
                未来预测值:
                """
                
                for i, pred in enumerate(result['predictions']):
                    output += f"  第{i+1}天: {pred:.2f} μg/m³\n"
                
                # 更新图表
                self.visualizer.plot_prediction(
                    self.current_data, result['predictions'], 
                    len(result['predictions']), f"{result['pollutant']}浓度预测")
        
        self.analysis_text.setText(output)
    
    def add_station(self):
        """添加监测点"""
        # 这里应该打开一个对话框来输入监测点信息
        # 简化实现：添加一个示例监测点
        station_id = self.data_manager.add_station(
            name=f"监测点{self.station_combo.count()+1}",
            latitude=39.9 + np.random.uniform(-0.1, 0.1),
            longitude=116.4 + np.random.uniform(-0.1, 0.1),
            station_type="自动监测站",
            description="示例监测点"
        )
        
        self.update_station_combo()
        QMessageBox.information(self, "成功", f"已添加监测点，ID: {station_id}")
    
    def import_data(self):
        """导入数据"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择CSV文件", "", "CSV文件 (*.csv)")
        
        if file_path:
            success, message = DataImportExport.import_from_csv(
                file_path, self.data_manager)
            
            if success:
                QMessageBox.information(self, "成功", message)
                self.update_station_combo()
                self.load_data()
            else:
                QMessageBox.critical(self, "错误", message)
    
    def export_data(self):
        """导出数据"""
        if not self.current_station_id:
            QMessageBox.warning(self, "警告", "请先选择监测点")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存CSV文件", "", "CSV文件 (*.csv)")
        
        if file_path:
            start_date = self.start_date_edit.date().toString("yyyy-MM-dd")
            end_date = self.end_date_edit.date().toString("yyyy-MM-dd")
            
            success, message = DataImportExport.export_to_csv(
                self.data_manager, self.current_station_id, 
                start_date, end_date, file_path)
            
            if success:
                QMessageBox.information(self, "成功", message)
            else:
                QMessageBox.critical(self, "错误", message)
    
    def generate_report(self):
        """生成报告"""
        if not self.current_station_id:
            QMessageBox.warning(self, "警告", "请先选择监测点")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存报告", "", "JSON文件 (*.json)")
        
        if file_path:
            start_date = self.start_date_edit.date().toString("yyyy-MM-dd")
            end_date = self.end_date_edit.date().toString("yyyy-MM-dd")
            
            success, message = DataImportExport.export_report(
                self.data_manager, self.current_station_id, 
                start_date, end_date, file_path)
            
            if success:
                QMessageBox.information(self, "成功", message)
            else:
                QMessageBox.critical(self, "错误", message)
    
    def generate_heatmap(self):
        """生成热力图"""
        # 获取所有监测点的最新数据
        stations = self.data_manager.get_all_stations()
        if stations.empty:
            QMessageBox.warning(self, "警告", "没有监测点数据")
            return
        
        # 获取每个监测点的最新数据
        latest_data = []
        for _, station in stations.iterrows():
            data = self.data_manager.get_station_data(station['id'])
            if not data.empty:
                latest = data.iloc[-1].to_dict()
                latest['name'] = station['name']
                latest['latitude'] = station['latitude']
                latest['longitude'] = station['longitude']
                latest_data.append(latest)
        
        if not latest_data:
            QMessageBox.warning(self, "警告", "没有污染数据")
            return
        
        stations_df = pd.DataFrame(latest_data)
        
        # 创建热力图
        output_file = os.path.join(tempfile.gettempdir(), "pollution_heatmap.html")
        MapVisualizer.create_heatmap(stations_df, 'pm25', output_file)
        
        # 在浏览器中打开
        webbrowser.open('file://' + output_file)
        QMessageBox.information(self, "成功", f"热力图已生成并在浏览器中打开")


def main():
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = PollutionAssessmentSystem()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()