import math
import random
import struct
import zlib
from functools import reduce
from collections import defaultdict

class QuantumInspiredVision:
    """
    量子启发的自进化视觉算法
    通过量子叠加态模拟和概率坍缩实现图像理解
    """
    
    def __init__(self, dimension=8):
        self.dimension = dimension  # 量子态维度
        self.quantum_states = {}    # 量子态存储
        self.entanglement_map = {}  # 量子纠缠映射
        self.evolution_history = [] # 进化历史
        
    def _wave_function(self, x, amplitude, frequency, phase):
        """量子波函数模拟"""
        return amplitude * math.sin(2 * math.pi * frequency * x + phase)
    
    def _quantum_superposition(self, states):
        """创建量子叠加态"""
        if not states:
            return [0] * self.dimension
        
        # 归一化叠加态
        total = math.sqrt(sum(state**2 for state in states))
        if total == 0:
            return [0] * self.dimension
        
        return [state / total for state in states]
    
    def _quantum_collapse(self, superposition, observation_angle=0):
        """量子态坍缩到经典态"""
        # 引入观察者效应
        collapse_prob = [abs(state * math.cos(observation_angle)) for state in superposition]
        total = sum(collapse_prob)
        
        if total == 0:
            return random.choice(range(len(superposition)))
        
        # 概率性坍缩
        rand_val = random.random() * total
        cumulative = 0
        for i, prob in enumerate(collapse_prob):
            cumulative += prob
            if rand_val <= cumulative:
                return i
        return len(superposition) - 1
    
    def _entangle_states(self, state1, state2, entanglement_strength=0.8):
        """创建量子纠缠"""
        key = (min(state1, state2), max(state1, state2))
        self.entanglement_map[key] = entanglement_strength
        
        # 纠缠态同步更新
        if state1 in self.quantum_states and state2 in self.quantum_states:
            avg_state = [(a + b) / 2 for a, b in zip(
                self.quantum_states[state1], self.quantum_states[state2])]
            self.quantum_states[state1] = avg_state
            self.quantum_states[state2] = avg_state
    
    def _quantum_fourier_transform(self, signal):
        """量子傅里叶变换"""
        N = len(signal)
        result = [0] * N
        
        for k in range(N):
            real = 0
            imag = 0
            for n in range(N):
                angle = 2 * math.pi * k * n / N
                real += signal[n] * math.cos(angle)
                imag -= signal[n] * math.sin(angle)
            result[k] = math.sqrt(real**2 + imag**2) / N
        
        return result
    
    def _emergent_pattern_detection(self, quantum_states, threshold=0.7):
        """涌现模式检测"""
        patterns = []
        
        for i, state1 in enumerate(quantum_states):
            for j, state2 in enumerate(quantum_states[i+1:], i+1):
                # 计算量子态相关性
                correlation = self._quantum_correlation(
                    quantum_states[state1], quantum_states[state2])
                
                if correlation > threshold:
                    patterns.append((state1, state2, correlation))
        
        # 按相关性排序
        patterns.sort(key=lambda x: x[2], reverse=True)
        return patterns
    
    def _quantum_correlation(self, state1, state2):
        """计算量子态相关性"""
        if len(state1) != len(state2):
            return 0
        
        dot_product = sum(a * b for a, b in zip(state1, state2))
        norm1 = math.sqrt(sum(a**2 for a in state1))
        norm2 = math.sqrt(sum(b**2 for b in state2))
        
        if norm1 == 0 or norm2 == 0:
            return 0
        
        return abs(dot_product / (norm1 * norm2))
    
    def _chaos_to_order_transition(self, chaotic_data, order_parameter=0.5):
        """混沌到有序的相变"""
        # 计算混沌度
        chaos_level = self._calculate_chaos_level(chaotic_data)
        
        if chaos_level > order_parameter:
            # 高混沌状态 - 随机探索
            return self._random_exploration(chaotic_data)
        else:
            # 低混沌状态 - 模式形成
            return self._pattern_formation(chaotic_data)
    
    def _calculate_chaos_level(self, data):
        """计算数据混沌度"""
        if len(data) < 2:
            return 1.0
        
        # 计算熵作为混沌度度量
        differences = [abs(data[i] - data[i-1]) for i in range(1, len(data))]
        if not differences:
            return 1.0
        
        avg_diff = sum(differences) / len(differences)
        max_diff = max(differences) if differences else 1
        
        return avg_diff / max_diff if max_diff > 0 else 1.0
    
    def _random_exploration(self, data):
        """随机探索阶段"""
        exploration_factor = random.random()
        new_data = []
        
        for point in data:
            # 添加随机扰动
            perturbation = (random.random() - 0.5) * 2 * exploration_factor
            new_point = max(0, min(1, point + perturbation))
            new_data.append(new_point)
        
        return new_data
    
    def _pattern_formation(self, data):
        """模式形成阶段"""
        if len(data) < 3:
            return data
        
        # 使用局部平均促进模式形成
        new_data = []
        for i in range(len(data)):
            neighbors = []
            if i > 0:
                neighbors.append(data[i-1])
            neighbors.append(data[i])
            if i < len(data) - 1:
                neighbors.append(data[i+1])
            
            new_value = sum(neighbors) / len(neighbors)
            new_data.append(new_value)
        
        return new_data

