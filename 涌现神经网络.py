import sys
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QComboBox, QSpinBox, QDoubleSpinBox, 
                             QSlider, QCheckBox, QGroupBox, QTabWidget, QTextEdit, 
                             QProgressBar, QTableWidget, QTableWidgetItem, QSplitter,
                             QFileDialog, QMessageBox, QGridLayout, QFrame, QScrollArea)
from PyQt5.QtCore import QTimer, Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPalette, QColor

from sklearn.datasets import make_classification, make_blobs, make_moons
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import seaborn as sns

# 导入之前定义的涌现临界网络类
class CriticalEmergenceNeuron:
    def __init__(self, neuron_id, base_activation=0.001, alpha=0.1, beta=0.05):
        self.id = neuron_id
        self.base_activation = base_activation
        self.alpha = alpha
        self.beta = beta
        self.connections = {}
        self.activation_history = []
        self.critical_state = False
        self.emergence_level = 0.0
        
    def add_connection(self, target_neuron, weight):
        self.connections[target_neuron.id] = {
            'neuron': target_neuron,
            'weight': weight,
            'synergy': 0.0
        }
    
    def compute_emergence_function(self, network_size):
        return 1 + self.alpha * np.log(network_size + 1)
    
    def critical_activation(self, input_stimulus, network_context):
        base_p = self.base_activation
        network_size = network_context['size']
        f_N = self.compute_emergence_function(network_size)
        
        connection_synergy = 0.0
        active_connections = 0
        
        for conn_id, conn_data in self.connections.items():
            target_neuron = conn_data['neuron']
            if target_neuron.critical_state:
                connection_synergy += conn_data['weight'] * conn_data['synergy']
                active_connections += 1
        
        if active_connections > 0:
            connection_synergy /= active_connections
        
        critical_prob = base_p * f_N * (1 + self.beta * connection_synergy)
        critical_prob = min(critical_prob, 0.99)
        
        activation_threshold = network_context['global_threshold']
        should_activate = (critical_prob > activation_threshold) and (np.random.random() < critical_prob)
        
        if should_activate:
            self.critical_state = True
            self.emergence_level = critical_prob
            
            for conn_id, conn_data in self.connections.items():
                conn_data['synergy'] = 0.9 * conn_data['synergy'] + 0.1 * critical_prob
        else:
            self.critical_state = False
            self.emergence_level *= 0.95
            
        self.activation_history.append(self.critical_state)
        return self.critical_state, critical_prob

class EmergenceCriticalLayer:
    def __init__(self, layer_id, num_neurons, base_activation=0.001):
        self.layer_id = layer_id
        self.neurons = [CriticalEmergenceNeuron(i, base_activation) for i in range(num_neurons)]
        self.layer_emergence = 0.0
        self.critical_mass = 0
        
    def connect_layers(self, previous_layer, connection_density=0.3):
        for neuron in self.neurons:
            num_connections = int(len(previous_layer.neurons) * connection_density)
            connected_neurons = np.random.choice(
                previous_layer.neurons, 
                size=num_connections, 
                replace=False
            )
            
            for prev_neuron in connected_neurons:
                weight = np.random.normal(0.5, 0.2)
                neuron.add_connection(prev_neuron, max(0.1, weight))
    
    def compute_layer_emergence(self):
        active_neurons = sum(1 for neuron in self.neurons if neuron.critical_state)
        total_neurons = len(self.neurons)
        
        self.critical_mass = active_neurons
        self.layer_emergence = active_neurons / total_neurons if total_neurons > 0 else 0
        return self.layer_emergence

