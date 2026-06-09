import sys
import numpy as np
import pyqtgraph as pg
import pyqtgraph.opengl as gl
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt, QTimer
from scipy.spatial.transform import Rotation as R
import hashlib
import json
from datetime import datetime
import time
import random
import qiskit
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import EfficientSU2
import torch
import torch.nn as nn
import torch.optim as optim
from collections import deque
import snntorch as snn
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import MinMaxScaler
from scipy.signal import savgol_filter
from qiskit_aer import Aer
import threading
import psutil

# 设置全局样式
GLOBAL_STYLE = """
    QMainWindow {
        background-color: #0a192f;
        color: #ccd6f6;
        font-family: 'Segoe UI', Arial, sans-serif;
    }
    QWidget {
        background-color: #0a192f;
        color: #ccd6f6;
        border: none;
    }
    QGroupBox {
        background-color: #112240;
        border: 1px solid #1e3a8a;
        border-radius: 8px;
        margin-top: 1ex;
        padding: 10px;
        font-weight: bold;
        color: #64ffda;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top center;
        padding: 0 5px;
    }
    QLabel {
        color: #ccd6f6;
    }
    QPushButton {
        background-color: #1e3a8a;
        color: white;
        border: 1px solid #3b82f6;
        border-radius: 4px;
        padding: 5px 10px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #3b82f6;
    }
    QPushButton:pressed {
        background-color: #1d4ed8;
    }
    QComboBox, QDoubleSpinBox, QSpinBox, QSlider {
        background-color: #112240;
        color: #ccd6f6;
        border: 1px solid #1e3a8a;
        border-radius: 4px;
        padding: 3px;
    }
    QTabWidget::pane {
        border: 1px solid #1e3a8a;
        border-radius: 4px;
        background: #112240;
    }
    QTabBar::tab {
        background: #0a192f;
        color: #ccd6f6;
        padding: 8px 15px;
        border: 1px solid #1e3a8a;
        border-bottom: none;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }
    QTabBar::tab:selected {
        background: #112240;
        color: #64ffda;
        border-color: #3b82f6;
    }
    QTextEdit {
        background-color: #0a192f;
        color: #64ffda;
        border: 1px solid #1e3a8a;
        border-radius: 4px;
        font-family: 'Consolas', monospace;
    }
"""

# 性能监控类
class PerformanceMonitor:
    def __init__(self):
        self.reset()
        
    def reset(self):
        self.frame_times = deque(maxlen=100)
        self.cpu_usage = deque(maxlen=100)
        self.memory_usage = deque(maxlen=100)
        self.last_update = time.time()
        
    def update(self):
        now = time.time()
        frame_time = now - self.last_update
        self.frame_times.append(frame_time * 1000)  # ms
        self.cpu_usage.append(psutil.cpu_percent())
        self.memory_usage.append(psutil.virtual_memory().percent)
        self.last_update = now
        
    def get_fps(self):
        if not self.frame_times:
            return 0
        avg_frame_time = sum(self.frame_times) / len(self.frame_times)
        return 1000 / avg_frame_time if avg_frame_time > 0 else 0
        
    def get_report(self):
        return {
            "fps": self.get_fps(),
            "cpu": psutil.cpu_percent(),
            "memory": psutil.virtual_memory().percent,
            "avg_frame": sum(self.frame_times) / len(self.frame_times) if self.frame_times else 0
        }

class QuantumBlockchain:
    """量子增强的区块链日志系统"""
    def __init__(self):
        self.chain = []
        self.create_genesis_block()
        self.backend = Aer.get_backend('qasm_simulator')
    
    def create_genesis_block(self):
        genesis_block = {
            'index': 0,
            'timestamp': datetime.now().isoformat(),
            'data': "Genesis Block",
            'previous_hash': "0",
            'nonce': 0,
            'quantum_signature': None
        }
        genesis_block['hash'] = self.hash_block(genesis_block)
        self.chain.append(genesis_block)
    
    def quantum_signature(self, data):
        """简化量子签名生成"""
        data_str = json.dumps(data, sort_keys=True)
        binary_data = ''.join(format(ord(i), '08b') for i in data_str)
        
        # 减少量子比特数量
        num_qubits = min(8, len(binary_data))  # 从16减少到8
        
        # 使用量子电路生成签名
        qc = QuantumCircuit(num_qubits, num_qubits)
        
        # 数据编码
        for i, bit in enumerate(binary_data[:num_qubits]):
            if bit == '1':
                qc.x(i)
        
        # 应用Hadamard门
        qc.h(range(num_qubits))
        
        # 纠缠
        for i in range(num_qubits-1):
            qc.cx(i, i+1)
        
        # 测量
        qc.measure(range(num_qubits), range(num_qubits))
        
        # 执行
        compiled_circuit = transpile(qc, self.backend)
        job = self.backend.run(compiled_circuit)
        result = job.result()
        counts = result.get_counts()
        
        # 返回测量结果作为签名
        return list(counts.keys())[0] if counts else ""
    
    def hash_block(self, block):
        block_string = json.dumps({k: v for k, v in block.items() if k != 'hash'}, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()
    
    def proof_of_work(self, block):
        target = "0000"
        block['nonce'] = 0
        computed_hash = self.hash_block(block)
        
        while not computed_hash.startswith(target):
            block['nonce'] += 1
            computed_hash = self.hash_block(block)
        
        # 添加量子签名
        block['quantum_signature'] = self.quantum_signature(block['data'])
        return computed_hash
    
    def add_block(self, data):
        previous_block = self.chain[-1]
        new_block = {
            'index': len(self.chain),
            'timestamp': datetime.now().isoformat(),
            'data': data,
            'previous_hash': previous_block['hash'],
            'nonce': 0,
            'quantum_signature': None
        }
        new_block['hash'] = self.proof_of_work(new_block)
        self.chain.append(new_block)
        return new_block
    
    def validate_chain(self):
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i-1]
            
            # 验证哈希链
            if current['hash'] != self.hash_block(current):
                return False
            if current['previous_hash'] != previous['hash']:
                return False
            
            # 验证量子签名
            expected_signature = self.quantum_signature(current['data'])
            if current['quantum_signature'] != expected_signature:
                return False
        
        return True

class QuantumSNN(nn.Module):
    """量子启发的脉冲神经网络故障预测器"""
    def __init__(self, input_dim=27, hidden_dim=64, output_dim=3, beta=0.95):  # 修改 input_dim 为 27
        super().__init__()
        
        # 输入层
        self.fc_in = nn.Linear(input_dim, hidden_dim)
        self.lif_in = snn.Leaky(beta=beta)
        
        # 隐藏层
        self.fc_hid = nn.Linear(hidden_dim, hidden_dim)
        self.lif_hid = snn.Leaky(beta=beta)
        
        # 输出层
        self.fc_out = nn.Linear(hidden_dim, output_dim)
        self.lif_out = snn.Leaky(beta=beta)
        
    def forward(self, x):
        # 初始化记忆电位
        mem_in = self.lif_in.init_leaky()
        mem_hid = self.lif_hid.init_leaky()
        mem_out = self.lif_out.init_leaky()
        
        # 时间步循环 (25步)
        for _ in range(25):
            cur_in = self.fc_in(x)
            spk_in, mem_in = self.lif_in(cur_in, mem_in)
            
            cur_hid = self.fc_hid(spk_in)
            spk_hid, mem_hid = self.lif_hid(cur_hid, mem_hid)
            
            cur_out = self.fc_out(spk_hid)
            spk_out, mem_out = self.lif_out(cur_out, mem_out)
        
        # 返回最终时间步的膜电位作为预测
        return mem_out

