import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import seaborn as sns
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QTabWidget, QTableWidget, QTableWidgetItem, QPushButton, 
                             QLabel, QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox,
                             QGroupBox, QFormLayout, QMessageBox, QSplitter, QHeaderView,
                             QCheckBox, QFileDialog, QProgressBar, QTextEdit, QScrollArea)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPalette, QColor
import warnings
warnings.filterwarnings('ignore')

class InnovationMatrix:
    """创新度度量矩阵核心计算类"""
    def __init__(self, dimensions=None):
        if dimensions is None:
            self.dimensions = {
                'novelty': {'name': '新颖性', 'description': '技术/方案的原创性和突破性'},
                'impact': {'name': '影响力', 'description': '对市场/技术/社会的潜在影响范围'},
                'feasibility': {'name': '可实现性', 'description': '技术实现和商业化的可行性'},
                'strategic_fit': {'name': '战略契合度', 'description': '与组织战略目标的匹配程度'},
                'cost_efficiency': {'name': '成本效益', 'description': '投入产出比和经济效益'},
                'time_to_market': {'name': '上市时间', 'description': '从研发到商业化的速度'}
            }
        else:
            self.dimensions = dimensions
        
        self.projects = {}
        self.weights = {dim: 1.0/len(self.dimensions) for dim in self.dimensions.keys()}
        self.cost_data = {}
        self.risk_data = {}
    
    def set_weights(self, weights):
        if abs(sum(weights.values()) - 1.0) > 0.001:
            raise ValueError("权重总和必须为1")
        self.weights = weights
    
    def add_project(self, name, scores, cost=None, risk_level=None, description=""):
        if len(scores) != len(self.dimensions):
            raise ValueError(f"评分数量必须与维度数量({len(self.dimensions)})匹配")
        
        self.projects[name] = {
            'scores': scores.copy(),
            'description': description,
            'weighted_score': sum(scores[dim] * self.weights[dim] for dim in self.dimensions.keys())
        }
        
        if cost is not None:
            self.cost_data[name] = cost
        if risk_level is not None:
            self.risk_data[name] = risk_level
    
    def calculate_innovation_index(self, project_name):
        """计算创新指数"""
        if project_name not in self.projects:
            raise ValueError(f"项目 '{project_name}' 不存在")
        
        scores = self.projects[project_name]['scores']
        return sum(scores[dim] * self.weights[dim] for dim in self.dimensions.keys())
    
    def get_ranked_projects(self):
        """获取按综合得分排序的项目列表"""
        ranked = sorted(self.projects.items(), 
                       key=lambda x: x[1]['weighted_score'], 
                       reverse=True)
        return ranked
    
    def sensitivity_analysis(self, project_name, dimension, value_range=np.arange(1, 5.1, 0.1)):
        """敏感性分析"""
        if project_name not in self.projects:
            raise ValueError(f"项目 '{project_name}' 不存在")
        
        base_scores = self.projects[project_name]['scores'].copy()
        results = []
        
        for value in value_range:
            temp_scores = base_scores.copy()
            temp_scores[dimension] = value
            weighted_score = sum(temp_scores[dim] * self.weights[dim] for dim in self.dimensions.keys())
            results.append(weighted_score)
        
        return value_range, results, base_scores[dimension]
    
    def portfolio_optimization(self, budget_constraint=None, max_projects=None):
        """投资组合优化"""
        if not self.projects:
            return []
        
        projects_data = []
        for name, data in self.projects.items():
            cost = self.cost_data.get(name, 0)
            risk = self.risk_data.get(name, 3.0)  # 默认中等风险
            score = data['weighted_score']
            projects_data.append({
                'name': name,
                'score': score,
                'cost': cost,
                'risk': risk,
                'efficiency': score / cost if cost > 0 else score
            })
        
        df = pd.DataFrame(projects_data)
        
        # 简单的贪心算法选择最优组合
        if budget_constraint:
            df_sorted = df.sort_values('efficiency', ascending=False)
            selected = []
            total_cost = 0
            
            for _, project in df_sorted.iterrows():
                if total_cost + project['cost'] <= budget_constraint:
                    selected.append(project)
                    total_cost += project['cost']
            
            return selected
        
        elif max_projects:
            df_sorted = df.sort_values('score', ascending=False)
            return df_sorted.head(max_projects).to_dict('records')
        
        else:
            return df.sort_values('score', ascending=False).to_dict('records')
    
    def generate_report(self):
        """生成分析报告"""
        report = "创新度度量矩阵分析报告\n"
        report += "=" * 50 + "\n\n"
        
        # 项目排名
        report += "项目排名:\n"
        ranked = self.get_ranked_projects()
        for i, (name, data) in enumerate(ranked, 1):
            report += f"{i}. {name}: {data['weighted_score']:.2f}\n"
        
        report += "\n维度权重:\n"
        for dim, weight in self.weights.items():
            report += f"- {self.dimensions[dim]['name']}: {weight:.2f}\n"
        
        # 投资组合建议
        if self.cost_data:
            report += "\n投资组合建议:\n"
            portfolio = self.portfolio_optimization(budget_constraint=sum(self.cost_data.values()) * 0.6)
            for project in portfolio:
                report += f"- {project['name']} (得分: {project['score']:.2f}, 成本: {project['cost']:.0f})\n"
        
        return report

