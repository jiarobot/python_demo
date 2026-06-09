import sys
import numpy as np
import pyqtgraph as pg
import pyqtgraph.opengl as gl
from pyqtgraph.opengl import (
    GLViewWidget, GLBoxItem, GLLinePlotItem, 
    GLTextItem, GLSurfacePlotItem, GLScatterPlotItem, GLMeshItem
)
# 移除错误的导入
# from pyqtgraph.opengl.meshdata import sphere
import qutip as qt
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QPointF, QSize, QElapsedTimer 
from PyQt6.QtGui import (QColor, QFont, QPixmap, QImage, QPainter, QPen, 
                         QLinearGradient, QRadialGradient, QBrush, QPolygonF,
                         QFontMetrics, QAction, QIcon, QVector3D, QQuaternion,
                         QKeySequence, QShortcut, QMatrix4x4, QVector4D)
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QSplitter, QTabWidget, QGroupBox, QLabel, QPushButton, 
                            QComboBox, QSlider, QGraphicsView, QGraphicsScene, QGraphicsItem,
                            QTextEdit, QLineEdit, QFrame, QStatusBar, QMenuBar, QMenu,
                            QDialog, QProgressBar, QToolBar, QDockWidget, QSizePolicy,
                            QFileDialog, QMessageBox, QInputDialog, QTreeWidget, QTreeWidgetItem,
                            QStackedWidget, QFormLayout, QDoubleSpinBox, QCheckBox, QListWidget,QSplashScreen,
                            QListWidgetItem, QScrollArea, QSizeGrip, QProgressDialog)

# === 量子-生物混合计算核心 ===
class QuantumBioHybridComputer:
    def __init__(self, num_qubits=12, num_bio_units=8):
        self.num_qubits = num_qubits
        self.num_bio_units = num_bio_units
        self.quantum_state = qt.basis(2**num_qubits, 0)
        self.bio_state = np.zeros(num_bio_units, dtype=np.complex128)
        self.entanglement_map = {}
        self.hybrid_circuits = {}
        self.initialize_system()
        
    def initialize_system(self):
        """初始化量子-生物混合系统"""
        # 创建量子比特
        self.qubits = [qt.basis(2, 0) for _ in range(self.num_qubits)]
        
        # 初始化生物单元状态
        for i in range(self.num_bio_units):
            self.bio_state[i] = np.random.uniform(0.1, 0.9) * np.exp(1j * np.random.uniform(0, 2*np.pi))
        
        # 预定义混合电路
        self.hybrid_circuits['metabolic_optimization'] = self.create_metabolic_circuit()
        self.hybrid_circuits['pollution_response'] = self.create_pollution_response_circuit()
        self.hybrid_circuits['resource_balancing'] = self.create_resource_balancing_circuit()
        
    def create_metabolic_circuit(self):
        """创建代谢优化混合电路"""
        circuit = {
            'quantum_gates': [
                ('h', 0), ('cnot', (0, 1)), ('rz', (2, np.pi/4)),
                ('crx', (3, 4, np.pi/3))
            ],
            'bio_operations': [
                ('amplify', 1, 0.8), ('inhibit', 3, 0.4),
                ('resonate', (2, 5), 0.6)
            ],
            'entanglement': [(0, 'bio1'), (2, 'bio3')]
        }
        return circuit
    
    def create_pollution_response_circuit(self):
        """创建污染响应混合电路"""
        circuit = {
            'quantum_gates': [
                ('x', 0), ('y', 1), ('cz', (0, 2)),
                ('rxx', (3, 4, np.pi/2))
            ],
            'bio_operations': [
                ('purify', 0, 1.2), ('neutralize', 2, 0.9),
                ('cascade', (1, 4), 0.7)
            ],
            'entanglement': [(1, 'bio0'), (3, 'bio2')]
        }
        return circuit
    
    def create_resource_balancing_circuit(self):
        """创建资源平衡混合电路"""
        circuit = {
            'quantum_gates': [
                ('s', 0), ('t', 1), ('swap', (0, 2)),
                ('ccx', (3, 4, 5))
            ],
            'bio_operations': [
                ('balance', 0, 0.5), ('distribute', 1, 0.6),
                ('synchronize', (2, 3), 0.8)
            ],
            'entanglement': [(4, 'bio4'), (5, 'bio6')]
        }
        return circuit
    
    def execute_circuit(self, circuit_name):
        """执行指定的混合电路"""
        if circuit_name not in self.hybrid_circuits:
            raise ValueError(f"未知电路: {circuit_name}")
        
        circuit = self.hybrid_circuits[circuit_name]
        
        # 执行量子门操作
        for gate in circuit['quantum_gates']:
            self.apply_quantum_gate(*gate)
            
        # 执行生物操作
        for op in circuit['bio_operations']:
            self.apply_bio_operation(*op)
            
        # 建立纠缠
        for ent in circuit['entanglement']:
            self.entangle(ent[0], ent[1])
            
        # 同步状态
        self.synchronize_states()
        
    def apply_quantum_gate(self, gate_type, targets, param=None):
        """应用量子门操作"""
        if gate_type == 'h':
            # Hadamard门
            gate = qt.hadamard_transform()
            self.qubits[targets] = gate * self.qubits[targets]
        elif gate_type == 'cnot':
            # CNOT门
            control, target = targets
            gate = qt.cnot(N=2, control=control, target=target)
            self.qubits[control] = gate * self.qubits[control]
        # ... 其他量子门实现 ...
            
    def apply_bio_operation(self, op_type, targets, strength):
        """应用生物操作"""
        if op_type == 'amplify':
            # 放大生物信号
            self.bio_state[targets] *= (1 + strength)
        elif op_type == 'inhibit':
            # 抑制生物信号
            self.bio_state[targets] *= (1 - strength)
        elif op_type == 'resonate':
            # 共振耦合
            unit1, unit2 = targets
            phase_diff = np.angle(self.bio_state[unit1]) - np.angle(self.bio_state[unit2])
            self.bio_state[unit1] *= np.exp(1j * phase_diff * strength)
            self.bio_state[unit2] *= np.exp(-1j * phase_diff * strength)
        # ... 其他生物操作实现 ...
            
    def entangle(self, qubit_idx, bio_unit_id):
        """建立量子比特与生物单元的纠缠"""
        self.entanglement_map[qubit_idx] = bio_unit_id
        
    def synchronize_states(self):
        """同步量子态与生物态"""
        for qubit_idx, bio_unit_id in self.entanglement_map.items():
            # 获取量子态相位
            quantum_phase = np.angle(qt.expect(qt.sigmaz(), self.qubits[qubit_idx]))
            
            # 更新生物态相位
            bio_magnitude = np.abs(self.bio_state[bio_unit_id])
            self.bio_state[bio_unit_id] = bio_magnitude * np.exp(1j * quantum_phase)
            
    def measure_system(self):
        """测量混合系统状态"""
        quantum_results = []
        for i in range(self.num_qubits):
            prob_0 = qt.expect(qt.projection(2, i, 0), self.qubits[i])
            quantum_results.append(prob_0)
            
        bio_results = {
            'magnitudes': np.abs(self.bio_state),
            'phases': np.angle(self.bio_state)
        }
        
        return {
            'quantum': quantum_results,
            'biological': bio_results
        }

