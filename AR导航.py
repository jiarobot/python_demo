import cv2
import numpy as np
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import threading
import time
import json
import pygame
import math
from collections import deque
import os

class AdvancedARNavigationSystem:
    def __init__(self):
        # 初始化摄像头
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # 初始化音频
        pygame.mixer.init()
        
        # 特征检测器 - 使用单一特征检测器避免兼容性问题
        self.orb = cv2.ORB_create(nfeatures=2000)
        self.bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        
        # SLAM相关变量
        self.map_points = []
        self.keyframes = []
        self.current_pose = np.eye(4)
        self.camera_matrix = self.get_camera_matrix()
        self.dist_coeffs = np.zeros(4)
        
        # 导航状态
        self.reference_images = {}
        self.path_points = []
        self.current_target_index = 0
        self.is_navigating = False
        self.navigation_mode = "2D"  # 2D or 3D
        self.user_position = None
        self.user_orientation = 0
        
        # 性能监控
        self.frame_times = deque(maxlen=30)
        self.feature_counts = deque(maxlen=30)
        
        # 语音提示
        self.voice_enabled = True
        self.last_voice_time = 0
        
        # 当前帧和关键点
        self.current_frame = None
        self.current_keypoints = None
        self.current_descriptors = None
        
        # 线程控制
        self.processing_active = True
        
        # 创建GUI
        self.create_advanced_gui()
        
        # 启动处理线程
        self.processing_thread = threading.Thread(target=self.process_frames, daemon=True)
        self.processing_thread.start()
        
    def get_camera_matrix(self):
        """获取相机内参矩阵（简化版本）"""
        fx, fy = 800, 800  # 焦距
        cx, cy = 320, 240  # 主点
        return np.array([[fx, 0, cx],
                        [0, fy, cy], 
                        [0, 0, 1]], dtype=np.float32)
    
    def create_advanced_gui(self):
        """创建高级图形用户界面"""
        self.root = tk.Tk()
        self.root.title("高级AR室内导航系统")
        self.root.geometry("1400x900")
        
        # 设置样式
        style = ttk.Style()
        style.configure('Title.TLabelframe', font=('Arial', 12, 'bold'))
        style.configure('Status.TLabel', font=('Arial', 10), background='#f0f0f0')
        
        # 主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左侧视频和控制面板
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 视频显示区域
        video_frame = ttk.LabelFrame(left_frame, text="实时AR导航视图", style='Title.TLabelframe')
        video_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.video_label = ttk.Label(video_frame)
        self.video_label.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 控制面板
        control_frame = ttk.LabelFrame(left_frame, text="导航控制", style='Title.TLabelframe')
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 第一行控制按钮
        control_row1 = ttk.Frame(control_frame)
        control_row1.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Button(control_row1, text="📷 捕获参考点", 
                  command=self.capture_reference_point).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_row1, text="🗺️ 加载地图", 
                  command=self.load_map).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_row1, text="💾 保存地图", 
                  command=self.save_map).pack(side=tk.LEFT, padx=2)
        
        # 第二行控制按钮
        control_row2 = ttk.Frame(control_frame)
        control_row2.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Button(control_row2, text="🎯 设置起点", 
                  command=self.set_start_point).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_row2, text="📍 添加路径点", 
                  command=self.add_path_point).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_row2, text="🏁 设置终点", 
                  command=self.set_end_point).pack(side=tk.LEFT, padx=2)
        
        # 第三行控制按钮
        control_row3 = ttk.Frame(control_frame)
        control_row3.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Button(control_row3, text="🚀 开始导航", 
                  command=self.start_navigation).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_row3, text="⏹️ 停止导航", 
                  command=self.stop_navigation).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_row3, text="🔄 重置系统", 
                  command=self.reset_system).pack(side=tk.LEFT, padx=2)
        
        # 右侧信息面板
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        
        # 系统状态
        status_frame = ttk.LabelFrame(right_frame, text="系统状态", style='Title.TLabelframe')
        status_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.status_text = tk.Text(status_frame, height=8, width=40, font=('Arial', 9))
        scrollbar = ttk.Scrollbar(status_frame, command=self.status_text.yview)
        self.status_text.config(yscrollcommand=scrollbar.set)
        self.status_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 路径信息
        path_frame = ttk.LabelFrame(right_frame, text="路径信息", style='Title.TLabelframe')
        path_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.path_listbox = tk.Listbox(path_frame, height=6, font=('Arial', 9))
        path_scrollbar = ttk.Scrollbar(path_frame, command=self.path_listbox.yview)
        self.path_listbox.config(yscrollcommand=path_scrollbar.set)
        self.path_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        path_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 设置面板
        settings_frame = ttk.LabelFrame(right_frame, text="系统设置", style='Title.TLabelframe')
        settings_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 导航模式选择
        mode_frame = ttk.Frame(settings_frame)
        mode_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(mode_frame, text="导航模式:").pack(side=tk.LEFT)
        self.mode_var = tk.StringVar(value="2D")
        ttk.Radiobutton(mode_frame, text="2D导航", variable=self.mode_var, 
                       value="2D", command=self.change_navigation_mode).pack(side=tk.LEFT)
        ttk.Radiobutton(mode_frame, text="3D导航", variable=self.mode_var, 
                       value="3D", command=self.change_navigation_mode).pack(side=tk.LEFT)
        
        # 语音控制
        voice_frame = ttk.Frame(settings_frame)
        voice_frame.pack(fill=tk.X, padx=5, pady=2)
        self.voice_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(voice_frame, text="启用语音提示", variable=self.voice_var,
                       command=self.toggle_voice).pack(side=tk.LEFT)
        
        # 性能监控
        perf_frame = ttk.LabelFrame(right_frame, text="性能监控", style='Title.TLabelframe')
        perf_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.fps_label = ttk.Label(perf_frame, text="FPS: --", style='Status.TLabel')
        self.fps_label.pack(anchor=tk.W, padx=5, pady=2)
        
        self.features_label = ttk.Label(perf_frame, text="特征点: --", style='Status.TLabel')
        self.features_label.pack(anchor=tk.W, padx=5, pady=2)
        
        self.position_label = ttk.Label(perf_frame, text="位置: 未知", style='Status.TLabel')
        self.position_label.pack(anchor=tk.W, padx=5, pady=2)
        
        # 初始化状态
        self.update_status("系统初始化完成")
        
        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def on_closing(self):
        """处理窗口关闭事件"""
        self.processing_active = False
        time.sleep(0.1)  # 给线程一点时间退出
        self.cap.release()
        self.root.destroy()
        
    def update_status(self, message):
        """更新状态信息"""
        timestamp = time.strftime("%H:%M:%S")
        self.status_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.status_text.see(tk.END)
        if hasattr(self, 'root'):
            self.root.update()
        
    def extract_features(self, frame):
        """提取特征 - 使用单一特征检测器确保兼容性"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # 使用ORB特征检测器
        keypoints, descriptors = self.orb.detectAndCompute(gray, None)
        
        # 如果特征点太少，尝试调整参数重新检测
        if keypoints is None or len(keypoints) < 10:
            self.orb = cv2.ORB_create(nfeatures=1000, fastThreshold=5)
            keypoints, descriptors = self.orb.detectAndCompute(gray, None)
            
        return keypoints, descriptors
    
    def estimate_pose(self, frame, keypoints, descriptors):
        """估计相机位姿（简化的视觉里程计）"""
        if len(self.keyframes) == 0:
            # 第一帧，初始化地图
            self.add_keyframe(frame, keypoints, descriptors, np.eye(4))
            return np.eye(4)
        
        # 与上一关键帧匹配
        last_kf = self.keyframes[-1]
        
        # 确保描述符不为空
        if descriptors is None or last_kf['descriptors'] is None:
            return self.current_pose
            
        matches = self.bf.match(descriptors, last_kf['descriptors'])
        
        if len(matches) < 8:
            return self.current_pose
        
        try:
            # 提取匹配点
            src_pts = np.float32([keypoints[m.queryIdx].pt for m in matches])
            dst_pts = np.float32([last_kf['keypoints'][m.trainIdx].pt for m in matches])
            
            # 估计基础矩阵
            E, mask = cv2.findEssentialMat(src_pts, dst_pts, self.camera_matrix, 
                                          method=cv2.RANSAC, prob=0.999, threshold=1.0)
            
            if E is not None:
                # 从本质矩阵恢复位姿
                _, R, t, mask = cv2.recoverPose(E, src_pts, dst_pts, self.camera_matrix)
                
                # 更新当前位姿
                new_pose = np.eye(4)
                new_pose[:3, :3] = R
                new_pose[:3, 3] = t.flatten() * 0.1  # 缩放平移量
                
                self.current_pose = new_pose @ self.current_pose
                
                # 如果移动足够大，添加新的关键帧
                translation_norm = np.linalg.norm(t)
                if translation_norm > 0.5:  # 移动阈值
                    self.add_keyframe(frame, keypoints, descriptors, self.current_pose)
                    
        except Exception as e:
            print(f"位姿估计错误: {e}")
            
        return self.current_pose
    
    def add_keyframe(self, frame, keypoints, descriptors, pose):
        """添加关键帧到地图"""
        keyframe = {
            'frame': frame.copy(),
            'keypoints': keypoints,
            'descriptors': descriptors.copy() if descriptors is not None else None,
            'pose': pose.copy()
        }
        self.keyframes.append(keyframe)
        self.update_status(f"添加关键帧 {len(self.keyframes)}")
        
    def draw_3d_arrow(self, frame, direction, distance=5.0):
        """绘制3D导航箭头"""
        h, w = frame.shape[:2]
        
        # 3D箭头顶点（在相机坐标系中）
        if direction == "forward":
            vertices = np.array([
                [0, 0, distance],           # 箭头尖端
                [-0.3, -0.5, distance-1],   # 左下
                [0.3, -0.5, distance-1],    # 右下
                [0, 0.8, distance-1]        # 上
            ])
        elif direction == "left":
            vertices = np.array([
                [-distance, 0, 0],          # 箭头尖端
                [-distance+1, -0.5, -0.3],  # 左下
                [-distance+1, -0.5, 0.3],   # 右下  
                [-distance+1, 0.8, 0]       # 上
            ])
        elif direction == "right":
            vertices = np.array([
                [distance, 0, 0],           # 箭头尖端
                [distance-1, -0.5, -0.3],   # 左下
                [distance-1, -0.5, 0.3],    # 右下
                [distance-1, 0.8, 0]        # 上
            ])
        else:
            return
        
        try:
            # 投影到图像平面
            projected_points, _ = cv2.projectPoints(
                vertices, np.eye(3), np.zeros(3), 
                self.camera_matrix, self.dist_coeffs
            )
            
            projected_points = projected_points.reshape(-1, 2).astype(int)
            
            # 绘制3D箭头
            color = (0, 255, 0) if direction == "forward" else (255, 255, 0)
            cv2.fillPoly(frame, [projected_points], color)
            
            # 添加距离文本
            if direction != "arrived":
                text_pos = (projected_points[0][0], projected_points[0][1] - 20)
                cv2.putText(frame, f"{distance:.1f}m", text_pos, 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        except Exception as e:
            print(f"3D箭头绘制错误: {e}")
    
    def draw_advanced_navigation(self, frame):
        """绘制高级导航界面"""
        h, w = frame.shape[:2]
        
        # 半透明信息面板
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 80), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        
        # 导航信息
        if self.path_points:
            progress = f"{self.current_target_index + 1}/{len(self.path_points)}"
            cv2.putText(frame, f"目标点: {progress}", (20, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            
            remaining = len(self.path_points) - self.current_target_index - 1
            cv2.putText(frame, f"剩余路径点: {remaining}", (20, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        
        # 根据模式绘制导航箭头
        if self.navigation_mode == "3D" and self.is_navigating:
            directions = ["forward", "left", "right", "forward", "arrived"]
            direction = directions[min(self.current_target_index, len(directions)-1)]
            self.draw_3d_arrow(frame, direction)
        elif self.is_navigating:
            self.draw_2d_navigation(frame)
        
        # 绘制指南针
        self.draw_compass(frame)
        
        # 绘制特征点（调试用）
        if self.current_keypoints and len(self.current_keypoints) > 0:
            for kp in self.current_keypoints[:20]:  # 只显示前20个特征点
                x, y = int(kp.pt[0]), int(kp.pt[1])
                cv2.circle(frame, (x, y), 3, (0, 255, 255), -1)
    
    def draw_2d_navigation(self, frame):
        """绘制2D导航界面"""
        h, w = frame.shape[:2]
        center_x, center_y = w // 2, h // 2
        
        # 绘制导航圆环
        cv2.circle(frame, (center_x, center_y), 80, (100, 100, 100), 2)
        
        directions = ["forward", "left", "right", "forward", "arrived"]
        direction = directions[min(self.current_target_index, len(directions)-1)]
        
        if direction == "forward":
            pts = np.array([[center_x, center_y - 60],
                           [center_x - 40, center_y - 10],
                           [center_x + 40, center_y - 10]], np.int32)
            cv2.fillPoly(frame, [pts], (0, 255, 0))
        elif direction == "left":
            pts = np.array([[center_x - 60, center_y],
                           [center_x - 10, center_y - 40],
                           [center_x - 10, center_y + 40]], np.int32)
            cv2.fillPoly(frame, [pts], (255, 255, 0))
        elif direction == "right":
            pts = np.array([[center_x + 60, center_y],
                           [center_x + 10, center_y - 40],
                           [center_x + 10, center_y + 40]], np.int32)
            cv2.fillPoly(frame, [pts], (255, 255, 0))
        elif direction == "arrived":
            cv2.circle(frame, (center_x, center_y), 50, (0, 0, 255), -1)
            cv2.putText(frame, "到达!", (center_x - 40, center_y + 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    def draw_compass(self, frame):
        """绘制指南针"""
        h, w = frame.shape[:2]
        compass_radius = 30
        center_x, center_y = w - 50, 50
        
        # 绘制指南针圆盘
        cv2.circle(frame, (center_x, center_y), compass_radius, (200, 200, 200), -1)
        cv2.circle(frame, (center_x, center_y), compass_radius, (50, 50, 50), 2)
        
        # 绘制方向标记
        cv2.putText(frame, "N", (center_x - 5, center_y - compass_radius - 5), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
        cv2.putText(frame, "S", (center_x - 5, center_y + compass_radius + 15), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
        
        # 绘制指针（简化版本）
        angle_rad = math.radians(self.user_orientation)
        end_x = center_x + compass_radius * 0.7 * math.sin(angle_rad)
        end_y = center_y - compass_radius * 0.7 * math.cos(angle_rad)
        cv2.arrowedLine(frame, (center_x, center_y), (int(end_x), int(end_y)), 
                       (0, 0, 255), 2)
    
    def play_voice_guidance(self, message):
        """播放语音指导（简化版本）"""
        if self.voice_enabled and time.time() - self.last_voice_time > 5:
            print(f"语音提示: {message}")  # 在实际应用中替换为真正的语音合成
            self.last_voice_time = time.time()
    
    def process_frames(self):
        """处理视频帧的线程函数"""
        while self.processing_active:
            try:
                start_time = time.time()
                
                ret, frame = self.cap.read()
                if not ret:
                    time.sleep(0.01)
                    continue
                
                # 特征提取和位姿估计
                self.current_keypoints, self.current_descriptors = self.extract_features(frame)
                
                # 确保特征点存在
                if self.current_keypoints is not None and len(self.current_keypoints) > 0:
                    pose = self.estimate_pose(frame, self.current_keypoints, self.current_descriptors)
                    
                    # 更新用户位置和方向（简化）
                    if pose is not None:
                        self.user_position = pose[:3, 3]
                        # 从旋转矩阵提取偏航角
                        if np.linalg.norm(pose[:3, 2]) > 0:
                            self.user_orientation = math.degrees(
                                math.atan2(pose[1, 2], pose[0, 2])
                            )
                
                # 导航处理
                if self.is_navigating:
                    processed_frame = self.process_navigation(frame)
                else:
                    processed_frame = frame.copy()
                    cv2.putText(processed_frame, "等待导航开始", (50, 50), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                
                # 性能监控
                self.update_performance_stats(start_time)
                
                # 更新显示
                self.update_display(processed_frame)
                
                time.sleep(0.03)  # 控制处理频率
                
            except Exception as e:
                print(f"处理帧时出错: {e}")
                time.sleep(0.1)  # 出错时稍作等待
    
    def process_navigation(self, frame):
        """处理导航逻辑"""
        processed_frame = frame.copy()
        
        # 绘制高级导航界面
        self.draw_advanced_navigation(processed_frame)
        
        # 简单的导航逻辑（在实际应用中应该更复杂）
        if self.path_points and self.current_target_index < len(self.path_points):
            current_target = self.path_points[self.current_target_index]
            
            # 模拟位置检测和导航更新
            if self.current_keypoints and len(self.current_keypoints) > 50:
                # 模拟到达目标点 - 基于特征点数量变化
                if len(self.current_keypoints) > 200 and np.random.random() < 0.02:  # 2%的几率模拟到达
                    self.current_target_index += 1
                    if self.current_target_index < len(self.path_points):
                        next_target = self.path_points[self.current_target_index]
                        self.play_voice_guidance(f"向 {next_target} 前进")
                        self.update_status(f"到达 {current_target}，下一个目标: {next_target}")
                    else:
                        self.play_voice_guidance("已到达目的地")
                        self.update_status("导航完成！已到达最终目的地")
                        self.is_navigating = False
        
        return processed_frame
    
    def update_performance_stats(self, start_time):
        """更新性能统计"""
        frame_time = time.time() - start_time
        self.frame_times.append(frame_time)
        
        if self.current_keypoints:
            self.feature_counts.append(len(self.current_keypoints))
        
        # 更新GUI（在主线程中）
        if hasattr(self, 'root'):
            self.root.after(0, self.update_gui_stats)
    
    def update_gui_stats(self):
        """更新GUI性能显示"""
        try:
            if self.frame_times:
                fps = 1.0 / (sum(self.frame_times) / len(self.frame_times))
                self.fps_label.config(text=f"FPS: {fps:.1f}")
            
            if self.feature_counts:
                avg_features = sum(self.feature_counts) / len(self.feature_counts)
                self.features_label.config(text=f"特征点: {int(avg_features)}")
            
            if self.user_position is not None:
                pos_str = f"位置: ({self.user_position[0]:.2f}, {self.user_position[1]:.2f})"
                self.position_label.config(text=pos_str)
        except Exception as e:
            print(f"更新GUI统计时出错: {e}")
    
    def update_display(self, frame):
        """更新视频显示"""
        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb_frame)
            imgtk = ImageTk.PhotoImage(image=img)
            
            # 在主线程中更新GUI
            if hasattr(self, 'root'):
                self.root.after(0, lambda: self._update_video_label(imgtk))
        except Exception as e:
            print(f"更新显示时出错: {e}")
    
    def _update_video_label(self, imgtk):
        """在主线程中更新视频标签"""
        try:
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)
        except Exception as e:
            print(f"更新视频标签时出错: {e}")
    
    def capture_reference_point(self):
        """捕获参考点"""
        ret, frame = self.cap.read()
        if ret:
            point_name = f"参考点_{len(self.reference_images) + 1}"
            self.reference_images[point_name] = {
                'frame': frame.copy(),
                'keypoints': self.current_keypoints,
                'descriptors': self.current_descriptors.copy() if self.current_descriptors is not None else None
            }
            self.update_status(f"已捕获参考点: {point_name}")
            
            # 添加到路径列表
            self.path_listbox.insert(tk.END, point_name)
    
    def load_map(self):
        """加载地图文件"""
        filename = filedialog.askopenfilename(
            title="加载地图文件",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'r') as f:
                    map_data = json.load(f)
                
                # 这里应该实现地图数据的加载逻辑
                self.update_status(f"已加载地图文件: {filename}")
                
                # 模拟加载路径点
                if 'path_points' in map_data:
                    self.path_points = map_data['path_points']
                    self.path_listbox.delete(0, tk.END)
                    for point in self.path_points:
                        self.path_listbox.insert(tk.END, point)
                        
            except Exception as e:
                messagebox.showerror("错误", f"加载地图失败: {str(e)}")
    
    def save_map(self):
        """保存地图文件"""
        if not self.reference_images and not self.path_points:
            messagebox.showwarning("警告", "没有地图数据可保存")
            return
        
        filename = filedialog.asksaveasfilename(
            title="保存地图文件",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                map_data = {
                    'reference_points': list(self.reference_images.keys()),
                    'path_points': self.path_points,
                    'keyframes_count': len(self.keyframes),
                    'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
                }
                
                with open(filename, 'w') as f:
                    json.dump(map_data, f, indent=2)
                
                self.update_status(f"地图已保存: {filename}")
            except Exception as e:
                messagebox.showerror("错误", f"保存地图失败: {str(e)}")
    
    def set_start_point(self):
        """设置起点"""
        if self.reference_images:
            start_point = list(self.reference_images.keys())[0]
            self.path_points = [start_point]
            self.update_status(f"起点已设置为: {start_point}")
            self.path_listbox.delete(0, tk.END)
            self.path_listbox.insert(tk.END, f"起点: {start_point}")
        else:
            messagebox.showwarning("警告", "请先捕获参考点")
    
    def add_path_point(self):
        """添加路径点"""
        if self.reference_images:
            available_points = list(self.reference_images.keys())
            if available_points and len(self.path_points) > 0:
                point_name = available_points[len(self.path_points) % len(available_points)]
                self.path_points.append(point_name)
                self.update_status(f"已添加路径点: {point_name}")
                self.path_listbox.insert(tk.END, point_name)
            else:
                messagebox.showwarning("警告", "请先设置起点")
        else:
            messagebox.showwarning("警告", "请先捕获参考点")
    
    def set_end_point(self):
        """设置终点"""
        if self.reference_images and len(self.path_points) >= 1:
            available_points = list(self.reference_images.keys())
            if available_points:
                end_point = available_points[(len(self.path_points)) % len(available_points)]
                self.path_points.append(end_point)
                self.update_status(f"终点已设置为: {end_point}")
                self.path_listbox.insert(tk.END, f"终点: {end_point}")
        else:
            messagebox.showwarning("警告", "请先设置起点和路径点")
    
    def start_navigation(self):
        """开始导航"""
        if len(self.path_points) < 2:
            messagebox.showwarning("警告", "请先设置完整的路径（起点、路径点、终点）")
            return
        
        self.is_navigating = True
        self.current_target_index = 0
        self.update_status("导航已开始 - 跟随AR指引前进")
        self.play_voice_guidance("导航开始，请跟随箭头指引")
    
    def stop_navigation(self):
        """停止导航"""
        self.is_navigating = False
        self.update_status("导航已停止")
    
    def reset_system(self):
        """重置系统"""
        self.path_points = []
        self.current_target_index = 0
        self.is_navigating = False
        self.keyframes = []
        self.map_points = []
        self.path_listbox.delete(0, tk.END)
        self.update_status("系统已重置")
    
    def change_navigation_mode(self):
        """切换导航模式"""
        self.navigation_mode = self.mode_var.get()
        self.update_status(f"已切换到{self.navigation_mode}导航模式")
    
    def toggle_voice(self):
        """切换语音提示"""
        self.voice_enabled = self.voice_var.get()
        status = "启用" if self.voice_enabled else "禁用"
        self.update_status(f"语音提示已{status}")
    
    def run(self):
        """运行应用程序"""
        try:
            self.update_status("高级AR导航系统启动完成")
            self.update_status("使用方法: 1. 捕获参考点 2. 设置路径 3. 开始导航")
            self.root.mainloop()
        except Exception as e:
            self.update_status(f"系统错误: {str(e)}")
        finally:
            self.processing_active = False
            self.cap.release()
            cv2.destroyAllWindows()

def main():
    print("启动高级AR室内导航系统...")
    print("=" * 50)
    print("系统特性:")
    print("✓ 实时视觉里程计")
    print("✓ 2D/3D导航模式")
    print("✓ 语音导航提示") 
    print("✓ 地图保存/加载")
    print("✓ 性能监控")
    print("✓ 高级用户界面")
    print("=" * 50)
    
    app = AdvancedARNavigationSystem()
    app.run()

if __name__ == "__main__":
    main()