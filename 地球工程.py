"""
地球工程无人机舰队 - 增强版模拟系统
包含更真实的物理模型、实时监控和风险评估
注意：这仅用于科学研究和技术验证
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from scipy import integrate, interpolate
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class MissionType(Enum):
    STRATOSPHERIC_AEROSOL = "平流层气溶胶注入"
    MARINE_CLOUD_BRIGHTENING = "海洋云亮化"
    PRECIPITATION_ENHANCEMENT = "人工增雨雪"
    CARBON_CAPTURE = "直接空气碳捕集"

class DroneStatus(Enum):
    IDLE = "待命"
    DEPLOYING = "部署中"
    ACTIVE = "任务中"
    RETURNING = "返航中"
    MAINTENANCE = "维护中"
    CRITICAL = "紧急状态"

@dataclass
class AtmosphericConditions:
    """大气条件数据类"""
    temperature: float  # 温度 °C
    pressure: float     # 压力 hPa
    humidity: float     # 湿度 %
    wind_speed: float   # 风速 m/s
    wind_direction: float  # 风向 degrees
    turbulence: float   # 湍流强度

@dataclass
class Drone:
    """增强版无人机属性"""
    id: str
    position: Tuple[float, float, float]  # 经度, 纬度, 高度(米)
    battery_level: float
    payload_capacity: float
    current_payload: float
    mission_type: Optional[MissionType] = None
    status: DroneStatus = DroneStatus.IDLE
    flight_speed: float = 30.0  # m/s
    max_altitude: float = 25000  # meters
    operational_range: float = 500  # km
    fuel_consumption: float = 0.8  # kg/km
    communication_range: float = 50  # km
    
    # 传感器数据
    sensors: Dict = field(default_factory=lambda: {
        'temperature': 0.0,
        'humidity': 0.0,
        'pressure': 0.0,
        'particle_concentration': 0.0,
        'solar_radiation': 0.0
    })
    
    def update_sensors(self, env_conditions: 'EnvironmentalModel'):
        """更新传感器读数"""
        lat, lon, alt = self.position
        self.sensors['temperature'] = env_conditions.get_temperature(lat, lon, alt)
        self.sensors['humidity'] = env_conditions.get_humidity(lat, lon, alt)
        self.sensors['pressure'] = env_conditions.get_pressure(alt)
        self.sensors['solar_radiation'] = env_conditions.get_solar_radiation(lat, lon)

class EnvironmentalModel:
    """增强版环境模型"""
    
    def __init__(self):
        # 初始化气候数据
        self.temperature_profile = self._create_standard_atmosphere()
        self.humidity_profile = self._create_humidity_profile()
        self.wind_models = {}
        self.solar_radiation_data = {}
        self.aerosol_concentration = np.zeros((180, 360))  # 全球气溶胶浓度网格
        
    def _create_standard_atmosphere(self) -> interpolate.interp1d:
        """创建标准大气温度剖面"""
        altitudes = np.array([0, 1000, 5000, 10000, 15000, 20000, 25000, 30000])
        temperatures = np.array([15, 8.5, -17.5, -50, -56.5, -56.5, -51.5, -46.5])
        return interpolate.interp1d(altitudes, temperatures, fill_value="extrapolate")
    
    def _create_humidity_profile(self) -> interpolate.interp1d:
        """创建湿度剖面"""
        altitudes = np.array([0, 1000, 3000, 6000, 9000, 12000])
        humidity = np.array([60, 50, 30, 15, 5, 2])  # 百分比
        return interpolate.interp1d(altitudes, humidity, fill_value="extrapolate")
    
    def get_temperature(self, lat: float, lon: float, altitude: float) -> float:
        """获取指定位置温度"""
        base_temp = self.temperature_profile(altitude)
        # 添加纬度修正
        lat_effect = -0.6 * abs(lat)  # 极地更冷
        seasonal_effect = 10 * np.sin(2 * np.pi * datetime.now().timetuple().tm_yday / 365)
        return base_temp + lat_effect + seasonal_effect + np.random.normal(0, 2)
    
    def get_humidity(self, lat: float, lon: float, altitude: float) -> float:
        """获取指定位置湿度"""
        base_humidity = float(self.humidity_profile(altitude))
        # 海洋区域湿度更高
        if self._is_ocean(lat, lon):
            base_humidity *= 1.3
        return max(1, min(100, base_humidity + np.random.normal(0, 5)))
    
    def get_pressure(self, altitude: float) -> float:
        """计算大气压力"""
        # 使用压高公式
        return 1013.25 * np.exp(-altitude / 8400)
    
    def get_solar_radiation(self, lat: float, lon: float) -> float:
        """计算太阳辐射"""
        # 简化模型，考虑纬度、季节和时间
        lat_rad = np.radians(lat)
        day_of_year = datetime.now().timetuple().tm_yday
        declination = 23.45 * np.sin(2 * np.pi * (284 + day_of_year) / 365)
        hour_angle = (datetime.now().hour - 12) * 15
        
        cos_zenith = (np.sin(lat_rad) * np.sin(np.radians(declination)) + 
                     np.cos(lat_rad) * np.cos(np.radians(declination)) * np.cos(np.radians(hour_angle)))
        
        solar_constant = 1361  # W/m²
        clear_sky_radiation = solar_constant * max(0, cos_zenith)
        
        # 考虑云量和气溶胶影响
        cloud_reduction = 0.2  # 简化的云量减少
        aerosol_effect = 0.95  # 气溶胶减少
        
        return clear_sky_radiation * (1 - cloud_reduction) * aerosol_effect
    
    def _is_ocean(self, lat: float, lon: float) -> bool:
        """简单判断是否为海洋区域"""
        # 在实际应用中应该使用地理数据库
        return abs(lat) < 60 and (abs(lon) < 30 or abs(lon) > 150)
    
    def update_aerosol_concentration(self, lat: float, lon: float, amount: float, 
                                   particle_size: float, altitude: float):
        """更新气溶胶浓度"""
        lat_idx = int((lat + 90) % 180)
        lon_idx = int((lon + 180) % 360)
        
        # 考虑扩散效应
        diffusion_factor = 1.0 / (particle_size + 0.1)  # 小颗粒扩散更快
        altitude_factor = 1.0 if altitude > 10000 else 0.1  # 平流层停留时间更长
        
        self.aerosol_concentration[lat_idx, lon_idx] += amount * diffusion_factor * altitude_factor

class MissionPlanner:
    """任务规划系统"""
    
    def __init__(self, env_model: EnvironmentalModel):
        self.env_model = env_model
        self.weather_forecast = {}
        
    def optimize_stratospheric_injection(self, target_locations: List[Tuple[float, float]], 
                                       total_sulfate: float) -> Dict:
        """优化平流层气溶胶注入策略"""
        optimized_locations = []
        sulfate_distribution = []
        
        for lat, lon in target_locations:
            # 考虑风场和大气环流模式
            wind_effect = self._calculate_wind_dispersion(lat, lon, 20000)
            optimal_amount = total_sulfate * wind_effect / len(target_locations)
            
            optimized_locations.append((lat, lon))
            sulfate_distribution.append(optimal_amount)
            
        return {
            "optimized_locations": optimized_locations,
            "sulfate_distribution": sulfate_distribution,
            "estimated_efficiency": self._calculate_injection_efficiency(optimized_locations),
            "risk_assessment": self._assess_stratospheric_risk(optimized_locations)
        }
    
    def _calculate_wind_dispersion(self, lat: float, lon: float, altitude: float) -> float:
        """计算风场扩散效应"""
        # 简化的大气环流模型
        if altitude > 10000:  # 平流层
            # 极地涡旋和赤道环流影响
            if abs(lat) > 60:
                return 0.3  # 极地区域扩散较慢
            elif abs(lat) < 30:
                return 1.2  # 赤道区域扩散较快
            else:
                return 0.8
        else:  # 对流层
            return 1.0
    
    def _calculate_injection_efficiency(self, locations: List[Tuple[float, float]]) -> float:
        """计算注入效率"""
        if len(locations) < 2:
            return 0.5
        
        # 基于位置分布计算效率
        latitudes = [loc[0] for loc in locations]
        coverage = (max(latitudes) - min(latitudes)) / 180.0
        return min(1.0, 0.3 + coverage * 0.7)
    
    def _assess_stratospheric_risk(self, locations: List[Tuple[float, float]]) -> Dict:
        """评估平流层注入风险"""
        risk_factors = []
        
        for lat, lon in locations:
            risk_score = 0.0
            
            # 臭氧层风险
            if abs(lat) > 60:
                risk_score += 0.7  # 极地臭氧层脆弱
            
            # 航空交通风险
            if self._is_high_traffic_airway(lat, lon):
                risk_score += 0.5
                
            risk_factors.append(risk_score)
            
        return {
            "overall_risk": max(risk_factors) if risk_factors else 0.0,
            "risk_factors": risk_factors,
            "recommendations": self._generate_risk_recommendations(max(risk_factors))
        }
    
    def _is_high_traffic_airway(self, lat: float, lon: float) -> bool:
        """判断是否为高密度航空路线"""
        # 简化的航空路线判断
        major_routes = [
            (30, -120), (40, -75), (50, 0), (35, 135)  # 示例主要航线
        ]
        
        for route_lat, route_lon in major_routes:
            distance = np.sqrt((lat - route_lat)**2 + (lon - route_lon)**2)
            if distance < 10:  # 10度以内的航线
                return True
        return False
    
    def _generate_risk_recommendations(self, risk_score: float) -> List[str]:
        """生成风险建议"""
        recommendations = []
        
        if risk_score > 0.7:
            recommendations.append("高风险区域 - 需要国际航空协调")
        if risk_score > 0.5:
            recommendations.append("中等风险 - 建议调整投放高度")
        if risk_score > 0.3:
            recommendations.append("低风险 - 标准操作程序适用")
            
        recommendations.append("持续监测臭氧层浓度")
        recommendations.append("实时气象数据验证")
        
        return recommendations

class RealTimeMonitor:
    """实时监控系统"""
    
    def __init__(self):
        self.drone_status_log = []
        self.environmental_impact_log = []
        self.emergency_events = []
        
    def log_drone_status(self, drone: Drone, mission_info: Dict):
        """记录无人机状态"""
        log_entry = {
            'timestamp': datetime.now(),
            'drone_id': drone.id,
            'position': drone.position,
            'battery': drone.battery_level,
            'status': drone.status.value,
            'mission_type': drone.mission_type.value if drone.mission_type else 'None',
            'sensor_data': drone.sensors.copy()
        }
        self.drone_status_log.append(log_entry)
        
    def log_environmental_impact(self, impact_data: Dict):
        """记录环境影响"""
        impact_entry = {
            'timestamp': datetime.now(),
            'temperature_change': impact_data.get('temperature_change', 0),
            'radiation_change': impact_data.get('radiation_change', 0),
            'aerosol_concentration': impact_data.get('aerosol_concentration', 0),
            'area_affected': impact_data.get('area_affected', 0)
        }
        self.environmental_impact_log.append(impact_entry)
        
    def check_emergency_conditions(self, drone: Drone) -> Optional[str]:
        """检查紧急状况"""
        emergencies = []
        
        # 电池电量检查
        if drone.battery_level < 0.1:
            emergencies.append("电池电量严重不足")
            
        # 传感器异常检查
        if drone.sensors['pressure'] < 300:  # hPa
            emergencies.append("压力传感器异常")
            
        # 通信中断模拟
        if np.random.random() < 0.001:  # 0.1%概率通信中断
            emergencies.append("通信信号丢失")
            
        if emergencies:
            emergency_msg = f"无人机 {drone.id} 紧急状况: {', '.join(emergencies)}"
            self.emergency_events.append({
                'timestamp': datetime.now(),
                'drone_id': drone.id,
                'emergency': emergency_msg
            })
            return emergency_msg
            
        return None

class EnhancedGeoEngineeringFleet:
    """增强版地球工程无人机舰队"""
    
    def __init__(self, fleet_size: int = 100):
        self.env_model = EnvironmentalModel()
        self.mission_planner = MissionPlanner(self.env_model)
        self.monitor = RealTimeMonitor()
        self.drones = self.initialize_enhanced_fleet(fleet_size)
        self.mission_log = []
        self.global_impact_data = {
            'temperature_reduction': 0.0,
            'radiation_reduction': 0.0,
            'co2_equivalent_reduced': 0.0
        }
        
    def initialize_enhanced_fleet(self, size: int) -> List[Drone]:
        """初始化增强版无人机舰队"""
        drones = []
        drone_types = [
            {'capacity': 2000, 'range': 800, 'speed': 35},   # 大型无人机
            {'capacity': 1000, 'range': 500, 'speed': 30},   # 中型无人机  
            {'capacity': 500, 'range': 300, 'speed': 25}     # 小型无人机
        ]
        
        for i in range(size):
            drone_type = drone_types[i % len(drone_types)]
            
            # 战略分布：主要在北半球中纬度地区
            if i < size * 0.6:
                lat = np.random.uniform(20, 60)
                lon = np.random.uniform(-180, 180)
            else:
                lat = np.random.uniform(-60, 60)
                lon = np.random.uniform(-180, 180)
                
            altitude = np.random.uniform(0, 1000)
            
            drone = Drone(
                id=f"GED_{i:04d}",
                position=(lon, lat, altitude),
                battery_level=np.random.uniform(0.8, 1.0),
                payload_capacity=drone_type['capacity'],
                current_payload=0,
                flight_speed=drone_type['speed'],
                operational_range=drone_type['range']
            )
            drones.append(drone)
            
            # 初始化传感器读数
            drone.update_sensors(self.env_model)
            
        return drones
    
    def execute_stratospheric_mission(self, target_regions: List[Tuple[float, float]], 
                                    total_sulfate: float, duration_days: int = 30) -> Dict:
        """执行平流层气溶胶注入任务"""
        print(f"开始平流层气溶胶注入任务，持续时间: {duration_days} 天")
        
        # 任务规划优化
        mission_plan = self.mission_planner.optimize_stratospheric_injection(
            target_regions, total_sulfate)
        
        # 选择无人机
        suitable_drones = [d for d in self.drones 
                         if d.status == DroneStatus.IDLE and d.max_altitude >= 20000]
        selected_drones = suitable_drones[:min(20, len(suitable_drones))]
        
        mission_results = {
            'particles_injected': 0.0,
            'area_covered': 0.0,
            'energy_consumed': 0.0,
            'environmental_impact': {},
            'risk_assessment': mission_plan['risk_assessment']
        }
        
        # 模拟任务执行
        for day in range(duration_days):
            daily_results = self._simulate_daily_operations(selected_drones, mission_plan, day)
            mission_results['particles_injected'] += daily_results['particles_injected']
            mission_results['area_covered'] += daily_results['area_covered']
            mission_results['energy_consumed'] += daily_results['energy_consumed']
            
            # 更新环境影响
            self._update_global_impact(daily_results)
            
            print(f"第 {day+1} 天完成: {daily_results['particles_injected']:.2e} 颗粒子")
        
        return mission_results
    
    def _simulate_daily_operations(self, drones: List[Drone], mission_plan: Dict, day: int) -> Dict:
        """模拟日常操作"""
        daily_results = {
            'particles_injected': 0.0,
            'area_covered': 0.0,
            'energy_consumed': 0.0
        }
        
        for drone in drones:
            if drone.status == DroneStatus.IDLE:
                drone.status = DroneStatus.ACTIVE
                drone.mission_type = MissionType.STRATOSPHERIC_AEROSOL
                
                # 计算当日任务量
                sulfate_amount = mission_plan['sulfate_distribution'][0] / len(drones)
                drone.current_payload = sulfate_amount
                
                # 模拟飞行和投放
                flight_distance = np.random.uniform(200, 500)  # km
                energy_consumed = flight_distance * drone.fuel_consumption
                
                # 粒子投放
                particles_injected = drone.current_payload * 1e9  # 转换为粒子数
                daily_results['particles_injected'] += particles_injected
                daily_results['energy_consumed'] += energy_consumed
                daily_results['area_covered'] += 150  # 每架无人机覆盖面积 km²
                
                # 更新环境模型
                lat, lon, alt = drone.position
                self.env_model.update_aerosol_concentration(
                    lat, lon, particles_injected, 0.1, 20000)
                
                # 更新无人机状态
                drone.current_payload = 0
                drone.battery_level -= energy_consumed / 1000  # 简化电池消耗模型
                drone.update_sensors(self.env_model)
                
                # 监控和日志记录
                self.monitor.log_drone_status(drone, mission_plan)
                
                # 紧急状况检查
                emergency = self.monitor.check_emergency_conditions(drone)
                if emergency:
                    print(f"警告: {emergency}")
                    drone.status = DroneStatus.CRITICAL
        
        return daily_results
    
    def _update_global_impact(self, daily_results: Dict):
        """更新全球影响评估"""
        particles = daily_results['particles_injected']
        
        # 基于科学文献的简化影响模型
        temp_reduction = particles * 5e-13  # 温度降低效应
        rad_reduction = particles * 2e-12   # 辐射减少效应
        
        self.global_impact_data['temperature_reduction'] += temp_reduction
        self.global_impact_data['radiation_reduction'] += rad_reduction
        self.global_impact_data['co2_equivalent_reduced'] += particles * 1e-8
        
        # 记录环境影响
        impact_data = {
            'temperature_change': -temp_reduction,
            'radiation_change': -rad_reduction,
            'aerosol_concentration': particles * 1e-10,
            'area_affected': daily_results['area_covered']
        }
        self.monitor.log_environmental_impact(impact_data)
    
    def generate_comprehensive_report(self) -> Dict:
        """生成综合报告"""
        # 无人机状态统计
        status_count = {}
        for status in DroneStatus:
            status_count[status.value] = sum(1 for d in self.drones if d.status == status)
        
        # 任务统计
        mission_count = {}
        for mission in MissionType:
            mission_count[mission.value] = sum(1 for d in self.drones if d.mission_type == mission)
        
        return {
            'timestamp': datetime.now(),
            'fleet_status': {
                'total_drones': len(self.drones),
                'status_distribution': status_count,
                'mission_distribution': mission_count,
                'operational_rate': sum(1 for d in self.drones if d.status in 
                                      [DroneStatus.IDLE, DroneStatus.ACTIVE]) / len(self.drones)
            },
            'environmental_impact': self.global_impact_data.copy(),
            'safety_metrics': {
                'emergency_events': len(self.monitor.emergency_events),
                'recent_emergencies': [e['emergency'] for e in self.monitor.emergency_events[-5:]],
                'average_battery_level': np.mean([d.battery_level for d in self.drones])
            },
            'recommendations': self._generate_operational_recommendations()
        }
    
    def _generate_operational_recommendations(self) -> List[str]:
        """生成操作建议"""
        recommendations = []
        
        # 基于电池状态
        low_battery_count = sum(1 for d in self.drones if d.battery_level < 0.3)
        if low_battery_count > len(self.drones) * 0.1:
            recommendations.append(f"{low_battery_count} 架无人机需要充电")
        
        # 基于紧急事件
        if len(self.monitor.emergency_events) > 10:
            recommendations.append("紧急事件增多，建议检查系统稳定性")
            
        # 基于任务分布
        active_missions = sum(1 for d in self.drones if d.mission_type is not None)
        if active_missions < len(self.drones) * 0.2:
            recommendations.append("无人机利用率较低，建议安排更多任务")
            
        recommendations.append("定期校准传感器")
        recommendations.append("更新气象和空域信息")
        
        return recommendations

def run_enhanced_simulation():
    """运行增强版模拟"""
    print("=== 地球工程无人机舰队 - 增强版模拟系统 ===\n")
    print("注意：此模拟仅用于科学研究和技术验证\n")
    
    # 初始化增强版舰队
    fleet = EnhancedGeoEngineeringFleet(fleet_size=50)
    print(f"增强版舰队初始化完成: {len(fleet.drones)} 架无人机")
    
    # 显示初始状态
    initial_report = fleet.generate_comprehensive_report()
    print(f"\n初始状态报告:")
    print(f"可操作无人机: {initial_report['fleet_status']['operational_rate']:.1%}")
    print(f"平均电池电量: {initial_report['safety_metrics']['average_battery_level']:.1%}")
    
    # 执行平流层气溶胶任务
    print("\n" + "="*50)
    print("开始执行平流层气溶胶注入任务")
    print("="*50)
    
    # 目标区域：主要在北半球中纬度
    target_regions = [
        (35, -120),  # 北美西海岸
        (40, -75),   # 北美东海岸  
        (45, 10),    # 欧洲
        (35, 135),   # 东亚
        (30, 30)     # 北非
    ]
    
    mission_results = fleet.execute_stratospheric_mission(
        target_regions, total_sulfate=5000, duration_days=7)
    
    print(f"\n任务完成总结:")
    print(f"总注入粒子: {mission_results['particles_injected']:.2e}")
    print(f"总覆盖面积: {mission_results['area_covered']:,.0f} km²")
    print(f"总能耗: {mission_results['energy_consumed']:,.0f} kWh")
    
    # 最终报告
    final_report = fleet.generate_comprehensive_report()
    print(f"\n最终综合报告:")
    print(f"预估全球温度降低: {final_report['environmental_impact']['temperature_reduction']*1000:.3f} mK")
    print(f"太阳辐射减少: {final_report['environmental_impact']['radiation_reduction']*100:.3f}%")
    print(f"CO₂当量减少: {final_report['environmental_impact']['co2_equivalent_reduced']:.1f} 吨")
    
    # 安全状况
    print(f"\n安全状况:")
    print(f"紧急事件数量: {final_report['safety_metrics']['emergency_events']}")
    if final_report['safety_metrics']['recent_emergencies']:
        print("最近紧急事件:")
        for event in final_report['safety_metrics']['recent_emergencies']:
            print(f"  - {event}")
    
    return fleet, mission_results, final_report

def create_enhanced_visualization(fleet, mission_results, final_report):
    """创建增强版可视化"""
    fig = plt.figure(figsize=(16, 12))
    
    # 1. 无人机全球分布和状态
    ax1 = plt.subplot(2, 3, 1)
    colors = {'待命': 'green', '任务中': 'blue', '维护中': 'orange', '紧急状态': 'red'}
    
    for drone in fleet.drones:
        color = colors.get(drone.status.value, 'gray')
        ax1.scatter(drone.position[0], drone.position[1], c=color, alpha=0.7, s=50)
    
    ax1.set_title("无人机全球分布和状态", fontsize=14, fontweight='bold')
    ax1.set_xlabel("经度")
    ax1.set_ylabel("纬度")
    ax1.grid(True, alpha=0.3)
    
    # 创建图例
    from matplotlib.lines import Line2D
    legend_elements = [Line2D([0], [0], marker='o', color='w', 
                            markerfacecolor=color, label=status, markersize=8)
                      for status, color in colors.items()]
    ax1.legend(handles=legend_elements, loc='upper right')
    
    # 2. 环境影响随时间变化
    ax2 = plt.subplot(2, 3, 2)
    if fleet.monitor.environmental_impact_log:
        timestamps = [entry['timestamp'] for entry in fleet.monitor.environmental_impact_log]
        temp_changes = [entry['temperature_change'] * 1000 for entry in fleet.monitor.environmental_impact_log]  # 转换为 mK
        
        ax2.plot(timestamps, temp_changes, 'b-', linewidth=2, label='温度变化')
        ax2.set_title("环境影响趋势", fontsize=14, fontweight='bold')
        ax2.set_xlabel("时间")
        ax2.set_ylabel("温度变化 (mK)")
        ax2.legend()
        ax2.grid(True, alpha=0.3)
    
    # 3. 任务类型分布
    ax3 = plt.subplot(2, 3, 3)
    mission_types = [d.mission_type.value if d.mission_type else '无任务' for d in fleet.drones]
    mission_counts = pd.Series(mission_types).value_counts()
    
    colors = plt.cm.Set3(np.linspace(0, 1, len(mission_counts)))
    mission_counts.plot(kind='pie', ax=ax3, colors=colors, autopct='%1.1f%%')
    ax3.set_title("任务类型分布", fontsize=14, fontweight='bold')
    ax3.set_ylabel('')
    
    # 4. 系统性能指标
    ax4 = plt.subplot(2, 3, 4)
    metrics = ['操作率', '电池健康', '任务效率']
    values = [
        final_report['fleet_status']['operational_rate'],
        final_report['safety_metrics']['average_battery_level'],
        mission_results['particles_injected'] / mission_results['energy_consumed'] * 1e6
    ]
    
    bars = ax4.bar(metrics, values, color=['skyblue', 'lightgreen', 'gold'])
    ax4.set_title("系统性能指标", fontsize=14, fontweight='bold')
    ax4.set_ylabel("指标值")
    ax4.grid(True, alpha=0.3, axis='y')
    
    # 在柱状图上添加数值标签
    for bar, value in zip(bars, values):
        height = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2., height,
                f'{value:.1%}' if value <= 1 else f'{value:.1f}',
                ha='center', va='bottom')
    
    # 5. 风险评估
    ax5 = plt.subplot(2, 3, 5)
    risk_categories = ['操作风险', '环境风险', '技术风险', '政治风险']
    risk_scores = [0.3, 0.6, 0.4, 0.7]  # 示例风险评分
    
    colors = ['green' if score < 0.4 else 'orange' if score < 0.7 else 'red' 
             for score in risk_scores]
    
    bars = ax5.bar(risk_categories, risk_scores, color=colors, alpha=0.7)
    ax5.set_title("系统风险评估", fontsize=14, fontweight='bold')
    ax5.set_ylabel("风险评分")
    ax5.set_ylim(0, 1)
    ax5.grid(True, alpha=0.3, axis='y')
    
    # 6. 能源消耗分析
    ax6 = plt.subplot(2, 3, 6)
    energy_sources = ['化石燃料', '太阳能', '风能', '电池']
    energy_usage = [60, 20, 15, 5]  # 百分比
    
    ax6.pie(energy_usage, labels=energy_sources, autopct='%1.1f%%', startangle=90)
    ax6.set_title("能源消耗分析", fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    # 运行增强版模拟
    fleet, mission_results, final_report = run_enhanced_simulation()
    
    # 创建可视化
    create_enhanced_visualization(fleet, mission_results, final_report)
    
    # 输出操作建议
    print(f"\n操作建议:")
    for i, recommendation in enumerate(final_report['recommendations'], 1):
        print(f"{i}. {recommendation}")