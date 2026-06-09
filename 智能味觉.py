import sys
import os
import numpy as np
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from scipy import stats
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import sqlite3
import json

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTabWidget, QPushButton, QLabel, 
                             QLineEdit, QTextEdit, QTableWidget, QTableWidgetItem,
                             QHeaderView, QFileDialog, QMessageBox, QComboBox,
                             QGroupBox, QSpinBox, QDoubleSpinBox, QCheckBox,
                             QProgressBar, QSplitter, QListWidget, QTreeWidget,
                             QTreeWidgetItem, QDialog, QFormLayout, QDialogButtonBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QIcon, QPixmap, QPalette, QColor


class TasteData:
    """味觉数据类"""
    def __init__(self):
        self.samples = []
        self.features = ['sweetness', 'sourness', 'saltiness', 'bitterness', 'umami']
        self.labels = []
        self.timestamps = []
    
    def add_sample(self, sample_data, label=None, timestamp=None):
        """添加样本数据"""
        if timestamp is None:
            timestamp = datetime.now()
        
        self.samples.append(sample_data)
        self.labels.append(label)
        self.timestamps.append(timestamp)
    
    def to_dataframe(self):
        """转换为DataFrame"""
        data = {
            'timestamp': self.timestamps,
            'label': self.labels
        }
        
        for i, feature in enumerate(self.features):
            data[feature] = [sample[i] for sample in self.samples]
        
        return pd.DataFrame(data)
    
    def from_dataframe(self, df):
        """从DataFrame加载数据"""
        self.samples = []
        self.labels = []
        self.timestamps = []
        
        for _, row in df.iterrows():
            sample = [row[feature] for feature in self.features]
            self.samples.append(sample)
            self.labels.append(row.get('label', ''))
            self.timestamps.append(row.get('timestamp', datetime.now()))


class DataAcquisitionThread(QThread):
    """数据采集线程"""
    data_acquired = pyqtSignal(list)
    acquisition_finished = pyqtSignal()
    
    def __init__(self, duration=10, interval=0.1):
        super().__init__()
        self.duration = duration
        self.interval = interval
        self.is_running = False
    
    def run(self):
        """运行数据采集"""
        self.is_running = True
        start_time = datetime.now()
        
        while self.is_running:
            current_time = datetime.now()
            elapsed = (current_time - start_time).total_seconds()
            
            if elapsed >= self.duration:
                break
            
            # 模拟数据采集 - 实际应用中这里应该连接硬件传感器
            sample = self.simulate_taste_data()
            self.data_acquired.emit(sample)
            
            # 等待指定间隔
            self.msleep(int(self.interval * 1000))
        
        self.acquisition_finished.emit()
    
    def stop(self):
        """停止数据采集"""
        self.is_running = False
    
    def simulate_taste_data(self):
        """模拟味觉数据"""
        # 模拟五种基本味觉的强度值 (0-1)
        return [np.random.random() for _ in range(5)]


