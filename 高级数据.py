import sys
import numpy as np
import pandas as pd
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
import pyqtgraph as pg
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
import plotly.graph_objects as go
from plotly.offline import plot
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import seaborn as sns
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# 设置样式
pg.setConfigOptions(antialias=True)
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")


class MplCanvas(FigureCanvas):
    """Matplotlib画布封装"""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super(MplCanvas, self).__init__(self.fig)
        self.setParent(parent)


class AdvancedVisualizationTool(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.data = None
        self.initUI()
        
    def initUI(self):
        """初始化用户界面"""
        self.setWindowTitle("CHRO - 高级数据可视化工具")
        self.setGeometry(100, 100, 1600, 900)
        
        # 创建中央部件和主布局
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QHBoxLayout(central_widget)
        
        # 创建左侧控制面板
        control_panel = QtWidgets.QWidget()
        control_panel.setMaximumWidth(300)
        control_layout = QtWidgets.QVBoxLayout(control_panel)
        
        # 数据加载部分
        data_group = QtWidgets.QGroupBox("数据管理")
        data_layout = QtWidgets.QVBoxLayout(data_group)
        
        self.load_btn = QtWidgets.QPushButton("加载数据")
        self.load_btn.clicked.connect(self.load_data)
        data_layout.addWidget(self.load_btn)
        
        self.generate_btn = QtWidgets.QPushButton("生成示例数据")
        self.generate_btn.clicked.connect(self.generate_sample_data)
        data_layout.addWidget(self.generate_btn)
        
        # 可视化选项
        viz_group = QtWidgets.QGroupBox("可视化选项")
        viz_layout = QtWidgets.QVBoxLayout(viz_group)
        
        self.viz_combo = QtWidgets.QComboBox()
        self.viz_combo.addItems([
            "散点图矩阵", 
            "3D散点图", 
            "平行坐标图", 
            "热力图", 
            "小提琴图", 
            "PCA降维", 
            "t-SNE降维",
            "交互式3D图"
        ])
        viz_layout.addWidget(self.viz_combo)
        
        self.viz_btn = QtWidgets.QPushButton("生成可视化")
        self.viz_btn.clicked.connect(self.update_visualization)
        viz_layout.addWidget(self.viz_btn)
        
        # 图表控制
        control_group = QtWidgets.QGroupBox("图表控制")
        control_ctrl_layout = QtWidgets.QVBoxLayout(control_group)
        
        self.color_combo = QtWidgets.QComboBox()
        control_ctrl_layout.addWidget(QtWidgets.QLabel("颜色映射:"))
        control_ctrl_layout.addWidget(self.color_combo)
        
        self.size_slider = QtWidgets.QSlider(Qt.Horizontal)
        self.size_slider.setRange(1, 20)
        self.size_slider.setValue(5)
        control_ctrl_layout.addWidget(QtWidgets.QLabel("点大小:"))
        control_ctrl_layout.addWidget(self.size_slider)
        
        self.alpha_slider = QtWidgets.QSlider(Qt.Horizontal)
        self.alpha_slider.setRange(1, 10)
        self.alpha_slider.setValue(7)
        control_ctrl_layout.addWidget(QtWidgets.QLabel("透明度:"))
        control_ctrl_layout.addWidget(self.alpha_slider)
        
        # 添加到控制面板
        control_layout.addWidget(data_group)
        control_layout.addWidget(viz_group)
        control_layout.addWidget(control_group)
        control_layout.addStretch()
        
        # 创建右侧可视化区域
        self.viz_area = QtWidgets.QTabWidget()
        
        # 添加到主布局
        layout.addWidget(control_panel)
        layout.addWidget(self.viz_area, 1)
        
        # 状态栏
        self.statusBar().showMessage("就绪")
        
    def load_data(self):
        """加载数据文件"""
        options = QtWidgets.QFileDialog.Options()
        file_name, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "打开数据文件", "", 
            "CSV文件 (*.csv);;Excel文件 (*.xlsx);;所有文件 (*)", 
            options=options
        )
        
        if file_name:
            try:
                if file_name.endswith('.csv'):
                    self.data = pd.read_csv(file_name)
                else:
                    self.data = pd.read_excel(file_name)
                
                self.statusBar().showMessage(f"已加载数据: {file_name}")
                self.update_data_info()
                
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "错误", f"加载数据时出错: {str(e)}")
    
    def generate_sample_data(self):
        """生成示例数据"""
        np.random.seed(42)
        n_samples = 300
        
        # 创建多元正态分布数据
        mean = [0, 0, 0]
        cov = [[1, 0.8, 0.5], [0.8, 1, 0.3], [0.5, 0.3, 1]]
        data1 = np.random.multivariate_normal(mean, cov, n_samples)
        
        mean = [3, 3, 3]
        cov = [[1, -0.6, 0.4], [-0.6, 1, -0.2], [0.4, -0.2, 1]]
        data2 = np.random.multivariate_normal(mean, cov, n_samples)
        
        # 创建分类特征
        categories = np.random.choice(['A', 'B', 'C'], n_samples*2)
        
        # 组合数据
        data = np.vstack([data1, data2])
        self.data = pd.DataFrame(data, columns=['特征1', '特征2', '特征3'])
        self.data['类别'] = categories
        self.data['数值特征'] = np.random.randn(n_samples*2) * 0.5 + 2
        
        self.statusBar().showMessage("已生成示例数据")
        self.update_data_info()
    
    def update_data_info(self):
        """更新数据信息并填充控制选项"""
        if self.data is not None:
            # 更新颜色映射选项
            self.color_combo.clear()
            self.color_combo.addItems(["无"] + list(self.data.select_dtypes(include=['object', 'category']).columns))
            
            # 显示数据基本信息
            info_text = f"数据集形状: {self.data.shape}\n\n列信息:\n"
            for col in self.data.columns:
                info_text += f"{col} ({self.data[col].dtype})\n"
            
            info_dialog = QtWidgets.QDialog(self)
            info_dialog.setWindowTitle("数据信息")
            layout = QtWidgets.QVBoxLayout(info_dialog)
            text_edit = QtWidgets.QTextEdit()
            text_edit.setPlainText(info_text)
            layout.addWidget(text_edit)
            info_dialog.exec_()
    
    def update_visualization(self):
        """根据选择更新可视化"""
        if self.data is None:
            QtWidgets.QMessageBox.warning(self, "警告", "请先加载或生成数据")
            return
        
        viz_type = self.viz_combo.currentText()
        
        # 清除之前的可视化
        self.viz_area.clear()
        
        # 根据选择创建不同的可视化
        if viz_type == "散点图矩阵":
            self.create_scatter_matrix()
        elif viz_type == "3D散点图":
            self.create_3d_scatter()
        elif viz_type == "平行坐标图":
            self.create_parallel_coordinates()
        elif viz_type == "热力图":
            self.create_heatmap()
        elif viz_type == "小提琴图":
            self.create_violin_plot()
        elif viz_type == "PCA降维":
            self.create_pca_visualization()
        elif viz_type == "t-SNE降维":
            self.create_tsne_visualization()
        elif viz_type == "交互式3D图":
            self.create_interactive_3d()
    
    def create_scatter_matrix(self):
        """创建散点图矩阵"""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        
        # 选择数值列
        numeric_cols = self.data.select_dtypes(include=[np.number]).columns.tolist()
        if len(numeric_cols) < 2:
            QtWidgets.QMessageBox.warning(self, "警告", "需要至少两个数值列")
            return
        
        # 创建matplotlib图形
        canvas = MplCanvas(width=10, height=8, dpi=100)
        layout.addWidget(canvas)
        
        # 获取颜色映射
        color_by = self.color_combo.currentText() if self.color_combo.currentText() != "无" else None
        
        # 绘制散点图矩阵
        if color_by and color_by in self.data.columns:
            g = sns.pairplot(self.data, vars=numeric_cols[:4], hue=color_by)
            g._legend.set_bbox_to_anchor((0.7, 0.7))
        else:
            g = sns.pairplot(self.data, vars=numeric_cols[:4])
        
        # 复制图形到我们的画布
        canvas.fig = g.fig
        canvas.draw()
        
        self.viz_area.addTab(tab, "散点图矩阵")
    
    def create_3d_scatter(self):
        """创建3D散点图"""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        
        # 选择数值列
        numeric_cols = self.data.select_dtypes(include=[np.number]).columns.tolist()
        if len(numeric_cols) < 3:
            QtWidgets.QMessageBox.warning(self, "警告", "需要至少三个数值列")
            return
        
        # 创建matplotlib图形
        canvas = MplCanvas(width=8, height=6, dpi=100)
        layout.addWidget(canvas)
        
        # 创建3D散点图
        ax = canvas.fig.add_subplot(111, projection='3d')
        
        # 获取颜色映射
        color_by = self.color_combo.currentText() if self.color_combo.currentText() != "无" else None
        
        # 设置颜色
        if color_by and color_by in self.data.columns:
            unique_categories = self.data[color_by].unique()
            colors = plt.cm.tab10(np.linspace(0, 1, len(unique_categories)))
            color_map = dict(zip(unique_categories, colors))
            
            for category in unique_categories:
                subset = self.data[self.data[color_by] == category]
                ax.scatter(
                    subset[numeric_cols[0]], 
                    subset[numeric_cols[1]], 
                    subset[numeric_cols[2]],
                    label=category,
                    alpha=self.alpha_slider.value()/10,
                    s=self.size_slider.value()*10
                )
            ax.legend()
        else:
            ax.scatter(
                self.data[numeric_cols[0]], 
                self.data[numeric_cols[1]], 
                self.data[numeric_cols[2]],
                alpha=self.alpha_slider.value()/10,
                s=self.size_slider.value()*10,
                c=self.data.get(numeric_cols[3], 1) if len(numeric_cols) > 3 else 1,
                cmap='viridis'
            )
        
        ax.set_xlabel(numeric_cols[0])
        ax.set_ylabel(numeric_cols[1])
        ax.set_zlabel(numeric_cols[2])
        ax.set_title("3D散点图")
        
        canvas.draw()
        self.viz_area.addTab(tab, "3D散点图")
    
    def create_parallel_coordinates(self):
        """创建平行坐标图"""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        
        # 选择数值列
        numeric_cols = self.data.select_dtypes(include=[np.number]).columns.tolist()
        if len(numeric_cols) < 2:
            QtWidgets.QMessageBox.warning(self, "警告", "需要至少两个数值列")
            return
        
        # 创建matplotlib图形
        canvas = MplCanvas(width=10, height=6, dpi=100)
        layout.addWidget(canvas)
        
        # 获取颜色映射
        color_by = self.color_combo.currentText() if self.color_combo.currentText() != "无" else None
        
        # 创建平行坐标图
        if color_by and color_by in self.data.columns:
            pd.plotting.parallel_coordinates(
                self.data, 
                color_by, 
                cols=numeric_cols[:4],
                ax=canvas.axes
            )
        else:
            # 如果没有颜色映射，使用第一个数值列作为颜色
            self.data['temp_color'] = pd.qcut(self.data[numeric_cols[0]], 5, labels=False)
            pd.plotting.parallel_coordinates(
                self.data, 
                'temp_color', 
                cols=numeric_cols[:4],
                ax=canvas.axes
            )
        
        canvas.axes.legend_.remove()
        canvas.axes.set_title("平行坐标图")
        canvas.draw()
        
        self.viz_area.addTab(tab, "平行坐标图")
    
    def create_heatmap(self):
        """创建热力图"""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        
        # 选择数值列
        numeric_cols = self.data.select_dtypes(include=[np.number]).columns.tolist()
        if len(numeric_cols) < 2:
            QtWidgets.QMessageBox.warning(self, "警告", "需要至少两个数值列")
            return
        
        # 创建matplotlib图形
        canvas = MplCanvas(width=8, height=6, dpi=100)
        layout.addWidget(canvas)
        
        # 计算相关性矩阵
        corr = self.data[numeric_cols].corr()
        
        # 创建热力图
        sns.heatmap(corr, annot=True, cmap='coolwarm', center=0, ax=canvas.axes)
        canvas.axes.set_title("特征相关性热力图")
        canvas.draw()
        
        self.viz_area.addTab(tab, "热力图")
    
    def create_violin_plot(self):
        """创建小提琴图"""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        
        # 选择数值列和分类列
        numeric_cols = self.data.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = self.data.select_dtypes(include=['object', 'category']).columns.tolist()
        
        if not numeric_cols or not categorical_cols:
            QtWidgets.QMessageBox.warning(self, "警告", "需要至少一个数值列和一个分类列")
            return
        
        # 创建matplotlib图形
        canvas = MplCanvas(width=8, height=6, dpi=100)
        layout.addWidget(canvas)
        
        # 创建小提琴图
        sns.violinplot(
            x=categorical_cols[0], 
            y=numeric_cols[0], 
            data=self.data, 
            ax=canvas.axes
        )
        canvas.axes.set_title("小提琴图")
        canvas.draw()
        
        self.viz_area.addTab(tab, "小提琴图")
    
    def create_pca_visualization(self):
        """创建PCA降维可视化"""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        
        # 选择数值列
        numeric_cols = self.data.select_dtypes(include=[np.number]).columns.tolist()
        if len(numeric_cols) < 2:
            QtWidgets.QMessageBox.warning(self, "警告", "需要至少两个数值列")
            return
        
        # 创建matplotlib图形
        canvas = MplCanvas(width=8, height=6, dpi=100)
        layout.addWidget(canvas)
        
        # 执行PCA
        pca = PCA(n_components=2)
        X = self.data[numeric_cols].fillna(self.data[numeric_cols].mean())
        X_pca = pca.fit_transform(X)
        
        # 获取颜色映射
        color_by = self.color_combo.currentText() if self.color_combo.currentText() != "无" else None
        
        # 绘制PCA结果
        if color_by and color_by in self.data.columns:
            unique_categories = self.data[color_by].unique()
            colors = plt.cm.tab10(np.linspace(0, 1, len(unique_categories)))
            
            for i, category in enumerate(unique_categories):
                mask = self.data[color_by] == category
                canvas.axes.scatter(
                    X_pca[mask, 0], 
                    X_pca[mask, 1],
                    label=category,
                    alpha=self.alpha_slider.value()/10,
                    s=self.size_slider.value()*10,
                    color=colors[i]
                )
            canvas.axes.legend()
        else:
            canvas.axes.scatter(
                X_pca[:, 0], 
                X_pca[:, 1],
                alpha=self.alpha_slider.value()/10,
                s=self.size_slider.value()*10,
                c=X[numeric_cols[0]] if len(numeric_cols) > 0 else 1,  # 修复这里
                cmap='viridis'
            )
        
        canvas.axes.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]:.2%}方差)")
        canvas.axes.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]:.2%}方差)")
        canvas.axes.set_title("PCA降维可视化")
        canvas.draw()
        
        self.viz_area.addTab(tab, "PCA降维")
    
    def create_tsne_visualization(self):
        """创建t-SNE降维可视化"""
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        
        # 选择数值列
        numeric_cols = self.data.select_dtypes(include=[np.number]).columns.tolist()
        if len(numeric_cols) < 2:
            QtWidgets.QMessageBox.warning(self, "警告", "需要至少两个数值列")
            return
        
        # 创建matplotlib图形
        canvas = MplCanvas(width=8, height=6, dpi=100)
        layout.addWidget(canvas)
        
        # 执行t-SNE
        tsne = TSNE(n_components=2, random_state=42, perplexity=30)
        X = self.data[numeric_cols].fillna(self.data[numeric_cols].mean())
        X_tsne = tsne.fit_transform(X)
        
        # 获取颜色映射
        color_by = self.color_combo.currentText() if self.color_combo.currentText() != "无" else None
        
        # 绘制t-SNE结果
        if color_by and color_by in self.data.columns:
            unique_categories = self.data[color_by].unique()
            colors = plt.cm.tab10(np.linspace(0, 1, len(unique_categories)))
            
            for i, category in enumerate(unique_categories):
                mask = self.data[color_by] == category
                canvas.axes.scatter(
                    X_tsne[mask, 0], 
                    X_tsne[mask, 1],
                    label=category,
                    alpha=self.alpha_slider.value()/10,
                    s=self.size_slider.value()*10,
                    color=colors[i]
                )
            canvas.axes.legend()
        else:
            canvas.axes.scatter(
                X_tsne[:, 0], 
                X_tsne[:, 1],
                alpha=self.alpha_slider.value()/10,
                s=self.size_slider.value()*10,
                c=X[numeric_cols[0]] if len(numeric_cols) > 0 else 1,  # 修复这里
                cmap='viridis'
            )
        
        canvas.axes.set_xlabel("t-SNE维度1")
        canvas.axes.set_ylabel("t-SNE维度2")
        canvas.axes.set_title("t-SNE降维可视化")
        canvas.draw()
        
        self.viz_area.addTab(tab, "t-SNE降维")
        
    def create_interactive_3d(self):
        """创建交互式3D图（使用Plotly）"""
        # 选择数值列
        numeric_cols = self.data.select_dtypes(include=[np.number]).columns.tolist()
        if len(numeric_cols) < 3:
            QtWidgets.QMessageBox.warning(self, "警告", "需要至少三个数值列")
            return
        
        # 获取颜色映射
        color_by = self.color_combo.currentText() if self.color_combo.currentText() != "无" else None
        
        # 创建Plotly图形
        fig = go.Figure()
        
        if color_by and color_by in self.data.columns:
            unique_categories = self.data[color_by].unique()
            for category in unique_categories:
                subset = self.data[self.data[color_by] == category]
                fig.add_trace(go.Scatter3d(
                    x=subset[numeric_cols[0]],
                    y=subset[numeric_cols[1]],
                    z=subset[numeric_cols[2]],
                    mode='markers',
                    name=str(category),
                    marker=dict(
                        size=self.size_slider.value(),
                        opacity=self.alpha_slider.value()/10,
                    )
                ))
        else:
            fig.add_trace(go.Scatter3d(
                x=self.data[numeric_cols[0]],
                y=self.data[numeric_cols[1]],
                z=self.data[numeric_cols[2]],
                mode='markers',
                marker=dict(
                    size=self.size_slider.value(),
                    opacity=self.alpha_slider.value()/10,
                    color=self.data[numeric_cols[3]] if len(numeric_cols) > 3 else 1,
                    colorscale='Viridis',
                    colorbar=dict(title=numeric_cols[3] if len(numeric_cols) > 3 else "值")
                )
            ))
        
        fig.update_layout(
            scene=dict(
                xaxis_title=numeric_cols[0],
                yaxis_title=numeric_cols[1],
                zaxis_title=numeric_cols[2]
            ),
            title="交互式3D散点图"
        )
        
        # 保存为HTML并在QWebEngineView中显示
        html_file = "interactive_3d_plot.html"
        plot(fig, filename=html_file, auto_open=False)
        
        # 创建Web视图选项卡
        web_view = QtWidgets.QTextBrowser()
        with open(html_file, "r", encoding="utf-8") as f:
            html_content = f.read()
        web_view.setHtml(html_content)
        
        self.viz_area.addTab(web_view, "交互式3D图")


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # 设置应用程序样式
    palette = QtGui.QPalette()
    palette.setColor(QtGui.QPalette.Window, QtGui.QColor(53, 53, 53))
    palette.setColor(QtGui.QPalette.WindowText, QtCore.Qt.white)
    palette.setColor(QtGui.QPalette.Base, QtGui.QColor(25, 25, 25))
    palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(53, 53, 53))
    palette.setColor(QtGui.QPalette.ToolTipBase, QtCore.Qt.white)
    palette.setColor(QtGui.QPalette.ToolTipText, QtCore.Qt.white)
    palette.setColor(QtGui.QPalette.Text, QtCore.Qt.white)
    palette.setColor(QtGui.QPalette.Button, QtGui.QColor(53, 53, 53))
    palette.setColor(QtGui.QPalette.ButtonText, QtCore.Qt.white)
    palette.setColor(QtGui.QPalette.BrightText, QtCore.Qt.red)
    palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor(142, 45, 197).lighter())
    palette.setColor(QtGui.QPalette.HighlightedText, QtCore.Qt.black)
    app.setPalette(palette)
    
    window = AdvancedVisualizationTool()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()