# === 自适应城市代谢网络 ===
class AdaptiveMetabolicNetwork:
    def __init__(self, city_model):
        self.city_model = city_model
        self.network_graph = self.build_initial_network()
        self.performance_history = []
        self.learning_rate = 0.1
    
    def get_node(self, node_id):
        """根据节点ID返回节点"""
        for node in self.network_graph['nodes']:
            if node['id'] == node_id:
                return node
        return None
    
    def build_initial_network(self):
        """构建初始代谢网络"""
        graph = {
            'nodes': [],
            'edges': [],
            'resources': {}
        }
        
        # 添加区域节点
        for region in self.city_model['regions']:
            node = {
                'id': region['id'],
                'type': 'region',
                'capacity': 100,
                'load': 0,
                'connections': []
            }
            graph['nodes'].append(node)
            
        # 添加处理中心节点
        centers = ['water_processing', 'energy_generation', 'waste_recycling']
        for center in centers:
            node = {
                'id': center,
                'type': 'center',
                'capacity': 200,
                'load': 0,
                'connections': []
            }
            graph['nodes'].append(node)
            
        # 添加连接边
        connections = [
            ('NW', 'water_processing'), ('NE', 'water_processing'),
            ('SW', 'water_processing'), ('SE', 'water_processing'),
            ('water_processing', 'energy_generation'),
            ('energy_generation', 'waste_recycling'),
            ('waste_recycling', 'NW'), ('waste_recycling', 'NE'),
            ('waste_recycling', 'SW'), ('waste_recycling', 'SE')
        ]
        
        for source, target in connections:
            edge = {
                'source': source,
                'target': target,
                'capacity': 150,
                'load': 0,
                'latency': 5
            }
            graph['edges'].append(edge)
            # 添加到节点连接
            self.add_connection(graph, source, target)
            
        return graph
    
    def add_connection(self, graph, source, target):
        """添加节点连接"""
        for node in graph['nodes']:
            if node['id'] == source:
                node['connections'].append(target)
            if node['id'] == target:
                node['connections'].append(source)
                
    def update_network(self, city_state):
        """根据城市状态更新网络负载"""
        # 重置负载
        for node in self.network_graph['nodes']:
            node['load'] = 0
        for edge in self.network_graph['edges']:
            edge['load'] = 0
            
        # 计算区域负载
        for region in city_state['regions']:
            node = self.get_node(region['id'])
            if node:
                # 负载基于废物水平和污染指数
                node['load'] = region['waste_level'] * 0.7 + region['pollution_index'] * 0.3
                
        # 计算处理中心负载
        total_waste = sum(r['waste_level'] for r in city_state['regions'])
        total_pollution = sum(r['pollution_index'] for r in city_state['regions'])
        
        water_center = self.get_node('water_processing')
        if water_center:
            water_center['load'] = total_pollution * 0.8
            
        energy_center = self.get_node('energy_generation')
        if energy_center:
            energy_center['load'] = total_waste * 0.6
            
        waste_center = self.get_node('waste_recycling')
        if waste_center:
            waste_center['load'] = total_waste * 0.9
            
        # 计算边负载
        for edge in self.network_graph['edges']:
            source_node = self.get_node(edge['source'])
            target_node = self.get_node(edge['target'])
            if source_node and target_node:
                edge['load'] = (source_node['load'] + target_node['load']) / 2
                
        # 评估网络性能
        performance = self.calculate_performance()
        self.performance_history.append(performance)
        
        # 自适应调整
        if performance < 0.8:
            self.adapt_network()
            
    def calculate_performance(self):
        """计算网络性能指标"""
        max_node_load = max(node['load'] for node in self.network_graph['nodes'])
        max_edge_load = max(edge['load'] for edge in self.network_graph['edges'])
        
        node_performance = 1 - (max_node_load / 100)
        edge_performance = 1 - (max_edge_load / 150)
        
        return (node_performance + edge_performance) / 2
    
    def adapt_network(self):
        """自适应调整网络结构"""
        # 识别瓶颈
        bottlenecks = self.identify_bottlenecks()
        
        # 应用优化
        for node_id in bottlenecks['nodes']:
            self.enhance_node(node_id)
            
        for edge in bottlenecks['edges']:
            self.enhance_edge(edge)
            
        # 添加新连接
        if len(bottlenecks['critical_pairs']) > 0:
            source, target = bottlenecks['critical_pairs'][0]
            self.add_new_connection(source, target)
            
    def identify_bottlenecks(self):
        """识别网络瓶颈"""
        bottlenecks = {
            'nodes': [],
            'edges': [],
            'critical_pairs': []
        }
        
        # 识别高负载节点
        for node in self.network_graph['nodes']:
            if node['load'] > node['capacity'] * 0.9:
                bottlenecks['nodes'].append(node['id'])
                
        # 识别高负载边
        for edge in self.network_graph['edges']:
            if edge['load'] > edge['capacity'] * 0.85:
                bottlenecks['edges'].append((edge['source'], edge['target']))
                
        # 识别关键节点对
        for i in range(len(self.network_graph['nodes'])):
            for j in range(i+1, len(self.network_graph['nodes'])):
                node1 = self.network_graph['nodes'][i]
                node2 = self.network_graph['nodes'][j]
                if node1['id'] not in node2['connections']:
                    # 计算潜在负载减少
                    load_reduction = min(node1['load'], node2['load']) * 0.5
                    if load_reduction > 20:  # 如果减少负载超过20，则认为是关键对
                        bottlenecks['critical_pairs'].append((node1['id'], node2['id']))
                        
        return bottlenecks
    
    def enhance_node(self, node_id):
        """增强节点能力"""
        node = self.get_node(node_id)
        if node:
            node['capacity'] *= 1.2
            print(f"增强节点 {node_id} 容量至 {node['capacity']}")
            
    def enhance_edge(self, edge):
        """增强边能力"""
        for e in self.network_graph['edges']:
            if e['source'] == edge[0] and e['target'] == edge[1]:
                e['capacity'] *= 1.15
                e['latency'] *= 0.9
                print(f"增强边 {edge[0]}-{edge[1]} 容量至 {e['capacity']}")
                
    def add_new_connection(self, source, target):
        """添加新连接"""
        edge = {
            'source': source,
            'target': target,
            'capacity': 100,
            'load': 0,
            'latency': 8
        }
        self.network_graph['edges'].append(edge)
        self.add_connection(self.network_graph, source, target)
        print(f"添加新连接: {source} - {target}")