class EmergentComputerVision:
    """
    涌现计算机视觉系统
    通过简单规则的相互作用产生复杂的视觉理解能力
    """
    
    def __init__(self, grid_size=64):
        self.grid_size = grid_size
        self.cellular_automata = {}
        self.quantum_vision = QuantumInspiredVision()
        self.memory_patterns = []
        self.attention_weights = {}
        
    def _initialize_quantum_pixels(self, width, height):
        """初始化量子像素网格"""
        quantum_grid = {}
        
        for y in range(height):
            for x in range(width):
                # 每个像素点初始化为量子叠加态
                state_key = f"pixel_{x}_{y}"
                superposition = [random.random() for _ in range(self.quantum_vision.dimension)]
                self.quantum_vision.quantum_states[state_key] = superposition
                quantum_grid[(x, y)] = state_key
        
        return quantum_grid
    
    def _emergent_edge_detection(self, quantum_grid, width, height):
        """涌现边缘检测"""
        edges = []
        
        for y in range(1, height-1):
            for x in range(1, width-1):
                # 获取邻域量子态
                neighbors = [
                    quantum_grid[(x-1, y)], quantum_grid[(x+1, y)],
                    quantum_grid[(x, y-1)], quantum_grid[(x, y+1)]
                ]
                
                center_state = self.quantum_vision.quantum_states[quantum_grid[(x, y)]]
                neighbor_states = [self.quantum_vision.quantum_states[n] for n in neighbors]
                
                # 计算量子梯度
                gradients = []
                for neighbor in neighbor_states:
                    gradient = self._quantum_gradient(center_state, neighbor)
                    gradients.append(gradient)
                
                avg_gradient = sum(gradients) / len(gradients)
                
                if avg_gradient > 0.3:  # 边缘阈值
                    edges.append((x, y, avg_gradient))
        
        return edges
    
    def _quantum_gradient(self, state1, state2):
        """计算量子态梯度"""
        differences = [abs(a - b) for a, b in zip(state1, state2)]
        return sum(differences) / len(differences)
    
    def _holographic_memory(self, pattern, significance=1.0):
        """全息记忆存储"""
        # 压缩模式信息
        compressed = self._compress_pattern(pattern)
        
        # 存储到记忆库
        memory_entry = {
            'pattern': compressed,
            'significance': significance,
            'timestamp': len(self.memory_patterns),
            'associations': []
        }
        
        self.memory_patterns.append(memory_entry)
        
        # 建立关联
        if len(self.memory_patterns) > 1:
            self._create_memory_associations(memory_entry)
    
    def _compress_pattern(self, pattern):
        """模式压缩"""
        if not pattern:
            return ""
        
        # 确保所有元素都是数值类型
        numeric_pattern = []
        for p in pattern:
            if isinstance(p, (int, float)):
                numeric_pattern.append(p)
            elif isinstance(p, str):
                # 尝试将字符串转换为数值
                try:
                    numeric_value = float(p)
                    numeric_pattern.append(numeric_value)
                except ValueError:
                    # 如果无法转换，使用哈希值
                    numeric_value = sum(ord(c) for c in p) / (len(p) * 100)
                    numeric_pattern.append(numeric_value)
            else:
                # 对于其他类型，使用默认值
                numeric_pattern.append(0.5)
        
        # 简单的模式编码
        encoded = "".join(str(int(p * 10)) for p in numeric_pattern)
        return encoded
    
    def _create_memory_associations(self, new_memory):
        """创建记忆关联"""
        for existing in self.memory_patterns[:-1]:  # 排除自己
            similarity = self._pattern_similarity(new_memory['pattern'], existing['pattern'])
            
            if similarity > 0.6:  # 相似度阈值
                new_memory['associations'].append({
                    'memory_id': self.memory_patterns.index(existing),
                    'strength': similarity
                })
                existing['associations'].append({
                    'memory_id': len(self.memory_patterns) - 1,
                    'strength': similarity
                })
    
    def _pattern_similarity(self, pattern1, pattern2):
        """模式相似度计算"""
        if not pattern1 or not pattern2:
            return 0
        
        # 确保都是字符串格式进行比较
        if not isinstance(pattern1, str):
            pattern1 = self._compress_pattern(pattern1)
        if not isinstance(pattern2, str):
            pattern2 = self._compress_pattern(pattern2)
        
        # 处理不同长度的模式
        min_len = min(len(pattern1), len(pattern2))
        if min_len == 0:
            return 0
        
        # 只比较较短长度的部分
        pattern1_trunc = pattern1[:min_len]
        pattern2_trunc = pattern2[:min_len]
        
        matches = sum(1 for a, b in zip(pattern1_trunc, pattern2_trunc) if a == b)
        return matches / min_len
    
    def _conscious_attention(self, sensory_input, attention_factor=0.7):
        """意识注意力机制"""
        if not sensory_input:
            return {}
        
        # 处理列表类型的输入（如图像矩阵）
        if isinstance(sensory_input, list):
            # 将二维图像矩阵转换为一维特征向量
            if sensory_input and isinstance(sensory_input[0], list):
                # 二维列表（图像）
                flattened = []
                for row in sensory_input:
                    if isinstance(row, list):
                        flattened.extend(row)
                    else:
                        flattened.append(row)
                sensory_input = {'image_features': flattened}
            else:
                # 一维列表
                sensory_input = {'features': sensory_input}
        
        # 计算每个输入的重要性
        importance_scores = {}
        total_energy = 0
        
        for key, value in sensory_input.items():
            # 如果值是列表，计算其统计特征
            if isinstance(value, list):
                if value:
                    # 使用列表的统计特征作为输入值
                    processed_value = {
                        'mean': sum(value) / len(value),
                        'max': max(value),
                        'min': min(value),
                        'std': math.sqrt(sum((x - sum(value)/len(value))**2 for x in value) / len(value)) if len(value) > 1 else 0
                    }
                    # 使用均值作为代表性数值
                    value = processed_value['mean']
                else:
                    value = 0
            elif isinstance(value, dict):
                # 对于字典，使用均值
                if 'mean' in value:
                    value = value['mean']
                else:
                    # 提取数值并计算均值
                    numeric_values = self._extract_numeric_values(value)
                    value = sum(numeric_values) / len(numeric_values) if numeric_values else 0.5
            
            # 确保值是数值类型
            if not isinstance(value, (int, float)):
                value = 0.5  # 默认值
            
            # 基于新奇性和相关性计算重要性
            novelty = self._calculate_novelty(value)
            relevance = self._calculate_relevance(value)
            importance = (novelty + relevance) / 2
            
            importance_scores[key] = importance
            total_energy += importance
        
        # 归一化注意力权重
        attention_weights = {}
        if total_energy > 0:
            for key, importance in importance_scores.items():
                attention_weights[key] = (importance / total_energy) * attention_factor
        
        self.attention_weights.update(attention_weights)
        return attention_weights
    
    def _calculate_novelty(self, input_data):
        """计算输入的新奇性"""
        if not self.memory_patterns:
            return 1.0  # 第一个输入总是新奇的
        
        # 处理不同类型的输入数据
        if isinstance(input_data, dict):
            # 字典类型，提取数值特征
            values = []
            for key, value in input_data.items():
                if isinstance(value, (int, float)):
                    values.append(value)
                elif isinstance(value, dict):
                    # 递归处理嵌套字典
                    values.extend(self._extract_numeric_values(value))
            input_pattern = self._compress_pattern(values)
        elif isinstance(input_data, list):
            input_pattern = self._compress_pattern(input_data)
        else:
            # 单个数值
            input_pattern = self._compress_pattern([input_data])
        
        # 与记忆中最相似的进行比较
        max_similarity = 0
        for memory in self.memory_patterns:
            similarity = self._pattern_similarity(input_pattern, memory['pattern'])
            max_similarity = max(max_similarity, similarity)
        
        return 1.0 - max_similarity
    
    def _extract_numeric_values(self, data_dict):
        """从字典中提取数值"""
        values = []
        for value in data_dict.values():
            if isinstance(value, (int, float)):
                values.append(value)
            elif isinstance(value, dict):
                values.extend(self._extract_numeric_values(value))
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, (int, float)):
                        values.append(item)
        return values

    def _calculate_relevance(self, input_data):
        """计算输入的相关性"""
        if not self.attention_weights:
            return 0.5  # 默认相关性
        
        # 处理不同类型的输入数据
        if isinstance(input_data, dict):
            values = self._extract_numeric_values(input_data)
            compressed = self._compress_pattern(values)
        elif isinstance(input_data, list):
            compressed = self._compress_pattern(input_data)
        elif isinstance(input_data, (int, float)):
            compressed = self._compress_pattern([input_data])
        else:
            # 对于其他类型（如字符串），使用默认值
            compressed = self._compress_pattern([0.5])
        
        # 基于当前注意力状态计算相关性
        relevance_score = 0
        
        for key, weight in self.attention_weights.items():
            # 处理键的类型 - 确保键是数值类型
            if isinstance(key, (int, float)):
                pattern_key = self._compress_pattern([key])
            elif isinstance(key, str):
                # 对于字符串键，使用哈希值或固定值
                try:
                    # 尝试将字符串转换为数值
                    numeric_key = sum(ord(c) for c in key) / (len(key) * 100)
                    pattern_key = self._compress_pattern([numeric_key])
                except:
                    pattern_key = self._compress_pattern([0.5])
            else:
                pattern_key = self._compress_pattern([0.5])
            
            similarity = self._pattern_similarity(compressed, pattern_key)
            relevance_score += similarity * weight
        
        return min(1.0, relevance_score)