class CriticalEmergenceNetwork:
    def __init__(self, layer_sizes, base_activation=0.001):
        self.layers = []
        self.global_threshold = 0.1
        self.phase_transition_detected = False
        self.learning_cycles = 0
        
        for i, size in enumerate(layer_sizes):
            layer = EmergenceCriticalLayer(i, size, base_activation)
            self.layers.append(layer)
            
            if i > 0:
                layer.connect_layers(self.layers[i-1])
    
    def forward_emergence(self, input_pattern, max_cycles=100):
        for layer in self.layers:
            for neuron in layer.neurons:
                neuron.critical_state = False
                neuron.emergence_level = 0.0
        
        input_layer = self.layers[0]
        for i, activation in enumerate(input_pattern):
            if i < len(input_layer.neurons):
                input_layer.neurons[i].critical_state = (activation > 0.5)
                input_layer.neurons[i].emergence_level = activation
        
        network_context = {
            'size': sum(len(layer.neurons) for layer in self.layers),
            'global_threshold': self.global_threshold,
            'cycle': 0
        }
        
        for cycle in range(max_cycles):
            network_context['cycle'] = cycle
            
            total_activations = 0
            for layer_idx, layer in enumerate(self.layers[1:], 1):
                layer_activations = 0
                
                for neuron in layer.neurons:
                    activated, prob = neuron.critical_activation(0, network_context)
                    if activated:
                        layer_activations += 1
                
                total_activations += layer_activations
                layer.compute_layer_emergence()
            
            if total_activations > network_context['size'] * 0.3:
                self.phase_transition_detected = True
                break
            
            if cycle % 10 == 0:
                self.global_threshold *= 0.95
        
        return self.get_output_emergence()
    
    def get_output_emergence(self):
        output_layer = self.layers[-1]
        output_pattern = []
        
        for neuron in output_layer.neurons:
            output_pattern.append(1.0 if neuron.critical_state else 0.0)
        
        return np.array(output_pattern)
    
    def adaptive_learning(self, target_pattern, learning_rate=0.1):
        output_pattern = self.get_output_emergence()
        error = np.mean((output_pattern - target_pattern) ** 2)
        
        for layer in self.layers[1:]:
            for neuron in layer.neurons:
                for conn_id, conn_data in neuron.connections.items():
                    target_neuron = conn_data['neuron']
                    
                    if (target_neuron.critical_state and 
                        any(target_pattern > 0.5) and 
                        not neuron.critical_state):
                        conn_data['weight'] += learning_rate * conn_data['synergy']
                    
                    elif (not target_neuron.critical_state and 
                          neuron.critical_state and 
                          all(target_pattern < 0.5)):
                        conn_data['weight'] *= (1 - learning_rate)
                    
                    conn_data['weight'] = max(0.01, min(1.0, conn_data['weight']))
        
        self.learning_cycles += 1
        
        if self.learning_cycles % 100 == 0:
            self.global_threshold = 0.1
        
        return error

class EmergenceCriticalClassifier:
    def __init__(self, input_size, hidden_sizes, output_size, base_activation=0.001):
        layer_sizes = [input_size] + hidden_sizes + [output_size]
        self.network = CriticalEmergenceNetwork(layer_sizes, base_activation)
        self.learning_rate = 0.1
        self.emergence_history = []
        
    def train(self, X, y, epochs=100, batch_size=32):
        losses = []
        accuracies = []
        
        for epoch in range(epochs):
            epoch_loss = 0
            correct = 0
            total = 0
            
            for i in range(0, len(X), batch_size):
                batch_X = X[i:i+batch_size]
                batch_y = y[i:i+batch_size]
                
                batch_loss = 0
                for x, target in zip(batch_X, batch_y):
                    self.network.forward_emergence(x)
                    
                    target_pattern = np.zeros(len(self.network.layers[-1].neurons))
                    if len(target_pattern) > 0:
                        target_idx = int(target) if hasattr(target, '__len__') else target
                        target_pattern[target_idx % len(target_pattern)] = 1.0
                    
                    loss = self.network.adaptive_learning(target_pattern, self.learning_rate)
                    batch_loss += loss
                    
                    output = self.network.get_output_emergence()
                    predicted = np.argmax(output)
                    true_label = np.argmax(target_pattern) if hasattr(target_pattern[0], '__len__') else int(target)
                    
                    if predicted == true_label:
                        correct += 1
                    total += 1
                
                epoch_loss += batch_loss / len(batch_X)
            
            accuracy = correct / total if total > 0 else 0
            losses.append(epoch_loss)
            accuracies.append(accuracy)
            
            if epoch > 10 and accuracy > 0.8:
                self.learning_rate *= 0.99
            
            if epoch % 10 == 0:
                print(f'Epoch {epoch}, Loss: {epoch_loss:.4f}, Accuracy: {accuracy:.4f}')
        
        return losses, accuracies
    
    def predict(self, X):
        predictions = []
        
        for x in X:
            self.network.forward_emergence(x)
            output = self.network.get_output_emergence()
            predicted = np.argmax(output)
            predictions.append(predicted)
        
        return np.array(predictions)
    
    def analyze_emergence(self, X_sample):
        emergence_stats = []
        
        for x in X_sample:
            self.network.forward_emergence(x)
            
            layer_stats = []
            for layer in self.network.layers:
                layer_stats.append({
                    'emergence_level': layer.layer_emergence,
                    'critical_mass': layer.critical_mass,
                    'total_neurons': len(layer.neurons)
                })
            
            emergence_stats.append(layer_stats)
        
        return emergence_stats

