import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import torch
import torch.nn as nn
import torch.optim as optim
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                             QTextEdit, QTabWidget, QGroupBox, QGridLayout,
                             QSpinBox, QDoubleSpinBox, QComboBox, QCheckBox,
                             QProgressBar, QMessageBox, QFileDialog, QSplitter)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
import random

# 神经网络模型定义
class CircuitExplorerNet(nn.Module):
    def __init__(self, input_size=10, hidden_layers=[64, 32], output_size=5, dropout_rate=0.2):
        super(CircuitExplorerNet, self).__init__()
        self.layers = nn.ModuleList()
        
        # 输入层
        self.layers.append(nn.Linear(input_size, hidden_layers[0]))
        self.layers.append(nn.ReLU())
        self.layers.append(nn.Dropout(dropout_rate))
        
        # 隐藏层
        for i in range(len(hidden_layers)-1):
            self.layers.append(nn.Linear(hidden_layers[i], hidden_layers[i+1]))
            self.layers.append(nn.ReLU())
            self.layers.append(nn.Dropout(dropout_rate))
        
        # 输出层
        self.layers.append(nn.Linear(hidden_layers[-1], output_size))
        self.layers.append(nn.Sigmoid())  # 使用Sigmoid将输出限制在0-1范围内
    
    def forward(self, x):
        for layer in self.layers:
            x = layer(x)
        return x

# 训练线程
class TrainingThread(QThread):
    update_progress = pyqtSignal(int, float, float)  # epoch, loss, accuracy
    training_finished = pyqtSignal()
    
    def __init__(self, model, train_data, train_labels, epochs, batch_size, learning_rate):
        super().__init__()
        self.model = model
        self.train_data = train_data
        self.train_labels = train_labels
        self.epochs = epochs
        self.batch_size = batch_size
        self.learning_rate = learning_rate
        self.criterion = nn.MSELoss()
        self.optimizer = optim.Adam(self.model.parameters(), lr=self.learning_rate)
        
    def run(self):
        self.model.train()
        n_samples = len(self.train_data)
        
        for epoch in range(self.epochs):
            # 随机打乱数据
            indices = torch.randperm(n_samples)
            total_loss = 0
            
            for i in range(0, n_samples, self.batch_size):
                batch_indices = indices[i:i+self.batch_size]
                batch_data = self.train_data[batch_indices]
                batch_labels = self.train_labels[batch_indices]
                
                # 前向传播
                outputs = self.model(batch_data)
                loss = self.criterion(outputs, batch_labels)
                
                # 反向传播和优化
                self.optimizer.zero_grad()
                loss.backward()
                self.optimizer.step()
                
                total_loss += loss.item()
            
            avg_loss = total_loss / (n_samples / self.batch_size)
            
            # 计算准确率（简化版，根据实际需求调整）
            with torch.no_grad():
                predictions = self.model(self.train_data)
                accuracy = torch.mean(1 - torch.abs(predictions - self.train_labels)).item()
            
            self.update_progress.emit(epoch+1, avg_loss, accuracy)
        
        self.training_finished.emit()

