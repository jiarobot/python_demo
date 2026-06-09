import cv2
import numpy as np
import argparse
import time
from collections import deque, defaultdict
import json
import os
from datetime import datetime

class OptimizedMotionDetector:
    def __init__(self, min_area=500, show_mask=True, enable_tracking=True,
                 adaptive_sensitivity=True, use_gpu=False):
        """
        优化版运动检测器 - 平衡性能和准确性
        
        参数:
            min_area: 最小检测区域
            show_mask: 显示前景掩模
            enable_tracking: 启用物体跟踪
            adaptive_sensitivity: 自适应灵敏度
            use_gpu: 使用GPU加速
        """
        self.min_area = min_area
        self.show_mask = show_mask
        self.enable_tracking = enable_tracking
        self.adaptive_sensitivity = adaptive_sensitivity
        self.use_gpu = use_gpu
        
        # 初始化背景减除器 - 使用更稳定的参数
        self.backSub = cv2.createBackgroundSubtractorKNN(
            history=500,
            dist2Threshold=400,
            detectShadows=True
        )
        
        # 形态学内核 - 优化大小和形状
        self.kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        self.kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        
        # 跟踪相关
        self.track_history = defaultdict(lambda: deque(maxlen=20))
        self.next_id = 0
        self.track_colors = {}
        
        # 自适应参数
        self.sensitivity = 1.0
        self.noise_level = 0.0
        self.frame_count = 0
        
        # 性能优化
        self.last_frame_time = time.time()
        self.processing_times = deque(maxlen=30)
        
        # 统计
        self.stats = {
            'total_frames': 0,
            'motion_frames': 0,
            'detected_objects': 0
        }
        
        print("优化版运动检测器初始化完成")
        if use_gpu:
            print("GPU加速: 启用")

    def adaptive_preprocessing(self, frame):
        """自适应预处理"""
        # 降噪 - 根据噪声水平调整
        if self.noise_level > 0.1:
            frame = cv2.GaussianBlur(frame, (3, 3), 0)
        
        # 自适应对比度增强
        if len(frame.shape) == 3:
            lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
            lab[:,:,0] = cv2.createCLAHE(clipLimit=2.0).apply(lab[:,:,0])
            frame = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        
        return frame

    def smart_morphology(self, fg_mask):
        """智能形态学处理"""
        # 二值化
        _, binary = cv2.threshold(fg_mask, 200, 255, cv2.THRESH_BINARY)
        
        # 根据噪声水平调整形态学操作
        if self.noise_level > 0.2:
            # 高噪声环境 - 更强的过滤
            binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, self.kernel_open)
            binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, 
                                    cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11)))
        else:
            # 低噪声环境 - 保持更多细节
            binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, self.kernel_open)
            binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, self.kernel_close)
        
        return binary

    def efficient_contour_analysis(self, binary_mask):
        """高效轮廓分析"""
        # 使用RETR_EXTERNAL只检测外部轮廓，提高效率
        contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        valid_contours = []
        bounding_boxes = []
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < self.min_area:
                continue
                
            # 计算边界框
            x, y, w, h = cv2.boundingRect(contour)
            
            # 过滤不合理的长宽比
            aspect_ratio = w / h if h > 0 else 0
            if aspect_ratio < 0.1 or aspect_ratio > 10:
                continue
                
            # 计算中心点
            moments = cv2.moments(contour)
            if moments["m00"] != 0:
                cx = int(moments["m10"] / moments["m00"])
                cy = int(moments["m01"] / moments["m00"])
            else:
                cx, cy = x + w // 2, y + h // 2
            
            valid_contours.append(contour)
            bounding_boxes.append({
                'bbox': (x, y, w, h),
                'center': (cx, cy),
                'area': area,
                'contour': contour
            })
        
        return valid_contours, bounding_boxes

    def fast_object_tracking(self, current_boxes):
        """快速物体跟踪"""
        if not self.enable_tracking or not current_boxes:
            return {}
            
        object_matches = {}
        used_indices = set()
        
        # 第一阶段：匹配现有轨迹
        for obj_id, history in list(self.track_history.items()):
            if len(history) > 0:
                last_center = history[-1]
                best_match = None
                min_distance = float('inf')
                
                for i, box in enumerate(current_boxes):
                    if i in used_indices:
                        continue
                        
                    current_center = box['center']
                    distance = np.sqrt((current_center[0]-last_center[0])**2 + 
                                     (current_center[1]-last_center[1])**2)
                    
                    # 使用动态阈值
                    threshold = 100 * (1.0 + self.noise_level)
                    if distance < min_distance and distance < threshold:
                        min_distance = distance
                        best_match = i
                
                if best_match is not None:
                    object_matches[obj_id] = best_match
                    used_indices.add(best_match)
                    self.track_history[obj_id].append(current_boxes[best_match]['center'])
        
        # 第二阶段：为新检测分配ID
        for i, box in enumerate(current_boxes):
            if i not in used_indices:
                new_id = self.next_id
                self.next_id += 1
                object_matches[new_id] = i
                self.track_history[new_id].append(box['center'])
                self.track_colors[new_id] = (
                    np.random.randint(50, 255),
                    np.random.randint(50, 255),
                    np.random.randint(50, 255)
                )
        
        # 清理丢失的轨迹
        self.cleanup_tracks()
        
        return object_matches

    def cleanup_tracks(self):
        """清理丢失的轨迹"""
        lost_tracks = []
        for obj_id in list(self.track_history.keys()):
            if len(self.track_history[obj_id]) == 0:
                lost_tracks.append(obj_id)
        
        for obj_id in lost_tracks:
            del self.track_history[obj_id]
            if obj_id in self.track_colors:
                del self.track_colors[obj_id]

    def update_adaptive_parameters(self, motion_mask, num_objects):
        """更新自适应参数"""
        # 计算噪声水平（基于运动掩模中的小区域数量）
        contours, _ = cv2.findContours(motion_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        small_areas = sum(1 for c in contours if cv2.contourArea(c) < self.min_area)
        total_areas = len(contours)
        
        if total_areas > 0:
            self.noise_level = small_areas / total_areas
        
        # 自适应灵敏度调整
        if self.adaptive_sensitivity:
            if self.noise_level > 0.3:
                self.sensitivity = max(0.5, self.sensitivity * 0.95)
            elif num_objects == 0 and self.noise_level < 0.1:
                self.sensitivity = min(2.0, self.sensitivity * 1.05)

    def draw_optimized_detections(self, frame, boxes, object_matches):
        """优化绘制检测结果"""
        motion_detected = False
        
        for obj_id, box_idx in object_matches.items():
            if box_idx < len(boxes):
                box_data = boxes[box_idx]
                x, y, w, h = box_data['bbox']
                
                # 获取跟踪颜色
                color = self.track_colors.get(obj_id, (0, 255, 0))
                
                # 绘制边界框
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                
                # 绘制ID和中心点
                cv2.circle(frame, box_data['center'], 3, color, -1)
                cv2.putText(frame, f'ID:{obj_id}', (x, y-5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                
                # 绘制轨迹（限制轨迹长度以提高性能）
                if obj_id in self.track_history:
                    points = list(self.track_history[obj_id])
                    # 只绘制最近的点
                    for i in range(max(1, len(points)-5), len(points)):
                        if i > 0:
                            cv2.line(frame, points[i-1], points[i], color, 1)
                
                motion_detected = True
        
        return motion_detected

    def process_frame_optimized(self, frame):
        """优化帧处理"""
        start_time = time.time()
        self.frame_count += 1
        
        # 1. 自适应预处理
        processed_frame = self.adaptive_preprocessing(frame)
        
        # 2. 背景减除
        learning_rate = 0.005 * self.sensitivity
        fg_mask = self.backSub.apply(processed_frame, learningRate=learning_rate)
        
        # 3. 智能形态学处理
        binary_mask = self.smart_morphology(fg_mask)
        
        # 4. 轮廓分析
        contours, boxes = self.efficient_contour_analysis(binary_mask)
        
        # 5. 物体跟踪
        object_matches = self.fast_object_tracking(boxes)
        
        # 6. 绘制结果
        result_frame = frame.copy()
        motion_detected = self.draw_optimized_detections(result_frame, boxes, object_matches)
        
        # 7. 显示掩模
        if self.show_mask:
            mask_display = cv2.cvtColor(binary_mask, cv2.COLOR_GRAY2BGR)
            # 调整掩模大小以匹配原帧（如果分辨率不同）
            if mask_display.shape != result_frame.shape:
                mask_display = cv2.resize(mask_display, 
                                        (result_frame.shape[1], result_frame.shape[0]))
            result_frame = np.hstack((result_frame, mask_display))
        
        # 8. 更新自适应参数
        self.update_adaptive_parameters(binary_mask, len(boxes))
        
        # 9. 性能统计
        processing_time = time.time() - start_time
        self.processing_times.append(processing_time)
        
        self.stats['total_frames'] += 1
        if motion_detected:
            self.stats['motion_frames'] += 1
        self.stats['detected_objects'] = len(boxes)
        
        return result_frame, motion_detected, len(boxes)

    def get_performance_stats(self):
        """获取性能统计"""
        if len(self.processing_times) > 0:
            avg_time = np.mean(self.processing_times)
            fps = 1.0 / avg_time if avg_time > 0 else 0
        else:
            avg_time = 0
            fps = 0
            
        return {
            'fps': fps,
            'avg_processing_time_ms': avg_time * 1000,
            'total_frames': self.stats['total_frames'],
            'motion_frames': self.stats['motion_frames'],
            'motion_ratio': (self.stats['motion_frames'] / self.stats['total_frames'] * 100) 
                            if self.stats['total_frames'] > 0 else 0,
            'current_objects': self.stats['detected_objects'],
            'sensitivity': self.sensitivity,
            'noise_level': self.noise_level,
            'active_tracks': len(self.track_history)
        }

class MotionAnalyzer:
    """运动分析器 - 提供高级分析功能"""
    def __init__(self):
        self.motion_history = deque(maxlen=100)
        self.zone_alerts = {}
        
    def analyze_motion_patterns(self, objects, frame_shape):
        """分析运动模式"""
        analysis = {
            'total_motion': len(objects),
            'motion_zones': self.detect_motion_zones(objects, frame_shape),
            'movement_trend': self.calculate_movement_trend(objects)
        }
        
        self.motion_history.append(analysis)
        return analysis
    
    def detect_motion_zones(self, objects, frame_shape):
        """检测运动区域"""
        zones = {
            'top_left': 0, 'top_right': 0,
            'bottom_left': 0, 'bottom_right': 0,
            'center': 0
        }
        
        height, width = frame_shape[:2]
        center_x, center_y = width // 2, height // 2
        
        for obj in objects:
            x, y, w, h = obj['bbox']
            obj_center = obj['center']
            
            # 确定物体所在区域
            if obj_center[0] < center_x and obj_center[1] < center_y:
                zones['top_left'] += 1
            elif obj_center[0] >= center_x and obj_center[1] < center_y:
                zones['top_right'] += 1
            elif obj_center[0] < center_x and obj_center[1] >= center_y:
                zones['bottom_left'] += 1
            elif obj_center[0] >= center_x and obj_center[1] >= center_y:
                zones['bottom_right'] += 1
            
            # 检查是否在中心区域
            center_dist = np.sqrt((obj_center[0]-center_x)**2 + (obj_center[1]-center_y)**2)
            if center_dist < min(center_x, center_y) * 0.3:
                zones['center'] += 1
        
        return zones
    
    def calculate_movement_trend(self, objects):
        """计算运动趋势"""
        if len(objects) == 0:
            return "STABLE"
        
        avg_area = np.mean([obj['area'] for obj in objects])
        if avg_area > 5000:
            return "LARGE_MOVEMENT"
        elif avg_area > 1000:
            return "MEDIUM_MOVEMENT"
        else:
            return "SMALL_MOVEMENT"

def main():
    parser = argparse.ArgumentParser(description='高性能实时运动检测系统')
    parser.add_argument('--input', type=str, default='0', 
                       help='输入源: 摄像头ID (如0,1) 或视频文件路径')
    parser.add_argument('--min_area', type=int, default=500,
                       help='最小检测区域面积 (默认: 500)')
    parser.add_argument('--no_mask', action='store_true',
                       help='不显示前景掩模')
    parser.add_argument('--no_tracking', action='store_true',
                       help='禁用物体跟踪')
    parser.add_argument('--fixed_sensitivity', action='store_true',
                       help='使用固定灵敏度')
    parser.add_argument('--resolution', type=str, default='720p',
                       choices=['480p', '720p', '1080p'],
                       help='分辨率设置')
    parser.add_argument('--output_dir', type=str, default='motion_output',
                       help='输出目录')
    
    args = parser.parse_args()
    
    # 分辨率映射
    resolutions = {
        '480p': (640, 480),
        '720p': (1280, 720),
        '1080p': (1920, 1080)
    }
    
    # 初始化视频源
    try:
        input_source = int(args.input)
    except ValueError:
        input_source = args.input
    
    cap = cv2.VideoCapture(input_source)
    
    if not cap.isOpened():
        print(f"错误: 无法打开视频源 {args.input}")
        return
    
    # 设置分辨率
    target_width, target_height = resolutions[args.resolution]
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, target_width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, target_height)
    
    # 获取实际分辨率
    actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    print(f"视频源: {args.input}")
    print(f"分辨率: {actual_width}x{actual_height}")
    print(f"FPS: {fps}")
    
    # 初始化检测器和分析器
    detector = OptimizedMotionDetector(
        min_area=args.min_area,
        show_mask=not args.no_mask,
        enable_tracking=not args.no_tracking,
        adaptive_sensitivity=not args.fixed_sensitivity
    )
    
    analyzer = MotionAnalyzer()
    
    # 性能监控
    start_time = time.time()
    performance_log = deque(maxlen=100)
    
    print("\n=== 高性能实时运动检测系统 ===")
    print("快捷键:")
    print("  'q' - 退出")
    print("  'p' - 暂停/继续")
    print("  'r' - 重置检测器")
    print("  'c' - 清除跟踪")
    print("  '+' - 增加灵敏度")
    print("  '-' - 降低灵敏度")
    print("  's' - 保存当前帧")
    
    paused = False
    show_stats = True
    
    # 创建输出目录
    os.makedirs(args.output_dir, exist_ok=True)
    
    try:
        while True:
            if not paused:
                ret, frame = cap.read()
                if not ret:
                    print("无法读取帧，退出...")
                    break
                
                # 处理帧
                processed_frame, motion_detected, num_objects = detector.process_frame_optimized(frame)
                
                # 运动分析
                motion_analysis = analyzer.analyze_motion_patterns(
                    [{'bbox': (0,0,0,0), 'center': (0,0), 'area': 0}],  # 简化示例
                    frame.shape
                )
                
                # 获取性能统计
                stats = detector.get_performance_stats()
                performance_log.append(stats['fps'])
                
                # 显示统计信息
                if show_stats:
                    stats_text = [
                        f'FPS: {stats["fps"]:.1f}',
                        f'Process: {stats["avg_processing_time_ms"]:.1f}ms',
                        f'Frames: {stats["total_frames"]}',
                        f'Motion: {stats["motion_frames"]} ({stats["motion_ratio"]:.1f}%)',
                        f'Objects: {stats["current_objects"]}',
                        f'Tracks: {stats["active_tracks"]}',
                        f'Sensitivity: {stats["sensitivity"]:.2f}',
                        f'Noise: {stats["noise_level"]:.2f}'
                    ]
                    
                    for i, text in enumerate(stats_text):
                        # 背景阴影提高可读性
                        cv2.putText(processed_frame, text, (12, 30 + i * 25), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3)
                        cv2.putText(processed_frame, text, (10, 28 + i * 25), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                
                # 显示状态
                status = "MOTION DETECTED" if motion_detected else "NO MOTION"
                color = (0, 255, 0) if motion_detected else (0, 0, 255)
                cv2.putText(processed_frame, status, (actual_width-250, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
                
                # 显示分辨率信息
                res_text = f'Resolution: {actual_width}x{actual_height}'
                cv2.putText(processed_frame, res_text, (10, actual_height-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                # 显示结果
                cv2.imshow('Optimized Motion Detection', processed_frame)
            
            # 键盘输入处理
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('p'):
                paused = not paused
                print("暂停" if paused else "继续")
            elif key == ord('r'):
                detector.backSub = cv2.createBackgroundSubtractorKNN(
                    history=500,
                    dist2Threshold=400,
                    detectShadows=True
                )
                print("检测器已重置")
            elif key == ord('c'):
                detector.track_history.clear()
                detector.next_id = 0
                print("跟踪已清除")
            elif key == ord('+'):
                detector.sensitivity = min(2.0, detector.sensitivity * 1.1)
                print(f"灵敏度增加: {detector.sensitivity:.2f}")
            elif key == ord('-'):
                detector.sensitivity = max(0.5, detector.sensitivity * 0.9)
                print(f"灵敏度降低: {detector.sensitivity:.2f}")
            elif key == ord('s'):
                # 保存当前帧
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                filename = os.path.join(args.output_dir, f"frame_{timestamp}.jpg")
                cv2.imwrite(filename, processed_frame)
                print(f"帧已保存: {filename}")
            elif key == ord('d'):
                show_stats = not show_stats
                print("统计显示:" + ("开启" if show_stats else "关闭"))
    
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    
    finally:
        # 释放资源
        cap.release()
        cv2.destroyAllWindows()
        
        # 打印最终统计
        total_time = time.time() - start_time
        final_stats = detector.get_performance_stats()
        
        print(f"\n=== 最终统计 ===")
        print(f"总运行时间: {total_time:.2f}秒")
        print(f"处理帧数: {final_stats['total_frames']}")
        print(f"平均FPS: {final_stats['fps']:.2f}")
        print(f"检测到运动的帧数: {final_stats['motion_frames']}")
        print(f"运动帧比例: {final_stats['motion_ratio']:.2f}%")
        print(f"最大跟踪物体数: {final_stats['active_tracks']}")
        print(f"最终灵敏度: {final_stats['sensitivity']:.2f}")
        
        # 保存统计信息
        stats_filename = os.path.join(args.output_dir, f"stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(stats_filename, 'w') as f:
            json.dump({
                'total_time': total_time,
                'total_frames': final_stats['total_frames'],
                'motion_frames': final_stats['motion_frames'],
                'motion_ratio': final_stats['motion_ratio'],
                'avg_fps': final_stats['fps'],
                'max_tracked_objects': final_stats['active_tracks'],
                'final_sensitivity': final_stats['sensitivity'],
                'min_area': args.min_area,
                'resolution': f"{actual_width}x{actual_height}"
            }, f, indent=2)
        
        print(f"统计信息已保存: {stats_filename}")

if __name__ == "__main__":
    main()