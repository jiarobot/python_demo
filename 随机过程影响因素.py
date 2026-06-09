import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import pandas as pd
from matplotlib.gridspec import GridSpec
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')

class StochasticProcessAnalyzer:
    def __init__(self):
        self.results = {}
    
    def markov_chain_analysis(self, p_values, num_steps=100, num_simulations=50):
        """
        分析马尔可夫链中转移概率对随机性的影响
        """
        print("=== 马尔可夫链分析 ===")
        
        fig = plt.figure(figsize=(15, 10))
        gs = GridSpec(3, 2, figure=fig)
        
        # 存储结果
        entropy_results = []
        deterministic_results = []
        
        for i, p in enumerate(p_values):
            print(f"\n分析转移概率 p = {p}")
            
            # 二状态马尔可夫链的转移矩阵
            P = np.array([[p, 1-p],
                          [1-p, p]])
            
            # 模拟多个轨迹
            trajectories = []
            current_states = np.zeros(num_simulations, dtype=int)  # 初始状态全为0
            
            for step in range(num_steps):
                new_states = []
                for state in current_states:
                    # 根据转移概率选择下一个状态
                    next_state = np.random.choice([0, 1], p=P[state])
                    new_states.append(next_state)
                
                trajectories.append(new_states)
                current_states = np.array(new_states)
            
            trajectories = np.array(trajectories).T  # 转置为 (num_simulations, num_steps)
            
            # 计算条件熵
            entropy = -p * np.log(p + 1e-10) - (1-p) * np.log(1-p + 1e-10)
            entropy_results.append(entropy)
            
            # 计算确定性程度（状态变化的方差）
            state_variance = np.var(trajectories, axis=0).mean()
            deterministic_results.append(1 / (1 + state_variance))  # 方差越小，确定性越高
            
            # 绘制轨迹
            ax = fig.add_subplot(gs[i//2, i%2])
            for j in range(min(10, num_simulations)):  # 只绘制前10个轨迹
                ax.plot(trajectories[j], alpha=0.7, linewidth=1)
            
            ax.set_title(f'转移概率 p = {p}\n熵 = {entropy:.3f}')
            ax.set_xlabel('时间步')
            ax.set_ylabel('状态')
            ax.set_ylim(-0.1, 1.1)
        
        # 绘制熵和确定性程度随p的变化
        ax_entropy = fig.add_subplot(gs[2, :])
        ax_entropy.plot(p_values, entropy_results, 'o-', label='条件熵', linewidth=2)
        ax_det = ax_entropy.twinx()
        ax_det.plot(p_values, deterministic_results, 's-', color='red', label='确定性程度', linewidth=2)
        
        ax_entropy.set_xlabel('转移概率 p')
        ax_entropy.set_ylabel('条件熵', color='blue')
        ax_det.set_ylabel('确定性程度', color='red')
        ax_entropy.legend(loc='upper left')
        ax_det.legend(loc='upper right')
        ax_entropy.set_title('转移概率对随机性的影响')
        
        plt.tight_layout()
        plt.show()
        
        return {
            'p_values': p_values,
            'entropy': entropy_results,
            'determinism': deterministic_results
        }
    
    def sde_analysis(self, sigma_values, mu=0.1, T=1.0, dt=0.01, num_paths=20):
        """
        分析随机微分方程中噪声水平对随机性的影响
        """
        print("\n=== 随机微分方程分析 ===")
        
        fig = plt.figure(figsize=(15, 12))
        gs = GridSpec(3, 2, figure=fig)
        
        time = np.arange(0, T + dt, dt)
        n_steps = len(time)
        
        variance_results = []
        determinism_results = []
        
        for i, sigma in enumerate(sigma_values):
            print(f"\n分析噪声水平 σ = {sigma}")
            
            # 模拟SDE路径: dX_t = μ dt + σ dW_t
            paths = np.zeros((num_paths, n_steps))
            paths[:, 0] = 0  # 初始条件
            
            for step in range(1, n_steps):
                dW = np.random.normal(0, np.sqrt(dt), num_paths)  # 维纳过程增量
                paths[:, step] = paths[:, step-1] + mu * dt + sigma * dW
            
            # 计算路径方差
            path_variance = np.var(paths, axis=0)
            avg_variance = path_variance.mean()
            variance_results.append(avg_variance)
            
            # 确定性程度（与确定性解的接近程度）
            deterministic_path = mu * time  # 确定性解
            mse = np.mean((paths - deterministic_path[np.newaxis, :])**2)
            determinism = 1 / (1 + mse)  # MSE越小，确定性越高
            determinism_results.append(determinism)
            
            # 绘制路径
            ax = fig.add_subplot(gs[i//2, i%2])
            for j in range(min(10, num_paths)):
                ax.plot(time, paths[j], alpha=0.6, linewidth=1)
            
            # 绘制确定性解
            ax.plot(time, deterministic_path, 'k--', linewidth=2, label='确定性解')
            
            ax.set_title(f'噪声水平 σ = {sigma}\n路径方差 = {avg_variance:.4f}')
            ax.set_xlabel('时间')
            ax.set_ylabel('X(t)')
            ax.legend()
        
        # 绘制方差和确定性程度随sigma的变化
        ax_var = fig.add_subplot(gs[2, :])
        ax_var.plot(sigma_values, variance_results, 'o-', label='路径方差', linewidth=2)
        ax_det = ax_var.twinx()
        ax_det.plot(sigma_values, determinism_results, 's-', color='red', 
                   label='确定性程度', linewidth=2)
        
        ax_var.set_xlabel('噪声水平 σ')
        ax_var.set_ylabel('路径方差', color='blue')
        ax_det.set_ylabel('确定性程度', color='red')
        ax_var.legend(loc='upper left')
        ax_det.legend(loc='upper right')
        ax_var.set_title('噪声水平对随机性的影响')
        
        plt.tight_layout()
        plt.show()
        
        return {
            'sigma_values': sigma_values,
            'variance': variance_results,
            'determinism': determinism_results
        }
    
    def absorption_state_analysis(self, absorption_prob=0.1, num_states=5, num_steps=50, num_simulations=30):
        """
        分析吸收状态对随机过程的影响
        """
        print("\n=== 吸收状态分析 ===")
        
        # 创建转移矩阵（包含吸收状态）
        P = np.random.dirichlet(np.ones(num_states), size=num_states)
        
        # 将状态0设置为吸收状态
        P[0, :] = 0
        P[0, 0] = 1  # 吸收状态
        
        # 增加从其他状态到吸收状态的转移概率
        for i in range(1, num_states):
            P[i, 0] = absorption_prob
            P[i, 1:] = (1 - absorption_prob) * P[i, 1:] / P[i, 1:].sum()
        
        print("转移矩阵:")
        print(P.round(3))
        
        # 模拟过程
        trajectories = []
        absorption_times = []
        
        for sim in range(num_simulations):
            states = [np.random.choice(num_states)]  # 随机初始状态
            absorption_time = None
            
            for step in range(num_steps):
                current_state = states[-1]
                next_state = np.random.choice(num_states, p=P[current_state])
                states.append(next_state)
                
                # 检查是否被吸收
                if next_state == 0 and absorption_time is None:
                    absorption_time = step + 1
            
            trajectories.append(states)
            absorption_times.append(absorption_time if absorption_time is not None else num_steps)
        
        # 可视化
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # 绘制轨迹
        for i, states in enumerate(trajectories[:15]):  # 只显示前15个轨迹
            ax1.plot(states, alpha=0.7, linewidth=1, 
                    label=f'Sim {i+1}' if i < 3 else "")
        
        ax1.axhline(y=0, color='red', linestyle='--', linewidth=2, label='吸收状态')
        ax1.set_xlabel('时间步')
        ax1.set_ylabel('状态')
        ax1.set_title(f'吸收状态对过程的影响 (吸收概率={absorption_prob})')
        ax1.legend()
        
        # 绘制吸收时间分布
        ax2.hist(absorption_times, bins=20, alpha=0.7, edgecolor='black')
        ax2.set_xlabel('吸收时间')
        ax2.set_ylabel('频数')
        ax2.set_title('吸收时间分布')
        
        plt.tight_layout()
        plt.show()
        
        return {
            'absorption_times': absorption_times,
            'trajectories': trajectories,
            'transition_matrix': P
        }
    
    def comprehensive_analysis(self):
        """
        综合可视化分析
        """
        print("=== 综合可视化分析 ===")
        
        # 1. 马尔可夫链分析
        p_values = [0.1, 0.3, 0.5, 0.7, 0.9, 0.99]
        markov_results = self.markov_chain_analysis(p_values)
        
        # 2. SDE分析
        sigma_values = [0.01, 0.1, 0.3, 0.5, 1.0, 2.0]
        sde_results = self.sde_analysis(sigma_values)
        
        # 3. 吸收状态分析
        absorption_results = self.absorption_state_analysis()
        
        # 创建综合对比图
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        
        # 马尔可夫链结果可视化
        ax1.plot(markov_results['p_values'], markov_results['entropy'], 'bo-', 
                linewidth=2, markersize=8, label='条件熵')
        ax1.set_xlabel('转移概率 p')
        ax1.set_ylabel('条件熵', color='blue')
        ax1.set_title('马尔可夫链: 转移概率 vs 随机性')
        ax1.grid(True, alpha=0.3)
        
        ax1_twin = ax1.twinx()
        ax1_twin.plot(markov_results['p_values'], markov_results['determinism'], 'ro-',
                     linewidth=2, markersize=8, label='确定性程度')
        ax1_twin.set_ylabel('确定性程度', color='red')
        
        # SDE结果可视化
        ax2.plot(sde_results['sigma_values'], sde_results['variance'], 'bo-',
                linewidth=2, markersize=8, label='路径方差')
        ax2.set_xlabel('噪声水平 σ')
        ax2.set_ylabel('路径方差', color='blue')
        ax2.set_title('SDE: 噪声水平 vs 随机性')
        ax2.grid(True, alpha=0.3)
        
        ax2_twin = ax2.twinx()
        ax2_twin.plot(sde_results['sigma_values'], sde_results['determinism'], 'ro-',
                     linewidth=2, markersize=8, label='确定性程度')
        ax2_twin.set_ylabel('确定性程度', color='red')
        
        # 吸收时间分布
        ax3.hist(absorption_results['absorption_times'], bins=15, 
                alpha=0.7, color='green', edgecolor='black')
        ax3.set_xlabel('吸收时间')
        ax3.set_ylabel('频数')
        ax3.set_title('吸收状态: 吸收时间分布')
        ax3.grid(True, alpha=0.3)
        
        # 随机性量化对比
        categories = ['低转移概率\n(p=0.1)', '平衡状态\n(p=0.5)', '高转移概率\n(p=0.99)',
                     '低噪声\n(σ=0.01)', '中等噪声\n(σ=0.5)', '高噪声\n(σ=2.0)']
        randomness_scores = [
            markov_results['entropy'][0],  # p=0.1
            markov_results['entropy'][2],  # p=0.5
            markov_results['entropy'][5],  # p=0.99
            1/sde_results['variance'][0],  # σ=0.01 (倒数，因为方差小表示随机性小)
            1/sde_results['variance'][3],  # σ=0.5
            1/sde_results['variance'][5]   # σ=2.0
        ]
        
        ax4.bar(categories, randomness_scores, color=['blue', 'blue', 'blue', 'red', 'red', 'red'],
               alpha=0.7, edgecolor='black')
        ax4.set_ylabel('随机性指标 (1/方差 或 熵)')
        ax4.set_title('不同参数下的随机性比较')
        ax4.tick_params(axis='x', rotation=45)
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
        
        # 打印统计摘要
        print("\n=== 统计分析摘要 ===")
        print(f"马尔可夫链最大熵: {max(markov_results['entropy']):.3f} (p={p_values[np.argmax(markov_results['entropy'])]})")
        print(f"马尔可夫链最小熵: {min(markov_results['entropy']):.3f} (p={p_values[np.argmin(markov_results['entropy'])]})")
        print(f"SDE最大方差: {max(sde_results['variance']):.3f} (σ={sigma_values[np.argmax(sde_results['variance'])]})")
        print(f"SDE最小方差: {min(sde_results['variance']):.3f} (σ={sigma_values[np.argmin(sde_results['variance'])]})")
        print(f"平均吸收时间: {np.mean(absorption_results['absorption_times']):.1f} 步")
        
        return {
            'markov': markov_results,
            'sde': sde_results,
            'absorption': absorption_results
        }

# 运行分析
if __name__ == "__main__":
    analyzer = StochasticProcessAnalyzer()
    results = analyzer.comprehensive_analysis()