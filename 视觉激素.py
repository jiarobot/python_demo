import cv2
import numpy as np
import time
import json
import threading
from collections import defaultdict
import requests
from datetime import datetime
import random

# 模拟激素分泌和调节的完整系统
class NeuroSyncEnvironmentSystem:
    def __init__(self):
        self.object_hormone_map = self.load_hormone_mapping()
        self.current_hormone_levels = defaultdict(float)
        self.environment_state = {
            'lighting': 'neutral',
            'temperature': 22,
            'sound_environment': 'silent',
            'aroma': 'none',
            'visual_display': 'neutral'
        }
        self.emotional_state = 'neutral'
        self.hormone_history = []
        
        # 初始化设备连接
        self.device_controllers = {
            'lights': SmartLightController(),
            'thermostat': ThermostatController(),
            'audio': AudioSystemController(),
            'aroma': AromaDiffuserController(),
            'display': VisualDisplayController()
        }
        
        # 启动监控
        self.monitoring_active = True
        self.camera = cv2.VideoCapture(0)
        
    def load_hormone_mapping(self):
        """加载物体到激素的映射关系"""
        return {
            # 自然元素
            'tree': {'oxytocin': 0.3, 'serotonin': 0.4, 'cortisol': -0.2},
            'flower': {'oxytocin': 0.5, 'serotonin': 0.6, 'dopamine': 0.3},
            'water': {'serotonin': 0.2, 'cortisol': -0.3},
            'sun': {'serotonin': 0.7, 'vitamin_d': 0.8},
            
            # 动物
            'cat': {'oxytocin': 0.8, 'serotonin': 0.6, 'cortisol': -0.4},
            'dog': {'oxytocin': 0.7, 'serotonin': 0.5, 'cortisol': -0.3},
            'bird': {'serotonin': 0.3, 'dopamine': 0.2},
            
            # 人物
            'person': {'oxytocin': 0.4, 'cortisol': 0.1},  # 可能增加压力
            'smiling_person': {'oxytocin': 0.6, 'serotonin': 0.4, 'cortisol': -0.2},
            
            # 工作相关
            'computer': {'cortisol': 0.3, 'adrenaline': 0.2},
            'book': {'serotonin': 0.2, 'cortisol': -0.1},
            'clock': {'cortisol': 0.4, 'adrenaline': 0.3},
            
            # 食物
            'fruit': {'dopamine': 0.3, 'serotonin': 0.2},
            'chocolate': {'dopamine': 0.7, 'serotonin': 0.5},
            
            # 负面元素
            'trash': {'cortisol': 0.5, 'adrenaline': 0.1},
            'spider': {'adrenaline': 0.8, 'cortisol': 0.6},
            'fire': {'adrenaline': 0.7, 'cortisol': 0.5}
        }
    
    def detect_objects(self, frame):
        """使用YOLO进行物体检测"""
        # 这里使用简化的模拟检测，实际应使用YOLO模型
        height, width = frame.shape[:2]
        
        # 模拟检测结果
        detected_objects = []
        
        # 在实际应用中，这里应该调用YOLO模型
        # 为了演示，我们随机检测一些物体
        objects_to_detect = ['person', 'computer', 'book', 'cat', 'flower']
        
        for obj in objects_to_detect:
            if random.random() < 0.3:  # 30%概率检测到每个物体
                x = random.randint(0, width-100)
                y = random.randint(0, height-100)
                w = random.randint(50, 200)
                h = random.randint(50, 200)
                confidence = random.uniform(0.5, 0.95)
                
                detected_objects.append({
                    'label': obj,
                    'confidence': confidence,
                    'bbox': [x, y, w, h]
                })
                
        return detected_objects
    
    def simulate_hormone_release(self, detected_objects):
        """模拟激素分泌过程"""
        hormone_changes = defaultdict(float)
        
        for obj in detected_objects:
            label = obj['label']
            confidence = obj['confidence']
            
            if label in self.object_hormone_map:
                hormone_effects = self.object_hormone_map[label]
                
                for hormone, effect in hormone_effects.items():
                    # 根据检测置信度调整激素影响
                    adjusted_effect = effect * confidence
                    hormone_changes[hormone] += adjusted_effect
        
        return hormone_changes
    
    def update_hormone_levels(self, hormone_changes):
        """更新当前激素水平"""
        decay_rate = 0.9  # 激素自然衰减率
        
        # 应用衰减
        for hormone in self.current_hormone_levels:
            self.current_hormone_levels[hormone] *= decay_rate
        
        # 应用新变化
        for hormone, change in hormone_changes.items():
            self.current_hormone_levels[hormone] += change
            # 限制激素水平在合理范围内
            self.current_hormone_levels[hormone] = max(-1.0, min(1.0, 
                self.current_hormone_levels[hormone]))
        
        # 记录历史
        self.hormone_history.append({
            'timestamp': datetime.now(),
            'levels': dict(self.current_hormone_levels),
            'changes': dict(hormone_changes)
        })
        
        # 保持历史记录长度
        if len(self.hormone_history) > 1000:
            self.hormone_history.pop(0)
    
    def analyze_emotional_state(self):
        """根据激素水平分析情绪状态"""
        oxytocin = self.current_hormone_levels.get('oxytocin', 0)
        serotonin = self.current_hormone_levels.get('serotonin', 0)
        dopamine = self.current_hormone_levels.get('dopamine', 0)
        cortisol = self.current_hormone_levels.get('cortisol', 0)
        adrenaline = self.current_hormone_levels.get('adrenaline', 0)
        
        # 情绪状态判断逻辑
        if serotonin > 0.6 and oxytocin > 0.5:
            self.emotional_state = 'blissful'
        elif dopamine > 0.5 and serotonin > 0.3:
            self.emotional_state = 'excited'
        elif oxytocin > 0.4:
            self.emotional_state = 'loving'
        elif serotonin > 0.4:
            self.emotional_state = 'calm'
        elif cortisol > 0.6 or adrenaline > 0.6:
            self.emotional_state = 'stressed'
        elif cortisol > 0.4:
            self.emotional_state = 'anxious'
        else:
            self.emotional_state = 'neutral'
        
        return self.emotional_state
    
    def calculate_environment_adjustments(self):
        """根据情绪状态计算环境调节"""
        adjustments = {}
        
        if self.emotional_state == 'stressed':
            adjustments = {
                'lighting': 'warm_dim',
                'temperature': -1,
                'sound_environment': 'nature_sounds',
                'aroma': 'lavender',
                'visual_display': 'calming_nature'
            }
        elif self.emotional_state == 'anxious':
            adjustments = {
                'lighting': 'soft_warm',
                'temperature': 0,
                'sound_environment': 'white_noise',
                'aroma': 'chamomile',
                'visual_display': 'breathing_exercise'
            }
        elif self.emotional_state == 'blissful':
            adjustments = {
                'lighting': 'bright_warm',
                'temperature': 0,
                'sound_environment': 'uplifting_music',
                'aroma': 'citrus',
                'visual_display': 'colorful_patterns'
            }
        elif self.emotional_state == 'excited':
            adjustments = {
                'lighting': 'dynamic_colors',
                'temperature': -1,
                'sound_environment': 'energetic_music',
                'aroma': 'peppermint',
                'visual_display': 'abstract_art'
            }
        elif self.emotional_state == 'loving':
            adjustments = {
                'lighting': 'romantic_warm',
                'temperature': 1,
                'sound_environment': 'soft_music',
                'aroma': 'rose',
                'visual_display': 'warm_glow'
            }
        elif self.emotional_state == 'calm':
            adjustments = {
                'lighting': 'neutral',
                'temperature': 0,
                'sound_environment': 'ambient',
                'aroma': 'sandalwood',
                'visual_display': 'gentle_waves'
            }
        else:  # neutral
            adjustments = {
                'lighting': 'neutral',
                'temperature': 0,
                'sound_environment': 'silent',
                'aroma': 'none',
                'visual_display': 'neutral'
            }
        
        return adjustments
    
    def apply_environment_adjustments(self, adjustments):
        """应用环境调节"""
        for device, adjustment in adjustments.items():
            if device in self.device_controllers:
                self.device_controllers[device].apply_adjustment(adjustment)
        
        self.environment_state.update(adjustments)
    
    def process_frame(self, frame):
        """处理单帧图像"""
        # 物体检测
        detected_objects = self.detect_objects(frame)
        
        # 激素分泌模拟
        hormone_changes = self.simulate_hormone_release(detected_objects)
        
        # 更新激素水平
        self.update_hormone_levels(hormone_changes)
        
        # 分析情绪状态
        emotional_state = self.analyze_emotional_state()
        
        # 计算环境调节
        adjustments = self.calculate_environment_adjustments()
        
        # 应用环境调节
        self.apply_environment_adjustments(adjustments)
        
        return {
            'detected_objects': detected_objects,
            'hormone_changes': hormone_changes,
            'emotional_state': emotional_state,
            'adjustments': adjustments
        }
    
    def start_monitoring(self):
        """开始监控循环"""
        def monitoring_loop():
            while self.monitoring_active:
                ret, frame = self.camera.read()
                if ret:
                    result = self.process_frame(frame)
                    self.display_results(frame, result)
                
                time.sleep(2)  # 每2秒处理一帧
        
        monitor_thread = threading.Thread(target=monitoring_loop)
        monitor_thread.daemon = True
        monitor_thread.start()
    
    def display_results(self, frame, result):
        """显示处理结果"""
        display_frame = frame.copy()
        
        # 绘制检测到的物体
        for obj in result['detected_objects']:
            label = obj['label']
            confidence = obj['confidence']
            x, y, w, h = obj['bbox']
            
            cv2.rectangle(display_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(display_frame, f"{label}: {confidence:.2f}", 
                       (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        # 显示激素水平和情绪状态
        y_offset = 30
        cv2.putText(display_frame, f"Emotional State: {result['emotional_state']}", 
                   (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        y_offset += 25
        
        for hormone, level in self.current_hormone_levels.items():
            if abs(level) > 0.1:  # 只显示显著变化的激素
                color = (0, 255, 0) if level > 0 else (0, 0, 255)
                cv2.putText(display_frame, f"{hormone}: {level:+.2f}", 
                           (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                y_offset += 20
        
        # 显示环境调节
        y_offset += 10
        cv2.putText(display_frame, "Environment Adjustments:", 
                   (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        y_offset += 25
        
        for adjustment, value in result['adjustments'].items():
            cv2.putText(display_frame, f"{adjustment}: {value}", 
                       (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
            y_offset += 20
        
        cv2.imshow('NeuroSync Environment System', display_frame)
        
        # 按'q'退出
        if cv2.waitKey(1) & 0xFF == ord('q'):
            self.monitoring_active = False
    
    def get_system_status(self):
        """获取系统状态"""
        return {
            'emotional_state': self.emotional_state,
            'hormone_levels': dict(self.current_hormone_levels),
            'environment_state': self.environment_state,
            'timestamp': datetime.now()
        }
    
    def save_data(self, filename='neurosync_data.json'):
        """保存系统数据"""
        data = {
            'hormone_history': self.hormone_history,
            'system_status': self.get_system_status(),
            'mapping_config': self.object_hormone_map
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, default=str, indent=2)

# 设备控制器类
class SmartLightController:
    def apply_adjustment(self, lighting_mode):
        print(f"Smart Lights: Changing to {lighting_mode} mode")
        # 实际实现会控制智能灯泡

class ThermostatController:
    def apply_adjustment(self, temperature_change):
        print(f"Thermostat: Adjusting temperature by {temperature_change}°C")
        # 实际实现会控制智能恒温器

class AudioSystemController:
    def apply_adjustment(self, sound_environment):
        print(f"Audio System: Playing {sound_environment}")
        # 实际实现会控制音响系统

class AromaDiffuserController:
    def apply_adjustment(self, aroma):
        if aroma != 'none':
            print(f"Aroma Diffuser: Releasing {aroma} scent")
        # 实际实现会控制香薰机

class VisualDisplayController:
    def apply_adjustment(self, display_mode):
        print(f"Visual Display: Showing {display_mode}")
        # 实际实现会控制显示屏

# 使用示例
if __name__ == "__main__":
    # 初始化系统
    neurosync_system = NeuroSyncEnvironmentSystem()
    
    print("NeuroSync Environment System Started!")
    print("Monitoring camera feed and adjusting environment...")
    print("Press 'q' to quit")
    
    try:
        # 开始监控
        neurosync_system.start_monitoring()
        
        # 保持主线程运行
        while neurosync_system.monitoring_active:
            time.sleep(1)
            
            # 每30秒打印一次状态
            if int(time.time()) % 30 == 0:
                status = neurosync_system.get_system_status()
                print(f"\nCurrent Status: {status}")
                
    except KeyboardInterrupt:
        print("\nShutting down NeuroSync System...")
    
    finally:
        neurosync_system.monitoring_active = False
        neurosync_system.camera.release()
        cv2.destroyAllWindows()
        neurosync_system.save_data()
        
        print("NeuroSync System shut down successfully!")
        print("Data saved to neurosync_data.json")