# === 跨维度通信协议 ===
class CrossDimensionProtocol:
    def __init__(self, quantum_system, bio_system, network):
        self.quantum_system = quantum_system
        self.bio_system = bio_system
        self.network = network
        self.encryption_key = self.generate_quantum_key()
        self.protocols = self.initialize_protocols()
        
    def generate_quantum_key(self, length=512):
        """生成量子密钥"""
        return np.random.randint(0, 2, size=length)
    
    def initialize_protocols(self):
        """初始化通信协议"""
        return {
            'Q2B': self.quantum_to_bio,
            'B2Q': self.bio_to_quantum,
            'Q2N': self.quantum_to_network,
            'N2B': self.network_to_bio,
            'EMERGENCY': self.emergency_broadcast
        }
    
    def quantum_to_bio(self, data):
        """量子到生物通信"""
        # 加密数据
        encrypted = self.encrypt_data(data)
        
        # 转换为生物信号
        bio_signal = self.convert_to_bio_signal(encrypted)
        
        # 传输到生物系统
        self.bio_system.receive_signal(bio_signal)
        
    def bio_to_quantum(self, data):
        """生物到量子通信"""
        # 转换生物数据为量子态
        quantum_state = self.convert_to_quantum_state(data)
        
        # 传输到量子系统
        self.quantum_system.receive_state(quantum_state)
    
    def quantum_to_network(self, data):
        """量子到网络通信"""
        # 解密数据
        decrypted = self.decrypt_data(data)
        
        # 转换为网络指令
        network_command = self.parse_network_command(decrypted)
        
        # 执行网络指令
        self.network.execute_command(network_command)
    
    def network_to_bio(self, data):
        """网络到生物通信"""
        # 转换为生物指令
        bio_command = self.parse_bio_command(data)
        
        # 传输到生物系统
        self.bio_system.execute_command(bio_command)
    
    def emergency_broadcast(self, message):
        """紧急广播"""
        # 全系统广播
        self.quantum_system.receive_emergency(message)
        self.bio_system.receive_emergency(message)
        self.network.receive_emergency(message)
    
    def encrypt_data(self, data):
        """使用量子密钥加密数据"""
        # 简单的异或加密
        encrypted = []
        key_index = 0
        for byte in data:
            encrypted_byte = byte ^ self.encryption_key[key_index]
            encrypted.append(encrypted_byte)
            key_index = (key_index + 1) % len(self.encryption_key)
        return bytes(encrypted)
    
    def decrypt_data(self, data):
        """解密数据"""
        # 加密和解密使用相同方法
        return self.encrypt_data(data)
    
    def convert_to_bio_signal(self, data):
        """将数据转换为生物信号"""
        # 简化的转换：将字节映射为生物信号参数
        return {
            'frequency': data[0] * 10,
            'amplitude': data[1] / 255.0,
            'duration': data[2] * 0.1
        }
    
    def convert_to_quantum_state(self, data):
        """将生物数据转换为量子态"""
        # 使用数据创建量子态
        state_vector = np.zeros(2**8, dtype=complex)
        for i, byte in enumerate(data[:256]):  # 使用前256字节
            state_vector[i] = byte / 255.0
        # 归一化
        norm = np.linalg.norm(state_vector)
        return state_vector / norm
    
    def parse_network_command(self, data):
        """解析网络指令"""
        # 简化的指令解析
        command_str = data.decode('utf-8', errors='ignore')
        if "ENHANCE" in command_str:
            parts = command_str.split()
            return {'type': 'enhance', 'target': parts[1], 'factor': float(parts[2])}
        elif "ADD_CONNECTION" in command_str:
            parts = command_str.split()
            return {'type': 'add_connection', 'source': parts[1], 'target': parts[2]}
        else:
            return {'type': 'unknown', 'data': command_str}
    
    def parse_bio_command(self, data):
        """解析生物指令"""
        # 简化的指令解析
        if "ACTIVATE" in data:
            return {'type': 'activate', 'strain': data.split()[1], 'level': float(data.split()[2])}
        elif "MUTATE" in data:
            return {'type': 'mutate', 'strain': data.split()[1], 'feature': data.split()[2]}
        else:
            return {'type': 'unknown', 'data': data}