class AdaptiveFaultController:
    """基于强化学习的自适应容错控制器"""
    def __init__(self, state_dim=16, action_dim=9):  # 修改为16维输入
        self.state_dim = state_dim
        self.action_dim = action_dim
        
        # 策略网络
        self.policy_net = nn.Sequential(
            nn.Linear(state_dim, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, action_dim)
        )
        
        # 价值网络
        self.value_net = nn.Sequential(
            nn.Linear(state_dim, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 1)
        )
        
        self.optimizer = optim.Adam(
            list(self.policy_net.parameters()) + list(self.value_net.parameters()),
            lr=1e-4
        )
        
        # 经验回放
        self.memory = deque(maxlen=10000)
        
    def select_action(self, state):
        state = torch.FloatTensor(state).unsqueeze(0)
        action_probs = torch.softmax(self.policy_net(state), dim=-1)
        action_dist = torch.distributions.Categorical(action_probs)
        action = action_dist.sample()
        return action.item(), action_dist.log_prob(action)
    
    def store_experience(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))
    
    def update(self, batch_size=64):
        if len(self.memory) < batch_size:
            return 0, 0
        
        batch = random.sample(self.memory, batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)
        
        states = torch.FloatTensor(states)
        actions = torch.LongTensor(actions)
        rewards = torch.FloatTensor(rewards)
        next_states = torch.FloatTensor(next_states)
        dones = torch.FloatTensor(dones)
        
        # 计算价值函数
        values = self.value_net(states).squeeze()
        next_values = self.value_net(next_states).squeeze()
        
        # 计算优势函数
        advantages = rewards + 0.99 * next_values * (1 - dones) - values
        advantages = advantages.detach()
        
        # 策略梯度
        action_probs = torch.softmax(self.policy_net(states), dim=-1)
        action_dist = torch.distributions.Categorical(action_probs)
        log_probs = action_dist.log_prob(actions)
        
        policy_loss = -(log_probs * advantages).mean()
        
        # 价值函数损失
        value_loss = nn.MSELoss()(values, rewards + 0.99 * next_values * (1 - dones))
        
        # 总损失
        loss = policy_loss + 0.5 * value_loss
        
        # 优化
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        
        return policy_loss.item(), value_loss.item()

