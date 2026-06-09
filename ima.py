import random
import sys
import os
import json
import time
from datetime import datetime
import numpy as np
import math
from collections import deque

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import Normal, kl_divergence
from torch.utils.data import DataLoader, TensorDataset, Dataset

import pyqtgraph as pg
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize, QRectF 
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QSlider, QLabel, QComboBox, QCheckBox, QGroupBox,
                             QTextEdit, QTabWidget, QSpinBox, QDoubleSpinBox, QFileDialog,
                             QSplitter, QProgressBar, QListWidget, QTableWidget, QTableWidgetItem,
                             QHeaderView, QMessageBox, QToolBar, QStatusBar, QDockWidget,
                             QFormLayout, QSizePolicy, QMenu, QMenuBar, QGridLayout,
                             QFrame, QToolButton, QStyle, QStyleOption, QLineEdit)
from PyQt6.QtGui import (QPainter, QColor, QPen, QFont, QPixmap, QImage, QActionEvent, 
                         QIcon, QPalette, QLinearGradient, QBrush, QPainterPath, QKeySequence,QAction)

# 设置pyqtgraph样式
pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')
pg.setConfigOption('antialias', True)

class EnhancedTrainingThread(QThread):
    """增强的训练线程，支持更多统计信息和控制选项"""
    update_signal = pyqtSignal(dict)
    finished_signal = pyqtSignal()
    epoch_complete_signal = pyqtSignal(int, float)
    
    def __init__(self, model, dataloader, epochs, imagination_prob, 
                 imagination_strength, use_adversarial, use_memory, 
                 learning_rate, weight_decay, parent=None):
        super().__init__(parent)
        self.model = model
        self.dataloader = dataloader
        self.epochs = epochs
        self.imagination_prob = imagination_prob
        self.imagination_strength = imagination_strength
        self.use_adversarial = use_adversarial
        self.use_memory = use_memory
        self.learning_rate = learning_rate
        self.weight_decay = weight_decay
        self.is_running = True
        self.is_paused = False
        self.current_epoch = 0
        self.best_loss = float('inf')
        
        # 优化器
        self.optimizer = torch.optim.AdamW(
            list(model.parameters()), 
            lr=learning_rate, 
            weight_decay=weight_decay
        )
        
        # 学习率调度器
        self.scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer, mode='min', factor=0.5, patience=3
        )
        
        # 判别器优化器
        if use_adversarial:
            self.discriminator_optimizer = torch.optim.AdamW(
                list(model.imagination_layer.discriminator.parameters()), 
                lr=learning_rate/2,
                weight_decay=weight_decay
            )
            self.discriminator_scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
                self.discriminator_optimizer, mode='min', factor=0.5, patience=3
            )
        
        # 训练历史记录
        self.history = {
            'loss': [], 'kl_loss': [], 'rec_loss': [], 'adv_loss': [], 
            'disc_loss': [], 'diversity_loss': [], 'lr': []
        }
        
    def run(self):
        """训练循环"""
        self.model.train()
        
        for epoch in range(self.epochs):
            if not self.is_running:
                break
                
            # 等待暂停状态结束
            while self.is_paused and self.is_running:
                time.sleep(0.1)
                
            self.current_epoch = epoch
            total_loss = 0
            total_kl_loss = 0
            total_rec_loss = 0
            total_adv_loss = 0
            total_disc_loss = 0
            total_div_loss = 0
            batch_count = 0
            
            for batch_idx, (data, target) in enumerate(self.dataloader):
                if not self.is_running:
                    break
                    
                # 等待暂停状态结束
                while self.is_paused and self.is_running:
                    time.sleep(0.1)
                    
                # 训练判别器
                if self.use_adversarial:
                    self.discriminator_optimizer.zero_grad()
                    
                    # 真实数据
                    real_features = self.model.feature_extractor(data)
                    real_outputs = self.model.imagination_layer.discriminate(real_features.detach())
                    real_labels = torch.ones_like(real_outputs)
                    real_loss = F.binary_cross_entropy(real_outputs, real_labels)
                    
                    # 生成想象数据
                    with torch.no_grad():
                        imagined_features, _, _, _ = self.model.imagination_layer(
                            real_features, use_imagination=True,
                            imagination_strength=self.imagination_strength
                        )
                    
                    # 想象数据
                    fake_outputs = self.model.imagination_layer.discriminate(imagined_features.detach())
                    fake_labels = torch.zeros_like(fake_outputs)
                    fake_loss = F.binary_cross_entropy(fake_outputs, fake_labels)
                    
                    # 判别器总损失
                    disc_loss = (real_loss + fake_loss) / 2
                    disc_loss.backward()
                    torch.nn.utils.clip_grad_norm_(self.model.imagination_layer.discriminator.parameters(), 1.0)
                    self.discriminator_optimizer.step()
                
                # 训练生成器（主模型）
                self.optimizer.zero_grad()
                
                # 随机决定是否使用想象
                use_imagination = torch.rand(1).item() < self.imagination_prob
                
                # 前向传播
                output, kl_loss, attention_weights, z, attn_weights = self.model(
                    data, 
                    use_imagination=use_imagination,
                    imagination_strength=self.imagination_strength
                )
                
                # 计算重构损失
                reconstruction_loss = F.mse_loss(output, target)
                
                # 对抗损失
                adversarial_loss = 0
                if self.use_adversarial:
                    imagined_outputs = self.model.imagination_layer.discriminate(imagined_features)
                    adversarial_loss = F.binary_cross_entropy(
                        imagined_outputs, torch.ones_like(imagined_outputs)
                    )
                
                # 多样性损失
                if attn_weights is not None:
                    # 计算注意力权重的负熵以鼓励多样性
                    entropy = -torch.sum(attn_weights * torch.log(attn_weights + 1e-10), dim=1)
                    diversity_loss = -entropy.mean()
                else:
                    diversity_loss = torch.tensor(0.0, device=data.device)
                
                # 总损失
                loss = (
                    reconstruction_loss + 
                    kl_loss * 0.01 + 
                    adversarial_loss * 0.1 +
                    diversity_loss * 0.05
                )
                
                # 反向传播
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                self.optimizer.step()
                
                # 记录损失
                total_loss += loss.item()
                total_kl_loss += kl_loss.item()
                total_rec_loss += reconstruction_loss.item()
                total_adv_loss += adversarial_loss.item() if self.use_adversarial else 0
                total_disc_loss += disc_loss.item() if self.use_adversarial else 0
                total_div_loss += diversity_loss.item()
                batch_count += 1
                
                # 每10个批次发送一次更新信号
                if batch_idx % 10 == 0:
                    stats = {
                        'epoch': epoch,
                        'batch': batch_idx,
                        'loss': loss.item(),
                        'kl_loss': kl_loss.item(),
                        'rec_loss': reconstruction_loss.item(),
                        'adv_loss': adversarial_loss.item() if self.use_adversarial else 0,
                        'disc_loss': disc_loss.item() if self.use_adversarial else 0,
                        'div_loss': diversity_loss.item(),
                        'progress': (epoch * len(self.dataloader) + batch_idx) / 
                                   (self.epochs * len(self.dataloader)) * 100,
                        'lr': self.optimizer.param_groups[0]['lr']
                    }
                    self.update_signal.emit(stats)
            
            # 每个epoch结束后发送统计信息
            if batch_count > 0:
                avg_loss = total_loss / batch_count
                stats = {
                    'epoch': epoch,
                    'avg_loss': avg_loss,
                    'avg_kl_loss': total_kl_loss / batch_count,
                    'avg_rec_loss': total_rec_loss / batch_count,
                    'avg_adv_loss': total_adv_loss / batch_count if self.use_adversarial else 0,
                    'avg_disc_loss': total_disc_loss / batch_count if self.use_adversarial else 0,
                    'avg_div_loss': total_div_loss / batch_count,
                    'progress': (epoch + 1) / self.epochs * 100,
                    'lr': self.optimizer.param_groups[0]['lr']
                }
                
                # 更新学习率
                self.scheduler.step(avg_loss)
                if self.use_adversarial:
                    self.discriminator_scheduler.step(total_disc_loss / batch_count)
                
                # 保存最佳模型
                if avg_loss < self.best_loss:
                    self.best_loss = avg_loss
                    stats['best_loss'] = True
                
                self.update_signal.emit(stats)
                self.epoch_complete_signal.emit(epoch, avg_loss)
                
                # 记录历史
                self.history['loss'].append(avg_loss)
                self.history['kl_loss'].append(total_kl_loss / batch_count)
                self.history['rec_loss'].append(total_rec_loss / batch_count)
                self.history['adv_loss'].append(total_adv_loss / batch_count if self.use_adversarial else 0)
                self.history['disc_loss'].append(total_disc_loss / batch_count if self.use_adversarial else 0)
                self.history['diversity_loss'].append(total_div_loss / batch_count)
                self.history['lr'].append(self.optimizer.param_groups[0]['lr'])
        
        self.finished_signal.emit()
    
    def pause(self):
        """暂停训练"""
        self.is_paused = True
    
    def resume(self):
        """恢复训练"""
        self.is_paused = False
    
    def stop(self):
        """停止训练"""
        self.is_running = False
    
    def get_history(self):
        """获取训练历史"""
        return self.history