# === 全息指挥中心 ===
class HolographicCommandCenter(gl.GLViewWidget):
    def __init__(self, city_model, network, quantum_bio_system, parent=None):
        super().__init__(parent)
        self.city_model = city_model
        self.network = network
        self.quantum_bio_system = quantum_bio_system
        self.setCameraPosition(distance=300, elevation=30, azimuth=45)
        self.holographic_items = []
        self.control_holograms = []
        self.data_streams = []
        self.init_holographic_display()
        
    def init_holographic_display(self):
        """初始化全息显示"""
        # 创建城市全息模型
        self.create_city_hologram()
        
        # 创建代谢网络全息图
        self.create_network_hologram()
        
        # 创建量子-生物系统全息图
        self.create_quantum_bio_hologram()
        
        # 创建控制面板全息投影
        self.create_control_panels()
        
        # 创建数据流全息图
        self.create_data_streams()
        
    def create_city_hologram(self):
        """创建城市全息模型"""
        # 使用3D图形表示城市区域
        for region in self.city_model['regions']:
            # 根据区域类型和状态设置不同颜色和形状
            color = self.get_region_color(region)
            pos = self.get_region_position(region['id'])
            
            # 创建区域立方体
            item = GLBoxItem()
            item.setSize(x=30, y=30, z=region['energy_output'] * 0.7)
            item.translate(pos[0], pos[1], region['energy_output'] * 0.35)
            item.setColor(color)
            self.addItem(item)
            self.holographic_items.append(item)
            
            # 添加区域标签 - 使用3D坐标
            text_pos = QVector3D(pos[0], pos[1], region['energy_output'] * 0.7 + 10)
            text = gl.GLTextItem(pos=text_pos, 
                    text=region['name'], font=QFont('Arial', 12), color=(255, 255, 255, 255))
            self.addItem(text)
            self.holographic_items.append(text)
            
    # 修改创建网络全息图的部分代码
    def create_network_hologram(self):
        """创建代谢网络全息图"""
        # 创建节点
        node_positions = {}
        for node in self.network['nodes']:
            pos = self.get_node_position(node['id'])
            node_positions[node['id']] = pos
            
            # 创建节点球体 - 使用GLMeshItem替代GLSphereItem
            load_ratio = node['load'] / node['capacity']
            color = (1.0, 1.0 - load_ratio, 1.0 - load_ratio, 0.8)  # RGBA元组
            
            # 创建球体网格
            meshdata = gl.MeshData.sphere(rows=10, cols=10, radius=5)
            sphere_item = GLMeshItem(meshdata=meshdata, smooth=True, color=color, shader='shaded')
            sphere_item.translate(pos[0], pos[1], pos[2])
            
            self.addItem(sphere_item)
            self.holographic_items.append(sphere_item)
            
            # 添加节点标签 - 使用3D坐标
            text_pos = (pos[0], pos[1], pos[2] + 8)  # 使用三元组而不是QVector3D
            text = gl.GLTextItem(pos=text_pos, 
                                text=node['id'], font=QFont('Arial', 10),
                                color=QColor(200, 200, 255))
            self.addItem(text)
            self.holographic_items.append(text)
            
        # 创建边
        for edge in self.network['edges']:
            if edge['source'] in node_positions and edge['target'] in node_positions:
                start = node_positions[edge['source']]
                end = node_positions[edge['target']]
                
                # 创建连接线
                line = GLLinePlotItem()
                line.setData(
                    pos=np.array([[start[0], start[1], start[2]], [end[0], end[1], end[2]]]),
                    color=self.get_edge_color(edge),
                    width=3,
                    antialias=True
                )
                self.addItem(line)
                self.holographic_items.append(line)
                
                # 添加负载指示器 - 使用3D坐标
                load_ratio = edge['load'] / edge['capacity']
                mid_x = (start[0] + end[0]) / 2
                mid_y = (start[1] + end[1]) / 2
                mid_z = (start[2] + end[2]) / 2
                text_pos = (mid_x, mid_y, mid_z + 5)  # 使用三元组而不是QVector3D
                text = gl.GLTextItem(pos=text_pos, 
                                    text=f"{load_ratio*100:.1f}%", font=QFont('Arial', 8),
                                    color=QColor(255, 255, 0))
                self.addItem(text)
                self.holographic_items.append(text)
                
    def create_quantum_bio_hologram(self):
        """创建量子-生物系统全息图"""
        # 量子系统可视化
        quantum_pos = (-100, 100)
        
        # 量子系统主球体 - 使用GLMeshItem
        meshdata = gl.MeshData.sphere(rows=15, cols=15, radius=15)
        quantum_sphere = GLMeshItem(meshdata=meshdata, smooth=True, 
                                   color=(0.39, 0.78, 1.0, 0.59), shader='shaded')  # RGBA元组
        quantum_sphere.translate(quantum_pos[0], quantum_pos[1], 0)
        self.addItem(quantum_sphere)
        self.holographic_items.append(quantum_sphere)
        
        # 量子比特
        for i in range(12):
            angle = i * np.pi / 6
            x = quantum_pos[0] + 20 * np.cos(angle)
            y = quantum_pos[1] + 20 * np.sin(angle)
            
            # 量子比特球体 - 使用GLMeshItem
            meshdata = gl.MeshData.sphere(rows=8, cols=8, radius=3)
            qubit = GLMeshItem(meshdata=meshdata, smooth=True, 
                              color=(1.0, 0.39, 0.39, 0.78), shader='shaded')  # RGBA元组
            qubit.translate(x, y, 0)
            self.addItem(qubit)
            self.holographic_items.append(qubit)
            
        # 生物系统可视化
        bio_pos = (100, 100)
        
        # 生物系统主球体 - 使用GLMeshItem
        meshdata = gl.MeshData.sphere(rows=15, cols=15, radius=15)
        bio_sphere = GLMeshItem(meshdata=meshdata, smooth=True, 
                               color=(0.39, 1.0, 0.39, 0.59), shader='shaded')  # RGBA元组
        bio_sphere.translate(bio_pos[0], bio_pos[1], 0)
        self.addItem(bio_sphere)
        self.holographic_items.append(bio_sphere)
        
        # 生物单元
        for i in range(8):
            angle = i * np.pi / 4
            x = bio_pos[0] + 20 * np.cos(angle)
            y = bio_pos[1] + 20 * np.sin(angle)
            
            # 生物单元球体 - 使用GLMeshItem
            meshdata = gl.MeshData.sphere(rows=8, cols=8, radius=3)
            bio_unit = GLMeshItem(meshdata=meshdata, smooth=True, 
                                 color=(0.39, 0.39, 1.0, 0.78), shader='shaded')  # RGBA元组
            bio_unit.translate(x, y, 0)
            self.addItem(bio_unit)
            self.holographic_items.append(bio_unit)
            
        # 量子-生物连接
        for i in range(4):
            q_angle = i * np.pi / 2
            b_angle = i * np.pi / 2 + np.pi/4
            qx = quantum_pos[0] + 20 * np.cos(q_angle)
            qy = quantum_pos[1] + 20 * np.sin(q_angle)
            bx = bio_pos[0] + 20 * np.cos(b_angle)
            by = bio_pos[1] + 20 * np.sin(b_angle)
            
            line = gl.GLLinePlotItem()
            line.setData(
                pos=np.array([[qx, qy, 0], [bx, by, 0]]),
                color=(1.0, 0.5, 0.0, 0.7),
                width=2,
                antialias=True
            )
            self.addItem(line)
            self.holographic_items.append(line)
            
    def create_control_panels(self):
        """创建漂浮在空中的全息控制面板"""
        # 在四个方向创建控制面板
        for i, angle in enumerate([45, 135, 225, 315]):
            rad = np.deg2rad(angle)
            radius = 80
            x = radius * np.cos(rad)
            y = radius * np.sin(rad)
            z = 50
            
            # 创建面板（使用一个平面）
            panel = GLSurfacePlotItem(
                x=np.array([-15, 15]),
                y=np.array([-10, 10]),
                z=np.array([[0,0],[0,0]]),
                color=(0.2, 0.5, 1.0, 0.3)
            )
            panel.translate(x, y, z)
            panel.rotate(angle, 0, 0, 1)
            self.addItem(panel)
            self.control_holograms.append(panel)
            
            # 添加面板标签
            labels = ["量子控制", "生物调节", "网络优化", "系统监控"]
            text = gl.GLTextItem(pos=QVector3D(x, y, z+12), 
                    text=labels[i], font=QFont('Arial', 14),
                    color=QColor(255, 255, 0))
            self.addItem(text)
            self.control_holograms.append(text)
            
    def create_particle_stream(self, source_id, target_id):
        """创建粒子流效果"""
        source_pos = self.get_node_position(source_id) if source_id in ['water_processing', 'energy_generation', 'waste_recycling'] else self.get_region_position(source_id)
        target_pos = self.get_node_position(target_id) if target_id in ['water_processing', 'energy_generation', 'waste_recycling'] else self.get_region_position(target_id)
        
        if not source_pos or not target_pos:
            return None
            
        # 创建粒子系统
        particle_count = 50
        positions = np.zeros((particle_count, 3))
        
        # 沿路径分布粒子
        for i in range(particle_count):
            t = i / particle_count
            x = source_pos[0] + (target_pos[0] - source_pos[0]) * t
            y = source_pos[1] + (target_pos[1] - source_pos[1]) * t
            z = source_pos[2] + (target_pos[2] - source_pos[2]) * t + 10 * np.sin(t * np.pi)  # 正弦波效果
            positions[i] = [x, y, z]
        
        # 创建颜色数组（所有粒子相同颜色）
        colors = np.zeros((particle_count, 4))
        colors[:] = (0, 1, 1, 0.7)  # RGBA
        # 创建大小数组（所有粒子相同大小）
        sizes = np.full(particle_count, 0.5)
            
        # 创建粒子项
        particles = GLScatterPlotItem()
        particles.setData(
            pos=positions,
            color=colors,
            size=sizes,
            pxMode=False
        )
        
        # 存储数据以便更新
        particles.particle_positions = positions
        particles.particle_colors = colors
        particles.particle_sizes = sizes
        
        return particles
    
    def update_data_streams(self):
        """更新数据流效果"""
        for stream in self.data_streams:
            if stream is None:
                continue
            # 移动粒子：每个粒子在x方向上移动0.5
            stream.particle_positions[:, 0] += 0.5
            # 重置超出范围的粒子
            for i in range(len(stream.particle_positions)):
                if stream.particle_positions[i, 0] > 100:
                    stream.particle_positions[i, 0] = -100
            # 更新粒子流数据
            stream.setData(
                pos=stream.particle_positions,
                color=stream.particle_colors,
                size=stream.particle_sizes,
                pxMode=False
            )
            
    def create_data_streams(self):
        """创建数据流全息图，显示资源流动和信息传递"""
        # 在关键节点之间创建动态数据流
        stream_pairs = [
            ('NW', 'water_processing'), ('NE', 'water_processing'),
            ('water_processing', 'energy_generation'),
            ('energy_generation', 'waste_recycling'),
            ('waste_recycling', 'SW'), ('waste_recycling', 'SE')
        ]
        
        for source, target in stream_pairs:
            # 创建流动粒子效果
            stream = self.create_particle_stream(source, target)
            if stream:
                self.addItem(stream)
                self.data_streams.append(stream)
    
    def get_region_color(self, region):
        """根据区域状态获取颜色"""
        # 使用水质决定颜色（蓝色）
        water_quality = region['water_quality'] / 100.0
        # 使用污染指数决定红色分量
        pollution = region['pollution_index'] / 20.0
        return (pollution, water_quality, 1.0 - pollution, 0.8)
        
    def get_region_position(self, region_id):
        """获取区域位置（返回3D坐标）"""
        positions = {
            'NW': (-50, -50, 0),
            'NE': (50, -50, 0),
            'SW': (-50, 50, 0),
            'SE': (50, 50, 0)
        }
        return positions.get(region_id, (0, 0, 0))

    def get_node_position(self, node_id):
        """获取节点位置（返回3D坐标）"""
        # 区域节点
        region_positions = {
            'NW': (-50, -50, 0),
            'NE': (50, -50, 0),
            'SW': (-50, 50, 0),
            'SE': (50, 50, 0)
        }
        if node_id in region_positions:
            return region_positions[node_id]
        
        # 处理中心节点
        center_positions = {
            'water_processing': (0, -80, 0),
            'energy_generation': (0, 0, 0),
            'waste_recycling': (0, 80, 0)
        }
        pos = center_positions.get(node_id, (0, 0, 0))
        return (pos[0], pos[1], pos[2])  # 确保返回三元组
    
    def get_edge_color(self, edge):
        """获取边颜色"""
        load_ratio = edge['load'] / edge['capacity']
        return (1.0, 1.0 - load_ratio, 0, 0.8)
    
    def update_hologram(self, city_model, network):
        """更新全息显示"""
        self.city_model = city_model
        self.network = network
        
        # 清除旧项目
        for item in self.holographic_items:
            self.removeItem(item)
        self.holographic_items = []
        
        # 重新创建全息图
        self.create_city_hologram()
        self.create_network_hologram()
        
        # 更新数据流
        self.update_data_streams()