class UltimateTripleSystem:
    """终极三三制容错系统"""
    def __init__(self):
        # 三套传感器
        self.sensors = {
            'primary': {'accel': np.zeros(3), 'gyro': np.zeros(3), 'mag': np.zeros(3), 'healthy': True},
            'secondary': {'accel': np.zeros(3), 'gyro': np.zeros(3), 'mag': np.zeros(3), 'healthy': True},
            'tertiary': {'accel': np.zeros(3), 'gyro': np.zeros(3), 'mag': np.zeros(3), 'healthy': True}
        }
        
        # 动态权重
        self.weights = {'primary': 0.5, 'secondary': 0.3, 'tertiary': 0.2}
        
        # 量子神经形态故障预测器
        self.predictor = QuantumSNN()
        self.predictor.load_state_dict(torch.load('quantum_snn_predictor.pth', map_location=torch.device('cpu')))
        self.predictor.eval()
        
        # 强化学习控制器
        self.controller = AdaptiveFaultController()
        
        # 量子区块链
        self.blockchain = QuantumBlockchain()
        
        # 数字孪生
        self.digital_twin = {
            'position': np.zeros(3),
            'velocity': np.zeros(3),
            'attitude': np.zeros(3),
            'health': 1.0,  # 系统健康度
            'energy': 100.0,
            'environment': {
                'wind': np.zeros(3),
                'turbulence': 0.0,
                'temperature': 25.0
            }
        }
        
        # 异常检测器
        self.anomaly_detector = IsolationForest(contamination=0.01)
        self.sensor_data_buffer = deque(maxlen=1000)
        self._init_anomaly_detector()
        
        # 故障注入
        self.fault_params = {
            'type': None,
            'target': None,
            'magnitude': 0.0,
            'start_time': 0.0,
            'duration': 0.0
        }
        
        # 系统状态
        self.system_state = {
            'mode': 'NORMAL',  # NORMAL, DEGRADED, CRITICAL
            'uptime': 0.0,
            'faults_detected': 0,
            'faults_predicted': 0,
            'reconfigurations': 0,
            'last_recovery_time': 0.0
        }
        
        # 历史数据
        self.history = {
            'sensor_data': deque(maxlen=500),
            'fused_data': deque(maxlen=500),
            'weights': deque(maxlen=500),
            'predictions': deque(maxlen=500)
        }
    
    def _init_anomaly_detector(self):
        """使用历史数据初始化异常检测器"""
        # 生成模拟正常数据
        normal_data = []
        for _ in range(1000):
            data = {
                'accel': np.random.normal([0, 0, -9.8], 0.1),
                'gyro': np.random.normal(0, 0.05, 3),
                'mag': np.random.normal([0.2, 0.1, 0.5], 0.05)
            }
            normal_data.append(np.concatenate([data['accel'], data['gyro'], data['mag']]))
        
        # 训练异常检测器
        self.anomaly_detector.fit(normal_data)
    
    def update_sensors(self, true_data):
        """更新传感器数据并注入故障"""
        t = time.time()
        
        # 复制真实数据
        for sensor in self.sensors.values():
            sensor['accel'] = true_data['accel'].copy()
            sensor['gyro'] = true_data['gyro'].copy()
            sensor['mag'] = true_data['mag'].copy()
        
        # 注入故障
        if self.fault_params['type']:
            elapsed = t - self.fault_params['start_time']
            target_sensor = self.sensors[self.fault_params['target']]
            duration = self.fault_params['duration']
            
            if 0 < elapsed < duration:
                if self.fault_params['type'] == 'bias':
                    target_sensor['accel'] += self.fault_params['magnitude']
                elif self.fault_params['type'] == 'drift':
                    drift_rate = self.fault_params['magnitude'] * elapsed
                    target_sensor['gyro'] += drift_rate
                elif self.fault_params['type'] == 'noise':
                    noise = np.random.normal(0, self.fault_params['magnitude'], 3)
                    target_sensor['accel'] += noise
                elif self.fault_params['type'] == 'stuck':
                    if elapsed > 1.0:  # 1秒后卡死
                        target_sensor['accel'] = np.array([0.0, 0.0, -9.8])
                elif self.fault_params['type'] == 'spike':
                    if 0.5 < elapsed < 0.6:  # 短时脉冲
                        target_sensor['accel'] += np.array([8.0, 0.0, 0.0])
        
        # 记录到区块链
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'sensors': {k: {'accel': v['accel'].tolist(), 'gyro': v['gyro'].tolist()} for k, v in self.sensors.items()}
        }
        self.blockchain.add_block(log_data)
        
        # 保存数据用于异常检测
        sensor_data = np.concatenate([
            self.sensors['primary']['accel'], 
            self.sensors['primary']['gyro'],
            self.sensors['primary']['mag']
        ])
        self.sensor_data_buffer.append(sensor_data)
    
    def predict_faults(self):
        """使用量子神经形态网络预测故障"""
        # 准备输入数据
        input_data = []
        for name in ['primary', 'secondary', 'tertiary']:
            sensor = self.sensors[name]
            input_data.extend(sensor['accel'])
            input_data.extend(sensor['gyro'])
            input_data.extend(sensor['mag'])
        
        input_tensor = torch.FloatTensor(input_data)
        
        # 预测
        with torch.no_grad():
            predictions = self.predictor(input_tensor.unsqueeze(0))
        
        return torch.sigmoid(predictions).squeeze().numpy()
    
    def detect_anomalies(self):
        """检测传感器异常"""
        if len(self.sensor_data_buffer) < 100:
            return [False, False, False]
        
        # 使用最近100个数据点
        recent_data = list(self.sensor_data_buffer)[-100:]
        anomalies = self.anomaly_detector.predict(recent_data)
        
        # 计算每个传感器的异常分数
        sensor_anomalies = [False, False, False]
        anomaly_counts = [0, 0, 0]
        
        for i, anomaly in enumerate(anomalies):
            sensor_idx = i % 3  # 循环使用三个传感器
            if anomaly == -1:
                anomaly_counts[sensor_idx] += 1
        
        # 如果超过20%的数据点异常，则标记传感器故障
        for i in range(3):
            if anomaly_counts[i] > 20:
                sensor_anomalies[i] = True
        
        return sensor_anomalies
    
    def adaptive_fusion(self):
        """自适应传感器融合"""
        # 构建状态向量
        state = []
        for name in ['primary', 'secondary', 'tertiary']:
            state.extend(self.sensors[name]['accel'])
            state.append(self.sensors[name]['healthy'])
        state.extend(self.weights.values())
        state.append(self.digital_twin['health'])
        
        # 选择动作
        action_idx, log_prob = self.controller.select_action(state)
        
        # 将动作转换为权重调整
        # 动作0-2: 增加权重, 3-5: 减少权重, 6-8: 重置权重
        sensor_idx = action_idx % 3
        action_type = action_idx // 3
        
        if action_type == 0:  # 增加权重
            self.weights[list(self.weights.keys())[sensor_idx]] = min(0.8, self.weights[list(self.weights.keys())[sensor_idx]] + 0.1)
        elif action_type == 1:  # 减少权重
            self.weights[list(self.weights.keys())[sensor_idx]] = max(0.1, self.weights[list(self.weights.keys())[sensor_idx]] - 0.1)
        else:  # 重置权重
            self.weights = {'primary': 0.5, 'secondary': 0.3, 'tertiary': 0.2}
        
        # 归一化权重
        total = sum(self.weights.values())
        for name in self.weights:
            self.weights[name] /= total
        
        return state, action_idx
    
    def update_digital_twin(self, fused_data, dt=0.02):
        """更新数字孪生模型"""
        # 姿态更新
        gyro = fused_data['gyro']
        rotation = R.from_rotvec(gyro * dt)
        current_rot = R.from_euler('xyz', self.digital_twin['attitude'])
        new_rot = rotation * current_rot
        self.digital_twin['attitude'] = new_rot.as_euler('xyz')
        
        # 位置更新
        rot_matrix = new_rot.as_matrix()
        global_accel = rot_matrix @ fused_data['accel'] - np.array([0, 0, 9.8])
        self.digital_twin['velocity'] += global_accel * dt
        self.digital_twin['position'] += self.digital_twin['velocity'] * dt
        
        # 更新环境
        self._update_environment(dt)
        
        # 更新系统健康度
        fault_count = sum(not s['healthy'] for s in self.sensors.values())
        self.digital_twin['health'] = max(0.3, 1.0 - fault_count * 0.2)
        
        # 能量消耗
        power_usage = np.linalg.norm(fused_data['accel']) * 0.005
        self.digital_twin['energy'] -= power_usage * dt
    
    def _update_environment(self, dt):
        """更新环境模型"""
        # 风模型
        self.digital_twin['environment']['wind'] = np.array([
            2.0 * np.sin(0.1 * time.time()),
            1.5 * np.cos(0.15 * time.time()),
            0.5 * np.sin(0.05 * time.time())
        ])
        
        # 湍流
        self.digital_twin['environment']['turbulence'] = 0.5 * np.random.randn()
        
        # 温度变化
        altitude_effect = max(0, self.digital_twin['position'][2] / 1000 * -0.0065)
        self.digital_twin['environment']['temperature'] = 25.0 + altitude_effect
    
    def reconfigure_system(self):
        """系统重构"""
        fault_count = sum(not s['healthy'] for s in self.sensors.values())
        
        if fault_count == 0:
            self.system_state['mode'] = 'NORMAL'
        elif fault_count == 1:
            self.system_state['mode'] = 'DEGRADED'
            
            # 在降级模式下，增加健康传感器的权重
            for name, sensor in self.sensors.items():
                if sensor['healthy']:
                    self.weights[name] = min(0.7, self.weights[name] + 0.1)
            
            # 归一化权重
            total = sum(self.weights.values())
            for name in self.weights:
                self.weights[name] /= total
        else:
            self.system_state['mode'] = 'CRITICAL'
            
            # 在临界模式下，使用最可靠的传感器
            max_weight = 0.0
            best_sensor = None
            
            for name, sensor in self.sensors.items():
                if sensor['healthy'] and self.weights[name] > max_weight:
                    max_weight = self.weights[name]
                    best_sensor = name
            
            if best_sensor:
                # 将所有权重分配给最佳传感器
                self.weights = {name: 1.0 if name == best_sensor else 0.0 for name in self.weights}
        
        self.system_state['reconfigurations'] += 1
        self.system_state['last_recovery_time'] = time.time()
    
    def run_cycle(self, true_data):
        """运行一个系统周期"""
        dt = 0.02
        self.system_state['uptime'] += dt
        
        # 1. 更新传感器
        self.update_sensors(true_data)
        
        # 2. 故障预测
        fault_probs = self.predict_faults()
        self.history['predictions'].append(fault_probs)
        
        # 3. 故障检测
        anomalies = self.detect_anomalies()
        sensor_names = ['primary', 'secondary', 'tertiary']
        for i, name in enumerate(sensor_names):
            if anomalies[i] and fault_probs[i] > 0.7:
                self.sensors[name]['healthy'] = False
                self.system_state['faults_detected'] += 1
                self.system_state['faults_predicted'] += 1
        
        # 4. 自适应融合
        state, action = self.adaptive_fusion()
        
        # 5. 数据融合
        fused_data = {'accel': np.zeros(3), 'gyro': np.zeros(3)}
        for name, sensor in self.sensors.items():
            weight = self.weights[name]
            fused_data['accel'] += sensor['accel'] * weight
            fused_data['gyro'] += sensor['gyro'] * weight
        self.history['fused_data'].append(fused_data)
        
        # 6. 更新数字孪生
        self.update_digital_twin(fused_data, dt)
        
        # 7. 系统重构
        self.reconfigure_system()
        
        # 8. 强化学习奖励
        reward = self._calculate_reward()
        next_state = state  # 简化处理，实际应为下一个状态
        self.controller.store_experience(state, action, reward, next_state, False)
        
        # 9. 定期更新控制器
        if int(self.system_state['uptime'] / dt) % 10 == 0:
            self.controller.update()
        
        return fused_data
    
    def _calculate_reward(self):
        """计算强化学习奖励"""
        # 基于系统稳定性、能效和健康度
        stability = 1.0 / (1.0 + np.linalg.norm(self.history['fused_data'][-1]['accel']))
        energy_efficiency = self.digital_twin['energy'] / 100.0
        health = self.digital_twin['health']
        
        # 惩罚传感器故障
        fault_penalty = sum(not s['healthy'] for s in self.sensors.values()) * 0.2
        
        return stability * 0.4 + energy_efficiency * 0.3 + health * 0.3 - fault_penalty
    
    def inject_fault(self, fault_type, target, magnitude, duration=5.0):
        """注入传感器故障"""
        self.fault_params = {
            'type': fault_type,
            'target': target,
            'magnitude': magnitude,
            'start_time': time.time(),
            'duration': duration
        }
    
    def get_system_report(self):
        """生成系统报告"""
        return {
            'status': {
                'mode': self.system_state['mode'],
                'uptime': self.system_state['uptime'],
                'health': self.digital_twin['health'],
                'energy': self.digital_twin['energy'],
                'position': self.digital_twin['position'].tolist(),
                'attitude': self.digital_twin['attitude'].tolist(),
                'faults': {
                    'detected': self.system_state['faults_detected'],
                    'predicted': self.system_state['faults_predicted']
                }
            },
            'sensors': {
                name: {
                    'healthy': sensor['healthy'],
                    'weight': self.weights[name]
                } for name, sensor in self.sensors.items()
            },
            'environment': self.digital_twin['environment']
        }

