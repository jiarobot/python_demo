import numpy as np
import cv2
import random
import math
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Tuple, Optional
import json
import time

@dataclass
class Gene:
    """基因结构 - 控制生物的特性和行为"""
    color: Tuple[int, int, int]  # RGB颜色
    size: float  # 大小
    speed: float  # 移动速度
    vision_range: int  # 视野范围
    aggression: float  # 攻击性
    cooperation: float  # 合作性
    metabolism: float  # 新陈代谢速率
    reproduction_threshold: float  # 繁殖阈值

class Organism:
    """生物体类"""
    def __init__(self, x: int, y: int, genes: Gene, energy: float = 100.0):
        self.x = x
        self.y = y
        self.genes = genes
        self.energy = energy
        self.age = 0
        self.direction = random.uniform(0, 2 * math.pi)
        self.memory = []  # 短期记忆
        self.offspring_count = 0
        
    def perceive(self, environment: 'Environment') -> List[dict]:
        """感知环境中的其他生物和资源"""
        perceptions = []
        vision_range = self.genes.vision_range
        
        # 检测范围内的其他生物
        for other in environment.organisms:
            if other != self:
                distance = math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
                if distance <= vision_range:
                    perceptions.append({
                        'type': 'organism',
                        'entity': other,
                        'distance': distance,
                        'direction': math.atan2(other.y - self.y, other.x - self.x)
                    })
        
        # 检测范围内的资源
        for resource in environment.resources:
            distance = math.sqrt((self.x - resource.x)**2 + (self.y - resource.y)**2)
            if distance <= vision_range:
                perceptions.append({
                    'type': 'resource',
                    'entity': resource,
                    'distance': distance,
                    'direction': math.atan2(resource.y - self.y, resource.x - self.x)
                })
        
        return perceptions
    
    def decide_action(self, perceptions: List[dict]) -> str:
        """基于感知决定行为"""
        if not perceptions:
            # 没有感知到任何东西，随机移动
            return "wander"
        
        # 按距离排序感知
        perceptions.sort(key=lambda x: x['distance'])
        closest = perceptions[0]
        
        # 基于基因决定行为
        if closest['type'] == 'resource':
            return "approach_resource"
        elif closest['type'] == 'organism':
            other_genes = closest['entity'].genes
            
            # 判断是否是同类（基于颜色相似度）
            color_similarity = self._color_similarity(other_genes.color)
            
            if color_similarity > 0.7:  # 同类
                if self.genes.cooperation > 0.5:
                    return "cooperate"
                else:
                    return "avoid" if self.energy > 50 else "approach_resource"
            else:  # 异类
                if self.genes.aggression > 0.6 and self.energy > 30:
                    return "attack"
                else:
                    return "avoid"
        
        return "wander"
    
    def _color_similarity(self, other_color: Tuple[int, int, int]) -> float:
        """计算颜色相似度"""
        r1, g1, b1 = self.genes.color
        r2, g2, b2 = other_color
        distance = math.sqrt((r1-r2)**2 + (g1-g2)**2 + (b1-b2)**2)
        return 1 - (distance / 441.67)  # 最大欧氏距离归一化
    
    def mutate_genes(self) -> Gene:
        """基因突变"""
        new_color = tuple(
            max(0, min(255, c + random.randint(-20, 20))) 
            for c in self.genes.color
        )
        
        return Gene(
            color=new_color,
            size=max(1, self.genes.size + random.uniform(-0.5, 0.5)),
            speed=max(0.1, self.genes.speed + random.uniform(-0.2, 0.2)),
            vision_range=max(10, self.genes.vision_range + random.randint(-5, 5)),
            aggression=max(0, min(1, self.genes.aggression + random.uniform(-0.1, 0.1))),
            cooperation=max(0, min(1, self.genes.cooperation + random.uniform(-0.1, 0.1))),
            metabolism=max(0.01, self.genes.metabolism + random.uniform(-0.05, 0.05)),
            reproduction_threshold=max(50, self.genes.reproduction_threshold + random.uniform(-10, 10))
        )
    
    def reproduce(self) -> Optional['Organism']:
        """繁殖后代"""
        if self.energy >= self.genes.reproduction_threshold and self.offspring_count < 3:
            self.energy *= 0.6  # 消耗能量繁殖
            self.offspring_count += 1
            
            # 基因突变
            child_genes = self.mutate_genes()
            
            # 在附近位置生成后代
            offset_x = random.randint(-20, 20)
            offset_y = random.randint(-20, 20)
            
            return Organism(
                self.x + offset_x,
                self.y + offset_y,
                child_genes,
                energy=self.genes.reproduction_threshold * 0.4
            )
        return None

