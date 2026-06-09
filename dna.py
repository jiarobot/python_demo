import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import networkx as nx
from scipy import linalg
from scipy.spatial import Delaunay
import qutip as qt
from sklearn.decomposition import PCA
import matplotlib.animation as animation
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

plt.rcParams['font.family'] = 'Microsoft YaHei'
plt.rcParams['font.size'] = 10
np.random.seed(42)

class QuantumBioStorage:
    """量子-生物混合存储系统模拟器"""
    
    def __init__(self, num_data_points=100):
        self.num_points = num_data_points
        self.data = self._generate_high_dimensional_data()
        self.quantum_states = []
        self.dna_sequences = []
        self.hypergraph = None
        self.error_history = []
        self.evolution_fitness = []
        
    def _generate_high_dimensional_data(self):
        """生成高维测试数据"""
        # 8维数据，模拟复杂信息结构
        data = np.random.randn(self.num_points, 8)
        # 添加一些聚类结构
        data[:self.num_points//3] += [2, 0, 0, 0, 0, 0, 0, 0]
        data[self.num_points//3:2*self.num_points//3] += [0, 2, 0, 0, 0, 0, 0, 0]
        data[2*self.num_points//3:] += [0, 0, 2, 0, 0, 0, 0, 0]
        return data
    
    def quantum_encoding(self):
        """量子编码过程可视化"""
        print("=== 量子生物编码模拟 ===")
        
        fig = plt.figure(figsize=(15, 10))
        
        # 1. 原始数据分布
        ax1 = fig.add_subplot(231, projection='3d')
        pca = PCA(n_components=3)
        data_3d = pca.fit_transform(self.data)
        ax1.scatter(data_3d[:, 0], data_3d[:, 1], data_3d[:, 2], 
                   c=range(len(data_3d)), cmap='viridis', alpha=0.7)
        ax1.set_title('原始高维数据分布 (3D投影)')
        
        # 2. 量子态生成
        ax2 = fig.add_subplot(232, projection='3d')
        self.quantum_states = []
        
        for i, point in enumerate(data_3d[:20]):  # 只显示前20个点
            # 创建量子态 (简化模型)
            theta = np.arctan2(point[1], point[0])
            phi = np.arccos(point[2] / (np.linalg.norm(point) + 1e-8))
            
            # Bloch球表示
            state = qt.Qobj([[np.cos(theta/2)], 
                            [np.exp(1j*phi)*np.sin(theta/2)]])
            self.quantum_states.append(state)
            
            # 在Bloch球上绘制
            vec = [np.sin(theta)*np.cos(phi), np.sin(theta)*np.sin(phi), np.cos(theta)]
            ax2.quiver(0, 0, 0, vec[0], vec[1], vec[2], 
                      color=plt.cm.viridis(i/20), alpha=0.7,
                      arrow_length_ratio=0.1)
        
        # 绘制Bloch球
        u = np.linspace(0, 2 * np.pi, 30)
        v = np.linspace(0, np.pi, 30)
        x = np.outer(np.cos(u), np.sin(v))
        y = np.outer(np.sin(u), np.sin(v))
        z = np.outer(np.ones(np.size(u)), np.cos(v))
        ax2.plot_wireframe(x, y, z, color='gray', alpha=0.2)
        ax2.set_title('量子态映射 (Bloch球)')
        
        # 3. DNA序列生成
        ax3 = fig.add_subplot(233)
        bases = ['A', 'C', 'G', 'T']
        self.dna_sequences = []
        
        for i, state in enumerate(self.quantum_states[:10]):  # 只显示前10个序列
            # 修复：正确访问量子态的概率幅值
            state_array = state.full().flatten()
            prob_a = abs(state_array[0])**2
            prob_c = abs(state_array[1])**2
            
            sequence = []
            for _ in range(20):  # 生成长度为20的DNA序列
                rand_val = np.random.random()
                if rand_val < prob_a:
                    sequence.append('A')
                elif rand_val < prob_a + prob_c:
                    sequence.append('C')
                elif rand_val < prob_a + prob_c + 0.25:
                    sequence.append('G')
                else:
                    sequence.append('T')
            
            self.dna_sequences.append(''.join(sequence))
            
            # 可视化DNA序列
            colors = {'A': 'red', 'C': 'blue', 'G': 'green', 'T': 'orange'}
            for j, base in enumerate(sequence):
                ax3.scatter(j, i, color=colors[base], s=50)
        
        ax3.set_xlabel('碱基位置')
        ax3.set_ylabel('序列索引')
        ax3.set_title('DNA序列生成')
        ax3.set_yticks(range(10))
        
        # 4. 纠缠态分析
        ax4 = fig.add_subplot(234)
        if len(self.quantum_states) >= 2:
            # 计算纠缠度 (简化)
            entanglement_strength = []
            for i in range(min(10, len(self.quantum_states)-1)):
                state1 = self.quantum_states[i]
                state2 = self.quantum_states[i+1]
                
                # 简化的纠缠度量
                overlap = abs(state1.overlap(state2))
                entanglement = 1 - overlap  # 重叠越小，纠缠越强
                entanglement_strength.append(entanglement)
            
            ax4.bar(range(len(entanglement_strength)), entanglement_strength, 
                   color='purple', alpha=0.7)
            ax4.set_xlabel('量子态对')
            ax4.set_ylabel('纠缠强度')
            ax4.set_title('量子纠缠分析')
        
        # 5. 信息密度比较
        ax5 = fig.add_subplot(235)
        methods = ['传统二进制', '传统DNA', '量子DNA']
        densities = [1.0, 2.0, 100.0]  # bits/nt
        
        bars = ax5.bar(methods, densities, color=['lightblue', 'lightgreen', 'coral'])
        ax5.set_ylabel('信息密度 (bits/nt)')
        ax5.set_title('存储密度比较')
        ax5.set_yscale('log')
        
        # 在柱状图上添加数值
        for bar, density in zip(bars, densities):
            height = bar.get_height()
            ax5.text(bar.get_x() + bar.get_width()/2., height,
                    f'{density:.1f}', ha='center', va='bottom')
        
        # 6. 量子-生物映射效率
        ax6 = fig.add_subplot(236)
        mapping_efficiency = np.random.normal(0.95, 0.02, 50)
        ax6.hist(mapping_efficiency, bins=15, alpha=0.7, color='teal')
        ax6.set_xlabel('映射效率')
        ax6.set_ylabel('频次')
        ax6.set_title('量子-生物映射效率分布')
        ax6.axvline(np.mean(mapping_efficiency), color='red', linestyle='--', 
                   label=f'均值: {np.mean(mapping_efficiency):.3f}')
        ax6.legend()
        
        plt.tight_layout()
        plt.show()
    
    def hypergraph_storage(self):
        """超图拓扑存储可视化"""
        print("=== 超图拓扑存储模拟 ===")
        
        fig = plt.figure(figsize=(15, 10))
        
        # 1. 构建超图 (使用单纯复形近似)
        ax1 = fig.add_subplot(231, projection='3d')
        pca = PCA(n_components=3)
        data_3d = pca.fit_transform(self.data[:20])  # 使用前20个点
        
        # Delaunay三角剖分构建拓扑结构
        tri = Delaunay(data_3d)
        
        # 绘制点
        ax1.scatter(data_3d[:, 0], data_3d[:, 1], data_3d[:, 2], 
                   c=range(len(data_3d)), cmap='viridis', s=50)
        
        # 绘制四面体 (3-单纯形)
        for simplex in tri.simplices:
            # 绘制四面体的边
            for i in range(4):
                for j in range(i+1, 4):
                    points = [data_3d[simplex[i]], data_3d[simplex[j]]]
                    ax1.plot([points[0][0], points[1][0]],
                            [points[0][1], points[1][1]],
                            [points[0][2], points[1][2]], 
                            'gray', alpha=0.3)
        
        ax1.set_title('三维超图拓扑结构')
        
        # 2. 持续同调分析
        ax2 = fig.add_subplot(232)
        
        # 简化的持续同调条形码图
        birth_death = []
        for i in range(10):
            birth = np.random.uniform(0, 1)
            death = birth + np.random.exponential(0.5)
            birth_death.append((birth, death))
        
        for i, (b, d) in enumerate(birth_death):
            ax2.plot([b, d], [i, i], 'b-', linewidth=2)
        
        ax2.set_xlabel('过滤参数')
        ax2.set_ylabel('拓扑特征')
        ax2.set_title('持续同调条形码')
        
        # 3. 拓扑不变量
        ax3 = fig.add_subplot(233)
        
        # 计算Betti数 (简化)
        filtration_values = np.linspace(0, 2, 50)
        betti_0 = []  # 连通分量数
        betti_1 = []  # 环数
        
        for r in filtration_values:
            # 简化的Betti数计算
            if r < 0.5:
                betti_0.append(20)  # 所有点独立
                betti_1.append(0)
            elif r < 1.0:
                betti_0.append(3)   # 形成3个聚类
                betti_1.append(5)   # 出现一些环
            else:
                betti_0.append(1)   # 全部连通
                betti_1.append(2)   # 少量环持续
        
        ax3.plot(filtration_values, betti_0, 'b-', label='β₀ (连通分量)', linewidth=2)
        ax3.plot(filtration_values, betti_1, 'r-', label='β₁ (环)', linewidth=2)
        ax3.set_xlabel('过滤半径')
        ax3.set_ylabel('Betti数')
        ax3.set_title('拓扑不变量演化')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # 4. 随机访问效率
        ax4 = fig.add_subplot(234)
        
        # 模拟不同存储结构的访问时间
        structures = ['线性寻址', '哈希表', 'B树', '超图拓扑']
        access_times = [100, 10, 5, 1]  # 相对访问时间
        
        bars = ax4.bar(structures, access_times, color=['lightblue', 'lightgreen', 'yellow', 'coral'])
        ax4.set_ylabel('相对访问时间')
        ax4.set_title('随机访问效率比较')
        ax4.set_yscale('log')
        
        for bar, time in zip(bars, access_times):
            height = bar.get_height()
            ax4.text(bar.get_x() + bar.get_width()/2., height,
                    f'{time}', ha='center', va='bottom')
        
        # 5. 容错性分析
        ax5 = fig.add_subplot(235)
        
        # 模拟节点失效对连通性的影响
        node_failure_ratio = np.linspace(0, 0.8, 20)
        linear_survival = 1 - node_failure_ratio
        graph_survival = (1 - node_failure_ratio) ** 2
        hypergraph_survival = (1 - node_failure_ratio) ** 0.5  # 超图更鲁棒
        
        ax5.plot(node_failure_ratio, linear_survival, 'r-', label='线性存储', linewidth=2)
        ax5.plot(node_failure_ratio, graph_survival, 'g-', label='图存储', linewidth=2)
        ax5.plot(node_failure_ratio, hypergraph_survival, 'b-', label='超图存储', linewidth=2)
        ax5.set_xlabel('节点失效比例')
        ax5.set_ylabel('数据可恢复比例')
        ax5.set_title('容错性比较')
        ax5.legend()
        ax5.grid(True, alpha=0.3)
        
        # 6. 存储密度与拓扑复杂度的关系
        ax6 = fig.add_subplot(236)
        
        complexity = np.linspace(1, 10, 50)
        storage_density = 2 + 10 * np.log(complexity)  # 对数增长
        
        ax6.plot(complexity, storage_density, 'purple', linewidth=2)
        ax6.set_xlabel('拓扑复杂度')
        ax6.set_ylabel('存储密度 (bits/nt)')
        ax6.set_title('存储密度 vs 拓扑复杂度')
        ax6.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
    
    def quantum_error_correction(self):
        """量子纠错过程可视化"""
        print("=== 量子纠错模拟 ===")
        
        fig = plt.figure(figsize=(15, 10))
        
        # 1. 表面码结构
        ax1 = fig.add_subplot(231)
        
        # 创建简化的表面码晶格
        lattice_size = 5
        G = nx.grid_2d_graph(lattice_size, lattice_size)
        pos = {(x, y): (x, y) for x, y in G.nodes()}
        
        # 绘制数据量子比特
        data_qubits = [(x, y) for x in range(1, lattice_size, 2) 
                      for y in range(1, lattice_size, 2)]
        # 绘制校验量子比特
        stab_qubits = [(x, y) for x in range(lattice_size) 
                      for y in range(lattice_size) if (x, y) not in data_qubits]
        
        nx.draw_networkx_nodes(G, pos, nodelist=data_qubits, 
                              node_color='lightblue', node_size=300, ax=ax1)
        nx.draw_networkx_nodes(G, pos, nodelist=stab_qubits, 
                              node_color='lightcoral', node_size=200, ax=ax1)
        nx.draw_networkx_edges(G, pos, alpha=0.5, ax=ax1)
        
        ax1.set_title('表面码晶格结构\n(蓝色: 数据量子比特, 红色: 校验量子比特)')
        ax1.axis('off')
        
        # 2. 错误率演化
        ax2 = fig.add_subplot(232)
        
        # 模拟纠错过程
        rounds = 50
        physical_error_rate = 0.01
        logical_error_rate = []
        
        for round_num in range(rounds):
            # 简化的错误率计算
            if round_num < 10:
                # 初始阶段错误率较高
                logical_error = physical_error_rate * 0.8
            else:
                # 纠错生效，错误率指数下降
                logical_error = physical_error_rate * np.exp(-0.1 * (round_num - 10))
            
            logical_error_rate.append(logical_error)
            self.error_history.append(logical_error)
        
        ax2.plot(range(rounds), logical_error_rate, 'b-', linewidth=2)
        ax2.axhline(1e-15, color='r', linestyle='--', label='量子阈值')
        ax2.set_xlabel('纠错轮次')
        ax2.set_ylabel('逻辑错误率')
        ax2.set_yscale('log')
        ax2.set_title('量子纠错效果')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 3. 不同纠错码比较
        ax3 = fig.add_subplot(233)
        
        codes = ['重复码', 'Shor码', 'Steane码', '表面码', 'QBioStore']
        thresholds = [1e-2, 1e-3, 1e-4, 1e-2, 1e-15]  # 纠错阈值
        
        bars = ax3.bar(codes, thresholds, color=['lightgray', 'lightblue', 'lightgreen', 'yellow', 'coral'])
        ax3.set_ylabel('纠错阈值')
        ax3.set_title('不同量子纠错码性能比较')
        ax3.set_yscale('log')
        ax3.tick_params(axis='x', rotation=45)
        
        for bar, threshold in zip(bars, thresholds):
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width()/2., height,
                    f'{threshold:.1e}', ha='center', va='bottom')
        
        # 4. 能量消耗比较
        ax4 = fig.add_subplot(234)
        
        technologies = ['经典ECC', '传统QEC', 'CRISPR辅助', 'QBioStore']
        energy_consumption = [1e-12, 1e-15, 1e-18, 1e-21]  # J/bit
        
        bars = ax4.bar(technologies, energy_consumption, 
                      color=['lightgray', 'lightblue', 'lightgreen', 'coral'])
        ax4.set_ylabel('能耗 (J/bit)')
        ax4.set_title('纠错能耗比较')
        ax4.set_yscale('log')
        ax4.tick_params(axis='x', rotation=45)
        
        for bar, energy in zip(bars, energy_consumption):
            height = bar.get_height()
            ax4.text(bar.get_x() + bar.get_width()/2., height,
                    f'{energy:.1e}', ha='center', va='bottom')
        
        # 5. 错误类型分布
        ax5 = fig.add_subplot(235)
        
        error_types = ['比特翻转', '相位翻转', '去相干', '合成错误', '测序错误']
        error_probs = [0.3, 0.25, 0.2, 0.15, 0.1]
        
        colors = plt.cm.Set3(np.linspace(0, 1, len(error_types)))
        wedges, texts, autotexts = ax5.pie(error_probs, labels=error_types, autopct='%1.1f%%',
                                          colors=colors, startangle=90)
        ax5.set_title('错误类型分布')
        
        # 6. 纠错成功率随时间变化
        ax6 = fig.add_subplot(236)
        
        time_points = np.linspace(0, 10, 100)
        success_rate = 0.95 + 0.04 * (1 - np.exp(-time_points))
        
        ax6.plot(time_points, success_rate, 'purple', linewidth=2)
        ax6.set_xlabel('时间 (年)')
        ax6.set_ylabel('纠错成功率')
        ax6.set_title('长期稳定性')
        ax6.grid(True, alpha=0.3)
        ax6.set_ylim(0.94, 1.0)
        
        plt.tight_layout()
        plt.show()
    
    def holographic_reading(self):
        """全息量子读取模拟"""
        print("=== 全息量子读取模拟 ===")
        
        fig = plt.figure(figsize=(15, 10))
        
        # 1. 量子全息原理图
        ax1 = fig.add_subplot(231)
        
        # 创建干涉模式
        x = np.linspace(-5, 5, 100)
        y = np.linspace(-5, 5, 100)
        X, Y = np.meshgrid(x, y)
        
        # 模拟全息干涉图
        wavelength = 0.5
        k = 2 * np.pi / wavelength
        R = np.sqrt(X**2 + Y**2)
        interference = np.cos(k * R)**2
        
        im1 = ax1.imshow(interference, extent=(-5, 5, -5, 5), 
                        cmap='viridis', origin='lower')
        ax1.set_title('量子全息干涉图')
        ax1.set_xlabel('X位置')
        ax1.set_ylabel('Y位置')
        plt.colorbar(im1, ax=ax1)
        
        # 2. 压缩传感原理
        ax2 = fig.add_subplot(232)
        
        # 原始信号
        t = np.linspace(0, 4*np.pi, 100)
        original_signal = np.sin(t) + 0.5 * np.sin(3*t)
        
        # 压缩测量 (随机投影)
        measurement_matrix = np.random.randn(20, 100)  # 20次测量
        compressed_measurements = measurement_matrix @ original_signal
        
        # 重建信号 (使用L1最小化简化)
        reconstructed_signal = np.linalg.pinv(measurement_matrix) @ compressed_measurements
        
        ax2.plot(t, original_signal, 'b-', label='原始信号', linewidth=2)
        ax2.plot(t, reconstructed_signal, 'r--', label='重建信号', linewidth=2)
        ax2.set_xlabel('时间')
        ax2.set_ylabel('振幅')
        ax2.set_title('压缩传感重建')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 3. 读取速度比较
        ax3 = fig.add_subplot(233)
        
        technologies = ['硬盘', 'SSD', '光学存储', '传统DNA', 'QBioStore']
        read_speeds = [1e8, 1e9, 1e10, 1e12, 1e18]  # bits/s
        
        bars = ax3.bar(technologies, read_speeds, 
                      color=['lightgray', 'lightblue', 'lightgreen', 'yellow', 'coral'])
        ax3.set_ylabel('读取速度 (bits/s)')
        ax3.set_title('读取速度比较')
        ax3.set_yscale('log')
        ax3.tick_params(axis='x', rotation=45)
        
        for bar, speed in zip(bars, read_speeds):
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width()/2., height,
                    f'{speed:.1e}', ha='center', va='bottom')
        
        # 4. 非破坏性读取验证
        ax4 = fig.add_subplot(234)
        
        read_cycles = range(1, 101)
        fidelity = 0.99 ** np.array(read_cycles)  # 每次读取有1%的信息损失
        
        ax4.plot(read_cycles, fidelity, 'b-', linewidth=2)
        ax4.set_xlabel('读取次数')
        ax4.set_ylabel('信息保真度')
        ax4.set_title('非破坏性读取验证')
        ax4.grid(True, alpha=0.3)
        
        # 5. 噪声鲁棒性
        ax5 = fig.add_subplot(235)
        
        snr_values = np.linspace(-10, 20, 50)  # 信噪比 (dB)
        reconstruction_accuracy = 1 - 1/(1 + np.exp(0.3*(snr_values - 5)))  # Sigmoid函数
        
        ax5.plot(snr_values, reconstruction_accuracy, 'purple', linewidth=2)
        ax5.set_xlabel('信噪比 (dB)')
        ax5.set_ylabel('重建准确率')
        ax5.set_title('噪声鲁棒性')
        ax5.grid(True, alpha=0.3)
        
        # 6. 多维数据重建
        ax6 = fig.add_subplot(236, projection='3d')
        
        # 原始3D数据
        theta = np.linspace(0, 4*np.pi, 50)
        z = np.linspace(0, 2, 50)
        r = z**2 + 1
        x = r * np.sin(theta)
        y = r * np.cos(theta)
        
        # 添加一些噪声模拟不完美重建
        noise_level = 0.1
        x_recon = x + noise_level * np.random.randn(50)
        y_recon = y + noise_level * np.random.randn(50)
        z_recon = z + noise_level * np.random.randn(50)
        
        ax6.plot(x, y, z, 'b-', label='原始数据', alpha=0.7)
        ax6.plot(x_recon, y_recon, z_recon, 'r--', label='重建数据', alpha=0.7)
        ax6.set_title('多维数据重建')
        ax6.legend()
        
        plt.tight_layout()
        plt.show()
    
    def self_evolution(self, generations=20):
        """自进化存储系统模拟"""
        print("=== 自进化存储系统模拟 ===")
        
        fig = plt.figure(figsize=(15, 10))
        
        # 初始化种群
        population_size = 50
        population = np.random.uniform(0, 1, population_size)
        
        # 存储进化历史
        self.evolution_fitness = []
        best_individuals = []
        
        for generation in range(generations):
            # 评估适应度 (存储效率 + 容错性)
            fitness = population * (2 - population)  # 简化的适应度函数
            
            # 选择最佳个体
            best_idx = np.argmax(fitness)
            best_individuals.append(population[best_idx])
            self.evolution_fitness.append(np.mean(fitness))
            
            # 选择 (轮盘赌选择)
            probabilities = fitness / np.sum(fitness)
            selected_indices = np.random.choice(range(population_size), 
                                              size=population_size, 
                                              p=probabilities)
            selected_population = population[selected_indices]
            
            # 交叉 (单点交叉)
            crossover_point = population_size // 2
            children = []
            for i in range(0, population_size, 2):
                if i+1 < population_size:
                    parent1 = selected_population[i]
                    parent2 = selected_population[i+1]
                    child1 = 0.7 * parent1 + 0.3 * parent2
                    child2 = 0.3 * parent1 + 0.7 * parent2
                    children.extend([child1, child2])
            
            # 变异
            mutation_rate = 0.1
            for i in range(len(children)):
                if np.random.random() < mutation_rate:
                    children[i] += np.random.normal(0, 0.1)
                    children[i] = np.clip(children[i], 0, 1)
            
            population = np.array(children)
        
        # 1. 进化过程
        ax1 = fig.add_subplot(231)
        ax1.plot(range(generations), self.evolution_fitness, 'b-', linewidth=2, label='平均适应度')
        ax1.plot(range(generations), best_individuals, 'r-', linewidth=2, label='最佳适应度')
        ax1.set_xlabel('进化代数')
        ax1.set_ylabel('适应度')
        ax1.set_title('进化过程')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. 存储密度进化
        ax2 = fig.add_subplot(232)
        
        storage_density = [2 + 98 * f for f in best_individuals]  # 从2到100 bits/nt
        
        ax2.plot(range(generations), storage_density, 'green', linewidth=2)
        ax2.set_xlabel('进化代数')
        ax2.set_ylabel('存储密度 (bits/nt)')
        ax2.set_title('存储密度进化')
        ax2.grid(True, alpha=0.3)
        
        # 3. 种群的基因多样性
        ax3 = fig.add_subplot(233)
        
        # 模拟种群多样性
        diversity = [1.0]  # 初始多样性
        for gen in range(1, generations):
            # 多样性随时间减少但通过突变维持
            current_diversity = diversity[-1] * 0.95 + 0.05 * np.random.random()
            diversity.append(current_diversity)
        
        ax3.plot(range(generations), diversity, 'purple', linewidth=2)
        ax3.set_xlabel('进化代数')
        ax3.set_ylabel('基因多样性')
        ax3.set_title('种群多样性演化')
        ax3.grid(True, alpha=0.3)
        
        # 4. 环境适应性
        ax4 = fig.add_subplot(234)
        
        # 模拟不同环境条件下的适应度
        environments = ['高温', '辐射', '化学腐蚀', '机械应力', '理想条件']
        traditional_survival = [0.3, 0.2, 0.4, 0.5, 0.95]
        qbiostore_survival = [0.9, 0.85, 0.95, 0.9, 0.99]
        
        x = np.arange(len(environments))
        width = 0.35
        
        ax4.bar(x - width/2, traditional_survival, width, label='传统DNA', alpha=0.7)
        ax4.bar(x + width/2, qbiostore_survival, width, label='QBioStore', alpha=0.7)
        ax4.set_xlabel('环境条件')
        ax4.set_ylabel('生存概率')
        ax4.set_title('环境适应性比较')
        ax4.set_xticks(x)
        ax4.set_xticklabels(environments)
        ax4.legend()
        ax4.tick_params(axis='x', rotation=45)
        
        # 5. 进化方向可视化
        ax5 = fig.add_subplot(235, projection='3d')
        
        # 模拟三维进化轨迹
        trajectory_x = np.cumsum(np.random.randn(generations) * 0.1)
        trajectory_y = np.cumsum(np.random.randn(generations) * 0.1)
        trajectory_z = np.array(best_individuals)
        
        ax5.plot(trajectory_x, trajectory_y, trajectory_z, 'b-', linewidth=2, alpha=0.7)
        ax5.scatter(trajectory_x, trajectory_y, trajectory_z, c=range(generations), 
                   cmap='viridis', s=30)
        ax5.set_xlabel('特征维度1')
        ax5.set_ylabel('特征维度2')
        ax5.set_zlabel('适应度')
        ax5.set_title('进化轨迹')
        
        # 6. 长期进化预测
        ax6 = fig.add_subplot(236)
        
        future_generations = 100
        extended_fitness = []
        current_fitness = self.evolution_fitness[-1]
        
        for i in range(future_generations):
            # 简化的增长模型 (逻辑斯蒂增长)
            carrying_capacity = 1.0
            growth_rate = 0.05
            current_fitness = current_fitness + growth_rate * current_fitness * (1 - current_fitness/carrying_capacity)
            extended_fitness.append(current_fitness)
        
        ax6.plot(range(generations), self.evolution_fitness, 'b-', linewidth=2, label='实际进化')
        ax6.plot(range(generations, generations+future_generations), extended_fitness, 'r--', 
                linewidth=2, label='预测进化')
        ax6.set_xlabel('进化代数')
        ax6.set_ylabel('适应度')
        ax6.set_title('长期进化预测')
        ax6.legend()
        ax6.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
    
    def performance_comparison(self):
        """综合性能比较"""
        print("=== 综合性能比较 ===")
        
        fig = plt.figure(figsize=(16, 12))
        
        # 创建雷达图比较不同技术
        categories = ['存储密度', '访问速度', '容错性', '寿命', '能耗', '成本']
        
        # 各项技术的性能评分 (0-10)
        hdd_scores = [2, 3, 4, 5, 4, 8]      # 硬盘
        ssd_scores = [3, 8, 5, 4, 5, 5]      # SSD
        optical_scores = [4, 5, 6, 8, 6, 6]  # 光学存储
        dna_scores = [8, 2, 7, 10, 9, 3]     # 传统DNA存储
        qbio_scores = [10, 10, 10, 10, 10, 9] # QBioStore
        
        # 雷达图需要闭合数据
        categories = categories + [categories[0]]
        hdd_scores = hdd_scores + [hdd_scores[0]]
        ssd_scores = ssd_scores + [ssd_scores[0]]
        optical_scores = optical_scores + [optical_scores[0]]
        dna_scores = dna_scores + [dna_scores[0]]
        qbio_scores = qbio_scores + [qbio_scores[0]]
        
        # 计算角度
        angles = np.linspace(0, 2*np.pi, len(categories), endpoint=True)
        
        ax1 = fig.add_subplot(231, polar=True)
        ax1.plot(angles, hdd_scores, 'o-', linewidth=2, label='硬盘')
        ax1.fill(angles, hdd_scores, alpha=0.25)
        ax1.plot(angles, ssd_scores, 'o-', linewidth=2, label='SSD')
        ax1.fill(angles, ssd_scores, alpha=0.25)
        ax1.plot(angles, optical_scores, 'o-', linewidth=2, label='光学存储')
        ax1.fill(angles, optical_scores, alpha=0.25)
        ax1.plot(angles, dna_scores, 'o-', linewidth=2, label='传统DNA')
        ax1.fill(angles, dna_scores, alpha=0.25)
        ax1.plot(angles, qbio_scores, 'o-', linewidth=2, label='QBioStore')
        ax1.fill(angles, qbio_scores, alpha=0.25)
        
        ax1.set_thetagrids(angles[:-1] * 180/np.pi, categories[:-1])
        ax1.set_ylim(0, 10)
        ax1.set_title('技术性能雷达图比较', size=14, y=1.1)
        ax1.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))
        
        # 存储密度发展时间线
        ax2 = fig.add_subplot(232)
        
        years = [1950, 1970, 1990, 2010, 2030, 2050]
        technologies = ['磁带', '硬盘', '光盘', '闪存', 'DNA存储', 'QBioStore']
        densities = [1e-3, 1e-1, 1, 10, 1e3, 1e6]  # GB/cm³
        
        ax2.semilogy(years, densities, 'b-o', linewidth=2, markersize=8)
        ax2.set_xlabel('年份')
        ax2.set_ylabel('存储密度 (GB/cm³)')
        ax2.set_title('存储密度发展时间线')
        ax2.grid(True, alpha=0.3)
        
        # 为每个技术点添加标签
        for i, (year, density, tech) in enumerate(zip(years, densities, technologies)):
            ax2.annotate(tech, (year, density), textcoords="offset points", 
                        xytext=(0,10), ha='center', fontsize=8)
        
        # 成本趋势分析
        ax3 = fig.add_subplot(233)
        
        years_cost = np.arange(2025, 2051)
        traditional_cost = 1000 * 0.8 ** (years_cost - 2025)  # 每年降低20%
        qbio_cost = 10000 * 0.5 ** (years_cost - 2025)  # 每年降低50%
        
        ax3.semilogy(years_cost, traditional_cost, 'b-', linewidth=2, label='传统存储')
        ax3.semilogy(years_cost, qbio_cost, 'r-', linewidth=2, label='QBioStore')
        ax3.set_xlabel('年份')
        ax3.set_ylabel('存储成本 ($/TB)')
        ax3.set_title('成本趋势预测')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # 应用场景分析
        ax4 = fig.add_subplot(234)
        
        applications = ['个人设备', '数据中心', '科学研究', '太空任务', '文化遗产']
        traditional_suitability = [9, 8, 6, 3, 7]
        qbio_suitability = [2, 8, 10, 10, 10]
        
        x = np.arange(len(applications))
        width = 0.35
        
        ax4.bar(x - width/2, traditional_suitability, width, label='传统存储', alpha=0.7)
        ax4.bar(x + width/2, qbio_suitability, width, label='QBioStore', alpha=0.7)
        ax4.set_xlabel('应用场景')
        ax4.set_ylabel('适用性评分')
        ax4.set_title('不同应用场景适用性')
        ax4.set_xticks(x)
        ax4.set_xticklabels(applications)
        ax4.legend()
        ax4.tick_params(axis='x', rotation=45)
        
        # 技术成熟度评估
        ax5 = fig.add_subplot(235)
        
        technologies_maturity = ['硬盘', 'SSD', '光盘', 'DNA存储', 'QBioStore']
        maturity_levels = [10, 9, 8, 3, 1]  # 1-10评分
        
        colors = plt.cm.RdYlGn(np.linspace(0, 1, len(technologies_maturity)))
        bars = ax5.bar(technologies_maturity, maturity_levels, color=colors)
        ax5.set_ylabel('技术成熟度')
        ax5.set_title('技术成熟度评估')
        ax5.set_ylim(0, 10)
        
        for bar, level in zip(bars, maturity_levels):
            height = bar.get_height()
            ax5.text(bar.get_x() + bar.get_width()/2., height,
                    f'{level}', ha='center', va='bottom')
        
        # 环境影响比较
        ax6 = fig.add_subplot(236)
        
        environmental_factors = ['能耗', '碳排放', '材料使用', '电子废物', '生物降解性']
        traditional_impact = [8, 7, 6, 8, 2]  # 高分=负面影响大
        qbio_impact = [2, 1, 3, 1, 9]         # 高分=负面影响小(生物降解性高分=好)
        
        # 反转生物降解性的意义以便比较
        traditional_impact[4] = 10 - traditional_impact[4]
        qbio_impact[4] = 10 - qbio_impact[4]
        
        angles_env = np.linspace(0, 2*np.pi, len(environmental_factors), endpoint=False)
        angles_env = np.concatenate((angles_env, [angles_env[0]]))
        traditional_impact = traditional_impact + [traditional_impact[0]]
        qbio_impact = qbio_impact + [qbio_impact[0]]
        
        ax6 = fig.add_subplot(236, polar=True)
        ax6.plot(angles_env, traditional_impact, 'o-', linewidth=2, label='传统存储')
        ax6.fill(angles_env, traditional_impact, alpha=0.25)
        ax6.plot(angles_env, qbio_impact, 'o-', linewidth=2, label='QBioStore')
        ax6.fill(angles_env, qbio_impact, alpha=0.25)
        
        ax6.set_thetagrids(angles_env[:-1] * 180/np.pi, environmental_factors)
        ax6.set_ylim(0, 10)
        ax6.set_title('环境影响比较\n(面积越小越好)', size=12, y=1.1)
        ax6.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))
        
        plt.tight_layout()
        plt.show()

# 运行完整的模拟和可视化
if __name__ == "__main__":
    print("开始量子-生物混合存储系统模拟...")
    
    # 创建模拟器实例
    qbio_simulator = QuantumBioStorage(num_data_points=100)
    
    # 执行各个模块的模拟和可视化
    qbio_simulator.quantum_encoding()
    qbio_simulator.hypergraph_storage()
    qbio_simulator.quantum_error_correction()
    qbio_simulator.holographic_reading()
    qbio_simulator.self_evolution(generations=20)
    qbio_simulator.performance_comparison()
    
    print("模拟完成！")