# === 元胞自动机模拟 ===
class CellularAutomataSimulator:
    def __init__(self, width=50, height=50, depth=20):
        self.width = width
        self.height = height
        self.depth = depth
        self.grid = np.zeros((width, height, depth), dtype=np.float32)
        self.rules = self.default_rules()
        self.initialize_grid()
        
    def default_rules(self):
        """定义默认规则"""
        return {
            'diffusion_rate': 0.05,
            'reaction_threshold': 0.6,
            'decay_rate': 0.01,
            'growth_factor': 0.03,
            'pollution_impact': 0.1
        }
    
    def initialize_grid(self):
        """初始化网格"""
        # 创建初始污染源
        for x in range(20, 30):
            for y in range(20, 30):
                for z in range(5, 15):
                    self.grid[x, y, z] = 0.8
        
        # 创建微生物群落
        for x in range(10, 40):
            for y in range(10, 40):
                for z in range(2, 8):
                    if np.random.random() > 0.7:
                        self.grid[x, y, z] = -0.5  # 负值表示微生物
    
    def update(self, pollution_level):
        """更新元胞自动机状态"""
        new_grid = np.copy(self.grid)
        
        # 应用规则更新每个元胞
        for x in range(1, self.width-1):
            for y in range(1, self.height-1):
                for z in range(1, self.depth-1):
                    current_value = self.grid[x, y, z]
                    
                    # 扩散过程
                    if current_value > 0:  # 污染物
                        self.diffuse_pollutant(x, y, z, new_grid)
                    
                    # 微生物过程
                    elif current_value < 0:  # 微生物
                        self.grow_microbes(x, y, z, new_grid, pollution_level)
        
        self.grid = np.clip(new_grid, -1, 1)
    
    def diffuse_pollutant(self, x, y, z, new_grid):
        """污染物扩散"""
        neighbors = self.grid[x-1:x+2, y-1:y+2, z-1:z+2]
        average = np.sum(neighbors) / 26.0  # 26个邻居
        
        # 扩散
        diffusion = self.rules['diffusion_rate'] * (average - self.grid[x, y, z])
        new_grid[x, y, z] += diffusion
        
        # 衰减
        new_grid[x, y, z] -= self.rules['decay_rate']
    
    def grow_microbes(self, x, y, z, new_grid, pollution_level):
        """微生物生长"""
        # 微生物在污染物附近生长更快
        neighbor_pollution = 0
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                for dz in [-1, 0, 1]:
                    if dx == 0 and dy == 0 and dz == 0:
                        continue
                    neighbor_value = self.grid[x+dx, y+dy, z+dz]
                    if neighbor_value > 0:
                        neighbor_pollution += neighbor_value
        
        # 生长率受污染物影响
        growth_rate = self.rules['growth_factor'] * (1 + self.rules['pollution_impact'] * neighbor_pollution)
        new_grid[x, y, z] -= growth_rate  # 负值增加表示微生物数量增加
        
        # 消耗污染物
        if neighbor_pollution > 0 and new_grid[x, y, z] < -0.8:
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    for dz in [-1, 0, 1]:
                        if self.grid[x+dx, y+dy, z+dz] > 0:
                            new_grid[x+dx, y+dy, z+dz] -= growth_rate * 0.5
    
    def get_visualization_data(self):
        """获取可视化数据"""
        # 提取污染物和微生物位置
        pollutant_pos = np.argwhere(self.grid > 0.1)
        microbe_pos = np.argwhere(self.grid < -0.1)
        
        # 设置颜色
        pollutant_colors = np.zeros((len(pollutant_pos), 4))
        pollutant_colors[:, 0] = 1.0  # 红色
        pollutant_colors[:, 3] = self.grid[tuple(pollutant_pos.T)]  # 透明度
        
        microbe_colors = np.zeros((len(microbe_pos), 4))
        microbe_colors[:, 1] = 1.0  # 绿色
        microbe_colors[:, 3] = -self.grid[tuple(microbe_pos.T)]  # 透明度
        
        return {
            'pollutant': {'pos': pollutant_pos, 'color': pollutant_colors},
            'microbe': {'pos': microbe_pos, 'color': microbe_colors}
        }

