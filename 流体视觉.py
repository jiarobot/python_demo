import numpy as np
import cv2
import time
from typing import Tuple, List, Dict, Any
from collections import deque
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('FluidDetector')

class FixedFluidDetector:
    """
    修复的流体检测器 - 解决图像深度和尺寸问题
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = self._get_config(config)
        self.frame_buffer = deque(maxlen=self.config['frame_buffer_size'])
        self.last_frame_shape = None
        
        # 性能统计
        self.stats = {
            'frame_count': 0,
            'avg_processing_time': 0,
            'fps': 0,
            'last_frame_time': time.time()
        }
        
        logger.info("修复版流体检测器初始化完成")
    
    def _get_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """获取配置参数"""
        default_config = {
            'frame_buffer_size': 3,
            'processing_scale': 0.5,
            'min_flow_magnitude': 0.1,
            'vortex_threshold': 0.15,
            'use_lucas_kanade': True,
            'max_corners': 200,
            'quality_level': 0.01,
            'min_distance': 10,
            'block_size': 3,
            'enable_visualization': True,
            'win_size': (15, 15),  # 窗口大小必须大于2x2
            'max_level': 2
        }
        
        if config:
            default_config.update(config)
        
        # 确保窗口大小有效
        if default_config['win_size'][0] <= 2 or default_config['win_size'][1] <= 2:
            default_config['win_size'] = (15, 15)
            logger.warning("窗口大小无效，已设置为(15, 15)")
        
        return default_config
    
    def ensure_frame_consistency(self, frame1: np.ndarray, frame2: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """确保两帧尺寸和类型一致"""
        # 确保都是灰度图
        if len(frame1.shape) == 3:
            frame1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        if len(frame2.shape) == 3:
            frame2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
        
        # 确保尺寸一致
        if frame1.shape != frame2.shape:
            h1, w1 = frame1.shape
            frame2 = cv2.resize(frame2, (w1, h1))
            logger.warning(f"帧尺寸不匹配: {frame1.shape} vs {frame2.shape}, 已调整")
        
        # 确保都是8位无符号整数
        if frame1.dtype != np.uint8:
            frame1 = (frame1 * 255).astype(np.uint8)
        if frame2.dtype != np.uint8:
            frame2 = (frame2 * 255).astype(np.uint8)
        
        return frame1, frame2
    
    def preprocess_frame(self, frame: np.ndarray) -> np.ndarray:
        """帧预处理 - 返回8位无符号整数"""
        # 调整尺寸
        if self.config['processing_scale'] != 1.0:
            h, w = frame.shape[:2]
            new_w = int(w * self.config['processing_scale'])
            new_h = int(h * self.config['processing_scale'])
            processed = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
        else:
            processed = frame.copy()
        
        # 转换为灰度并确保是8位无符号整数
        if len(processed.shape) == 3:
            processed = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
        
        # 确保是8位无符号整数
        if processed.dtype != np.uint8:
            if processed.dtype == np.float32 or processed.dtype == np.float64:
                processed = (np.clip(processed, 0, 1) * 255).astype(np.uint8)
            else:
                processed = processed.astype(np.uint8)
        
        return processed
    
    def lucas_kanade_optical_flow(self, prev_frame: np.ndarray, curr_frame: np.ndarray) -> Dict[str, Any]:
        """
        使用Lucas-Kanade方法计算稀疏光流
        修复了图像深度和窗口大小问题
        """
        try:
            # 确保尺寸和类型一致
            prev_frame, curr_frame = self.ensure_frame_consistency(prev_frame, curr_frame)
            
            # 检查窗口大小
            win_size = self.config['win_size']
            if win_size[0] <= 2 or win_size[1] <= 2:
                win_size = (15, 15)
                logger.warning(f"无效窗口大小，使用默认值: {win_size}")
            
            # 检测特征点
            prev_pts = cv2.goodFeaturesToTrack(
                prev_frame,
                maxCorners=self.config['max_corners'],
                qualityLevel=self.config['quality_level'],
                minDistance=self.config['min_distance'],
                blockSize=self.config['block_size']
            )
            
            if prev_pts is None:
                return {
                    'flow_vectors': np.array([]),
                    'prev_points': np.array([]),
                    'curr_points': np.array([]),
                    'status': np.array([])
                }
            
            # 计算光流 - 使用正确的参数
            curr_pts, status, _ = cv2.calcOpticalFlowPyrLK(
                prev_frame, 
                curr_frame, 
                prev_pts, 
                None,
                winSize=win_size,
                maxLevel=self.config['max_level'],
                criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03)
            )
            
            # 过滤有效点
            if status is not None and np.sum(status) > 0:
                good_prev = prev_pts[status == 1]
                good_curr = curr_pts[status == 1]
                flow_vectors = good_curr - good_prev
            else:
                good_prev = np.array([])
                good_curr = np.array([])
                flow_vectors = np.array([])
            
            return {
                'flow_vectors': flow_vectors,
                'prev_points': good_prev,
                'curr_points': good_curr,
                'status': status
            }
            
        except Exception as e:
            logger.error(f"Lucas-Kanade光流计算错误: {e}")
            return {
                'flow_vectors': np.array([]),
                'prev_points': np.array([]),
                'curr_points': np.array([]),
                'status': np.array([])
            }
    
    def dense_optical_flow_fallback(self, prev_frame: np.ndarray, curr_frame: np.ndarray) -> np.ndarray:
        """
        稠密光流备选方案 - 修复了图像深度问题
        """
        try:
            # 确保尺寸和类型一致
            prev_frame, curr_frame = self.ensure_frame_consistency(prev_frame, curr_frame)
            
            # 使用更保守的参数
            flow = cv2.calcOpticalFlowFarneback(
                prev_frame, curr_frame, None,
                pyr_scale=0.5,
                levels=2,
                winsize=10,
                iterations=2,
                poly_n=5,
                poly_sigma=1.1,
                flags=0
            )
            
            return flow
            
        except Exception as e:
            logger.error(f"稠密光流计算错误: {e}")
            # 返回空的流场
            h, w = prev_frame.shape
            return np.zeros((h, w, 2), dtype=np.float32)
    
    def calculate_vorticity_from_sparse_flow(self, flow_data: Dict[str, Any], frame_shape: Tuple[int, int]) -> np.ndarray:
        """从稀疏光流计算涡度场"""
        h, w = frame_shape
        vorticity = np.zeros((h, w), dtype=np.float32)
        
        if len(flow_data['flow_vectors']) == 0:
            return vorticity
        
        prev_points = flow_data['prev_points']
        flow_vectors = flow_data['flow_vectors']
        
        # 为每个点计算局部涡度
        for i in range(len(prev_points)):
            point = prev_points[i]
            vector = flow_vectors[i]
            
            x, y = int(point[0]), int(point[1])
            
            if 1 <= x < w-1 and 1 <= y < h-1:
                # 简单的局部梯度计算
                dx = vector[0]
                dy = vector[1]
                
                # 近似涡度 (dv/dx - du/dy)
                vorticity[y, x] = abs(dx - dy)
        
        # 高斯平滑
        if np.any(vorticity):
            vorticity = cv2.GaussianBlur(vorticity, (5, 5), 1.5)
        
        return vorticity
    
    def detect_vortex_regions(self, vorticity: np.ndarray) -> np.ndarray:
        """检测涡旋区域"""
        if not np.any(vorticity):
            return np.zeros_like(vorticity, dtype=bool)
        
        # 阈值处理
        vortex_mask = vorticity > self.config['vortex_threshold']
        
        # 形态学操作
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        vortex_mask = cv2.morphologyEx(vortex_mask.astype(np.uint8), cv2.MORPH_CLOSE, kernel)
        
        return vortex_mask.astype(bool)
    
    def analyze_flow_patterns(self, flow_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析流动模式"""
        if len(flow_data['flow_vectors']) == 0:
            return {
                'mean_velocity': 0,
                'flow_consistency': 0,
                'turbulence_level': 0,
                'dominant_direction': 0,
                'feature_count': 0
            }
        
        vectors = flow_data['flow_vectors']
        
        # 计算速度大小
        velocities = np.sqrt(vectors[:, 0]**2 + vectors[:, 1]**2)
        mean_velocity = np.mean(velocities)
        
        # 计算流动一致性（向量方向的一致性）
        directions = np.arctan2(vectors[:, 1], vectors[:, 0])
        direction_std = np.std(directions)
        flow_consistency = 1.0 / (1.0 + direction_std)  # 标准差越小，一致性越高
        
        # 湍流水平（速度变化）
        turbulence_level = np.std(velocities) / (mean_velocity + 1e-8)
        
        # 主导方向
        dominant_direction = np.arctan2(np.mean(vectors[:, 1]), np.mean(vectors[:, 0]))
        
        return {
            'mean_velocity': float(mean_velocity),
            'flow_consistency': float(flow_consistency),
            'turbulence_level': float(turbulence_level),
            'dominant_direction': float(dominant_direction),
            'feature_count': len(vectors)
        }
    
    def process_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        """处理单帧"""
        start_time = time.time()
        
        try:
            # 预处理 - 确保返回8位无符号整数
            processed_frame = self.preprocess_frame(frame)
            current_shape = processed_frame.shape
            
            result = {
                'timestamp': time.time(),
                'frame_shape': current_shape,
                'features_detected': False,
                'processing_time': 0,
                'frame_dtype': str(processed_frame.dtype)
            }
            
            # 如果有前一帧，计算光流
            if len(self.frame_buffer) > 0:
                prev_frame = self.frame_buffer[-1]
                
                # 选择光流方法
                if self.config['use_lucas_kanade']:
                    flow_data = self.lucas_kanade_optical_flow(prev_frame, processed_frame)
                    
                    # 分析流动模式
                    flow_analysis = self.analyze_flow_patterns(flow_data)
                    result.update(flow_analysis)
                    
                    # 计算涡度
                    vorticity = self.calculate_vorticity_from_sparse_flow(flow_data, current_shape)
                    
                    # 检测涡旋
                    vortex_mask = self.detect_vortex_regions(vorticity)
                    
                    result.update({
                        'flow_data': flow_data,
                        'vorticity_map': vorticity,
                        'vortex_mask': vortex_mask,
                        'vortex_count': int(np.sum(vortex_mask)),
                        'features_detected': len(flow_data['flow_vectors']) > 0
                    })
                else:
                    # 使用稠密光流
                    flow = self.dense_optical_flow_fallback(prev_frame, processed_frame)
                    
                    # 计算基本统计
                    flow_magnitude = np.sqrt(flow[..., 0]**2 + flow[..., 1]**2)
                    mean_velocity = np.mean(flow_magnitude)
                    
                    result.update({
                        'dense_flow': flow,
                        'mean_velocity': float(mean_velocity),
                        'features_detected': mean_velocity > self.config['min_flow_magnitude']
                    })
            
            # 更新帧缓冲区
            self.frame_buffer.append(processed_frame)
            self.last_frame_shape = current_shape
            
            # 更新统计
            processing_time = time.time() - start_time
            result['processing_time'] = processing_time
            
            self.stats['frame_count'] += 1
            self.stats['avg_processing_time'] = (
                self.stats['avg_processing_time'] * (self.stats['frame_count'] - 1) + processing_time
            ) / self.stats['frame_count']
            
            current_time = time.time()
            time_diff = current_time - self.stats['last_frame_time']
            if time_diff > 0:
                self.stats['fps'] = 1.0 / time_diff
            self.stats['last_frame_time'] = current_time
            
            return result
            
        except Exception as e:
            logger.error(f"帧处理错误: {e}")
            return {
                'timestamp': time.time(),
                'error': str(e),
                'features_detected': False,
                'processing_time': time.time() - start_time
            }

