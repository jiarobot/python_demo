import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import math
from scipy import signal
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import networkx as nx
from geopy.distance import geodesic
import requests
import json
from typing import Dict, List, Tuple, Any
import warnings
warnings.filterwarnings('ignore')

class YinFuEnergySystem:
    """黄帝阴符经五贼能量系统"""
    
    def __init__(self):
        self.five_thieves = {
            '金': {'frequency': 18.5, 'amplitude': 1.0, 'phase': 0.0, 'color': '#FFD700'},
            '木': {'frequency': 7.83, 'amplitude': 0.8, 'phase': 0.618, 'color': '#32CD32'},
            '水': {'frequency': 12.0, 'amplitude': 1.2, 'phase': 1.618, 'color': '#1E90FF'},
            '火': {'frequency': 25.0, 'amplitude': 0.9, 'phase': 2.618, 'color': '#FF4500'},
            '土': {'frequency': 5.0, 'amplitude': 1.1, 'phase': 3.1416, 'color': '#8B4513'}
        }
        
    def generate_energy_wave(self, thief: str, duration: int = 1000) -> np.ndarray:
        """生成五贼能量波"""
        params = self.five_thieves[thief]
        t = np.linspace(0, 10, duration)
        frequency = params['frequency']
        amplitude = params['amplitude']
        phase = params['phase']
        
        # 生成基波和调制波
        base_wave = amplitude * np.sin(2 * np.pi * frequency * t + phase)
        modulation = 0.3 * np.sin(2 * np.pi * 0.1 * frequency * t)
        
        # 添加混沌特性
        chaos_component = 0.1 * np.random.normal(0, 1, duration)
        
        wave = base_wave * (1 + modulation) + chaos_component
        return wave
    
    def calculate_energy_resonance(self, crop_type: str, lunar_phase: float) -> Dict[str, float]:
        """计算作物与五贼能量的共振强度"""
        resonance_scores = {}
        
        for thief, params in self.five_thieves.items():
            base_freq = params['frequency']
            
            # 不同作物的共振频率映射
            crop_frequencies = {
                'wheat': 7.5, 'rice': 8.2, 'corn': 6.8, 
                'cotton': 9.1, 'vegetable': 10.3
            }
            
            crop_freq = crop_frequencies.get(crop_type, 8.0)
            
            # 考虑月相影响的共振计算
            lunar_modulation = 1 + 0.2 * math.sin(lunar_phase * 2 * math.pi)
            
            # 共振强度计算（基于频率匹配度）
            freq_diff = abs(base_freq - crop_freq)
            resonance = lunar_modulation * math.exp(-freq_diff / 2)
            
            resonance_scores[thief] = resonance
        
        return resonance_scores

