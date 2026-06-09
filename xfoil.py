import sys
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel as C
from scipy.optimize import minimize
import subprocess
import os
import json
from datetime import datetime
from collections import deque
import warnings
warnings.filterwarnings('ignore')

# PyQt5 imports
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QTabWidget, QGroupBox, QPushButton, QLabel, QLineEdit, 
                             QTextEdit, QComboBox, QSlider, QDoubleSpinBox, QSpinBox,
                             QProgressBar, QFileDialog, QMessageBox, QSplitter, QFrame,
                             QGridLayout, QCheckBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPalette, QColor

# ==================== 配置类 ====================
class Config:
    """系统配置参数"""
    def __init__(self):
        # 模型参数
        self.latent_dim = 8
        self.cst_params_dim = 12  # 上下表面各6个CST参数
        self.performance_dim = 3  # Cl, Cd, Cl/Cd
        self.condition_dim = 4    # Re, Ma, Alpha, Thickness
        
        # 训练参数
        self.batch_size = 128
        self.vae_epochs = 500
        self.gp_epochs = 100
        self.learning_rate = 1e-4
        self.kld_weight = 0.01
        
        # 优化参数
        self.bo_n_calls = 50
        self.rl_episodes = 100
        
        # 物理参数范围
        self.reynolds_range = [5e4, 5e6]
        self.mach_range = [0.0, 0.8]
        self.alpha_range = [-5.0, 15.0]
        
        # 路径设置
        self.xfoil_path = 'xfoil'
        self.data_dir = './data/'
        self.model_dir = './models/'
        
        # 创建目录
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.model_dir, exist_ok=True)
        
config = Config()

# ==================== 高级CST参数化 ====================
class AdvancedCSTParameterization:
    """高级翼型参数化类，支持多种翼型家族"""
    def __init__(self, n_params=6):
        self.n_params = n_params
        
    def generate_airfoil(self, wu, wl, te_thickness=0.001, n_points=200):
        """生成翼型坐标 - 使用改进的CST方法"""
        x = np.linspace(0, 1, n_points)
        
        # Class function
        c = np.power(x, 0.5) * np.power(1 - x, 1.0)
        
        # Shape function (Bernstein多项式)
        n = len(wu) - 1
        su = np.zeros_like(x)
        sl = np.zeros_like(x)
        
        for i in range(n + 1):
            binom = np.math.factorial(n) / (np.math.factorial(i) * np.math.factorial(n - i))
            bernstein_i = binom * np.power(x, i) * np.power(1 - x, n - i)
            su += wu[i] * bernstein_i
            sl += wl[i] * bernstein_i
        
        # 上下表面
        yu = c * su + x * te_thickness / 2
        yl = c * sl - x * te_thickness / 2
        
        # 确保前缘闭合
        yu[0] = 0
        yl[0] = 0
        
        return x, yu, yl
    
    def generate_random_parameters(self, n_samples=1, family="general"):
        """生成随机CST参数，支持不同翼型家族"""
        if family == "naca":
            # 生成类似NACA系列的参数
            wu = np.random.uniform(-0.1, 0.1, (n_samples, self.n_params))
            wl = np.random.uniform(-0.1, 0.1, (n_samples, self.n_params))
        elif family == "high_lift":
            # 生成高升力翼型参数
            wu = np.random.uniform(0.0, 0.3, (n_samples, self.n_params))
            wl = np.random.uniform(-0.3, 0.0, (n_samples, self.n_params))
        else:
            # 通用翼型
            wu = np.random.uniform(-0.2, 0.2, (n_samples, self.n_params))
            wl = np.random.uniform(-0.2, 0.2, (n_samples, self.n_params))
            
        return wu, wl