# 系统工作线程
class SystemWorker(QtCore.QObject):
    update_signal = QtCore.pyqtSignal(dict)
    finished = QtCore.pyqtSignal()
    
    def __init__(self, system):
        super().__init__()
        self.system = system
        self.running = True
        
    def run(self):
        while self.running:
            start_time = time.time()
            
            # 生成模拟飞行数据
            t = time.time()
            true_data = {
                'accel': np.array([
                    1.5 * np.sin(0.2 * t),
                    1.2 * np.cos(0.3 * t),
                    -9.8 - 0.5 * np.sin(0.1 * t)
                ]),
                'gyro': np.array([
                    0.2 * np.sin(0.4 * t),
                    0.25 * np.cos(0.35 * t),
                    0.3
                ]),
                'mag': np.array([
                    0.15 * np.sin(0.1 * t),
                    0.25 * np.cos(0.15 * t),
                    0.5
                ])
            }
            
            # 运行系统周期
            fused_data = self.system.run_cycle(true_data)
            
            # 获取系统报告
            report = self.system.get_system_report()
            
            # 添加性能数据
            report['performance'] = {
                'cycle_time': (time.time() - start_time) * 1000  # ms
            }
            
            # 发送更新信号
            self.update_signal.emit(report)
            
            # 控制更新频率 (最大50Hz)
            elapsed = (time.time() - start_time) * 1000
            if elapsed < 20:
                time.sleep((20 - elapsed) / 1000)
                
        self.finished.emit()
    
    def stop(self):
        self.running = False

# 训练工作线程
class TrainingWorker(QtCore.QObject):
    """强化学习训练工作线程"""
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
    
    def run(self):
        while True:
            if len(self.controller.memory) > 64:
                self.controller.update()
            time.sleep(0.1)  # 避免过度消耗CPU