# 主窗口类
class NeuralCircuitExplorer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.model = None
        self.train_data = None
        self.train_labels = None
        self.test_data = None
        self.test_labels = None
        self.training_thread = None
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("神经网络颠覆性电路探索算法")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中央窗口和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # 创建左侧面板
        left_panel = QWidget()
        left_panel.setMaximumWidth(300)
        left_layout = QVBoxLayout(left_panel)
        
        # 网络配置组
        net_config_group = QGroupBox("神经网络配置")
        net_config_layout = QGridLayout(net_config_group)
        
        net_config_layout.addWidget(QLabel("输入维度:"), 0, 0)
        self.input_dim = QSpinBox()
        self.input_dim.setRange(1, 100)
        self.input_dim.setValue(10)
        net_config_layout.addWidget(self.input_dim, 0, 1)
        
        net_config_layout.addWidget(QLabel("隐藏层:"), 1, 0)
        self.hidden_layers = QLineEdit("64,32")
        net_config_layout.addWidget(self.hidden_layers, 1, 1)
        
        net_config_layout.addWidget(QLabel("输出维度:"), 2, 0)
        self.output_dim = QSpinBox()
        self.output_dim.setRange(1, 50)
        self.output_dim.setValue(5)
        net_config_layout.addWidget(self.output_dim, 2, 1)
        
        net_config_layout.addWidget(QLabel("Dropout率:"), 3, 0)
        self.dropout_rate = QDoubleSpinBox()
        self.dropout_rate.setRange(0.0, 0.9)
        self.dropout_rate.setValue(0.2)
        self.dropout_rate.setSingleStep(0.1)
        net_config_layout.addWidget(self.dropout_rate, 3, 1)
        
        left_layout.addWidget(net_config_group)
        
        # 训练配置组
        train_config_group = QGroupBox("训练配置")
        train_config_layout = QGridLayout(train_config_group)
        
        train_config_layout.addWidget(QLabel("训练轮数:"), 0, 0)
        self.epochs = QSpinBox()
        self.epochs.setRange(1, 10000)
        self.epochs.setValue(100)
        train_config_layout.addWidget(self.epochs, 0, 1)
        
        train_config_layout.addWidget(QLabel("批大小:"), 1, 0)
        self.batch_size = QSpinBox()
        self.batch_size.setRange(1, 1000)
        self.batch_size.setValue(32)
        train_config_layout.addWidget(self.batch_size, 1, 1)
        
        train_config_layout.addWidget(QLabel("学习率:"), 2, 0)
        self.learning_rate = QDoubleSpinBox()
        self.learning_rate.setRange(0.0001, 1.0)
        self.learning_rate.setValue(0.001)
        self.learning_rate.setDecimals(4)
        train_config_layout.addWidget(self.learning_rate, 2, 1)
        
        train_config_layout.addWidget(QLabel("数据量:"), 3, 0)
        self.data_size = QSpinBox()
        self.data_size.setRange(100, 100000)
        self.data_size.setValue(1000)
        train_config_layout.addWidget(self.data_size, 3, 1)
        
        left_layout.addWidget(train_config_group)
        
        # 按钮组
        button_group = QGroupBox("操作")
        button_layout = QVBoxLayout(button_group)
        
        self.generate_data_btn = QPushButton("生成训练数据")
        self.generate_data_btn.clicked.connect(self.generate_data)
        button_layout.addWidget(self.generate_data_btn)
        
        self.create_model_btn = QPushButton("创建模型")
        self.create_model_btn.clicked.connect(self.create_model)
        button_layout.addWidget(self.create_model_btn)
        
        self.train_btn = QPushButton("开始训练")
        self.train_btn.clicked.connect(self.start_training)
        self.train_btn.setEnabled(False)
        button_layout.addWidget(self.train_btn)
        
        self.explore_btn = QPushButton("电路探索")
        self.explore_btn.clicked.connect(self.explore_circuits)
        self.explore_btn.setEnabled(False)
        button_layout.addWidget(self.explore_btn)
        
        self.save_model_btn = QPushButton("保存模型")
        self.save_model_btn.clicked.connect(self.save_model)
        self.save_model_btn.setEnabled(False)
        button_layout.addWidget(self.save_model_btn)
        
        self.load_model_btn = QPushButton("加载模型")
        self.load_model_btn.clicked.connect(self.load_model)
        button_layout.addWidget(self.load_model_btn)
        
        left_layout.addWidget(button_group)
        
        # 训练进度组
        progress_group = QGroupBox("训练进度")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_bar)
        
        self.epoch_label = QLabel("轮次: 0/0")
        progress_layout.addWidget(self.epoch_label)
        
        self.loss_label = QLabel("损失: --")
        progress_layout.addWidget(self.loss_label)
        
        self.accuracy_label = QLabel("准确率: --")
        progress_layout.addWidget(self.accuracy_label)
        
        left_layout.addWidget(progress_group)
        
        left_layout.addStretch()
        
        # 创建右侧面板（标签页）
        right_panel = QTabWidget()
        
        # 网络结构标签页
        self.network_tab = QWidget()
        network_layout = QVBoxLayout(self.network_tab)
        self.network_text = QTextEdit()
        self.network_text.setReadOnly(True)
        network_layout.addWidget(self.network_text)
        right_panel.addTab(self.network_tab, "网络结构")
        
        # 训练过程标签页
        self.training_tab = QWidget()
        training_layout = QVBoxLayout(self.training_tab)
        self.training_figure = Figure(figsize=(10, 8))
        self.training_canvas = FigureCanvas(self.training_figure)
        training_layout.addWidget(self.training_canvas)
        right_panel.addTab(self.training_tab, "训练过程")
        
        # 电路探索标签页
        self.exploration_tab = QWidget()
        exploration_layout = QVBoxLayout(self.exploration_tab)
        self.exploration_figure = Figure(figsize=(10, 8))
        self.exploration_canvas = FigureCanvas(self.exploration_figure)
        exploration_layout.addWidget(self.exploration_canvas)
        right_panel.addTab(self.exploration_tab, "电路探索")
        
        # 结果输出标签页
        self.results_tab = QWidget()
        results_layout = QVBoxLayout(self.results_tab)
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        results_layout.addWidget(self.results_text)
        right_panel.addTab(self.results_tab, "结果输出")
        
        # 将左右面板添加到主布局
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)
        
        # 状态栏
        self.statusBar().showMessage("准备就绪")
        
        # 初始化训练图表
        self.init_training_plot()
        
    def init_training_plot(self):
        self.training_figure.clear()
        self.ax1 = self.training_figure.add_subplot(211)
        self.ax2 = self.training_figure.add_subplot(212)
        
        self.ax1.set_title('训练损失')
        self.ax1.set_xlabel('轮次')
        self.ax1.set_ylabel('损失')
        
        self.ax2.set_title('训练准确率')
        self.ax2.set_xlabel('轮次')
        self.ax2.set_ylabel('准确率')
        
        self.training_canvas.draw()
        
    def generate_data(self):
        try:
            data_size = self.data_size.value()
            input_dim = self.input_dim.value()
            output_dim = self.output_dim.value()
            
            # 生成模拟电路数据
            # 这里使用随机数据作为示例，实际应用中应使用真实电路数据
            self.train_data = torch.randn(data_size, input_dim)
            
            # 生成模拟标签（电路性能指标）
            # 这里使用简单的非线性函数作为示例
            weights = torch.randn(input_dim, output_dim)
            bias = torch.randn(output_dim)
            self.train_labels = torch.sigmoid(torch.mm(self.train_data, weights) + bias)
            
            # 添加一些噪声
            self.train_labels += 0.1 * torch.randn_like(self.train_labels)
            self.train_labels = torch.clamp(self.train_labels, 0, 1)
            
            # 分割训练集和测试集
            split_idx = int(0.8 * data_size)
            self.test_data = self.train_data[split_idx:]
            self.test_labels = self.train_labels[split_idx:]
            self.train_data = self.train_data[:split_idx]
            self.train_labels = self.train_labels[:split_idx]
            
            self.results_text.append(f"已生成 {data_size} 个训练样本")
            self.results_text.append(f"输入维度: {input_dim}, 输出维度: {output_dim}")
            self.results_text.append(f"训练集大小: {len(self.train_data)}, 测试集大小: {len(self.test_data)}")
            
            self.statusBar().showMessage("数据生成完成")
            
            # 启用训练按钮
            self.train_btn.setEnabled(True)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"生成数据时出错: {str(e)}")
    
    def create_model(self):
        try:
            input_dim = self.input_dim.value()
            hidden_layers = [int(x.strip()) for x in self.hidden_layers.text().split(',')]
            output_dim = self.output_dim.value()
            dropout_rate = self.dropout_rate.value()
            
            self.model = CircuitExplorerNet(input_dim, hidden_layers, output_dim, dropout_rate)
            
            # 显示网络结构
            self.network_text.clear()
            self.network_text.append("神经网络结构:")
            self.network_text.append(f"输入层: {input_dim} 个神经元")
            for i, layer_size in enumerate(hidden_layers):
                self.network_text.append(f"隐藏层 {i+1}: {layer_size} 个神经元")
            self.network_text.append(f"输出层: {output_dim} 个神经元")
            self.network_text.append(f"Dropout率: {dropout_rate}")
            
            # 显示模型参数数量
            total_params = sum(p.numel() for p in self.model.parameters())
            self.network_text.append(f"总参数数量: {total_params}")
            
            self.statusBar().showMessage("模型创建完成")
            self.explore_btn.setEnabled(True)
            self.save_model_btn.setEnabled(True)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"创建模型时出错: {str(e)}")
    
    def start_training(self):
        if self.model is None:
            QMessageBox.warning(self, "警告", "请先创建模型")
            return
        
        if self.train_data is None:
            QMessageBox.warning(self, "警告", "请先生成训练数据")
            return
        
        try:
            # 禁用训练按钮，防止重复点击
            self.train_btn.setEnabled(False)
            
            # 重置训练图表
            self.init_training_plot()
            
            # 创建训练线程
            self.training_thread = TrainingThread(
                self.model, 
                self.train_data, 
                self.train_labels,
                self.epochs.value(),
                self.batch_size.value(),
                self.learning_rate.value()
            )
            
            # 连接信号
            self.training_thread.update_progress.connect(self.update_training_progress)
            self.training_thread.training_finished.connect(self.training_finished)
            
            # 开始训练
            self.training_thread.start()
            
            self.statusBar().showMessage("训练开始...")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"开始训练时出错: {str(e)}")
            self.train_btn.setEnabled(True)
    
    def update_training_progress(self, epoch, loss, accuracy):
        # 更新进度条
        progress = int((epoch / self.epochs.value()) * 100)
        self.progress_bar.setValue(progress)
        
        # 更新标签
        self.epoch_label.setText(f"轮次: {epoch}/{self.epochs.value()}")
        self.loss_label.setText(f"损失: {loss:.6f}")
        self.accuracy_label.setText(f"准确率: {accuracy:.4f}")
        
        # 更新图表
        if not hasattr(self, 'loss_history'):
            self.loss_history = []
            self.accuracy_history = []
        
        self.loss_history.append(loss)
        self.accuracy_history.append(accuracy)
        
        self.ax1.clear()
        self.ax1.plot(range(1, epoch+1), self.loss_history)
        self.ax1.set_title('训练损失')
        self.ax1.set_xlabel('轮次')
        self.ax1.set_ylabel('损失')
        
        self.ax2.clear()
        self.ax2.plot(range(1, epoch+1), self.accuracy_history)
        self.ax2.set_title('训练准确率')
        self.ax2.set_xlabel('轮次')
        self.ax2.set_ylabel('准确率')
        
        self.training_canvas.draw()
        
        self.statusBar().showMessage(f"训练中... 轮次: {epoch}/{self.epochs.value()}")
    
    def training_finished(self):
        self.train_btn.setEnabled(True)
        self.statusBar().showMessage("训练完成")
        
        # 在测试集上评估模型
        self.evaluate_model()
    
    def evaluate_model(self):
        if self.model is None or self.test_data is None:
            return
        
        self.model.eval()
        with torch.no_grad():
            predictions = self.model(self.test_data)
            test_loss = nn.MSELoss()(predictions, self.test_labels).item()
            test_accuracy = torch.mean(1 - torch.abs(predictions - self.test_labels)).item()
        
        self.results_text.append(f"测试集损失: {test_loss:.6f}")
        self.results_text.append(f"测试集准确率: {test_accuracy:.4f}")
    
    def explore_circuits(self):
        if self.model is None:
            QMessageBox.warning(self, "警告", "请先创建并训练模型")
            return
        
        try:
            self.model.eval()
            
            # 生成随机电路配置进行探索
            n_explorations = 100
            input_dim = self.input_dim.value()
            random_inputs = torch.randn(n_explorations, input_dim)
            
            with torch.no_grad():
                explorations = self.model(random_inputs)
            
            # 可视化探索结果
            self.exploration_figure.clear()
            ax = self.exploration_figure.add_subplot(111)
            
            # 选择前两个输出维度进行可视化
            if explorations.shape[1] >= 2:
                ax.scatter(explorations[:, 0].numpy(), explorations[:, 1].numpy(), alpha=0.7)
                ax.set_xlabel('输出维度 1')
                ax.set_ylabel('输出维度 2')
                ax.set_title('电路探索结果')
            else:
                ax.plot(explorations.numpy())
                ax.set_xlabel('样本索引')
                ax.set_ylabel('输出值')
                ax.set_title('电路探索结果')
            
            self.exploration_canvas.draw()
            
            # 输出探索结果
            self.results_text.append("电路探索完成")
            self.results_text.append(f"探索了 {n_explorations} 个电路配置")
            
            # 找出最佳配置
            if explorations.shape[1] >= 2:
                # 假设我们希望最大化第一个输出并最小化第二个输出
                scores = explorations[:, 0] - explorations[:, 1]
                best_idx = torch.argmax(scores)
                best_config = random_inputs[best_idx]
                best_output = explorations[best_idx]
                
                self.results_text.append("最佳电路配置:")
                self.results_text.append(f"输入: {best_config.numpy()}")
                self.results_text.append(f"输出: {best_output.numpy()}")
                self.results_text.append(f"评分: {scores[best_idx].item():.4f}")
            
            self.statusBar().showMessage("电路探索完成")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"电路探索时出错: {str(e)}")
    
    def save_model(self):
        if self.model is None:
            QMessageBox.warning(self, "警告", "没有模型可保存")
            return
        
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存模型", "", "PyTorch模型文件 (*.pth)"
            )
            
            if file_path:
                torch.save(self.model.state_dict(), file_path)
                self.results_text.append(f"模型已保存到: {file_path}")
                self.statusBar().showMessage("模型保存成功")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存模型时出错: {str(e)}")
    
    def load_model(self):
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "加载模型", "", "PyTorch模型文件 (*.pth)"
            )
            
            if file_path:
                # 先创建模型结构
                self.create_model()
                
                # 加载模型参数
                self.model.load_state_dict(torch.load(file_path))
                self.model.eval()
                
                self.results_text.append(f"模型已从 {file_path} 加载")
                self.statusBar().showMessage("模型加载成功")
                self.explore_btn.setEnabled(True)
                self.save_model_btn.setEnabled(True)
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载模型时出错: {str(e)}")

# 主函数
def main():
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = NeuralCircuitExplorer()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()