class MplCanvas(FigureCanvas):
    """Matplotlib画布"""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)

class RadarChartWidget(MplCanvas):
    """雷达图组件"""
    def __init__(self, parent=None):
        super().__init__(parent, width=8, height=6)
    
    def plot_radar(self, innovation_matrix):
        """绘制雷达图"""
        self.fig.clear()
        
        if not innovation_matrix.projects:
            ax = self.fig.add_subplot(111)
            ax.text(0.5, 0.5, '暂无项目数据', ha='center', va='center', transform=ax.transAxes)
            self.draw()
            return
        
        # 创建雷达图坐标
        dim_names = [innovation_matrix.dimensions[dim]['name'] for dim in innovation_matrix.dimensions.keys()]
        num_vars = len(dim_names)
        angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
        angles += angles[:1]  # 闭合
        
        ax = self.fig.add_subplot(111, polar=True)
        
        # 设置角度刻度
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(dim_names)
        
        # 设置径向刻度
        ax.set_rlabel_position(30)
        plt.yticks([1, 2, 3, 4, 5], ["1", "2", "3", "4", "5"], color="grey", size=8)
        plt.ylim(0, 5)
        
        # 绘制每个项目
        colors = plt.cm.Set1(np.linspace(0, 1, len(innovation_matrix.projects)))
        for idx, (project, data) in enumerate(innovation_matrix.projects.items()):
            scores = list(data['scores'].values())
            scores += scores[:1]  # 闭合数据
            ax.plot(angles, scores, color=colors[idx], linewidth=2, label=project)
            ax.fill(angles, scores, color=colors[idx], alpha=0.1)
        
        # 添加图例
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))
        ax.set_title('创新度度量矩阵 - 项目比较雷达图', size=14, fontweight='bold')
        
        self.draw()

class AnalysisThread(QThread):
    """分析线程"""
    progress_updated = pyqtSignal(int)
    analysis_completed = pyqtSignal(dict)
    
    def __init__(self, innovation_matrix):
        super().__init__()
        self.innovation_matrix = innovation_matrix
    
    def run(self):
        """执行分析"""
        results = {}
        
        # 项目排名
        results['ranking'] = self.innovation_matrix.get_ranked_projects()
        self.progress_updated.emit(25)
        
        # 敏感性分析数据
        results['sensitivity'] = {}
        if self.innovation_matrix.projects:
            project = list(self.innovation_matrix.projects.keys())[0]
            dim = list(self.innovation_matrix.dimensions.keys())[0]
            results['sensitivity'][(project, dim)] = self.innovation_matrix.sensitivity_analysis(project, dim)
        self.progress_updated.emit(50)
        
        # 投资组合分析
        results['portfolio'] = self.innovation_matrix.portfolio_optimization()
        self.progress_updated.emit(75)
        
        # 生成报告
        results['report'] = self.innovation_matrix.generate_report()
        self.progress_updated.emit(100)
        
        self.analysis_completed.emit(results)

