import sys
import numpy as np
import pandas as pd
import networkx as nx
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QSplitter, QToolBar, QAction, QStatusBar, QDockWidget, QTabWidget,
                             QLabel, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox, QSlider,
                             QDialog, QPushButton, QTextEdit, QFileDialog, QMessageBox,
                             QTableWidget, QTableWidgetItem, QGroupBox, QProgressBar)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QColor, QPainter, QPen, QFont, QPixmap
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.patches import Circle, Rectangle, Polygon
import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_squared_error
import pickle
import json
from datetime import datetime, timedelta
import time
import random
import folium
from folium import plugins
import branca.colormap as cm
from io import BytesIO
from PIL import Image
import requests
import os


class TrafficSimulationThread(QThread):
    """交通模拟线程"""
    update_signal = pyqtSignal(dict)
    finished_signal = pyqtSignal()
    
    def __init__(self, network, parameters):
        super().__init__()
        self.network = network
        self.parameters = parameters
        self.is_running = True
        self.is_paused = False
        self.current_time = datetime.now().replace(hour=7, minute=0, second=0, microsecond=0)
        
    def run(self):
        """运行模拟"""
        simulation_duration = self.parameters.get('duration', 24)  # 小时
        time_step = self.parameters.get('time_step', 5)  # 分钟
        
        end_time = self.current_time + timedelta(hours=simulation_duration)
        
        while self.current_time < end_time and self.is_running:
            if not self.is_paused:
                # 模拟交通流变化
                traffic_state = self.simulate_traffic_step()
                
                # 发送更新信号
                self.update_signal.emit({
                    'time': self.current_time,
                    'traffic_state': traffic_state
                })
                
                # 更新时间
                self.current_time += timedelta(minutes=time_step)
                
                # 控制模拟速度
                time.sleep(1.0 / self.parameters.get('speed', 1))
            
        self.finished_signal.emit()
    
    def simulate_traffic_step(self):
        """模拟单步交通状态"""
        traffic_state = {}
        
        # 获取当前小时的交通数据
        current_hour = self.current_time.replace(minute=0, second=0, microsecond=0)
        
        for road_id in range(len(self.network.roads)):
            # 获取基础交通数据
            road_data = self.network.traffic_data[
                (self.network.traffic_data.road_id == road_id) & 
                (self.network.traffic_data.timestamp == current_hour)
            ]
            
            if not road_data.empty:
                base_volume = road_data.volume.values[0]
                base_speed = road_data.speed.values[0]
                base_congestion = road_data.congestion.values[0]
            else:
                # 如果没有数据，使用道路容量估算
                road = self.network.roads.iloc[road_id]
                base_volume = road.lanes * 500
                base_speed = road.speed_limit
                base_congestion = 0.3
            
            # 添加随机波动和趋势
            hour = self.current_time.hour
            minute_fraction = self.current_time.minute / 60.0
            
            # 早晚高峰效应
            if 7 <= hour <= 9:  # 早高峰
                peak_factor = 1.5 + 0.5 * np.sin((hour - 7 + minute_fraction) * np.pi / 2)
            elif 16 <= hour <= 19:  # 晚高峰
                peak_factor = 1.3 + 0.4 * np.sin(((hour - 16) + minute_fraction) * np.pi / 3)
            else:  # 非高峰
                peak_factor = 0.7 + 0.3 * np.sin(hour * np.pi / 12)
            
            # 随机波动
            random_factor = 0.9 + 0.2 * random.random()
            
            # 计算当前交通状态
            volume = base_volume * peak_factor * random_factor
            capacity = self.network.roads.iloc[road_id].lanes * 1000  # 每小时每车道容量
            
            # 计算拥堵程度 (0-1)
            congestion = min(volume / capacity, 1.0)
            
            # 计算速度 (拥堵越严重，速度越慢)
            speed = base_speed * (1.0 - 0.7 * congestion)
            
            traffic_state[road_id] = {
                'volume': volume,
                'speed': speed,
                'congestion': congestion
            }
        
        return traffic_state
    
    def stop(self):
        """停止模拟"""
        self.is_running = False
        
    def pause(self):
        """暂停模拟"""
        self.is_paused = True
        
    def resume(self):
        """继续模拟"""
        self.is_paused = False


class MLTrafficPredictor:
    """机器学习交通预测器"""
    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.is_trained = False
        
    def prepare_features(self, network, include_weather=False):
        """准备特征数据"""
        features = []
        targets_volume = []
        targets_speed = []
        
        for _, traffic_point in network.traffic_data.iterrows():
            road_id = traffic_point.road_id
            road = network.roads.iloc[road_id]
            
            # 基本特征
            feature = [
                road_id,
                road.lanes,
                road.speed_limit,
                traffic_point.timestamp.hour,
                traffic_point.timestamp.weekday(),
                traffic_point.timestamp.month,
            ]
            
            # 添加天气数据（如果可用）
            if include_weather and hasattr(network, 'weather_data'):
                # 这里可以添加天气数据的处理
                pass
            
            features.append(feature)
            targets_volume.append(traffic_point.volume)
            targets_speed.append(traffic_point.speed)
        
        return np.array(features), np.array(targets_volume), np.array(targets_speed)
    
    def train(self, network):
        """训练模型"""
        X, y_volume, y_speed = self.prepare_features(network)
        
        # 分割数据集
        X_train, X_test, y_volume_train, y_volume_test = train_test_split(
            X, y_volume, test_size=0.2, random_state=42
        )
        
        # 训练流量预测模型
        self.model.fit(X_train, y_volume_train)
        
        # 评估模型
        y_pred = self.model.predict(X_test)
        r2 = r2_score(y_volume_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_volume_test, y_pred))
        
        self.is_trained = True
        
        return r2, rmse
    
    def predict(self, road_id, hour, weekday, month, lanes, speed_limit):
        """预测交通流量"""
        if not self.is_trained:
            raise ValueError("模型尚未训练")
            
        features = np.array([[road_id, lanes, speed_limit, hour, weekday, month]])
        return self.model.predict(features)[0]