class DiMuAgriculture:
    """地母经农业预测系统"""
    
    def __init__(self):
        self.jiazi_cycles = self._load_jiazi_data()
        self.weather_patterns = self._load_weather_patterns()
        
    def _load_jiazi_data(self) -> Dict[str, Dict]:
        """加载60甲子数据"""
        # 简化的甲子年预测数据
        jiazi_data = {
            '甲子': {'advice': '高田宜早种', 'risk': '水灾', 'yield_trend': 1.2},
            '乙丑': {'advice': '低田晚种佳', 'risk': '干旱', 'yield_trend': 0.9},
            '丙寅': {'advice': '多种豆类作物', 'risk': '虫害', 'yield_trend': 1.1},
            '丁卯': {'advice': '适宜果树种植', 'risk': '霜冻', 'yield_trend': 1.15},
            '戊辰': {'advice': '扩大粮食面积', 'risk': '风灾', 'yield_trend': 1.3},
            # 可以继续添加其他59个甲子...
        }
        return jiazi_data
    
    def _load_weather_patterns(self) -> Dict[str, List[float]]:
        """加载天气模式数据"""
        return {
            '厄尔尼诺': [0.8, 1.2, 0.9, 1.1, 1.3, 0.7],
            '拉尼娜': [1.1, 0.8, 1.2, 0.9, 0.7, 1.4],
            '正常年': [1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
        }
    
    def predict_yield(self, jiazi_year: str, crop_type: str, region: str) -> Dict[str, Any]:
        """预测作物产量"""
        year_data = self.jiazi_cycles.get(jiazi_year, {})
        
        # 基础产量预测
        base_yield = {
            'wheat': 5000, 'rice': 6500, 'corn': 7000, 
            'cotton': 3000, 'vegetable': 8000
        }
        
        base = base_yield.get(crop_type, 5000)
        trend = year_data.get('yield_trend', 1.0)
        
        # 区域调整因子
        region_factors = {'north': 0.9, 'south': 1.1, 'east': 1.05, 'west': 0.85}
        region_factor = region_factors.get(region, 1.0)
        
        predicted_yield = base * trend * region_factor
        
        return {
            'predicted_yield': predicted_yield,
            'advice': year_data.get('advice', '正常种植'),
            'risk': year_data.get('risk', '无显著风险'),
            'confidence': 0.85
        }

class TopologicalFarm:
    """拓扑农场实现"""
    
    def __init__(self, location: Tuple[float, float], size: float):
        self.location = location  # (纬度, 经度)
        self.size = size  # 农场面积(公顷)
        self.yin_fu_system = YinFuEnergySystem()
        self.di_mu_system = DiMuAgriculture()
        self.energy_devices = {}
        
    def setup_energy_devices(self):
        """设置能量装置"""
        # 五贼能量转换器
        devices = {
            'wood_tower': {'type': '木贼谐振塔', 'power': 1.0, 'status': 'active'},
            'water_channel': {'type': '水弦虹吸渠', 'power': 0.8, 'status': 'active'},
            'fire_prism': {'type': '火棱镜温室', 'power': 0.9, 'status': 'active'},
            'metal_field': {'type': '金弦磁化场', 'power': 0.7, 'status': 'active'},
            'earth_network': {'type': '土波传导网', 'power': 1.1, 'status': 'active'}
        }
        self.energy_devices = devices
    
    def calculate_optimal_planting(self, crop_type: str, current_date: datetime) -> Dict[str, Any]:
        """计算最优种植方案"""
        # 获取当前月相
        lunar_phase = self._get_lunar_phase(current_date)
        
        # 计算能量共振
        resonance = self.yin_fu_system.calculate_energy_resonance(crop_type, lunar_phase)
        
        # 获取甲子年预测
        jiazi_year = self._get_jiazi_year(current_date.year)
        yield_prediction = self.di_mu_system.predict_yield(jiazi_year, crop_type, 'north')
        
        # 计算最优种植参数
        optimal_density = self._calculate_planting_density(crop_type, resonance)
        energy_schedule = self._generate_energy_schedule(resonance)
        
        return {
            'crop_type': crop_type,
            'optimal_density': optimal_density,
            'energy_resonance': resonance,
            'yield_prediction': yield_prediction,
            'energy_schedule': energy_schedule,
            'recommended_devices': self._recommend_devices(resonance)
        }
    
    def _get_lunar_phase(self, date: datetime) -> float:
        """计算月相（简化版）"""
        # 简化的月相计算，实际应该使用天文算法
        days_in_month = 29.53
        day_of_cycle = (date.day + date.month * 30) % days_in_month
        return day_of_cycle / days_in_month
    
    def _get_jiazi_year(self, year: int) -> str:
        """计算甲子年"""
        jiazi_cycle = ['甲子', '乙丑', '丙寅', '丁卯', '戊辰', '己巳', '庚午', '辛未', '壬申', '癸酉']
        index = (year - 1984) % 60 % 10  # 从1984年（甲子年）开始计算
        return jiazi_cycle[index]
    
    def _calculate_planting_density(self, crop_type: str, resonance: Dict[str, float]) -> float:
        """计算种植密度"""
        base_density = {
            'wheat': 200, 'rice': 150, 'corn': 60, 
            'cotton': 80, 'vegetable': 400
        }
        
        base = base_density.get(crop_type, 100)
        
        # 根据木贼共振调整密度
        wood_resonance = resonance.get('木', 1.0)
        density_adjustment = 1 + 0.2 * (wood_resonance - 1)
        
        return base * density_adjustment
    
    def _generate_energy_schedule(self, resonance: Dict[str, float]) -> List[Dict]:
        """生成能量调度计划"""
        schedule = []
        
        for thief, strength in resonance.items():
            if strength > 0.8:  # 高共振强度
                schedule.append({
                    'energy_type': thief,
                    'intensity': strength,
                    'duration_hours': 6,
                    'optimal_time': 'day' if thief in ['火', '金'] else 'night'
                })
        
        return schedule
    
    def _recommend_devices(self, resonance: Dict[str, float]) -> List[str]:
        """推荐使用的能量装置"""
        recommendations = []
        
        if resonance.get('木', 0) > 0.8:
            recommendations.append('木贼谐振塔')
        if resonance.get('水', 0) > 0.7:
            recommendations.append('水弦虹吸渠')
        if resonance.get('火', 0) > 0.75:
            recommendations.append('火棱镜温室')
        if resonance.get('金', 0) > 0.6:
            recommendations.append('金弦磁化场')
        if resonance.get('土', 0) > 0.9:
            recommendations.append('土波传导网')
            
        return recommendations

class ChaosWeatherPredictor:
    """混沌气候预测器"""
    
    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
        
    def prepare_training_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """准备训练数据（模拟）"""
        # 在实际应用中，这里应该使用真实的历史气候数据
        np.random.seed(42)
        n_samples = 1000
        
        # 特征：太阳黑子、海温、气压等（改为7维以匹配预测时的特征数量）
        X = np.random.randn(n_samples, 7)  # 将6改为7
        
        # 目标：降水量、温度等
        y = np.column_stack([
            np.random.normal(100, 30, n_samples),  # 降水量
            np.random.normal(25, 5, n_samples)     # 平均温度
        ])
        
        return X, y
    
    def train(self):
        """训练预测模型"""
        X, y = self.prepare_training_data()
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)
        self.is_trained = True
    
    def predict_weather(self, jiazi_year: str, month: int) -> Dict[str, float]:
        """预测天气"""
        if not self.is_trained:
            self.train()
        
        # 基于甲子年和月份生成特征
        jiazi_features = self._jiazi_to_features(jiazi_year)
        month_features = self._month_to_features(month)
        
        features = np.concatenate([jiazi_features, month_features]).reshape(1, -1)
        features_scaled = self.scaler.transform(features)
        
        prediction = self.model.predict(features_scaled)[0]
        
        return {
            'precipitation_mm': max(0, prediction[0]),
            'temperature_c': prediction[1],
            'humidity_percent': 60 + 20 * np.random.random(),
            'wind_speed_kmh': 5 + 10 * np.random.random()
        }
    
    def _jiazi_to_features(self, jiazi_year: str) -> np.ndarray:
        """将甲子年转换为特征向量"""
        # 简化的特征映射
        jiazi_mapping = {
            '甲子': [1, 0, 0, 0.8, 0.2],
            '乙丑': [0, 1, 0, 0.3, 0.7],
            '丙寅': [0, 0, 1, 0.6, 0.4],
            '丁卯': [1, 0, 0, 0.7, 0.3],
            '戊辰': [0, 1, 0, 0.9, 0.1]
        }
        return np.array(jiazi_mapping.get(jiazi_year, [0.5, 0.5, 0.5, 0.5, 0.5]))
    
    def _month_to_features(self, month: int) -> np.ndarray:
        """将月份转换为特征向量"""
        seasonal = [math.sin(2 * math.pi * (month - 1) / 12),
                   math.cos(2 * math.pi * (month - 1) / 12)]
        return np.array(seasonal)