class TastePlotCanvas(FigureCanvas):
    """味觉数据绘图画布"""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        
        self.axes = self.fig.add_subplot(111)
        self.fig.tight_layout()
    
    def plot_taste_profile(self, data, labels=None):
        """绘制味觉轮廓图"""
        self.axes.clear()
        
        if len(data) == 0:
            return
        
        # 雷达图显示味觉轮廓
        angles = np.linspace(0, 2*np.pi, 5, endpoint=False).tolist()
        angles += angles[:1]  # 闭合图形
        
        features = ['甜度', '酸度', '咸度', '苦度', '鲜度']
        
        if labels is None:
            labels = [f'样本 {i+1}' for i in range(len(data))]
        
        for i, sample in enumerate(data):
            values = sample.tolist()
            values += values[:1]  # 闭合图形
            self.axes.plot(angles, values, 'o-', linewidth=2, label=labels[i])
            self.axes.fill(angles, values, alpha=0.1)
        
        self.axes.set_xticks(angles[:-1])
        self.axes.set_xticklabels(features)
        self.axes.set_ylim(0, 1)
        self.axes.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
        self.axes.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))
        
        self.draw()
    
    def plot_time_series(self, data, timestamps, features=None):
        """绘制时间序列图"""
        self.axes.clear()
        
        if features is None:
            features = ['甜度', '酸度', '咸度', '苦度', '鲜度']
        
        data = np.array(data)
        
        for i in range(data.shape[1]):
            self.axes.plot(timestamps, data[:, i], marker='o', label=features[i])
        
        self.axes.set_xlabel('时间')
        self.axes.set_ylabel('强度')
        self.axes.legend()
        self.axes.grid(True, linestyle='--', alpha=0.7)
        
        # 格式化时间轴
        plt.setp(self.axes.xaxis.get_majorticklabels(), rotation=45)
        
        self.fig.tight_layout()
        self.draw()
    
    def plot_pca(self, data, labels=None):
        """绘制PCA分析图"""
        self.axes.clear()
        
        if len(data) < 2:
            return
        
        # 标准化数据
        scaler = StandardScaler()
        data_scaled = scaler.fit_transform(data)
        
        # 执行PCA
        pca = PCA(n_components=2)
        principal_components = pca.fit_transform(data_scaled)
        
        # 绘制散点图
        if labels is None:
            self.axes.scatter(principal_components[:, 0], principal_components[:, 1])
        else:
            unique_labels = set(labels)
            for label in unique_labels:
                mask = [l == label for l in labels]
                self.axes.scatter(principal_components[mask, 0], principal_components[mask, 1], label=label)
            self.axes.legend()
        
        self.axes.set_xlabel(f'主成分 1 ({pca.explained_variance_ratio_[0]:.2%})')
        self.axes.set_ylabel(f'主成分 2 ({pca.explained_variance_ratio_[1]:.2%})')
        self.axes.set_title('PCA分析')
        self.axes.grid(True, linestyle='--', alpha=0.7)
        
        self.fig.tight_layout()
        self.draw()