class AdvancedTrafficNetwork:
    """高级交通网络数据模型"""
    def __init__(self):
        self.roads = gpd.GeoDataFrame(columns=[
            'id', 'name', 'type', 'lanes', 'speed_limit', 'capacity', 'geometry'
        ])
        self.intersections = gpd.GeoDataFrame(columns=[
            'id', 'name', 'type', 'signal_timing', 'geometry'
        ])
        self.zones = gpd.GeoDataFrame(columns=[
            'id', 'name', 'type', 'population', 'employment', 'geometry'
        ])
        self.public_transit = gpd.GeoDataFrame(columns=[
            'id', 'name', 'type', 'capacity', 'frequency', 'geometry'
        ])
        self.traffic_data = pd.DataFrame(columns=[
            'road_id', 'timestamp', 'volume', 'speed', 'congestion'
        ])
        self.od_matrix = pd.DataFrame()  # 起讫点矩阵
        self.weather_data = pd.DataFrame()
        self.graph = nx.MultiDiGraph()  # 有向多重图，支持多种交通模式
        self.ml_predictor = MLTrafficPredictor()
        
    def add_road(self, id, name, road_type, lanes, speed_limit, capacity, geometry):
        """添加道路"""
        new_road = gpd.GeoDataFrame([{
            'id': id,
            'name': name,
            'type': road_type,
            'lanes': lanes,
            'speed_limit': speed_limit,
            'capacity': capacity,
            'geometry': geometry
        }])
        self.roads = gpd.GeoDataFrame(pd.concat([self.roads, new_road], ignore_index=True))
        self._update_graph()
        
    def add_intersection(self, id, name, intersection_type, signal_timing, geometry):
        """添加交叉口"""
        new_intersection = gpd.GeoDataFrame([{
            'id': id,
            'name': name,
            'type': intersection_type,
            'signal_timing': signal_timing,
            'geometry': geometry
        }])
        self.intersections = gpd.GeoDataFrame(pd.concat([self.intersections, new_intersection], ignore_index=True))
        self._update_graph()
        
    def add_zone(self, id, name, zone_type, population, employment, geometry):
        """添加交通分区"""
        new_zone = gpd.GeoDataFrame([{
            'id': id,
            'name': name,
            'type': zone_type,
            'population': population,
            'employment': employment,
            'geometry': geometry
        }])
        self.zones = gpd.GeoDataFrame(pd.concat([self.zones, new_zone], ignore_index=True))
        
    def add_public_transit(self, id, name, transit_type, capacity, frequency, geometry):
        """添加公共交通线路"""
        new_transit = gpd.GeoDataFrame([{
            'id': id,
            'name': name,
            'type': transit_type,
            'capacity': capacity,
            'frequency': frequency,
            'geometry': geometry
        }])
        self.public_transit = gpd.GeoDataFrame(pd.concat([self.public_transit, new_transit], ignore_index=True))
        self._update_graph()
        
    def _update_graph(self):
        """更新网络图"""
        self.graph.clear()
        
        # 添加节点（交叉口和区域中心）
        for idx, intersection in self.intersections.iterrows():
            point = intersection.geometry
            self.graph.add_node(
                f"i_{idx}", 
                pos=(point.x, point.y), 
                type='intersection',
                signal_timing=intersection.signal_timing
            )
        
        for idx, zone in self.zones.iterrows():
            centroid = zone.geometry.centroid
            self.graph.add_node(
                f"z_{idx}", 
                pos=(centroid.x, centroid.y), 
                type='zone',
                population=zone.population,
                employment=zone.employment
            )
        
        # 添加边（道路和公共交通）
        for idx, road in self.roads.iterrows():
            line = road.geometry
            # 找到与道路起点和终点最近的节点
            start_point, end_point = line.boundary.geoms
            start_node = self._find_closest_node(start_point)
            end_node = self._find_closest_node(end_point)
            
            if start_node is not None and end_node is not None:
                # 计算时间权重 (秒)
                time_weight = line.length / (road.speed_limit * 0.2778)  # 转换为m/s
                
                # 添加双向道路（如果允许）
                self.graph.add_edge(
                    start_node, end_node, 
                    key='car',
                    weight=time_weight,
                    road_id=idx,
                    type='road',
                    lanes=road.lanes,
                    speed_limit=road.speed_limit,
                    capacity=road.capacity,
                    length=line.length
                )
                
                # 反向道路
                self.graph.add_edge(
                    end_node, start_node, 
                    key='car',
                    weight=time_weight,
                    road_id=idx,
                    type='road',
                    lanes=road.lanes,
                    speed_limit=road.speed_limit,
                    capacity=road.capacity,
                    length=line.length
                )
        
        # 添加公共交通边
        for idx, transit in self.public_transit.iterrows():
            line = transit.geometry
            start_point, end_point = line.boundary.geoms
            start_node = self._find_closest_node(start_point)
            end_node = self._find_closest_node(end_point)
            
            if start_node is not None and end_node is not None:
                # 公共交通时间权重（考虑等待时间）
                wait_time = 60 / transit.frequency / 2  # 平均等待时间（秒）
                travel_time = line.length / (transit.speed if hasattr(transit, 'speed') else 50 * 0.2778)
                time_weight = travel_time + wait_time
                
                self.graph.add_edge(
                    start_node, end_node,
                    key='transit',
                    weight=time_weight,
                    transit_id=idx,
                    type='transit',
                    capacity=transit.capacity,
                    frequency=transit.frequency,
                    length=line.length
                )
    
    def _find_closest_node(self, point, max_distance=100):
        """找到最近的节点"""
        min_dist = float('inf')
        closest_node = None
        
        for node in self.graph.nodes(data=True):
            node_pos = node[1]['pos']
            dist = point.distance(Point(node_pos))
            if dist < min_dist and dist < max_distance:
                min_dist = dist
                closest_node = node[0]
                
        return closest_node
    
    def generate_od_matrix(self):
        """生成起讫点矩阵"""
        num_zones = len(self.zones)
        self.od_matrix = pd.DataFrame(np.zeros((num_zones, num_zones)), 
                                     index=[f"z_{i}" for i in range(num_zones)],
                                     columns=[f"z_{i}" for i in range(num_zones)])
        
        # 基于人口和就业生成出行需求
        for i in range(num_zones):
            for j in range(num_zones):
                if i != j:
                    # 重力模型：出行量与人口和就业成正比，与距离成反比
                    pop_i = self.zones.iloc[i].population
                    emp_j = self.zones.iloc[j].employment
                    
                    # 计算区域中心之间的距离
                    centroid_i = self.zones.iloc[i].geometry.centroid
                    centroid_j = self.zones.iloc[j].geometry.centroid
                    distance = centroid_i.distance(centroid_j)
                    
                    # 重力模型公式
                    self.od_matrix.iloc[i, j] = (pop_i * emp_j) / (distance + 1)
        
        # 标准化
        total_trips = self.od_matrix.values.sum()
        if total_trips > 0:
            self.od_matrix = self.od_matrix / total_trips * 10000  # 假设总出行量为10000
    
    def generate_traffic_data(self, time_range=24):
        """生成模拟交通数据"""
        timestamps = pd.date_range(start='2023-01-01', periods=time_range, freq='H')
        data = []
        
        for road_id in range(len(self.roads)):
            road = self.roads.iloc[road_id]
            base_volume = road.capacity * 0.5  # 初始流量为容量的一半
            
            for i, ts in enumerate(timestamps):
                # 早晚高峰模式
                hour = ts.hour
                if 7 <= hour <= 9:  # 早高峰
                    volume = base_volume * (1.5 + 0.5 * np.sin((hour - 7) * np.pi / 2))
                elif 16 <= hour <= 19:  # 晚高峰
                    volume = base_volume * (1.3 + 0.4 * np.sin((hour - 16) * np.pi / 3))
                else:  # 非高峰
                    volume = base_volume * (0.7 + 0.3 * np.sin(hour * np.pi / 12))
                
                # 添加随机变化
                volume *= (0.9 + 0.2 * np.random.random())
                volume = min(volume, road.capacity * 1.2)  # 不能超过容量的120%
                
                # 计算速度和拥堵程度
                speed = road.speed_limit * (0.7 + 0.3 * (1 - min(volume / road.capacity, 1)))
                congestion = min(volume / road.capacity, 1)
                
                data.append({
                    'road_id': road_id,
                    'timestamp': ts,
                    'volume': volume,
                    'speed': speed,
                    'congestion': congestion
                })
        
        self.traffic_data = pd.DataFrame(data)
    
    def find_optimal_path(self, start_point, end_point, mode='car', criteria='time'):
        """查找最优路径"""
        start_node = self._find_closest_node(Point(start_point))
        end_node = self._find_closest_node(Point(end_point))
        
        if start_node is None or end_node is None:
            return None, None
        
        if criteria == 'time':
            weight = 'weight'
        elif criteria == 'distance':
            weight = 'length'
        elif criteria == 'congestion':
            # 使用当前拥堵情况作为权重
            # 这里需要实时交通数据
            weight = 'congestion_weight'
        else:
            weight = 'weight'
        
        try:
            # 修改前：使用 key 参数
            # path = nx.shortest_path(self.graph, start_node, end_node, weight=weight, key=mode)
            
            # 修改后：创建一个只包含特定模式的子图
            edges_to_include = []
            for u, v, k, data in self.graph.edges(keys=True, data=True):
                if k == mode:  # 只包含指定模式的边
                    edges_to_include.append((u, v, k))
            
            # 创建子图
            subgraph = self.graph.edge_subgraph(edges_to_include)
            
            # 在子图中查找最短路径
            path = nx.shortest_path(subgraph, start_node, end_node, weight=weight)
            
            path_details = []
            
            for i in range(len(path)-1):
                # 获取边数据
                edge_data = subgraph[path[i]][path[i+1]][mode]
                
                if edge_data['type'] == 'road':
                    road_id = edge_data['road_id']
                    road = self.roads.iloc[road_id]
                    path_details.append({
                        'type': 'road',
                        'id': road_id,
                        'name': road.name,
                        'length': edge_data['length'],
                        'time': edge_data['weight']
                    })
                else:  # transit
                    transit_id = edge_data['transit_id']
                    transit = self.public_transit.iloc[transit_id]
                    path_details.append({
                        'type': 'transit',
                        'id': transit_id,
                        'name': transit.name,
                        'length': edge_data['length'],
                        'time': edge_data['weight']
                    })
            
            return path, path_details
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None, None
    
    def estimate_emissions(self, traffic_state):
        """估计交通排放"""
        total_co2 = 0
        total_nox = 0
        total_pm = 0
        
        for road_id, data in traffic_state.items():
            road = self.roads.iloc[road_id]
            volume = data['volume']
            speed = data['speed']
            
            # 基于速度和流量的排放因子（g/veh-kg）
            # 这些是简化值，实际应用中应使用更复杂的模型
            if speed > 80:
                co2_factor = 180  # 高速行驶
                nox_factor = 0.4
                pm_factor = 0.02
            elif speed > 50:
                co2_factor = 160  # 中速行驶
                nox_factor = 0.5
                pm_factor = 0.03
            elif speed > 20:
                co2_factor = 200  # 低速行驶
                nox_factor = 0.7
                pm_factor = 0.05
            else:
                co2_factor = 250  # 拥堵
                nox_factor = 1.0
                pm_factor = 0.08
            
            # 计算排放量
            distance = road.geometry.length / 1000  # 转换为公里
            total_co2 += volume * distance * co2_factor / 1000  # 转换为kg
            total_nox += volume * distance * nox_factor / 1000
            total_pm += volume * distance * pm_factor / 1000
        
        return {
            'co2_kg': total_co2,
            'nox_kg': total_nox,
            'pm_kg': total_pm
        }
    
    def train_ml_predictor(self):
        """训练机器学习预测器"""
        return self.ml_predictor.train(self)
    
    def predict_traffic(self, road_id, hour, weekday, month):
        """预测交通流量"""
        road = self.roads.iloc[road_id]
        return self.ml_predictor.predict(road_id, hour, weekday, month, road.lanes, road.speed_limit)