class GlobalEnergyGrid:
    """全球能量网格系统"""
    
    def __init__(self):
        self.nodes = self._initialize_grid_nodes()
        self.connections = self._initialize_connections()
        self.energy_flow = {}
        
    def _initialize_grid_nodes(self) -> Dict[str, Dict]:
        """初始化网格节点"""
        nodes = {
            'qinghai_tibet': {
                'name': '青藏高原引力波基站',
                'type': '土弦',
                'location': (35.0, 85.0),
                'power_capacity': 1000,
                'current_power': 850
            },
            'mariana_trench': {
                'name': '马里亚纳海沟地热井', 
                'type': '水弦',
                'location': (18.0, 145.0),
                'power_capacity': 800,
                'current_power': 720
            },
            'congo_rainforest': {
                'name': '刚果雨林生物电站',
                'type': '木弦', 
                'location': (-3.0, 23.0),
                'power_capacity': 600,
                'current_power': 550
            },
            'siberia_permafrost': {
                'name': '西伯利亚冻土碳库',
                'type': '金弦',
                'location': (65.0, 100.0),
                'power_capacity': 700, 
                'current_power': 630
            },
            'sahara_desert': {
                'name': '撒哈拉沙漠光阱',
                'type': '火弦',
                'location': (25.0, 15.0),
                'power_capacity': 1200,
                'current_power': 1100
            }
        }
        return nodes
    
    def _initialize_connections(self) -> List[Tuple[str, str, str]]:
        """初始化连接关系"""
        return [
            ('qinghai_tibet', 'mariana_trench', '土弦→水弦'),
            ('mariana_trench', 'congo_rainforest', '水弦→木弦'),
            ('congo_rainforest', 'siberia_permafrost', '木弦→金弦'),
            ('siberia_permafrost', 'sahara_desert', '金弦→火弦'),
            ('sahara_desert', 'qinghai_tibet', '火弦→土弦')
        ]
    
    def calculate_energy_flow(self) -> Dict[str, Any]:
        """计算能量流动"""
        total_power = sum(node['current_power'] for node in self.nodes.values())
        avg_power = total_power / len(self.nodes)
        
        # 计算能量平衡度
        balance_scores = []
        for node_id, node in self.nodes.items():
            balance = node['current_power'] / node['power_capacity']
            balance_scores.append(balance)
        
        balance_std = np.std(balance_scores)
        stability = 1 / (1 + balance_std)  # 稳定性指标
        
        self.energy_flow = {
            'total_power': total_power,
            'average_power': avg_power,
            'stability': stability,
            'balance_scores': dict(zip(self.nodes.keys(), balance_scores))
        }
        
        return self.energy_flow
    
    def optimize_energy_distribution(self) -> Dict[str, float]:
        """优化能量分布"""
        flow = self.calculate_energy_flow()
        avg_power = flow['average_power']
        
        adjustments = {}
        for node_id, node in self.nodes.items():
            current = node['current_power']
            capacity = node['power_capacity']
            
            # 计算调整量
            if current < avg_power * 0.9:
                adjustment = min(avg_power - current, capacity - current)
                adjustments[node_id] = adjustment
            elif current > avg_power * 1.1:
                adjustment = avg_power - current
                adjustments[node_id] = adjustment
        
        return adjustments