# 训练线程
class TrainingThread(QThread):
    update_signal = pyqtSignal(dict)
    finished_signal = pyqtSignal(dict)
    
    def __init__(self, classifier, X_train, y_train, X_test, y_test, epochs):
        super().__init__()
        self.classifier = classifier
        self.X_train = X_train
        self.y_train = y_train
        self.X_test = X_test
        self.y_test = y_test
        self.epochs = epochs
        self.is_running = True
        
    def run(self):
        losses, accuracies = self.classifier.train(
            self.X_train, self.y_train, 
            epochs=self.epochs, batch_size=16
        )
        
        # 测试性能
        y_pred = self.classifier.predict(self.X_test)
        test_accuracy = np.mean(y_pred == self.y_test)
        
        # 分析涌现特性
        sample_indices = np.random.choice(len(self.X_test), min(10, len(self.X_test)), replace=False)
        X_sample = self.X_test[sample_indices]
        emergence_stats = self.classifier.analyze_emergence(X_sample)
        
        result = {
            'losses': losses,
            'accuracies': accuracies,
            'test_accuracy': test_accuracy,
            'emergence_stats': emergence_stats,
            'y_pred': y_pred
        }
        
        self.finished_signal.emit(result)
    
    def stop(self):
        self.is_running = False

# 可视化组件
class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)

class RealTimeVisualizationWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        
        # 训练过程标签页
        self.training_tab = QWidget()
        self.setup_training_tab()
        self.tab_widget.addTab(self.training_tab, "训练过程")
        
        # 网络结构标签页
        self.network_tab = QWidget()
        self.setup_network_tab()
        self.tab_widget.addTab(self.network_tab, "网络结构")
        
        # 涌现分析标签页
        self.emergence_tab = QWidget()
        self.setup_emergence_tab()
        self.tab_widget.addTab(self.emergence_tab, "涌现分析")
        
        # 对比分析标签页
        self.comparison_tab = QWidget()
        self.setup_comparison_tab()
        self.tab_widget.addTab(self.comparison_tab, "对比分析")
        
        layout.addWidget(self.tab_widget)
        self.setLayout(layout)
        
    def setup_training_tab(self):
        layout = QVBoxLayout()
        
        # 训练指标图
        self.training_canvas = MplCanvas(self, width=10, height=8)
        self.training_toolbar = NavigationToolbar(self.training_canvas, self)
        
        layout.addWidget(self.training_toolbar)
        layout.addWidget(self.training_canvas)
        
        self.training_tab.setLayout(layout)
    
    def setup_network_tab(self):
        layout = QVBoxLayout()
        
        self.network_canvas = MplCanvas(self, width=10, height=8)
        self.network_toolbar = NavigationToolbar(self.network_canvas, self)
        
        layout.addWidget(self.network_toolbar)
        layout.addWidget(self.network_canvas)
        
        self.network_tab.setLayout(layout)
    
    def setup_emergence_tab(self):
        layout = QVBoxLayout()
        
        self.emergence_canvas = MplCanvas(self, width=10, height=8)
        self.emergence_toolbar = NavigationToolbar(self.emergence_canvas, self)
        
        layout.addWidget(self.emergence_toolbar)
        layout.addWidget(self.emergence_canvas)
        
        self.emergence_tab.setLayout(layout)
    
    def setup_comparison_tab(self):
        layout = QVBoxLayout()
        
        self.comparison_canvas = MplCanvas(self, width=10, height=8)
        self.comparison_toolbar = NavigationToolbar(self.comparison_canvas, self)
        
        layout.addWidget(self.comparison_toolbar)
        layout.addWidget(self.comparison_canvas)
        
        self.comparison_tab.setLayout(layout)
    
    def update_training_plot(self, losses, accuracies):
        self.training_canvas.fig.clear()
        
        ax1 = self.training_canvas.fig.add_subplot(211)
        ax1.plot(losses, 'b-', linewidth=2)
        ax1.set_title('训练损失', fontsize=14, fontweight='bold')
        ax1.set_ylabel('损失')
        ax1.grid(True, alpha=0.3)
        
        ax2 = self.training_canvas.fig.add_subplot(212)
        ax2.plot(accuracies, 'r-', linewidth=2)
        ax2.set_title('训练准确率', fontsize=14, fontweight='bold')
        ax2.set_xlabel('训练轮次')
        ax2.set_ylabel('准确率')
        ax2.grid(True, alpha=0.3)
        
        self.training_canvas.fig.tight_layout()
        self.training_canvas.draw()
    
    def update_network_plot(self, classifier, sample_data):
        self.network_canvas.fig.clear()
        
        # 分析网络激活状态
        emergence_stats = classifier.analyze_emergence(sample_data[:1])[0]
        
        # 网络激活热图
        ax1 = self.network_canvas.fig.add_subplot(221)
        layer_activations = [layer['emergence_level'] for layer in emergence_stats]
        layers = [f'L{i}' for i in range(len(emergence_stats))]
        ax1.bar(layers, layer_activations, color='skyblue', alpha=0.7)
        ax1.set_title('各层涌现水平')
        ax1.set_ylabel('涌现水平')
        
        # 临界质量分布
        ax2 = self.network_canvas.fig.add_subplot(222)
        critical_masses = [layer['critical_mass'] for layer in emergence_stats]
        total_neurons = [layer['total_neurons'] for layer in emergence_stats]
        ax2.bar(layers, critical_masses, color='lightcoral', alpha=0.7, label='临界质量')
        ax2.plot(layers, total_neurons, 'ko-', label='总神经元数')
        ax2.set_title('临界质量分布')
        ax2.legend()
        
        # 连接权重分布
        ax3 = self.network_canvas.fig.add_subplot(223)
        all_weights = []
        for layer in classifier.network.layers:
            for neuron in layer.neurons:
                for conn_data in neuron.connections.values():
                    all_weights.append(conn_data['weight'])
        
        if all_weights:
            ax3.hist(all_weights, bins=20, alpha=0.7, color='lightgreen')
            ax3.set_title('连接权重分布')
            ax3.set_xlabel('权重值')
            ax3.set_ylabel('频次')
        
        # 协同效应分布
        ax4 = self.network_canvas.fig.add_subplot(224)
        all_synergies = []
        for layer in classifier.network.layers:
            for neuron in layer.neurons:
                for conn_data in neuron.connections.values():
                    all_synergies.append(conn_data['synergy'])
        
        if all_synergies:
            ax4.hist(all_synergies, bins=20, alpha=0.7, color='gold')
            ax4.set_title('协同效应分布')
            ax4.set_xlabel('协同值')
            ax4.set_ylabel('频次')
        
        self.network_canvas.fig.tight_layout()
        self.network_canvas.draw()
    
    def update_emergence_plot(self, emergence_stats):
        self.emergence_canvas.fig.clear()
        
        if not emergence_stats:
            return
            
        # 转换数据结构
        layer_emergence = np.array([[layer['emergence_level'] for layer in sample] 
                                   for sample in emergence_stats])
        critical_mass = np.array([[layer['critical_mass'] for layer in sample] 
                                 for sample in emergence_stats])
        
        # 涌现水平箱线图
        ax1 = self.emergence_canvas.fig.add_subplot(221)
        ax1.boxplot(layer_emergence.T)
        ax1.set_xlabel('网络层')
        ax1.set_ylabel('涌现水平')
        ax1.set_title('各层涌现水平分布')
        ax1.grid(True, alpha=0.3)
        
        # 临界质量趋势
        ax2 = self.emergence_canvas.fig.add_subplot(222)
        ax2.plot(critical_mass.mean(axis=0), 'o-', linewidth=2)
        ax2.fill_between(range(len(critical_mass.mean(axis=0))),
                        critical_mass.mean(axis=0) - critical_mass.std(axis=0),
                        critical_mass.mean(axis=0) + critical_mass.std(axis=0),
                        alpha=0.3)
        ax2.set_xlabel('网络层')
        ax2.set_ylabel('临界质量')
        ax2.set_title('临界质量传播趋势')
        ax2.grid(True, alpha=0.3)
        
        # 相变检测统计
        ax3 = self.emergence_canvas.fig.add_subplot(223)
        phase_transitions = [any(layer['emergence_level'] > 0.5 for layer in sample) 
                           for sample in emergence_stats]
        ax3.bar(['无相变', '有相变'], 
                [phase_transitions.count(False), phase_transitions.count(True)],
                color=['lightgray', 'lightcoral'])
        ax3.set_title('相变检测统计')
        ax3.set_ylabel('样本数')
        
        # 涌现相关性热图
        ax4 = self.emergence_canvas.fig.add_subplot(224)
        correlation_matrix = np.corrcoef(layer_emergence.T)
        im = ax4.imshow(correlation_matrix, cmap='coolwarm', aspect='auto', 
                       vmin=-1, vmax=1)
        ax4.set_title('层间涌现相关性')
        ax4.set_xlabel('网络层')
        ax4.set_ylabel('网络层')
        plt.colorbar(im, ax=ax4)
        
        self.emergence_canvas.fig.tight_layout()
        self.emergence_canvas.draw()
    
    def update_comparison_plot(self, ecn_results, mlp_results, X_test, y_test):
        self.comparison_canvas.fig.clear()
        
        # 性能对比
        ax1 = self.comparison_canvas.fig.add_subplot(221)
        models = ['涌现临界网络', '传统MLP']
        accuracies = [ecn_results.get('test_accuracy', 0), 
                     mlp_results.get('accuracy', 0)]
        bars = ax1.bar(models, accuracies, color=['lightblue', 'lightcoral'])
        ax1.set_ylabel('测试准确率')
        ax1.set_title('模型性能对比')
        ax1.set_ylim(0, 1)
        
        # 在柱状图上显示数值
        for bar, acc in zip(bars, accuracies):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                    f'{acc:.3f}', ha='center', va='bottom')
        
        # 训练曲线对比
        ax2 = self.comparison_canvas.fig.add_subplot(222)
        if 'accuracies' in ecn_results:
            ax2.plot(ecn_results['accuracies'], 'b-', label='涌现网络', linewidth=2)
        if 'mlp_accuracies' in mlp_results:
            ax2.plot(mlp_results['mlp_accuracies'], 'r-', label='传统MLP', linewidth=2)
        ax2.set_xlabel('训练轮次')
        ax2.set_ylabel('准确率')
        ax2.set_title('训练过程对比')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 混淆矩阵对比
        ax3 = self.comparison_canvas.fig.add_subplot(223)
        if 'y_pred' in ecn_results:
            cm_ecn = confusion_matrix(y_test, ecn_results['y_pred'])
            sns.heatmap(cm_ecn, annot=True, fmt='d', cmap='Blues', ax=ax3)
            ax3.set_title('涌现网络混淆矩阵')
            ax3.set_xlabel('预测标签')
            ax3.set_ylabel('真实标签')
        
        ax4 = self.comparison_canvas.fig.add_subplot(224)
        if 'y_pred_mlp' in mlp_results:
            cm_mlp = confusion_matrix(y_test, mlp_results['y_pred_mlp'])
            sns.heatmap(cm_mlp, annot=True, fmt='d', cmap='Reds', ax=ax4)
            ax4.set_title('传统MLP混淆矩阵')
            ax4.set_xlabel('预测标签')
            ax4.set_ylabel('真实标签')
        
        self.comparison_canvas.fig.tight_layout()
        self.comparison_canvas.draw()