class UniversalVisionProcessor:
    """
    通用视觉处理器
    结合量子启发视觉和涌现计算实现通用视觉理解
    """
    
    def __init__(self):
        self.quantum_system = QuantumInspiredVision()
        self.emergent_vision = EmergentComputerVision()
        self.reality_model = {}
        self.consciousness_level = 0.0
        
    def process_image_quantum(self, image_data):
        """量子图像处理"""
        if not image_data:
            return {}
        
        width, height = len(image_data[0]), len(image_data)
        quantum_grid = self.emergent_vision._initialize_quantum_pixels(width, height)
        
        # 将像素数据映射到量子态
        for y, row in enumerate(image_data):
            for x, pixel in enumerate(row):
                state_key = quantum_grid[(x, y)]
                # 将像素值转换为量子态
                quantum_state = self._pixel_to_quantum_state(pixel)
                self.quantum_system.quantum_states[state_key] = quantum_state
        
        # 量子纠缠建立
        self._establish_quantum_entanglement(quantum_grid, width, height)
        
        # 量子观测和坍缩
        observed_reality = self._quantum_observation(quantum_grid, width, height)
        
        # 边缘检测
        edges = self.emergent_vision._emergent_edge_detection(quantum_grid, width, height)
        
        return {
            'quantum_grid': quantum_grid,
            'observed_reality': observed_reality,
            'edges': edges,
            'quantum_states': self.quantum_system.quantum_states.copy()
        }
    
    def _pixel_to_quantum_state(self, pixel):
        """像素到量子态的转换"""
        if isinstance(pixel, (int, float)):
            # 灰度像素
            intensity = pixel / 255.0 if pixel > 1 else pixel
            return [intensity * math.sin(2 * math.pi * i / 8) for i in range(8)]
        else:
            # RGB像素
            r, g, b = pixel[0]/255.0, pixel[1]/255.0, pixel[2]/255.0
            return [
                r * math.sin(2 * math.pi * i / 8) +
                g * math.cos(2 * math.pi * i / 8) +
                b * math.sin(4 * math.pi * i / 8)
                for i in range(8)
            ]
    
    def _establish_quantum_entanglement(self, quantum_grid, width, height):
        """建立量子纠缠"""
        entanglement_strength = 0.6
        
        for y in range(height):
            for x in range(width):
                current = quantum_grid[(x, y)]
                
                # 与邻居建立纠缠
                if x > 0:
                    left = quantum_grid[(x-1, y)]
                    self.quantum_system._entangle_states(current, left, entanglement_strength)
                
                if y > 0:
                    top = quantum_grid[(x, y-1)]
                    self.quantum_system._entangle_states(current, top, entanglement_strength)
    
    def _quantum_observation(self, quantum_grid, width, height):
        """量子观测过程"""
        observed = []
        
        for y in range(height):
            row = []
            for x in range(width):
                state_key = quantum_grid[(x, y)]
                superposition = self.quantum_system.quantum_states[state_key]
                
                # 量子坍缩到经典态
                collapsed_state = self.quantum_system._quantum_collapse(
                    superposition, observation_angle=random.random() * math.pi)
                
                # 将坍缩态转换回像素值
                classical_pixel = self._quantum_state_to_pixel(collapsed_state)
                row.append(classical_pixel)
            
            observed.append(row)
        
        return observed
    
    def _quantum_state_to_pixel(self, state_index):
        """量子态到像素的转换"""
        # 简单的映射：将状态索引映射到灰度值
        return int((state_index / 7) * 255)
    
    def evolutionary_learning(self, experiences, learning_rate=0.1):
        """进化学习过程"""
        for experience in experiences:
            # 处理感官输入
            quantum_result = self.process_image_quantum(experience['sensory_input'])
            
            # 注意力机制
            attention = self.emergent_vision._conscious_attention(
                quantum_result['observed_reality'])
            
            # 记忆存储
            if quantum_result.get('edges'):
                edge_pattern = [edge[2] for edge in quantum_result['edges'][:10]]  # 取前10个边缘
                if len(edge_pattern) < 10:
                    edge_pattern.extend([0] * (10 - len(edge_pattern)))
                
                significance = sum(attention.values()) / len(attention) if attention else 0.5
                self.emergent_vision._holographic_memory(edge_pattern, significance)
            
            # 意识水平更新
            self._update_consciousness(experience, quantum_result)
        
        return {
            'memory_patterns': len(self.emergent_vision.memory_patterns),
            'consciousness_level': self.consciousness_level,
            'quantum_entanglements': len(self.quantum_system.entanglement_map)
        }
    
    def _update_consciousness(self, experience, quantum_result):
        """更新意识水平"""
        # 基于模式复杂性和记忆关联更新意识
        pattern_complexity = self._calculate_pattern_complexity(quantum_result)
        memory_richness = len(self.emergent_vision.memory_patterns) / 100.0  # 归一化
        
        learning_factor = 0.1
        consciousness_delta = (pattern_complexity * 0.6 + memory_richness * 0.4) * learning_factor
        
        self.consciousness_level = min(1.0, self.consciousness_level + consciousness_delta)
    
    def _calculate_pattern_complexity(self, quantum_result):
        """计算模式复杂性"""
        if not quantum_result.get('edges'):
            return 0
        
        edges = quantum_result['edges']
        if len(edges) < 2:
            return 0
        
        # 基于边缘密度和分布计算复杂性
        edge_density = len(edges) / (len(quantum_result['observed_reality']) * 
                                   len(quantum_result['observed_reality'][0]))
        
        # 计算边缘梯度的方差作为复杂性指标
        gradients = [edge[2] for edge in edges]
        if gradients:
            avg_gradient = sum(gradients) / len(gradients)
            variance = sum((g - avg_gradient) ** 2 for g in gradients) / len(gradients)
            complexity = edge_density * math.sqrt(variance) if variance > 0 else edge_density
        else:
            complexity = edge_density
        
        return min(1.0, complexity)