class AgriculturalCivilization:
    """新农道文明系统"""
    
    def __init__(self):
        self.energy_grid = GlobalEnergyGrid()
        self.weather_predictor = ChaosWeatherPredictor()
        self.farms = []
        
    def add_farm(self, farm: TopologicalFarm):
        """添加农场"""
        self.farms.append(farm)
    
    def run_simulation(self, years: int = 1) -> Dict[str, Any]:
        """运行文明模拟"""
        results = {
            'total_yield': 0,
            'energy_efficiency': 0,
            'weather_accuracy': 0,
            'grid_stability': 0,
            'farm_reports': []
        }
        
        current_date = datetime.now()
        
        for year in range(years):
            year_results = self._simulate_year(current_date)
            results['total_yield'] += year_results['total_yield']
            results['energy_efficiency'] += year_results['energy_efficiency']
            results['weather_accuracy'] += year_results['weather_accuracy']
            results['grid_stability'] += year_results['grid_stability']
            results['farm_reports'].extend(year_results['farm_reports'])
            
            current_date = current_date.replace(year=current_date.year + 1)
        
        # 计算平均值
        if years > 0:
            for key in ['energy_efficiency', 'weather_accuracy', 'grid_stability']:
                results[key] /= years
        
        return results
    
    def _simulate_year(self, start_date: datetime) -> Dict[str, Any]:
        """模拟一年"""
        total_yield = 0
        farm_reports = []
        
        for farm in self.farms:
            # 为每种作物计算最优种植
            crops = ['wheat', 'rice', 'corn', 'cotton']
            farm_yield = 0
            
            for crop in crops:
                planting_plan = farm.calculate_optimal_planting(crop, start_date)
                predicted_yield = planting_plan['yield_prediction']['predicted_yield']
                farm_yield += predicted_yield
                
                farm_reports.append({
                    'farm_location': farm.location,
                    'crop': crop,
                    'plan': planting_plan,
                    'predicted_yield': predicted_yield
                })
            
            total_yield += farm_yield
        
        # 计算各项指标
        grid_flow = self.energy_grid.calculate_energy_flow()
        
        return {
            'total_yield': total_yield,
            'energy_efficiency': 0.85,  # 模拟值
            'weather_accuracy': 0.92,   # 模拟值  
            'grid_stability': grid_flow['stability'],
            'farm_reports': farm_reports
        }

