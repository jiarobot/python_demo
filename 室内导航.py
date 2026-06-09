import cv2
import numpy as np
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import threading
import time

class ARNavigationSystem:
    def __init__(self):
        # 初始化摄像头
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # 特征检测器
        self.orb = cv2.ORB_create(nfeatures=1000)
        self.bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        
        # 存储参考图像和路径点
        self.reference_images = {}
        self.path_points = []
        self.current_target_index = 0
        self.is_navigating = False
        
        # 创建GUI
        self.create_gui()
        
        # 加载预设的参考图像（在实际应用中应该从文件加载）
        self.load_sample_reference_images()
        
    def load_sample_reference_images(self):
        """加载示例参考图像（在实际应用中应该从文件加载）"""
        # 这里我们创建一些示例参考图像
        # 在实际应用中，这些应该是预先拍摄的室内环境关键位置照片
        for i in range(5):
            # 创建一个示例图像（在实际中应该从文件加载真实图像）
            sample_img = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            self.add_reference_image(f"location_{i}", sample_img)
    
    def create_gui(self):
        """创建图形用户界面"""
        self.root = tk.Tk()
        self.root.title("AR室内导航系统")
        self.root.geometry("1200x800")
        
        # 主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 视频显示区域
        video_frame = ttk.LabelFrame(main_frame, text="实时AR导航视图")
        video_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.video_label = ttk.Label(video_frame)
        self.video_label.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 控制面板
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 路径设置
        path_frame = ttk.LabelFrame(control_frame, text="导航路径设置")
        path_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(path_frame, text="设置起点", 
                  command=self.set_start_point).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(path_frame, text="添加路径点", 
                  command=self.add_path_point).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(path_frame, text="设置终点", 
                  command=self.set_end_point).pack(side=tk.LEFT, padx=5, pady=5)
        
        # 导航控制
        nav_frame = ttk.LabelFrame(control_frame, text="导航控制")
        nav_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(nav_frame, text="开始导航", 
                  command=self.start_navigation).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(nav_frame, text="停止导航", 
                  command=self.stop_navigation).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(nav_frame, text="重置路径", 
                  command=self.reset_path).pack(side=tk.LEFT, padx=5, pady=5)
        
        # 状态显示
        status_frame = ttk.LabelFrame(control_frame, text="系统状态")
        status_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.status_label = ttk.Label(status_frame, text="系统就绪 - 等待用户操作")
        self.status_label.pack(padx=5, pady=5)
        
    def add_reference_image(self, name, image):
        """添加参考图像用于特征匹配"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        keypoints, descriptors = self.orb.detectAndCompute(gray, None)
        
        self.reference_images[name] = {
            'image': image,
            'keypoints': keypoints,
            'descriptors': descriptors
        }
    
    def extract_features(self, frame):
        """从帧中提取特征"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        keypoints, descriptors = self.orb.detectAndCompute(gray, None)
        return keypoints, descriptors
    
    def match_features(self, desc1, desc2):
        """匹配特征点"""
        if desc1 is None or desc2 is None:
            return []
        
        matches = self.bf.match(desc1, desc2)
        matches = sorted(matches, key=lambda x: x.distance)
        return matches[:50]  # 返回前50个最佳匹配
    
    def estimate_homography(self, kp1, kp2, matches, frame_shape):
        """估计单应性矩阵"""
        if len(matches) < 4:
            return None
        
        src_pts = np.float32([kp1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)
        
        H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
        return H
    
    def draw_navigation_arrow(self, frame, direction="forward"):
        """绘制导航箭头"""
        h, w = frame.shape[:2]
        center_x, center_y = w // 2, h // 2
        
        # 根据方向绘制不同的箭头
        if direction == "forward":
            # 向前箭头
            pts = np.array([[center_x, center_y - 100],
                           [center_x - 50, center_y],
                           [center_x + 50, center_y]], np.int32)
            cv2.fillPoly(frame, [pts], (0, 255, 0))
            
        elif direction == "left":
            # 向左箭头
            pts = np.array([[center_x - 100, center_y],
                           [center_x, center_y - 50],
                           [center_x, center_y + 50]], np.int32)
            cv2.fillPoly(frame, [pts], (255, 255, 0))
            
        elif direction == "right":
            # 向右箭头
            pts = np.array([[center_x + 100, center_y],
                           [center_x, center_y - 50],
                           [center_x, center_y + 50]], np.int32)
            cv2.fillPoly(frame, [pts], (255, 255, 0))
            
        elif direction == "arrived":
            # 到达目标点
            cv2.circle(frame, (center_x, center_y), 60, (0, 0, 255), -1)
            cv2.putText(frame, "ARRIVED", (center_x - 80, center_y - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    def draw_path_guidance(self, frame):
        """绘制路径引导信息"""
        h, w = frame.shape[:2]
        
        # 绘制顶部信息栏
        cv2.rectangle(frame, (0, 0), (w, 60), (0, 0, 0), -1)
        cv2.putText(frame, f"目标点: {self.current_target_index + 1}/{len(self.path_points)}", 
                   (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # 绘制方向指示（模拟）
        if len(self.path_points) > self.current_target_index:
            # 在实际应用中，这里应该根据当前位置和目标位置计算真实方向
            directions = ["forward", "left", "right", "forward", "arrived"]
            direction = directions[min(self.current_target_index, len(directions)-1)]
            self.draw_navigation_arrow(frame, direction)
    
    def process_frame(self, frame):
        """处理视频帧"""
        if not self.is_navigating:
            return frame
        
        # 提取当前帧特征
        kp_frame, desc_frame = self.extract_features(frame)
        
        # 简单的特征匹配和位置识别（在实际应用中应该更复杂）
        best_match = None
        best_matches_count = 0
        
        for name, ref_data in self.reference_images.items():
            matches = self.match_features(desc_frame, ref_data['descriptors'])
            if len(matches) > best_matches_count:
                best_matches_count = len(matches)
                best_match = name
        
        # 如果找到匹配的位置
        if best_match and best_matches_count > 10:
            cv2.putText(frame, f"当前位置: {best_match}", (20, 80), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        # 绘制导航信息
        self.draw_path_guidance(frame)
        
        return frame
    
    def set_start_point(self):
        """设置起点"""
        self.status_label.config(text="起点已设置")
        self.path_points = ["start_point"]
        
    def add_path_point(self):
        """添加路径点"""
        point_name = f"path_point_{len(self.path_points)}"
        self.path_points.append(point_name)
        self.status_label.config(text=f"已添加路径点: {point_name}")
        
    def set_end_point(self):
        """设置终点"""
        self.path_points.append("end_point")
        self.status_label.config(text="终点已设置，路径规划完成")
        
    def start_navigation(self):
        """开始导航"""
        if len(self.path_points) < 2:
            self.status_label.config(text="错误：请先设置路径点")
            return
            
        self.is_navigating = True
        self.current_target_index = 0
        self.status_label.config(text="导航已开始 - 跟随箭头指引")
        
    def stop_navigation(self):
        """停止导航"""
        self.is_navigating = False
        self.status_label.config(text="导航已停止")
        
    def reset_path(self):
        """重置路径"""
        self.path_points = []
        self.is_navigating = False
        self.current_target_index = 0
        self.status_label.config(text="路径已重置")
        
    def update_video(self):
        """更新视频显示"""
        ret, frame = self.cap.read()
        if ret:
            # 处理帧
            processed_frame = self.process_frame(frame)
            
            # 转换为RGB格式用于显示
            rgb_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb_frame)
            imgtk = ImageTk.PhotoImage(image=img)
            
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)
        
        self.root.after(10, self.update_video)
        
    def run(self):
        """运行应用程序"""
        try:
            self.update_video()
            self.root.mainloop()
        except Exception as e:
            print(f"发生错误: {e}")
        finally:
            self.cap.release()
            cv2.destroyAllWindows()

def main():
    print("启动AR室内导航系统...")
    print("系统功能说明:")
    print("1. 设置起点、路径点和终点")
    print("2. 开始导航后，系统会在视频上叠加导航箭头")
    print("3. 绿色箭头：直行")
    print("4. 黄色箭头：左转/右转")
    print("5. 红色圆圈：到达目标点")
    
    app = ARNavigationSystem()
    app.run()

if __name__ == "__main__":
    main()