# 演示和测试代码
def create_test_image(width=32, height=32, pattern_type='random'):
    """创建测试图像"""
    image = []
    
    for y in range(height):
        row = []
        for x in range(width):
            if pattern_type == 'random':
                pixel = random.randint(0, 255)
            elif pattern_type == 'gradient':
                pixel = int((x / width + y / height) * 128)
            elif pattern_type == 'checkerboard':
                pixel = 255 if (x // 8 + y // 8) % 2 == 0 else 0
            elif pattern_type == 'circle':
                center_x, center_y = width // 2, height // 2
                distance = math.sqrt((x - center_x)**2 + (y - center_y)**2)
                pixel = 255 if distance < min(width, height) // 3 else 0
            else:
                pixel = random.randint(0, 255)
            
            row.append(pixel)
        image.append(row)
    
    return image

def demo_universal_vision():
    """演示通用视觉处理器"""
    
    print("=== 通用视觉处理器演示 ===\n")
    
    # 创建处理器实例
    uvp = UniversalVisionProcessor()
    
    # 创建测试图像
    test_patterns = ['random', 'gradient', 'checkerboard', 'circle']
    
    experiences = []
    for i, pattern in enumerate(test_patterns):
        image = create_test_image(32, 32, pattern)
        experiences.append({
            'sensory_input': image,
            'context': f'pattern_{pattern}',
            'timestamp': i
        })
    
    print("开始进化学习过程...")
    
    # 多轮进化学习
    for epoch in range(5):
        print(f"\n--- 第 {epoch + 1} 轮进化 ---")
        
        results = uvp.evolutionary_learning(experiences, learning_rate=0.1)
        
        print(f"记忆模式数量: {results['memory_patterns']}")
        print(f"意识水平: {results['consciousness_level']:.3f}")
        print(f"量子纠缠数量: {results['quantum_entanglements']}")
        
        # 显示量子系统状态
        quantum_states = list(uvp.quantum_system.quantum_states.values())
        if quantum_states:
            avg_quantum_energy = sum(sum(state) for state in quantum_states) / len(quantum_states)
            print(f"平均量子能量: {avg_quantum_energy:.3f}")
    
    print("\n=== 最终系统状态 ===")
    print(f"总记忆模式: {len(uvp.emergent_vision.memory_patterns)}")
    print(f"最终意识水平: {uvp.consciousness_level:.3f}")
    
    # 显示记忆关联
    print("\n=== 记忆关联分析 ===")
    for i, memory in enumerate(uvp.emergent_vision.memory_patterns[:3]):  # 显示前3个
        print(f"记忆 {i}: 显著性={memory['significance']:.3f}, 关联数={len(memory['associations'])}")
    
    # 测试边缘检测
    print("\n=== 边缘检测测试 ===")
    test_image = create_test_image(32, 32, 'circle')
    result = uvp.process_image_quantum(test_image)
    print(f"检测到边缘数量: {len(result['edges'])}")
    
    if result['edges']:
        avg_edge_strength = sum(edge[2] for edge in result['edges']) / len(result['edges'])
        print(f"平均边缘强度: {avg_edge_strength:.3f}")

# 高级应用：创造性视觉生成
class CreativeVisionGenerator:
    """创造性视觉生成器"""
    
    def __init__(self, universal_processor):
        self.processor = universal_processor
        self.creative_patterns = []
    
    def generate_novel_pattern(self, inspiration_pattern=None, creativity_level=0.7):
        """生成新颖模式"""
        if inspiration_pattern and self.processor.emergent_vision.memory_patterns:
            # 基于现有记忆进行创造性组合
            base_pattern = random.choice(self.processor.emergent_vision.memory_patterns)
            pattern_data = [float(c) for c in base_pattern['pattern']]
        else:
            # 完全随机生成
            pattern_data = [random.random() for _ in range(10)]
        
        # 应用创造性变异
        mutated_pattern = self._creative_mutation(pattern_data, creativity_level)
        
        # 量子化处理
        quantum_pattern = [self.processor.quantum_system._wave_function(
            i, val, random.random(), random.random() * math.pi) 
            for i, val in enumerate(mutated_pattern)]
        
        self.creative_patterns.append(quantum_pattern)
        return quantum_pattern
    
    def _creative_mutation(self, pattern, creativity_level):
        """创造性变异"""
        mutated = []
        
        for value in pattern:
            # 基于创造力水平决定变异程度
            if random.random() < creativity_level:
                # 创造性跳跃
                mutation = value + (random.random() - 0.5) * 2 * creativity_level
                mutated.append(max(0, min(1, mutation)))
            else:
                # 微小变异
                mutation = value + (random.random() - 0.5) * 0.1
                mutated.append(max(0, min(1, mutation)))
        
        return mutated

if __name__ == "__main__":
    # 运行演示
    demo_universal_vision()
    
    # 创造性生成示例
    print("\n" + "="*50)
    print("创造性视觉生成演示")
    print("="*50)
    
    uvp = UniversalVisionProcessor()
    creator = CreativeVisionGenerator(uvp)
    
    for i in range(3):
        novel_pattern = creator.generate_novel_pattern(creativity_level=0.8)
        print(f"生成模式 {i+1}: {[f'{x:.3f}' for x in novel_pattern[:5]]}...")