def visualize_system(civilization: AgriculturalCivilization):
    """可视化系统状态"""
    fig = plt.figure(figsize=(20, 12))
    
    # 1. 五贼能量波可视化
    ax1 = plt.subplot(2, 3, 1)
    yin_fu = YinFuEnergySystem()
    t = np.linspace(0, 10, 1000)
    
    for i, (thief, params) in enumerate(yin_fu.five_thieves.items()):
        wave = yin_fu.generate_energy_wave(thief, 1000)
        ax1.plot(t[:100], wave[:100], label=thief, color=params['color'], linewidth=2)
    
    ax1.set_title('黄帝阴符经 - 五贼能量波', fontsize=14, fontweight='bold')
    ax1.set_xlabel('时间')
    ax1.set_ylabel('能量强度')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2. 全球能量网格可视化
    ax2 = plt.subplot(2, 3, 2)
    grid = civilization.energy_grid
    
    # 创建网络图
    G = nx.DiGraph()
    for node_id, node in grid.nodes.items():
        G.add_node(node_id, **node)
    
    for connection in grid.connections:
        G.add_edge(connection[0], connection[1], label=connection[2])
    
    pos = nx.circular_layout(G)
    node_colors = []
    for node_id in G.nodes():
        node_type = grid.nodes[node_id]['type']
        color_map = {'土弦': '#8B4513', '水弦': '#1E90FF', '木弦': '#32CD32', 
                    '金弦': '#FFD700', '火弦': '#FF4500'}
        node_colors.append(color_map.get(node_type, 'gray'))
    
    nx.draw(G, pos, with_labels=True, node_color=node_colors, 
            node_size=2000, font_size=8, font_weight='bold',
            arrows=True, arrowsize=20, edge_color='gray')
    
    edge_labels = {(u, v): d['label'] for u, v, d in G.edges(data=True)}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=6)
    
    ax2.set_title('全球能量网格 - 五行超导环流', fontsize=14, fontweight='bold')
    
    # 3. 农场产量预测
    ax3 = plt.subplot(2, 3, 3)
    crops = ['wheat', 'rice', 'corn', 'cotton']
    yields = []
    
    di_mu = DiMuAgriculture()
    for crop in crops:
        prediction = di_mu.predict_yield('甲子', crop, 'north')
        yields.append(prediction['predicted_yield'])
    
    bars = ax3.bar(crops, yields, color=['#FFD700', '#32CD32', '#8B4513', '#1E90FF'])
    ax3.set_title('地母经 - 作物产量预测', fontsize=14, fontweight='bold')
    ax3.set_ylabel('产量 (kg/公顷)')
    
    # 在柱状图上添加数值
    for bar, yield_val in zip(bars, yields):
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 100,
                f'{yield_val:.0f}', ha='center', va='bottom')
    
    # 4. 能量共振雷达图
    ax4 = plt.subplot(2, 3, 4, polar=True)
    farm = TopologicalFarm((35.0, 115.0), 100)
    resonance = farm.yin_fu_system.calculate_energy_resonance('wheat', 0.5)
    
    categories = list(resonance.keys())
    values = list(resonance.values())
    values += values[:1]  # 闭合雷达图
    
    angles = np.linspace(0, 2*np.pi, len(categories), endpoint=False).tolist()
    angles += angles[:1]
    
    ax4.plot(angles, values, 'o-', linewidth=2, label='能量共振')
    ax4.fill(angles, values, alpha=0.25)
    ax4.set_xticks(angles[:-1])
    ax4.set_xticklabels(categories)
    ax4.set_title('五贼能量共振分析', fontsize=14, fontweight='bold')
    ax4.grid(True)
    
    # 5. 气候预测可视化
    ax5 = plt.subplot(2, 3, 5)
    predictor = ChaosWeatherPredictor()
    months = range(1, 13)
    temperatures = []
    precipitations = []
    
    for month in months:
        weather = predictor.predict_weather('甲子', month)
        temperatures.append(weather['temperature_c'])
        precipitations.append(weather['precipitation_mm'])
    
    ax5.plot(months, temperatures, 'r-o', label='温度', linewidth=2)
    ax5.set_xlabel('月份')
    ax5.set_ylabel('温度 (°C)', color='red')
    ax5.tick_params(axis='y', labelcolor='red')
    
    ax6 = ax5.twinx()
    ax6.bar(months, precipitations, alpha=0.3, color='blue', label='降水量')
    ax6.set_ylabel('降水量 (mm)', color='blue')
    ax6.tick_params(axis='y', labelcolor='blue')
    
    ax5.set_title('混沌气候预测', fontsize=14, fontweight='bold')
    ax5.legend(loc='upper left')
    ax6.legend(loc='upper right')
    
    # 6. 系统总体状态
    ax7 = plt.subplot(2, 3, 6)
    simulation_results = civilization.run_simulation(1)
    
    metrics = ['能量效率', '气候精度', '网格稳定', '产量指数']
    values = [
        simulation_results['energy_efficiency'],
        simulation_results['weather_accuracy'], 
        simulation_results['grid_stability'],
        min(1.0, simulation_results['total_yield'] / 1000000)
    ]
    
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
    bars = ax7.bar(metrics, values, color=colors)
    ax7.set_ylim(0, 1)
    ax7.set_title('系统总体性能', fontsize=14, fontweight='bold')
    ax7.set_ylabel('性能指标')
    
    # 添加数值标签
    for bar, value in zip(bars, values):
        ax7.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                f'{value:.2f}', ha='center', va='bottom')
    
    plt.tight_layout()
    plt.show()

