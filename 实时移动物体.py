import cv2
import numpy as np
import argparse
import time

class MotionDetector:
    def __init__(self, use_knn=False, min_area=500, show_mask=True):
        """
        初始化运动检测器
        
        参数:
            use_knn: 是否使用KNN背景减除器 (False则使用MOG2)
            min_area: 最小轮廓面积阈值，过滤小噪声
            show_mask: 是否显示前景掩模
        """
        # 创建背景减除器
        if use_knn:
            self.backSub = cv2.createBackgroundSubtractorKNN(
                history=500,        # 用于背景建模的帧数
                dist2Threshold=400, # 距离阈值
                detectShadows=True  # 检测阴影
            )
        else:
            self.backSub = cv2.createBackgroundSubtractorMOG2(
                history=500,        # 用于背景建模的帧数
                varThreshold=16,    # 方差阈值
                detectShadows=True  # 检测阴影
            )
        
        self.min_area = min_area
        self.show_mask = show_mask
        
        # 形态学操作的内核
        self.kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        self.kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        
        print(f"运动检测器初始化完成 - 使用 {'KNN' if use_knn else 'MOG2'} 背景减除器")

    def preprocess_mask(self, fg_mask):
        """
        对前景掩模进行预处理
        
        参数:
            fg_mask: 原始前景掩模
            
        返回:
            处理后的二值图像
        """
        # 1. 二值化处理 - 去除阴影（阴影通常显示为灰色）
        _, binary_mask = cv2.threshold(fg_mask, 200, 255, cv2.THRESH_BINARY)
        
        # 2. 形态学开运算 - 去除小的噪声点
        binary_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_OPEN, self.kernel_open)
        
        # 3. 形态学闭运算 - 填充物体内部的小孔洞
        binary_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_CLOSE, self.kernel_close)
        
        return binary_mask

    def detect_contours(self, binary_mask):
        """
        检测轮廓并过滤
        
        参数:
            binary_mask: 二值掩模图像
            
        返回:
            过滤后的轮廓列表
        """
        # 查找轮廓
        contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 过滤小面积的轮廓
        valid_contours = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > self.min_area:
                valid_contours.append(contour)
                
        return valid_contours

    def draw_detections(self, frame, contours):
        """
        在帧上绘制检测结果
        
        参数:
            frame: 原始视频帧
            contours: 检测到的轮廓列表
        """
        motion_detected = False
        
        for contour in contours:
            # 计算边界矩形
            x, y, w, h = cv2.boundingRect(contour)
            area = cv2.contourArea(contour)
            
            # 绘制边界框
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            # 绘制轮廓
            cv2.drawContours(frame, [contour], -1, (255, 0, 0), 1)
            
            # 显示面积信息
            cv2.putText(frame, f'Area: {int(area)}', (x, y - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            
            motion_detected = True
        
        # 显示状态信息
        status = "Motion Detected!" if motion_detected else "No Motion"
        color = (0, 0, 255) if motion_detected else (255, 255, 255)
        cv2.putText(frame, f'Status: {status}', (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        
        return motion_detected

    def process_frame(self, frame):
        """
        处理单帧图像
        
        参数:
            frame: 输入帧
            
        返回:
            处理后的帧和检测结果
        """
        # 应用背景减除
        fg_mask = self.backSub.apply(frame)
        
        # 预处理掩模
        processed_mask = self.preprocess_mask(fg_mask)
        
        # 检测轮廓
        contours = self.detect_contours(processed_mask)
        
        # 绘制检测结果
        frame_copy = frame.copy()
        motion_detected = self.draw_detections(frame_copy, contours)
        
        # 如果需要显示掩模
        if self.show_mask:
            # 将掩模转换为彩色以便显示
            mask_display = cv2.cvtColor(processed_mask, cv2.COLOR_GRAY2BGR)
            # 水平拼接原帧和掩模
            result_frame = np.hstack((frame_copy, mask_display))
        else:
            result_frame = frame_copy
            
        return result_frame, motion_detected, len(contours)

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='实时运动检测系统')
    parser.add_argument('--input', type=str, default='0', 
                       help='输入源: 摄像头ID (如0,1) 或视频文件路径')
    parser.add_argument('--min_area', type=int, default=500,
                       help='最小检测区域面积 (默认: 500)')
    parser.add_argument('--use_knn', action='store_true',
                       help='使用KNN背景减除器 (默认使用MOG2)')
    parser.add_argument('--no_mask', action='store_true',
                       help='不显示前景掩模')
    
    args = parser.parse_args()
    
    # 初始化视频源
    try:
        # 尝试将输入转换为整数（摄像头ID）
        input_source = int(args.input)
    except ValueError:
        # 如果是字符串，则作为视频文件路径
        input_source = args.input
    
    cap = cv2.VideoCapture(input_source)
    
    if not cap.isOpened():
        print(f"错误: 无法打开视频源 {args.input}")
        return
    
    # 获取视频属性
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print(f"视频源: {args.input}")
    print(f"分辨率: {width}x{height}")
    print(f"FPS: {fps}")
    
    # 初始化运动检测器
    detector = MotionDetector(
        use_knn=args.use_knn,
        min_area=args.min_area,
        show_mask=not args.no_mask
    )
    
    # 性能统计
    frame_count = 0
    motion_frames = 0
    start_time = time.time()
    
    print("开始实时运动检测...")
    print("按 'q' 退出")
    print("按 'p' 暂停/继续")
    print("按 'r' 重置背景模型")
    
    paused = False
    
    while True:
        if not paused:
            ret, frame = cap.read()
            if not ret:
                print("无法读取帧，退出...")
                break
            
            frame_count += 1
            
            # 处理帧
            processed_frame, motion_detected, num_objects = detector.process_frame(frame)
            
            if motion_detected:
                motion_frames += 1
            
            # 显示统计信息
            elapsed_time = time.time() - start_time
            current_fps = frame_count / elapsed_time if elapsed_time > 0 else 0
            motion_ratio = (motion_frames / frame_count) * 100 if frame_count > 0 else 0
            
            stats_text = [
                f'FPS: {current_fps:.1f}',
                f'Frames: {frame_count}',
                f'Motion Frames: {motion_frames} ({motion_ratio:.1f}%)',
                f'Objects: {num_objects}',
                f'Min Area: {args.min_area}'
            ]
            
            for i, text in enumerate(stats_text):
                cv2.putText(processed_frame, text, (10, 60 + i * 25), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # 显示结果
            cv2.imshow('Motion Detection', processed_frame)
        
        # 键盘输入处理
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('p'):
            paused = not paused
            print("暂停" if paused else "继续")
        elif key == ord('r'):
            # 重置背景模型
            detector.backSub = cv2.createBackgroundSubtractorMOG2() if not args.use_knn else cv2.createBackgroundSubtractorKNN()
            print("背景模型已重置")
    
    # 释放资源
    cap.release()
    cv2.destroyAllWindows()
    
    # 打印最终统计
    total_time = time.time() - start_time
    print(f"\n=== 检测统计 ===")
    print(f"总帧数: {frame_count}")
    print(f"检测到运动的帧数: {motion_frames}")
    print(f"运动帧比例: {motion_ratio:.2f}%")
    print(f"总运行时间: {total_time:.2f}秒")
    print(f"平均FPS: {frame_count/total_time:.2f}")

if __name__ == "__main__":
    main()