class Resource:
    """资源类"""
    def __init__(self, x: int, y: int, resource_type: str = "food", value: float = 25.0):
        self.x = x
        self.y = y
        self.type = resource_type
        self.value = value
        self.regrowth_timer = 0

class Environment:
    """环境类"""
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.organisms = []
        self.resources = []
        self.time_step = 0
        self.statistics = {
            'population': [],
            'diversity': [],
            'average_energy': []
        }
    
    def add_organism(self, organism: Organism):
        self.organisms.append(organism)
    
    def add_resource(self, resource: Resource):
        self.resources.append(resource)
    
    def generate_resources(self, count: int):
        """生成随机资源"""
        for _ in range(count):
            x = random.randint(0, self.width - 1)
            y = random.randint(0, self.height - 1)
            self.resources.append(Resource(x, y))
    
    def update(self):
        """更新环境状态"""
        self.time_step += 1
        
        # 更新所有生物
        new_organisms = []
        dead_organisms = []
        
        for organism in self.organisms[:]:
            # 感知环境
            perceptions = organism.perceive(self)
            
            # 决定行为
            action = organism.decide_action(perceptions)
            
            # 执行行为
            self._execute_action(organism, action, perceptions)
            
            # 消耗能量
            organism.energy -= organism.genes.metabolism
            organism.age += 1
            
            # 检查死亡
            if organism.energy <= 0 or organism.age > 1000:
                dead_organisms.append(organism)
                continue
            
            # 尝试繁殖
            offspring = organism.reproduce()
            if offspring:
                new_organisms.append(offspring)
            
            new_organisms.append(organism)
        
        # 更新生物列表
        self.organisms = new_organisms
        
        # 移除死亡生物
        for dead in dead_organisms:
            if dead in self.organisms:
                self.organisms.remove(dead)
        
        # 资源再生
        if self.time_step % 50 == 0:
            self.generate_resources(10)
        
        # 记录统计信息
        self._record_statistics()
    
    def _execute_action(self, organism: Organism, action: str, perceptions: List[dict]):
        """执行生物行为"""
        if action == "wander":
            # 随机游走
            organism.direction += random.uniform(-0.5, 0.5)
        elif action == "approach_resource" and perceptions:
            # 朝向最近的资源移动
            closest_resource = next((p for p in perceptions if p['type'] == 'resource'), None)
            if closest_resource:
                organism.direction = closest_resource['direction']
                
                # 如果足够近，消耗资源
                if closest_resource['distance'] < 5:
                    organism.energy += closest_resource['entity'].value
                    self.resources.remove(closest_resource['entity'])
        elif action == "attack" and perceptions:
            # 攻击最近的生物
            closest_organism = next((p for p in perceptions if p['type'] == 'organism'), None)
            if closest_organism and closest_organism['distance'] < 10:
                target = closest_organism['entity']
                damage = organism.genes.aggression * 20
                target.energy -= damage
                organism.energy -= damage * 0.1  # 攻击消耗能量
        
        # 移动生物
        dx = math.cos(organism.direction) * organism.genes.speed
        dy = math.sin(organism.direction) * organism.genes.speed
        
        organism.x = max(0, min(self.width - 1, organism.x + dx))
        organism.y = max(0, min(self.height - 1, organism.y + dy))
    
    def _record_statistics(self):
        """记录环境统计信息"""
        if self.organisms:
            self.statistics['population'].append(len(self.organisms))
            
            # 计算多样性（基于颜色）
            colors = [org.genes.color for org in self.organisms]
            unique_colors = set(colors)
            diversity = len(unique_colors) / len(colors) if colors else 0
            self.statistics['diversity'].append(diversity)
            
            # 平均能量
            avg_energy = sum(org.energy for org in self.organisms) / len(self.organisms)
            self.statistics['average_energy'].append(avg_energy)
        else:
            self.statistics['population'].append(0)
            self.statistics['diversity'].append(0)
            self.statistics['average_energy'].append(0)