class FixedVisualizer:
    """修复的可视化器"""
    
    def __init__(self):
        self.colors = {
            'flow': (0, 255, 255),  # 青色
            'vortex': (0, 0, 255),   # 红色
            'text': (255, 255, 255), # 白色
            'background': (0, 0, 0)  # 黑色
        }
    
    def draw_analysis_results(self, frame: np.ndarray, analysis: Dict[str, Any]) -> np.ndarray:
        """绘制分析结果"""
        display = frame.copy()
        
        # 绘制光流向量
        if 'flow_data' in analysis and analysis['features_detected']:
            display = self.draw_flow_vectors(display, analysis['flow_data'])
        
        # 绘制涡旋区域
        if 'vortex_mask' in analysis:
            display = self.draw_vortex_regions(display, analysis['vortex_mask'])
        
        # 添加信息面板
        display = self.add_info_panel(display, analysis)
        
        return display
    
    def draw_flow_vectors(self, frame: np.ndarray, flow_data: Dict[str, Any]) -> np.ndarray:
        """绘制光流向量"""
        display = frame.copy()
        
        prev_points = flow_data['prev_points']
        curr_points = flow_data['curr_points']
        
        if len(prev_points) == 0:
            return display
        
        for i in range(len(prev_points)):
            pt1 = (int(prev_points[i][0]), int(prev_points[i][1]))
            pt2 = (int(curr_points[i][0]), int(curr_points[i][1]))
            
            # 绘制箭头
            cv2.arrowedLine(display, pt1, pt2, self.colors['flow'], 1, tipLength=0.3)
            cv2.circle(display, pt1, 2, self.colors['flow'], -1)
        
        return display
    
    def draw_vortex_regions(self, frame: np.ndarray, vortex_mask: np.ndarray) -> np.ndarray:
        """绘制涡旋区域"""
        display = frame.copy()
        
        # 调整掩码尺寸以匹配显示帧
        if vortex_mask.shape != frame.shape[:2]:
            vortex_mask_resized = cv2.resize(
                vortex_mask.astype(np.uint8), 
                (frame.shape[1], frame.shape[0])
            ).astype(bool)
        else:
            vortex_mask_resized = vortex_mask
        
        # 为涡旋区域着色
        vortex_indices = np.where(vortex_mask_resized)
        if len(vortex_indices[0]) > 0:
            display[vortex_indices] = (
                0.7 * display[vortex_indices].astype(np.float32) + 
                0.3 * np.array(self.colors['vortex'], dtype=np.float32)
            ).astype(np.uint8)
        
        return display
    
    def add_info_panel(self, frame: np.ndarray, analysis: Dict[str, Any]) -> np.ndarray:
        """添加信息面板"""
        display = frame.copy()
        h, w = display.shape[:2]
        
        # 创建半透明背景
        panel_height = 120
        overlay = display.copy()
        cv2.rectangle(overlay, (0, h-panel_height), (w, h), self.colors['background'], -1)
        display = cv2.addWeighted(display, 0.7, overlay, 0.3, 0)
        
        # 添加文本信息
        y_pos = h - panel_height + 25
        line_height = 20
        
        info_lines = [
            f"FPS: {1.0/analysis.get('processing_time', 1):.1f}" if analysis.get('processing_time', 0) > 0 else "FPS: Calculating...",
            f"Processing: {analysis.get('processing_time', 0)*1000:.1f}ms",
        ]
        
        if analysis.get('features_detected', False):
            info_lines.extend([
                f"Features: {analysis.get('feature_count', 0)}",
                f"Velocity: {analysis.get('mean_velocity', 0):.3f}",
                f"Vortices: {analysis.get('vortex_count', 0)}",
                f"Consistency: {analysis.get('flow_consistency', 0):.2f}",
                f"Turbulence: {analysis.get('turbulence_level', 0):.3f}"
            ])
        else:
            info_lines.append("No motion detected")
        
        # 添加错误信息（如果有）
        if 'error' in analysis:
            info_lines.append(f"Error: {analysis['error'][:30]}...")
        
        for i, line in enumerate(info_lines):
            cv2.putText(display, line, (10, y_pos + i * line_height),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.colors['text'], 1)
        
        # 状态指示器
        status_color = (0, 255, 0) if analysis.get('features_detected', False) else (0, 0, 255)
        cv2.circle(display, (w - 20, 20), 8, status_color, -1)
        
        return display