def main():
    """主函数 - 运行完整的时空农耕拓扑学系统"""
    print("=" * 80)
    print("           时空农耕拓扑学系统 - 黄帝阴符经 × 地母经集成")
    print("=" * 80)
    
    # 创建新农道文明实例
    civilization = AgriculturalCivilization()
    
    # 创建多个拓扑农场
    farm_locations = [
        (35.0, 115.0),   # 华北平原
        (30.0, 120.0),   # 长江三角洲  
        (40.0, 110.0),   # 内蒙古草原
        (25.0, 105.0)    # 云贵高原
    ]
    
    for i, location in enumerate(farm_locations):
        farm = TopologicalFarm(location, 100 + i * 50)
        farm.setup_energy_devices()
        civilization.add_farm(farm)
        print(f"✅ 创建农场 {i+1}: 位置 {location}, 面积 {farm.size} 公顷")
    
    # 运行系统模拟
    print("\n🔮 运行文明模拟...")
    results = civilization.run_simulation(years=1)
    
    print(f"\n📊 模拟结果:")
    print(f"  总产量: {results['total_yield']:,.0f} kg")
    print(f"  能量效率: {results['energy_efficiency']:.1%}")
    print(f"  气候预测精度: {results['weather_accuracy']:.1%}")
    print(f"  网格稳定性: {results['grid_stability']:.3f}")
    
    # 显示详细农场报告
    print(f"\n🏠 农场详细报告:")
    for i, report in enumerate(results['farm_reports'][:4]):  # 显示前4个报告
        print(f"  农场 {i+1} - {report['crop']}: {report['predicted_yield']:,.0f} kg")
        print(f"    推荐装置: {', '.join(report['plan']['recommended_devices'])}")
    
    # 优化全球能量网格
    print(f"\n🌍 全球能量网格优化:")
    grid_flow = civilization.energy_grid.calculate_energy_flow()
    adjustments = civilization.energy_grid.optimize_energy_distribution()
    
    print(f"  总功率: {grid_flow['total_power']:,.0f} MW")
    print(f"  平均功率: {grid_flow['average_power']:,.0f} MW") 
    print(f"  稳定性指数: {grid_flow['stability']:.3f}")
    
    if adjustments:
        print("  能量调整建议:")
        for node_id, adjustment in adjustments.items():
            node_name = civilization.energy_grid.nodes[node_id]['name']
            print(f"    {node_name}: {adjustment:+.1f} MW")
    
    # 可视化系统
    print(f"\n📈 生成系统可视化...")
    visualize_system(civilization)
    
    print(f"\n🎯 系统就绪! 时空农耕拓扑学正在运行...")
    print("《阴符经》: '宇宙在乎手，万化生身'")
    print("《地母经》: '知岁宜种，避凶趋吉'")

if __name__ == "__main__":
    main()