# 主界面
class EmergenceCriticalApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.classifier = None
        self.training_thread = None
        self.mlp_results = {}
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("涌现临界神经网络验证平台")
        self.setGeometry(100, 100, 1400, 900)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        
        # 左侧控制面板
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel, 1)
        
        # 右侧可视化区域
        self.visualization_widget = RealTimeVisualizationWidget()
        main_layout.addWidget(self.visualization_widget, 3)
        
        # 状态栏
        self.statusBar().showMessage('就绪')
        
    def create_control_panel(self):
        panel = QFrame()
        panel.setFrameStyle(QFrame.Box)
        panel.setMaximumWidth(400)
        
        layout = QVBoxLayout()
        
        # 数据集配置
        dataset_group = QGroupBox("数据集配置")
        dataset_layout = QVBoxLayout()
        
        self.dataset_combo = QComboBox()
        self.dataset_combo.addItems(["合成分类数据", "月亮数据", "团状数据", "自定义数据"])
        dataset_layout.addWidget(QLabel("选择数据集:"))
        dataset_layout.addWidget(self.dataset_combo)
        
        self.samples_spin = QSpinBox()
        self.samples_spin.setRange(100, 10000)
        self.samples_spin.setValue(2000)
        dataset_layout.addWidget(QLabel("样本数量:"))
        dataset_layout.addWidget(self.samples_spin)
        
        self.features_spin = QSpinBox()
        self.features_spin.setRange(2, 100)
        self.features_spin.setValue(20)
        dataset_layout.addWidget(QLabel("特征数量:"))
        dataset_layout.addWidget(self.features_spin)
        
        self.classes_spin = QSpinBox()
        self.classes_spin.setRange(2, 10)
        self.classes_spin.setValue(3)
        dataset_layout.addWidget(QLabel("类别数量:"))
        dataset_layout.addWidget(self.classes_spin)
        
        self.load_data_btn = QPushButton("生成/加载数据")
        self.load_data_btn.clicked.connect(self.load_data)
        dataset_layout.addWidget(self.load_data_btn)
        
        dataset_group.setLayout(dataset_layout)
        layout.addWidget(dataset_group)
        
        # 网络参数配置
        network_group = QGroupBox("网络参数配置")
        network_layout = QGridLayout()
        
        network_layout.addWidget(QLabel("输入层大小:"), 0, 0)
        self.input_spin = QSpinBox()
        self.input_spin.setRange(1, 1000)
        self.input_spin.setValue(20)
        network_layout.addWidget(self.input_spin, 0, 1)
        
        network_layout.addWidget(QLabel("隐藏层1:"), 1, 0)
        self.hidden1_spin = QSpinBox()
        self.hidden1_spin.setRange(1, 500)
        self.hidden1_spin.setValue(64)
        network_layout.addWidget(self.hidden1_spin, 1, 1)
        
        network_layout.addWidget(QLabel("隐藏层2:"), 2, 0)
        self.hidden2_spin = QSpinBox()
        self.hidden2_spin.setRange(0, 500)
        self.hidden2_spin.setValue(32)
        network_layout.addWidget(self.hidden2_spin, 2, 1)
        
        network_layout.addWidget(QLabel("输出层:"), 3, 0)
        self.output_spin = QSpinBox()
        self.output_spin.setRange(1, 100)
        self.output_spin.setValue(3)
        network_layout.addWidget(self.output_spin, 3, 1)
        
        network_layout.addWidget(QLabel("基础激活概率:"), 4, 0)
        self.activation_spin = QDoubleSpinBox()
        self.activation_spin.setRange(0.0001, 0.1)
        self.activation_spin.setValue(0.005)
        self.activation_spin.setSingleStep(0.001)
        network_layout.addWidget(self.activation_spin, 4, 1)
        
        network_layout.addWidget(QLabel("协同参数α:"), 5, 0)
        self.alpha_spin = QDoubleSpinBox()
        self.alpha_spin.setRange(0.01, 1.0)
        self.alpha_spin.setValue(0.1)
        self.alpha_spin.setSingleStep(0.01)
        network_layout.addWidget(self.alpha_spin, 5, 1)
        
        network_layout.addWidget(QLabel("敏感参数β:"), 6, 0)
        self.beta_spin = QDoubleSpinBox()
        self.beta_spin.setRange(0.01, 0.5)
        self.beta_spin.setValue(0.05)
        self.beta_spin.setSingleStep(0.01)
        network_layout.addWidget(self.beta_spin, 6, 1)
        
        network_group.setLayout(network_layout)
        layout.addWidget(network_group)
        
        # 训练配置
        training_group = QGroupBox("训练配置")
        training_layout = QVBoxLayout()
        
        training_layout.addWidget(QLabel("训练轮次:"))
        self.epochs_spin = QSpinBox()
        self.epochs_spin.setRange(10, 1000)
        self.epochs_spin.setValue(100)
        training_layout.addWidget(self.epochs_spin)
        
        training_layout.addWidget(QLabel("批处理大小:"))
        self.batch_spin = QSpinBox()
        self.batch_spin.setRange(1, 128)
        self.batch_spin.setValue(16)
        training_layout.addWidget(self.batch_spin)
        
        training_layout.addWidget(QLabel("学习率:"))
        self.lr_spin = QDoubleSpinBox()
        self.lr_spin.setRange(0.001, 1.0)
        self.lr_spin.setValue(0.1)
        self.lr_spin.setSingleStep(0.01)
        training_layout.addWidget(self.lr_spin)
        
        training_group.setLayout(training_layout)
        layout.addWidget(training_group)
        
        # 操作按钮
        button_layout = QVBoxLayout()
        
        self.train_ecn_btn = QPushButton("训练涌现网络")
        self.train_ecn_btn.clicked.connect(self.train_emergence_network)
        button_layout.addWidget(self.train_ecn_btn)
        
        self.train_mlp_btn = QPushButton("训练传统MLP")
        self.train_mlp_btn.clicked.connect(self.train_mlp)
        button_layout.addWidget(self.train_mlp_btn)
        
        self.analyze_btn = QPushButton("分析涌现特性")
        self.analyze_btn.clicked.connect(self.analyze_emergence)
        button_layout.addWidget(self.analyze_btn)
        
        self.export_btn = QPushButton("导出结果")
        self.export_btn.clicked.connect(self.export_results)
        button_layout.addWidget(self.export_btn)
        
        layout.addLayout(button_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        # 信息显示
        self.info_text = QTextEdit()
        self.info_text.setMaximumHeight(200)
        layout.addWidget(QLabel("训练信息:"))
        layout.addWidget(self.info_text)
        
        layout.addStretch()
        panel.setLayout(layout)
        
        return panel
    
    def load_data(self):
        try:
            dataset_type = self.dataset_combo.currentText()
            n_samples = self.samples_spin.value()
            n_features = self.features_spin.value()
            n_classes = self.classes_spin.value()
            
            if dataset_type == "合成分类数据":
                self.X, self.y = make_classification(
                    n_samples=n_samples,
                    n_features=n_features,
                    n_informative=min(15, n_features),
                    n_redundant=max(0, n_features - 15),
                    n_classes=n_classes,
                    random_state=42
                )
            elif dataset_type == "月亮数据":
                self.X, self.y = make_moons(n_samples=n_samples, noise=0.2, random_state=42)
                n_features = 2
                n_classes = 2
            elif dataset_type == "团状数据":
                self.X, self.y = make_blobs(n_samples=n_samples, n_features=n_features, 
                                          centers=n_classes, random_state=42)
            else:  # 自定义数据
                file_path, _ = QFileDialog.getOpenFileName(self, "选择数据文件")
                if file_path:
                    if file_path.endswith('.csv'):
                        data = pd.read_csv(file_path)
                        self.X = data.iloc[:, :-1].values
                        self.y = data.iloc[:, -1].values
                    else:
                        QMessageBox.warning(self, "错误", "仅支持CSV格式文件")
                        return
            
            # 数据预处理
            scaler = StandardScaler()
            self.X = scaler.fit_transform(self.X)
            self.X = (self.X - self.X.min()) / (self.X.max() - self.X.min())
            
            # 分割数据集
            self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(
                self.X, self.y, test_size=0.2, random_state=42
            )
            
            # 更新网络参数
            self.input_spin.setValue(n_features)
            self.output_spin.setValue(n_classes)
            
            self.info_text.append(f"数据加载成功: {len(self.X_train)}训练样本, {len(self.X_test)}测试样本")
            self.info_text.append(f"特征数: {n_features}, 类别数: {n_classes}")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"数据加载失败: {str(e)}")
    
    def train_emergence_network(self):
        if not hasattr(self, 'X_train'):
            QMessageBox.warning(self, "警告", "请先加载数据")
            return
            
        try:
            # 获取参数
            input_size = self.input_spin.value()
            hidden_sizes = []
            if self.hidden1_spin.value() > 0:
                hidden_sizes.append(self.hidden1_spin.value())
            if self.hidden2_spin.value() > 0:
                hidden_sizes.append(self.hidden2_spin.value())
            output_size = self.output_spin.value()
            base_activation = self.activation_spin.value()
            
            # 创建分类器
            self.classifier = EmergenceCriticalClassifier(
                input_size=input_size,
                hidden_sizes=hidden_sizes,
                output_size=output_size,
                base_activation=base_activation
            )
            
            # 设置学习率
            self.classifier.learning_rate = self.lr_spin.value()
            
            # 创建训练线程
            self.training_thread = TrainingThread(
                self.classifier, self.X_train, self.y_train,
                self.X_test, self.y_test, self.epochs_spin.value()
            )
            
            self.training_thread.finished_signal.connect(self.on_training_finished)
            
            # 禁用按钮
            self.train_ecn_btn.setEnabled(False)
            self.progress_bar.setRange(0, 0)  # 无限进度条
            
            self.info_text.append("开始训练涌现临界网络...")
            self.training_thread.start()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"训练失败: {str(e)}")
    
    def train_mlp(self):
        if not hasattr(self, 'X_train'):
            QMessageBox.warning(self, "警告", "请先加载数据")
            return
            
        try:
            # 获取隐藏层大小
            hidden_layers = []
            if self.hidden1_spin.value() > 0:
                hidden_layers.append(self.hidden1_spin.value())
            if self.hidden2_spin.value() > 0:
                hidden_layers.append(self.hidden2_spin.value())
            
            # 创建传统MLP
            mlp = MLPClassifier(
                hidden_layer_sizes=tuple(hidden_layers),
                max_iter=self.epochs_spin.value(),
                random_state=42
            )
            
            self.info_text.append("开始训练传统MLP...")
            
            # 训练MLP
            mlp.fit(self.X_train, self.y_train)
            
            # 预测
            y_pred_mlp = mlp.predict(self.X_test)
            mlp_accuracy = accuracy_score(self.y_test, y_pred_mlp)
            
            # 保存结果
            self.mlp_results = {
                'accuracy': mlp_accuracy,
                'y_pred_mlp': y_pred_mlp,
                'mlp_accuracies': [mlp_accuracy] * 10  # 简化显示
            }
            
            self.info_text.append(f"传统MLP训练完成，测试准确率: {mlp_accuracy:.4f}")
            
            # 更新对比图
            if hasattr(self, 'ecn_results'):
                self.visualization_widget.update_comparison_plot(
                    self.ecn_results, self.mlp_results, self.X_test, self.y_test
                )
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"MLP训练失败: {str(e)}")
    
    def on_training_finished(self, results):
        # 启用按钮
        self.train_ecn_btn.setEnabled(True)
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(1)
        
        # 保存结果
        self.ecn_results = results
        
        # 更新可视化
        self.visualization_widget.update_training_plot(
            results['losses'], results['accuracies']
        )
        
        # 更新网络结构图
        sample_data = self.X_test[:5] if hasattr(self, 'X_test') else None
        if sample_data is not None and self.classifier is not None:
            self.visualization_widget.update_network_plot(
                self.classifier, sample_data
            )
        
        # 更新涌现分析图
        self.visualization_widget.update_emergence_plot(
            results['emergence_stats']
        )
        
        # 更新对比图（如果MLP已训练）
        if self.mlp_results:
            self.visualization_widget.update_comparison_plot(
                results, self.mlp_results, self.X_test, self.y_test
            )
        
        self.info_text.append(f"涌现网络训练完成，测试准确率: {results['test_accuracy']:.4f}")
        self.info_text.append(f"总学习周期: {self.classifier.network.learning_cycles}")
    
    def analyze_emergence(self):
        if self.classifier is None:
            QMessageBox.warning(self, "警告", "请先训练涌现网络")
            return
            
        try:
            # 随机选择样本进行详细分析
            sample_indices = np.random.choice(len(self.X_test), min(20, len(self.X_test)), replace=False)
            X_sample = self.X_test[sample_indices]
            
            # 分析涌现特性
            emergence_stats = self.classifier.analyze_emergence(X_sample)
            
            # 计算统计信息
            total_connections = 0
            high_synergy_connections = 0
            
            for layer in self.classifier.network.layers:
                for neuron in layer.neurons:
                    for conn_data in neuron.connections.values():
                        total_connections += 1
                        if conn_data['synergy'] > 0.5:
                            high_synergy_connections += 1
            
            connection_efficiency = high_synergy_connections / total_connections if total_connections > 0 else 0
            
            # 显示分析结果
            analysis_text = f"""
涌现特性分析报告:
========================
网络规模: {sum(len(layer.neurons) for layer in self.classifier.network.layers)} 神经元
总连接数: {total_connections}
高协同连接: {high_synergy_connections}
连接效率: {connection_efficiency:.4f}
学习周期: {self.classifier.network.learning_cycles}
最终阈值: {self.classifier.network.global_threshold:.4f}

各层涌现水平:
"""
            for i, layer in enumerate(self.classifier.network.layers):
                analysis_text += f"层 {i}: {layer.layer_emergence:.4f}\n"
            
            self.info_text.append(analysis_text)
            
            # 更新涌现分析图
            self.visualization_widget.update_emergence_plot(emergence_stats)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"分析失败: {str(e)}")
    
    def export_results(self):
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "导出结果", "", "CSV Files (*.csv);;All Files (*)"
            )
            
            if file_path:
                results_data = {}
                
                if hasattr(self, 'ecn_results'):
                    results_data['ECN_Losses'] = self.ecn_results['losses']
                    results_data['ECN_Accuracies'] = self.ecn_results['accuracies']
                    results_data['ECN_Test_Accuracy'] = [self.ecn_results['test_accuracy']]
                
                if self.mlp_results:
                    results_data['MLP_Accuracy'] = [self.mlp_results['accuracy']]
                
                # 确保所有数组长度一致
                max_len = max(len(arr) for arr in results_data.values() if hasattr(arr, '__len__'))
                for key in results_data:
                    if hasattr(results_data[key], '__len__') and len(results_data[key]) < max_len:
                        results_data[key] = list(results_data[key]) + [np.nan] * (max_len - len(results_data[key]))
                
                df = pd.DataFrame(results_data)
                df.to_csv(file_path, index=False)
                
                self.info_text.append(f"结果已导出到: {file_path}")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")

def main():
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = EmergenceCriticalApp()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()