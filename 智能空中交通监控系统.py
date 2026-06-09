import cv2
import numpy as np
import matplotlib.pyplot as plt
from collections import deque, defaultdict
import time
from scipy.spatial import distance
from sklearn.cluster import DBSCAN
import warnings
warnings.filterwarnings('ignore')

class AerialObject:
    """空中目标对象"""
    def __init__(self, object_id, position, frame_count):
        self.id = object_id
        self.positions = deque(maxlen=50)  # 存储最近50个位置
        self.positions.append(position)
        self.speeds = deque(maxlen=10)
        self.directions = deque(maxlen=10)
        self.first_seen = frame_count
        self.last_seen = frame_count
        self.track_color = np.random.randint(0, 255, 3).tolist()
        self.status = "active"  # active, lost, removed
        self.lost_count = 0
        self.classification = "unknown"
        
    def update(self, position, frame_count):
        """更新目标位置"""
        if len(self.positions) > 0:
            # 计算速度
            last_pos = self.positions[-1]
            dist = np.sqrt((position[0]-last_pos[0])**2 + (position[1]-last_pos[1])**2)
            self.speeds.append(dist)
            
            # 计算方向
            dx = position[0] - last_pos[0]
            dy = position[1] - last_pos[1]
            direction = np.arctan2(dy, dx)
            self.directions.append(direction)
            
            # 分类目标
            self._classify_object()
        
        self.positions.append(position)
        self.last_seen = frame_count
        self.lost_count = 0
        
    def _classify_object(self):
        """基于运动特征分类目标"""
        if len(self.speeds) < 3:
            return
            
        avg_speed = np.mean(self.speeds)
        speed_std = np.std(self.speeds)
        
        if avg_speed < 2:
            self.classification = "stationary"
        elif avg_speed < 10 and speed_std < 3:
            self.classification = "bird"
        elif avg_speed >= 10 and speed_std > 5:
            self.classification = "aircraft"
        else:
            self.classification = "unknown"