class EnhancedImaginationVisualizationWidget(QWidget):
    """增强的想象可视化组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(500, 400)
        self.history = []
        self.max_history = 200
        
        # 设置布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 标题和控制栏
        control_layout = QHBoxLayout()
        title = QLabel("想象过程可视化")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        
        self.clear_btn = QPushButton("清除")
        self.clear_btn.clicked.connect(self.clear_history)
        self.export_btn = QPushButton("导出")
        self.export_btn.clicked.connect(self.export_data)
        
        control_layout.addWidget(title)
        control_layout.addStretch()
        control_layout.addWidget(self.clear_btn)
        control_layout.addWidget(self.export_btn)
        
        layout.addLayout(control_layout)
        
        # 绘图区域
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel('left', '特征值')
        self.plot_widget.setLabel('bottom', '时间步')
        self.plot_widget.addLegend()
        self.plot_widget.showGrid(x=True, y=True)
        layout.addWidget(self.plot_widget)
        
        # 初始化曲线
        self.original_curve = self.plot_widget.plot(
            [], [], 
            pen=pg.mkPen(color='b', width=2),
            name="原始特征",
            symbol='o',
            symbolSize=5,
            symbolBrush='b'
        )
        self.imagined_curve = self.plot_widget.plot(
            [], [], 
            pen=pg.mkPen(color='r', width=2),
            name="想象特征",
            symbol='x',
            symbolSize=5,
            symbolBrush='r'
        )
        self.difference_curve = self.plot_widget.plot(
            [], [], 
            pen=pg.mkPen(color='g', width=1, style=pg.QtCore.Qt.PenStyle.DashLine),
            name="差异",
            fillLevel=0,
            fillBrush=pg.mkBrush(0, 255, 0, 50)
        )
        
        # 统计信息标签
        stats_layout = QHBoxLayout()
        self.avg_diff_label = QLabel("平均差异: -")
        self.max_diff_label = QLabel("最大差异: -")
        self.min_diff_label = QLabel("最小差异: -")
        
        stats_layout.addWidget(self.avg_diff_label)
        stats_layout.addWidget(self.max_diff_label)
        stats_layout.addWidget(self.min_diff_label)
        stats_layout.addStretch()
        
        layout.addLayout(stats_layout)
    
    def clear_history(self):
        """清除历史数据"""
        self.history = []
        self.update_plot()
    
    def export_data(self):
        """导出数据到CSV"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出数据", "", "CSV Files (*.csv)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    f.write("Step,Original,Imagined,Difference\n")
                    for i, data in enumerate(self.history):
                        f.write(f"{i},{data['original']},{data['imagined']},{data['difference']}\n")
                QMessageBox.information(self, "成功", "数据已成功导出")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")
    
    def update_visualization(self, original, imagined):
        """更新可视化"""
        # 转换为numpy数组
        if torch.is_tensor(original):
            original = original.detach().cpu().numpy()
        if torch.is_tensor(imagined):
            imagined = imagined.detach().cpu().numpy()
        
        # 计算差异
        difference = np.abs(original - imagined)
        
        # 计算统计信息
        avg_diff = np.mean(difference)
        max_diff = np.max(difference)
        min_diff = np.min(difference)
        
        # 更新统计标签
        self.avg_diff_label.setText(f"平均差异: {avg_diff:.6f}")
        self.max_diff_label.setText(f"最大差异: {max_diff:.6f}")
        self.min_diff_label.setText(f"最小差异: {min_diff:.6f}")
        
        # 更新历史数据
        self.history.append({
            'original': np.mean(original),
            'imagined': np.mean(imagined),
            'difference': avg_diff
        })
        
        if len(self.history) > self.max_history:
            self.history.pop(0)
        
        self.update_plot()
    
    def update_plot(self):
        """更新绘图"""
        if not self.history:
            return
            
        # 准备绘图数据
        x = np.arange(len(self.history))
        original_data = np.array([h['original'] for h in self.history])
        imagined_data = np.array([h['imagined'] for h in self.history])
        difference_data = np.array([h['difference'] for h in self.history])
        
        # 更新曲线
        self.original_curve.setData(x, original_data)
        self.imagined_curve.setData(x, imagined_data)
        self.difference_curve.setData(x, difference_data)