# === 终极城市代谢控制系统 ===
class UltimateMetropolisControlSystem(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("量子-生物城市代谢控制系统 - 终极增强版")
        self.setGeometry(100, 100, 1920, 1080)
        
        # 创建核心组件
        self.city_model = self.create_city_model()
        self.quantum_bio_computer = QuantumBioHybridComputer()
        self.metabolic_network = AdaptiveMetabolicNetwork(self.city_model)
        self.communication_protocol = CrossDimensionProtocol(
            self.quantum_bio_computer, 
            self.quantum_bio_computer,  # 简化示例，实际应为生物系统
            self.metabolic_network
        )
        self.cellular_automata = CellularAutomataSimulator()
        
        # 创建全息指挥中心
        self.holographic_center = HolographicCommandCenter(
            self.city_model,
            self.metabolic_network.network_graph,
            self.quantum_bio_computer
        )
        
        # 设置主窗口
        self.setCentralWidget(self.holographic_center)
        
        # 创建控制面板
        self.create_control_dock()
        
        # 创建状态栏
        self.status_bar = self.create_status_bar()
        self.setStatusBar(self.status_bar)
        
        # 创建菜单栏
        self.create_menu()
        
        # 启动更新定时器
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_system)
        self.update_timer.start(100)  # 10 FPS
        
        # 添加快捷键
        QShortcut(QKeySequence("Ctrl+Q"), self, self.execute_quantum_circuit)
        QShortcut(QKeySequence("Ctrl+E"), self, self.emergency_response)
        QShortcut(QKeySequence("Ctrl+A"), self, self.activate_ai_control)
    
    def create_city_model(self):
        """创建城市模型"""
        return {
            'regions': [
                {'id': 'NW', 'name': '西北工业区', 'water_quality': 98.7, 'energy_output': 45.2, 
                 'emc_activity': 0.85, 'waste_level': 22.1, 'pollution_index': 5.3,
                 'temperature': 28.5, 'ph_level': 7.2},
                {'id': 'NE', 'name': '东北住宅区', 'water_quality': 96.2, 'energy_output': 62.1, 
                 'emc_activity': 0.92, 'waste_level': 18.7, 'pollution_index': 3.8,
                 'temperature': 26.8, 'ph_level': 7.4},
                {'id': 'SW', 'name': '西南农业区', 'water_quality': 89.5, 'energy_output': 38.7, 
                 'emc_activity': 0.78, 'waste_level': 35.2, 'pollution_index': 7.9,
                 'temperature': 30.2, 'ph_level': 6.9},
                {'id': 'SE', 'name': '东南商业区', 'water_quality': 94.3, 'energy_output': 57.8, 
                 'emc_activity': 0.88, 'waste_level': 28.4, 'pollution_index': 6.2,
                 'temperature': 29.1, 'ph_level': 7.1}
            ],
            'system_metrics': {
                'efficiency': 92.4,
                'health': 98.7,
                'quantum_coherence': 0.95
            }
        }
    
    def create_control_dock(self):
        """创建控制面板停靠窗口"""
        control_dock = QDockWidget("量子-生物控制面板", self)
        control_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | 
                                    Qt.DockWidgetArea.RightDockWidgetArea)
        
        control_widget = QWidget()
        layout = QVBoxLayout(control_widget)
        
        # 量子电路选择
        circuit_group = QGroupBox("量子-生物混合电路")
        circuit_layout = QVBoxLayout(circuit_group)
        
        self.circuit_combo = QComboBox()
        self.circuit_combo.addItems([
            "代谢优化",
            "污染响应",
            "资源平衡",
            "紧急恢复"
        ])
        circuit_layout.addWidget(self.circuit_combo)
        
        execute_btn = QPushButton("执行电路")
        execute_btn.clicked.connect(self.execute_quantum_circuit)
        circuit_layout.addWidget(execute_btn)
        
        layout.addWidget(circuit_group)
        
        # 系统控制
        system_group = QGroupBox("系统控制")
        system_layout = QVBoxLayout(system_group)
        
        self.auto_mode = QCheckBox("自动模式")
        system_layout.addWidget(self.auto_mode)
        
        emergency_btn = QPushButton("紧急响应")
        emergency_btn.setStyleSheet("background-color: #ff4444; color: white;")
        emergency_btn.clicked.connect(self.emergency_response)
        system_layout.addWidget(emergency_btn)
        
        ai_btn = QPushButton("激活AI控制")
        ai_btn.setStyleSheet("background-color: #44aa44; color: white;")
        ai_btn.clicked.connect(self.activate_ai_control)
        system_layout.addWidget(ai_btn)
        
        layout.addWidget(system_group)
        
        # 元胞自动机控制
        ca_group = QGroupBox("微观模拟控制")
        ca_layout = QVBoxLayout(ca_group)
        
        self.ca_speed = QSlider(Qt.Orientation.Horizontal)
        self.ca_speed.setRange(1, 10)
        self.ca_speed.setValue(5)
        ca_layout.addWidget(QLabel("模拟速度:"))
        ca_layout.addWidget(self.ca_speed)
        
        self.ca_visible = QCheckBox("显示微观模拟")
        self.ca_visible.setChecked(True)
        ca_layout.addWidget(self.ca_visible)
        
        layout.addWidget(ca_group)
        
        # 通信协议控制
        comm_group = QGroupBox("跨维度通信")
        comm_layout = QVBoxLayout(comm_group)
        
        self.comm_protocol = QComboBox()
        self.comm_protocol.addItems(["Q2B", "B2Q", "Q2N", "N2B", "EMERGENCY"])
        comm_layout.addWidget(self.comm_protocol)
        
        comm_btn = QPushButton("发送测试信号")
        comm_btn.clicked.connect(self.send_test_signal)
        comm_layout.addWidget(comm_btn)
        
        layout.addWidget(comm_group)
        
        control_dock.setWidget(control_widget)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, control_dock)
    
    def create_status_bar(self):
        """创建状态栏"""
        status_bar = QStatusBar()
        
        # 系统状态指示灯
        self.status_led = QLabel()
        self.status_led.setPixmap(QPixmap(16, 16))
        self.status_led.pixmap().fill(QColor(0, 255, 0))
        status_bar.addWidget(self.status_led)
        
        # 效率指标
        self.efficiency_label = QLabel("效率: 92.4%")
        status_bar.addWidget(self.efficiency_label)
        
        # 健康指标
        self.health_label = QLabel("健康度: 98.7%")
        status_bar.addWidget(self.health_label)
        
        # 量子相干性
        self.quantum_label = QLabel("量子相干性: 95.2%")
        status_bar.addWidget(self.quantum_label)
        
        # 网络性能
        self.network_label = QLabel("网络性能: 89.3%")
        status_bar.addWidget(self.network_label)
        
        return status_bar
    
    def create_menu(self):
        """创建菜单栏"""
        menu_bar = QMenuBar()
        
        # 文件菜单
        file_menu = QMenu("文件", self)
        save_action = QAction("保存系统状态", self)
        load_action = QAction("加载系统状态", self)
        exit_action = QAction("退出", self)
        
        file_menu.addAction(save_action)
        file_menu.addAction(load_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)
        
        # 视图菜单
        view_menu = QMenu("视图", self)
        hologram_action = QAction("全息投影", self)
        control_action = QAction("控制面板", self)
        
        view_menu.addAction(hologram_action)
        view_menu.addAction(control_action)
        
        # 添加到菜单栏
        menu_bar.addMenu(file_menu)
        menu_bar.addMenu(view_menu)
        
        self.setMenuBar(menu_bar)
    
    def update_system(self):
        """更新整个系统"""
        # 更新城市模型
        self.update_city_model()
        
        # 更新代谢网络
        self.metabolic_network.update_network(self.city_model)
        
        # 更新元胞自动机
        total_pollution = sum(r['pollution_index'] for r in self.city_model['regions'])
        self.cellular_automata.update(total_pollution)
        
        # 更新全息显示
        self.holographic_center.update_hologram(
            self.city_model,
            self.metabolic_network.network_graph
        )
        
        # 更新状态栏
        self.update_status_bar()
        
        # 自动模式控制
        if self.auto_mode.isChecked():
            self.auto_control()
    
    def update_city_model(self):
        """动态更新城市模型"""
        for region in self.city_model['regions']:
            # 随机波动
            fluctuation = np.random.uniform(-0.5, 0.5)
            region['water_quality'] = max(80, min(99, region['water_quality'] + fluctuation * 0.3))
            region['energy_output'] = max(30, min(70, region['energy_output'] + fluctuation * 0.8))
            region['emc_activity'] = max(0.7, min(0.99, region['emc_activity'] + fluctuation * 0.02))
            region['waste_level'] = max(10, min(80, region['waste_level'] + np.random.uniform(-1.0, 2.0)))
            region['pollution_index'] = max(1, min(15, region['pollution_index'] + np.random.uniform(0, 0.5)))
            
            # 环境参数
            if np.random.random() > 0.8:
                region['temperature'] += np.random.uniform(-1, 1)
                region['ph_level'] += np.random.uniform(-0.1, 0.1)
        
        # 系统指标
        self.city_model['system_metrics']['efficiency'] = np.mean([
            r['water_quality'] * 0.3 + 
            r['energy_output'] * 0.4 + 
            (100 - r['waste_level']) * 0.2 + 
            (20 - r['pollution_index']) * 0.1
            for r in self.city_model['regions']
        ])
        
        self.city_model['system_metrics']['health'] = 100 - np.mean([
            r['pollution_index'] * 0.6 + 
            (100 - r['water_quality']) * 0.4
            for r in self.city_model['regions']
        ])
    
    def update_status_bar(self):
        """更新状态栏"""
        metrics = self.city_model['system_metrics']
        self.efficiency_label.setText(f"效率: {metrics['efficiency']:.1f}%")
        self.health_label.setText(f"健康度: {metrics['health']:.1f}%")
        
        # 网络性能
        network_perf = self.metabolic_network.calculate_performance() * 100
        self.network_label.setText(f"网络性能: {network_perf:.1f}%")
        
        # 更新状态指示灯
        if metrics['health'] > 90:
            color = QColor(0, 255, 0)
        elif metrics['health'] > 75:
            color = QColor(255, 255, 0)
        else:
            color = QColor(255, 0, 0)
        self.status_led.pixmap().fill(color)
    
    def execute_quantum_circuit(self):
        """执行量子-生物混合电路"""
        circuit_name = self.circuit_combo.currentText()
        if circuit_name == "代谢优化":
            self.quantum_bio_computer.execute_circuit('metabolic_optimization')
        elif circuit_name == "污染响应":
            self.quantum_bio_computer.execute_circuit('pollution_response')
        elif circuit_name == "资源平衡":
            self.quantum_bio_computer.execute_circuit('resource_balancing')
        
        print(f"执行电路: {circuit_name}")
    
    def emergency_response(self):
        """紧急响应"""
        self.communication_protocol.emergency_broadcast("SYSTEM_EMERGENCY")
        
        # 执行紧急电路
        self.quantum_bio_computer.execute_circuit('pollution_response')
        
        # 重置污染区域
        for region in self.city_model['regions']:
            region['pollution_index'] *= 0.7
            region['waste_level'] *= 0.8
        
        print("紧急响应已激活")
    
    def activate_ai_control(self):
        """激活AI控制"""
        # 执行所有优化电路
        self.quantum_bio_computer.execute_circuit('metabolic_optimization')
        self.quantum_bio_computer.execute_circuit('resource_balancing')
        
        # 优化网络
        self.metabolic_network.adapt_network()
        
        print("AI控制已激活")
    
    def send_test_signal(self):
        """发送测试信号"""
        protocol = self.comm_protocol.currentText()
        if protocol == "Q2B":
            self.communication_protocol.quantum_to_bio(b"Quantum to Bio test signal")
        elif protocol == "B2Q":
            self.communication_protocol.bio_to_quantum(b"Bio to Quantum test signal")
        elif protocol == "Q2N":
            self.communication_protocol.quantum_to_network(b"Quantum to Network test signal")
        elif protocol == "N2B":
            self.communication_protocol.network_to_bio(b"Network to Bio test signal")
        elif protocol == "EMERGENCY":
            self.communication_protocol.emergency_broadcast("TEST_EMERGENCY")
        
        print(f"发送 {protocol} 测试信号")
    
    def auto_control(self):
        """自动控制系统"""
        # 根据系统健康度决定行动
        health = self.city_model['system_metrics']['health']
        
        if health < 85:
            self.quantum_bio_computer.execute_circuit('pollution_response')
        elif health < 92:
            self.quantum_bio_computer.execute_circuit('metabolic_optimization')
        
        # 定期优化网络
        if np.random.random() > 0.95:
            self.metabolic_network.adapt_network()

