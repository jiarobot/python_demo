import cv2
import numpy as np
import argparse
import time
import threading
from collections import deque, defaultdict
import json
import os
from datetime import datetime

class EnhancedMotionDetector:
    def __init__(self, use_knn=False, min_area=500, show_mask=True, 
                 enable_tracking=True, enable_classification=False,
                 detection_threshold=0.7, max_track_points=50):
        """
        增强版运动检测器
        
        参数:
            use_knn: 是否使用KNN背景减除器
            min_area: 最小轮廓面积阈值
            show_mask: 是否显示前景掩模
            enable_tracking: 是否启用物体跟踪
            enable_classification: 是否启用物体分类
            detection_threshold: 检测阈值
            max_track_points: 最大跟踪点数
        """
        # 背景减除器
        if use_knn:
            self.backSub = cv2.createBackgroundSubtractorKNN(
                history=1000,
                dist2Threshold=400,
                detectShadows=True
            )
        else:
            self.backSub = cv2.createBackgroundSubtractorMOG2(
                history=1000,
                varThreshold=16,
                detectShadows=True
            )
        
        self.min_area = min_area
        self.show_mask = show_mask
        self.enable_tracking = enable_tracking
        self.enable_classification = enable_classification
        self.detection_threshold = detection_threshold
        self.max_track_points = max_track_points
        
        # 形态学内核
        self.kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        self.kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        self.kernel_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        
        # 物体跟踪相关
        self.track_history = defaultdict(lambda: deque(maxlen=max_track_points))
        self.object_ids = {}
        self.next_object_id = 0
        self.track_colors = {}
        
        # 性能优化
        self.frame_queue = deque(maxlen=3)
        self.processing_lock = threading.Lock()
        self.last_processed_time = time.time()
        
        # 分类器（如果启用）
        if enable_classification:
            self.classifier = self._load_classifier()
        else:
            self.classifier = None
            
        # 统计信息
        self.stats = {
            'total_frames': 0,
            'motion_frames': 0,
            'detected_objects': 0,
            'processing_times': deque(maxlen=100)
        }
        
        print(f"增强版运动检测器初始化完成")
        print(f"跟踪: {'启用' if enable_tracking else '禁用'}")
        print(f"分类: {'启用' if enable_classification else '禁用'}")

    def _load_classifier(self):
        """加载预训练的分类器"""
        try:
            # 尝试加载YOLO或其他分类器
            # 这里使用OpenCV的DNN模块
            net = cv2.dnn.readNetFromDarknet('yolov3.cfg', 'yolov3.weights')
            print("YOLO分类器加载成功")
            return net
        except:
            print("分类器加载失败，继续使用基础检测")
            return None

    def preprocess_frame(self, frame):
        """帧预处理"""
        # 高斯模糊降噪
        blurred = cv2.GaussianBlur(frame, (5, 5), 0)
        
        # 可选：直方图均衡化（改善对比度）
        if len(frame.shape) == 3:
            lab = cv2.cvtColor(blurred, cv2.COLOR_BGR2LAB)
            lab[:,:,0] = cv2.createCLAHE(clipLimit=2.0).apply(lab[:,:,0])
            blurred = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
            
        return blurred

    def extract_foreground(self, frame):
        """提取前景"""
        fg_mask = self.backSub.apply(frame)
        
        # 二值化处理
        _, binary_mask = cv2.threshold(fg_mask, 200, 255, cv2.THRESH_BINARY)
        
        # 形态学操作
        binary_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_OPEN, self.kernel_open)
        binary_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_CLOSE, self.kernel_close)
        binary_mask = cv2.dilate(binary_mask, self.kernel_dilate, iterations=1)
        
        return binary_mask

    def detect_contours(self, binary_mask):
        """检测并过滤轮廓"""
        contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        valid_contours = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > self.min_area:
                # 计算轮廓的宽高比
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h if h > 0 else 0
                
                # 过滤不合理形状
                if 0.1 < aspect_ratio < 10.0:
                    valid_contours.append(contour)
                    
        return valid_contours

    def calculate_motion_features(self, contour):
        """计算运动特征"""
        moments = cv2.moments(contour)
        
        if moments["m00"] != 0:
            cx = int(moments["m10"] / moments["m00"])
            cy = int(moments["m01"] / moments["m00"])
        else:
            x, y, w, h = cv2.boundingRect(contour)
            cx = x + w // 2
            cy = y + h // 2
            
        area = cv2.contourArea(contour)
        perimeter = cv2.arcLength(contour, True)
        circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0
        
        return (cx, cy), area, circularity

    def track_objects(self, current_centers):
        """多目标跟踪"""
        if not self.enable_tracking:
            return list(range(len(current_centers)))
            
        object_matches = {}
        used_centers = set()
        
        # 简单的最近邻跟踪
        for obj_id, history in self.track_history.items():
            if len(history) > 0:
                last_center = history[-1]
                min_distance = float('inf')
                best_match = None
                
                for i, center in enumerate(current_centers):
                    if i not in used_centers:
                        distance = np.sqrt((center[0]-last_center[0])**2 + (center[1]-last_center[1])**2)
                        if distance < min_distance and distance < 100:  # 距离阈值
                            min_distance = distance
                            best_match = i
                
                if best_match is not None:
                    object_matches[obj_id] = best_match
                    used_centers.add(best_match)
                    self.track_history[obj_id].append(current_centers[best_match])
        
        # 为新检测到的物体分配ID
        for i, center in enumerate(current_centers):
            if i not in used_centers:
                new_id = self.next_object_id
                self.next_object_id += 1
                object_matches[new_id] = i
                self.track_history[new_id].append(center)
                # 生成随机颜色用于跟踪
                self.track_colors[new_id] = (
                    np.random.randint(0, 255),
                    np.random.randint(0, 255),
                    np.random.randint(0, 255)
                )
        
        return object_matches

    def classify_object(self, frame, contour):
        """物体分类"""
        if not self.enable_classification or self.classifier is None:
            return "Unknown"
            
        try:
            x, y, w, h = cv2.boundingRect(contour)
            roi = frame[y:y+h, x:x+w]
            
            if roi.size == 0:
                return "Unknown"
                
            # 这里可以添加具体的分类逻辑
            # 暂时返回基于形状的简单分类
            area = cv2.contourArea(contour)
            perimeter = cv2.arcLength(contour, True)
            circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0
            
            if circularity > 0.8:
                return "Round"
            elif w > 2 * h:
                return "Horizontal"
            elif h > 2 * w:
                return "Vertical"
            else:
                return "Rectangular"
                
        except Exception as e:
            return "Unknown"

    def draw_enhanced_detections(self, frame, contours, object_matches, centers):
        """绘制增强的检测结果"""
        motion_detected = False
        
        for obj_id, contour_idx in object_matches.items():
            if contour_idx < len(contours):
                contour = contours[contour_idx]
                center = centers[contour_idx]
                
                # 计算边界框和特征
                x, y, w, h = cv2.boundingRect(contour)
                area = cv2.contourArea(contour)
                
                # 绘制边界框
                color = self.track_colors.get(obj_id, (0, 255, 0))
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                
                # 绘制中心点和轨迹
                cv2.circle(frame, center, 4, color, -1)
                
                # 绘制跟踪轨迹
                if obj_id in self.track_history:
                    points = list(self.track_history[obj_id])
                    for i in range(1, len(points)):
                        cv2.line(frame, points[i-1], points[i], color, 2)
                
                # 物体分类
                obj_type = self.classify_object(frame, contour)
                
                # 显示信息
                info_text = [
                    f'ID: {obj_id}',
                    f'Type: {obj_type}',
                    f'Area: {int(area)}',
                    f'Pos: ({center[0]},{center[1]})'
                ]
                
                for i, text in enumerate(info_text):
                    y_offset = y - 10 - i * 15
                    cv2.putText(frame, text, (x, max(y_offset, 15)), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
                
                motion_detected = True
        
        return motion_detected

    def process_frame_optimized(self, frame):
        """优化版的帧处理"""
        start_time = time.time()
        
        # 预处理
        processed_frame = self.preprocess_frame(frame)
        
        # 提取前景
        binary_mask = self.extract_foreground(processed_frame)
        
        # 检测轮廓
        contours = self.detect_contours(binary_mask)
        
        # 计算特征
        centers = []
        for contour in contours:
            center, area, circularity = self.calculate_motion_features(contour)
            centers.append(center)
        
        # 目标跟踪
        object_matches = self.track_objects(centers)
        
        # 绘制结果
        result_frame = frame.copy()
        motion_detected = self.draw_enhanced_detections(result_frame, contours, object_matches, centers)
        
        # 显示掩模（如果需要）
        if self.show_mask:
            mask_display = cv2.cvtColor(binary_mask, cv2.COLOR_GRAY2BGR)
            result_frame = np.hstack((result_frame, mask_display))
        
        # 性能统计
        processing_time = time.time() - start_time
        self.stats['processing_times'].append(processing_time)
        self.stats['total_frames'] += 1
        if motion_detected:
            self.stats['motion_frames'] += 1
        self.stats['detected_objects'] = len(contours)
        
        return result_frame, motion_detected, len(contours)

    def get_performance_stats(self):
        """获取性能统计"""
        if len(self.stats['processing_times']) > 0:
            avg_time = np.mean(self.stats['processing_times'])
            fps = 1.0 / avg_time if avg_time > 0 else 0
        else:
            avg_time = 0
            fps = 0
            
        return {
            'fps': fps,
            'avg_processing_time': avg_time,
            'total_frames': self.stats['total_frames'],
            'motion_frames': self.stats['motion_frames'],
            'motion_ratio': (self.stats['motion_frames'] / self.stats['total_frames'] * 100) 
                            if self.stats['total_frames'] > 0 else 0,
            'current_objects': self.stats['detected_objects']
        }

class VideoWriterManager:
    """视频写入管理器"""
    def __init__(self, output_dir="output"):
        self.output_dir = output_dir
        self.writer = None
        self.is_recording = False
        os.makedirs(output_dir, exist_ok=True)
    
    def start_recording(self, frame_size, fps=20):
        """开始录制"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.output_dir, f"motion_{timestamp}.avi")
        
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        self.writer = cv2.VideoWriter(filename, fourcc, fps, frame_size)
        self.is_recording = True
        print(f"开始录制: {filename}")
    
    def stop_recording(self):
        """停止录制"""
        if self.writer is not None:
            self.writer.release()
            self.is_recording = False
            print("录制已停止")
    
    def write_frame(self, frame):
        """写入帧"""
        if self.is_recording and self.writer is not None:
            self.writer.write(frame)

def main():
    parser = argparse.ArgumentParser(description='增强版实时运动检测系统')
    parser.add_argument('--input', type=str, default='0', 
                       help='输入源: 摄像头ID (如0,1) 或视频文件路径')
    parser.add_argument('--min_area', type=int, default=500,
                       help='最小检测区域面积 (默认: 500)')
    parser.add_argument('--use_knn', action='store_true',
                       help='使用KNN背景减除器 (默认使用MOG2)')
    parser.add_argument('--no_mask', action='store_true',
                       help='不显示前景掩模')
    parser.add_argument('--no_tracking', action='store_true',
                       help='禁用物体跟踪')
    parser.add_argument('--enable_classification', action='store_true',
                       help='启用物体分类')
    parser.add_argument('--output_dir', type=str, default='output',
                       help='输出目录')
    parser.add_argument('--resolution', type=str, default='HD',
                       choices=['VGA', 'HD', 'FHD', '4K'],
                       help='分辨率设置')
    
    args = parser.parse_args()
    
    # 分辨率映射
    resolutions = {
        'VGA': (640, 480),
        'HD': (1280, 720),
        'FHD': (1920, 1080),
        '4K': (3840, 2160)
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
    
    # 初始化检测器
    detector = EnhancedMotionDetector(
        use_knn=args.use_knn,
        min_area=args.min_area,
        show_mask=not args.no_mask,
        enable_tracking=not args.no_tracking,
        enable_classification=args.enable_classification
    )
    
    # 初始化视频写入器
    video_writer = VideoWriterManager(args.output_dir)
    
    # 性能监控
    performance_history = deque(maxlen=100)
    start_time = time.time()
    
    print("\n=== 增强版实时运动检测系统 ===")
    print("快捷键:")
    print("  'q' - 退出")
    print("  'p' - 暂停/继续")
    print("  'r' - 重置背景模型")
    print("  's' - 开始/停止录制")
    print("  'c' - 清除跟踪历史")
    print("  'd' - 切换调试显示")
    
    paused = False
    show_debug = True
    is_recording = False
    
    try:
        while True:
            if not paused:
                ret, frame = cap.read()
                if not ret:
                    print("无法读取帧，退出...")
                    break
                
                # 处理帧
                processed_frame, motion_detected, num_objects = detector.process_frame_optimized(frame)
                
                # 录制视频（如果检测到运动）
                if motion_detected and not video_writer.is_recording and is_recording:
                    video_writer.start_recording((actual_width, actual_height), fps=20)
                elif not motion_detected and video_writer.is_recording:
                    video_writer.stop_recording()
                
                if video_writer.is_recording:
                    video_writer.write_frame(processed_frame)
                
                # 获取性能统计
                stats = detector.get_performance_stats()
                performance_history.append(stats['fps'])
                
                # 显示统计信息
                if show_debug:
                    stats_text = [
                        f'FPS: {stats["fps"]:.1f}',
                        f'Processing: {stats["avg_processing_time"]*1000:.1f}ms',
                        f'Frames: {stats["total_frames"]}',
                        f'Motion: {stats["motion_frames"]} ({stats["motion_ratio"]:.1f}%)',
                        f'Objects: {stats["current_objects"]}',
                        f'Tracking: {len(detector.track_history)}',
                        f'Recording: {"ON" if video_writer.is_recording else "OFF"}'
                    ]
                    
                    for i, text in enumerate(stats_text):
                        cv2.putText(processed_frame, text, (10, 30 + i * 25), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3)
                        cv2.putText(processed_frame, text, (10, 30 + i * 25), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
                
                # 显示结果
                cv2.imshow('Enhanced Motion Detection', processed_frame)
            
            # 键盘输入处理
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('p'):
                paused = not paused
                print("暂停" if paused else "继续")
            elif key == ord('r'):
                detector.backSub = cv2.createBackgroundSubtractorMOG2() if not args.use_knn else cv2.createBackgroundSubtractorKNN()
                print("背景模型已重置")
            elif key == ord('s'):
                is_recording = not is_recording
                print("录制:" + ("开启" if is_recording else "关闭"))
            elif key == ord('c'):
                detector.track_history.clear()
                detector.next_object_id = 0
                print("跟踪历史已清除")
            elif key == ord('d'):
                show_debug = not show_debug
                print("调试显示:" + ("开启" if show_debug else "关闭"))
    
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    
    finally:
        # 释放资源
        cap.release()
        video_writer.stop_recording()
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
        print(f"最大跟踪物体数: {len(detector.track_history)}")
        
        # 保存统计信息
        stats_filename = os.path.join(args.output_dir, f"stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(stats_filename, 'w') as f:
            json.dump({
                'total_time': total_time,
                'total_frames': final_stats['total_frames'],
                'motion_frames': final_stats['motion_frames'],
                'motion_ratio': final_stats['motion_ratio'],
                'avg_fps': final_stats['fps'],
                'max_tracked_objects': len(detector.track_history)
            }, f, indent=2)
        
        print(f"统计信息已保存: {stats_filename}")

if __name__ == "__main__":
    main()