def create_test_video(output_path: str = "test_fluid.mp4", duration: int = 5):
    """创建测试视频"""
    print("创建测试视频...")
    
    # 视频参数
    width, height = 640, 480
    fps = 30
    total_frames = duration * fps
    
    # 创建视频写入器
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    # 创建包含流体运动的测试视频
    for frame_idx in range(total_frames):
        # 创建基础图像
        frame = np.ones((height, width, 3), dtype=np.uint8) * 128
        
        # 添加移动的圆形模拟流体
        center_x = width // 2 + int(100 * np.sin(frame_idx * 0.1))
        center_y = height // 2 + int(80 * np.cos(frame_idx * 0.08))
        
        # 绘制移动的圆形
        cv2.circle(frame, (center_x, center_y), 50, (255, 0, 0), -1)
        
        # 添加一些随机噪声模拟湍流
        noise = np.random.randint(0, 50, (height, width, 3), dtype=np.uint8)
        frame = cv2.addWeighted(frame, 0.8, noise, 0.2, 0)
        
        # 写入帧
        out.write(frame)
    
    out.release()
    print(f"测试视频已创建: {output_path}")
    return output_path

def test_with_video_file(video_path: str = None):
    """使用视频文件测试"""
    print("流体检测系统测试")
    print("按 'q' 退出, 按 'p' 暂停/继续, 按 'r' 重置")
    
    # 初始化检测器和可视化器
    detector = FixedFluidDetector({
        'processing_scale': 0.6,
        'use_lucas_kanade': True,
        'max_corners': 150,
        'win_size': (15, 15),
        'max_level': 2
    })
    visualizer = FixedVisualizer()
    
    # 打开视频文件或摄像头
    if video_path:
        cap = cv2.VideoCapture(video_path)
        print(f"使用视频文件: {video_path}")
    else:
        cap = cv2.VideoCapture(0)
        print("使用摄像头")
    
    if not cap.isOpened():
        print("无法打开视频源，创建测试视频...")
        video_path = create_test_video()
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print("无法创建测试视频")
            return
    
    # 设置参数
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    paused = False
    frame_count = 0
    success_count = 0
    
    try:
        while True:
            if not paused:
                ret, frame = cap.read()
                if not ret:
                    print("视频结束")
                    break
                
                # 处理帧
                analysis = detector.process_frame(frame)
                
                # 检查是否成功处理
                if 'error' not in analysis:
                    success_count += 1
                
                # 可视化结果
                display_frame = visualizer.draw_analysis_results(frame, analysis)
                
                # 显示
                cv2.imshow('Fixed Fluid Detection', display_frame)
                
                frame_count += 1
                if frame_count % 30 == 0:
                    success_rate = (success_count / frame_count) * 100
                    print(f"已处理 {frame_count} 帧, 成功率: {success_rate:.1f}%, 平均FPS: {1.0/detector.stats['avg_processing_time']:.1f}")
            
            # 键盘控制
            key = cv2.waitKey(1 if not paused else 0) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('p'):
                paused = not paused
                print("暂停" if paused else "继续")
            elif key == ord('r'):
                # 重置检测器
                detector = FixedFluidDetector()
                frame_count = 0
                success_count = 0
                print("检测器已重置")
    
    except KeyboardInterrupt:
        print("用户中断")
    except Exception as e:
        print(f"运行错误: {e}")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        
        # 打印最终统计
        success_rate = (success_count / frame_count) * 100 if frame_count > 0 else 0
        print(f"\n最终统计:")
        print(f"总帧数: {frame_count}")
        print(f"成功处理: {success_count} ({success_rate:.1f}%)")
        print(f"平均处理时间: {detector.stats['avg_processing_time']*1000:.1f}ms")
        print(f"平均FPS: {1.0/detector.stats['avg_processing_time']:.1f}")