# ==================== 多保真度CFD模拟器 ====================
class MultiFidelityCFD:
    """多保真度CFD评估类"""
    def __init__(self, config):
        self.config = config
        self.xfoil_path = config.xfoil_path
        
    def evaluate(self, airfoil_coords, conditions, fidelity="high"):
        """
        评估翼型性能 - 支持多种保真度级别
        conditions: [Re, Ma, Alpha]
        """
        Re, Ma, Alpha = conditions
        
        if fidelity == "low":
            # 使用XFOIL快速评估
            return self._run_xfoil(airfoil_coords, Re, Alpha)
        elif fidelity == "medium":
            # 使用改进的XFOIL设置
            return self._run_xfoil(airfoil_coords, Re, Alpha, iter=100)
        else:
            # 高保真度评估 (可扩展为调用外部CFD软件)
            return self._run_xfoil(airfoil_coords, Re, Alpha, iter=200)
    
    def _run_xfoil(self, airfoil_coords, Re, alpha, iter=50):
        """运行XFOIL计算气动系数"""
        # 创建临时文件
        airfoil_file = f"{self.config.data_dir}/temp_airfoil.dat"
        input_file = f"{self.config.data_dir}/xfoil_input.inp"
        output_file = f"{self.config.data_dir}/xfoil_output.txt"
        
        # 保存翼型坐标
        with open(airfoil_file, 'w') as f:
            f.write('Temp Airfoil\n')
            for i, (x, y) in enumerate(airfoil_coords):
                f.write(f'{x:.6f} {y:.6f}\n')
                if i > 0 and x == 0.0:  # 避免重复前缘点
                    break
        
        # 创建XFOIL输入
        with open(input_file, 'w') as f:
            f.write(f'LOAD {airfoil_file}\n')
            f.write('Temp Airfoil\n')
            f.write('OPER\n')
            f.write(f'VISC {Re}\n')
            f.write('ITER\n')
            f.write(f'{iter}\n')
            f.write(f'ALFA {alpha}\n')
            f.write('CPWR temp_cp.dat\n')
            f.write('\n')
            f.write('QUIT\n')
        
        # 执行XFOIL
        try:
            with open(output_file, 'w') as f:
                subprocess.run([self.xfoil_path], stdin=open(input_file, 'r'), 
                              stdout=f, stderr=subprocess.PIPE, timeout=30)
            
            # 解析输出
            cl, cd = self._parse_xfoil_output(output_file)
            
            # 计算升阻比
            if cd > 0:
                cl_cd = cl / cd
            else:
                cl_cd = 0.0
                
            return np.array([cl, cd, cl_cd])
            
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return np.array([0.0, 0.0, 0.0])
    
    def _parse_xfoil_output(self, output_file):
        """解析XFOIL输出文件"""
        cl, cd = 0.0, 0.0
        try:
            with open(output_file, 'r') as f:
                lines = f.readlines()
                for line in lines:
                    if 'CL =' in line and 'CD =' in line:
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part == 'CL':
                                cl = float(parts[i+2])
                            elif part == 'CD':
                                cd = float(parts[i+2])
                        break
        except:
            pass
            
        return cl, cd

# ==================== 条件变分自编码器 (CVAE) ====================
class ConditionedVAE(nn.Module):
    """条件变分自编码器，能够根据飞行条件生成翼型"""
    def __init__(self, config):
        super(ConditionedVAE, self).__init__()
        self.config = config
        
        # 编码器
        self.encoder = nn.Sequential(
            nn.Linear(config.cst_params_dim + config.condition_dim, 256),
            nn.LeakyReLU(0.2),
            nn.Linear(256, 128),
            nn.LeakyReLU(0.2),
            nn.Linear(128, 64),
            nn.LeakyReLU(0.2),
        )
        
        self.fc_mu = nn.Linear(64, config.latent_dim)
        self.fc_logvar = nn.Linear(64, config.latent_dim)
        
        # 解码器
        self.decoder = nn.Sequential(
            nn.Linear(config.latent_dim + config.condition_dim, 64),
            nn.LeakyReLU(0.2),
            nn.Linear(64, 128),
            nn.LeakyReLU(0.2),
            nn.Linear(128, 256),
            nn.LeakyReLU(0.2),
            nn.Linear(256, config.cst_params_dim),
        )
    
    def encode(self, x, c):
        """编码输入和条件"""
        h = self.encoder(torch.cat([x, c], dim=1))
        return self.fc_mu(h), self.fc_logvar(h)
    
    def reparameterize(self, mu, logvar):
        """重参数化技巧"""
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std
    
    def decode(self, z, c):
        """从潜在空间解码"""
        return self.decoder(torch.cat([z, c], dim=1))
    
    def forward(self, x, c):
        """前向传播"""
        mu, logvar = self.encode(x, c)
        z = self.reparameterize(mu, logvar)
        return self.decode(z, c), mu, logvar
    
    def generate(self, c, n_samples=1):
        """从条件生成样本"""
        z = torch.randn(n_samples, self.config.latent_dim).to(next(self.parameters()).device)
        return self.decode(z, c)

# ==================== 深度代理模型 ====================
class DeepSurrogate(nn.Module):
    """深度神经网络代理模型，预测翼型性能"""
    def __init__(self, config):
        super(DeepSurrogate, self).__init__()
        
        self.network = nn.Sequential(
            nn.Linear(config.cst_params_dim + config.condition_dim, 512),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, config.performance_dim)
        )
    
    def forward(self, x, c):
        return self.network(torch.cat([x, c], dim=1))

# ==================== 主动学习管理器 ====================
class ActiveLearningManager:
    """主动学习管理器，智能选择最有价值的样本进行评估"""
    def __init__(self, config, surrogate_model):
        self.config = config
        self.surrogate = surrogate_model
        self.acquisition_history = []
        
        # 高斯过程作为不确定性估计器
        self.gp = GaussianProcessRegressor(
            kernel=C(1.0) * RBF(1.0),
            alpha=1e-5,
            normalize_y=True,
            n_restarts_optimizer=5
        )
    
    def acquisition_function(self, X_candidate):
        """获取函数 - 期望改进"""
        if len(self.acquisition_history) < 10:
            return np.random.random(len(X_candidate))
            
        # 使用GP预测均值和标准差
        y_mean, y_std = self.gp.predict(X_candidate, return_std=True)
        
        # 当前最佳性能
        best_perf = max(self.acquisition_history)
        
        # 计算期望改进
        with np.errstate(divide='warn'):
            imp = y_mean - best_perf
            Z = imp / y_std
            ei = imp * dist.norm.cdf(Z) + y_std * dist.norm.pdf(Z)
            ei[y_std == 0.0] = 0.0
            
        return ei
    
    def select_samples(self, X_pool, n_samples=5):
        """选择最有价值的样本"""
        # 计算所有候选样本的获取函数值
        acq_values = self.acquisition_function(X_pool)
        
        # 选择获取函数值最高的样本
        selected_indices = np.argsort(acq_values)[-n_samples:]
        
        return selected_indices, acq_values[selected_indices]
    
    def update(self, X_new, y_new):
        """用新数据更新模型"""
        self.acquisition_history.extend(y_new)
        if len(self.acquisition_history) > 0:
            X_train = np.vstack([self.gp.X_train_, X_new]) if hasattr(self.gp, 'X_train_') else X_new
            y_train = np.concatenate([self.gp.y_train_, y_new]) if hasattr(self.gp, 'y_train_') else y_new
            
            # 只保留最近1000个样本以避免内存问题
            if len(X_train) > 1000:
                X_train = X_train[-1000:]
                y_train = y_train[-1000:]
                
            self.gp.fit(X_train, y_train)