class Visualizer:
    """可视化类"""
    def __init__(self, environment: Environment, scale: int = 4):
        self.env = environment
        self.scale = scale
        self.width = environment.width * scale
        self.height = environment.height * scale
        self.canvas = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
    def render(self) -> np.ndarray:
        """渲染当前环境状态"""
        # 清空画布
        self.canvas.fill(0)
        
        # 绘制资源
        for resource in self.env.resources:
            x = int(resource.x * self.scale)
            y = int(resource.y * self.scale)
            cv2.circle(self.canvas, (x, y), 3, (0, 255, 0), -1)
        
        # 绘制生物
        for organism in self.env.organisms:
            x = int(organism.x * self.scale)
            y = int(organism.y * self.scale)
            size = int(organism.genes.size * self.scale)
            color = organism.genes.color
            
            # 绘制生物主体
            cv2.circle(self.canvas, (x, y), size, color, -1)
            cv2.circle(self.canvas, (x, y), size, (255, 255, 255), 1)
            
            # 绘制视野范围
            vision_radius = organism.genes.vision_range * self.scale
            cv2.circle(self.canvas, (x, y), vision_radius, color, 1)
            
            # 绘制移动方向
            end_x = int(x + math.cos(organism.direction) * size * 2)
            end_y = int(y + math.sin(organism.direction) * size * 2)
            cv2.arrowedLine(self.canvas, (x, y), (end_x, end_y), (255, 255, 255), 1)
        
        return self.canvas
    
    def draw_statistics(self, canvas: np.ndarray) -> np.ndarray:
        """在画布上绘制统计信息"""
        stats = self.env.statistics
        
        if len(stats['population']) > 1:
            # 创建统计图
            stat_height = 150
            stat_width = 300
            stat_canvas = np.zeros((stat_height, stat_width, 3), dtype=np.uint8)
            
            # 绘制人口统计
            pop_data = stats['population'][-100:]  # 最近100个时间步
            if pop_data:
                max_pop = max(pop_data) if max(pop_data) > 0 else 1
                for i in range(1, len(pop_data)):
                    x1 = int((i-1) * stat_width / len(pop_data))
                    y1 = int(stat_height - (pop_data[i-1] / max_pop) * stat_height)
                    x2 = int(i * stat_width / len(pop_data))
                    y2 = int(stat_height - (pop_data[i] / max_pop) * stat_height)
                    cv2.line(stat_canvas, (x1, y1), (x2, y2), (0, 0, 255), 2)
            
            # 将统计图叠加到主画布
            canvas[10:10+stat_height, 10:10+stat_width] = stat_canvas
            
            # 添加文字信息
            cv2.putText(canvas, f"Population: {stats['population'][-1]}", 
                       (10, stat_height + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(canvas, f"Time: {self.env.time_step}", 
                       (10, stat_height + 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return canvas

def initialize_environment(width: int, height: int) -> Environment:
    """初始化环境并创建初始生物种群"""
    env = Environment(width, height)
    
    # 创建初始生物种群
    for _ in range(20):
        genes = Gene(
            color=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)),
            size=random.uniform(1.0, 3.0),
            speed=random.uniform(1.0, 3.0),
            vision_range=random.randint(20, 60),
            aggression=random.uniform(0, 1),
            cooperation=random.uniform(0, 1),
            metabolism=random.uniform(0.5, 2.0),
            reproduction_threshold=random.uniform(60, 120)
        )
        
        organism = Organism(
            x=random.randint(0, width - 1),
            y=random.randint(0, height - 1),
            genes=genes,
            energy=random.uniform(80, 120)
        )
        
        env.add_organism(organism)
    
    # 生成初始资源
    env.generate_resources(50)
    
    return env

def main():
    """主函数"""
    # 初始化环境和可视化
    env = initialize_environment(200, 150)
    visualizer = Visualizer(env, scale=4)
    
    print("Starting Artificial Life Ecosystem Simulation")
    print("Press 'q' to quit, 'p' to pause, 'r' to reset")
    
    paused = False
    
    while True:
        if not paused:
            # 更新环境
            env.update()
            
            # 渲染可视化
            frame = visualizer.render()
            frame = visualizer.draw_statistics(frame)
            
            # 显示帧
            cv2.imshow('Artificial Life Ecosystem', frame)
        
        # 处理按键
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('p'):
            paused = not paused
            print("Paused" if paused else "Resumed")
        elif key == ord('r'):
            env = initialize_environment(200, 150)
            visualizer = Visualizer(env, scale=4)
            print("Simulation Reset")
        
        # 添加延迟控制模拟速度
        time.sleep(0.05)
    
    cv2.destroyAllWindows()
    
    # 保存统计数据
    save_statistics(env.statistics)

def save_statistics(statistics: dict):
    """保存统计信息到文件"""
    with open('ecosystem_stats.json', 'w') as f:
        json.dump(statistics, f, indent=2)
    print("Statistics saved to ecosystem_stats.json")

if __name__ == "__main__":
    main()