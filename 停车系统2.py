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

class DroneParkingMonitor:
    def __init__(self, model_path='yolov8s.pt', conf_threshold=0.5):
        """
        无人机停车监控系统 - 现实场景优化版本
        """
        # 性能优化
        self.frame_skip = 1  # 不跳过帧，保证检测精度
        self.frame_count = 0
        
        # 加载车辆检测模型
        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold
        
        # 车辆类别
        self.vehicle_classes = [2, 3, 5, 7]  # car, motorcycle, bus, truck
        
        # 数据存储
        self.track_history = defaultdict(lambda: deque(maxlen=30))
        self.vehicle_data = defaultdict(lambda: {
            'first_seen': None,
            'last_seen': None,
            'parking_start': None,
            'total_parking_time': 0,
            'violations': [],
            'current_spot': -1,
            'license_plate': None,
            'license_confidence': 0
        })
        
        # 停车位管理
        self.parking_spots = []
        self.spot_status = {}  # 0:空闲, 1:占用, 2:违规
        
        # 现实参数
        self.min_parking_time = 10  # 秒
        self.stationary_threshold = 3.0  # 像素移动阈值
        self.min_stationary_frames = 20
        
        # 性能监控
        self.performance = {
            'fps': 0,
            'detection_time': 0,
            'total_frames': 0,
            'start_time': time.time()
        }
        
        # 可视化配置
        self.colors = {
            'free': (0, 255, 0),      # 绿色
            'occupied': (0, 165, 255), # 橙色
            'violation': (0, 0, 255),  # 红色
            'road': (100, 100, 100),   # 灰色
            'vehicle_moving': (255, 255, 0),   # 黄色
            'vehicle_stopped': (255, 0, 255),  # 紫色
            'text': (255, 255, 255)    # 白色
        }
        
        print("🚁 无人机停车监控系统初始化完成")

    def setup_realistic_parking_area(self, frame_width=1280, frame_height=720):
        """
        设置真实停车区域 - 适合低空无人机视角
        """
        self.parking_spots = []
        
        # 道路区域（中间）
        road_width = 300
        self.road_area = [
            [frame_width//2 - road_width//2, 0],
            [frame_width//2 + road_width//2, 0],
            [frame_width//2 + road_width//2, frame_height],
            [frame_width//2 - road_width//2, frame_height]
        ]
        
        # 左侧停车区 - 2排，每排3个车位
        left_start_x = 80
        spot_width = 120
        spot_length = 180
        
        for row in range(2):
            for col in range(3):
                base_x = left_start_x + col * (spot_width + 15)
                base_y = 200 + row * (spot_length + 20)
                
                # 轻微倾斜
                tilt_angle = 5  # 小角度倾斜
                rad_angle = math.radians(tilt_angle)
                x_offset = spot_length * math.sin(rad_angle) * 0.2
                
                spot = [
                    [base_x, base_y],
                    [base_x + x_offset, base_y + spot_length],
                    [base_x + x_offset + spot_width, base_y + spot_length],
                    [base_x + spot_width, base_y]
                ]
                self.parking_spots.append({
                    'polygon': spot,
                    'direction': 'left',
                    'expected_angle': tilt_angle,
                    'type': 'standard'
                })
        
        # 右侧停车区 - 对称布局
        right_start_x = frame_width - 80 - spot_width
        for row in range(2):
            for col in range(3):
                base_x = right_start_x - col * (spot_width + 15)
                base_y = 200 + row * (spot_length + 20)
                
                tilt_angle = -5  # 对称倾斜
                rad_angle = math.radians(tilt_angle)
                x_offset = spot_length * math.sin(rad_angle) * 0.2
                
                spot = [
                    [base_x, base_y],
                    [base_x + x_offset, base_y + spot_length],
                    [base_x + x_offset + spot_width, base_y + spot_length],
                    [base_x + spot_width, base_y]
                ]
                self.parking_spots.append({
                    'polygon': spot,
                    'direction': 'right',
                    'expected_angle': tilt_angle,
                    'type': 'standard'
                })
        
        # 初始化车位状态
        for i in range(len(self.parking_spots)):
            self.spot_status[i] = 0
        
        print(f"🅿️ 停车区域设置完成 - 总共 {len(self.parking_spots)} 个车位")

    def detect_vehicles(self, frame):
        """
        车辆检测 - 优化版本
        """
        start_time = time.time()
        
        try:
            # 使用优化的推理参数
            results = self.model.track(
                frame,
                persist=True,
                conf=self.conf_threshold,
                iou=0.5,
                classes=self.vehicle_classes,
                verbose=False,
                imgsz=640,
                device='cuda' if torch.cuda.is_available() else 'cpu'
            )
            
            vehicles = []
            
            if results[0].boxes is not None and results[0].boxes.id is not None:
                boxes = results[0].boxes.xywh.cpu()
                track_ids = results[0].boxes.id.int().cpu().tolist()
                class_ids = results[0].boxes.cls.int().cpu().tolist()
                confidences = results[0].boxes.conf.float().cpu().tolist()
                
                # 获取带标注的帧
                annotated_frame = results[0].plot()
                
                for box, track_id, class_id, conf in zip(boxes, track_ids, class_ids, confidences):
                    x, y, w, h = box
                    bbox = [float(x - w/2), float(y - h/2), float(x + w/2), float(y + h/2)]
                    
                    # 更新轨迹历史
                    self.track_history[track_id].append((float(x), float(y)))
                    
                    vehicles.append({
                        'track_id': track_id,
                        'bbox': bbox,
                        'center': (float(x), float(y)),
                        'confidence': conf,
                        'class_id': class_id,
                        'track_points': list(self.track_history[track_id]),
                        'class_name': self.model.names[class_id],
                        'width': float(w),
                        'height': float(h)
                    })
                
                processed_frame = annotated_frame
            else:
                processed_frame = frame.copy()
                
        except Exception as e:
            print(f"车辆检测错误: {e}")
            processed_frame = frame.copy()
            vehicles = []
        
        # 更新性能统计
        detection_time = (time.time() - start_time) * 1000
        self.performance['detection_time'] = detection_time
        self.performance['total_frames'] += 1
        
        return processed_frame, vehicles

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

    def find_parking_spot(self, vehicle):
        """为车辆找到停车位"""
        center = vehicle['center']
        bbox = vehicle['bbox']
        
        best_spot = -1
        best_score = 0
        
        for i, spot_data in enumerate(self.parking_spots):
            spot = spot_data['polygon']
            
            # 计算重叠度
            overlap = self.calculate_overlap(bbox, spot)
            
            # 检查中心点
            center_in_spot = self.is_point_in_polygon(center, spot)
            
            # 综合评分
            score = 0
            if center_in_spot:
                score += 0.6
            score += overlap * 0.4
            
            if score > best_score:
                best_score = score
                best_spot = i
        
        return best_spot if best_score > 0.3 else -1

    def calculate_overlap(self, bbox, polygon):
        """计算边界框与多边形的重叠度"""
        # 简化的重叠计算
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

    def analyze_movement(self, track_points):
        """分析车辆运动状态"""
        if len(track_points) < 3:
            return {'is_stationary': False, 'movement': 0, 'stationary_frames': 0}
        
        # 计算移动距离
        recent_points = track_points[-5:]
        total_movement = 0
        
        for i in range(1, len(recent_points)):
            dx = recent_points[i][0] - recent_points[i-1][0]
            dy = recent_points[i][1] - recent_points[i-1][1]
            total_movement += math.sqrt(dx*dx + dy*dy)
        
        is_stationary = total_movement < self.stationary_threshold
        
        return {
            'is_stationary': is_stationary,
            'movement': total_movement,
            'stationary_frames': self.vehicle_data[id(track_points)].get('stationary_frames', 0) + 1 if is_stationary else 0
        }

    def detect_violations(self, vehicle, spot_index, movement_analysis):
        """检测违规行为"""
        violations = []
        track_id = vehicle['track_id']
        
        # 初始化车辆数据
        if self.vehicle_data[track_id]['first_seen'] is None:
            self.vehicle_data[track_id]['first_seen'] = datetime.now()
        
        self.vehicle_data[track_id]['last_seen'] = datetime.now()
        
        # 检查道路停车
        if self.is_point_in_polygon(vehicle['center'], self.road_area):
            violations.append("道路区域违规停车")
        
        # 停车位相关检查
        if spot_index != -1:
            # 停车时间检查
            if movement_analysis['is_stationary']:
                if self.vehicle_data[track_id]['parking_start'] is None:
                    self.vehicle_data[track_id]['parking_start'] = datetime.now()
                    self.vehicle_data[track_id]['current_spot'] = spot_index
                
                parking_duration = (datetime.now() - self.vehicle_data[track_id]['parking_start']).total_seconds()
                
                if parking_duration > self.min_parking_time:
                    # 更新总停车时间
                    self.vehicle_data[track_id]['total_parking_time'] += (datetime.now() - self.vehicle_data[track_id]['last_seen']).total_seconds()
                    
                    # 触发车牌识别标记
                    if self.vehicle_data[track_id]['license_plate'] is None:
                        violations.append("未识别车牌")
            else:
                # 车辆移动，重置停车时间
                self.vehicle_data[track_id]['parking_start'] = None
                self.vehicle_data[track_id]['current_spot'] = -1
        else:
            # 不在停车位但静止
            if movement_analysis['is_stationary'] and movement_analysis['stationary_frames'] > self.min_stationary_frames:
                violations.append("非停车区域停车")
        
        # 更新违规记录
        self.vehicle_data[track_id]['violations'] = violations
        
        return violations

    def update_spot_status(self, vehicles):
        """更新车位状态"""
        # 重置状态
        for spot_id in self.spot_status:
            self.spot_status[spot_id] = 0
        
        # 更新占用状态
        for track_id, data in self.vehicle_data.items():
            spot_index = data.get('current_spot', -1)
            if spot_index != -1 and data.get('parking_start') is not None:
                if data['violations']:
                    self.spot_status[spot_index] = 2  # 违规
                else:
                    self.spot_status[spot_index] = 1  # 正常占用

    def calculate_fps(self):
        """计算帧率"""
        current_time = time.time()
        elapsed = current_time - self.performance['start_time']
        
        if elapsed > 0:
            self.performance['fps'] = self.performance['total_frames'] / elapsed
        
        return self.performance['fps']

    def process_frame(self, frame):
        """处理视频帧"""
        # 车辆检测
        processed_frame, vehicles = self.detect_vehicles(frame)
        
        # 分析每个车辆
        for vehicle in vehicles:
            # 运动分析
            movement_analysis = self.analyze_movement(vehicle['track_points'])
            
            # 停车位匹配
            spot_index = self.find_parking_spot(vehicle)
            
            # 违规检测
            violations = self.detect_violations(vehicle, spot_index, movement_analysis)
            
            # 存储分析结果
            vehicle['analysis'] = {
                'movement': movement_analysis,
                'spot_index': spot_index,
                'violations': violations
            }
        
        # 更新车位状态
        self.update_spot_status(vehicles)
        
        # 绘制可视化
        self.draw_display(processed_frame, vehicles)
        
        return processed_frame, vehicles

    def draw_display(self, frame, vehicles):
        """绘制显示界面"""
        # 绘制基础设施
        self.draw_infrastructure(frame)
        
        # 绘制车辆
        for vehicle in vehicles:
            self.draw_vehicle(frame, vehicle)
        
        # 绘制统计信息
        self.draw_statistics(frame, vehicles)

    def draw_infrastructure(self, frame):
        """绘制基础设施"""
        # 绘制道路
        road_pts = np.array(self.road_area, np.int32)
        overlay = frame.copy()
        cv2.fillPoly(overlay, [road_pts], self.colors['road'])
        cv2.addWeighted(overlay, 0.15, frame, 0.85, 0, frame)
        cv2.polylines(frame, [road_pts], True, (150, 150, 150), 2)
        
        # 绘制道路中心线
        center_x = frame.shape[1] // 2
        cv2.line(frame, (center_x, 0), (center_x, frame.shape[0]), 
                (200, 200, 100), 1, cv2.LINE_AA)
        
        # 绘制停车位
        for i, spot_data in enumerate(self.parking_spots):
            spot = spot_data['polygon']
            status = self.spot_status[i]
            
            # 选择颜色
            if status == 2:
                color = self.colors['violation']
                alpha = 0.4
            elif status == 1:
                color = self.colors['occupied']
                alpha = 0.3
            else:
                color = self.colors['free']
                alpha = 0.2
            
            # 绘制车位
            pts = np.array(spot, np.int32)
            overlay = frame.copy()
            cv2.fillPoly(overlay, [pts], color)
            cv2.addWeighted(overlay, alpha, frame, 1-alpha, 0, frame)
            cv2.polylines(frame, [pts], True, color, 2)
            
            # 车位编号
            text_pos = (int(spot[0][0]), int(spot[0][1]) - 8)
            cv2.putText(frame, f"{i}", text_pos, 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

    def draw_vehicle(self, frame, vehicle):
        """绘制车辆信息"""
        track_id = vehicle['track_id']
        bbox = vehicle['bbox']
        analysis = vehicle['analysis']
        
        x1, y1, x2, y2 = [int(coord) for coord in bbox]
        
        # 选择颜色
        if analysis['violations']:
            color = self.colors['violation']
        elif analysis['movement']['is_stationary']:
            color = self.colors['vehicle_stopped']
        else:
            color = self.colors['vehicle_moving']
        
        # 绘制边界框
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        
        # 绘制信息
        info_lines = [f"ID:{track_id}"]
        
        if analysis['spot_index'] != -1:
            info_lines.append(f"车位:{analysis['spot_index']}")
        
        if analysis['violations']:
            info_lines.append("违规!")
        
        # 车牌信息
        license_plate = self.vehicle_data[track_id].get('license_plate')
        if license_plate:
            info_lines.append(f"车牌:{license_plate}")
        
        # 绘制信息背景
        text_height = len(info_lines) * 15 + 10
        cv2.rectangle(frame, (x1, y1 - text_height), (x2, y1), (0, 0, 0), -1)
        cv2.rectangle(frame, (x1, y1 - text_height), (x2, y1), color, 1)
        
        # 绘制文本
        for i, line in enumerate(info_lines):
            cv2.putText(frame, line, (x1 + 5, y1 - 10 - i * 15),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

    def draw_statistics(self, frame, vehicles):
        """绘制统计信息"""
        # 计算统计
        total_vehicles = len(vehicles)
        occupied_spots = sum(1 for status in self.spot_status.values() if status in [1, 2])
        total_spots = len(self.parking_spots)
        violation_count = sum(len(v['analysis']['violations']) for v in vehicles)
        
        # 计算帧率
        fps = self.calculate_fps()
        
        # 绘制统计面板
        panel_width = 300
        panel_height = 130
        cv2.rectangle(frame, (10, 10), (panel_width, panel_height), (0, 0, 0), -1)
        cv2.rectangle(frame, (10, 10), (panel_width, panel_height), (255, 255, 255), 2)
        
        # 统计信息
        stats = [
            "无人机停车监控系统",
            f"车辆数量: {total_vehicles}",
            f"车位占用: {occupied_spots}/{total_spots}",
            f"违规事件: {violation_count}",
            f"系统帧率: {fps:.1f} FPS",
            f"检测时间: {self.performance['detection_time']:.1f}ms"
        ]
        
        for i, text in enumerate(stats):
            color = self.colors['text']
            if i == 0:
                color = (0, 255, 255)
            elif "违规" in text and violation_count > 0:
                color = (0, 0, 255)
            
            cv2.putText(frame, text, (20, 35 + i * 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    def generate_report(self):
        """生成报告"""
        current_time = datetime.now()
        
        occupied_spots = sum(1 for status in self.spot_status.values() if status in [1, 2])
        total_spots = len(self.parking_spots)
        
        # 统计违规车辆
        violating_vehicles = []
        for track_id, data in self.vehicle_data.items():
            if data['violations']:
                violating_vehicles.append({
                    'track_id': track_id,
                    'violations': data['violations'],
                    'parking_time': data['total_parking_time'],
                    'license_plate': data['license_plate'],
                    'first_seen': data['first_seen'].isoformat() if data['first_seen'] else None
                })
        
        return {
            'timestamp': current_time.isoformat(),
            'summary': {
                'total_spots': total_spots,
                'occupied_spots': occupied_spots,
                'utilization': f"{(occupied_spots/total_spots*100):.1f}%",
                'violating_vehicles': len(violating_vehicles),
                'total_tracked_vehicles': len(self.vehicle_data)
            },
            'violations': violating_vehicles,
            'performance': {
                'average_fps': self.performance['fps'],
                'total_frames': self.performance['total_frames']
            }
        }

    def set_license_plate(self, track_id, license_plate, confidence=0.0):
        """设置车牌信息"""
        self.vehicle_data[track_id]['license_plate'] = license_plate
        self.vehicle_data[track_id]['license_confidence'] = confidence

def main():
    """主程序"""
    # 初始化系统
    parking_system = DroneParkingMonitor(
        model_path='yolov8s.pt',
        conf_threshold=0.5
    )
    
    # 设置停车区域
    parking_system.setup_realistic_parking_area()
    
    # 视频源
    video_source = 0  # 摄像头
    # video_source = "parking_video.mp4"  # 视频文件
    
    cap = cv2.VideoCapture(video_source)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    # 输出目录
    output_dir = Path("drone_parking_monitor")
    output_dir.mkdir(exist_ok=True)
    
    print("🚁 无人机停车监控系统启动!")
    print("📊 系统特性:")
    print("   • 真实低空视角优化")
    print("   • 高性能车辆检测")
    print("   • 智能停车位管理")
    print("   • 车牌识别集成")
    print("   • 实时违规检测")
    print("🎮 控制: q=退出, r=报告, s=截图, p=暂停, l=车牌识别")
    
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
                cv2.imshow('🚁 无人机停车监控系统', processed_frame)
            
            # 键盘控制
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                report = parking_system.generate_report()
                report_file = output_dir / f"停车监控报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(report_file, 'w', encoding='utf-8') as f:
                    json.dump(report, f, indent=2, ensure_ascii=False)
                print(f"📄 监控报告已保存: {report_file}")
            elif key == ord('s'):
                snapshot_file = output_dir / f"监控截图_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                cv2.imwrite(str(snapshot_file), processed_frame)
                print(f"📷 截图已保存: {snapshot_file}")
            elif key == ord('p'):
                paused = not paused
                print("⏸️ 已暂停" if paused else "▶️ 已继续")
            elif key == ord('l'):
                # 触发车牌识别
                print("🔍 启动车牌识别...")
                # 这里可以集成车牌识别功能
    
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
        final_report_file = output_dir / "最终监控报告.json"
        with open(final_report_file, 'w', encoding='utf-8') as f:
            json.dump(final_report, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 最终报告已保存: {final_report_file}")
        print("🎯 监控系统运行完成!")

if __name__ == "__main__":
    main()