# ==================== 气动生成与优化系统 ====================
class AerodynamicDesignSystem:
    """完整的气动设计与优化系统"""
    def __init__(self, config):
        self.config = config
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # 初始化组件
        self.parameterization = AdvancedCSTParameterization()
        self.cfd_simulator = MultiFidelityCFD(config)
        
        # 初始化模型
        self.cvae = ConditionedVAE(config).to(self.device)
        self.surrogate = DeepSurrogate(config).to(self.device)
        
        # 初始化优化器
        self.active_learner = ActiveLearningManager(config, self.surrogate)
        
        # 数据存储
        self.dataset = {
            'parameters': [],
            'conditions': [],
            'performance': [],
            'fidelity': []
        }
        
        # 加载已有数据
        self.load_data()
        
    def generate_dataset(self, n_samples=1000, fidelity_levels=['low', 'medium']):
        """生成多保真度数据集"""
        print("Generating multi-fidelity dataset...")
        
        for i in range(n_samples):
            # 随机生成翼型参数和条件
            wu, wl = self.parameterization.generate_random_parameters(
                family=np.random.choice(['naca', 'high_lift', 'general'])
            )
            params = np.concatenate([wu[0], wl[0]])
            
            # 随机生成飞行条件
            Re = np.random.uniform(*self.config.reynolds_range)
            Ma = np.random.uniform(*self.config.mach_range)
            Alpha = np.random.uniform(*self.config.alpha_range)
            Thickness = np.random.uniform(0.08, 0.15)  # 相对厚度
            
            conditions = np.array([Re, Ma, Alpha, Thickness])
            
            # 生成翼型坐标
            x, yu, yl = self.parameterization.generate_airfoil(wu[0], wl[0])
            airfoil_coords = np.column_stack([np.concatenate([x, x[::-1]]), 
                                             np.concatenate([yu, yl[::-1]])])
            
            # 多保真度评估
            for fidelity in fidelity_levels:
                performance = self.cfd_simulator.evaluate(
                    airfoil_coords, [Re, Ma, Alpha], fidelity
                )
                
                # 存储数据
                self.dataset['parameters'].append(params)
                self.dataset['conditions'].append(conditions)
                self.dataset['performance'].append(performance)
                self.dataset['fidelity'].append(fidelity)
            
            if (i + 1) % 100 == 0:
                print(f"Generated {i+1}/{n_samples} samples")
                
        # 保存数据
        self.save_data()
        
    def train_cvae(self):
        """训练条件变分自编码器"""
        print("Training Conditioned VAE...")
        
        # 准备数据
        X = np.array(self.dataset['parameters'])
        C = np.array(self.dataset['conditions'])
        
        # 标准化
        X_mean, X_std = X.mean(axis=0), X.std(axis=0)
        C_mean, C_std = C.mean(axis=0), C.std(axis=0)
        
        X = (X - X_mean) / X_std
        C = (C - C_mean) / C_std
        
        # 转换为张量
        X_tensor = torch.FloatTensor(X).to(self.device)
        C_tensor = torch.FloatTensor(C).to(self.device)
        
        dataset = torch.utils.data.TensorDataset(X_tensor, C_tensor)
        dataloader = torch.utils.data.DataLoader(
            dataset, batch_size=self.config.batch_size, shuffle=True
        )
        
        # 训练配置
        optimizer = optim.Adam(self.cvae.parameters(), lr=self.config.learning_rate)
        
        # 训练循环
        self.cvae.train()
        for epoch in range(self.config.vae_epochs):
            total_loss = 0
            recon_loss = 0
            kld_loss = 0
            
            for batch_idx, (x, c) in enumerate(dataloader):
                optimizer.zero_grad()
                
                x_recon, mu, logvar = self.cvae(x, c)
                
                # 计算损失
                recon = nn.MSELoss()(x_recon, x)
                kld = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp())
                loss = recon + self.config.kld_weight * kld
                
                loss.backward()
                optimizer.step()
                
                total_loss += loss.item()
                recon_loss += recon.item()
                kld_loss += kld.item()
            
            if (epoch + 1) % 50 == 0:
                print(f'Epoch {epoch+1}/{self.config.vae_epochs}, '
                      f'Loss: {total_loss/len(dataloader):.4f}, '
                      f'Recon: {recon_loss/len(dataloader):.4f}, '
                      f'KLD: {kld_loss/len(dataloader):.4f}')
        
        # 保存模型
        torch.save(self.cvae.state_dict(), f'{self.config.model_dir}/cvae_model.pth')
        
    def train_surrogate(self):
        """训练深度代理模型"""
        print("Training Deep Surrogate Model...")
        
        # 准备数据
        X = np.array(self.dataset['parameters'])
        C = np.array(self.dataset['conditions'])
        Y = np.array(self.dataset['performance'])
        
        # 标准化
        X_mean, X_std = X.mean(axis=0), X.std(axis=0)
        C_mean, C_std = C.mean(axis=0), C.std(axis=0)
        Y_mean, Y_std = Y.mean(axis=0), Y.std(axis=0)
        
        X = (X - X_mean) / X_std
        C = (C - C_mean) / C_std
        Y = (Y - Y_mean) / Y_std
        
        # 转换为张量
        X_tensor = torch.FloatTensor(X).to(self.device)
        C_tensor = torch.FloatTensor(C).to(self.device)
        Y_tensor = torch.FloatTensor(Y).to(self.device)
        
        dataset = torch.utils.data.TensorDataset(X_tensor, C_tensor, Y_tensor)
        dataloader = torch.utils.data.DataLoader(
            dataset, batch_size=self.config.batch_size, shuffle=True
        )
        
        # 训练配置
        optimizer = optim.Adam(self.surrogate.parameters(), lr=self.config.learning_rate)
        criterion = nn.MSELoss()
        
        # 训练循环
        self.surrogate.train()
        for epoch in range(self.config.gp_epochs):
            total_loss = 0
            
            for batch_idx, (x, c, y) in enumerate(dataloader):
                optimizer.zero_grad()
                
                y_pred = self.surrogate(x, c)
                loss = criterion(y_pred, y)
                
                loss.backward()
                optimizer.step()
                
                total_loss += loss.item()
            
            if (epoch + 1) % 20 == 0:
                print(f'Epoch {epoch+1}/{self.config.gp_epochs}, '
                      f'Loss: {total_loss/len(dataloader):.4f}')
        
        # 保存模型
        torch.save(self.surrogate.state_dict(), f'{self.config.model_dir}/surrogate_model.pth')
        
    def optimize_design(self, target_conditions, objective='max_lift_drag'):
        """优化设计以满足目标条件"""
        print(f"Optimizing design for conditions: {target_conditions}")
        
        # 标准化目标条件
        C = np.array(self.dataset['conditions'])
        C_mean, C_std = C.mean(axis=0), C.std(axis=0)
        target_conditions_norm = (target_conditions - C_mean) / C_std
        
        # 使用贝叶斯优化在潜在空间中搜索
        def objective_function(z):
            z_tensor = torch.FloatTensor(z).unsqueeze(0).to(self.device)
            c_tensor = torch.FloatTensor(target_conditions_norm).unsqueeze(0).to(self.device)
            
            # 解码参数
            with torch.no_grad():
                params = self.cvae.decode(z_tensor, c_tensor).cpu().numpy()[0]
            
            # 使用代理模型预测性能
            params_tensor = torch.FloatTensor(params).unsqueeze(0).to(self.device)
            with torch.no_grad():
                performance = self.surrogate(params_tensor, c_tensor).cpu().numpy()[0]
            
            # 根据目标返回适应度
            if objective == 'max_lift_drag':
                return -performance[2]  # 最大化升阻比
            elif objective == 'max_lift':
                return -performance[0]  # 最大化升力
            elif objective == 'min_drag':
                return performance[1]   # 最小化阻力
            else:
                return -performance[2]  # 默认最大化升阻比
        
        # 运行贝叶斯优化
        from skopt import gp_minimize
        from skopt.space import Real
        
        # 定义搜索空间
        space = [Real(-3, 3) for _ in range(self.config.latent_dim)]
        
        # 运行优化
        result = gp_minimize(
            objective_function, space, n_calls=self.config.bo_n_calls,
            random_state=42, verbose=True
        )
        
        # 获取最佳结果
        best_z = result.x
        best_fitness = -result.fun if objective == 'max_lift_drag' or objective == 'max_lift' else result.fun
        
        print(f"Best fitness: {best_fitness}")
        
        # 解码最佳设计
        z_tensor = torch.FloatTensor(best_z).unsqueeze(0).to(self.device)
        c_tensor = torch.FloatTensor(target_conditions_norm).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            best_params = self.cvae.decode(z_tensor, c_tensor).cpu().numpy()[0]
        
        # 生成翼型坐标
        wu = best_params[:self.config.cst_params_dim//2]
        wl = best_params[self.config.cst_params_dim//2:]
        x, yu, yl = self.parameterization.generate_airfoil(wu, wl)
        
        # 使用高保真模拟验证
        airfoil_coords = np.column_stack([np.concatenate([x, x[::-1]]), 
                                         np.concatenate([yu, yl[::-1]])])
        Re, Ma, Alpha, _ = target_conditions
        performance = self.cfd_simulator.evaluate(
            airfoil_coords, [Re, Ma, Alpha], fidelity="high"
        )
        
        print(f"Verified performance - Cl: {performance[0]:.4f}, "
              f"Cd: {performance[1]:.4f}, Cl/Cd: {performance[2]:.4f}")
        
        return {
            'parameters': best_params,
            'airfoil_coords': (x, yu, yl),
            'performance': performance,
            'latent_vector': best_z
        }
    
    def active_learning_cycle(self, n_cycles=5, n_samples_per_cycle=10):
        """执行主动学习循环以改进代理模型"""
        print("Starting active learning cycle...")
        
        # 获取当前数据集
        X_pool = np.array(self.dataset['parameters'])
        C_pool = np.array(self.dataset['conditions'])
        
        # 合并特征
        X_full = np.hstack([X_pool, C_pool])
        
        for cycle in range(n_cycles):
            print(f"Active learning cycle {cycle+1}/{n_cycles}")
            
            # 选择最有价值的样本
            selected_indices, acq_values = self.active_learner.select_samples(
                X_full, n_samples=n_samples_per_cycle
            )
            
            print(f"Selected {len(selected_indices)} samples with acquisition values: {acq_values}")
            
            # 高保真评估选定的样本
            new_X = []
            new_y = []
            
            for idx in selected_indices:
                params = X_pool[idx]
                conditions = C_pool[idx]
                
                # 生成翼型
                wu = params[:self.config.cst_params_dim//2]
                wl = params[self.config.cst_params_dim//2:]
                x, yu, yl = self.parameterization.generate_airfoil(wu, wl)
                airfoil_coords = np.column_stack([np.concatenate([x, x[::-1]]), 
                                                 np.concatenate([yu, yl[::-1]])])
                
                # 高保真评估
                Re, Ma, Alpha, _ = conditions
                performance = self.cfd_simulator.evaluate(
                    airfoil_coords, [Re, Ma, Alpha], fidelity="high"
                )
                
                # 添加到新数据
                new_X.append(np.hstack([params, conditions]))
                new_y.append(performance[2])  # 使用升阻比作为目标
                
                # 更新数据集
                self.dataset['fidelity'][idx] = "high"
                self.dataset['performance'][idx] = performance
            
            # 更新主动学习器
            self.active_learner.update(np.array(new_X), np.array(new_y))
            
            # 重新训练代理模型
            self.train_surrogate()
        
        # 保存更新后的数据
        self.save_data()
        
    def save_data(self):
        """保存数据集"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.config.data_dir}/dataset_{timestamp}.npz"
        
        np.savez(
            filename,
            parameters=np.array(self.dataset['parameters']),
            conditions=np.array(self.dataset['conditions']),
            performance=np.array(self.dataset['performance']),
            fidelity=np.array(self.dataset['fidelity'])
        )
        
        print(f"Dataset saved to {filename}")
    
    def load_data(self):
        """加载数据集"""
        data_files = [f for f in os.listdir(self.config.data_dir) if f.startswith('dataset_')]
        
        if data_files:
            # 加载最新的数据文件
            latest_file = sorted(data_files)[-1]
            data = np.load(f"{self.config.data_dir}/{latest_file}")
            
            self.dataset['parameters'] = data['parameters'].tolist()
            self.dataset['conditions'] = data['conditions'].tolist()
            self.dataset['performance'] = data['performance'].tolist()
            self.dataset['fidelity'] = data['fidelity'].tolist()
            
            print(f"Loaded dataset with {len(self.dataset['parameters'])} samples from {latest_file}")

# ==================== PyQt5界面组件 ====================
class MplCanvas(FigureCanvas):
    """Matplotlib画布"""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super(MplCanvas, self).__init__(self.fig)
        self.setParent(parent)
        
    def plot_airfoil(self, x, yu, yl, title="Airfoil Profile"):
        """绘制翼型"""
        self.axes.clear()
        self.axes.plot(x, yu, 'b-', label='Upper surface')
        self.axes.plot(x, yl, 'r-', label='Lower surface')
        self.axes.set_xlabel('x/c')
        self.axes.set_ylabel('y/c')
        self.axes.set_title(title)
        self.axes.legend()
        self.axes.grid(True)
        self.axes.axis('equal')
        self.draw()
        
    def plot_optimization_progress(self, progress_data, title="Optimization Progress"):
        """绘制优化进度"""
        self.axes.clear()
        self.axes.plot(progress_data, 'b-')
        self.axes.set_xlabel('Iteration')
        self.axes.set_ylabel('Fitness')
        self.axes.set_title(title)
        self.axes.grid(True)
        self.draw()

class WorkerThread(QThread):
    """工作线程，用于执行耗时操作"""
    progress = pyqtSignal(int)
    message = pyqtSignal(str)
    finished = pyqtSignal(object)
    
    def __init__(self, task, *args, **kwargs):
        super().__init__()
        self.task = task
        self.args = args
        self.kwargs = kwargs
        
    def run(self):
        try:
            result = self.task(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.message.emit(f"Error: {str(e)}")
            self.finished.emit(None)

class AerodynamicDesignApp(QMainWindow):
    """气动设计应用主窗口"""
    def __init__(self):
        super().__init__()
        self.system = AerodynamicDesignSystem(config)
        self.initUI()
        
    def initUI(self):
        """初始化用户界面"""
        self.setWindowTitle('Aerodynamic Design System')
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中心部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # 创建左侧控制面板
        control_panel = QWidget()
        control_panel.setFixedWidth(300)
        control_layout = QVBoxLayout(control_panel)
        
        # 创建选项卡
        self.tabs = QTabWidget()
        control_layout.addWidget(self.tabs)
        
        # 数据生成选项卡
        data_tab = QWidget()
        data_layout = QVBoxLayout(data_tab)
        self.setup_data_tab(data_layout)
        self.tabs.addTab(data_tab, "Data Generation")
        
        # 模型训练选项卡
        training_tab = QWidget()
        training_layout = QVBoxLayout(training_tab)
        self.setup_training_tab(training_layout)
        self.tabs.addTab(training_tab, "Model Training")
        
        # 优化选项卡
        optimization_tab = QWidget()
        optimization_layout = QVBoxLayout(optimization_tab)
        self.setup_optimization_tab(optimization_layout)
        self.tabs.addTab(optimization_tab, "Optimization")
        
        # 添加到主布局
        main_layout.addWidget(control_panel)
        
        # 创建右侧可视化区域
        viz_panel = QWidget()
        viz_layout = QVBoxLayout(viz_panel)
        
        # 翼型可视化
        self.airfoil_canvas = MplCanvas(self, width=5, height=4, dpi=100)
        viz_layout.addWidget(self.airfoil_canvas)
        
        # 优化进度可视化
        self.progress_canvas = MplCanvas(self, width=5, height=4, dpi=100)
        viz_layout.addWidget(self.progress_canvas)
        
        main_layout.addWidget(viz_panel)
        
        # 状态栏
        self.statusBar().showMessage('Ready')
        
    def setup_data_tab(self, layout):
        """设置数据生成选项卡"""
        # 样本数量设置
        sample_group = QGroupBox("Dataset Generation")
        sample_layout = QVBoxLayout(sample_group)
        
        sample_count_layout = QHBoxLayout()
        sample_count_layout.addWidget(QLabel("Number of Samples:"))
        self.sample_count = QSpinBox()
        self.sample_count.setRange(100, 10000)
        self.sample_count.setValue(1000)
        sample_count_layout.addWidget(self.sample_count)
        sample_layout.addLayout(sample_count_layout)
        
        # 保真度选择
        fidelity_layout = QHBoxLayout()
        fidelity_layout.addWidget(QLabel("Fidelity Levels:"))
        self.fidelity_combo = QComboBox()
        self.fidelity_combo.addItems(["Low", "Medium", "Low + Medium"])
        fidelity_layout.addWidget(self.fidelity_combo)
        sample_layout.addLayout(fidelity_layout)
        
        # 生成按钮
        self.generate_btn = QPushButton("Generate Dataset")
        self.generate_btn.clicked.connect(self.generate_dataset)
        sample_layout.addWidget(self.generate_btn)
        
        # 进度条
        self.data_progress = QProgressBar()
        sample_layout.addWidget(self.data_progress)
        
        layout.addWidget(sample_group)
        layout.addStretch()
        
    def setup_training_tab(self, layout):
        """设置模型训练选项卡"""
        # VAE训练设置
        vae_group = QGroupBox("VAE Training")
        vae_layout = QVBoxLayout(vae_group)
        
        epochs_layout = QHBoxLayout()
        epochs_layout.addWidget(QLabel("Epochs:"))
        self.vae_epochs = QSpinBox()
        self.vae_epochs.setRange(100, 2000)
        self.vae_epochs.setValue(500)
        epochs_layout.addWidget(self.vae_epochs)
        vae_layout.addLayout(epochs_layout)
        
        self.train_vae_btn = QPushButton("Train VAE")
        self.train_vae_btn.clicked.connect(self.train_vae)
        vae_layout.addWidget(self.train_vae_btn)
        
        # 代理模型训练设置
        surrogate_group = QGroupBox("Surrogate Model Training")
        surrogate_layout = QVBoxLayout(surrogate_group)
        
        surr_epochs_layout = QHBoxLayout()
        surr_epochs_layout.addWidget(QLabel("Epochs:"))
        self.surrogate_epochs = QSpinBox()
        self.surrogate_epochs.setRange(50, 500)
        self.surrogate_epochs.setValue(100)
        surr_epochs_layout.addWidget(self.surrogate_epochs)
        surrogate_layout.addLayout(surr_epochs_layout)
        
        self.train_surrogate_btn = QPushButton("Train Surrogate Model")
        self.train_surrogate_btn.clicked.connect(self.train_surrogate)
        surrogate_layout.addWidget(self.train_surrogate_btn)
        
        # 主动学习设置
        active_learning_group = QGroupBox("Active Learning")
        active_layout = QVBoxLayout(active_learning_group)
        
        al_cycles_layout = QHBoxLayout()
        al_cycles_layout.addWidget(QLabel("Cycles:"))
        self.al_cycles = QSpinBox()
        self.al_cycles.setRange(1, 20)
        self.al_cycles.setValue(5)
        al_cycles_layout.addWidget(self.al_cycles)
        active_layout.addLayout(al_cycles_layout)
        
        al_samples_layout = QHBoxLayout()
        al_samples_layout.addWidget(QLabel("Samples per Cycle:"))
        self.al_samples = QSpinBox()
        self.al_samples.setRange(1, 50)
        self.al_samples.setValue(10)
        al_samples_layout.addWidget(self.al_samples)
        active_layout.addLayout(al_samples_layout)
        
        self.active_learning_btn = QPushButton("Run Active Learning")
        self.active_learning_btn.clicked.connect(self.run_active_learning)
        active_layout.addWidget(self.active_learning_btn)
        
        # 训练进度条
        self.training_progress = QProgressBar()
        active_layout.addWidget(self.training_progress)
        
        layout.addWidget(vae_group)
        layout.addWidget(surrogate_group)
        layout.addWidget(active_learning_group)
        layout.addStretch()
        
    def setup_optimization_tab(self, layout):
        """设置优化选项卡"""
        # 目标条件设置
        conditions_group = QGroupBox("Target Conditions")
        conditions_layout = QGridLayout(conditions_group)
        
        conditions_layout.addWidget(QLabel("Reynolds Number:"), 0, 0)
        self.reynolds = QDoubleSpinBox()
        self.reynolds.setRange(50000, 5000000)
        self.reynolds.setValue(1000000)
        self.reynolds.setDecimals(0)
        conditions_layout.addWidget(self.reynolds, 0, 1)
        
        conditions_layout.addWidget(QLabel("Mach Number:"), 1, 0)
        self.mach = QDoubleSpinBox()
        self.mach.setRange(0.0, 0.8)
        self.mach.setValue(0.3)
        self.mach.setSingleStep(0.05)
        conditions_layout.addWidget(self.mach, 1, 1)
        
        conditions_layout.addWidget(QLabel("Angle of Attack:"), 2, 0)
        self.alpha = QDoubleSpinBox()
        self.alpha.setRange(-5.0, 15.0)
        self.alpha.setValue(2.0)
        self.alpha.setSingleStep(0.5)
        conditions_layout.addWidget(self.alpha, 2, 1)
        
        conditions_layout.addWidget(QLabel("Thickness Ratio:"), 3, 0)
        self.thickness = QDoubleSpinBox()
        self.thickness.setRange(0.08, 0.15)
        self.thickness.setValue(0.12)
        self.thickness.setSingleStep(0.01)
        conditions_layout.addWidget(self.thickness, 3, 1)
        
        # 优化目标设置
        objective_group = QGroupBox("Optimization Objective")
        objective_layout = QVBoxLayout(objective_group)
        
        self.objective_combo = QComboBox()
        self.objective_combo.addItems(["Maximize Lift/Drag", "Maximize Lift", "Minimize Drag"])
        objective_layout.addWidget(self.objective_combo)
        
        # 优化设置
        optimization_group = QGroupBox("Optimization Settings")
        optimization_layout = QVBoxLayout(optimization_group)
        
        iterations_layout = QHBoxLayout()
        iterations_layout.addWidget(QLabel("Iterations:"))
        self.iterations = QSpinBox()
        self.iterations.setRange(10, 200)
        self.iterations.setValue(50)
        iterations_layout.addWidget(self.iterations)
        optimization_layout.addLayout(iterations_layout)
        
        self.optimize_btn = QPushButton("Start Optimization")
        self.optimize_btn.clicked.connect(self.start_optimization)
        optimization_layout.addWidget(self.optimize_btn)
        
        # 优化进度条
        self.optimization_progress = QProgressBar()
        optimization_layout.addWidget(self.optimization_progress)
        
        # 结果显示
        result_group = QGroupBox("Results")
        result_layout = QVBoxLayout(result_group)
        
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        result_layout.addWidget(self.result_text)
        
        self.save_result_btn = QPushButton("Save Results")
        self.save_result_btn.clicked.connect(self.save_results)
        result_layout.addWidget(self.save_result_btn)
        
        layout.addWidget(conditions_group)
        layout.addWidget(objective_group)
        layout.addWidget(optimization_group)
        layout.addWidget(result_group)
        
    def generate_dataset(self):
        """生成数据集"""
        n_samples = self.sample_count.value()
        fidelity_option = self.fidelity_combo.currentText()
        
        if fidelity_option == "Low":
            fidelity_levels = ["low"]
        elif fidelity_option == "Medium":
            fidelity_levels = ["medium"]
        else:
            fidelity_levels = ["low", "medium"]
        
        self.worker = WorkerThread(self.system.generate_dataset, n_samples, fidelity_levels)
        self.worker.message.connect(self.statusBar().showMessage)
        self.worker.finished.connect(self.dataset_generation_finished)
        self.worker.start()
        
        self.generate_btn.setEnabled(False)
        self.statusBar().showMessage("Generating dataset...")
        
    def dataset_generation_finished(self, result):
        """数据集生成完成"""
        self.generate_btn.setEnabled(True)
        self.statusBar().showMessage("Dataset generation completed")
        QMessageBox.information(self, "Success", "Dataset generation completed successfully!")
        
    def train_vae(self):
        """训练VAE模型"""
        config.vae_epochs = self.vae_epochs.value()
        
        self.worker = WorkerThread(self.system.train_cvae)
        self.worker.message.connect(self.statusBar().showMessage)
        self.worker.finished.connect(self.vae_training_finished)
        self.worker.start()
        
        self.train_vae_btn.setEnabled(False)
        self.statusBar().showMessage("Training VAE...")
        
    def vae_training_finished(self, result):
        """VAE训练完成"""
        self.train_vae_btn.setEnabled(True)
        self.statusBar().showMessage("VAE training completed")
        QMessageBox.information(self, "Success", "VAE training completed successfully!")
        
    def train_surrogate(self):
        """训练代理模型"""
        config.gp_epochs = self.surrogate_epochs.value()
        
        self.worker = WorkerThread(self.system.train_surrogate)
        self.worker.message.connect(self.statusBar().showMessage)
        self.worker.finished.connect(self.surrogate_training_finished)
        self.worker.start()
        
        self.train_surrogate_btn.setEnabled(False)
        self.statusBar().showMessage("Training surrogate model...")
        
    def surrogate_training_finished(self, result):
        """代理模型训练完成"""
        self.train_surrogate_btn.setEnabled(True)
        self.statusBar().showMessage("Surrogate model training completed")
        QMessageBox.information(self, "Success", "Surrogate model training completed successfully!")
        
    def run_active_learning(self):
        """运行主动学习"""
        n_cycles = self.al_cycles.value()
        n_samples = self.al_samples.value()
        
        self.worker = WorkerThread(self.system.active_learning_cycle, n_cycles, n_samples)
        self.worker.message.connect(self.statusBar().showMessage)
        self.worker.finished.connect(self.active_learning_finished)
        self.worker.start()
        
        self.active_learning_btn.setEnabled(False)
        self.statusBar().showMessage("Running active learning...")
        
    def active_learning_finished(self, result):
        """主动学习完成"""
        self.active_learning_btn.setEnabled(True)
        self.statusBar().showMessage("Active learning completed")
        QMessageBox.information(self, "Success", "Active learning completed successfully!")
        
    def start_optimization(self):
        """开始优化"""
        # 获取目标条件
        target_conditions = np.array([
            self.reynolds.value(),
            self.mach.value(),
            self.alpha.value(),
            self.thickness.value()
        ])
        
        # 获取优化目标
        objective_option = self.objective_combo.currentText()
        if objective_option == "Maximize Lift/Drag":
            objective = "max_lift_drag"
        elif objective_option == "Maximize Lift":
            objective = "max_lift"
        else:
            objective = "min_drag"
        
        config.bo_n_calls = self.iterations.value()
        
        self.worker = WorkerThread(self.system.optimize_design, target_conditions, objective)
        self.worker.message.connect(self.statusBar().showMessage)
        self.worker.finished.connect(self.optimization_finished)
        self.worker.start()
        
        self.optimize_btn.setEnabled(False)
        self.statusBar().showMessage("Running optimization...")
        
    def optimization_finished(self, result):
        """优化完成"""
        self.optimize_btn.setEnabled(True)
        
        if result is None:
            self.statusBar().showMessage("Optimization failed")
            QMessageBox.critical(self, "Error", "Optimization failed!")
            return
            
        self.optimization_result = result
        
        # 显示结果
        perf = result['performance']
        self.result_text.setText(
            f"Optimization completed successfully!\n\n"
            f"Performance results:\n"
            f"Lift coefficient (Cl): {perf[0]:.4f}\n"
            f"Drag coefficient (Cd): {perf[1]:.4f}\n"
            f"Lift-to-Drag ratio (Cl/Cd): {perf[2]:.2f}\n\n"
            f"Target conditions:\n"
            f"Reynolds number: {self.reynolds.value():.0f}\n"
            f"Mach number: {self.mach.value():.2f}\n"
            f"Angle of attack: {self.alpha.value():.1f}°\n"
            f"Thickness ratio: {self.thickness.value():.2f}"
        )
        
        # 可视化结果
        x, yu, yl = result['airfoil_coords']
        self.airfoil_canvas.plot_airfoil(
            x, yu, yl, 
            f"Optimized Airfoil - Cl/Cd: {perf[2]:.2f}"
        )
        
        self.statusBar().showMessage("Optimization completed")
        
    def save_results(self):
        """保存优化结果"""
        if not hasattr(self, 'optimization_result'):
            QMessageBox.warning(self, "Warning", "No optimization results to save!")
            return
            
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getSaveFileName(
            self, "Save Results", "", "Text Files (*.txt);;All Files (*)", options=options)
            
        if fileName:
            try:
                with open(fileName, 'w') as f:
                    f.write(self.result_text.toPlainText())
                    
                # 保存翼型坐标
                coords_file = fileName.replace('.txt', '_coords.txt')
                x, yu, yl = self.optimization_result['airfoil_coords']
                with open(coords_file, 'w') as f:
                    f.write("x/c\tUpper y/c\tLower y/c\n")
                    for i in range(len(x)):
                        f.write(f"{x[i]:.6f}\t{yu[i]:.6f}\t{yl[i]:.6f}\n")
                        
                QMessageBox.information(self, "Success", "Results saved successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save results: {str(e)}")

# ==================== 主程序入口 ====================
if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = AerodynamicDesignApp()
    window.show()
    
    sys.exit(app.exec_())