class ProjectTableWidget(QTableWidget):
    """项目数据表格"""
    def __init__(self, innovation_matrix):
        super().__init__()
        self.innovation_matrix = innovation_matrix
        self.setup_table()
    
    def setup_table(self):
        """初始化表格"""
        dim_names = [self.innovation_matrix.dimensions[dim]['name'] for dim in self.innovation_matrix.dimensions.keys()]
        headers = ['项目名称'] + dim_names + ['成本', '风险等级', '描述']
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        
        # 设置表格属性
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.setAlternatingRowColors(True)
    
    def load_projects(self):
        """加载项目数据到表格"""
        self.setRowCount(len(self.innovation_matrix.projects))
        
        for row, (project_name, project_data) in enumerate(self.innovation_matrix.projects.items()):
            # 项目名称
            self.setItem(row, 0, QTableWidgetItem(project_name))
            
            # 各维度评分
            for col, dim in enumerate(self.innovation_matrix.dimensions.keys(), 1):
                score = project_data['scores'][dim]
                item = QTableWidgetItem(f"{score:.1f}")
                item.setTextAlignment(Qt.AlignCenter)
                self.setItem(row, col, item)
            
            # 成本
            cost = self.innovation_matrix.cost_data.get(project_name, 0)
            self.setItem(row, len(self.innovation_matrix.dimensions) + 1, QTableWidgetItem(f"{cost}"))
            
            # 风险等级
            risk = self.innovation_matrix.risk_data.get(project_name, 3)
            self.setItem(row, len(self.innovation_matrix.dimensions) + 2, QTableWidgetItem(f"{risk}"))
            
            # 描述
            desc = project_data.get('description', '')
            self.setItem(row, len(self.innovation_matrix.dimensions) + 3, QTableWidgetItem(desc))

