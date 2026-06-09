import cv2
import numpy as np
import time

class InvisibleCloak:
    def __init__(self, camera_index=0):
        """
        初始化隐身算法
        
        参数:
            camera_index: 摄像头索引
        """
        self.cap = cv2.VideoCapture(camera_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        # 背景模型
        self.background = None
        self.background_captured = False
        
        # 背景减除器
        self.back_sub = cv2.createBackgroundSubtractorMOG2(
            history=500, 
            varThreshold=16, 
            detectShadows=True
        )
        
        # 形态学操作核
        self.kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        
        # 隐身颜色范围 (这里以蓝色为例，可以根据需要调整)
        self.lower_color = np.array([100, 50, 50])
        self.upper_color = np.array([140, 255, 255])
        
        print("隐身算法初始化完成!")
        print("按 'b' 键捕获背景")
        print("按 'r' 键重置背景")
        print("按 'q' 键退出")
    
    def capture_background(self, frame):
        """捕获背景"""
        self.background = frame.copy()
        self.background_captured = True
        print("背景捕获成功!")
    
    def color_based_segmentation(self, frame):
        """
        基于颜色的前景分割
        返回前景掩码
        """
        # 转换为HSV颜色空间
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # 创建颜色掩码
        color_mask = cv2.inRange(hsv, self.lower_color, self.upper_color)
        
        # 形态学操作去除噪声
        color_mask = cv2.morphologyEx(color_mask, cv2.MORPH_OPEN, self.kernel)
        color_mask = cv2.morphologyEx(color_mask, cv2.MORPH_CLOSE, self.kernel)
        color_mask = cv2.dilate(color_mask, self.kernel, iterations=2)
        
        return color_mask
    
    def background_subtraction(self, frame):
        """
        背景减除方法
        返回前景掩码
        """
        if not self.background_captured:
            return np.zeros(frame.shape[:2], dtype=np.uint8)
        
        # 计算当前帧与背景的差异
        diff = cv2.absdiff(self.background, frame)
        diff_gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        
        # 二值化
        _, fg_mask = cv2.threshold(diff_gray, 25, 255, cv2.THRESH_BINARY)
        
        # 形态学操作
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, self.kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, self.kernel)
        
        return fg_mask
    
    def combined_segmentation(self, frame):
        """
        组合多种分割方法
        返回精细的前景掩码
        """
        # 方法1: 背景减除
        bg_sub_mask = self.background_subtraction(frame)
        
        # 方法2: 颜色分割
        color_mask = self.color_based_segmentation(frame)
        
        # 组合掩码
        combined_mask = cv2.bitwise_or(bg_sub_mask, color_mask)
        
        # 精细处理
        combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, self.kernel)
        combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, self.kernel)
        
        # 寻找轮廓
        contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 创建精细掩码
        refined_mask = np.zeros_like(combined_mask)
        
        for contour in contours:
            # 过滤小区域
            if cv2.contourArea(contour) > 1000:
                cv2.drawContours(refined_mask, [contour], -1, 255, -1)
        
        return refined_mask
    
    def apply_invisible_effect(self, frame, foreground_mask):
        """
        应用隐身效果
        """
        if not self.background_captured:
            return frame
        
        # 创建背景的副本
        result = self.background.copy()
        
        # 将前景区域从原始帧复制到结果中
        foreground = cv2.bitwise_and(frame, frame, mask=foreground_mask)
        background_without_fg = cv2.bitwise_and(result, result, mask=cv2.bitwise_not(foreground_mask))
        
        # 合并前景和背景
        result = cv2.add(background_without_fg, foreground)
        
        return result
    
    def process_frame(self, frame):
        """
        处理单帧图像
        """
        # 获取前景掩码
        foreground_mask = self.combined_segmentation(frame)
        
        # 应用隐身效果
        if self.background_captured:
            result = self.apply_invisible_effect(frame, foreground_mask)
        else:
            result = frame
        
        # 在图像上添加信息
        info_text = f"Background: {'Captured' if self.background_captured else 'Not Captured'}"
        cv2.putText(result, info_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(result, "Press 'b' to capture background", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        cv2.putText(result, "Press 'r' to reset background", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        
        # 显示前景掩码
        mask_display = cv2.cvtColor(foreground_mask, cv2.COLOR_GRAY2BGR)
        
        return result, mask_display
    
    def run(self):
        """主循环"""
        print("开始实时隐身处理...")
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("无法读取摄像头帧")
                break
            
            # 水平翻转帧以获得镜像效果
            frame = cv2.flip(frame, 1)
            
            # 处理帧
            result, mask_display = self.process_frame(frame)
            
            # 显示结果
            cv2.imshow('Original', frame)
            cv2.imshow('Foreground Mask', mask_display)
            cv2.imshow('Invisible Effect', result)
            
            # 键盘控制
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('b'):
                self.capture_background(frame)
            elif key == ord('r'):
                self.background_captured = False
                print("背景已重置")
            elif key == ord('c'):
                # 调整颜色阈值
                self.adjust_color_threshold()
        
        # 清理资源
        self.cap.release()
        cv2.destroyAllWindows()
    
    def adjust_color_threshold(self):
        """调整颜色阈值 (示例方法)"""
        print("当前颜色阈值:")
        print(f"Lower: {self.lower_color}")
        print(f"Upper: {self.upper_color}")
        
        # 这里可以添加交互式调整阈值的代码
        # 例如使用滑动条或命令行输入

# 高级版本 - 使用动态背景更新
class AdvancedInvisibleCloak(InvisibleCloak):
    def __init__(self, camera_index=0):
        super().__init__(camera_index)
        # 动态背景更新参数
        self.learning_rate = 0.01
        self.dynamic_background = None
        
    def update_dynamic_background(self, frame, foreground_mask):
        """动态更新背景模型"""
        if self.dynamic_background is None:
            self.dynamic_background = frame.copy().astype(np.float32)
            return
        
        # 只在非前景区域更新背景
        background_mask = cv2.bitwise_not(foreground_mask)
        background_mask = cv2.erode(background_mask, self.kernel, iterations=2)
        
        # 更新背景
        self.dynamic_background = cv2.accumulateWeighted(
            frame, 
            self.dynamic_background, 
            self.learning_rate,
            mask=background_mask
        )
    
    def apply_advanced_invisible_effect(self, frame, foreground_mask):
        """应用高级隐身效果"""
        if self.dynamic_background is None:
            return frame
        
        # 使用动态背景
        dynamic_bg = self.dynamic_background.astype(np.uint8)
        
        # 创建结果图像
        foreground = cv2.bitwise_and(frame, frame, mask=foreground_mask)
        background_without_fg = cv2.bitwise_and(dynamic_bg, dynamic_bg, mask=cv2.bitwise_not(foreground_mask))
        
        result = cv2.add(background_without_fg, foreground)
        return result
    
    def process_frame(self, frame):
        """重写处理帧方法"""
        foreground_mask = self.combined_segmentation(frame)
        
        # 更新动态背景
        self.update_dynamic_background(frame, foreground_mask)
        
        # 应用隐身效果
        if self.dynamic_background is not None:
            result = self.apply_advanced_invisible_effect(frame, foreground_mask)
        else:
            result = frame
        
        # 添加信息显示
        info_text = "Advanced Invisible Cloak - Dynamic Background"
        cv2.putText(result, info_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        mask_display = cv2.cvtColor(foreground_mask, cv2.COLOR_GRAY2BGR)
        
        return result, mask_display

def main():
    """主函数"""
    print("选择隐身算法版本:")
    print("1. 基础版本")
    print("2. 高级版本 (动态背景)")
    
    choice = input("请输入选择 (1 或 2): ").strip()
    
    if choice == "1":
        cloak = InvisibleCloak()
    elif choice == "2":
        cloak = AdvancedInvisibleCloak()
    else:
        print("无效选择，使用基础版本")
        cloak = InvisibleCloak()
    
    try:
        cloak.run()
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"发生错误: {e}")
    finally:
        if hasattr(cloak, 'cap'):
            cloak.cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()