class AdvancedTrafficMapCanvas(FigureCanvas):
    """高级交通地图画布"""
    def __init__(self, parent=None, width=10, height=8, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlabel('经度')
        self.ax.set_ylabel('纬度')
        self.ax.set_title('城市交通网络')
        
        self.network = None
        self.current_path = None
        self.current_path_details = None
        self.traffic_flow = False
        self.show_public_transit = False
        self.show_zones = False
        self.traffic_state = {}
        
    def set_network(self, network):
        """设置交通网络"""
        self.network = network
        self.draw_network()
        
    def draw_network(self):
        """绘制交通网络"""
        self.ax.clear()
        
        if self.network is None:
            self.draw()
            return
            
        # 绘制交通分区
        if self.show_zones:
            for idx, zone in self.network.zones.iterrows():
                if zone.geometry.geom_type == 'Polygon':
                    x, y = zone.geometry.exterior.xy
                    self.ax.fill(x, y, alpha=0.2, color='lightblue')
                    centroid = zone.geometry.centroid
                    self.ax.text(centroid.x, centroid.y, zone.name, fontsize=8, 
                                ha='center', va='center', alpha=0.7)
        
        # 绘制公共交通
        if self.show_public_transit:
            for idx, transit in self.network.public_transit.iterrows():
                line = transit.geometry
                x, y = line.xy
                self.ax.plot(x, y, 'r-', linewidth=2, alpha=0.7)
                
                # 添加公共交通标签
                mid_point = line.interpolate(0.5, normalized=True)
                self.ax.text(mid_point.x, mid_point.y, transit.name, fontsize=8, 
                            ha='center', va='center', color='red', alpha=0.7)
        
        # 绘制道路
        for idx, road in self.network.roads.iterrows():
            line = road.geometry
            x, y = line.xy
            
            # 根据拥堵程度选择颜色
            if self.traffic_flow and idx in self.traffic_state:
                congestion = self.traffic_state[idx]['congestion']
                if congestion < 0.3:
                    color = 'green'
                elif congestion < 0.7:
                    color = 'orange'
                else:
                    color = 'red'
                    
                # 线宽基于车道数
                linewidth = road.lanes * 0.5 + congestion * 2
            else:
                color = 'gray'
                linewidth = road.lanes * 0.5
                
            self.ax.plot(x, y, color=color, linewidth=linewidth, alpha=0.7)
            
            # 添加道路标签
            mid_point = line.interpolate(0.5, normalized=True)
            self.ax.text(mid_point.x, mid_point.y, road.name, fontsize=8, 
                        ha='center', va='center', alpha=0.7)
        
        # 绘制交叉口
        for idx, intersection in self.network.intersections.iterrows():
            point = intersection.geometry
            self.ax.plot(point.x, point.y, 'ko', markersize=5)
            self.ax.text(point.x, point.y, intersection.name, fontsize=8,
                        ha='right', va='bottom')
        
        # 绘制路径（如果有）
        if self.current_path is not None and self.current_path_details is not None:
            for segment in self.current_path_details:
                if segment['type'] == 'road':
                    road = self.network.roads.iloc[segment['id']]
                    line = road.geometry
                    x, y = line.xy
                    self.ax.plot(x, y, 'b-', linewidth=road.lanes*0.8, alpha=0.9)
                else:  # transit
                    transit = self.network.public_transit.iloc[segment['id']]
                    line = transit.geometry
                    x, y = line.xy
                    self.ax.plot(x, y, 'r-', linewidth=3, alpha=0.9)
        
        self.ax.set_xlabel('经度')
        self.ax.set_ylabel('纬度')
        self.ax.set_title('城市交通网络')
        self.ax.grid(True, alpha=0.3)
        self.draw()
        
    def show_traffic_flow(self, show):
        """显示/隐藏交通流量"""
        self.traffic_flow = show
        if self.network is not None:
            self.draw_network()
            
    def show_public_transit_lines(self, show):
        """显示/隐藏公共交通线路"""
        self.show_public_transit = show
        if self.network is not None:
            self.draw_network()
            
    def show_zones(self, show):
        """显示/隐藏交通分区"""
        self.show_zones = show
        if self.network is not None:
            self.draw_network()
            
    def update_traffic_state(self, traffic_state):
        """更新交通状态"""
        self.traffic_state = traffic_state
        if self.traffic_flow and self.network is not None:
            self.draw_network()
            
    def highlight_path(self, path, path_details):
        """高亮显示路径"""
        self.current_path = path
        self.current_path_details = path_details
        if self.network is not None:
            self.draw_network()

    def set_show_traffic_flow(self, show):
        """设置是否显示交通流量"""
        self.traffic_flow = show
        if self.network is not None:
            self.draw_network()

    def set_show_public_transit(self, show):
        """设置是否显示公共交通线路"""
        self.show_public_transit = show
        if self.network is not None:
            self.draw_network()

    def set_show_zones(self, show):
        """设置是否显示交通分区"""
        self.show_zones = show
        if self.network is not None:
            self.draw_network()

class AdvancedTrafficAnalysisWidget(QWidget):
    """高级交通分析面板"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.network = None
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 分析类型选择
        analysis_type_layout = QHBoxLayout()
        analysis_type_layout.addWidget(QLabel("分析类型:"))
        self.analysis_combo = QComboBox()
        self.analysis_combo.addItems([
            "交通流量", "拥堵指数", "速度分布", "路径分析", 
            "排放分析", "OD矩阵", "预测分析"
        ])
        analysis_type_layout.addWidget(self.analysis_combo)
        layout.addLayout(analysis_type_layout)
        
        # 时间选择
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("时间:"))
        self.time_slider = QSlider(Qt.Horizontal)
        self.time_slider.setMinimum(0)
        self.time_slider.setMaximum(23)
        self.time_slider.setValue(8)
        time_layout.addWidget(self.time_slider)
        self.time_label = QLabel("08:00")
        time_layout.addWidget(self.time_label)
        
        # 日期选择
        time_layout.addWidget(QLabel("日期:"))
        self.date_combo = QComboBox()
        self.date_combo.addItems(["工作日", "周末", "节假日"])
        time_layout.addWidget(self.date_combo)
        layout.addLayout(time_layout)
        
        # 图表区域
        self.figure = Figure(figsize=(8, 6))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        
        # 分析结果摘要
        self.summary_text = QTextEdit()
        self.summary_text.setMaximumHeight(100)
        layout.addWidget(self.summary_text)
        
        self.setLayout(layout)
        
        # 连接信号
        self.analysis_combo.currentTextChanged.connect(self.update_analysis)
        self.time_slider.valueChanged.connect(self.update_time)
        self.date_combo.currentTextChanged.connect(self.update_analysis)
        
    def set_network(self, network):
        """设置交通网络"""
        self.network = network
        self.update_analysis()
        
    def update_time(self, value):
        """更新时间显示"""
        self.time_label.setText(f"{value:02d}:00")
        self.update_analysis()
        
    def update_analysis(self):
        """更新分析图表"""
        if self.network is None or self.network.traffic_data.empty:
            return
            
        self.figure.clear()
        analysis_type = self.analysis_combo.currentText()
        hour = self.time_slider.value()
        day_type = self.date_combo.currentText()
        
        # 获取当前小时的交通数据
        current_time = pd.Timestamp.now().replace(hour=hour, minute=0, second=0, microsecond=0)
        current_data = self.network.traffic_data[self.network.traffic_data.timestamp == current_time]
        
        # 在 update_analysis 方法中，找到交通流量的分析部分（大约第822行）
        if analysis_type == "交通流量":
            ax = self.figure.add_subplot(111)
            volumes = [d.volume for _, d in current_data.iterrows()]
            
            # 添加检查，确保 volumes 不为空
            if not volumes:  # 检查是否为空
                ax.text(0.5, 0.5, '当前时间无交通数据', ha='center', va='center', transform=ax.transAxes)
                self.summary_text.setText("当前时间无交通数据")
                self.canvas.draw()
                return
            
            road_names = [self.network.roads.iloc[d.road_id].name for _, d in current_data.iterrows()]
            
            ax.bar(road_names, volumes, alpha=0.7)
            ax.set_title(f'交通流量 - {hour:02d}:00 ({day_type})')
            ax.set_ylabel('车辆数/小时')
            ax.tick_params(axis='x', rotation=45)
            
            # 更新摘要
            total_volume = sum(volumes)
            avg_volume = total_volume / len(volumes)  # 这里不会再除以零了
            max_volume = max(volumes)
            max_road = road_names[volumes.index(max_volume)]
            
            self.summary_text.setText(
                f"总流量: {total_volume:.0f} 车辆/小时\n"
                f"平均流量: {avg_volume:.0f} 车辆/小时\n"
                f"最高流量: {max_volume:.0f} 车辆/小时 ({max_road})"
            )
            
        elif analysis_type == "拥堵指数":
            ax = self.figure.add_subplot(111)
            congestions = [d.congestion for _, d in current_data.iterrows()]
            
            # 添加检查
            if not congestions:
                ax.text(0.5, 0.5, '当前时间无交通数据', ha='center', va='center', transform=ax.transAxes)
                self.summary_text.setText("当前时间无交通数据")
                self.canvas.draw()
                return
            road_names = [self.network.roads.iloc[d.road_id].name for _, d in current_data.iterrows()]
            
            ax.bar(road_names, congestions, alpha=0.7, color='red')
            ax.set_title(f'拥堵指数 - {hour:02d}:00 ({day_type})')
            ax.set_ylabel('拥堵指数 (0-1)')
            ax.set_ylim(0, 1)
            ax.tick_params(axis='x', rotation=45)
            
            # 更新摘要
            avg_congestion = sum(congestions) / len(congestions)
            max_congestion = max(congestions)
            max_road = road_names[congestions.index(max_congestion)]
            congested_roads = sum(1 for c in congestions if c > 0.7)
            
            self.summary_text.setText(
                f"平均拥堵指数: {avg_congestion:.2f}\n"
                f"最高拥堵指数: {max_congestion:.2f} ({max_road})\n"
                f"严重拥堵道路: {congested_roads} 条"
            )
            
        elif analysis_type == "速度分布":
            ax = self.figure.add_subplot(111)
            speeds = [d.speed for _, d in current_data.iterrows()]
            if not speeds:
                ax.text(0.5, 0.5, '当前时间无交通数据', ha='center', va='center', transform=ax.transAxes)
                self.summary_text.setText("当前时间无交通数据")
                self.canvas.draw()
                return
            road_names = [self.network.roads.iloc[d.road_id].name for _, d in current_data.iterrows()]
            
            ax.bar(road_names, speeds, alpha=0.7, color='green')
            ax.set_title(f'平均速度 - {hour:02d}:00 ({day_type})')
            ax.set_ylabel('速度 (km/h)')
            ax.tick_params(axis='x', rotation=45)
            
            # 更新摘要
            avg_speed = sum(speeds) / len(speeds)
            min_speed = min(speeds)
            min_road = road_names[speeds.index(min_speed)]
            
            self.summary_text.setText(
                f"平均速度: {avg_speed:.1f} km/h\n"
                f"最低速度: {min_speed:.1f} km/h ({min_road})\n"
                f"速度差异: {max(speeds)-min(speeds):.1f} km/h"
            )
            
        elif analysis_type == "排放分析":
            ax = self.figure.add_subplot(111)
            
            # 计算排放量
            traffic_state = {}
            for _, d in current_data.iterrows():
                traffic_state[d.road_id] = {
                    'volume': d.volume,
                    'speed': d.speed,
                    'congestion': d.congestion
                }
            
            emissions = self.network.estimate_emissions(traffic_state)
            
            # 绘制排放图表
            pollutants = ['CO₂', 'NOx', 'PM']
            values = [emissions['co2_kg'], emissions['nox_kg'], emissions['pm_kg']]
            colors = ['gray', 'orange', 'black']
            
            bars = ax.bar(pollutants, values, alpha=0.7, color=colors)
            ax.set_title(f'交通排放 - {hour:02d}:00 ({day_type})')
            ax.set_ylabel('排放量 (kg/小时)')
            
            # 在柱子上添加数值标签
            for bar, value in zip(bars, values):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                        f'{value:.1f}', ha='center', va='bottom')
            
            # 更新摘要
            self.summary_text.setText(
                f"总CO₂排放: {emissions['co2_kg']:.1f} kg/小时\n"
                f"总NOx排放: {emissions['nox_kg']:.1f} kg/小时\n"
                f"总PM排放: {emissions['pm_kg']:.1f} kg/小时"
            )
            
        elif analysis_type == "OD矩阵":
            ax = self.figure.add_subplot(111)
            
            if self.network.od_matrix.empty:
                self.network.generate_od_matrix()
            
            # 绘制OD矩阵热力图
            im = ax.imshow(self.network.od_matrix.values, cmap='hot', interpolation='nearest')
            ax.set_title('起讫点矩阵')
            ax.set_xlabel('目的地区域')
            ax.set_ylabel('出发地区域')
            
            # 添加颜色条
            plt.colorbar(im, ax=ax, label='出行量')
            
            # 更新摘要
            total_trips = self.network.od_matrix.values.sum()
            max_trips = self.network.od_matrix.values.max()
            avg_trips = total_trips / (len(self.network.zones) ** 2)
            
            self.summary_text.setText(
                f"总出行量: {total_trips:.0f}\n"
                f"最大OD对出行量: {max_trips:.0f}\n"
                f"平均OD对出行量: {avg_trips:.1f}"
            )
            
        elif analysis_type == "预测分析":
            ax = self.figure.add_subplot(111)
            
            # 检查模型是否已训练
            if not hasattr(self.network.ml_predictor, 'is_trained') or not self.network.ml_predictor.is_trained:
                ax.text(0.5, 0.5, '请先训练预测模型', ha='center', va='center', transform=ax.transAxes)
                self.summary_text.setText("预测模型未训练。请使用机器学习功能训练模型。")
                self.canvas.draw()
                return
            
            # 预测未来交通流量
            future_hours = list(range(24))
            predicted_volumes = []
            
            for h in future_hours:
                # 简化：只预测第一条道路
                road_id = 0
                predicted_volume = self.network.predict_traffic(road_id, h, 0, 1)  # 假设工作日，一月
                predicted_volumes.append(predicted_volume)
            
            ax.plot(future_hours, predicted_volumes, 'b-', label='预测流量')
            ax.set_xlabel('小时')
            ax.set_ylabel('预测流量 (车辆/小时)')
            ax.set_title('交通流量预测 (道路: {})'.format(self.network.roads.iloc[0].name))
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            # 更新摘要
            max_volume = max(predicted_volumes)
            min_volume = min(predicted_volumes)
            peak_hour = predicted_volumes.index(max_volume)
            
            self.summary_text.setText(
                f"预测最高流量: {max_volume:.0f} 车辆/小时 (在 {peak_hour:02d}:00)\n"
                f"预测最低流量: {min_volume:.0f} 车辆/小时\n"
                f"预测平均流量: {sum(predicted_volumes)/len(predicted_volumes):.0f} 车辆/小时"
            )
        
        self.figure.tight_layout()
        self.canvas.draw()

class SimulationControlWidget(QWidget):
    """模拟控制面板"""
    traffic_state_updated = pyqtSignal(dict)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.simulation_thread = None
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 模拟控制按钮
        control_layout = QHBoxLayout()
        
        self.start_button = QPushButton("开始模拟")
        self.pause_button = QPushButton("暂停")
        self.stop_button = QPushButton("停止")
        
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.pause_button)
        control_layout.addWidget(self.stop_button)
        layout.addLayout(control_layout)
        
        # 模拟参数
        params_group = QGroupBox("模拟参数")
        params_layout = QVBoxLayout()
        
        # 模拟持续时间
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("持续时间 (小时):"))
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 72)
        self.duration_spin.setValue(24)
        duration_layout.addWidget(self.duration_spin)
        params_layout.addLayout(duration_layout)
        
        # 时间步长
        timestep_layout = QHBoxLayout()
        timestep_layout.addWidget(QLabel("时间步长 (分钟):"))
        self.timestep_spin = QSpinBox()
        self.timestep_spin.setRange(1, 60)
        self.timestep_spin.setValue(5)
        timestep_layout.addWidget(self.timestep_spin)
        params_layout.addLayout(timestep_layout)
        
        # 模拟速度
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("模拟速度:"))
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(1, 10)
        self.speed_slider.setValue(5)
        speed_layout.addWidget(self.speed_slider)
        params_layout.addLayout(speed_layout)
        
        # 车辆数量
        vehicle_layout = QHBoxLayout()
        vehicle_layout.addWidget(QLabel("车辆数量:"))
        self.vehicle_spin = QSpinBox()
        self.vehicle_spin.setRange(10, 10000)
        self.vehicle_spin.setValue(1000)
        vehicle_layout.addWidget(self.vehicle_spin)
        params_layout.addLayout(vehicle_layout)
        
        params_group.setLayout(params_layout)
        layout.addWidget(params_group)
        
        # 模拟状态
        status_group = QGroupBox("模拟状态")
        status_layout = QVBoxLayout()
        
        self.time_label = QLabel("当前时间: 未开始")
        status_layout.addWidget(self.time_label)
        
        self.progress_bar = QProgressBar()
        status_layout.addWidget(self.progress_bar)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        self.setLayout(layout)
        
        # 连接信号
        self.start_button.clicked.connect(self.start_simulation)
        self.pause_button.clicked.connect(self.pause_simulation)
        self.stop_button.clicked.connect(self.stop_simulation)
        
    def set_network(self, network):
        """设置交通网络"""
        self.network = network
        
    def start_simulation(self):
        """开始模拟"""
        if self.network is None:
            QMessageBox.warning(self, "警告", "请先加载交通网络")
            return
            
        parameters = {
            'duration': self.duration_spin.value(),
            'time_step': self.timestep_spin.value(),
            'speed': self.speed_slider.value(),
            'vehicles': self.vehicle_spin.value()
        }
        
        self.simulation_thread = TrafficSimulationThread(self.network, parameters)
        self.simulation_thread.update_signal.connect(self.update_simulation_status)
        self.simulation_thread.finished_signal.connect(self.simulation_finished)
        
        self.start_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        
        self.simulation_thread.start()
        
    def pause_simulation(self):
        """暂停模拟"""
        if self.simulation_thread and self.simulation_thread.isRunning():
            if self.simulation_thread.is_paused:
                self.simulation_thread.resume()
                self.pause_button.setText("暂停")
            else:
                self.simulation_thread.pause()
                self.pause_button.setText("继续")
                
    def stop_simulation(self):
        """停止模拟"""
        if self.simulation_thread and self.simulation_thread.isRunning():
            self.simulation_thread.stop()
            self.simulation_thread.wait()
            self.simulation_finished()
            
    def update_simulation_status(self, data):
        """更新模拟状态"""
        current_time = data['time']
        self.time_label.setText(f"当前时间: {current_time.strftime('%Y-%m-%d %H:%M')}")
        
        # 更新进度条
        total_minutes = self.duration_spin.value() * 60
        elapsed_minutes = (current_time.hour - 7) * 60 + current_time.minute
        progress = int((elapsed_minutes / total_minutes) * 100)
        self.progress_bar.setValue(progress)
        
        # 发送交通状态更新信号
        self.traffic_state_updated.emit(data['traffic_state'])
        
    def simulation_finished(self):
        """模拟完成"""
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.pause_button.setText("暂停")
        
        self.time_label.setText("当前时间: 模拟完成")
        self.progress_bar.setValue(100)


class AdvancedMainWindow(QMainWindow):
    """高级主窗口"""
    def __init__(self):
        super().__init__()
        self.network = AdvancedTrafficNetwork()
        self.init_ui()
        self.create_sample_network()
        
    def init_ui(self):
        self.setWindowTitle("前沿城市交通规划高级工具")
        self.setGeometry(100, 100, 1600, 900)
        
        # 创建中心部件和分割器
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：地图视图
        self.map_canvas = AdvancedTrafficMapCanvas(self)
        splitter.addWidget(self.map_canvas)
        
        # 右侧：选项卡部件（分析、控制、ML等）
        right_tab = QTabWidget()
        
        # 分析选项卡
        self.analysis_widget = AdvancedTrafficAnalysisWidget()
        self.analysis_widget.set_network(self.network)
        right_tab.addTab(self.analysis_widget, "交通分析")
        
        # 模拟控制选项卡
        self.simulation_widget = SimulationControlWidget()
        self.simulation_widget.set_network(self.network)
        self.simulation_widget.traffic_state_updated.connect(self.update_traffic_state)
        right_tab.addTab(self.simulation_widget, "模拟控制")
        
        # 机器学习选项卡
        self.ml_widget = QWidget()
        self.init_ml_tab()
        right_tab.addTab(self.ml_widget, "机器学习")
        
        splitter.addWidget(right_tab)
        splitter.setSizes([1000, 600])
        
        main_layout.addWidget(splitter)
        
        # 创建工具栏
        self.create_toolbar()
        
        # 创建状态栏
        self.statusBar().showMessage("就绪")
        
        # 创建菜单栏
        self.create_menubar()
        
    def create_menubar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        new_action = QAction("新建", self)
        new_action.setShortcut("Ctrl+N")
        file_menu.addAction(new_action)
        
        open_action = QAction("打开", self)
        open_action.setShortcut("Ctrl+O")
        file_menu.addAction(open_action)
        
        save_action = QAction("保存", self)
        save_action.setShortcut("Ctrl+S")
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu("工具")
        
        path_planning_action = QAction("路径规划", self)
        path_planning_action.triggered.connect(self.show_path_planning_dialog)
        tools_menu.addAction(path_planning_action)
        
        od_analysis_action = QAction("OD分析", self)
        tools_menu.addAction(od_analysis_action)
        
        emission_analysis_action = QAction("排放分析", self)
        tools_menu.addAction(emission_analysis_action)
        
        # 视图菜单
        view_menu = menubar.addMenu("视图")
        
        traffic_flow_action = QAction("交通流量", self)
        traffic_flow_action.setCheckable(True)
        traffic_flow_action.toggled.connect(self.map_canvas.set_show_traffic_flow)
        view_menu.addAction(traffic_flow_action)
        
        public_transit_action = QAction("公共交通", self)
        public_transit_action.setCheckable(True)
        public_transit_action.toggled.connect(self.map_canvas.set_show_public_transit)
        view_menu.addAction(public_transit_action)
        
        zones_action = QAction("交通分区", self)
        zones_action.setCheckable(True)
        zones_action.toggled.connect(self.map_canvas.set_show_zones)
        view_menu.addAction(zones_action)
        
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar("主工具栏")
        self.addToolBar(toolbar)
        
        # 路径规划操作
        path_planning_action = QAction("路径规划", self)
        path_planning_action.triggered.connect(self.show_path_planning_dialog)
        toolbar.addAction(path_planning_action)
        
        # 交通流量显示
        traffic_flow_action = QAction("交通流量", self)
        traffic_flow_action.setCheckable(True)
        traffic_flow_action.toggled.connect(self.map_canvas.set_show_traffic_flow)
        toolbar.addAction(traffic_flow_action)
        
        toolbar.addSeparator()
        
        # 缩放工具
        zoom_in_action = QAction("放大", self)
        zoom_out_action = QAction("缩小", self)
        toolbar.addAction(zoom_in_action)
        toolbar.addAction(zoom_out_action)
        
    def init_ml_tab(self):
        """初始化机器学习选项卡"""
        layout = QVBoxLayout()
        
        # 模型训练部分
        train_group = QGroupBox("模型训练")
        train_layout = QVBoxLayout()
        
        train_button = QPushButton("训练预测模型")
        train_layout.addWidget(train_button)
        
        self.ml_results = QTextEdit()
        self.ml_results.setMaximumHeight(100)
        train_layout.addWidget(self.ml_results)
        
        train_group.setLayout(train_layout)
        layout.addWidget(train_group)
        
        # 预测部分
        predict_group = QGroupBox("交通预测")
        predict_layout = QVBoxLayout()
        
        # 预测参数
        params_layout = QHBoxLayout()
        params_layout.addWidget(QLabel("道路:"))
        self.road_combo = QComboBox()
        params_layout.addWidget(self.road_combo)
        
        params_layout.addWidget(QLabel("小时:"))
        self.hour_spin = QSpinBox()
        self.hour_spin.setRange(0, 23)
        self.hour_spin.setValue(8)
        params_layout.addWidget(self.hour_spin)
        predict_layout.addLayout(params_layout)
        
        predict_button = QPushButton("预测流量")
        predict_layout.addWidget(predict_button)
        
        self.prediction_result = QLabel("预测结果将显示在这里")
        predict_layout.addWidget(self.prediction_result)
        
        predict_group.setLayout(predict_layout)
        layout.addWidget(predict_group)
        
        self.ml_widget.setLayout(layout)
        
        # 连接信号
        train_button.clicked.connect(self.train_ml_model)
        predict_button.clicked.connect(self.predict_traffic)
        
    def train_ml_model(self):
        """训练机器学习模型"""
        try:
            r2, rmse = self.network.train_ml_predictor()
            self.ml_results.setText(
                f"模型训练完成!\n"
                f"R²分数: {r2:.3f}\n"
                f"RMSE: {rmse:.1f}"
            )
            
            # 更新道路选择框
            self.road_combo.clear()
            for idx, road in self.network.roads.iterrows():
                self.road_combo.addItem(str(road.name), idx)
                
        except Exception as e:
            self.ml_results.setText(f"训练错误: {str(e)}")
            
    def predict_traffic(self):
        """预测交通流量"""
        try:
            road_id = self.road_combo.currentData()
            hour = self.hour_spin.value()
            
            # 简化：假设工作日和一月
            predicted_volume = self.network.predict_traffic(road_id, hour, 0, 1)
            
            road = self.network.roads.iloc[road_id]
            capacity = road.capacity
            
            self.prediction_result.setText(
                f"预测流量: {predicted_volume:.0f} 车辆/小时\n"
                f"道路容量: {capacity:.0f} 车辆/小时\n"
                f"饱和度: {predicted_volume/capacity:.2f}"
            )
            
        except Exception as e:
            self.prediction_result.setText(f"预测错误: {str(e)}")
        
    def create_sample_network(self):
        """创建示例交通网络"""
        # 添加交通分区
        self.network.add_zone(0, "住宅区", "residential", 5000, 500, Polygon([(0, 0), (0, 2000), (2000, 2000), (2000, 0)]))
        self.network.add_zone(1, "商业区", "commercial", 1000, 8000, Polygon([(2000, 0), (2000, 2000), (4000, 2000), (4000, 0)]))
        self.network.add_zone(2, "工业区", "industrial", 2000, 10000, Polygon([(0, 2000), (0, 4000), (2000, 4000), (2000, 2000)]))
        self.network.add_zone(3, "混合区", "mixed", 4000, 6000, Polygon([(2000, 2000), (2000, 4000), (4000, 4000), (4000, 2000)]))
        
        # 添加交叉口
        self.network.add_intersection(0, "A", "signal", {"cycle": 120, "green": 60}, Point(0, 0))
        self.network.add_intersection(1, "B", "signal", {"cycle": 120, "green": 60}, Point(1000, 0))
        self.network.add_intersection(2, "C", "signal", {"cycle": 120, "green": 60}, Point(2000, 0))
        self.network.add_intersection(3, "D", "roundabout", {}, Point(3000, 0))
        self.network.add_intersection(4, "E", "signal", {"cycle": 120, "green": 60}, Point(4000, 0))
        
        self.network.add_intersection(5, "F", "signal", {"cycle": 120, "green": 60}, Point(0, 1000))
        self.network.add_intersection(6, "G", "signal", {"cycle": 120, "green": 60}, Point(1000, 1000))
        self.network.add_intersection(7, "H", "signal", {"cycle": 120, "green": 60}, Point(2000, 1000))
        self.network.add_intersection(8, "I", "signal", {"cycle": 120, "green": 60}, Point(3000, 1000))
        self.network.add_intersection(9, "J", "signal", {"cycle": 120, "green": 60}, Point(4000, 1000))
        
        self.network.add_intersection(10, "K", "signal", {"cycle": 120, "green": 60}, Point(0, 2000))
        self.network.add_intersection(11, "L", "signal", {"cycle": 120, "green": 60}, Point(1000, 2000))
        self.network.add_intersection(12, "M", "signal", {"cycle": 120, "green": 60}, Point(2000, 2000))
        self.network.add_intersection(13, "N", "signal", {"cycle": 120, "green": 60}, Point(3000, 2000))
        self.network.add_intersection(14, "O", "signal", {"cycle": 120, "green": 60}, Point(4000, 2000))
        
        self.network.add_intersection(15, "P", "signal", {"cycle": 120, "green": 60}, Point(0, 3000))
        self.network.add_intersection(16, "Q", "signal", {"cycle": 120, "green": 60}, Point(1000, 3000))
        self.network.add_intersection(17, "R", "signal", {"cycle": 120, "green": 60}, Point(2000, 3000))
        self.network.add_intersection(18, "S", "signal", {"cycle": 120, "green": 60}, Point(3000, 3000))
        self.network.add_intersection(19, "T", "signal", {"cycle": 120, "green": 60}, Point(4000, 3000))
        
        self.network.add_intersection(20, "U", "signal", {"cycle": 120, "green": 60}, Point(0, 4000))
        self.network.add_intersection(21, "V", "signal", {"cycle": 120, "green": 60}, Point(1000, 4000))
        self.network.add_intersection(22, "W", "signal", {"cycle": 120, "green": 60}, Point(2000, 4000))
        self.network.add_intersection(23, "X", "signal", {"cycle": 120, "green": 60}, Point(3000, 4000))
        self.network.add_intersection(24, "Y", "signal", {"cycle": 120, "green": 60}, Point(4000, 4000))
        
        # 添加道路
        # 水平道路
        for y in [0, 1000, 2000, 3000, 4000]:
            for i in range(4):
                start_x, end_x = i * 1000, (i + 1) * 1000
                road_id = len(self.network.roads)
                lanes = 4 if y in [0, 2000, 4000] else 2
                capacity = lanes * 1000
                self.network.add_road(
                    road_id, f"Road_{y}_{start_x}_{end_x}", 
                    "arterial" if lanes == 4 else "collector",
                    lanes, 60 if lanes == 4 else 40, capacity,
                    LineString([(start_x, y), (end_x, y)])
                )
        
        # 垂直道路
        for x in [0, 1000, 2000, 3000, 4000]:
            for i in range(4):
                start_y, end_y = i * 1000, (i + 1) * 1000
                road_id = len(self.network.roads)
                lanes = 4 if x in [0, 2000, 4000] else 2
                capacity = lanes * 1000
                self.network.add_road(
                    road_id, f"Road_{x}_{start_y}_{end_y}", 
                    "arterial" if lanes == 4 else "collector",
                    lanes, 60 if lanes == 4 else 40, capacity,
                    LineString([(x, start_y), (x, end_y)])
                )
        
        # 添加公共交通
        self.network.add_public_transit(
            0, "地铁1号线", "subway", 1000, 12,
            LineString([(500, 0), (500, 1000), (500, 2000), (500, 3000), (500, 4000)])
        )
        
        self.network.add_public_transit(
            1, "公交2路", "bus", 80, 10,
            LineString([(0, 500), (1000, 500), (2000, 500), (3000, 500), (4000, 500)])
        )
        
        # 生成交通数据和OD矩阵
        self.network.generate_traffic_data()
        self.network.generate_od_matrix()
        
        # 更新地图
        self.map_canvas.set_network(self.network)
        self.statusBar().showMessage("示例网络已加载")
        
    def show_path_planning_dialog(self):
        """显示路径规划对话框"""
        dialog = AdvancedPathPlanningDialog(self, self.network)
        if dialog.exec_():
            start_point = dialog.get_start_point()
            end_point = dialog.get_end_point()
            mode = dialog.get_mode()
            criteria = dialog.get_criteria()
            
            path, path_details = self.network.find_optimal_path(start_point, end_point, mode, criteria)
            if path:
                self.map_canvas.highlight_path(path, path_details)
                
                # 显示路径详情
                total_time = sum(segment['time'] for segment in path_details)
                total_distance = sum(segment['length'] for segment in path_details)
                
                self.statusBar().showMessage(
                    f"找到路径: {len(path)}个节点, "
                    f"总时间: {total_time/60:.1f}分钟, "
                    f"总距离: {total_distance:.0f}米"
                )
            else:
                self.statusBar().showMessage("未找到路径")
                
    def update_traffic_state(self, traffic_state):
        """更新交通状态"""
        self.map_canvas.update_traffic_state(traffic_state)
        
        # 更新分析面板（如果需要）
        if self.analysis_widget.analysis_combo.currentText() in ["交通流量", "拥堵指数", "速度分布"]:
            self.analysis_widget.update_analysis()


class AdvancedPathPlanningDialog(QDialog):
    """高级路径规划对话框"""
    def __init__(self, parent=None, network=None):
        super().__init__(parent)
        self.network = network
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("路径规划")
        self.setMinimumWidth(400)
        layout = QVBoxLayout()
        
        # 起点选择
        start_layout = QHBoxLayout()
        start_layout.addWidget(QLabel("起点:"))
        self.start_combo = QComboBox()
        for idx, zone in self.network.zones.iterrows():
            self.start_combo.addItem(str(zone.name), idx)
        start_layout.addWidget(self.start_combo)
        layout.addLayout(start_layout)
        
        # 终点选择
        end_layout = QHBoxLayout()
        end_layout.addWidget(QLabel("终点:"))
        self.end_combo = QComboBox()
        for idx, zone in self.network.zones.iterrows():
            self.end_combo.addItem(str(zone.name), idx)
        end_layout.addWidget(self.end_combo)
        layout.addLayout(end_layout)
        
        # 交通模式
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("交通模式:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["汽车", "公共交通", "步行", "自行车"])
        mode_layout.addWidget(self.mode_combo)
        layout.addLayout(mode_layout)
        
        # 路径标准
        criteria_layout = QHBoxLayout()
        criteria_layout.addWidget(QLabel("路径标准:"))
        self.criteria_combo = QComboBox()
        self.criteria_combo.addItems(["最短时间", "最短距离", "最少拥堵", "最少换乘"])
        criteria_layout.addWidget(self.criteria_combo)
        layout.addLayout(criteria_layout)
        
        # 按钮
        button_layout = QHBoxLayout()
        ok_button = QPushButton("确定")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
    def get_start_point(self):
        """获取起点坐标"""
        idx = self.start_combo.currentData()
        centroid = self.network.zones.iloc[idx].geometry.centroid
        return (centroid.x, centroid.y)
    
    def get_end_point(self):
        """获取终点坐标"""
        idx = self.end_combo.currentData()
        centroid = self.network.zones.iloc[idx].geometry.centroid
        return (centroid.x, centroid.y)
    
    def get_mode(self):
        """获取交通模式"""
        mode = self.mode_combo.currentText()
        if mode == "汽车":
            return "car"
        elif mode == "公共交通":
            return "transit"
        elif mode == "步行":
            return "walk"
        else:  # 自行车
            return "bike"
    
    def get_criteria(self):
        """获取路径标准"""
        criteria = self.criteria_combo.currentText()
        if criteria == "最短时间":
            return "time"
        elif criteria == "最短距离":
            return "distance"
        elif criteria == "最少拥堵":
            return "congestion"
        else:  # 最少换乘
            return "transfers"


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = AdvancedMainWindow()
    main_window.show()
    sys.exit(app.exec_())