class DataAcquisitionTab(QWidget):
    """数据采集标签页"""
    def __init__(self, taste_data):
        super().__init__()
        self.taste_data = taste_data
        self.acquisition_thread = None
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        
        # 控制面板
        control_group = QGroupBox("数据采集控制")
        control_layout = QHBoxLayout()
        
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 3600)
        self.duration_spin.setValue(10)
        self.duration_spin.setSuffix(" 秒")
        
        self.interval_spin = QDoubleSpinBox()
        self.interval_spin.setRange(0.01, 10.0)
        self.interval_spin.setValue(0.1)
        self.interval_spin.setSuffix(" 秒")
        
        self.sample_label_edit = QLineEdit()
        self.sample_label_edit.setPlaceholderText("样本标签")
        
        self.start_btn = QPushButton("开始采集")
        self.stop_btn = QPushButton("停止采集")
        self.stop_btn.setEnabled(False)
        
        control_layout.addWidget(QLabel("采集时长:"))
        control_layout.addWidget(self.duration_spin)
        control_layout.addWidget(QLabel("采样间隔:"))
        control_layout.addWidget(self.interval_spin)
        control_layout.addWidget(QLabel("样本标签:"))
        control_layout.addWidget(self.sample_label_edit)
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)
        control_layout.addStretch()
        
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)
        
        # 进度条
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        # 实时图表
        self.plot_canvas = TastePlotCanvas(self, width=8, height=4)
        layout.addWidget(self.plot_canvas)
        
        # 数据表格
        self.data_table = QTableWidget()
        self.data_table.setColumnCount(7)
        self.data_table.setHorizontalHeaderLabels(['时间', '标签', '甜度', '酸度', '咸度', '苦度', '鲜度'])
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.data_table)
        
        # 连接信号
        self.start_btn.clicked.connect(self.start_acquisition)
        self.stop_btn.clicked.connect(self.stop_acquisition)
        
        self.setLayout(layout)
    
    def start_acquisition(self):
        """开始数据采集"""
        duration = self.duration_spin.value()
        interval = self.interval_spin.value()
        label = self.sample_label_edit.text().strip() or f"样本_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.acquisition_thread = DataAcquisitionThread(duration, interval)
        self.acquisition_thread.data_acquired.connect(self.on_data_acquired)
        self.acquisition_thread.acquisition_finished.connect(self.on_acquisition_finished)
        
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setRange(0, duration)
        self.progress_bar.setValue(0)
        
        # 清空当前数据
        self.current_data = []
        self.current_timestamps = []
        
        self.acquisition_thread.start()
    
    def stop_acquisition(self):
        """停止数据采集"""
        if self.acquisition_thread and self.acquisition_thread.isRunning():
            self.acquisition_thread.stop()
            self.acquisition_thread.wait()
    
    def on_data_acquired(self, sample):
        """处理采集到的数据"""
        timestamp = datetime.now()
        label = self.sample_label_edit.text().strip() or f"样本_{timestamp.strftime('%Y%m%d_%H%M%S')}"
        
        # 添加到数据集中
        self.taste_data.add_sample(sample, label, timestamp)
        
        # 更新实时图表
        self.current_data.append(sample)
        self.current_timestamps.append(timestamp)
        self.plot_canvas.plot_time_series(self.current_data, self.current_timestamps)
        
        # 更新数据表格
        row = self.data_table.rowCount()
        self.data_table.insertRow(row)
        
        self.data_table.setItem(row, 0, QTableWidgetItem(timestamp.strftime("%H:%M:%S")))
        self.data_table.setItem(row, 1, QTableWidgetItem(label))
        for i, value in enumerate(sample):
            self.data_table.setItem(row, i+2, QTableWidgetItem(f"{value:.3f}"))
        
        # 滚动到最新行
        self.data_table.scrollToItem(self.data_table.item(row, 0))
        
        # 更新进度条
        elapsed = (timestamp - self.current_timestamps[0]).total_seconds()
        self.progress_bar.setValue(int(elapsed))
    
    def on_acquisition_finished(self):
        """采集完成处理"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setValue(self.progress_bar.maximum())


class DataAnalysisTab(QWidget):
    """数据分析标签页"""
    def __init__(self, taste_data):
        super().__init__()
        self.taste_data = taste_data
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        
        # 分析控制面板
        analysis_control = QGroupBox("分析选项")
        analysis_layout = QHBoxLayout()
        
        self.analysis_type = QComboBox()
        self.analysis_type.addItems(["味觉轮廓", "PCA分析", "聚类分析", "统计分析"])
        
        self.cluster_count = QSpinBox()
        self.cluster_count.setRange(2, 10)
        self.cluster_count.setValue(3)
        
        self.analyze_btn = QPushButton("执行分析")
        
        analysis_layout.addWidget(QLabel("分析类型:"))
        analysis_layout.addWidget(self.analysis_type)
        analysis_layout.addWidget(QLabel("聚类数量:"))
        analysis_layout.addWidget(self.cluster_count)
        analysis_layout.addWidget(self.analyze_btn)
        analysis_layout.addStretch()
        
        analysis_control.setLayout(analysis_layout)
        layout.addWidget(analysis_control)
        
        # 图表区域
        self.plot_canvas = TastePlotCanvas(self, width=8, height=6)
        layout.addWidget(self.plot_canvas)
        
        # 分析结果区域
        self.result_text = QTextEdit()
        self.result_text.setMaximumHeight(200)
        layout.addWidget(self.result_text)
        
        # 连接信号
        self.analyze_btn.clicked.connect(self.perform_analysis)
        
        self.setLayout(layout)
    
    def perform_analysis(self):
        """执行分析"""
        if len(self.taste_data.samples) == 0:
            QMessageBox.warning(self, "警告", "没有可分析的数据")
            return
        
        analysis_type = self.analysis_type.currentText()
        
        try:
            if analysis_type == "味觉轮廓":
                self.plot_taste_profile()
            elif analysis_type == "PCA分析":
                self.plot_pca_analysis()
            elif analysis_type == "聚类分析":
                self.perform_clustering()
            elif analysis_type == "统计分析":
                self.perform_statistical_analysis()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"分析过程中出现错误: {str(e)}")
    
    def plot_taste_profile(self):
        """绘制味觉轮廓"""
        data = np.array(self.taste_data.samples)
        labels = self.taste_data.labels
        
        # 计算每个标签的平均轮廓
        unique_labels = list(set(labels))
        avg_profiles = []
        avg_labels = []
        
        for label in unique_labels:
            mask = [l == label for l in labels]
            if sum(mask) > 0:
                avg_profile = np.mean(data[mask], axis=0)
                avg_profiles.append(avg_profile)
                avg_labels.append(f"{label} (平均)")
        
        self.plot_canvas.plot_taste_profile(avg_profiles, avg_labels)
        
        # 显示结果
        result = "味觉轮廓分析完成\n\n"
        for i, label in enumerate(unique_labels):
            result += f"{label}: {avg_profiles[i]}\n"
        
        self.result_text.setText(result)
    
    def plot_pca_analysis(self):
        """执行PCA分析"""
        data = np.array(self.taste_data.samples)
        labels = self.taste_data.labels
        
        self.plot_canvas.plot_pca(data, labels)
        
        # 执行PCA计算
        scaler = StandardScaler()
        data_scaled = scaler.fit_transform(data)
        
        pca = PCA(n_components=2)
        principal_components = pca.fit_transform(data_scaled)
        
        result = f"PCA分析完成\n"
        result += f"主成分1解释方差: {pca.explained_variance_ratio_[0]:.2%}\n"
        result += f"主成分2解释方差: {pca.explained_variance_ratio_[1]:.2%}\n"
        result += f"累计解释方差: {sum(pca.explained_variance_ratio_):.2%}\n"
        
        self.result_text.setText(result)
    
    def perform_clustering(self):
        """执行聚类分析"""
        data = np.array(self.taste_data.samples)
        n_clusters = self.cluster_count.value()
        
        # 标准化数据
        scaler = StandardScaler()
        data_scaled = scaler.fit_transform(data)
        
        # 执行K-means聚类
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        cluster_labels = kmeans.fit_predict(data_scaled)
        
        # 绘制PCA图，用聚类结果着色
        self.plot_canvas.plot_pca(data, cluster_labels)
        
        # 显示聚类结果
        result = f"聚类分析完成 (K={n_clusters})\n\n"
        result += f"聚类中心:\n"
        
        # 将聚类中心转换回原始尺度
        cluster_centers = scaler.inverse_transform(kmeans.cluster_centers_)
        
        for i, center in enumerate(cluster_centers):
            result += f"聚类 {i+1}: {center}\n"
        
        result += f"\n样本分布:\n"
        for i in range(n_clusters):
            count = sum(cluster_labels == i)
            result += f"聚类 {i+1}: {count} 个样本\n"
        
        self.result_text.setText(result)
    
    def perform_statistical_analysis(self):
        """执行统计分析"""
        data = np.array(self.taste_data.samples)
        features = ['甜度', '酸度', '咸度', '苦度', '鲜度']
        
        result = "统计分析结果\n\n"
        result += "描述性统计:\n"
        
        # 计算基本统计量
        stats_df = pd.DataFrame(data, columns=features)
        desc_stats = stats_df.describe()
        
        for feature in features:
            result += f"{feature}:\n"
            result += f"  平均值: {desc_stats[feature]['mean']:.3f}\n"
            result += f"  标准差: {desc_stats[feature]['std']:.3f}\n"
            result += f"  最小值: {desc_stats[feature]['min']:.3f}\n"
            result += f"  最大值: {desc_stats[feature]['max']:.3f}\n\n"
        
        # 计算相关性矩阵
        corr_matrix = stats_df.corr()
        result += "相关性矩阵:\n"
        result += corr_matrix.to_string()
        
        self.result_text.setText(result)
        
        # 绘制相关性热图
        self.plot_correlation_heatmap(corr_matrix)
    
    def plot_correlation_heatmap(self, corr_matrix):
        """绘制相关性热图"""
        self.plot_canvas.axes.clear()
        
        im = self.plot_canvas.axes.matshow(corr_matrix, cmap='coolwarm', vmin=-1, vmax=1)
        
        # 添加颜色条
        self.plot_canvas.fig.colorbar(im, ax=self.plot_canvas.axes)
        
        # 设置刻度标签
        features = ['甜度', '酸度', '咸度', '苦度', '鲜度']
        ticks = np.arange(len(features))
        self.plot_canvas.axes.set_xticks(ticks)
        self.plot_canvas.axes.set_yticks(ticks)
        self.plot_canvas.axes.set_xticklabels(features)
        self.plot_canvas.axes.set_yticklabels(features)
        
        # 添加数值标注
        for i in range(len(features)):
            for j in range(len(features)):
                text = self.plot_canvas.axes.text(j, i, f'{corr_matrix.iloc[i, j]:.2f}',
                                                 ha="center", va="center", color="w")
        
        self.plot_canvas.axes.set_title("味觉特征相关性热图")
        self.plot_canvas.draw()


class DataManagementTab(QWidget):
    """数据管理标签页"""
    def __init__(self, taste_data):
        super().__init__()
        self.taste_data = taste_data
        self.current_file = None
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        
        # 文件操作面板
        file_group = QGroupBox("文件操作")
        file_layout = QHBoxLayout()
        
        self.new_btn = QPushButton("新建")
        self.open_btn = QPushButton("打开")
        self.save_btn = QPushButton("保存")
        self.save_as_btn = QPushButton("另存为")
        self.export_btn = QPushButton("导出报告")
        
        file_layout.addWidget(self.new_btn)
        file_layout.addWidget(self.open_btn)
        file_layout.addWidget(self.save_btn)
        file_layout.addWidget(self.save_as_btn)
        file_layout.addWidget(self.export_btn)
        file_layout.addStretch()
        
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # 数据表格
        self.data_table = QTableWidget()
        self.data_table.setColumnCount(7)
        self.data_table.setHorizontalHeaderLabels(['时间', '标签', '甜度', '酸度', '咸度', '苦度', '鲜度'])
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.data_table)
        
        # 连接信号
        self.new_btn.clicked.connect(self.new_file)
        self.open_btn.clicked.connect(self.open_file)
        self.save_btn.clicked.connect(self.save_file)
        self.save_as_btn.clicked.connect(self.save_as_file)
        self.export_btn.clicked.connect(self.export_report)
        
        self.setLayout(layout)
        
        # 更新表格显示
        self.update_table()
    
    def update_table(self):
        """更新数据表格"""
        self.data_table.setRowCount(0)
        
        for i, (sample, label, timestamp) in enumerate(zip(
            self.taste_data.samples, self.taste_data.labels, self.taste_data.timestamps)):
            
            self.data_table.insertRow(i)
            self.data_table.setItem(i, 0, QTableWidgetItem(timestamp.strftime("%Y-%m-%d %H:%M:%S")))
            self.data_table.setItem(i, 1, QTableWidgetItem(label))
            
            for j, value in enumerate(sample):
                self.data_table.setItem(i, j+2, QTableWidgetItem(f"{value:.3f}"))
    
    def new_file(self):
        """新建文件"""
        if len(self.taste_data.samples) > 0:
            reply = QMessageBox.question(self, "确认", "当前数据将被清除，是否继续?",
                                        QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.No:
                return
        
        self.taste_data = TasteData()
        self.current_file = None
        self.update_table()
        QMessageBox.information(self, "成功", "已创建新文件")
    
    def open_file(self):
        """打开文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开数据文件", "", "CSV文件 (*.csv);;JSON文件 (*.json);;所有文件 (*)")
        
        if file_path:
            try:
                if file_path.endswith('.csv'):
                    df = pd.read_csv(file_path)
                elif file_path.endswith('.json'):
                    df = pd.read_json(file_path)
                else:
                    QMessageBox.warning(self, "警告", "不支持的文件格式")
                    return
                
                self.taste_data.from_dataframe(df)
                self.current_file = file_path
                self.update_table()
                QMessageBox.information(self, "成功", f"已打开文件: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"打开文件失败: {str(e)}")
    
    def save_file(self):
        """保存文件"""
        if self.current_file is None:
            self.save_as_file()
        else:
            self._save_to_file(self.current_file)
    
    def save_as_file(self):
        """另存为文件"""
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self, "保存数据文件", "", "CSV文件 (*.csv);;JSON文件 (*.json)")
        
        if file_path:
            self._save_to_file(file_path, selected_filter)
            self.current_file = file_path
    
    def _save_to_file(self, file_path, file_type=None):
        """保存数据到文件"""
        try:
            df = self.taste_data.to_dataframe()
            
            if file_path.endswith('.csv') or (file_type and 'CSV' in file_type):
                df.to_csv(file_path, index=False)
            elif file_path.endswith('.json') or (file_type and 'JSON' in file_type):
                df.to_json(file_path, indent=2, orient='records')
            else:
                # 默认保存为CSV
                df.to_csv(file_path, index=False)
            
            QMessageBox.information(self, "成功", f"文件已保存: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存文件失败: {str(e)}")
    
    def export_report(self):
        """导出分析报告"""
        if len(self.taste_data.samples) == 0:
            QMessageBox.warning(self, "警告", "没有数据可导出")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出报告", "味觉分析报告.html", "HTML文件 (*.html)")
        
        if file_path:
            try:
                self.generate_html_report(file_path)
                QMessageBox.information(self, "成功", f"报告已导出: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出报告失败: {str(e)}")
    
    def generate_html_report(self, file_path):
        """生成HTML报告"""
        df = self.taste_data.to_dataframe()
        
        # 基本统计
        stats_html = df.describe().to_html(classes='table table-striped')
        
        # 生成报告HTML
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>味觉分析报告</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2 {{ color: #2c3e50; }}
                .table {{ border-collapse: collapse; width: 100%; }}
                .table th, .table td {{ border: 1px solid #ddd; padding: 8px; }}
                .table th {{ background-color: #f2f2f2; }}
                .table-striped tr:nth-child(even) {{ background-color: #f9f9f9; }}
            </style>
        </head>
        <body>
            <h1>智能味觉系统分析报告</h1>
            <p>生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            
            <h2>数据概览</h2>
            <p>总样本数: {len(df)}</p>
            <p>采集时间范围: {df['timestamp'].min()} 到 {df['timestamp'].max()}</p>
            
            <h2>描述性统计</h2>
            {stats_html}
            
            <h2>样本数据</h2>
            {df.to_html(classes='table table-striped', index=False)}
        </body>
        </html>
        """
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)


class SmartTasteSystem(QMainWindow):
    """智能味觉系统主窗口"""
    def __init__(self):
        super().__init__()
        self.taste_data = TasteData()
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("智能味觉分析系统")
        self.setGeometry(100, 100, 1200, 800)
        
        # 设置应用图标
        self.setWindowIcon(QIcon(self.create_icon()))
        
        # 创建中心部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 创建标签页
        self.tabs = QTabWidget()
        
        # 添加各个标签页
        self.acquisition_tab = DataAcquisitionTab(self.taste_data)
        self.analysis_tab = DataAnalysisTab(self.taste_data)
        self.management_tab = DataManagementTab(self.taste_data)
        
        self.tabs.addTab(self.acquisition_tab, "数据采集")
        self.tabs.addTab(self.analysis_tab, "数据分析")
        self.tabs.addTab(self.management_tab, "数据管理")
        
        layout.addWidget(self.tabs)
        
        # 状态栏
        self.statusBar().showMessage("就绪")
        
        # 应用样式
        self.apply_stylesheet()
    
    def create_icon(self):
        """创建应用图标（简单的味觉相关图标）"""
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)
        
        # 这里可以创建一个更复杂的图标，但为了简单起见，我们使用文本
        # 在实际应用中，应该使用专业的图标
        return pixmap
    
    def apply_stylesheet(self):
        """应用样式表"""
        style = """
        QMainWindow {
            background-color: #f0f0f0;
        }
        QTabWidget::pane {
            border: 1px solid #C2C7CB;
            background-color: white;
        }
        QTabBar::tab {
            background-color: #E1E1E1;
            border: 1px solid #C4C4C3;
            padding: 8px 20px;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background-color: #FFFFFF;
            border-bottom-color: #FFFFFF;
        }
        QGroupBox {
            font-weight: bold;
            border: 1px solid #C4C4C3;
            border-radius: 4px;
            margin-top: 1ex;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        QPushButton {
            background-color: #4CAF50;
            border: none;
            color: white;
            padding: 8px 16px;
            text-align: center;
            text-decoration: none;
            font-size: 14px;
            margin: 4px 2px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #45a049;
        }
        QPushButton:pressed {
            background-color: #3d8b40;
        }
        QTableWidget {
            gridline-color: #d0d0d0;
            selection-background-color: #4CAF50;
        }
        QHeaderView::section {
            background-color: #f0f0f0;
            padding: 4px;
            border: 1px solid #d0d0d0;
        }
        """
        self.setStyleSheet(style)
    
    def closeEvent(self, event):
        """关闭事件处理"""
        if len(self.taste_data.samples) > 0:
            reply = QMessageBox.question(
                self, "确认退出", 
                "有未保存的数据，是否确定退出?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            
            if reply == QMessageBox.Save:
                self.management_tab.save_file()
                event.accept()
            elif reply == QMessageBox.Discard:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用信息
    app.setApplicationName("智能味觉分析系统")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("味觉科技")
    
    # 创建并显示主窗口
    window = SmartTasteSystem()
    window.show()
    
    # 运行应用
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()