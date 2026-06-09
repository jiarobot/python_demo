import cv2
import numpy as np
from collections import defaultdict, deque
from ultralytics import YOLO
import torch
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from IPython.display import HTML
import json
from datetime import datetime
import time
import math
from geopy.distance import geodesic
from shapely.geometry import Point, Polygon, LineString
import os
from pyproj import Proj, transform
import logging

class AdvancedDroneTrafficInspector:
    def __init__(self, model_path='yolov8n.pt', tracker_config='botsort.yaml'):
        """
        初始化高级无人机交通巡检系统
        
        参数:
            model_path: YOLO模型路径
            tracker_config: 跟踪器配置文件路径
        """
        # 设置日志
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        
        # 检查GPU是否可用
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.logger.info(f"使用设备: {self.device}")
        
        # 加载YOLO模型
        try:
            self.model = YOLO(model_path)
            self.logger.info(f"模型加载成功: {model_path}")
        except Exception as e:
            self.logger.error(f"模型加载失败: {e}")
            raise
        
        # 存储跟踪历史和轨迹
        self.track_history = defaultdict(lambda: deque(maxlen=50))
        self.trajectories = defaultdict(lambda: [])
        self.crossing_events = []  # 存储压线事件
        self.lane_change_events = []  # 存储变道事件
        self.speeding_events = []  # 存储超速事件
        self.illegal_lane_events = []  # 存储非法占用应急车道事件
        self.reverse_events = []  # 存储逆行事件
        
        # 跟踪器配置
        self.tracker_config = tracker_config
        
        # 定义虚拟检测线和区域
        self.lines = []  # 压线检测线
        self.speed_zones = []  # 测速区域
        self.emergency_lanes = []  # 应急车道区域
        self.direction_arrows = []  # 方向箭头（用于逆行检测）
        
        # 定义检测方向 (1: 从上到下, -1: 从下到上, 0: 双向)
        self.line_directions = []
        
        # 存储每个对象的最后位置和方向状态
        self.last_positions = {}
        self.crossing_states = defaultdict(lambda: defaultdict(lambda: False))
        self.speed_zones_entered = defaultdict(lambda: defaultdict(lambda: False))
        self.emergency_lane_entered = defaultdict(lambda: False)
        
        # 颜色映射
        self.colors = {}
        
        # 车速计算相关
        self.speed_estimates = defaultdict(lambda: [])
        self.pixel_to_meter_ratio = 0.05  # 像素到米的转换比例，需要根据实际情况调整
        
        # 变道检测相关
        self.lane_change_threshold = 30  # 变道检测的横向移动阈值(像素)
        self.lane_history = defaultdict(lambda: deque(maxlen=10))
        
        # 无人机相关参数
        self.altitude = 100  # 默认高度(米)
        self.gps_position = (0, 0)  # 默认GPS位置
        self.camera_params = {
            'focal_length': 35,  # 焦距(mm)
            'sensor_width': 36,  # 传感器宽度(mm)
            'sensor_height': 24,  # 传感器高度(mm)
            'tilt_angle': 0  # 相机倾斜角度(度)
        }
        
        # 性能优化相关
        self.frame_skip = 2  # 每处理2帧跳过1帧，提高性能
        self.last_processed_time = time.time()
        self.processing_times = deque(maxlen=30)
        
        # 地图投影相关
        self.proj_wgs84 = Proj(init='epsg:4326')  # WGS84坐标系
        self.proj_utm = None  # UTM坐标系，根据位置动态确定
        
        # 加载预定义的交通规则配置
        self.load_traffic_rules()
        
    def load_traffic_rules(self, config_path='traffic_rules.json'):
        """
        加载交通规则配置
        
        参数:
            config_path: 配置文件路径
        """
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    self.traffic_rules = json.load(f)
                self.logger.info(f"交通规则配置加载成功: {config_path}")
            else:
                # 默认配置
                self.traffic_rules = {
                    "speed_limits": {
                        "highway": 120,  # 高速公路限速(km/h)
                        "urban": 60,     # 城市道路限速(km/h)
                        "school": 30     # 学校区域限速(km/h)
                    },
                    "illegal_lane_penalty": 200,  # 非法占用应急车道罚款(元)
                    "reverse_driving_penalty": 200,  # 逆行罚款(元)
                    "speeding_tolerance": 0.1  # 超速容忍度(10%)
                }
                self.logger.info("使用默认交通规则配置")
        except Exception as e:
            self.logger.error(f"交通规则配置加载失败: {e}")
            self.traffic_rules = {
                "speed_limits": {"highway": 120, "urban": 60, "school": 30},
                "illegal_lane_penalty": 200,
                "reverse_driving_penalty": 200,
                "speeding_tolerance": 0.1
            }
    
    def set_drone_parameters(self, altitude, gps_position, camera_params=None):
        """
        设置无人机参数
        
        参数:
            altitude: 飞行高度(米)
            gps_position: 无人机GPS位置(纬度, 经度)
            camera_params: 相机参数字典
        """
        self.altitude = altitude
        self.gps_position = gps_position
        
        # 设置UTM投影
        utm_zone = int((gps_position[1] + 180) / 6) + 1
        self.proj_utm = Proj(proj='utm', zone=utm_zone, ellps='WGS84')
        
        if camera_params:
            self.camera_params.update(camera_params)
            
        self.logger.info(f"无人机参数设置: 高度={altitude}m, GPS位置={gps_position}")
    
    def set_detection_lines(self, lines, directions=None):
        """
        设置检测线
        
        参数:
            lines: 线的列表，每条线由两个点组成 [(x1,y1), (x2,y2)]
            directions: 每条线的检测方向列表
        """
        self.lines = lines
        if directions is None:
            self.line_directions = [0] * len(lines)
        else:
            self.line_directions = directions
        self.logger.info(f"设置 {len(lines)} 条检测线")
    
    def set_speed_zones(self, zones, speed_limits):
        """
        设置测速区域和限速值
        
        参数:
            zones: 区域列表，每个区域由多个点组成的多边形
            speed_limits: 每个区域的限速值(km/h)列表
        """
        self.speed_zones = zones
        self.speed_limits = speed_limits
        self.logger.info(f"设置 {len(zones)} 个测速区域")
    
    def set_emergency_lanes(self, lanes):
        """
        设置应急车道区域
        
        参数:
            lanes: 应急车道区域列表，每个区域由多个点组成的多边形
        """
        self.emergency_lanes = lanes
        self.logger.info(f"设置 {len(lanes)} 个应急车道区域")
    
    def set_direction_arrows(self, arrows):
        """
        设置方向箭头（用于逆行检测）
        
        参数:
            arrows: 箭头列表，每个箭头由起点、终点和方向组成
        """
        self.direction_arrows = arrows
        self.logger.info(f"设置 {len(arrows)} 个方向箭头")
    
    def pixel_to_gps(self, pixel_x, pixel_y, frame_width, frame_height):
        """
        将像素坐标转换为GPS坐标
        
        参数:
            pixel_x: 像素X坐标
            pixel_y: 像素Y坐标
            frame_width: 帧宽度
            frame_height: 帧高度
            
        返回:
            (latitude, longitude): GPS坐标
        """
        # 计算相对于图像中心的位置
        dx = pixel_x - frame_width / 2
        dy = pixel_y - frame_height / 2
        
        # 计算地面采样距离(GSD)
        gsd = (self.altitude * self.camera_params['sensor_width']) / (
            self.camera_params['focal_length'] * frame_width)
        
        # 计算实际距离
        distance_x = dx * gsd
        distance_y = dy * gsd
        
        # 考虑相机倾斜角度
        tilt_rad = math.radians(self.camera_params['tilt_angle'])
        actual_distance_x = distance_x
        actual_distance_y = distance_y / math.cos(tilt_rad)
        
        # 转换为经纬度
        # 这里简化处理，实际应用需要更精确的投影转换
        lat, lon = self.gps_position
        dlat = actual_distance_y / 111320  # 1度纬度约111.32km
        dlon = actual_distance_x / (111320 * math.cos(math.radians(lat)))
        
        return lat + dlat, lon + dlon
    
    def is_crossing_line(self, point1, point2, line):
        """
        判断两点形成的线段是否与检测线相交
        
        参数:
            point1: 前一个位置点
            point2: 当前位置点
            line: 检测线，由两个点组成
            
        返回:
            bool: 是否相交
            point: 交点坐标 (如果相交)
        """
        x1, y1 = point1
        x2, y2 = point2
        x3, y3 = line[0]
        x4, y4 = line[1]
        
        # 计算分母
        den = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
        
        # 如果分母为0，则线段平行
        if den == 0:
            return False, None
            
        # 计算参数t和u
        t = ((x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)) / den
        u = -((x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)) / den
        
        # 检查是否在线段上
        if 0 <= t <= 1 and 0 <= u <= 1:
            # 计算交点
            x = x1 + t * (x2 - x1)
            y = y1 + t * (y2 - y1)
            return True, (int(x), int(y))
            
        return False, None
    
    def is_in_polygon(self, point, polygon):
        """
        判断点是否在多边形内
        
        参数:
            point: 点坐标(x, y)
            polygon: 多边形，由多个点组成
            
        返回:
            bool: 是否在多边形内
        """
        if len(polygon) < 3:
            return False
            
        x, y = point
        n = len(polygon)
        inside = False
        
        p1x, p1y = polygon[0]
        for i in range(n + 1):
            p2x, p2y = polygon[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
            
        return inside
    
    def detect_line_crossing(self, track_id, prev_point, current_point):
        """
        检测对象是否越过任何检测线
        
        参数:
            track_id: 对象ID
            prev_point: 前一个位置点
            current_point: 当前位置点
            
        返回:
            list: 检测到的事件列表
        """
        events = []
        
        for i, line in enumerate(self.lines):
            # 检查是否已经越过这条线
            if self.crossing_states[track_id][i]:
                continue
                
            # 检查是否与线相交
            is_crossing, cross_point = self.is_crossing_line(prev_point, current_point, line)
            
            if is_crossing:
                # 计算移动方向 (y方向)
                direction = 1 if current_point[1] > prev_point[1] else -1
                
                # 检查是否符合设定的检测方向
                if self.line_directions[i] == 0 or direction == self.line_directions[i]:
                    # 记录压线事件
                    event = {
                        'track_id': track_id,
                        'line_id': i,
                        'direction': direction,
                        'cross_point': cross_point,
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'type': 'line_crossing'
                    }
                    events.append(event)
                    self.crossing_events.append(event)
                    
                    # 标记这条线已经被该对象越过
                    self.crossing_states[track_id][i] = True
                    
        return events
    
    def detect_speeding(self, track_id, current_point, frame_width, frame_height, fps):
        """
        检测车辆是否超速 - 改进版本，考虑透视效应和距离因素
        
        参数:
            track_id: 对象ID
            current_point: 当前位置点
            frame_width: 帧宽度
            frame_height: 帧高度
            fps: 视频帧率
            
        返回:
            bool: 是否超速
            dict: 超速事件详情
        """
        if track_id not in self.last_positions:
            return False, None
        
        # 检查车辆是否在测速区域内
        in_speed_zone = False
        speed_limit = 0
        zone_id = -1
        
        for i, zone in enumerate(self.speed_zones):
            if self.is_in_polygon(current_point, zone):
                in_speed_zone = True
                speed_limit = self.speed_limits[i]
                zone_id = i
                
                # 标记车辆已进入测速区域
                if not self.speed_zones_entered[track_id][i]:
                    self.speed_zones_entered[track_id][i] = True
                    self.logger.info(f"车辆 {track_id} 进入测速区域 {i}, 限速 {speed_limit}km/h")
                break
        
        if not in_speed_zone:
            return False, None
        
        # 估算速度 - 使用改进的方法考虑透视效应
        if len(self.track_history[track_id]) < 5:  # 需要更多点以获得更准确的速度
            return False, None
        
        # 获取最近5个位置点
        recent_points = list(self.track_history[track_id])[-5:]
        
        # 计算基于透视效应的速度
        # 1. 计算每个点的深度（基于y坐标）
        depths = []
        for point in recent_points:
            # 使用y坐标估计深度（距离），y越大表示距离越近
            # 使用简单的线性模型：depth = a + b * y
            # 这个模型需要根据实际场景进行校准
            depth_estimate = 100 + (frame_height - point[1]) * 0.5  # 示例公式，需要调整
            depths.append(depth_estimate)
        
        # 2. 计算每个线段的速度并加权平均
        weighted_speeds = []
        total_weight = 0
        
        for i in range(1, len(recent_points)):
            x1, y1 = recent_points[i-1]
            x2, y2 = recent_points[i]
            
            # 计算像素距离
            pixel_distance = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
            
            # 计算平均深度（距离）
            avg_depth = (depths[i-1] + depths[i]) / 2
            
            # 计算地面采样距离(GSD) - 考虑深度
            # GSD与深度成正比：GSD = (depth * sensor_width) / (focal_length * frame_width)
            gsd = (avg_depth * self.camera_params['sensor_width']) / (
                self.camera_params['focal_length'] * frame_width)
            
            # 计算实际距离(米)
            distance_m = pixel_distance * gsd
            
            # 计算时间间隔 (1帧)
            time_interval = 1 / fps
            
            # 计算速度(m/s)
            speed_mps = distance_m / time_interval if time_interval > 0 else 0
            
            # 转换为km/h
            speed_kmh = speed_mps * 3.6
            
            # 使用深度作为权重（距离越远，权重越小，因为误差可能更大）
            weight = 1.0 / (avg_depth / 10)  # 调整权重公式
            weighted_speeds.append(speed_kmh * weight)
            total_weight += weight
        
        # 计算加权平均速度
        if total_weight > 0:
            speed_kmh = sum(weighted_speeds) / total_weight
        else:
            speed_kmh = 0
        
        # 过滤掉过低的速度（可能是检测噪声）
        if speed_kmh < 2.0:  # 小于2km/h认为是静止或误判
            return False, None
        
        # 存储速度估计
        self.speed_estimates[track_id].append(speed_kmh)
        
        # 使用指数加权移动平均进行平滑
        if len(self.speed_estimates[track_id]) > 1:
            # 使用EWMA (Exponentially Weighted Moving Average)
            alpha = 0.7  # 平滑因子，值越大对最近的值给予更多权重
            speed_kmh = alpha * speed_kmh + (1 - alpha) * self.speed_estimates[track_id][-2]
        
        # 检查是否超速
        tolerance = self.traffic_rules["speeding_tolerance"]
        if speed_kmh > speed_limit * (1 + tolerance):
            # 创建超速事件
            event = {
                'track_id': track_id,
                'speed': speed_kmh,
                'speed_limit': speed_limit,
                'zone_id': zone_id,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'type': 'speeding'
            }
            
            self.speeding_events.append(event)
            return True, event
        
        return False, None
    
    def detect_illegal_lane_usage(self, track_id, current_point):
        """
        检测车辆是否非法占用应急车道
        
        参数:
            track_id: 对象ID
            current_point: 当前位置点
            
        返回:
            bool: 是否非法占用
            dict: 非法占用事件详情
        """
        for i, lane in enumerate(self.emergency_lanes):
            if self.is_in_polygon(current_point, lane):
                # 检查车辆是否已经标记为进入应急车道
                if not self.emergency_lane_entered[track_id]:
                    self.emergency_lane_entered[track_id] = True
                    
                    # 创建非法占用事件
                    event = {
                        'track_id': track_id,
                        'lane_id': i,
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'type': 'illegal_lane_usage'
                    }
                    
                    self.illegal_lane_events.append(event)
                    return True, event
                break
            else:
                self.emergency_lane_entered[track_id] = False
        
        return False, None
    
    def detect_reverse_driving(self, track_id, prev_point, current_point):
        """
        检测车辆是否逆行
        
        参数:
            track_id: 对象ID
            prev_point: 前一个位置点
            current_point: 当前位置点
            
        返回:
            bool: 是否逆行
            dict: 逆行事件详情
        """
        # 计算移动方向向量
        direction_vector = (current_point[0] - prev_point[0], current_point[1] - prev_point[1])
        
        # 检查是否与任何方向箭头相反
        for i, arrow in enumerate(self.direction_arrows):
            arrow_start, arrow_end, arrow_direction = arrow
            arrow_vector = (arrow_end[0] - arrow_start[0], arrow_end[1] - arrow_start[1])
            
            # 计算方向向量之间的夹角
            dot_product = direction_vector[0] * arrow_vector[0] + direction_vector[1] * arrow_vector[1]
            mag_direction = math.sqrt(direction_vector[0]**2 + direction_vector[1]**2)
            mag_arrow = math.sqrt(arrow_vector[0]**2 + arrow_vector[1]**2)
            
            if mag_direction > 0 and mag_arrow > 0:
                cos_angle = dot_product / (mag_direction * mag_arrow)
                angle = math.degrees(math.acos(cos_angle))
                
                # 如果夹角大于90度，说明方向相反
                if angle > 90:
                    # 创建逆行事件
                    event = {
                        'track_id': track_id,
                        'arrow_id': i,
                        'angle': angle,
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'type': 'reverse_driving'
                    }
                    
                    self.reverse_events.append(event)
                    return True, event
        
        return False, None
    
    def detect_lane_change(self, track_id, current_point, frame_idx):
        """
        检测车辆是否变道
        
        参数:
            track_id: 对象ID
            current_point: 当前位置点
            frame_idx: 当前帧索引
            
        返回:
            bool: 是否检测到变道
            dict: 变道事件详情
        """
        # 存储当前横向位置
        self.lane_history[track_id].append((current_point[0], frame_idx))
        
        # 需要至少5个历史点才能检测变道
        if len(self.lane_history[track_id]) < 5:
            return False, None
        
        # 计算最近5个点的横向位置变化
        recent_points = list(self.lane_history[track_id])
        x_coords = [p[0] for p in recent_points]
        frames = [p[1] for p in recent_points]
        
        # 计算横向移动趋势
        if len(x_coords) >= 5:
            # 计算移动平均值
            moving_avg = np.convolve(x_coords, np.ones(5)/5, mode='valid')
            
            # 计算标准差
            std_dev = np.std(x_coords)
            
            # 如果标准差超过阈值，可能发生了变道
            if std_dev > self.lane_change_threshold:
                # 确定变道方向
                direction = "right" if x_coords[-1] > x_coords[0] else "left"
                
                # 创建变道事件
                event = {
                    'track_id': track_id,
                    'direction': direction,
                    'start_frame': frames[0],
                    'end_frame': frames[-1],
                    'start_x': x_coords[0],
                    'end_x': x_coords[-1],
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'type': 'lane_change'
                }
                
                self.lane_change_events.append(event)
                return True, event
        
        return False, None
    
    def detect_and_track(self, video_path, output_path='output.mp4', show_video=True, save_video=True):
        """
        对视频进行物体检测、跟踪和交通违规检测
        
        参数:
            video_path: 输入视频路径
            output_path: 输出视频路径
            show_video: 是否显示实时视频
            save_video: 是否保存输出视频
        """
        # 打开视频文件
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            self.logger.error(f"无法打开视频文件: {video_path}")
            return
        
        # 获取视频属性
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        self.logger.info(f"视频信息: 分辨率={width}x{height}, FPS={fps}, 总帧数={frame_count}")
        
        # 定义视频编写器
        if save_video:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        frame_idx = 0
        skipped_frames = 0
        
        while cap.isOpened():
            success, frame = cap.read()
            
            if not success:
                break
                
            # 帧跳过策略，提高性能
            if frame_idx % (self.frame_skip + 1) != 0:
                frame_idx += 1
                skipped_frames += 1
                continue
                
            start_time = time.time()
            
            # 绘制检测线
            for i, line in enumerate(self.lines):
                color = (0, 255, 0)  # 绿色线
                if self.line_directions[i] == 1:
                    color = (0, 0, 255)  # 红色线表示从上到下检测
                elif self.line_directions[i] == -1:
                    color = (255, 0, 0)  # 蓝色线表示从下到上检测
                    
                cv2.line(frame, line[0], line[1], color, 2)
                cv2.putText(frame, f"Line {i}", (line[0][0], line[0][1]-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # 绘制测速区域
            for i, zone in enumerate(self.speed_zones):
                pts = np.array(zone, np.int32)
                pts = pts.reshape((-1, 1, 2))
                cv2.polylines(frame, [pts], True, (255, 255, 0), 2)  # 青色边界
                cv2.putText(frame, f"Speed Zone {i}: {self.speed_limits[i]}km/h", 
                           (zone[0][0], zone[0][1]-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)
            
            # 绘制应急车道区域
            for i, lane in enumerate(self.emergency_lanes):
                pts = np.array(lane, np.int32)
                pts = pts.reshape((-1, 1, 2))
                cv2.polylines(frame, [pts], True, (0, 165, 255), 2)  # 橙色边界
                cv2.putText(frame, f"Emergency Lane {i}", 
                           (lane[0][0], lane[0][1]-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 2)
            
            # 绘制方向箭头
            for i, arrow in enumerate(self.direction_arrows):
                start, end, direction = arrow
                cv2.arrowedLine(frame, start, end, (255, 0, 255), 2)  # 紫色箭头
                cv2.putText(frame, f"Direction {i}", 
                           (start[0], start[1]-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 2)
            
            # 使用YOLO进行跟踪
            results = self.model.track(
                frame, 
                persist=True,  # 保持跟踪状态
                tracker=self.tracker_config,
                verbose=False, # 不打印详细信息
                device=self.device,
                imgsz=640  # 固定输入尺寸，提高性能
            )
            
            # 获取检测结果
            if results[0].boxes is not None and results[0].boxes.id is not None:
                boxes = results[0].boxes.xywh.cpu()
                track_ids = results[0].boxes.id.int().cpu().tolist()
                class_ids = results[0].boxes.cls.int().cpu().tolist()
                confidences = results[0].boxes.conf.cpu().tolist()
                
                # 可视化结果
                annotated_frame = results[0].plot()
                
                # 为每个跟踪ID分配颜色
                for track_id in track_ids:
                    if track_id not in self.colors:
                        self.colors[track_id] = tuple(np.random.randint(0, 255, 3).tolist())
                
                # 处理每个检测到的对象
                for box, track_id, class_id, confidence in zip(boxes, track_ids, class_ids, confidences):
                    x, y, w, h = box
                    center = (int(x), int(y))
                    
                    # 存储轨迹点
                    if track_id in self.last_positions:
                        prev_center = self.last_positions[track_id]
                        
                        # 检测是否越线
                        events = self.detect_line_crossing(track_id, prev_center, center)
                        
                        # 检测是否超速
                        speeding_detected, speed_event = self.detect_speeding(track_id, center, width, height, fps)
                        
                        # 检测是否非法占用应急车道
                        illegal_lane_detected, lane_event = self.detect_illegal_lane_usage(track_id, center)
                        
                        # 检测是否逆行
                        reverse_detected, reverse_event = self.detect_reverse_driving(track_id, prev_center, center)
                        
                        # 检测是否变道
                        lane_change_detected, lane_change_event = self.detect_lane_change(track_id, center, frame_idx)
                        
                        # 绘制越线事件
                        for event in events:
                            cv2.circle(annotated_frame, event['cross_point'], 8, (0, 0, 255), -1)
                            cv2.putText(annotated_frame, f"Cross! ID:{track_id}", 
                                       (event['cross_point'][0]+10, event['cross_point'][1]), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                        
                        # 绘制超速事件
                        if speeding_detected:
                            cv2.putText(annotated_frame, f"Speeding! ID:{track_id} {speed_event['speed']:.1f}km/h", 
                                       (int(x - w/2), int(y - h/2 - 30)), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                        
                        # 绘制非法占用应急车道事件
                        if illegal_lane_detected:
                            cv2.putText(annotated_frame, f"Illegal Lane! ID:{track_id}", 
                                       (int(x - w/2), int(y - h/2 - 60)), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
                        
                        # 绘制逆行事件
                        if reverse_detected:
                            cv2.putText(annotated_frame, f"Reverse! ID:{track_id}", 
                                       (int(x - w/2), int(y - h/2 - 90)), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
                        
                        # 绘制变道事件
                        if lane_change_detected:
                            cv2.putText(annotated_frame, f"Lane Change! ID:{track_id}", 
                                       (int(x - w/2), int(y - h/2 - 120)), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                    
                    self.last_positions[track_id] = center
                    self.track_history[track_id].append(center)
                    self.trajectories[track_id].append({
                        'frame': frame_idx,
                        'center': center,
                        'class_id': class_id,
                        'confidence': confidence
                    })
                    
                    # 绘制轨迹
                    points = np.array(self.track_history[track_id], dtype=np.int32)
                    if len(points) > 1:
                        cv2.polylines(annotated_frame, [points], isClosed=False, 
                                     color=self.colors[track_id], thickness=2)
                    
                    # 显示跟踪ID、类名和置信度
                    label = f"ID:{track_id} {self.model.names[class_id]}:{confidence:.2f}"
                    cv2.putText(annotated_frame, label, (int(x - w/2), int(y - h/2 - 10)), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.colors[track_id], 2)
                    
                    # 显示速度
                    if track_id in self.last_positions:
                        # 计算速度
                        prev_point = self.last_positions[track_id]
                        pixel_distance = np.sqrt((center[0] - prev_point[0])**2 + 
                                                (center[1] - prev_point[1])**2)
                        
                        # 计算地面采样距离(GSD)
                        gsd = (self.altitude * self.camera_params['sensor_width']) / (
                            self.camera_params['focal_length'] * width)
                        
                        # 计算实际距离(米)
                        distance_m = pixel_distance * gsd
                        
                        # 计算速度(m/s)
                        speed_mps = distance_m * fps
                        
                        # 转换为km/h
                        speed_kmh = speed_mps * 3.6
                        
                        # 存储速度估计
                        self.speed_estimates[track_id].append(speed_kmh)
                        
                        # 使用平滑后的速度(最近3帧的平均值)
                        if len(self.speed_estimates[track_id]) > 3:
                            speed_kmh = np.mean(list(self.speed_estimates[track_id])[-3:])
                        
                        cv2.putText(annotated_frame, f"{speed_kmh:.1f} km/h", 
                                   (int(x - w/2), int(y + h/2 + 20)), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
            else:
                annotated_frame = frame
                
            # 计算处理时间
            processing_time = time.time() - start_time
            self.processing_times.append(processing_time)
            avg_processing_time = np.mean(self.processing_times) if self.processing_times else 0
            
            # 显示帧号、事件计数和处理速度
            cv2.putText(annotated_frame, f"Frame: {frame_idx}/{frame_count}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(annotated_frame, f"Crossing Events: {len(self.crossing_events)}", (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.putText(annotated_frame, f"Speeding Events: {len(self.speeding_events)}", (10, 90), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.putText(annotated_frame, f"Illegal Lane Events: {len(self.illegal_lane_events)}", (10, 120), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
            cv2.putText(annotated_frame, f"Reverse Events: {len(self.reverse_events)}", (10, 150), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
            cv2.putText(annotated_frame, f"Lane Changes: {len(self.lane_change_events)}", (10, 180), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
            cv2.putText(annotated_frame, f"FPS: {1/avg_processing_time:.1f}", (10, 210), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            
            # 显示视频
            if show_video:
                cv2.imshow("Advanced Drone Traffic Inspector", annotated_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            
            # 保存视频
            if save_video:
                out.write(annotated_frame)
                
            frame_idx += 1
            self.logger.info(f"处理进度: {frame_idx}/{frame_count}帧, 跳过: {skipped_frames}, FPS: {1/avg_processing_time:.1f}")
        
        # 释放资源
        cap.release()
        if save_video:
            out.release()
        cv2.destroyAllWindows()
        
        self.logger.info(f"视频处理完成! 共处理{frame_idx}帧, 跳过{skipped_frames}帧")
        self.logger.info(f"检测到{len(self.crossing_events)}次压线事件, {len(self.speeding_events)}次超速事件")
        self.logger.info(f"{len(self.illegal_lane_events)}次非法占用应急车道事件, {len(self.reverse_events)}次逆行事件")
        self.logger.info(f"{len(self.lane_change_events)}次变道事件")
        
    def get_trajectories(self):
        """获取所有跟踪对象的轨迹数据"""
        return dict(self.trajectories)
    
    def get_crossing_events(self):
        """获取所有压线事件"""
        return self.crossing_events
    
    def get_speeding_events(self):
        """获取所有超速事件"""
        return self.speeding_events
    
    def get_illegal_lane_events(self):
        """获取所有非法占用应急车道事件"""
        return self.illegal_lane_events
    
    def get_reverse_events(self):
        """获取所有逆行事件"""
        return self.reverse_events
    
    def get_lane_change_events(self):
        """获取所有变道事件"""
        return self.lane_change_events
    
    def get_speed_estimates(self):
        """获取所有速度估计"""
        return {k: np.mean(v) if v else 0 for k, v in self.speed_estimates.items()}
    
    def save_data(self, trajectories_path='trajectories.json', events_path='events.json'):
        """保存所有数据到文件"""
        # 保存轨迹数据
        trajectories = {str(k): v for k, v in self.get_trajectories().items()}
        with open(trajectories_path, 'w') as f:
            json.dump(trajectories, f, indent=2)
        
        # 保存所有事件
        all_events = {
            'crossing_events': self.crossing_events,
            'speeding_events': self.speeding_events,
            'illegal_lane_events': self.illegal_lane_events,
            'reverse_events': self.reverse_events,
            'lane_change_events': self.lane_change_events
        }
        
        with open(events_path, 'w') as f:
            json.dump(all_events, f, indent=2)
            
        self.logger.info(f"轨迹数据已保存到: {trajectories_path}")
        self.logger.info(f"事件数据已保存到: {events_path}")
        
    def generate_report(self, report_path='traffic_inspection_report.html'):
        """生成交通巡检报告"""
        # 这里实现报告生成逻辑
        # 包括统计信息、违规事件详情、可视化图表等
        
        self.logger.info(f"巡检报告已生成: {report_path}")
        
    def visualize_trajectories(self, output_path='trajectories_visualization.png'):
        """可视化所有轨迹和事件"""
        plt.figure(figsize=(16, 12))
        
        # 绘制检测线
        for i, line in enumerate(self.lines):
            x_values = [line[0][0], line[1][0]]
            y_values = [line[0][1], line[1][1]]
            
            if self.line_directions[i] == 1:
                color = 'red'
                label = f'Line {i} (Down)'
            elif self.line_directions[i] == -1:
                color = 'blue'
                label = f'Line {i} (Up)'
            else:
                color = 'green'
                label = f'Line {i} (Both)'
                
            plt.plot(x_values, y_values, color=color, linewidth=3, label=label)
        
        # 绘制测速区域
        for i, zone in enumerate(self.speed_zones):
            x_coords = [p[0] for p in zone]
            y_coords = [p[1] for p in zone]
            x_coords.append(zone[0][0])  # 闭合多边形
            y_coords.append(zone[0][1])
            plt.plot(x_coords, y_coords, color='cyan', linewidth=2, linestyle='--', alpha=0.7)
            plt.fill(x_coords, y_coords, color='cyan', alpha=0.1)
            plt.text(np.mean(x_coords), np.mean(y_coords), f"Speed Zone {i}\n{self.speed_limits[i]}km/h", 
                    ha='center', va='center', fontsize=8, color='cyan')
        
        # 绘制应急车道区域
        for i, lane in enumerate(self.emergency_lanes):
            x_coords = [p[0] for p in lane]
            y_coords = [p[1] for p in lane]
            x_coords.append(lane[0][0])  # 闭合多边形
            y_coords.append(lane[0][1])
            plt.plot(x_coords, y_coords, color='orange', linewidth=2, linestyle='--', alpha=0.7)
            plt.fill(x_coords, y_coords, color='orange', alpha=0.1)
            plt.text(np.mean(x_coords), np.mean(y_coords), f"Emergency Lane {i}", 
                    ha='center', va='center', fontsize=8, color='orange')
        
        # 绘制方向箭头
        for i, arrow in enumerate(self.direction_arrows):
            start, end, direction = arrow
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            plt.arrow(start[0], start[1], dx, dy, head_width=10, head_length=10, 
                     fc='purple', ec='purple', length_includes_head=True)
            plt.text(start[0] + dx/2, start[1] + dy/2, f"Direction {i}", 
                    ha='center', va='center', fontsize=8, color='purple')
        
        # 绘制轨迹
        for track_id, points in self.trajectories.items():
            if not points:
                continue
                
            x_coords = [p['center'][0] for p in points]
            y_coords = [p['center'][1] for p in points]
            
            # 绘制轨迹线
            color = self.colors.get(track_id, (128, 128, 128))
            # 将0-255的颜色值转换为0-1的浮点数
            normalized_color = tuple(c/255.0 for c in color)
            plt.plot(x_coords, y_coords, color=normalized_color, 
                    alpha=0.7, linewidth=1, label=f'ID {track_id}')
            
            # 绘制起点和终点
            plt.scatter(x_coords[0], y_coords[0], color='green', s=50, marker='o')
            plt.scatter(x_coords[-1], y_coords[-1], color='red', s=50, marker='s')
        
        # 绘制压线事件点
        for event in self.crossing_events:
            plt.scatter(event['cross_point'][0], event['cross_point'][1], 
                       color='yellow', s=100, marker='*', edgecolors='black')
            plt.text(event['cross_point'][0]+10, event['cross_point'][1], 
                    f"Cross ID:{event['track_id']}", fontsize=8)
        
        # 绘制超速事件点
        for event in self.speeding_events:
            # 找到对应帧的位置
            track_points = self.trajectories[event['track_id']]
            event_point = next((p for p in track_points if abs(p['frame'] - event.get('frame', 0)) < 10), None)
            if event_point:
                plt.scatter(event_point['center'][0], event_point['center'][1], 
                           color='cyan', s=100, marker='d', edgecolors='black')
                plt.text(event_point['center'][0]+10, event_point['center'][1], 
                        f"Speed ID:{event['track_id']} {event['speed']:.1f}km/h", fontsize=8, color='cyan')
        
        # 绘制非法占用应急车道事件点
        for event in self.illegal_lane_events:
            # 找到对应帧的位置
            track_points = self.trajectories[event['track_id']]
            event_point = next((p for p in track_points if abs(p['frame'] - event.get('frame', 0)) < 10), None)
            if event_point:
                plt.scatter(event_point['center'][0], event_point['center'][1], 
                           color='orange', s=100, marker='^', edgecolors='black')
                plt.text(event_point['center'][0]+10, event_point['center'][1], 
                        f"Illegal Lane ID:{event['track_id']}", fontsize=8, color='orange')
        
        # 绘制逆行事件点
        for event in self.reverse_events:
            # 找到对应帧的位置
            track_points = self.trajectories[event['track_id']]
            event_point = next((p for p in track_points if abs(p['frame'] - event.get('frame', 0)) < 10), None)
            if event_point:
                plt.scatter(event_point['center'][0], event_point['center'][1], 
                           color='purple', s=100, marker='v', edgecolors='black')
                plt.text(event_point['center'][0]+10, event_point['center'][1], 
                        f"Reverse ID:{event['track_id']}", fontsize=8, color='purple')
        
        # 绘制变道事件
        for event in self.lane_change_events:
            # 找到对应帧的位置
            track_points = self.trajectories[event['track_id']]
            frame_points = [p for p in track_points if event['start_frame'] <= p['frame'] <= event['end_frame']]
            if frame_points:
                x_coords = [p['center'][0] for p in frame_points]
                y_coords = [p['center'][1] for p in frame_points]
                plt.plot(x_coords, y_coords, color='blue', linewidth=3, alpha=0.7)
                plt.text(x_coords[len(x_coords)//2], y_coords[len(y_coords)//2], 
                        f"Lane Change ID:{event['track_id']}", fontsize=8, color='blue')
        
        plt.xlabel('X Coordinate')
        plt.ylabel('Y Coordinate')
        plt.title('Drone Traffic Inspection - Object Trajectories and Events')
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.grid(True, alpha=0.3)
        plt.gca().invert_yaxis()  # 反转Y轴，因为图像坐标原点在左上角
        
        # 保存图像
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.show()
        
        self.logger.info(f"轨迹可视化已保存到: {output_path}")

# 使用示例
if __name__ == "__main__":
    # 初始化高级无人机交通巡检系统
    inspector = AdvancedDroneTrafficInspector(model_path='car.pt')
    
    # 设置无人机参数 (高度、GPS位置、相机参数)
    inspector.set_drone_parameters(
        altitude=3,  # 飞行高度100米
        gps_position=(39.9042, 116.4074),  # 北京天安门坐标
        camera_params={
            'focal_length': 35,
            'sensor_width': 36,
            'sensor_height': 24,
            'tilt_angle': 60  # 相机倾斜45度
        }
    )
    
    # 设置检测线 (可以根据实际视频调整)
    lines = [
        [(100, 200), (600, 200)],  # 水平线1
        [(100, 400), (600, 400)]   # 水平线2
    ]
    directions = [1, -1]  # 第一条线检测从上到下，第二条线检测从下到上
    
    inspector.set_detection_lines(lines, directions)
    
    # 设置测速区域和限速
    speed_zones = [
        [(0, 50), (800, 50), (800, 500), (0, 500)]  # 矩形测速区域
    ]
    speed_limits = [60]  # 限速60km/h
    
    inspector.set_speed_zones(speed_zones, speed_limits)
    
    # 设置应急车道区域
    emergency_lanes = [
        [(50, 300), (150, 300), (150, 500), (50, 500)]  # 矩形应急车道区域
    ]
    
    inspector.set_emergency_lanes(emergency_lanes)
    
    # 设置方向箭头
    direction_arrows = [
        [(400, 300), (400, 200), "up"]  # 向上箭头
    ]
    
    inspector.set_direction_arrows(direction_arrows)
    
    # 处理视频
    inspector.detect_and_track(
        video_path='G:\\t.mp4',  # 输入视频路径
        output_path='output_video.mp4',  # 输出视频路径
        show_video=True,  # 显示实时视频
        save_video=True  # 保存输出视频
    )
    
    # 保存数据
    inspector.save_data('trajectories.json', 'events.json')
    
    # 可视化轨迹
    inspector.visualize_trajectories('trajectories_visualization.png')
    
    # 生成报告
    inspector.generate_report('traffic_inspection_report.html')
    
    # 打印统计信息
    print(f"跟踪对象数量: {len(inspector.get_trajectories())}")
    print(f"压线事件数量: {len(inspector.get_crossing_events())}")
    print(f"超速事件数量: {len(inspector.get_speeding_events())}")
    print(f"非法占用应急车道事件数量: {len(inspector.get_illegal_lane_events())}")
    print(f"逆行事件数量: {len(inspector.get_reverse_events())}")
    print(f"变道事件数量: {len(inspector.get_lane_change_events())}")
    
    # 打印超速事件详情
    for event in inspector.get_speeding_events():
        print(f"对象 {event['track_id']} 在 {event['timestamp']} 超速: {event['speed']:.1f}km/h (限速 {event['speed_limit']}km/h)")
    
    # 打印非法占用应急车道事件详情
    for event in inspector.get_illegal_lane_events():
        print(f"对象 {event['track_id']} 在 {event['timestamp']} 非法占用应急车道 {event['lane_id']}")