class EagleVisionSystem:
    """鹰眼视觉系统主类"""
    
    def __init__(self):
        # 目标跟踪
        self.objects = {}
        self.next_object_id = 0
        self.frame_count = 0
        
        # 背景减除器
        self.backSub = cv2.createBackgroundSubtractorMOG2(
            history=500, 
            varThreshold=16, 
            detectShadows=True
        )
        
        # 运动检测参数
        self.min_contour_area = 100
        self.max_contour_area = 5000
        self.tracking_threshold = 50
        
        # 轨迹分析
        self.trajectories = defaultdict(list)
        
        # 性能监控
        self.performance_stats = {
            'detection_time': [],
            'tracking_time': [],
            'objects_count': []
        }
        
    def preprocess_frame(self, frame):
        """帧预处理"""
        # 高斯模糊降噪
        blurred = cv2.GaussianBlur(frame, (5, 5), 0)
        
        # 对比度增强
        lab = cv2.cvtColor(blurred, cv2.COLOR_BGR2LAB)
        lab[:, :, 0] = cv2.createCLAHE(clipLimit=2.0).apply(lab[:, :, 0])
        enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        
        return enhanced
    
    def detect_motion(self, frame):
        """运动目标检测"""
        start_time = time.time()
        
        # 应用背景减除
        fg_mask = self.backSub.apply(frame)
        
        # 形态学操作去除噪声
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)
        
        # 查找轮廓
        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        detections = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if self.min_contour_area < area < self.max_contour_area:
                x, y, w, h = cv2.boundingRect(contour)
                center = (x + w//2, y + h//2)
                detections.append({
                    'bbox': (x, y, w, h),
                    'center': center,
                    'area': area
                })
        
        detection_time = time.time() - start_time
        self.performance_stats['detection_time'].append(detection_time)
        
        return detections, fg_mask
    
    def track_objects(self, detections):
        """多目标跟踪"""
        start_time = time.time()
        
        # 初始化变量
        assigned_detections = set()
        assigned_objects = set()
        
        # 如果没有检测到目标，更新所有目标状态
        if not detections:
            self._update_object_states()
            tracking_time = time.time() - start_time
            self.performance_stats['tracking_time'].append(tracking_time)
            return
        
        # 计算检测点与现有目标之间的距离
        detection_centers = [det['center'] for det in detections]
        object_centers = [obj.positions[-1] for obj in self.objects.values() 
                        if obj.status == "active"]
        object_ids = [obj_id for obj_id, obj in self.objects.items() 
                    if obj.status == "active"]
        
        if object_centers:
            # 计算距离矩阵
            dist_matrix = distance.cdist(detection_centers, object_centers)
            
            # 分配检测到现有目标
            for i, detection in enumerate(detections):
                if i in assigned_detections:
                    continue
                    
                min_dist = np.min(dist_matrix[i])
                if min_dist < self.tracking_threshold:
                    j = np.argmin(dist_matrix[i])
                    obj_id = object_ids[j]
                    if j not in assigned_objects:
                        self.objects[obj_id].update(detection['center'], self.frame_count)
                        assigned_detections.add(i)
                        assigned_objects.add(j)
        
        # 为未分配的检测创建新目标
        for i, detection in enumerate(detections):
            if i not in assigned_detections:
                self._create_new_object(detection['center'])
        
        # 更新目标状态
        self._update_object_states()
        
        tracking_time = time.time() - start_time
        self.performance_stats['tracking_time'].append(tracking_time)
    
    def _create_new_object(self, position):
        """创建新目标"""
        self.objects[self.next_object_id] = AerialObject(
            self.next_object_id, position, self.frame_count
        )
        self.next_object_id += 1
    
    def _update_object_states(self):
        """更新目标状态"""
        objects_to_remove = []
        
        for obj_id, obj in self.objects.items():
            if obj.status == "active":
                if self.frame_count - obj.last_seen > 10:  # 10帧未检测到
                    obj.status = "lost"
                    obj.lost_count += 1
                elif self.frame_count - obj.last_seen > 30:  # 30帧未检测到
                    obj.status = "removed"
                    objects_to_remove.append(obj_id)
        
        # 移除长时间丢失的目标
        for obj_id in objects_to_remove:
            del self.objects[obj_id]
    
    def analyze_trajectories(self):
        """轨迹分析"""
        trajectories = {}
        
        for obj_id, obj in self.objects.items():
            if obj.status == "active" and len(obj.positions) > 5:
                # 计算运动特征
                positions = list(obj.positions)
                speeds = list(obj.speeds) if obj.speeds else [0]
                directions = list(obj.directions) if obj.directions else [0]
                
                trajectories[obj_id] = {
                    'positions': positions,
                    'avg_speed': np.mean(speeds),
                    'speed_std': np.std(speeds),
                    'direction_consistency': np.std(directions),
                    'classification': obj.classification
                }
        
        return trajectories
    
    def detect_anomalies(self, trajectories):
        """异常行为检测"""
        anomalies = []
        
        for obj_id, traj in trajectories.items():
            # 检测异常速度
            if traj['avg_speed'] > 20:  # 速度过快
                anomalies.append({
                    'object_id': obj_id,
                    'type': 'high_speed',
                    'value': traj['avg_speed']
                })
            
            # 检测异常方向变化
            if traj['direction_consistency'] > 2.0:  # 方向变化过大
                anomalies.append({
                    'object_id': obj_id,
                    'type': 'erratic_movement',
                    'value': traj['direction_consistency']
                })
        
        return anomalies
    
    def visualize_results(self, frame, detections, trajectories, anomalies):
        """可视化结果"""
        result_frame = frame.copy()
        
        # 绘制检测框
        for detection in detections:
            x, y, w, h = detection['bbox']
            cv2.rectangle(result_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
        
        # 绘制目标轨迹和ID
        for obj_id, obj in self.objects.items():
            if obj.status == "active":
                # 绘制轨迹
                positions = list(obj.positions)
                for i in range(1, len(positions)):
                    cv2.line(result_frame, 
                            positions[i-1], positions[i],
                            obj.track_color, 2)
                
                # 绘制当前位置和ID
                current_pos = positions[-1]
                cv2.circle(result_frame, current_pos, 5, obj.track_color, -1)
                cv2.putText(result_frame, f'ID:{obj_id}', 
                           (current_pos[0]+10, current_pos[1]), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, obj.track_color, 2)
                
                # 显示分类信息
                cv2.putText(result_frame, obj.classification,
                           (current_pos[0]+10, current_pos[1]+20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, obj.track_color, 1)
        
        # 标记异常
        for anomaly in anomalies:
            obj_id = anomaly['object_id']
            if obj_id in self.objects:
                obj = self.objects[obj_id]
                pos = obj.positions[-1]
                cv2.putText(result_frame, f"ALERT: {anomaly['type']}",
                           (pos[0]-50, pos[1]-30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        # 显示统计信息
        active_objects = len([obj for obj in self.objects.values() 
                            if obj.status == "active"])
        cv2.putText(result_frame, f'Active Objects: {active_objects}', 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(result_frame, f'Anomalies: {len(anomalies)}', 
                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        return result_frame
    
    def process_frame(self, frame):
        """处理单帧"""
        self.frame_count += 1
        
        # 预处理
        processed_frame = self.preprocess_frame(frame)
        
        # 运动检测
        detections, motion_mask = self.detect_motion(processed_frame)
        
        # 目标跟踪
        self.track_objects(detections)
        
        # 轨迹分析
        trajectories = self.analyze_trajectories()
        
        # 异常检测
        anomalies = self.detect_anomalies(trajectories)
        
        # 可视化
        result_frame = self.visualize_results(frame, detections, trajectories, anomalies)
        
        # 更新性能统计
        self.performance_stats['objects_count'].append(
            len([obj for obj in self.objects.values() if obj.status == "active"])
        )
        
        return result_frame, motion_mask, trajectories, anomalies

def main():
    """主函数"""
    # 初始化系统
    eagle_vision = EagleVisionSystem()
    
    # 创建视频捕获对象（使用摄像头或视频文件）
    # cap = cv2.VideoCapture(0)  # 使用摄像头
    cap = cv2.VideoCapture(0)  # 使用视频文件
    
    # 如果没有视频文件，创建一个模拟视频
    if not cap.isOpened():
        print("创建模拟视频...")
        cap = create_simulation_video()
    
    # 创建窗口
    cv2.namedWindow('Eagle Vision System', cv2.WINDOW_NORMAL)
    
    print("启动鹰眼视觉系统...")
    print("按 'q' 退出，按 'p' 暂停")
    
    paused = False
    
    while True:
        if not paused:
            ret, frame = cap.read()
            if not ret:
                print("视频结束")
                break
            
            # 处理帧
            result_frame, motion_mask, trajectories, anomalies = eagle_vision.process_frame(frame)
            
            # 显示结果
            cv2.imshow('Eagle Vision System', result_frame)
            cv2.imshow('Motion Detection', motion_mask)
        
        # 键盘控制
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('p'):
            paused = not paused
        elif key == ord('s'):
            # 保存当前帧
            cv2.imwrite(f'capture_{eagle_vision.frame_count}.jpg', result_frame)
            print("截图已保存")
    
    # 释放资源
    cap.release()
    cv2.destroyAllWindows()
    
    # 生成性能报告
    generate_performance_report(eagle_vision)

def create_simulation_video():
    """创建模拟空中交通视频"""
    width, height = 800, 600
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter('simulation.avi', fourcc, 20.0, (width, height))
    
    # 创建背景
    background = np.ones((height, width, 3), dtype=np.uint8) * 150
    
    # 模拟多个移动目标
    objects = [
        {'pos': [100, 100], 'velocity': [3, 2], 'size': 20, 'color': (255, 0, 0)},
        {'pos': [200, 300], 'velocity': [2, -1], 'size': 15, 'color': (0, 255, 0)},
        {'pos': [400, 200], 'velocity': [-2, 3], 'size': 25, 'color': (0, 0, 255)},
        {'pos': [600, 400], 'velocity': [1, -2], 'size': 18, 'color': (255, 255, 0)},
    ]
    
    for frame_idx in range(300):  # 生成300帧
        frame = background.copy()
        
        # 添加一些噪声和云层
        noise = np.random.randint(0, 50, (height, width, 3), dtype=np.uint8)
        frame = cv2.add(frame, noise)
        
        # 更新和绘制目标
        for obj in objects:
            # 更新位置
            obj['pos'][0] += obj['velocity'][0]
            obj['pos'][1] += obj['velocity'][1]
            
            # 边界检查
            if obj['pos'][0] < 0 or obj['pos'][0] > width:
                obj['velocity'][0] *= -1
            if obj['pos'][1] < 0 or obj['pos'][1] > height:
                obj['velocity'][1] *= -1
            
            # 绘制目标
            x, y = int(obj['pos'][0]), int(obj['pos'][1])
            size = obj['size']
            cv2.circle(frame, (x, y), size, obj['color'], -1)
            cv2.circle(frame, (x, y), size, (255, 255, 255), 2)
        
        out.write(frame)
    
    out.release()
    
    # 重新打开生成的视频
    return cv2.VideoCapture('simulation.avi')

def generate_performance_report(system):
    """生成性能报告"""
    print("\n" + "="*50)
    print("鹰眼视觉系统性能报告")
    print("="*50)
    
    if system.performance_stats['detection_time']:
        avg_detection = np.mean(system.performance_stats['detection_time'])
        avg_tracking = np.mean(system.performance_stats['tracking_time'])
        max_objects = np.max(system.performance_stats['objects_count'])
        
        print(f"平均检测时间: {avg_detection*1000:.2f} ms")
        print(f"平均跟踪时间: {avg_tracking*1000:.2f} ms")
        print(f"最大同时跟踪目标数: {max_objects}")
        print(f"总处理帧数: {system.frame_count}")
        print(f"跟踪目标总数: {system.next_object_id}")
    
    # 绘制性能图表
    plt.figure(figsize=(12, 8))
    
    plt.subplot(2, 2, 1)
    plt.plot(system.performance_stats['detection_time'])
    plt.title('Detection Time per Frame')
    plt.ylabel('Time (s)')
    plt.xlabel('Frame')
    
    plt.subplot(2, 2, 2)
    plt.plot(system.performance_stats['tracking_time'])
    plt.title('Tracking Time per Frame')
    plt.ylabel('Time (s)')
    plt.xlabel('Frame')
    
    plt.subplot(2, 2, 3)
    plt.plot(system.performance_stats['objects_count'])
    plt.title('Active Objects Count')
    plt.ylabel('Count')
    plt.xlabel('Frame')
    
    plt.tight_layout()
    plt.savefig('performance_report.png')
    print("性能报告已保存为 'performance_report.png'")

if __name__ == "__main__":
    main()