class EnhancedMemoryVisualizationWidget(QWidget):
    """增强的记忆可视化组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(500, 400)
        
        # 设置布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 标题和控制栏
        control_layout = QHBoxLayout()
        title = QLabel("记忆网络可视化")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["使用频率", "记忆年龄", "记忆内容"])
        self.mode_combo.currentTextChanged.connect(self.update_visualization)
        
        control_layout.addWidget(title)
        control_layout.addStretch()
        control_layout.addWidget(QLabel("显示模式:"))
        control_layout.addWidget(self.mode_combo)
        
        layout.addLayout(control_layout)
        
        # 绘图区域
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel('left', '值')
        self.plot_widget.setLabel('bottom', '记忆索引')
        self.plot_widget.showGrid(x=True, y=True)
        layout.addWidget(self.plot_widget)
        
        # 初始化柱状图
        self.bar_graph = pg.BarGraphItem(x=[], height=[], width=0.8, brush='b')
        self.plot_widget.addItem(self.bar_graph)
        
        # 统计信息标签
        stats_layout = QHBoxLayout()
        self.total_mem_label = QLabel("总记忆数: -")
        self.used_mem_label = QLabel("使用中记忆: -")
        self.avg_usage_label = QLabel("平均使用率: -")
        
        stats_layout.addWidget(self.total_mem_label)
        stats_layout.addWidget(self.used_mem_label)
        stats_layout.addWidget(self.avg_usage_label)
        stats_layout.addStretch()
        
        layout.addLayout(stats_layout)
        
        self.current_data = None
    
    def update_visualization(self, memory_data):
        """更新记忆可视化"""
        if memory_data is None:
            return
            
        self.current_data = memory_data
        mode = self.mode_combo.currentText()
        
        # 转换为numpy数组
        weights = memory_data['weights'].cpu().numpy() if torch.is_tensor(memory_data['weights']) else memory_data['weights']
        age = memory_data['age'].cpu().numpy() if torch.is_tensor(memory_data['age']) else memory_data['age']
        memory = memory_data['memory'].cpu().numpy() if torch.is_tensor(memory_data['memory']) else memory_data['memory']
        
        # 根据模式选择数据
        if mode == "使用频率":
            data = weights
            y_label = "使用频率"
        elif mode == "记忆年龄":
            data = age
            y_label = "年龄"
        else:  # 记忆内容
            # 使用记忆内容的范数作为指标
            data = np.linalg.norm(memory, axis=1)
            y_label = "记忆范数"
        
        # 更新统计信息
        total_mem = len(weights)
        used_mem = np.sum(weights > 0.1)  # 使用阈值判断是否在使用
        avg_usage = np.mean(weights) if len(weights) > 0 else 0
        
        self.total_mem_label.setText(f"总记忆数: {total_mem}")
        self.used_mem_label.setText(f"使用中记忆: {used_mem}")
        self.avg_usage_label.setText(f"平均使用率: {avg_usage:.3f}")
        
        # 创建x轴数据
        x = np.arange(len(data))
        
        # 更新柱状图
        self.bar_graph.setOpts(x=x, height=data)
        self.plot_widget.setLabel('left', y_label)


class MultiScaleImaginationLayer(nn.Module):
    """
    多尺度想象层 - 支持多种想象模式、记忆网络和对抗训练
    """
    
    def __init__(self, input_dim, latent_dim=128, num_heads=6, 
                 memory_size=256, imagination_strength=0.1,
                 use_adversarial=True, use_memory=True):
        super(MultiScaleImaginationLayer, self).__init__()
        
        self.input_dim = input_dim
        self.latent_dim = latent_dim
        self.num_heads = num_heads
        self.memory_size = memory_size
        self.imagination_strength = imagination_strength
        self.use_adversarial = use_adversarial
        self.use_memory = use_memory
        
        # 编码器网络
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.LeakyReLU(0.1),
            nn.LayerNorm(256),
            nn.Linear(256, 192),
            nn.LeakyReLU(0.1),
            nn.LayerNorm(192),
            nn.Linear(192, 128),
            nn.LeakyReLU(0.1),
        )
        
        # 多头潜在空间映射
        self.head_mu_layers = nn.ModuleList([
            nn.Sequential(
                nn.Linear(128, 96),
                nn.LeakyReLU(0.1),
                nn.Linear(96, latent_dim)
            ) for _ in range(num_heads)
        ])
        
        self.head_logvar_layers = nn.ModuleList([
            nn.Sequential(
                nn.Linear(128, 96),
                nn.LeakyReLU(0.1),
                nn.Linear(96, latent_dim)
            ) for _ in range(num_heads)
        ])
        
        # 多头解码器
        self.head_decoders = nn.ModuleList([
            nn.Sequential(
                nn.Linear(latent_dim, 96),
                nn.LeakyReLU(0.1),
                nn.Linear(96, 128),
            ) for _ in range(num_heads)
        ])
        
        # 共享解码器尾部
        self.decoder_tail = nn.Sequential(
            nn.LeakyReLU(0.1),
            nn.Linear(128, 192),
            nn.LeakyReLU(0.1),
            nn.Linear(192, input_dim)
        )
        
        # 多头注意力机制
        self.attention_heads = nn.ModuleList([
            nn.MultiheadAttention(latent_dim, num_heads=4, batch_first=True)
            for _ in range(num_heads)
        ])
        
        # 记忆网络
        if use_memory:
            self.memory = nn.Parameter(torch.randn(memory_size, latent_dim))
            self.memory_weights = nn.Parameter(torch.ones(memory_size))
            self.memory_age = nn.Parameter(torch.zeros(memory_size), requires_grad=False)
            self.memory_updater = nn.GRUCell(latent_dim, latent_dim)
        
        # 对抗判别器
        if use_adversarial:
            self.discriminator = nn.Sequential(
                nn.Linear(input_dim, 256),
                nn.LeakyReLU(0.2),
                nn.LayerNorm(256),
                nn.Linear(256, 128),
                nn.LeakyReLU(0.2),
                nn.LayerNorm(128),
                nn.Linear(128, 64),
                nn.LeakyReLU(0.2),
                nn.Linear(64, 1),
                nn.Sigmoid()
            )
        
        # 先验分布参数 - 可学习的
        self.prior_mu = nn.Parameter(torch.zeros(latent_dim))
        self.prior_logvar = nn.Parameter(torch.zeros(latent_dim))
        
        # 尺度参数 - 控制不同头的想象强度
        self.scale_factors = nn.Parameter(torch.linspace(0.3, 3.0, num_heads))
        
        # 想象历史记录
        self.imagination_history = deque(maxlen=1000)
        
        # 初始化参数
        self._init_weights()
        
    def _init_weights(self):
        """初始化网络权重"""
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_normal_(m.weight)
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0.1)
    
    def encode(self, x):
        """将输入编码到共享特征空间"""
        return self.encoder(x)
    
    def head_encode(self, h, head_idx):
        """使用指定头编码到潜在空间"""
        mu = self.head_mu_layers[head_idx](h)
        logvar = self.head_logvar_layers[head_idx](h)
        return mu, logvar
    
    def reparameterize(self, mu, logvar):
        """重参数化技巧"""
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std
    
    def decode(self, z, head_idx):
        """使用指定头解码"""
        head_output = self.head_decoders[head_idx](z)
        return self.decoder_tail(head_output)
    
    def attend_to_memory(self, z, head_idx):
        """注意力机制与记忆交互"""
        if not self.use_memory:
            return z, None
            
        batch_size = z.size(0)
        
        # 扩展记忆以匹配批次大小
        memory_expanded = self.memory.unsqueeze(0).expand(batch_size, -1, -1)
        z_expanded = z.unsqueeze(1)
        
        # 应用注意力
        attended_z, attention_weights = self.attention_heads[head_idx](
            z_expanded, memory_expanded, memory_expanded
        )
        attended_z = attended_z.squeeze(1)
        
        return attended_z, attention_weights
    
    def update_memory(self, z, head_idx):
        """更新记忆"""
        if not self.use_memory:
            return
            
        batch_size = z.size(0)
        
        # 计算与记忆中每个条目的相似度
        similarities = torch.matmul(z, self.memory.t()) / math.sqrt(self.latent_dim)
        
        # 选择最相似的记忆条目进行更新
        _, topk_indices = torch.topk(similarities, k=min(5, self.memory_size), dim=1)
        
        # 更新选中的记忆条目
        for i in range(batch_size):
            for idx in topk_indices[i]:
                # 使用GRU更新记忆
                new_memory = self.memory_updater(
                    z[i].unsqueeze(0), 
                    self.memory[idx].unsqueeze(0)
                ).squeeze(0)
                
                # 保留部分旧记忆，增加稳定性
                self.memory.data[idx] = 0.8 * new_memory + 0.2 * self.memory.data[idx]
                
        # 更新记忆权重和年龄
        memory_usage = torch.zeros(self.memory_size, device=z.device)
        memory_usage.scatter_add_(0, topk_indices.flatten(), 
                                 torch.ones_like(topk_indices.flatten(), dtype=torch.float))
        self.memory_weights.data = 0.9 * self.memory_weights + 0.1 * memory_usage
        self.memory_age.data[topk_indices.flatten()] = 0  # 重置年龄
    
    def age_memory(self):
        """增加记忆年龄"""
        if not self.use_memory:
            return
        self.memory_age.data += 1
    
    def replace_old_memory(self, z, head_idx):
        """替换最旧的记忆"""
        if not self.use_memory:
            return
            
        # 找到最老的记忆位置
        oldest_idx = torch.argmax(self.memory_age).item()
        
        # 使用当前潜在表示替换
        if z.size(0) > 0:
            sample_idx = random.randint(0, z.size(0)-1)
            self.memory.data[oldest_idx] = z[sample_idx].detach()
            self.memory_age.data[oldest_idx] = 0
            self.memory_weights.data[oldest_idx] = 1.0
    
    def imagine(self, mu, logvar, head_idx, strength=None, use_attention=True):
        """
        增强版想象过程
        
        参数:
            mu: 潜在空间均值
            logvar: 潜在空间对数方差
            head_idx: 使用的头索引
            strength: 想象强度
            use_attention: 是否使用注意力机制
        """
        if strength is None:
            strength = self.imagination_strength
            
        # 从编码分布采样
        z = self.reparameterize(mu, logvar)
        
        # 应用注意力机制
        attention_weights = None
        if use_attention and self.use_memory:
            z, attention_weights = self.attend_to_memory(z, head_idx)
        
        # 添加尺度特定的噪声
        scale_factor = self.scale_factors[head_idx]
        imagination_noise = torch.randn_like(z) * strength * scale_factor
        
        # 应用非线性变换增强想象
        noise_transform = torch.sigmoid(imagination_noise) - 0.5
        z_imagined = z + noise_transform
        
        # 解码想象的特征
        x_imagined = self.decode(z_imagined, head_idx)
        
        # 记录想象历史
        self.imagination_history.append({
            'head_idx': head_idx,
            'strength': strength,
            'scale_factor': scale_factor.item(),
            'original_z': z.detach().cpu(),
            'imagined_z': z_imagined.detach().cpu(),
            'attention_weights': attention_weights.detach().cpu() if attention_weights is not None else None
        })
        
        return x_imagined, z, attention_weights
    
    def forward(self, x, use_imagination=True, imagination_strength=None, 
                head_idx=None, use_attention=True, update_memory=True):
        """
        前向传播
        
        参数:
            x: 输入特征
            use_imagination: 是否使用想象过程
            imagination_strength: 想象强度
            head_idx: 指定使用的头(None表示使用所有头)
            use_attention: 是否使用注意力机制
            update_memory: 是否更新记忆
        """
        batch_size = x.size(0)
        
        # 共享编码
        h = self.encode(x)
        
        if head_idx is None:
            # 使用所有头
            outputs = []
            kl_losses = []
            zs = []
            attention_weights_list = []
            
            for i in range(self.num_heads):
                mu, logvar = self.head_encode(h, i)
                
                if use_imagination:
                    output, z, attention_weights = self.imagine(
                        mu, logvar, i, imagination_strength, use_attention
                    )
                else:
                    z = self.reparameterize(mu, logvar)
                    output = self.decode(z, i)
                    attention_weights = None
                
                # 计算KL散度损失
                prior_dist = Normal(self.prior_mu, torch.exp(0.5 * self.prior_logvar))
                posterior_dist = Normal(mu, torch.exp(0.5 * logvar))
                kl_loss = kl_divergence(posterior_dist, prior_dist).mean()
                
                outputs.append(output)
                kl_losses.append(kl_loss)
                zs.append(z)
                attention_weights_list.append(attention_weights)
            
            # 合并所有头的输出
            output = torch.stack(outputs).mean(dim=0)
            kl_loss = torch.stack(kl_losses).mean()
            z = torch.stack(zs).mean(dim=0)
            attention_weights = torch.stack(attention_weights_list).mean(dim=0) if all(aw is not None for aw in attention_weights_list) else None
            
        else:
            # 使用指定头
            mu, logvar = self.head_encode(h, head_idx)
            
            if use_imagination:
                output, z, attention_weights = self.imagine(
                    mu, logvar, head_idx, imagination_strength, use_attention
                )
            else:
                z = self.reparameterize(mu, logvar)
                output = self.decode(z, head_idx)
                attention_weights = None
            
            # 计算KL散度损失
            prior_dist = Normal(self.prior_mu, torch.exp(0.5 * self.prior_logvar))
            posterior_dist = Normal(mu, torch.exp(0.5 * logvar))
            kl_loss = kl_divergence(posterior_dist, prior_dist).mean()
        
        # 更新记忆
        if update_memory and self.use_memory:
            self.update_memory(z, head_idx if head_idx is not None else 0)
            self.age_memory()
            
            # 定期替换旧记忆
            if random.random() < 0.05:  # 5%的概率替换旧记忆
                self.replace_old_memory(z, head_idx if head_idx is not None else 0)
        
        return output, kl_loss, z, attention_weights
    
    def generate(self, num_samples, head_idx=0, device='cpu'):
        """从先验分布生成样本"""
        z = torch.randn(num_samples, self.latent_dim).to(device)
        z = z * torch.exp(0.5 * self.prior_logvar) + self.prior_mu
        return self.decode(z, head_idx)
    
    def discriminate(self, x):
        """判别输入是真实数据还是想象数据"""
        if not self.use_adversarial:
            return torch.ones(x.size(0), 1, device=x.device) * 0.5  # 中性输出
        
        return self.discriminator(x)
    
    def get_memory_usage(self):
        """获取记忆使用情况"""
        if not self.use_memory:
            return None
            
        return {
            'weights': self.memory_weights.detach(),
            'age': self.memory_age.detach(),
            'memory': self.memory.detach()
        }
    
    def get_imagination_history(self, n=10):
        """获取最近的想象历史"""
        if len(self.imagination_history) == 0:
            return []
        
        return list(self.imagination_history)[-n:]
    
    def get_attention_weights(self, z, head_idx=0):
        """获取注意力权重"""
        if not self.use_memory:
            return None
            
        batch_size = z.size(0)
        memory_expanded = self.memory.unsqueeze(0).expand(batch_size, -1, -1)
        z_expanded = z.unsqueeze(1)
        
        _, attention_weights = self.attention_heads[head_idx](
            z_expanded, memory_expanded, memory_expanded, 
            need_weights=True
        )
        
        return attention_weights.squeeze(1)


class AdvancedImaginativeNetwork(nn.Module):
    """带有增强想象层的神经网络"""
    
    def __init__(self, input_dim, output_dim, num_imagination_heads=6,
                 use_adversarial=True, use_memory=True):
        super(AdvancedImaginativeNetwork, self).__init__()
        
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.num_imagination_heads = num_imagination_heads
        
        # 特征提取器
        self.feature_extractor = nn.Sequential(
            nn.Linear(input_dim, 512),
            nn.LeakyReLU(0.1),
            nn.LayerNorm(512),
            nn.Linear(512, 256),
            nn.LeakyReLU(0.1),
            nn.LayerNorm(256),
            nn.Linear(256, 128),
            nn.LeakyReLU(0.1),
        )
        
        # 增强想象层
        self.imagination_layer = MultiScaleImaginationLayer(
            128, latent_dim=64, num_heads=num_imagination_heads,
            use_adversarial=use_adversarial, use_memory=use_memory
        )
        
        # 想象特征处理器 - 每个头有不同的处理器
        self.imagination_processors = nn.ModuleList([
            nn.Sequential(
                nn.Linear(128, 96),
                nn.LeakyReLU(0.1),
                nn.LayerNorm(96),
                nn.Linear(96, 128),
                nn.LeakyReLU(0.1),
            ) for _ in range(num_imagination_heads)
        ])
        
        # 特征融合层
        input_dim_fusion = 128 + 128 * num_imagination_heads  # 原始特征 + 所有头的想象特征

        self.feature_fusion = nn.Sequential(
            nn.Linear(input_dim_fusion, 256),
            nn.LeakyReLU(0.1),
            nn.LayerNorm(256),
            nn.Linear(256, 128),
            nn.LeakyReLU(0.1),
        )
        
        # 输出层
        self.output_layer = nn.Sequential(
            nn.Linear(128, 64),
            nn.LeakyReLU(0.1),
            nn.Linear(64, output_dim)
        )
        
        # 想象控制器 - LSTM基于输入特征决定使用哪些想象头
        self.imagination_controller = nn.LSTM(128, 64, batch_first=True, num_layers=2)
        self.controller_output = nn.Linear(64, num_imagination_heads)
        
        # 初始化参数
        self._init_weights()
        
    def _init_weights(self):
        """初始化网络权重"""
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_normal_(m.weight)
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0.1)
    
    def forward(self, x, use_imagination=True, imagination_strength=0.1, 
                use_attention=True, update_memory=True, head_idx=None):
        # 获取批次大小
        batch_size = x.size(0)
        
        # 提取特征
        features = self.feature_extractor(x)
        
        # 使用想象层
        imagined_features, kl_loss, z, attention_weights = self.imagination_layer(
            features, 
            use_imagination=use_imagination,
            imagination_strength=imagination_strength,
            use_attention=use_attention,
            update_memory=update_memory,
            head_idx=head_idx
        )
        
        # 处理想象特征
        processed_imaginations = []
        for i, processor in enumerate(self.imagination_processors):
            # 使用不同的处理器处理想象特征
            processed = processor(imagined_features)
            processed_imaginations.append(processed)
        
        # 决定使用哪些想象特征
        controller_input = features.unsqueeze(1)
        controller_output, _ = self.imagination_controller(controller_input)
        attention_weights_controller = F.softmax(
            self.controller_output(controller_output.squeeze(1)), dim=1
        )
        
        # 加权合并想象特征
        weighted_imagination = torch.zeros_like(features)
        for i in range(len(processed_imaginations)):
            weight = attention_weights_controller[:, i].unsqueeze(1)
            weighted_imagination += weight * processed_imaginations[i]
        
        # 融合原始特征和想象特征
        processed_imaginations_tensor = torch.stack(processed_imaginations, dim=1)  # [batch, num_heads, 128]
        processed_imaginations_flat = processed_imaginations_tensor.view(batch_size, -1)  # [batch, num_heads * 128]
        combined = torch.cat([features, processed_imaginations_flat], dim=1)  # [batch, 128 + num_heads * 128]
        fused = self.feature_fusion(combined)
        
        # 最终输出
        output = self.output_layer(fused)
        
        return output, kl_loss, attention_weights_controller, z, attention_weights
    
    def get_imagination_stats(self):
        """获取想象统计信息"""
        return self.imagination_layer.get_imagination_history()
    
    def get_memory_stats(self):
        """获取记忆统计信息"""
        return self.imagination_layer.get_memory_usage()


class CustomDataset(Dataset):
    """自定义数据集类，支持从文件加载数据"""
    
    def __init__(self, data, targets):
        self.data = data
        self.targets = targets
        
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        return self.data[idx], self.targets[idx]
    
    @classmethod
    def from_numpy(cls, data_path, target_path):
        """从numpy文件加载数据"""
        data = np.load(data_path)
        targets = np.load(target_path)
        return cls(torch.FloatTensor(data), torch.FloatTensor(targets))
    
    @classmethod
    def from_csv(cls, data_path, target_path=None):
        """从CSV文件加载数据"""
        data = np.genfromtxt(data_path, delimiter=',')
        if target_path:
            targets = np.genfromtxt(target_path, delimiter=',')
        else:
            # 如果没有提供目标文件，则使用数据自身作为目标（自编码器）
            targets = data.copy()
        return cls(torch.FloatTensor(data), torch.FloatTensor(targets))


class EnhancedImaginationLayerGUI(QMainWindow):
    """增强的想象层图形界面"""
    
    def __init__(self):
        super().__init__()
        self.model = None
        self.training_thread = None
        self.dataset = None
        self.current_model_path = None
        self.current_data_path = None
        
        self.initUI()
        self.initModel()
        
    def initUI(self):
        """初始化用户界面"""
        self.setWindowTitle("神经网络想象层可视化工具 - PyQt6")
        self.setGeometry(100, 100, 1400, 900)
        
        # 创建菜单栏
        self.createMenuBar()
        
        # 创建工具栏
        self.createToolBar()
        
        # 创建状态栏
        self.statusBar().showMessage("就绪")
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # 左侧控制面板
        control_panel = QWidget()
        control_panel.setMaximumWidth(350)
        control_layout = QVBoxLayout(control_panel)
        control_layout.setContentsMargins(5, 5, 5, 5)
        
        # 模型控制组
        model_group = QGroupBox("模型控制")
        model_layout = QVBoxLayout(model_group)
        
        # 模型操作按钮
        model_btn_layout = QHBoxLayout()
        self.train_button = QPushButton("开始训练")
        self.train_button.clicked.connect(self.start_training)
        model_btn_layout.addWidget(self.train_button)
        
        self.pause_button = QPushButton("暂停")
        self.pause_button.clicked.connect(self.pause_training)
        self.pause_button.setEnabled(False)
        model_btn_layout.addWidget(self.pause_button)
        
        self.stop_button = QPushButton("停止")
        self.stop_button.clicked.connect(self.stop_training)
        self.stop_button.setEnabled(False)
        model_btn_layout.addWidget(self.stop_button)
        
        model_layout.addLayout(model_btn_layout)
        
        # 训练参数
        params_form = QFormLayout()
        
        self.epochs_spin = QSpinBox()
        self.epochs_spin.setRange(1, 10000)
        self.epochs_spin.setValue(50)
        params_form.addRow("训练轮数:", self.epochs_spin)
        
        self.batch_size_spin = QSpinBox()
        self.batch_size_spin.setRange(1, 1024)
        self.batch_size_spin.setValue(32)
        params_form.addRow("批大小:", self.batch_size_spin)
        
        self.lr_spin = QDoubleSpinBox()
        self.lr_spin.setRange(0.00001, 1.0)
        self.lr_spin.setValue(0.001)
        self.lr_spin.setDecimals(5)
        params_form.addRow("学习率:", self.lr_spin)
        
        self.wd_spin = QDoubleSpinBox()
        self.wd_spin.setRange(0.0, 0.1)
        self.wd_spin.setValue(0.0001)
        self.wd_spin.setDecimals(6)
        params_form.addRow("权重衰减:", self.wd_spin)
        
        model_layout.addLayout(params_form)
        
        # 想象参数
        imagination_form = QFormLayout()
        
        self.imagination_prob_slider = QSlider(Qt.Orientation.Horizontal)
        self.imagination_prob_slider.setRange(0, 100)
        self.imagination_prob_slider.setValue(70)
        imagination_form.addRow("想象概率:", self.imagination_prob_slider)
        
        self.imagination_strength_slider = QSlider(Qt.Orientation.Horizontal)
        self.imagination_strength_slider.setRange(0, 100)
        self.imagination_strength_slider.setValue(10)
        imagination_form.addRow("想象强度:", self.imagination_strength_slider)
        
        model_layout.addLayout(imagination_form)
        
        # 功能开关
        self.use_adversarial_cb = QCheckBox("使用对抗训练")
        self.use_adversarial_cb.setChecked(True)
        model_layout.addWidget(self.use_adversarial_cb)
        
        self.use_memory_cb = QCheckBox("使用记忆网络")
        self.use_memory_cb.setChecked(True)
        model_layout.addWidget(self.use_memory_cb)
        
        control_layout.addWidget(model_group)
        
        # 想象控制组
        imagination_group = QGroupBox("想象控制")
        imagination_layout = QVBoxLayout(imagination_group)
        
        head_idx_label = QLabel("选择想象头:")
        imagination_layout.addWidget(head_idx_label)
        self.head_idx_combo = QComboBox()
        for i in range(6):  # 假设有6个头
            self.head_idx_combo.addItem(f"头 {i}")
        imagination_layout.addWidget(self.head_idx_combo)
        
        self.generate_button = QPushButton("生成样本")
        self.generate_button.clicked.connect(self.generate_samples)
        imagination_layout.addWidget(self.generate_button)
        
        self.visualize_button = QPushButton("可视化想象")
        self.visualize_button.clicked.connect(self.visualize_imagination)
        imagination_layout.addWidget(self.visualize_button)
        
        control_layout.addWidget(imagination_group)
        
        # 状态信息组
        status_group = QGroupBox("训练状态")
        status_layout = QVBoxLayout(status_group)
        
        self.epoch_label = QLabel("轮数: 0/0")
        status_layout.addWidget(self.epoch_label)
        
        self.loss_label = QLabel("损失: -")
        status_layout.addWidget(self.loss_label)
        
        self.kl_loss_label = QLabel("KL损失: -")
        status_layout.addWidget(self.kl_loss_label)
        
        self.rec_loss_label = QLabel("重构损失: -")
        status_layout.addWidget(self.rec_loss_label)
        
        self.adv_loss_label = QLabel("对抗损失: -")
        status_layout.addWidget(self.adv_loss_label)
        
        self.disc_loss_label = QLabel("判别损失: -")
        status_layout.addWidget(self.disc_loss_label)
        
        self.div_loss_label = QLabel("多样性损失: -")
        status_layout.addWidget(self.div_loss_label)
        
        self.lr_label = QLabel("学习率: -")
        status_layout.addWidget(self.lr_label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        status_layout.addWidget(self.progress_bar)
        
        control_layout.addWidget(status_group)
        
        # 添加到主布局
        main_layout.addWidget(control_panel)
        
        # 右侧可视化区域
        visualization_tabs = QTabWidget()
        
        # 损失曲线标签
        loss_tab = QWidget()
        loss_layout = QVBoxLayout(loss_tab)
        
        # 损失曲线控制栏
        loss_control_layout = QHBoxLayout()
        self.loss_clear_btn = QPushButton("清除")
        self.loss_clear_btn.clicked.connect(self.clear_loss_plot)
        self.loss_export_btn = QPushButton("导出")
        self.loss_export_btn.clicked.connect(self.export_loss_data)
        
        loss_control_layout.addWidget(QLabel("训练曲线"))
        loss_control_layout.addStretch()
        loss_control_layout.addWidget(self.loss_clear_btn)
        loss_control_layout.addWidget(self.loss_export_btn)
        loss_layout.addLayout(loss_control_layout)
        
        self.loss_plot = pg.PlotWidget()
        self.loss_plot.setLabel('left', '损失值')
        self.loss_plot.setLabel('bottom', '迭代次数')
        self.loss_plot.addLegend()
        self.loss_plot.showGrid(x=True, y=True)
        loss_layout.addWidget(self.loss_plot)
        
        # 初始化损失曲线
        self.loss_curve = self.loss_plot.plot([], [], pen='r', name='总损失')
        self.kl_loss_curve = self.loss_plot.plot([], [], pen='b', name='KL损失')
        self.rec_loss_curve = self.loss_plot.plot([], [], pen='y', name='重构损失')
        self.adv_loss_curve = self.loss_plot.plot([], [], pen='g', name='对抗损失')
        self.div_loss_curve = self.loss_plot.plot([], [], pen='m', name='多样性损失')
        
        visualization_tabs.addTab(loss_tab, "训练损失")
        
        # 想象可视化标签
        imagination_tab = QWidget()
        imagination_tab_layout = QVBoxLayout(imagination_tab)
        self.imagination_viz = EnhancedImaginationVisualizationWidget()
        imagination_tab_layout.addWidget(self.imagination_viz)
        visualization_tabs.addTab(imagination_tab, "想象过程")
        
        # 记忆可视化标签
        memory_tab = QWidget()
        memory_tab_layout = QVBoxLayout(memory_tab)
        self.memory_viz = EnhancedMemoryVisualizationWidget()
        memory_tab_layout.addWidget(self.memory_viz)
        visualization_tabs.addTab(memory_tab, "记忆网络")
        
        # 想象历史标签
        history_tab = QWidget()
        history_layout = QVBoxLayout(history_tab)
        
        # 历史控制栏
        history_control_layout = QHBoxLayout()
        self.history_clear_btn = QPushButton("清除")
        self.history_clear_btn.clicked.connect(self.clear_history_table)
        self.history_export_btn = QPushButton("导出")
        self.history_export_btn.clicked.connect(self.export_history_data)
        
        history_control_layout.addWidget(QLabel("想象历史记录"))
        history_control_layout.addStretch()
        history_control_layout.addWidget(self.history_clear_btn)
        history_control_layout.addWidget(self.history_export_btn)
        history_layout.addLayout(history_control_layout)
        
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels(["时间", "头索引", "强度", "尺度", "差异"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        history_layout.addWidget(self.history_table)
        visualization_tabs.addTab(history_tab, "想象历史")
        
        # 样本生成标签
        generation_tab = QWidget()
        generation_layout = QVBoxLayout(generation_tab)
        
        generation_control_layout = QHBoxLayout()
        self.num_samples_spin = QSpinBox()
        self.num_samples_spin.setRange(1, 100)
        self.num_samples_spin.setValue(5)
        generation_control_layout.addWidget(QLabel("样本数量:"))
        generation_control_layout.addWidget(self.num_samples_spin)
        generation_control_layout.addStretch()
        
        self.generate_samples_btn = QPushButton("生成样本")
        self.generate_samples_btn.clicked.connect(self.generate_and_visualize_samples)
        generation_control_layout.addWidget(self.generate_samples_btn)
        
        generation_layout.addLayout(generation_control_layout)
        
        self.samples_text = QTextEdit()
        self.samples_text.setReadOnly(True)
        generation_layout.addWidget(self.samples_text)
        
        visualization_tabs.addTab(generation_tab, "样本生成")
        
        main_layout.addWidget(visualization_tabs)
        
        # 初始化数据
        self.loss_data = {'total': [], 'kl': [], 'rec': [], 'adv': [], 'div': []}
        self.iteration = 0
        self.training_start_time = None
        
        # 应用样式
        self.applyStyle()
        
    def createMenuBar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        new_action = QAction("新建", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self.newModel)
        file_menu.addAction(new_action)
        
        load_model_action = QAction("加载模型", self)
        load_model_action.setShortcut(QKeySequence.StandardKey.Open)
        load_model_action.triggered.connect(self.loadModel)
        file_menu.addAction(load_model_action)
        
        save_model_action = QAction("保存模型", self)
        save_model_action.setShortcut(QKeySequence.StandardKey.Save)
        save_model_action.triggered.connect(self.saveModel)
        file_menu.addAction(save_model_action)
        
        file_menu.addSeparator()
        
        load_data_action = QAction("加载数据", self)
        load_data_action.triggered.connect(self.loadData)
        file_menu.addAction(load_data_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 视图菜单
        view_menu = menubar.addMenu("视图")
        
        reset_view_action = QAction("重置视图", self)
        reset_view_action.triggered.connect(self.resetViews)
        view_menu.addAction(reset_view_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.showAbout)
        help_menu.addAction(about_action)
    
    def createToolBar(self):
        """创建工具栏"""
        toolbar = QToolBar("主工具栏")
        toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(toolbar)
        
        # 添加工具栏动作
        train_action = QAction("开始训练", self)
        train_action.triggered.connect(self.start_training)
        toolbar.addAction(train_action)
        
        stop_action = QAction("停止训练", self)
        stop_action.triggered.connect(self.stop_training)
        toolbar.addAction(stop_action)
        
        toolbar.addSeparator()
        
        generate_action = QAction("生成样本", self)
        generate_action.triggered.connect(self.generate_samples)
        toolbar.addAction(generate_action)
        
        visualize_action = QAction("可视化", self)
        visualize_action.triggered.connect(self.visualize_imagination)
        toolbar.addAction(visualize_action)
    
    def applyStyle(self):
        """应用样式表"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #cccccc;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #e0e0e0;
                border: 1px solid #aaaaaa;
                border-radius: 3px;
                padding: 5px;
                min-width: 70px;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
            QPushButton:pressed {
                background-color: #c0c0c0;
            }
            QPushButton:disabled {
                background-color: #eeeeee;
                color: #888888;
            }
            QTabWidget::pane {
                border: 1px solid #cccccc;
                background: white;
            }
            QTabBar::tab {
                background: #e0e0e0;
                border: 1px solid #cccccc;
                padding: 5px 10px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: white;
                border-bottom-color: white;
            }
            QProgressBar {
                border: 1px solid #cccccc;
                border-radius: 3px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #5c9ce6;
                width: 10px;
            }
        """)
    
    def initModel(self):
        """初始化模型"""
        input_dim = 100
        output_dim = 10
        
        # 创建模型
        self.model = AdvancedImaginativeNetwork(
            input_dim, output_dim, 
            use_adversarial=self.use_adversarial_cb.isChecked(),
            use_memory=self.use_memory_cb.isChecked()
        )
        
        # 创建示例数据集
        data = torch.randn(1000, input_dim)
        target = torch.randn(1000, output_dim)
        self.dataset = TensorDataset(data, target)
        
        self.statusBar().showMessage("模型已初始化")
    
    def newModel(self):
        """创建新模型"""
        reply = QMessageBox.question(self, "确认", "创建新模型将丢失当前未保存的更改。是否继续?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.initModel()
            self.current_model_path = None
            self.statusBar().showMessage("已创建新模型")
    
    def loadModel(self):
        """加载模型"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "加载模型", "", "PyTorch模型文件 (*.pth);;所有文件 (*)"
        )
        
        if file_path:
            try:
                # 停止当前训练
                if self.training_thread and self.training_thread.isRunning():
                    self.training_thread.stop()
                    self.training_thread.wait()
                
                # 加载模型
                checkpoint = torch.load(file_path)
                self.model.load_state_dict(checkpoint['model_state_dict'])
                
                # 恢复训练参数
                if 'training_params' in checkpoint:
                    params = checkpoint['training_params']
                    self.epochs_spin.setValue(params.get('epochs', 50))
                    self.lr_spin.setValue(params.get('learning_rate', 0.001))
                    self.wd_spin.setValue(params.get('weight_decay', 0.0001))
                    self.imagination_prob_slider.setValue(int(params.get('imagination_prob', 0.7) * 100))
                    self.imagination_strength_slider.setValue(int(params.get('imagination_strength', 0.1) * 100))
                    self.use_adversarial_cb.setChecked(params.get('use_adversarial', True))
                    self.use_memory_cb.setChecked(params.get('use_memory', True))
                
                self.current_model_path = file_path
                self.statusBar().showMessage(f"模型已加载: {file_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载模型失败: {str(e)}")
    
    def saveModel(self):
        """保存模型"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存模型", "", "PyTorch模型文件 (*.pth);;所有文件 (*)"
        )
        
        if file_path:
            try:
                # 准备训练参数
                training_params = {
                    'epochs': self.epochs_spin.value(),
                    'learning_rate': self.lr_spin.value(),
                    'weight_decay': self.wd_spin.value(),
                    'imagination_prob': self.imagination_prob_slider.value() / 100.0,
                    'imagination_strength': self.imagination_strength_slider.value() / 100.0,
                    'use_adversarial': self.use_adversarial_cb.isChecked(),
                    'use_memory': self.use_memory_cb.isChecked()
                }
                
                # 保存模型
                torch.save({
                    'model_state_dict': self.model.state_dict(),
                    'training_params': training_params
                }, file_path)
                
                self.current_model_path = file_path
                self.statusBar().showMessage(f"模型已保存: {file_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存模型失败: {str(e)}")
    
    def loadData(self):
        """加载数据"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "加载数据", "", "数据文件 (*.npy *.csv);;所有文件 (*)"
        )
        
        if file_path:
            try:
                ext = os.path.splitext(file_path)[1].lower()
                
                if ext == '.npy':
                    # 假设目标文件与数据文件同名但后缀为_target.npy
                    target_path = file_path.replace('.npy', '_target.npy')
                    if os.path.exists(target_path):
                        self.dataset = CustomDataset.from_numpy(file_path, target_path)
                    else:
                        # 如果没有目标文件，创建自编码器数据
                        data = np.load(file_path)
                        self.dataset = CustomDataset(torch.FloatTensor(data), torch.FloatTensor(data))
                
                elif ext == '.csv':
                    # 假设目标文件与数据文件同名但后缀为_target.csv
                    target_path = file_path.replace('.csv', '_target.csv')
                    if os.path.exists(target_path):
                        self.dataset = CustomDataset.from_csv(file_path, target_path)
                    else:
                        # 如果没有目标文件，创建自编码器数据
                        self.dataset = CustomDataset.from_csv(file_path)
                
                self.current_data_path = file_path
                self.statusBar().showMessage(f"数据已加载: {file_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载数据失败: {str(e)}")
    
    def start_training(self):
        """开始训练"""
        if self.training_thread and self.training_thread.isRunning():
            return
            
        # 更新模型设置
        use_adversarial = self.use_adversarial_cb.isChecked()
        use_memory = self.use_memory_cb.isChecked()
        
        if (use_adversarial != self.model.imagination_layer.use_adversarial or
            use_memory != self.model.imagination_layer.use_memory):
            # 重新初始化模型
            self.initModel()
        
        # 创建数据加载器
        batch_size = self.batch_size_spin.value()
        dataloader = DataLoader(self.dataset, batch_size=batch_size, shuffle=True)
        
        # 获取训练参数
        epochs = self.epochs_spin.value()
        imagination_prob = self.imagination_prob_slider.value() / 100.0
        imagination_strength = self.imagination_strength_slider.value() / 100.0
        learning_rate = self.lr_spin.value()
        weight_decay = self.wd_spin.value()
        
        # 创建训练线程
        self.training_thread = EnhancedTrainingThread(
            self.model, dataloader, epochs, imagination_prob,
            imagination_strength, use_adversarial, use_memory,
            learning_rate, weight_decay
        )
        
        # 连接信号
        self.training_thread.update_signal.connect(self.update_training_status)
        self.training_thread.finished_signal.connect(self.training_finished)
        self.training_thread.epoch_complete_signal.connect(self.epoch_complete)
        
        # 更新按钮状态
        self.train_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        
        # 重置训练状态
        self.loss_data = {'total': [], 'kl': [], 'rec': [], 'adv': [], 'div': []}
        self.iteration = 0
        self.training_start_time = time.time()
        
        # 开始训练
        self.training_thread.start()
        self.statusBar().showMessage("训练已开始")
        
    def pause_training(self):
        """暂停/恢复训练"""
        if self.training_thread and self.training_thread.isRunning():
            if not self.training_thread.is_paused:
                self.training_thread.pause()
                self.pause_button.setText("恢复")
                self.statusBar().showMessage("训练已暂停")
            else:
                self.training_thread.resume()
                self.pause_button.setText("暂停")
                self.statusBar().showMessage("训练已恢复")
        
    def stop_training(self):
        """停止训练"""
        if self.training_thread and self.training_thread.isRunning():
            self.training_thread.stop()
            self.training_thread.wait()
            
        self.train_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.pause_button.setText("暂停")
        self.stop_button.setEnabled(False)
        self.statusBar().showMessage("训练已停止")
        
    def training_finished(self):
        """训练完成"""
        self.train_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.pause_button.setText("暂停")
        self.stop_button.setEnabled(False)
        
        # 显示训练时间
        training_time = time.time() - self.training_start_time
        self.statusBar().showMessage(f"训练完成，耗时: {training_time:.2f}秒")
        
    def epoch_complete(self, epoch, loss):
        """一个训练轮次完成"""
        self.statusBar().showMessage(f"轮次 {epoch+1} 完成，损失: {loss:.6f}")
        
    def update_training_status(self, stats):
        """更新训练状态"""
        # 更新标签
        self.epoch_label.setText(f"轮数: {stats.get('epoch', 0)+1}/{self.epochs_spin.value()}")
        self.loss_label.setText(f"损失: {stats.get('loss', stats.get('avg_loss', 0)):.6f}")
        self.kl_loss_label.setText(f"KL损失: {stats.get('kl_loss', stats.get('avg_kl_loss', 0)):.6f}")
        self.rec_loss_label.setText(f"重构损失: {stats.get('rec_loss', stats.get('avg_rec_loss', 0)):.6f}")
        
        if self.use_adversarial_cb.isChecked():
            self.adv_loss_label.setText(f"对抗损失: {stats.get('adv_loss', stats.get('avg_adv_loss', 0)):.6f}")
            self.disc_loss_label.setText(f"判别损失: {stats.get('disc_loss', stats.get('avg_disc_loss', 0)):.6f}")
        
        self.div_loss_label.setText(f"多样性损失: {stats.get('div_loss', stats.get('avg_div_loss', 0)):.6f}")
        self.lr_label.setText(f"学习率: {stats.get('lr', 0):.2e}")
        
        # 更新进度条
        self.progress_bar.setValue(int(stats.get('progress', 0)))
        
        # 更新损失曲线
        if 'loss' in stats:
            self.loss_data['total'].append(stats['loss'])
            self.loss_data['kl'].append(stats['kl_loss'])
            self.loss_data['rec'].append(stats['rec_loss'])
            
            if self.use_adversarial_cb.isChecked():
                self.loss_data['adv'].append(stats['adv_loss'])
            
            self.loss_data['div'].append(stats['div_loss'])
            
            x = np.arange(len(self.loss_data['total']))
            self.loss_curve.setData(x, self.loss_data['total'])
            self.kl_loss_curve.setData(x, self.loss_data['kl'])
            self.rec_loss_curve.setData(x, self.loss_data['rec'])
            
            if self.use_adversarial_cb.isChecked():
                self.adv_loss_curve.setData(x, self.loss_data['adv'])
            
            self.div_loss_curve.setData(x, self.loss_data['div'])
            
            self.iteration += 1
            
        # 更新想象可视化
        if random.random() < 0.1:  # 10%的概率更新可视化
            self.update_visualizations()
            
    def update_visualizations(self):
        """更新所有可视化"""
        # 获取想象历史
        history = self.model.get_imagination_stats()
        if history:
            latest = history[-1]
            self.imagination_viz.update_visualization(
                latest['original_z'], 
                latest['imagined_z']
            )
            
            # 更新历史表格
            self.update_history_table(history)
        
        # 更新记忆可视化
        memory_stats = self.model.get_memory_stats()
        if memory_stats:
            self.memory_viz.update_visualization(memory_stats)
            
    def update_history_table(self, history):
        """更新历史表格"""
        self.history_table.setRowCount(min(20, len(history)))
        
        for i, item in enumerate(history[-20:]):
            # 添加时间戳
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.history_table.setItem(i, 0, QTableWidgetItem(timestamp))
            self.history_table.setItem(i, 1, QTableWidgetItem(str(item['head_idx'])))
            self.history_table.setItem(i, 2, QTableWidgetItem(f"{item['strength']:.3f}"))
            self.history_table.setItem(i, 3, QTableWidgetItem(f"{item['scale_factor']:.3f}"))
            
            # 计算差异
            diff = torch.mean(torch.abs(item['original_z'] - item['imagined_z'])).item()
            self.history_table.setItem(i, 4, QTableWidgetItem(f"{diff:.6f}"))
            
    def clear_history_table(self):
        """清除历史表格"""
        self.history_table.setRowCount(0)
        
    def export_history_data(self):
        """导出历史数据"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出历史数据", "", "CSV文件 (*.csv);;所有文件 (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    f.write("时间,头索引,强度,尺度,差异\n")
                    for row in range(self.history_table.rowCount()):
                        line = []
                        for col in range(self.history_table.columnCount()):
                            item = self.history_table.item(row, col)
                            line.append(item.text() if item else "")
                        f.write(",".join(line) + "\n")
                self.statusBar().showMessage(f"历史数据已导出: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出历史数据失败: {str(e)}")
    
    def clear_loss_plot(self):
        """清除损失曲线"""
        self.loss_data = {'total': [], 'kl': [], 'rec': [], 'adv': [], 'div': []}
        self.iteration = 0
        
        self.loss_curve.setData([], [])
        self.kl_loss_curve.setData([], [])
        self.rec_loss_curve.setData([], [])
        self.adv_loss_curve.setData([], [])
        self.div_loss_curve.setData([], [])
    
    def export_loss_data(self):
        """导出损失数据"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出损失数据", "", "CSV文件 (*.csv);;所有文件 (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    f.write("Iteration,Loss,KL_Loss,Reconstruction_Loss,Adversarial_Loss,Diversity_Loss\n")
                    for i in range(len(self.loss_data['total'])):
                        line = [
                            str(i),
                            str(self.loss_data['total'][i]),
                            str(self.loss_data['kl'][i]),
                            str(self.loss_data['rec'][i]),
                            str(self.loss_data['adv'][i] if i < len(self.loss_data['adv']) else 0),
                            str(self.loss_data['div'][i])
                        ]
                        f.write(",".join(line) + "\n")
                self.statusBar().showMessage(f"损失数据已导出: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出损失数据失败: {str(e)}")
    
    def generate_samples(self):
        """生成样本"""
        head_idx = self.head_idx_combo.currentIndex()
        samples = self.model.imagination_layer.generate(5, head_idx=head_idx)
        
        # 这里可以添加样本可视化代码
        print(f"生成了 {samples.shape[0]} 个样本 (头 {head_idx})")
        self.statusBar().showMessage(f"已生成 {samples.shape[0]} 个样本")
    
    def generate_and_visualize_samples(self):
        """生成并可视化样本"""
        head_idx = self.head_idx_combo.currentIndex()
        num_samples = self.num_samples_spin.value()
        
        samples = self.model.imagination_layer.generate(num_samples, head_idx=head_idx)
        
        # 显示样本
        sample_text = f"生成 {num_samples} 个样本 (头 {head_idx}):\n\n"
        for i, sample in enumerate(samples):
            sample_values = ", ".join([f"{x:.4f}" for x in sample.tolist()[:5]])
            if len(sample) > 5:
                sample_values += ", ..."
            sample_text += f"样本 {i+1}: [{sample_values}]\n\n"
        
        self.samples_text.setPlainText(sample_text)
        self.statusBar().showMessage(f"已生成并显示 {num_samples} 个样本")
    
    def visualize_imagination(self):
        """可视化想象过程"""
        # 使用随机输入数据
        input_data = torch.randn(1, self.model.input_dim)
        
        # 提取特征
        features = self.model.feature_extractor(input_data)
        
        # 使用想象层
        head_idx = self.head_idx_combo.currentIndex()
        imagined_features, _, _, _ = self.model.imagination_layer(
            features, 
            use_imagination=True,
            imagination_strength=self.imagination_strength_slider.value() / 100.0,
            head_idx=head_idx
        )
        
        # 更新可视化
        self.imagination_viz.update_visualization(features, imagined_features)
        self.statusBar().showMessage("想象过程已可视化")
    
    def resetViews(self):
        """重置所有视图"""
        self.clear_loss_plot()
        self.imagination_viz.clear_history()
        self.clear_history_table()
        self.samples_text.clear()
        self.statusBar().showMessage("所有视图已重置")
    
    def showAbout(self):
        """显示关于对话框"""
        about_text = """
        <h3>神经网络想象层可视化工具</h3>
        <p>这是一个基于PyQt6和PyTorch的神经网络想象层可视化工具。</p>
        <p>功能特点:</p>
        <ul>
            <li>多尺度想象层，支持多种想象模式</li>
            <li>记忆网络和注意力机制</li>
            <li>对抗训练支持</li>
            <li>实时训练监控和可视化</li>
            <li>样本生成和想象过程可视化</li>
        </ul>
        <p>版本: 2.0 (PyQt6)</p>
        """
        QMessageBox.about(self, "关于", about_text)


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建主窗口
    window = EnhancedImaginationLayerGUI()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()