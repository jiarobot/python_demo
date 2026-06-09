import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from scipy.spatial.distance import cdist
from tqdm import tqdm

class OriginOfLifeSimulator:
    def __init__(self, space_size=100, num_molecules=500, energy_levels=5):
        """
        初始化生命起源模拟环境
        
        参数:
        space_size: 模拟空间尺寸 (立方体边长)
        num_molecules: 初始分子数量
        energy_levels: 能量层级数量
        """
        self.space_size = space_size
        self.num_molecules = num_molecules
        self.energy_levels = energy_levels
        
        # 分子类型编码: 0=水, 1=氨, 2=甲烷, 3=磷酸, 4=核苷酸, 5=氨基酸, 6=短肽, 7=寡核苷酸, 8=自复制分子
        self.molecule_types = ["H2O", "NH3", "CH4", "PO4", "Nucleotide", "AminoAcid", "Peptide", "Oligonucleotide", "Replicator"]
        self.type_colors = ['#3498db', '#2ecc71', '#e74c3c', '#f1c40f', 
                          '#9b59b6', '#1abc9c', '#d35400', '#c0392b', '#27ae60']
        
        self.reset_simulation()
        
    def reset_simulation(self):
        """重置模拟环境到初始状态"""
        # 随机初始化分子位置
        self.positions = np.random.rand(self.num_molecules, 3) * self.space_size
        
        # 初始化分子类型 (主要为基础分子)
        self.types = np.zeros(self.num_molecules, dtype=int)
        type_probs = [0.4, 0.2, 0.2, 0.2]  # H2O, NH3, CH4, PO4
        for i in range(self.num_molecules):
            self.types[i] = np.random.choice([0,1,2,3], p=type_probs)
        
        # 分子属性
        self.energies = np.random.uniform(0.1, 1.0, self.num_molecules)
        self.complexity = np.zeros(self.num_molecules)  # 分子复杂度
        self.catalysis = np.zeros(self.num_molecules)  # 催化能力
        
        # 环境参数
        self.temperature = 300  # 开尔文
        self.energy_input = 0.5  # 环境能量输入
        self.reaction_history = []  # 记录关键反应
        self.time_step = 0
        
    def _energy_transfer(self, distances):
        """模拟分子间的能量传递"""
        # 距离越近传递效率越高
        energy_transfer = np.exp(-distances/5.0) 
        np.fill_diagonal(energy_transfer, 0)  # 排除自身
        
        # 计算净能量变化
        energy_diff = self.energies[:, None] - self.energies
        energy_flow = energy_transfer * energy_diff * 0.05
        return np.sum(energy_flow, axis=1)
    
    def _chemical_reactions(self, distances):
        """执行化学反应规则"""
        new_types = self.types.copy()
        new_positions = [pos.copy() for pos in self.positions]
        new_energies = self.energies.copy()
        new_complexity = self.complexity.copy()
        new_catalysis = self.catalysis.copy()
        
        reacted = set()  # 记录已反应的分子
        key_reactions = []  # 记录关键反应
        
        # 遍历所有分子对
        for i in range(len(self.types)):
            if i in reacted:
                continue
                
            for j in range(i+1, len(self.types)):
                if j in reacted:
                    continue
                    
                # 只有距离足够近才可能反应
                if distances[i,j] > 3.0:
                    continue
                    
                type_i, type_j = self.types[i], self.types[j]
                energy_i, energy_j = self.energies[i], self.energies[j]
                comp_i, comp_j = self.complexity[i], self.complexity[j]
                cat_i, cat_j = self.catalysis[i], self.catalysis[j]
                
                # 规则1: 核苷酸形成 (需要磷酸+碱基+糖，此处简化)
                if (type_i == 3 and type_j in [1,2]) or (type_j == 3 and type_i in [1,2]):
                    if np.random.rand() < 0.1 * (energy_i + energy_j):
                        new_types[i] = 4  # 核苷酸
                        new_complexity[i] = max(comp_i, comp_j) + 0.5
                        new_energies[i] = (energy_i + energy_j) * 0.8
                        reacted.add(j)
                        key_reactions.append((self.time_step, i, j, "Nucleotide formation"))
                
                # 规则2: 氨基酸形成
                elif (type_i in [1,2] and type_j == 0) or (type_j in [1,2] and type_i == 0):
                    if np.random.rand() < 0.08 * (energy_i + energy_j):
                        new_types[i] = 5  # 氨基酸
                        new_complexity[i] = max(comp_i, comp_j) + 0.6
                        new_energies[i] = (energy_i + energy_j) * 0.85
                        reacted.add(j)
                        key_reactions.append((self.time_step, i, j, "Amino acid formation"))
                
                # 规则3: 肽链形成 (氨基酸聚合)
                elif type_i == 5 and type_j == 5:
                    if np.random.rand() < 0.05 * (1 + cat_i + cat_j) * (energy_i + energy_j):
                        new_types[i] = 6  # 短肽
                        new_complexity[i] = comp_i + comp_j + 1.0
                        new_catalysis[i] = min(1.0, (cat_i + cat_j)*0.5 + 0.1)
                        new_energies[i] = (energy_i + energy_j) * 0.7
                        reacted.add(j)
                        key_reactions.append((self.time_step, i, j, "Peptide bond formation"))
                
                # 规则4: 寡核苷酸形成
                elif type_i == 4 and type_j == 4:
                    if np.random.rand() < 0.04 * (1 + cat_i + cat_j) * (energy_i + energy_j):
                        new_types[i] = 7  # 寡核苷酸
                        new_complexity[i] = comp_i + comp_j + 1.2
                        new_energies[i] = (energy_i + energy_j) * 0.75
                        reacted.add(j)
                        key_reactions.append((self.time_step, i, j, "Oligonucleotide formation"))
                
                # 规则5: 自复制系统形成 (RNA-肽复合体)
                elif (type_i == 6 and type_j == 7) or (type_i == 7 and type_j == 6):
                    if np.random.rand() < 0.01 * (cat_i + cat_j) * (energy_i + energy_j):
                        new_types[i] = 8  # 自复制分子
                        new_complexity[i] = comp_i + comp_j + 2.0
                        new_catalysis[i] = min(1.0, (cat_i + cat_j)*0.6 + 0.3)
                        new_energies[i] = (energy_i + energy_j) * 0.9
                        reacted.add(j)
                        key_reactions.append((self.time_step, i, j, "SELF-REPLICATING SYSTEM"))
                
                # 规则6: 自复制 (需要模板和构件分子)
                elif type_i == 8 and type_j in [4,5,6,7]:
                    if np.random.rand() < 0.2 * cat_i * energy_i:
                        # 创建新复制分子 (位置靠近模板)
                        new_pos = self.positions[i] + np.random.normal(0, 1.0, 3)
                        new_pos = np.clip(new_pos, 0, self.space_size)
                        new_positions.append(new_pos)
                        new_types = np.append(new_types, 8)  # 复制品
                        new_energies = np.append(new_energies, energy_i * 0.8)
                        new_complexity = np.append(new_complexity, comp_i * 0.95)
                        new_catalysis = np.append(new_catalysis, cat_i * 0.9)
                        reacted.add(j)
                        key_reactions.append((self.time_step, i, j, "Replication event"))
        
        # 更新系统状态
        mask = [i for i in range(len(self.types)) if i not in reacted]
        self.positions = np.array([new_positions[i] for i in mask])
        self.types = new_types[mask]
        self.energies = new_energies[mask]
        self.complexity = new_complexity[mask]
        self.catalysis = new_catalysis[mask]
        
        # 添加环境输入的新分子
        new_mols = max(0, self.num_molecules - len(self.positions))
        if new_mols > 0:
            new_pos = np.random.rand(new_mols, 3) * self.space_size
            new_typ = np.random.choice([0,1,2,3], size=new_mols, p=[0.5,0.2,0.2,0.1])
            new_eng = np.random.uniform(0.5, 1.0, new_mols)
            
            self.positions = np.vstack([self.positions, new_pos])
            self.types = np.concatenate([self.types, new_typ])
            self.energies = np.concatenate([self.energies, new_eng])
            self.complexity = np.concatenate([self.complexity, np.zeros(new_mols)])
            self.catalysis = np.concatenate([self.catalysis, np.zeros(new_mols)])
        
        # 记录关键反应
        self.reaction_history.extend(key_reactions)
        return key_reactions
    
    def _apply_environment_effects(self):
        """应用环境效应"""
        # 温度波动
        self.temperature += np.random.normal(0, 0.5)
        self.temperature = np.clip(self.temperature, 280, 320)
        
        # 能量输入 (例如热液喷口、闪电等)
        energy_input = self.energy_input * (1 + 0.1 * np.sin(self.time_step / 100))
        self.energies += np.random.uniform(0, energy_input, len(self.energies))
        self.energies = np.clip(self.energies, 0, 2.0)
        
        # 分子衰变
        decay_prob = 0.01 * (1 - self.complexity/10)
        decay_mask = np.random.rand(len(self.types)) < decay_prob
        if np.any(decay_mask):
            self.positions = self.positions[~decay_mask]
            self.types = self.types[~decay_mask]
            self.energies = self.energies[~decay_mask]
            self.complexity = self.complexity[~decay_mask]
            self.catalysis = self.catalysis[~decay_mask]
    
    def step(self):
        """执行一个模拟时间步"""
        self.time_step += 1
        
        # 1. 分子随机运动 (布朗运动)
        self.positions += np.random.normal(0, 0.5, self.positions.shape)
        self.positions = np.clip(self.positions, 0, self.space_size)
        
        # 2. 计算分子间距离
        distances = cdist(self.positions, self.positions)
        
        # 3. 能量传递
        energy_flow = self._energy_transfer(distances)
        self.energies += energy_flow
        self.energies = np.clip(self.energies, 0, 2.0)
        
        # 4. 发生化学反应
        key_reactions = self._chemical_reactions(distances)
        
        # 5. 环境效应
        self._apply_environment_effects()
        
        return key_reactions
    
    def run_simulation(self, steps=1000):
        """运行完整模拟"""
        complexity_history = []
        population_history = []
        type_distribution = []
        
        for _ in tqdm(range(steps)):
            self.step()
            
            # 记录数据
            if len(self.types) > 0:
                avg_complexity = np.mean(self.complexity)
                complexity_history.append(avg_complexity)
                population_history.append(len(self.types))
                
                # 计算类型分布
                type_count = [np.sum(self.types == i) for i in range(len(self.molecule_types))]
                type_distribution.append(type_count)
        
        # 转换历史数据为数组
        complexity_history = np.array(complexity_history)
        population_history = np.array(population_history)
        type_distribution = np.array(type_distribution).T
        
        return {
            'complexity': complexity_history,
            'population': population_history,
            'type_distribution': type_distribution,
            'reactions': self.reaction_history
        }
    
    def visualize(self, data, save_path='origin_of_life_evolution.mp4'):
        """可视化模拟结果"""
        fig, axs = plt.subplots(2, 2, figsize=(14, 10))
        
        # 1. 复杂度随时间变化
        axs[0,0].plot(data['complexity'], 'g-', linewidth=2)
        axs[0,0].set_title('Average Molecular Complexity Over Time')
        axs[0,0].set_xlabel('Time Steps')
        axs[0,0].set_ylabel('Complexity Index')
        axs[0,0].grid(alpha=0.3)
        
        # 2. 种群数量变化
        axs[0,1].plot(data['population'], 'b-', linewidth=2)
        axs[0,1].set_title('Total Molecular Population')
        axs[0,1].set_xlabel('Time Steps')
        axs[0,1].set_ylabel('Number of Molecules')
        axs[0,1].grid(alpha=0.3)
        
        # 3. 分子类型分布
        dist_data = data['type_distribution']
        labels = self.molecule_types
        colors = self.type_colors
        
        bottom = np.zeros(len(dist_data[0]))
        for i in range(len(labels)):
            axs[1,0].bar(range(len(dist_data[i])), dist_data[i], 
                        bottom=bottom, color=colors[i], label=labels[i])
            bottom += dist_data[i]
        
        axs[1,0].set_title('Molecular Type Distribution Over Time')
        axs[1,0].set_xlabel('Time Steps')
        axs[1,0].set_ylabel('Count')
        axs[1,0].legend(loc='upper left', bbox_to_anchor=(1,1))
        axs[1,0].grid(alpha=0.3)
        
        # 4. 关键反应事件
        reaction_times = [r[0] for r in self.reaction_history]
        reaction_types = [r[3] for r in self.reaction_history]
        
        unique_reactions = list(set(reaction_types))
        y_pos = {r: i for i, r in enumerate(unique_reactions)}
        
        for time, reaction in zip(reaction_times, reaction_types):
            axs[1,1].scatter(time, y_pos[reaction], color='red', s=50)
        
        axs[1,1].set_yticks(range(len(unique_reactions)))
        axs[1,1].set_yticklabels(unique_reactions)
        axs[1,1].set_title('Key Reaction Events')
        axs[1,1].set_xlabel('Time Steps')
        axs[1,1].grid(alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('origin_of_life_evolution.png', dpi=150)
        plt.show()
        
        # 动态3D可视化
        fig_3d = plt.figure(figsize=(10, 8))
        ax_3d = fig_3d.add_subplot(111, projection='3d')
        
        def update(frame):
            ax_3d.clear()
            ax_3d.set_xlim([0, self.space_size])
            ax_3d.set_ylim([0, self.space_size])
            ax_3d.set_zlim([0, self.space_size])
            
            # 运行到当前帧
            self.reset_simulation()
            for _ in range(frame):
                self.step()
            
            # 绘制分子
            colors = [self.type_colors[t] for t in self.types]
            ax_3d.scatter(
                self.positions[:,0], 
                self.positions[:,1], 
                self.positions[:,2],
                c=colors, s=self.energies*20, alpha=0.7
            )
            
            ax_3d.set_title(f'Molecular Evolution at Step {frame}\nReplicators: {np.sum(self.types==8)}')
            return fig_3d,
        
        # 创建动画 (缩短为100帧演示)
        ani = FuncAnimation(fig_3d, update, frames=100, interval=100, blit=False)
        ani.save(save_path, writer='ffmpeg', dpi=100)
        
        return ani

# 运行完整模拟
if __name__ == "__main__":
    print("Starting Origin of Life Simulation...")
    simulator = OriginOfLifeSimulator(space_size=50, num_molecules=300)
    results = simulator.run_simulation(steps=500)
    
    print("\nSimulation Completed!")
    print(f"Final Complexity: {results['complexity'][-1]:.2f}")
    print(f"Final Population: {results['population'][-1]}")
    print(f"Replicators Formed: {np.sum(np.array(simulator.types)==8)}")
    
    print("\nKey Reaction Events:")
    for i, reaction in enumerate(simulator.reaction_history[-5:]):
        print(f"Step {reaction[0]}: {reaction[3]}")
    
    # 可视化结果
    print("\nGenerating visualizations...")
    simulator.visualize(results)
    print("Visualization saved to 'origin_of_life_evolution.mp4'")