class MainWindow(QMainWindow):
    """主窗口"""
    def __init__(self):
        super().__init__()
        self.innovation_matrix = InnovationMatrix()
        self.init_ui()
        
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle('创新度度量矩阵分析系统')
        self.setGeometry(100, 100, 1400, 900)
        
        # 创建中央部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # 左侧控制面板
        control_panel = self.create_control_panel()
        splitter.addWidget(control_panel)
        
        # 右侧显示区域
        display_area = self.create_display_area()
        splitter.addWidget(display_area)
        
        # 设置分割比例
        splitter.setSizes([400, 1000])
        
        # 状态栏
        self.statusBar().showMessage('就绪')
        
    def create_control_panel(self):
        """创建左侧控制面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 项目管理组
        project_group = QGroupBox("项目管理")
        project_layout = QFormLayout(project_group)
        
        self.project_name_edit = QLineEdit()
        project_layout.addRow("项目名称:", self.project_name_edit)
        
        # 维度评分输入
        self.score_inputs = {}
        for dim in self.innovation_matrix.dimensions.keys():
            spinbox = QDoubleSpinBox()
            spinbox.setRange(1.0, 5.0)
            spinbox.setSingleStep(0.1)
            spinbox.setValue(3.0)
            self.score_inputs[dim] = spinbox
            project_layout.addRow(f"{self.innovation_matrix.dimensions[dim]['name']}:", spinbox)
        
        self.cost_spinbox = QSpinBox()
        self.cost_spinbox.setRange(0, 10000)
        self.cost_spinbox.setSuffix(" 万元")
        project_layout.addRow("研发成本:", self.cost_spinbox)
        
        self.risk_spinbox = QDoubleSpinBox()
        self.risk_spinbox.setRange(1.0, 5.0)
        self.risk_spinbox.setSingleStep(0.1)
        self.risk_spinbox.setValue(3.0)
        project_layout.addRow("风险等级:", self.risk_spinbox)
        
        self.desc_edit = QLineEdit()
        project_layout.addRow("项目描述:", self.desc_edit)
        
        # 按钮组
        button_layout = QHBoxLayout()
        self.add_btn = QPushButton("添加项目")
        self.add_btn.clicked.connect(self.add_project)
        button_layout.addWidget(self.add_btn)
        
        self.clear_btn = QPushButton("清空项目")
        self.clear_btn.clicked.connect(self.clear_projects)
        button_layout.addWidget(self.clear_btn)
        
        project_layout.addRow(button_layout)
        
        # 权重设置组
        weight_group = QGroupBox("维度权重设置")
        weight_layout = QFormLayout(weight_group)
        
        self.weight_inputs = {}
        for dim in self.innovation_matrix.dimensions.keys():
            spinbox = QDoubleSpinBox()
            spinbox.setRange(0.0, 1.0)
            spinbox.setSingleStep(0.05)
            spinbox.setValue(1.0/len(self.innovation_matrix.dimensions))
            self.weight_inputs[dim] = spinbox
            weight_layout.addRow(f"{self.innovation_matrix.dimensions[dim]['name']}:", spinbox)
        
        self.apply_weights_btn = QPushButton("应用权重")
        self.apply_weights_btn.clicked.connect(self.apply_weights)
        weight_layout.addRow(self.apply_weights_btn)
        
        # 分析控制组
        analysis_group = QGroupBox("分析控制")
        analysis_layout = QVBoxLayout(analysis_group)
        
        self.analyze_btn = QPushButton("开始分析")
        self.analyze_btn.clicked.connect(self.start_analysis)
        analysis_layout.addWidget(self.analyze_btn)
        
        self.progress_bar = QProgressBar()
        analysis_layout.addWidget(self.progress_bar)
        
        # 文件操作组
        file_group = QGroupBox("文件操作")
        file_layout = QVBoxLayout(file_group)
        
        self.import_btn = QPushButton("导入数据")
        self.import_btn.clicked.connect(self.import_data)
        file_layout.addWidget(self.import_btn)
        
        self.export_btn = QPushButton("导出报告")
        self.export_btn.clicked.connect(self.export_report)
        file_layout.addWidget(self.export_btn)
        
        # 添加到主布局
        layout.addWidget(project_group)
        layout.addWidget(weight_group)
        layout.addWidget(analysis_group)
        layout.addWidget(file_group)
        layout.addStretch()
        
        return panel
    
    def create_display_area(self):
        """创建右侧显示区域"""
        display_widget = QWidget()
        layout = QVBoxLayout(display_widget)
        
        # 创建标签页
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # 项目数据标签页
        self.project_table = ProjectTableWidget(self.innovation_matrix)
        self.tabs.addTab(self.project_table, "项目数据")
        
        # 雷达图标签页
        self.radar_tab = QWidget()
        radar_layout = QVBoxLayout(self.radar_tab)
        self.radar_canvas = RadarChartWidget(self.radar_tab)
        radar_layout.addWidget(self.radar_canvas)
        self.tabs.addTab(self.radar_tab, "雷达图分析")
        
        # 柱状图标签页
        self.bar_tab = QWidget()
        bar_layout = QVBoxLayout(self.bar_tab)
        self.bar_canvas = MplCanvas(self.bar_tab, width=8, height=6)
        bar_layout.addWidget(self.bar_canvas)
        self.tabs.addTab(self.bar_tab, "得分比较")
        
        # 敏感性分析标签页
        self.sensitivity_tab = QWidget()
        sensitivity_layout = QVBoxLayout(self.sensitivity_tab)
        self.sensitivity_canvas = MplCanvas(self.sensitivity_tab, width=8, height=6)
        sensitivity_layout.addWidget(self.sensitivity_canvas)
        self.tabs.addTab(self.sensitivity_tab, "敏感性分析")
        
        # 报告标签页
        self.report_tab = QWidget()
        report_layout = QVBoxLayout(self.report_tab)
        self.report_text = QTextEdit()
        self.report_text.setFont(QFont("Consolas", 10))
        report_layout.addWidget(self.report_text)
        self.tabs.addTab(self.report_tab, "分析报告")
        
        return display_widget
    
    def add_project(self):
        """添加项目"""
        name = self.project_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "输入错误", "请输入项目名称")
            return
        
        if name in self.innovation_matrix.projects:
            QMessageBox.warning(self, "输入错误", "项目名称已存在")
            return
        
        # 收集评分数据
        scores = {}
        for dim, spinbox in self.score_inputs.items():
            scores[dim] = spinbox.value()
        
        cost = self.cost_spinbox.value()
        risk = self.risk_spinbox.value()
        desc = self.desc_edit.text()
        
        # 添加到矩阵
        self.innovation_matrix.add_project(name, scores, cost, risk, desc)
        
        # 更新表格
        self.project_table.load_projects()
        
        # 清空输入
        self.project_name_edit.clear()
        self.desc_edit.clear()
        
        self.statusBar().showMessage(f"已添加项目: {name}")
    
    def clear_projects(self):
        """清空所有项目"""
        reply = QMessageBox.question(self, "确认清空", "确定要清空所有项目数据吗？",
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.innovation_matrix.projects.clear()
            self.innovation_matrix.cost_data.clear()
            self.innovation_matrix.risk_data.clear()
            self.project_table.load_projects()
            self.statusBar().showMessage("已清空所有项目数据")
    
    def apply_weights(self):
        """应用权重设置"""
        weights = {}
        for dim, spinbox in self.weight_inputs.items():
            weights[dim] = spinbox.value()
        
        try:
            self.innovation_matrix.set_weights(weights)
            
            # 重新计算所有项目的加权得分
            for name in self.innovation_matrix.projects.keys():
                self.innovation_matrix.projects[name]['weighted_score'] = \
                    self.innovation_matrix.calculate_innovation_index(name)
            
            self.project_table.load_projects()
            self.statusBar().showMessage("权重已应用")
            
        except ValueError as e:
            QMessageBox.warning(self, "权重错误", str(e))
    
    def start_analysis(self):
        """开始分析"""
        if not self.innovation_matrix.projects:
            QMessageBox.warning(self, "分析错误", "请先添加项目数据")
            return
        
        # 禁用分析按钮
        self.analyze_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        
        # 创建分析线程
        self.analysis_thread = AnalysisThread(self.innovation_matrix)
        self.analysis_thread.progress_updated.connect(self.update_progress)
        self.analysis_thread.analysis_completed.connect(self.analysis_finished)
        self.analysis_thread.start()
        
        self.statusBar().showMessage("分析进行中...")
    
    def update_progress(self, value):
        """更新进度条"""
        self.progress_bar.setValue(value)
    
    def analysis_finished(self, results):
        """分析完成"""
        self.analyze_btn.setEnabled(True)
        
        # 更新雷达图
        self.radar_canvas.plot_radar(self.innovation_matrix)
        
        # 更新柱状图
        self.update_bar_chart()
        
        # 更新敏感性分析
        self.update_sensitivity_analysis()
        
        # 更新报告
        self.report_text.setText(results['report'])
        
        self.statusBar().showMessage("分析完成")
    
    def update_bar_chart(self):
        """更新柱状图"""
        self.bar_canvas.fig.clear()
        ax = self.bar_canvas.fig.add_subplot(111)
        
        if not self.innovation_matrix.projects:
            ax.text(0.5, 0.5, '暂无项目数据', ha='center', va='center', transform=ax.transAxes)
            self.bar_canvas.draw()
            return
        
        ranked_projects = self.innovation_matrix.get_ranked_projects()
        projects = [p[0] for p in ranked_projects]
        scores = [p[1]['weighted_score'] for p in ranked_projects]
        
        bars = ax.bar(projects, scores, color=plt.cm.Set1(np.linspace(0, 1, len(projects))))
        
        # 添加数值标签
        for bar, score in zip(bars, scores):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.05,
                   f'{score:.2f}', ha='center', va='bottom', fontweight='bold')
        
        ax.set_ylabel('加权综合得分')
        ax.set_title('创新项目综合得分比较', fontweight='bold')
        ax.set_ylim(0, 5)
        plt.xticks(rotation=45)
        plt.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        
        self.bar_canvas.draw()
    
    def update_sensitivity_analysis(self):
        """更新敏感性分析图"""
        self.sensitivity_canvas.fig.clear()
        ax = self.sensitivity_canvas.fig.add_subplot(111)
        
        if len(self.innovation_matrix.projects) < 1:
            ax.text(0.5, 0.5, '需要至少一个项目进行分析', ha='center', va='center', transform=ax.transAxes)
            self.sensitivity_canvas.draw()
            return
        
        # 使用第一个项目和第一个维度进行演示
        project = list(self.innovation_matrix.projects.keys())[0]
        dimension = list(self.innovation_matrix.dimensions.keys())[0]
        
        x, y, current_value = self.innovation_matrix.sensitivity_analysis(project, dimension)
        
        ax.plot(x, y, linewidth=2)
        ax.axvline(x=current_value, color='red', linestyle='--', 
                  label=f'当前值: {current_value:.1f}')
        ax.set_xlabel(f'{self.innovation_matrix.dimensions[dimension]["name"]} 得分')
        ax.set_ylabel('综合得分')
        ax.set_title(f'{project} - {self.innovation_matrix.dimensions[dimension]["name"]}敏感性分析', 
                    fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        self.sensitivity_canvas.draw()
    
    def import_data(self):
        """导入数据"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入数据", "", "Excel Files (*.xlsx *.xls);;CSV Files (*.csv)")
        
        if file_path:
            try:
                if file_path.endswith(('.xlsx', '.xls')):
                    df = pd.read_excel(file_path)
                else:
                    df = pd.read_csv(file_path)
                
                # 清空现有数据
                self.innovation_matrix.projects.clear()
                self.innovation_matrix.cost_data.clear()
                self.innovation_matrix.risk_data.clear()
                
                # 解析数据
                for _, row in df.iterrows():
                    project_name = str(row.iloc[0])
                    scores = {}
                    
                    for i, dim in enumerate(self.innovation_matrix.dimensions.keys(), 1):
                        if i < len(row):
                            scores[dim] = float(row.iloc[i])
                    
                    cost = float(row.iloc[len(self.innovation_matrix.dimensions) + 1]) \
                        if len(row) > len(self.innovation_matrix.dimensions) + 1 else 0
                    
                    risk = float(row.iloc[len(self.innovation_matrix.dimensions) + 2]) \
                        if len(row) > len(self.innovation_matrix.dimensions) + 2 else 3.0
                    
                    desc = str(row.iloc[len(self.innovation_matrix.dimensions) + 3]) \
                        if len(row) > len(self.innovation_matrix.dimensions) + 3 else ""
                    
                    self.innovation_matrix.add_project(project_name, scores, cost, risk, desc)
                
                self.project_table.load_projects()
                self.statusBar().showMessage(f"已从 {file_path} 导入数据")
                
            except Exception as e:
                QMessageBox.critical(self, "导入错误", f"导入数据时出错: {str(e)}")
    
    def export_report(self):
        """导出报告"""
        if not self.innovation_matrix.projects:
            QMessageBox.warning(self, "导出错误", "没有可导出的数据")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出报告", "innovation_analysis_report.txt", "Text Files (*.txt)")
        
        if file_path:
            try:
                report = self.innovation_matrix.generate_report()
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(report)
                
                self.statusBar().showMessage(f"报告已导出到 {file_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "导出错误", f"导出报告时出错: {str(e)}")

def main():
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()