class UltimateDroneControlSystem(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 初始化系统
        self.system = UltimateTripleSystem()
        
        # 设置窗口属性
        self.setWindowTitle("终极无人机容错控制系统 - 量子增强版")
        self.resize(1800, 1000)
        self.setStyleSheet(GLOBAL_STYLE)
        
        # 创建主界面
        self.init_ui()
        
        # 初始化数据
        self.init_data()
        
        # 添加性能监控
        self.performance_monitor = PerformanceMonitor()
        self.last_quantum_update = 0
        self.last_neuromorphic_update = 0
        self.last_blockchain_update = 0
        self.last_3d_update = 0
        
        # 启动工作线程
        self.start_worker_thread()
        
        # 启动强化学习训练线程
        self.start_rl_training()
    
    def start_worker_thread(self):
        # 创建工作线程
        self.worker_thread = QtCore.QThread()
        self.worker = SystemWorker(self.system)
        self.worker.moveToThread(self.worker_thread)
        self.worker.update_signal.connect(self.update_ui)
        
        # 连接线程信号
        self.worker_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        
        # 启动线程
        self.worker_thread.start()
    
    def start_rl_training(self):
        """启动强化学习训练线程"""
        self.training_thread = QtCore.QThread()
        self.training_worker = TrainingWorker(self.system.controller)
        self.training_worker.moveToThread(self.training_thread)
        self.training_thread.started.connect(self.training_worker.run)
        self.training_thread.start()
    
    def closeEvent(self, event):
        # 停止工作线程
        self.worker.stop()
        self.worker_thread.quit()
        self.worker_thread.wait()
        
        # 停止训练线程
        self.training_thread.quit()
        self.training_thread.wait()
        
        super().closeEvent(event)
    
    def init_ui(self):
        # 创建主窗口部件
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QtWidgets.QHBoxLayout(central_widget)
        
        # 左侧控制面板
        left_panel = QtWidgets.QTabWidget()
        left_panel.setTabPosition(QtWidgets.QTabWidget.TabPosition.West)
        main_layout.addWidget(left_panel, 1)
        
        # 右侧可视化面板
        right_panel = QtWidgets.QTabWidget()
        main_layout.addWidget(right_panel, 2)
        
        # 添加左侧标签页
        self.add_system_status_tab(left_panel)
        self.add_sensor_control_tab(left_panel)
        self.add_fault_injection_tab(left_panel)
        self.add_quantum_view_tab(left_panel)
        
        # 添加右侧标签页
        self.add_digital_twin_tab(right_panel)
        self.add_sensor_data_tab(right_panel)
        self.add_health_analysis_tab(right_panel)
        self.add_blockchain_view_tab(right_panel)
    
    def add_system_status_tab(self, parent):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        
        # 系统状态
        status_group = QtWidgets.QGroupBox("系统状态")
        status_layout = QtWidgets.QFormLayout()
        
        self.mode_label = QtWidgets.QLabel("正常")
        self.mode_label.setStyleSheet("color: green; font-weight: bold; font-size: 14pt;")
        self.uptime_label = QtWidgets.QLabel("0.0 s")
        self.health_label = QtWidgets.QLabel("100%")
        self.energy_label = QtWidgets.QLabel("100%")
        self.position_label = QtWidgets.QLabel("[0.00, 0.00, 0.00]")
        self.fault_detected_label = QtWidgets.QLabel("0")
        self.fault_predicted_label = QtWidgets.QLabel("0")
        
        status_layout.addRow("运行模式:", self.mode_label)
        status_layout.addRow("运行时间:", self.uptime_label)
        status_layout.addRow("系统健康度:", self.health_label)
        status_layout.addRow("剩余能量:", self.energy_label)
        status_layout.addRow("位置:", self.position_label)
        status_layout.addRow("检测到故障:", self.fault_detected_label)
        status_layout.addRow("预测到故障:", self.fault_predicted_label)
        
        status_group.setLayout(status_layout)
        
        # 环境状态
        env_group = QtWidgets.QGroupBox("环境状态")
        env_layout = QtWidgets.QFormLayout()
        
        self.wind_label = QtWidgets.QLabel("[0.00, 0.00, 0.00] m/s")
        self.turbulence_label = QtWidgets.QLabel("0.0")
        self.temperature_label = QtWidgets.QLabel("25.0°C")
        
        env_layout.addRow("风速:", self.wind_label)
        env_layout.addRow("湍流强度:", self.turbulence_label)
        env_layout.addRow("温度:", self.temperature_label)
        
        env_group.setLayout(env_layout)
        
        # 性能监控
        performance_group = QtWidgets.QGroupBox("性能监控")
        performance_layout = QtWidgets.QFormLayout()
        
        self.fps_label = QtWidgets.QLabel("0")
        self.cpu_label = QtWidgets.QLabel("0%")
        self.memory_label = QtWidgets.QLabel("0%")
        self.frame_time_label = QtWidgets.QLabel("0ms")
        self.cycle_time_label = QtWidgets.QLabel("0ms")
        
        performance_layout.addRow("帧率 (FPS):", self.fps_label)
        performance_layout.addRow("CPU 使用率:", self.cpu_label)
        performance_layout.addRow("内存使用率:", self.memory_label)
        performance_layout.addRow("帧时间:", self.frame_time_label)
        performance_layout.addRow("系统周期时间:", self.cycle_time_label)
        
        performance_group.setLayout(performance_layout)
        
        layout.addWidget(status_group)
        layout.addWidget(env_group)
        layout.addWidget(performance_group)
        layout.addStretch()
        
        parent.addTab(tab, "系统状态")
    
    def add_sensor_control_tab(self, parent):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        
        # 传感器状态
        sensor_group = QtWidgets.QGroupBox("传感器状态与控制")
        sensor_layout = QtWidgets.QGridLayout()
        
        self.sensor_widgets = {}
        colors = ['#FF5555', '#55FF55', '#5555FF']
        
        for i, name in enumerate(['primary', 'secondary', 'tertiary']):
            group = QtWidgets.QGroupBox(f"{name.capitalize()} 传感器")
            group_layout = QtWidgets.QFormLayout()
            
            # 健康状态
            health_label = QtWidgets.QLabel("正常")
            health_label.setStyleSheet("color: green; font-weight: bold;")
            
            # 权重
            weight_label = QtWidgets.QLabel("0.00")
            
            # 故障概率
            fault_prob_label = QtWidgets.QLabel("0.0%")
            
            # 权重控制滑块
            weight_slider = QtWidgets.QSlider(Qt.Orientation.Horizontal)
            weight_slider.setRange(0, 100)
            weight_slider.setValue(50 if i==0 else 30 if i==1 else 20)
            weight_slider.setStyleSheet("""
                QSlider::groove:horizontal {
                    height: 8px;
                    background: #1e3a8a;
                    border-radius: 4px;
                }
                QSlider::handle:horizontal {
                    background: #64ffda;
                    border: 1px solid #5eead4;
                    width: 16px;
                    margin: -4px 0;
                    border-radius: 8px;
                }
                QSlider::sub-page:horizontal {
                    background: #3b82f6;
                    border-radius: 4px;
                }
            """)
            
            # 数据可视化
            data_plot = pg.PlotWidget()
            data_plot.setBackground('#0a192f')
            data_plot.setYRange(-15, 15)
            data_plot.getAxis('left').setPen('#ccd6f6')
            data_plot.getAxis('bottom').setPen('#ccd6f6')
            curve_x = data_plot.plot(pen=pg.mkPen(color=colors[0], width=2), name="X")
            curve_y = data_plot.plot(pen=pg.mkPen(color=colors[1], width=2), name="Y")
            curve_z = data_plot.plot(pen=pg.mkPen(color=colors[2], width=2), name="Z")
            data_plot.setMinimumHeight(100)
            
            group_layout.addRow("健康状态:", health_label)
            group_layout.addRow("权重:", weight_label)
            group_layout.addRow("故障概率:", fault_prob_label)
            group_layout.addRow("权重调整:", weight_slider)
            group_layout.addRow(data_plot)
            
            group.setLayout(group_layout)
            sensor_layout.addWidget(group, i//2, i%2)
            
            self.sensor_widgets[name] = {
                'health': health_label,
                'weight': weight_label,
                'fault_prob': fault_prob_label,
                'slider': weight_slider,
                'curves': [curve_x, curve_y, curve_z]
            }
        
        sensor_group.setLayout(sensor_layout)
        layout.addWidget(sensor_group)
        
        parent.addTab(tab, "传感器控制")
    
    def add_fault_injection_tab(self, parent):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(tab)
        
        # 故障注入控制
        fault_group = QtWidgets.QGroupBox("故障注入系统")
        fault_layout = QtWidgets.QFormLayout()
        
        self.fault_type = QtWidgets.QComboBox()
        self.fault_type.addItems(["偏置故障", "漂移故障", "噪声故障", "卡死故障", "脉冲故障"])
        
        self.target_sensor = QtWidgets.QComboBox()
        self.target_sensor.addItems(["主传感器", "备传感器", "辅传感器"])
        
        self.magnitude = QtWidgets.QDoubleSpinBox()
        self.magnitude.setRange(0.1, 10.0)
        self.magnitude.setValue(2.0)
        
        self.duration = QtWidgets.QDoubleSpinBox()
        self.duration.setRange(0.5, 60.0)
        self.duration.setValue(5.0)
        
        self.inject_btn = QtWidgets.QPushButton("注入故障")
        self.inject_btn.setStyleSheet("background-color: #ef4444; font-weight: bold;")
        self.inject_btn.clicked.connect(self.inject_fault)
        
        fault_layout.addRow("故障类型:", self.fault_type)
        fault_layout.addRow("目标传感器:", self.target_sensor)
        fault_layout.addRow("强度:", self.magnitude)
        fault_layout.addRow("持续时间(s):", self.duration)
        fault_layout.addRow(self.inject_btn)
        
        fault_group.setLayout(fault_layout)
        layout.addWidget(fault_group)
        
        # 故障历史
        history_group = QtWidgets.QGroupBox("故障历史")
        history_layout = QtWidgets.QVBoxLayout()
        
        self.fault_history = QtWidgets.QTableWidget(10, 4)
        self.fault_history.setHorizontalHeaderLabels(["时间", "传感器", "故障类型", "状态"])
        self.fault_history.verticalHeader().setVisible(False)
        self.fault_history.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.fault_history.setStyleSheet("""
            QTableWidget {
                background-color: #112240;
                gridline-color: #1e3a8a;
            }
            QHeaderView::section {
                background-color: #1e3a8a;
                color: white;
                padding: 4px;
            }
        """)
        
        history_layout.addWidget(self.fault_history)
        history_group.setLayout(history_layout)
        layout.addWidget(history_group)
        
        parent.addTab(tab, "故障注入")
    
    def add_quantum_view_tab(self, parent):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        
        # 量子计算视图
        quantum_group = QtWidgets.QGroupBox("量子计算视图")
        quantum_layout = QtWidgets.QVBoxLayout()
        
        self.quantum_circuit_view = QtWidgets.QLabel()
        self.quantum_circuit_view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.quantum_circuit_view.setStyleSheet("background-color: #0a192f; border: 1px solid #1e3a8a; border-radius: 4px; padding: 10px;")
        self.quantum_circuit_view.setMinimumHeight(200)
        
        quantum_layout.addWidget(QtWidgets.QLabel("当前量子电路:"))
        quantum_layout.addWidget(self.quantum_circuit_view)
        
        # 量子状态可视化
        self.quantum_state_plot = pg.PlotWidget()
        self.quantum_state_plot.setBackground('#0a192f')
        self.quantum_state_plot.setTitle("量子状态概率分布", color="#64ffda")
        self.quantum_state_plot.getAxis('left').setPen('#ccd6f6')
        self.quantum_state_plot.getAxis('bottom').setPen('#ccd6f6')
        self.quantum_state_plot.setMinimumHeight(200)
        
        quantum_layout.addWidget(QtWidgets.QLabel("量子状态概率:"))
        quantum_layout.addWidget(self.quantum_state_plot)
        
        quantum_group.setLayout(quantum_layout)
        layout.addWidget(quantum_group)
        
        # 神经形态计算视图
        neuromorphic_group = QtWidgets.QGroupBox("神经形态计算视图")
        neuromorphic_layout = QtWidgets.QVBoxLayout()
        
        self.neuron_activity_plot = pg.PlotWidget()
        self.neuron_activity_plot.setBackground('#0a192f')
        self.neuron_activity_plot.setTitle("神经元活动", color="#64ffda")
        self.neuron_activity_plot.getAxis('left').setPen('#ccd6f6')
        self.neuron_activity_plot.getAxis('bottom').setPen('#ccd6f6')
        self.neuron_activity_plot.setMinimumHeight(200)
        
        neuromorphic_layout.addWidget(self.neuron_activity_plot)
        
        neuromorphic_group.setLayout(neuromorphic_layout)
        layout.addWidget(neuromorphic_group)
        
        parent.addTab(tab, "量子计算")
    
    def add_digital_twin_tab(self, parent):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        
        # 3D数字孪生视图
        self.twin_view = gl.GLViewWidget()
        self.twin_view.setCameraPosition(distance=50, elevation=30, azimuth=45)
        self.twin_view.setBackgroundColor('#0a192f')
        
        # 创建无人机模型（多个部件）
        self.drone_model = self.create_drone_3d()
        for part in self.drone_model:
            self.twin_view.addItem(part)
        
        # 创建轨迹
        self.trajectory = gl.GLLinePlotItem()
        self.trajectory.setData(pos=np.zeros((100, 3)), color=(1, 1, 0, 0.5), width=2)
        self.twin_view.addItem(self.trajectory)
        
        # 添加网格
        grid = gl.GLGridItem()
        grid.setSize(100, 100, 1)
        grid.setSpacing(5, 5, 5)
        grid.setColor('#1e3a8a')
        self.twin_view.addItem(grid)
        
        # 添加坐标系
        axis = gl.GLAxisItem()
        axis.setSize(10, 10, 10)
        self.twin_view.addItem(axis)
        
        # 添加风场可视化
        self.wind_arrows = []
        for _ in range(20):
            arrow = gl.GLLinePlotItem()
            arrow.setData(pos=np.zeros((2, 3)), color=(0, 0.8, 1, 0.7), width=1)
            self.twin_view.addItem(arrow)
            self.wind_arrows.append(arrow)
        
        layout.addWidget(self.twin_view)
        parent.addTab(tab, "数字孪生")
    
    def add_sensor_data_tab(self, parent):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        
        # 传感器数据图
        sensor_plot = pg.PlotWidget()
        sensor_plot.setBackground('#0a192f')
        sensor_plot.setTitle("传感器数据融合", color="#64ffda")
        sensor_plot.addLegend()
        sensor_plot.setLabel('left', '加速度', 'm/s²', color="#ccd6f6")
        sensor_plot.setLabel('bottom', '时间', 's', color="#ccd6f6")
        sensor_plot.getAxis('left').setPen('#ccd6f6')
        sensor_plot.getAxis('bottom').setPen('#ccd6f6')
        
        self.accel_curves = {
            'primary': sensor_plot.plot(pen=pg.mkPen(color='#FF5555', width=2), name='主传感器'),
            'secondary': sensor_plot.plot(pen=pg.mkPen(color='#55FF55', width=2), name='备传感器'),
            'tertiary': sensor_plot.plot(pen=pg.mkPen(color='#5555FF', width=2), name='辅传感器'),
            'fused': sensor_plot.plot(pen=pg.mkPen(color='#FFFFFF', width=3), name='融合输出')
        }
        
        layout.addWidget(sensor_plot)
        parent.addTab(tab, "传感器数据")
    
    def add_health_analysis_tab(self, parent):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        
        # 系统健康图
        health_plot = pg.PlotWidget()
        health_plot.setBackground('#0a192f')
        health_plot.setTitle("系统健康分析", color="#64ffda")
        health_plot.addLegend()
        health_plot.setLabel('left', '健康指标', color="#ccd6f6")
        health_plot.setLabel('bottom', '时间', 's', color="#ccd6f6")
        health_plot.getAxis('left').setPen('#ccd6f6')
        health_plot.getAxis('bottom').setPen('#ccd6f6')
        
        self.health_curve = health_plot.plot(pen=pg.mkPen(color='#10B981', width=2), name="系统健康度")
        self.energy_curve = health_plot.plot(pen=pg.mkPen(color='#3B82F6', width=2), name="剩余能量")
        self.fault_curve = health_plot.plot(pen=pg.mkPen(color='#EF4444', width=2), name="故障计数")
        
        layout.addWidget(health_plot)
        parent.addTab(tab, "健康分析")
    
    def add_blockchain_view_tab(self, parent):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        
        # 区块链视图
        blockchain_group = QtWidgets.QGroupBox("量子区块链日志")
        blockchain_layout = QtWidgets.QVBoxLayout()
        
        self.blockchain_view = QtWidgets.QTextEdit()
        self.blockchain_view.setReadOnly(True)
        self.blockchain_view.setFont(QtGui.QFont("Consolas", 10))
        self.blockchain_view.setStyleSheet("""
            QTextEdit {
                background-color: #0a192f;
                color: #64ffda;
                border: 1px solid #1e3a8a;
                border-radius: 4px;
            }
        """)
        
        blockchain_layout.addWidget(self.blockchain_view)
        blockchain_group.setLayout(blockchain_layout)
        layout.addWidget(blockchain_group)
        
        # 区块链验证
        validate_layout = QtWidgets.QHBoxLayout()
        self.validate_btn = QtWidgets.QPushButton("验证区块链完整性")
        self.validate_btn.clicked.connect(self.validate_blockchain)
        self.validation_label = QtWidgets.QLabel("未验证")
        
        validate_layout.addWidget(self.validate_btn)
        validate_layout.addWidget(self.validation_label)
        layout.addLayout(validate_layout)
        
        parent.addTab(tab, "区块链")
    
    def update_wind_visualization(self, wind_vector):
        """更新风场可视化"""
        scale = 0.5  # 缩放因子，使箭头长度适中
        wind_strength = np.linalg.norm(wind_vector)
        
        # 如果风太小，不显示箭头
        if wind_strength < 0.1:
            for arrow in self.wind_arrows:
                arrow.setData(pos=np.zeros((2, 3)))
            return
        
        # 计算风的方向向量
        wind_dir = wind_vector / wind_strength
        
        for i, arrow in enumerate(self.wind_arrows):
            # 创建随机位置（在场景中均匀分布）
            x = random.uniform(-40, 40)
            y = random.uniform(-40, 40)
            z = random.uniform(0, 20)
            start = np.array([x, y, z])
            
            # 计算终点位置
            end = start + wind_dir * wind_strength * scale
            
            # 设置箭头数据
            arrow.setData(pos=np.array([start, end]), color=(0, 0.8, 1, 0.7), width=1)

    def create_drone_3d(self):
        """创建详细的无人机3D模型"""
        # 主体（球体）
        body = gl.GLMeshItem(
            meshdata=gl.MeshData.sphere(rows=10, cols=15, radius=1.0),
            color=(0.2, 0.6, 1.0, 0.8),
            shader='shaded'
        )
        
        # 机臂（圆柱体） - 修复：radius 应该是列表
        arm_positions = [(1.5, 0, 0), (-1.5, 0, 0), (0, 1.5, 0), (0, -1.5, 0)]
        arms = []
        for pos in arm_positions:
            arm = gl.GLMeshItem(
                meshdata=gl.MeshData.cylinder(rows=5, cols=8, radius=[0.1, 0.1], length=1.5),  # 修改这里
                color=(0.4, 0.4, 0.5, 1),
                shader='shaded'
            )
            arm.rotate(90, 0, 1, 0)  # 旋转使圆柱体水平
            arm.translate(*pos)
            arms.append(arm)
        
        # 螺旋桨（扁圆柱体） - 修复：radius 应该是列表
        prop_positions = [(1.5, 0, 0.3), (-1.5, 0, 0.3), (0, 1.5, 0.3), (0, -1.5, 0.3)]
        props = []
        for pos in prop_positions:
            prop = gl.GLMeshItem(
                meshdata=gl.MeshData.cylinder(rows=5, cols=12, radius=[0.5, 0.5], length=0.05),  # 修改这里
                color=(0.9, 0.9, 0.2, 0.6),
                shader='shaded'
            )
            prop.translate(*pos)
            props.append(prop)
        
        # 返回所有部件
        return [body] + arms + props
    
    def init_data(self):
        # 初始化数据存储
        self.time_data = []
        self.health_data = []
        self.energy_data = []
        self.fault_data = []
        self.trajectory_data = deque(maxlen=500)
        self.wind_data = []
        
        # 初始化传感器数据
        self.sensor_history = {
            name: {'x': [], 'y': [], 'z': []} for name in ['primary', 'secondary', 'tertiary']
        }
        
        # 初始化量子状态数据
        self.quantum_states = np.zeros(8)
        
        # 初始化量子电路图
        self.init_quantum_circuit_image()
    
    def init_quantum_circuit_image(self):
        """创建并缓存量子电路图"""
        qc = QuantumCircuit(3)
        qc.h(0)
        qc.cx(0, 1)
        qc.cx(0, 2)
        
        try:
            img = qc.draw(output='mpl', style={'backgroundcolor': '#0a192f'})
            img.canvas.draw()
            img_arr = np.array(img.canvas.renderer.buffer_rgba())
            self.quantum_circuit_image = QtGui.QImage(
                img_arr, img_arr.shape[1], img_arr.shape[0], 
                QtGui.QImage.Format.Format_RGBA8888
            )
        except Exception as e:
            print(f"量子电路可视化错误: {e}")
            self.quantum_circuit_image = None
    
    def inject_fault(self):
        """处理故障注入"""
        fault_map = {
            "偏置故障": "bias",
            "漂移故障": "drift",
            "噪声故障": "noise",
            "卡死故障": "stuck",
            "脉冲故障": "spike"
        }
        sensor_map = {
            "主传感器": "primary",
            "备传感器": "secondary",
            "辅传感器": "tertiary"
        }
        
        fault_type = fault_map[self.fault_type.currentText()]
        target = sensor_map[self.target_sensor.currentText()]
        magnitude = self.magnitude.value()
        duration = self.duration.value()
        
        self.system.inject_fault(fault_type, target, magnitude, duration)
        
        # 添加到故障历史
        row_count = self.fault_history.rowCount()
        self.fault_history.insertRow(0)
        self.fault_history.setItem(0, 0, QtWidgets.QTableWidgetItem(time.strftime("%H:%M:%S")))
        self.fault_history.setItem(0, 1, QtWidgets.QTableWidgetItem(self.target_sensor.currentText()))
        self.fault_history.setItem(0, 2, QtWidgets.QTableWidgetItem(self.fault_type.currentText()))
        self.fault_history.setItem(0, 3, QtWidgets.QTableWidgetItem("已注入"))
        self.fault_history.item(0, 3).setForeground(QtGui.QColor('#10B981'))
    
    def validate_blockchain(self):
        """验证区块链完整性"""
        is_valid = self.system.blockchain.validate_chain()
        if is_valid:
            self.validation_label.setText("区块链有效")
            self.validation_label.setStyleSheet("color: #10B981; font-weight: bold;")
        else:
            self.validation_label.setText("区块链无效!")
            self.validation_label.setStyleSheet("color: #EF4444; font-weight: bold;")
    
    def update_drone_attitude(self, pos, attitude):
        """更新无人机姿态"""
        self.drone_model.resetTransform()
        self.drone_model.translate(pos[0], pos[1], pos[2])
        self.drone_model.rotate(attitude[0] * 180/np.pi, 1, 0, 0)
        self.drone_model.rotate(attitude[1] * 180/np.pi, 0, 1, 0)
        self.drone_model.rotate(attitude[2] * 180/np.pi, 0, 0, 1)
    
    def update_drone_attitude(self, pos, attitude):
        """更新无人机姿态"""
        # 重置所有部件的变换
        for part in self.drone_model:
            part.resetTransform()
        
        # 应用位置和平移
        for part in self.drone_model:
            part.translate(pos[0], pos[1], pos[2])
            part.rotate(attitude[0] * 180/np.pi, 1, 0, 0)
            part.rotate(attitude[1] * 180/np.pi, 0, 1, 0)
            part.rotate(attitude[2] * 180/np.pi, 0, 0, 1)
    
    def update_quantum_view(self):
        """更新量子计算视图"""
        # 使用缓存的量子电路图
        if self.quantum_circuit_image:
            pixmap = QtGui.QPixmap.fromImage(self.quantum_circuit_image)
            self.quantum_circuit_view.setPixmap(pixmap)
        else:
            self.quantum_circuit_view.setText("量子电路可视化")
        
        # 更新量子状态概率图
        self.quantum_states = np.random.rand(8)
        self.quantum_states /= self.quantum_states.sum()
        
        x = np.arange(8)
        self.quantum_state_plot.clear()
        bg = pg.BarGraphItem(x=x, height=self.quantum_states, width=0.6, brush='#3b82f6')
        self.quantum_state_plot.addItem(bg)
        self.quantum_state_plot.getAxis('bottom').setTicks([[(i, f'|{i:03b}>') for i in range(8)]])
    
    def update_neuromorphic_view(self):
        """更新神经形态计算视图"""
        # 模拟神经元活动
        time_points = np.linspace(0, 10, 100)
        neuron_activity = np.zeros((5, 100))
        
        for i in range(5):
            base = np.sin(time_points * (i+1) * 0.5)
            noise = np.random.normal(0, 0.1, 100)
            neuron_activity[i] = base + noise
        
        self.neuron_activity_plot.clear()
        colors = ['#FF5555', '#55FF55', '#5555FF', '#FFAA00', '#FF00FF']
        for i in range(5):
            self.neuron_activity_plot.plot(time_points, neuron_activity[i], pen=pg.mkPen(color=colors[i], width=2), name=f"神经元 {i+1}")
    
    def update_ui(self, report):
        """更新UI（由工作线程触发）"""
        # 更新性能监控
        self.performance_monitor.update()
        perf_report = self.performance_monitor.get_report()
        
        self.fps_label.setText(f"{perf_report['fps']:.1f}")
        self.cpu_label.setText(f"{perf_report['cpu']:.1f}%")
        self.memory_label.setText(f"{perf_report['memory']:.1f}%")
        self.frame_time_label.setText(f"{perf_report['avg_frame']:.1f}ms")
        self.cycle_time_label.setText(f"{report['performance']['cycle_time']:.1f}ms")
        
        # 更新系统状态
        self.mode_label.setText(report['status']['mode'])
        self.mode_label.setStyleSheet(
            "color: #10B981; font-weight: bold;" if report['status']['mode'] == 'NORMAL' else
            "color: #F59E0B; font-weight: bold;" if report['status']['mode'] == 'DEGRADED' else
            "color: #EF4444; font-weight: bold;"
        )
        self.uptime_label.setText(f"{report['status']['uptime']:.1f} s")
        self.health_label.setText(f"{report['status']['health']*100:.1f}%")
        self.energy_label.setText(f"{report['status']['energy']:.1f}%")
        self.position_label.setText(
            f"[{report['status']['position'][0]:.2f}, "
            f"{report['status']['position'][1]:.2f}, "
            f"{report['status']['position'][2]:.2f}]"
        )
        self.fault_detected_label.setText(str(report['status']['faults']['detected']))
        self.fault_predicted_label.setText(str(report['status']['faults']['predicted']))
        
        # 更新环境状态
        env = report['environment']
        self.wind_label.setText(f"[{env['wind'][0]:.2f}, {env['wind'][1]:.2f}, {env['wind'][2]:.2f}] m/s")
        self.turbulence_label.setText(f"{env['turbulence']:.2f}")
        self.temperature_label.setText(f"{env['temperature']:.1f}°C")
        
        # 更新传感器状态
        for name, sensor in report['sensors'].items():
            widgets = self.sensor_widgets[name]
            health = sensor['healthy']
            widgets['health'].setText("正常" if health else "故障")
            widgets['health'].setStyleSheet(
                "color: #10B981; font-weight: bold;" if health else "color: #EF4444; font-weight: bold;"
            )
            widgets['weight'].setText(f"{sensor['weight']:.3f}")
            
            # 更新滑块
            widgets['slider'].setValue(int(sensor['weight'] * 100))
            
            # 获取故障概率
            if self.system.history['predictions']:
                fault_prob = self.system.history['predictions'][-1][list(report['sensors'].keys()).index(name)]
                widgets['fault_prob'].setText(f"{fault_prob*100:.1f}%")
                widgets['fault_prob'].setStyleSheet(
                    "color: #EF4444; font-weight: bold;" if fault_prob > 0.7 else 
                    "color: #F59E0B;" if fault_prob > 0.3 else 
                    "color: #10B981;"
                )
        
        # 更新3D视图 - 降低更新频率
        current_time = time.time()
        if current_time - self.last_3d_update > 0.05:  # 20Hz
            pos = np.array(report['status']['position'])
            attitude = report['status']['attitude']
            self.update_drone_attitude(pos, attitude)
            
            # 更新轨迹
            self.trajectory_data.append(pos)
            self.trajectory.setData(pos=np.array(self.trajectory_data))
            
            # 更新风场可视化
            wind_vector = np.array(report['environment']['wind'])
            self.update_wind_visualization(wind_vector)
            
            self.last_3d_update = current_time
        
        # 更新健康图
        self.time_data.append(report['status']['uptime'])
        self.health_data.append(report['status']['health'])
        self.energy_data.append(report['status']['energy'] / 100)
        self.fault_data.append(report['status']['faults']['detected'] / 10)
        
        max_points = 200
        if len(self.time_data) > max_points:
            self.time_data = self.time_data[-max_points:]
            self.health_data = self.health_data[-max_points:]
            self.energy_data = self.energy_data[-max_points:]
            self.fault_data = self.fault_data[-max_points:]
        
        self.health_curve.setData(self.time_data, self.health_data)
        self.energy_curve.setData(self.time_data, self.energy_data)
        self.fault_curve.setData(self.time_data, self.fault_data)
        
        # 更新传感器数据图
        for name in self.sensor_widgets:
            sensors = self.system.sensors
            self.sensor_history[name]['x'].append(sensors[name]['accel'][0])
            self.sensor_history[name]['y'].append(sensors[name]['accel'][1])
            self.sensor_history[name]['z'].append(sensors[name]['accel'][2])
            
            if len(self.sensor_history[name]['x']) > max_points:
                for axis in ['x', 'y', 'z']:
                    self.sensor_history[name][axis] = self.sensor_history[name][axis][-max_points:]
            
            widgets = self.sensor_widgets[name]
            widgets['curves'][0].setData(self.sensor_history[name]['x'])
            widgets['curves'][1].setData(self.sensor_history[name]['y'])
            widgets['curves'][2].setData(self.sensor_history[name]['z'])
        
        # 更新融合数据图
        self.accel_curves['primary'].setData(self.sensor_history['primary']['x'])
        self.accel_curves['secondary'].setData(self.sensor_history['secondary']['x'])
        self.accel_curves['tertiary'].setData(self.sensor_history['tertiary']['x'])
        
        # 更新区块链视图 - 降低更新频率
        if current_time - self.last_blockchain_update > 2.0:  # 0.5Hz
            self.update_blockchain_view()
            self.last_blockchain_update = current_time
        
        # 更新量子视图 - 降低更新频率
        if current_time - self.last_quantum_update > 1.0:  # 1Hz
            self.update_quantum_view()
            self.last_quantum_update = current_time
        
        # 更新神经形态视图 - 降低更新频率
        if current_time - self.last_neuromorphic_update > 0.5:  # 2Hz
            self.update_neuromorphic_view()
            self.last_neuromorphic_update = current_time
    
    def update_blockchain_view(self):
        """更新区块链显示"""
        chain = self.system.blockchain.chain
        text = "量子区块链 (最近5个区块):\n\n"
        
        for block in chain[-5:]:
            text += f"区块 #{block['index']}\n"
            text += f"时间: {block['timestamp']}\n"
            text += f"前哈希: {block['previous_hash'][:12]}...\n"
            text += f"哈希: {block['hash'][:12]}...\n"
            
            # 处理量子签名可能为None的情况
            quantum_sig = block['quantum_signature']
            if quantum_sig is None:
                quantum_sig_str = "N/A (创世区块)"
            else:
                quantum_sig_str = f"{quantum_sig[:12]}..."
            
            text += f"量子签名: {quantum_sig_str}\n"
            text += f"Nonce: {block['nonce']}\n"
            text += "验证: " + ("有效" if self.system.blockchain.validate_chain() else "无效")
            text += "\n" + "-"*50 + "\n"
        
        self.blockchain_view.setText(text)

if __name__ == "__main__":
    # 创建预训练模型文件（简化版）
    model = QuantumSNN(input_dim=27)  # 修改为正确的输入维度
    torch.save(model.state_dict(), 'quantum_snn_predictor.pth')
    
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # 设置应用样式
    palette = QtGui.QPalette()
    palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor(10, 25, 47))
    palette.setColor(QtGui.QPalette.ColorRole.WindowText, QtGui.QColor(204, 214, 246))
    palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor(17, 34, 64))
    palette.setColor(QtGui.QPalette.ColorRole.AlternateBase, QtGui.QColor(30, 58, 138))
    palette.setColor(QtGui.QPalette.ColorRole.ToolTipBase, QtGui.QColor(10, 25, 47))
    palette.setColor(QtGui.QPalette.ColorRole.ToolTipText, QtGui.QColor(204, 214, 246))
    palette.setColor(QtGui.QPalette.ColorRole.Text, QtGui.QColor(204, 214, 246))
    palette.setColor(QtGui.QPalette.ColorRole.Button, QtGui.QColor(30, 58, 138))
    palette.setColor(QtGui.QPalette.ColorRole.ButtonText, QtGui.QColor(255, 255, 255))
    palette.setColor(QtGui.QPalette.ColorRole.BrightText, QtGui.QColor(100, 255, 218))
    palette.setColor(QtGui.QPalette.ColorRole.Highlight, QtGui.QColor(59, 130, 246))
    palette.setColor(QtGui.QPalette.ColorRole.HighlightedText, QtGui.QColor(0, 0, 0))
    app.setPalette(palette)
    
    window = UltimateDroneControlSystem()
    window.show()
    sys.exit(app.exec())