# === 运行应用 ===
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置全局样式
    app.setStyleSheet("""
        QMainWindow {
            background-color: #0a0a1a;
        }
        QDockWidget {
            background-color: #1a1a3a;
            color: #aaccff;
            font-weight: bold;
            border: 2px solid #444477;
            titlebar-close-icon: url(close.png);
            titlebar-normal-icon: url(float.png);
        }
        QDockWidget::title {
            background-color: #2a2a5a;
            padding: 5px;
            text-align: center;
        }
        QGroupBox {
            background-color: #1a1a3a;
            color: #88ccff;
            font-weight: bold;
            border: 1px solid #444477;
            border-radius: 5px;
            margin-top: 1ex;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top center;
            padding: 0 5px;
            background-color: #1a1a3a;
        }
        QPushButton {
            background-color: #333366;
            color: white;
            border: 1px solid #555599;
            border-radius: 4px;
            padding: 5px;
            min-height: 25px;
        }
        QPushButton:hover {
            background-color: #444488;
        }
        QPushButton:pressed {
            background-color: #2a2a5a;
        }
        QStatusBar {
            background-color: #1a1a3a;
            color: #88ccff;
            border-top: 1px solid #444477;
        }
        QComboBox, QSlider, QCheckBox {
            background-color: #252545;
            color: #ccccff;
            border: 1px solid #555599;
            border-radius: 3px;
            padding: 2px;
        }
    """)
    
    # 创建启动画面
    splash = QSplashScreen(QPixmap("splash.png"))
    splash.show()
    splash.showMessage("正在初始化量子-生物系统...", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter, Qt.GlobalColor.white)
    app.processEvents()
    
    # 模拟初始化过程
    progress = QProgressDialog("初始化城市代谢模型...", "取消", 0, 100)
    progress.setWindowTitle("系统启动中")
    progress.setWindowModality(Qt.WindowModality.WindowModal)
    progress.setValue(0)
    
    for i in range(1, 101):
        progress.setValue(i)
        app.processEvents()
        QThread.msleep(30)
        if i == 30:
            progress.setLabelText("加载量子计算核心...")
        elif i == 60:
            progress.setLabelText("初始化生物接口...")
        elif i == 80:
            progress.setLabelText("构建自适应网络...")
    
    progress.close()
    splash.finish(progress)
    
    # 创建主窗口
    window = UltimateMetropolisControlSystem()
    window.showMaximized()
    
    sys.exit(app.exec())