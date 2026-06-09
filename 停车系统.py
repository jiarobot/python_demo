import cv2
import numpy as np
from ultralytics import YOLO
import torch
import time
from datetime import datetime, timedelta
import json
from collections import defaultdict, deque
import math
import os
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

class RealDroneParkingSystem:
    def __init__(self, model_path='yolov8n.pt', conf_threshold=0.5, iou_threshold=0.5):
        """
        真实场景无人机停车识别系统
        """
        # 性能优化
        self.frame_skip = 2  # 每2帧处理1次
        self.frame_count = 0
        self.last_frame = None
        
        # 加载模型 - 使用更适合车辆的模型
        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        
        # 车辆类别 - 专注于汽车和卡车
        self.vehicle_classes = [2, 5, 7]  # car, bus, truck
        
        # 跟踪和数据存储
        self.track_history = defaultdict(lambda: deque(maxlen=30))
        self.parking_data = defaultdict(lambda: {
            'first_detected': None,
            'last_detected': None,
            'parking_start': None,
            'total_parking_time': 0,
            'violations': [],
            'current_spot': -1
        })
        
        # 停车位管理
        self.parking_spots = []
        self.spot_status = {}  # -1: 未知, 0: 空闲, 1: 占用, 2: 违规
        
        # 参数配置
        self.min_parking_time = 10  # 秒
        self.stationary_threshold = 5.0  # 像素移动阈值
        self.min_stationary_frames = 15  # 最小静止帧数
        
        # 性能统计
        self.stats = {
            'fps': 0,
            'processing_time': 0,
            'total_frames': 0,
            'start_time': time.time()
        }
        
        # 可视化配置
        self.colors = {
            'free': (0, 255, 0),      # 绿色 - 空闲
            'occupied': (0, 165, 255), # 橙色 - 占用
            'violation': (0, 0, 255),  # 红色 - 违规
            'road': (100, 100, 100),   # 灰色 - 道路
            'vehicle': (255, 255, 0),  # 黄色 - 车辆
            'text': (255, 255, 255)    # 白色 - 文本
        }
        
        print("🚁 真实场景无人机停车识别系统初始化完成")

    def setup_realistic_parking_layout(self, frame_width=1280, frame_height=720):
        """
        设置真实场景的停车位布局 - 道路两侧，略微倾斜
        """
        self.parking_spots = []
        
        # 道路区域（中间区域）
        road_width = 400
        self.road_area = [
            [frame_width//2 - road_width//2, 0],
            [frame_width//2 + road_width//2, 0],
            [frame_width//2 + road_width//2, frame_height],
            [frame_width//2 - road_width//2, frame_height]
        ]
        
        # 左侧停车位（略微向右倾斜）
        left_start_x = 50
        spot_width = 100
        spot_length = 150
        
        for row in range(3):  # 3排
            for col in range(4):  # 每排4个车位
                base_x = left_start_x + col * (spot_width + 20)
                base_y = 150 + row * (spot_length + 30)
                
                # 轻微倾斜角度 (5-15度)
                tilt_angle = 10 + row * 2  # 每排角度略有不同
                rad_angle = math.radians(tilt_angle)
                x_offset = spot_length * math.sin(rad_angle) * 0.3  # 控制倾斜程度
                
                spot = [
                    [base_x, base_y],
                    [base_x + x_offset, base_y + spot_length],
                    [base_x + x_offset + spot_width, base_y + spot_length],
                    [base_x + spot_width, base_y]
                ]
                self.parking_spots.append({
                    'polygon': spot,
                    'direction': 'left',
                    'expected_angle': tilt_angle
                })
        
        # 右侧停车位（略微向左倾斜，与左侧对称）
        right_start_x = frame_width - 50 - spot_width
        for row in range(3):
            for col in range(4):
                base_x = right_start_x - col * (spot_width + 20)
                base_y = 150 + row * (spot_length + 30)
                
                tilt_angle = -10 - row * 2  # 负角度实现对称
                rad_angle = math.radians(tilt_angle)
                x_offset = spot_length * math.sin(rad_angle) * 0.3
                
                spot = [
                    [base_x, base_y],
                    [base_x + x_offset, base_y + spot_length],
                    [base_x + x_offset + spot_width, base_y + spot_length],
                    [base_x + spot_width, base_y]
                ]
                self.parking_spots.append({
                    'polygon': spot,
                    'direction': 'right', 
                    'expected_angle': tilt_angle
                })
        
        # 初始化车位状态
        for i in range(len(self.parking_spots)):
            self.spot_status[i] = 0  # 初始状态为空闲
        
        print(f"🅿️ 真实停车场景设置完成 - 总共 {len(self.parking_spots)} 个车位")

    def efficient_vehicle_detection(self, frame):
        """
        高效的车辆检测 - 针对真实场景优化
        """
        self.frame_count += 1
        
        # 性能优化：跳过部分帧
        if self.frame_count % self.frame_skip != 0 and self.last_frame is not None:
            return self.last_frame, []
        
        start_time = time.time()
        
        try:
            # 使用优化的推理参数
            results = self.model.track(
                frame,
                persist=True,
                conf=self.conf_threshold,
                iou=self.iou_threshold,
                classes=self.vehicle_classes,
                verbose=False,
                imgsz=640,  # 较小尺寸提高速度
                half=True,  # 使用半精度推理
                device='cuda' if torch.cuda.is_available() else 'cpu'
            )
            
            vehicles = []
            
            if results[0].boxes is not None and results[0].boxes.id is not None:
                boxes = results[0].boxes.xywh.cpu()
                track_ids = results[0].boxes.id.int().cpu().tolist()
                class_ids = results[0].boxes.cls.int().cpu().tolist()
                confidences = results[0].boxes.conf.float().cpu().tolist()
                
                # 使用YOLO自带的标注
                annotated_frame = results[0].plot()
                
                for box, track_id, class_id, conf in zip(boxes, track_ids, class_ids, confidences):
                    x, y, w, h = box
                    bbox = [float(x - w/2), float(y - h/2), float(x + w/2), float(y + h/2)]
                    
                    # 更新轨迹
                    self.track_history[track_id].append((float(x), float(y)))
                    
                    vehicles.append({
                        'track_id': track_id,
                        'bbox': bbox,
                        'center': (float(x), float(y)),
                        'confidence': conf,
                        'class_id': class_id,
                        'track_points': list(self.track_history[track_id]),
                        'class_name': self.model.names[class_id]
                    })
                
                self.last_frame = annotated_frame
            else:
                annotated_frame = frame.copy()
                self.last_frame = annotated_frame
                
        except Exception as e:
            print(f"检测错误: {e}")
            annotated_frame = frame.copy()
            vehicles = []
            self.last_frame = annotated_frame
        
        # 更新性能统计
        processing_time = (time.time() - start_time) * 1000
        self.stats['processing_time'] = processing_time
        self.stats['total_frames'] += 1
        
        return annotated_frame, vehicles

    def is_point_in_polygon(self, point, polygon):
        """判断点是否在多边形内"""
        x, y = point
        n = len(polygon)
        inside = False
        
        p1x, p1y = polygon[0]
        for i in range(1, n + 1):
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

    def find_vehicle_parking_spot(self, vehicle):
        """为车辆找到对应的停车位"""
        center = vehicle['center']
        bbox = vehicle['bbox']
        
        best_spot = -1
        best_score = 0
        
        for i, spot_data in enumerate(self.parking_spots):
            spot = spot_data['polygon']
            
            # 计算车辆与车位的重叠度
            overlap = self.calculate_bbox_polygon_overlap(bbox, spot)
            
            # 检查中心点是否在车位内
            center_in_spot = self.is_point_in_polygon(center, spot)
            
            # 综合评分
            score = 0
            if center_in_spot:
                score += 0.7
            score += overlap * 0.3
            
            if score > best_score:
                best_score = score
                best_spot = i
        
        return best_spot if best_score > 0.4 else -1

    def calculate_bbox_polygon_overlap(self, bbox, polygon):
        """计算边界框与多边形的重叠度"""
        # 简化的重叠计算 - 使用边界框近似
        poly_bbox = [
            min(p[0] for p in polygon), min(p[1] for p in polygon),
            max(p[0] for p in polygon), max(p[1] for p in polygon)
        ]
        
        return self.calculate_iou(bbox, poly_bbox)

    def calculate_iou(self, bbox1, bbox2):
        """计算IoU"""
        x1 = max(bbox1[0], bbox2[0])
        y1 = max(bbox1[1], bbox2[1])
        x2 = min(bbox1[2], bbox2[2])
        y2 = min(bbox1[3], bbox2[3])
        
        if x2 < x1 or y2 < y1:
            return 0.0
        
        intersection = (x2 - x1) * (y2 - y1)
        area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
        area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
        
        union = area1 + area2 - intersection
        return intersection / union if union > 0 else 0

    def analyze_vehicle_movement(self, track_points):
        """分析车辆运动状态"""
        if len(track_points) < 5:
            return {'is_stationary': False, 'movement': 0, 'stationary_frames': 0}
        
        # 计算最近5个点的总移动距离
        recent_points = track_points[-5:]
        total_movement = 0
        
        for i in range(1, len(recent_points)):
            dx = recent_points[i][0] - recent_points[i-1][0]
            dy = recent_points[i][1] - recent_points[i-1][1]
            total_movement += math.sqrt(dx*dx + dy*dy)
        
        is_stationary = total_movement < self.stationary_threshold
        
        # 更新静止帧计数
        track_id = id(track_points)
        if is_stationary:
            self.parking_data[track_id]['stationary_frames'] = \
                self.parking_data[track_id].get('stationary_frames', 0) + 1
        else:
            self.parking_data[track_id]['stationary_frames'] = 0
        
        return {
            'is_stationary': is_stationary,
            'movement': total_movement,
            'stationary_frames': self.parking_data[track_id].get('stationary_frames', 0)
        }

    def analyze_parking_angle(self, vehicle, spot_index):
        """分析停车角度"""
        if spot_index == -1:
            return {'angle': 0, 'is_proper': True, 'deviation': 0}
        
        track_points = vehicle['track_points']
        if len(track_points) < 2:
            return {'angle': 0, 'is_proper': True, 'deviation': 0}
        
        # 计算车辆方向
        recent_points = track_points[-5:]
        if len(recent_points) < 2:
            return {'angle': 0, 'is_proper': True, 'deviation': 0}
        
        dx = recent_points[-1][0] - recent_points[0][0]
        dy = recent_points[-1][1] - recent_points[0][1]
        
        if dx == 0 and dy == 0:
            # 使用边界框方向
            x1, y1, x2, y2 = vehicle['bbox']
            width = x2 - x1
            height = y2 - y1
            angle = 0 if width > height else 90
        else:
            angle = math.degrees(math.atan2(dy, dx))
            # 归一化到0-180度
            angle = angle % 180
            if angle < 0:
                angle += 180
        
        # 获取期望角度
        expected_angle = self.parking_spots[spot_index]['expected_angle']
        if expected_angle < 0:
            expected_angle += 180
        
        # 计算角度偏差
        deviation = min(abs(angle - expected_angle), 180 - abs(angle - expected_angle))
        is_proper = deviation <= 30  # 30度以内认为合适
        
        return {
            'angle': angle,
            'expected_angle': expected_angle,
            'deviation': deviation,
            'is_proper': is_proper
        }

    def detect_parking_violations(self, vehicle, spot_index, movement_analysis, angle_analysis):
        """检测停车违规"""
        violations = []
        track_id = vehicle['track_id']
        
        # 初始化车辆数据
        if self.parking_data[track_id]['first_detected'] is None:
            self.parking_data[track_id]['first_detected'] = datetime.now()
        
        self.parking_data[track_id]['last_detected'] = datetime.now()
        
        # 检查是否在道路上停车
        if self.is_point_in_polygon(vehicle['center'], self.road_area):
            violations.append("在道路区域停车")
        
        # 检查停车位相关违规
        if spot_index != -1:
            # 角度违规
            if not angle_analysis['is_proper']:
                violations.append(f"停车角度不规范 (当前{angle_analysis['angle']:.1f}°, 期望{angle_analysis['expected_angle']:.1f}°)")
            
            # 停车时间违规
            if movement_analysis['is_stationary']:
                if self.parking_data[track_id]['parking_start'] is None:
                    self.parking_data[track_id]['parking_start'] = datetime.now()
                    self.parking_data[track_id]['current_spot'] = spot_index
                
                parking_duration = (datetime.now() - self.parking_data[track_id]['parking_start']).total_seconds()
                
                if parking_duration > self.min_parking_time:
                    violations.append(f"停车时间过长 ({parking_duration:.0f}秒)")
            else:
                # 车辆移动，重置停车时间
                self.parking_data[track_id]['parking_start'] = None
                self.parking_data[track_id]['current_spot'] = -1
        else:
            # 不在停车位但静止 - 违规停车
            if movement_analysis['is_stationary'] and movement_analysis['stationary_frames'] > self.min_stationary_frames:
                violations.append("在非停车区域停车")
        
        # 更新违规记录
        self.parking_data[track_id]['violations'] = violations
        
        return violations

    def update_parking_spot_status(self, vehicles):
        """更新停车位状态"""
        # 重置所有车位状态
        for spot_id in self.spot_status:
            self.spot_status[spot_id] = 0  # 空闲
        
        # 更新占用状态
        for vehicle in vehicles:
            track_id = vehicle['track_id']
            spot_index = self.parking_data[track_id].get('current_spot', -1)
            
            if spot_index != -1:
                # 检查是否有违规
                if self.parking_data[track_id]['violations']:
                    self.spot_status[spot_index] = 2  # 违规占用
                else:
                    self.spot_status[spot_index] = 1  # 正常占用

    def calculate_fps(self):
        """计算帧率"""
        current_time = time.time()
        elapsed = current_time - self.stats['start_time']
        
        if elapsed > 0:
            self.stats['fps'] = self.stats['total_frames'] / elapsed
        
        return self.stats['fps']

    def process_frame(self, frame):
        """处理视频帧"""
        # 车辆检测
        processed_frame, vehicles = self.efficient_vehicle_detection(frame)
        
        # 分析每个车辆
        for vehicle in vehicles:
            # 运动分析
            movement_analysis = self.analyze_vehicle_movement(vehicle['track_points'])
            
            # 找到停车位
            spot_index = self.find_vehicle_parking_spot(vehicle)
            
            # 角度分析
            angle_analysis = self.analyze_parking_angle(vehicle, spot_index)
            
            # 违规检测
            violations = self.detect_parking_violations(vehicle, spot_index, movement_analysis, angle_analysis)
            
            # 存储分析结果
            vehicle['analysis'] = {
                'movement': movement_analysis,
                'spot_index': spot_index,
                'angle': angle_analysis,
                'violations': violations
            }
        
        # 更新车位状态
        self.update_parking_spot_status(vehicles)
        
        # 绘制可视化信息
        self.draw_realistic_display(processed_frame, vehicles)
        
        return processed_frame, vehicles

    def draw_realistic_display(self, frame, vehicles):
        """绘制真实场景的可视化"""
        # 绘制道路和停车位
        self.draw_infrastructure(frame)
        
        # 绘制车辆信息
        for vehicle in vehicles[:15]:  # 限制数量提高性能
            self.draw_vehicle_info(frame, vehicle)
        
        # 绘制统计信息
        self.draw_statistics_panel(frame, vehicles)

    def draw_infrastructure(self, frame):
        """绘制基础设施"""
        # 绘制道路区域
        road_pts = np.array(self.road_area, np.int32)
        overlay = frame.copy()
        cv2.fillPoly(overlay, [road_pts], self.colors['road'])
        cv2.addWeighted(overlay, 0.2, frame, 0.8, 0, frame)
        cv2.polylines(frame, [road_pts], True, (150, 150, 150), 2)
        
        # 绘制道路中心线
        center_x = frame.shape[1] // 2
        cv2.line(frame, (center_x, 0), (center_x, frame.shape[0]), 
                (255, 255, 100), 2, cv2.LINE_AA)
        
        # 绘制停车位
        for i, spot_data in enumerate(self.parking_spots):
            spot = spot_data['polygon']
            status = self.spot_status[i]
            
            # 根据状态选择颜色
            if status == 2:  # 违规
                color = self.colors['violation']
                alpha = 0.4
            elif status == 1:  # 占用
                color = self.colors['occupied']
                alpha = 0.3
            else:  # 空闲
                color = self.colors['free']
                alpha = 0.2
            
            # 绘制停车位
            pts = np.array(spot, np.int32)
            overlay = frame.copy()
            cv2.fillPoly(overlay, [pts], color)
            cv2.addWeighted(overlay, alpha, frame, 1-alpha, 0, frame)
            cv2.polylines(frame, [pts], True, color, 2)
            
            # 绘制车位编号（只在第一排显示）
            if i % 4 == 0:
                text_pos = (int(spot[0][0]), int(spot[0][1]) - 10)
                cv2.putText(frame, f"{i}", text_pos, 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    def draw_vehicle_info(self, frame, vehicle):
        """绘制车辆信息"""
        track_id = vehicle['track_id']
        bbox = vehicle['bbox']
        analysis = vehicle['analysis']
        
        x1, y1, x2, y2 = [int(coord) for coord in bbox]
        
        # 选择颜色
        if analysis['violations']:
            color = self.colors['violation']
        elif analysis['movement']['is_stationary']:
            color = (0, 255, 255)  # 黄色 - 静止
        else:
            color = self.colors['vehicle']  # 青色 - 移动
        
        # 绘制边界框
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        
        # 绘制简化信息
        info_lines = [
            f"ID:{track_id}",
            f"{vehicle['class_name']}"
        ]
        
        if analysis['spot_index'] != -1:
            info_lines.append(f"车位:{analysis['spot_index']}")
        
        if analysis['violations']:
            info_lines.append("违规!")
        
        # 绘制信息背景
        text_bg_y = y1 - len(info_lines) * 15 - 5
        cv2.rectangle(frame, (x1, text_bg_y), (x2, y1), (0, 0, 0), -1)
        cv2.rectangle(frame, (x1, text_bg_y), (x2, y1), color, 1)
        
        # 绘制文本
        for i, line in enumerate(info_lines):
            cv2.putText(frame, line, (x1 + 5, y1 - 10 - i * 15),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

    def draw_statistics_panel(self, frame, vehicles):
        """绘制统计信息面板"""
        # 计算统计信息
        total_vehicles = len(vehicles)
        occupied_spots = sum(1 for status in self.spot_status.values() if status in [1, 2])
        total_spots = len(self.parking_spots)
        violation_count = sum(len(v['analysis']['violations']) for v in vehicles)
        
        # 计算帧率
        fps = self.calculate_fps()
        
        # 绘制面板背景
        panel_width = 320
        panel_height = 140
        cv2.rectangle(frame, (10, 10), (panel_width, panel_height), (0, 0, 0), -1)
        cv2.rectangle(frame, (10, 10), (panel_width, panel_height), (255, 255, 255), 2)
        
        # 统计信息
        stats_lines = [
            "=== 无人机停车监控 ===",
            f"检测车辆: {total_vehicles}",
            f"占用车位: {occupied_spots}/{total_spots}",
            f"违规事件: {violation_count}",
            f"系统帧率: {fps:.1f} FPS",
            f"处理时间: {self.stats['processing_time']:.1f}ms"
        ]
        
        # 绘制统计信息
        for i, line in enumerate(stats_lines):
            color = self.colors['text']
            if i == 0:  # 标题
                color = (0, 255, 255)
            elif "违规" in line and violation_count > 0:
                color = (0, 0, 255)
            
            cv2.putText(frame, line, (20, 35 + i * 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        # 绘制图例
        legend_y = panel_height + 30
        legends = [
            ("道路区域", self.colors['road']),
            ("空闲车位", self.colors['free']),
            ("占用车位", self.colors['occupied']),
            ("违规停车", self.colors['violation'])
        ]
        
        for i, (text, color) in enumerate(legends):
            y_pos = legend_y + i * 25
            cv2.rectangle(frame, (20, y_pos), (40, y_pos + 15), color, -1)
            cv2.putText(frame, text, (50, y_pos + 12),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, self.colors['text'], 1)

    def generate_report(self):
        """生成监控报告"""
        current_time = datetime.now()
        
        occupied_spots = sum(1 for status in self.spot_status.values() if status in [1, 2])
        total_spots = len(self.parking_spots)
        utilization = occupied_spots / total_spots if total_spots > 0 else 0
        
        # 统计违规车辆
        violating_vehicles = []
        for track_id, data in self.parking_data.items():
            if data['violations']:
                violating_vehicles.append({
                    'track_id': track_id,
                    'violations': data['violations'],
                    'parking_time': data['total_parking_time'],
                    'first_detected': data['first_detected'].isoformat() if data['first_detected'] else None
                })
        
        return {
            'timestamp': current_time.isoformat(),
            'summary': {
                'total_spots': total_spots,
                'occupied_spots': occupied_spots,
                'utilization_rate': f"{utilization:.1%}",
                'violating_vehicles_count': len(violating_vehicles),
                'total_vehicles_tracked': len(self.parking_data)
            },
            'violations': violating_vehicles,
            'performance': {
                'average_fps': self.stats['fps'],
                'total_processing_time': self.stats['processing_time'],
                'frames_processed': self.stats['total_frames']
            }
        }

def main():
    """主程序"""
    # 初始化系统
    parking_system = RealDroneParkingSystem(
        model_path='yolov8n.pt',  # 可以尝试 yolov8s.pt 提高精度
        conf_threshold=0.5,
        iou_threshold=0.5
    )
    
    # 设置真实停车场景
    parking_system.setup_realistic_parking_layout()
    
    # 视频源设置
    video_source = 0  # 摄像头
    # video_source = "parking_lot.mp4"  # 视频文件
    
    cap = cv2.VideoCapture(video_source)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    # 输出目录
    output_dir = Path("drone_parking_output")
    output_dir.mkdir(exist_ok=True)
    
    print("🚁 真实场景无人机停车系统启动!")
    print("📊 系统特性:")
    print("   • 真实道路两侧停车场景")
    print("   • 高性能车辆检测与跟踪")
    print("   • 智能停车位匹配")
    print("   • 多维度违规检测")
    print("   • 实时性能监控")
    print("🎮 控制: q=退出, r=报告, s=截图, p=暂停")
    
    paused = False
    
    try:
        while True:
            if not paused:
                ret, frame = cap.read()
                if not ret:
                    print("❌ 无法读取视频流")
                    break
                
                # 处理帧
                processed_frame, vehicles = parking_system.process_frame(frame)
                
                # 显示结果
                cv2.imshow('🚁 真实场景无人机停车监控', processed_frame)
            
            # 键盘控制
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                report = parking_system.generate_report()
                report_file = output_dir / f"停车报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(report_file, 'w', encoding='utf-8') as f:
                    json.dump(report, f, indent=2, ensure_ascii=False)
                print(f"📄 报告已保存: {report_file}")
            elif key == ord('s'):
                snapshot_file = output_dir / f"截图_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                cv2.imwrite(str(snapshot_file), processed_frame)
                print(f"📷 截图已保存: {snapshot_file}")
            elif key == ord('p'):
                paused = not paused
                print("⏸️ 已暂停" if paused else "▶️ 已继续")
    
    except Exception as e:
        print(f"❌ 系统错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理资源
        cap.release()
        cv2.destroyAllWindows()
        
        # 生成最终报告
        final_report = parking_system.generate_report()
        final_report_file = output_dir / "最终停车报告.json"
        with open(final_report_file, 'w', encoding='utf-8') as f:
            json.dump(final_report, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 最终报告已保存: {final_report_file}")
        print("🎯 系统运行完成!")

if __name__ == "__main__":
    main()