def quick_test():
    """快速测试系统"""
    print("快速测试流体检测系统...")
    
    # 创建测试帧
    width, height = 320, 240
    frame1 = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
    frame2 = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
    
    # 添加一些运动
    frame2[50:100, 50:100] = frame1[50:100, 50:100]
    frame2 = np.roll(frame2, 5, axis=1)  # 水平滚动
    
    # 初始化检测器
    detector = FixedFluidDetector({
        'processing_scale': 0.5,
        'max_corners': 100
    })
    
    # 处理第一帧
    result1 = detector.process_frame(frame1)
    print(f"第一帧处理: {result1.get('features_detected', False)}")
    
    # 处理第二帧
    result2 = detector.process_frame(frame2)
    print(f"第二帧处理: {result2.get('features_detected', False)}")
    
    if result2.get('features_detected', False):
        print(f"检测到 {result2.get('feature_count', 0)} 个特征点")
        print(f"平均速度: {result2.get('mean_velocity', 0):.3f}")
        print(f"涡旋数量: {result2.get('vortex_count', 0)}")
        print("测试成功!")
    else:
        print("测试失败 - 未检测到特征")
    
    return result2.get('features_detected', False)

if __name__ == "__main__":
    print("修复版流体检测系统")
    print("=" * 50)
    
    # 首先运行快速测试
    if quick_test():
        print("\n快速测试成功，开始主测试...")
        print("1. 使用摄像头实时检测")
        print("2. 使用视频文件检测") 
        print("3. 使用测试视频")
        
        choice = input("选择测试模式 (1/2/3): ").strip()
        
        if choice == "1":
            test_with_video_file()
        elif choice == "2":
            video_path = input("输入视频文件路径: ").strip()
            test_with_video_file(video_path)
        elif choice == "3":
            test_with_video_file("test_fluid.mp4")
        else:
            print("使用默认摄像头模式")
            test_with_video_file()
    else:
        print("快速测试失败，请检查OpenCV安装和配置")