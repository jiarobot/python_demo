import sys
import os
import json
import pandas as pd
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QTabWidget, QPushButton, QTextEdit, QLineEdit, QLabel, 
                            QComboBox, QSpinBox, QDoubleSpinBox, QProgressBar, QTableWidget,
                            QTableWidgetItem, QHeaderView, QGroupBox, QSplitter, QFileDialog,
                            QMessageBox, QListWidget, QListWidgetItem, QCheckBox, QSlider)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QFont, QPalette, QColor
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

class KnowledgeDatasetManager:
    """知识数据集管理器"""
    
    def __init__(self):
        self.datasets = {
            "general_knowledge": [],
            "science_facts": [],
            "geography": [],
            "history": [],
            "mathematics": [],
            "programming": []
        }
        
    def add_text_example(self, dataset_name, text, category, difficulty, importance):
        """添加文本示例"""
        if dataset_name not in self.datasets:
            self.datasets[dataset_name] = []
            
        example = {
            "text": text,
            "category": category,
            "difficulty": difficulty,
            "importance": importance,
            "timestamp": datetime.now().isoformat(),
            "type": "text"
        }
        self.datasets[dataset_name].append(example)
        return True
        
    def add_qa_pair(self, dataset_name, question, answer, domain, complexity):
        """添加问答对"""
        if dataset_name not in self.datasets:
            self.datasets[dataset_name] = []
            
        example = {
            "question": question,
            "answer": answer,
            "domain": domain,
            "complexity": complexity,
            "timestamp": datetime.now().isoformat(),
            "type": "qa"
        }
        self.datasets[dataset_name].append(example)
        return True
        
    def export_dataset(self, dataset_name, filename):
        """导出数据集"""
        if dataset_name not in self.datasets:
            return False
            
        data = {
            "dataset_name": dataset_name,
            "examples": self.datasets[dataset_name],
            "export_time": datetime.now().isoformat(),
            "total_examples": len(self.datasets[dataset_name])
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
        
    def import_dataset(self, filename):
        """导入数据集"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            dataset_name = data.get("dataset_name", "imported_dataset")
            examples = data.get("examples", [])
            
            if dataset_name not in self.datasets:
                self.datasets[dataset_name] = []
                
            self.datasets[dataset_name].extend(examples)
            return True, f"成功导入 {len(examples)} 个示例到 {dataset_name}"
        except Exception as e:
            return False, f"导入失败: {str(e)}"
            
    def get_dataset_stats(self):
        """获取数据集统计"""
        stats = {}
        for name, examples in self.datasets.items():
            stats[name] = {
                "total": len(examples),
                "text_count": len([e for e in examples if e.get("type") == "text"]),
                "qa_count": len([e for e in examples if e.get("type") == "qa"]),
                "last_updated": max([e.get("timestamp", "") for e in examples]) if examples else ""
            }
        return stats

class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.metrics_history = {
            "accuracy": [],
            "loss": [],
            "reasoning": [],
            "memory": [],
            "planning": [],
            "execution": [],
            "learning": [],
            "creativity": []
        }
        self.timestamps = []
        
    def update_metrics(self, metrics):
        """更新性能指标"""
        timestamp = datetime.now()
        self.timestamps.append(timestamp)
        
        for key, value in metrics.items():
            if key in self.metrics_history:
                self.metrics_history[key].append(value)
                
        # 保持历史数据在合理范围内
        if len(self.timestamps) > 100:
            self.timestamps = self.timestamps[-100:]
            for key in self.metrics_history:
                self.metrics_history[key] = self.metrics_history[key][-100:]
                
    def get_recent_metrics(self, count=10):
        """获取最近的性能指标"""
        result = {}
        for key, values in self.metrics_history.items():
            result[key] = values[-count:] if values else []
        return result

class MplCanvas(FigureCanvas):
    """Matplotlib画布"""
    
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super(MplCanvas, self).__init__(self.fig)
        self.setParent(parent)

class KnowledgeFeedingTab(QWidget):
    """知识投喂标签页"""
    
    def __init__(self, dataset_manager):
        super().__init__()
        self.dataset_manager = dataset_manager
        self.init_ui()
        
    def init_ui(self):
        layout = QHBoxLayout()
        
        # 左侧：数据输入
        left_panel = QVBoxLayout()
        
        # 数据集选择
        dataset_group = QGroupBox("数据集管理")
        dataset_layout = QVBoxLayout()
        
        self.dataset_combo = QComboBox()
        self.dataset_combo.addItems(["general_knowledge", "science_facts", "geography", 
                                   "history", "mathematics", "programming", "custom"])
        dataset_layout.addWidget(QLabel("选择数据集:"))
        dataset_layout.addWidget(self.dataset_combo)
        
        self.custom_dataset_input = QLineEdit()
        self.custom_dataset_input.setPlaceholderText("输入自定义数据集名称")
        dataset_layout.addWidget(self.custom_dataset_input)
        
        dataset_layout.addWidget(QLabel("数据统计:"))
        self.dataset_stats_label = QLabel("无数据")
        dataset_layout.addWidget(self.dataset_stats_label)
        
        dataset_group.setLayout(dataset_layout)
        left_panel.addWidget(dataset_group)
        
        # 知识类型选择
        knowledge_type_group = QGroupBox("知识类型")
        knowledge_layout = QVBoxLayout()
        
        self.knowledge_type_combo = QComboBox()
        self.knowledge_type_combo.addItems(["文本知识", "问答对", "程序性知识", "概念定义"])
        self.knowledge_type_combo.currentTextChanged.connect(self.on_knowledge_type_changed)
        knowledge_layout.addWidget(self.knowledge_type_combo)
        
        # 文本知识输入
        self.text_input_group = QGroupBox("文本知识")
        text_layout = QVBoxLayout()
        
        text_layout.addWidget(QLabel("知识文本:"))
        self.text_input = QTextEdit()
        self.text_input.setMaximumHeight(100)
        text_layout.addWidget(self.text_input)
        
        text_layout.addWidget(QLabel("分类:"))
        self.category_input = QLineEdit()
        text_layout.addWidget(self.category_input)
        
        text_layout.addWidget(QLabel("难度 (0-1):"))
        self.difficulty_input = QDoubleSpinBox()
        self.difficulty_input.setRange(0.0, 1.0)
        self.difficulty_input.setSingleStep(0.1)
        self.difficulty_input.setValue(0.5)
        text_layout.addWidget(self.difficulty_input)
        
        text_layout.addWidget(QLabel("重要性 (0-1):"))
        self.importance_input = QDoubleSpinBox()
        self.importance_input.setRange(0.0, 1.0)
        self.importance_input.setSingleStep(0.1)
        self.importance_input.setValue(0.8)
        text_layout.addWidget(self.importance_input)
        
        self.text_input_group.setLayout(text_layout)
        knowledge_layout.addWidget(self.text_input_group)
        
        # 问答对输入
        self.qa_input_group = QGroupBox("问答对")
        qa_layout = QVBoxLayout()
        
        qa_layout.addWidget(QLabel("问题:"))
        self.question_input = QTextEdit()
        self.question_input.setMaximumHeight(60)
        qa_layout.addWidget(self.question_input)
        
        qa_layout.addWidget(QLabel("答案:"))
        self.answer_input = QTextEdit()
        self.answer_input.setMaximumHeight(60)
        qa_layout.addWidget(self.answer_input)
        
        qa_layout.addWidget(QLabel("领域:"))
        self.domain_input = QLineEdit()
        qa_layout.addWidget(self.domain_input)
        
        qa_layout.addWidget(QLabel("复杂度 (0-1):"))
        self.complexity_input = QDoubleSpinBox()
        self.complexity_input.setRange(0.0, 1.0)
        self.complexity_input.setSingleStep(0.1)
        self.complexity_input.setValue(0.5)
        qa_layout.addWidget(self.complexity_input)
        
        self.qa_input_group.setLayout(qa_layout)
        self.qa_input_group.setVisible(False)
        knowledge_layout.addWidget(self.qa_input_group)
        
        knowledge_type_group.setLayout(knowledge_layout)
        left_panel.addWidget(knowledge_type_group)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        self.add_button = QPushButton("添加知识")
        self.add_button.clicked.connect(self.add_knowledge)
        button_layout.addWidget(self.add_button)
        
        self.clear_button = QPushButton("清空输入")
        self.clear_button.clicked.connect(self.clear_inputs)
        button_layout.addWidget(self.clear_button)
        
        left_panel.addLayout(button_layout)
        
        # 右侧：数据预览
        right_panel = QVBoxLayout()
        
        preview_group = QGroupBox("数据预览")
        preview_layout = QVBoxLayout()
        
        self.preview_table = QTableWidget()
        self.preview_table.setColumnCount(5)
        self.preview_table.setHorizontalHeaderLabels(["类型", "内容", "分类/领域", "难度/复杂度", "时间"])
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        preview_layout.addWidget(self.preview_table)
        
        preview_group.setLayout(preview_layout)
        right_panel.addWidget(preview_group)
        
        # 导入导出按钮
        io_layout = QHBoxLayout()
        self.import_button = QPushButton("导入数据集")
        self.import_button.clicked.connect(self.import_dataset)
        io_layout.addWidget(self.import_button)
        
        self.export_button = QPushButton("导出数据集")
        self.export_button.clicked.connect(self.export_dataset)
        io_layout.addWidget(self.export_button)
        
        right_panel.addLayout(io_layout)
        
        # 组合左右面板
        splitter = QSplitter(Qt.Horizontal)
        left_widget = QWidget()
        left_widget.setLayout(left_panel)
        right_widget = QWidget()
        right_widget.setLayout(right_panel)
        
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([400, 600])
        
        layout.addWidget(splitter)
        self.setLayout(layout)
        
        # 初始更新
        self.update_dataset_stats()
        self.update_preview_table()
        
    def on_knowledge_type_changed(self, knowledge_type):
        """知识类型改变时的处理"""
        if knowledge_type == "文本知识":
            self.text_input_group.setVisible(True)
            self.qa_input_group.setVisible(False)
        elif knowledge_type == "问答对":
            self.text_input_group.setVisible(False)
            self.qa_input_group.setVisible(True)
        else:
            self.text_input_group.setVisible(False)
            self.qa_input_group.setVisible(False)
            
    def add_knowledge(self):
        """添加知识"""
        dataset_name = self.get_current_dataset_name()
        knowledge_type = self.knowledge_type_combo.currentText()
        
        if knowledge_type == "文本知识":
            text = self.text_input.toPlainText().strip()
            category = self.category_input.text().strip()
            difficulty = self.difficulty_input.value()
            importance = self.importance_input.value()
            
            if not text:
                QMessageBox.warning(self, "输入错误", "请输入知识文本")
                return
                
            success = self.dataset_manager.add_text_example(
                dataset_name, text, category, difficulty, importance
            )
            
            if success:
                QMessageBox.information(self, "成功", "文本知识添加成功")
                self.clear_inputs()
                self.update_dataset_stats()
                self.update_preview_table()
                
        elif knowledge_type == "问答对":
            question = self.question_input.toPlainText().strip()
            answer = self.answer_input.toPlainText().strip()
            domain = self.domain_input.text().strip()
            complexity = self.complexity_input.value()
            
            if not question or not answer:
                QMessageBox.warning(self, "输入错误", "请输入问题和答案")
                return
                
            success = self.dataset_manager.add_qa_pair(
                dataset_name, question, answer, domain, complexity
            )
            
            if success:
                QMessageBox.information(self, "成功", "问答对添加成功")
                self.clear_inputs()
                self.update_dataset_stats()
                self.update_preview_table()
                
    def clear_inputs(self):
        """清空输入"""
        self.text_input.clear()
        self.category_input.clear()
        self.difficulty_input.setValue(0.5)
        self.importance_input.setValue(0.8)
        
        self.question_input.clear()
        self.answer_input.clear()
        self.domain_input.clear()
        self.complexity_input.setValue(0.5)
        
    def get_current_dataset_name(self):
        """获取当前数据集名称"""
        dataset = self.dataset_combo.currentText()
        if dataset == "custom":
            custom_name = self.custom_dataset_input.text().strip()
            return custom_name if custom_name else "custom_dataset"
        return dataset
        
    def update_dataset_stats(self):
        """更新数据集统计"""
        dataset_name = self.get_current_dataset_name()
        stats = self.dataset_manager.get_dataset_stats()
        
        if dataset_name in stats:
            dataset_stats = stats[dataset_name]
            text = (f"总数: {dataset_stats['total']}\n"
                   f"文本: {dataset_stats['text_count']}\n"
                   f"问答: {dataset_stats['qa_count']}\n"
                   f"最后更新: {dataset_stats['last_updated'][:19] if dataset_stats['last_updated'] else '无'}")
        else:
            text = "无数据"
            
        self.dataset_stats_label.setText(text)
        
    def update_preview_table(self):
        """更新预览表格"""
        dataset_name = self.get_current_dataset_name()
        examples = self.dataset_manager.datasets.get(dataset_name, [])
        
        self.preview_table.setRowCount(len(examples))
        
        for i, example in enumerate(examples):
            if example.get("type") == "text":
                self.preview_table.setItem(i, 0, QTableWidgetItem("文本"))
                self.preview_table.setItem(i, 1, QTableWidgetItem(example.get("text", "")[:50] + "..."))
                self.preview_table.setItem(i, 2, QTableWidgetItem(example.get("category", "")))
                self.preview_table.setItem(i, 3, QTableWidgetItem(str(example.get("difficulty", 0))))
            elif example.get("type") == "qa":
                self.preview_table.setItem(i, 0, QTableWidgetItem("问答"))
                self.preview_table.setItem(i, 1, QTableWidgetItem(f"Q: {example.get('question', '')[:30]}..."))
                self.preview_table.setItem(i, 2, QTableWidgetItem(example.get("domain", "")))
                self.preview_table.setItem(i, 3, QTableWidgetItem(str(example.get("complexity", 0))))
                
            self.preview_table.setItem(i, 4, QTableWidgetItem(example.get("timestamp", "")[:19]))
            
    def import_dataset(self):
        """导入数据集"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "选择数据集文件", "", "JSON Files (*.json)"
        )
        
        if filename:
            success, message = self.dataset_manager.import_dataset(filename)
            if success:
                QMessageBox.information(self, "成功", message)
                self.update_dataset_stats()
                self.update_preview_table()
            else:
                QMessageBox.warning(self, "导入失败", message)
                
    def export_dataset(self):
        """导出数据集"""
        dataset_name = self.get_current_dataset_name()
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "保存数据集", f"{dataset_name}.json", "JSON Files (*.json)"
        )
        
        if filename:
            success = self.dataset_manager.export_dataset(dataset_name, filename)
            if success:
                QMessageBox.information(self, "成功", f"数据集已导出到 {filename}")
            else:
                QMessageBox.warning(self, "导出失败", "导出数据集时发生错误")

class TrainingMonitorTab(QWidget):
    """训练监控标签页"""
    
    def __init__(self, performance_monitor):
        super().__init__()
        self.performance_monitor = performance_monitor
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 训练控制
        control_group = QGroupBox("训练控制")
        control_layout = QHBoxLayout()
        
        self.start_training_button = QPushButton("开始训练")
        self.start_training_button.clicked.connect(self.start_training)
        control_layout.addWidget(self.start_training_button)
        
        self.stop_training_button = QPushButton("停止训练")
        self.stop_training_button.clicked.connect(self.stop_training)
        self.stop_training_button.setEnabled(False)
        control_layout.addWidget(self.stop_training_button)
        
        control_layout.addWidget(QLabel("训练数据集:"))
        self.training_dataset_combo = QComboBox()
        self.training_dataset_combo.addItems(["general_knowledge", "science_facts", "geography"])
        control_layout.addWidget(self.training_dataset_combo)
        
        control_layout.addWidget(QLabel("训练轮数:"))
        self.epochs_spinbox = QSpinBox()
        self.epochs_spinbox.setRange(1, 1000)
        self.epochs_spinbox.setValue(10)
        control_layout.addWidget(self.epochs_spinbox)
        
        control_layout.addStretch()
        
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)
        
        # 性能指标
        metrics_group = QGroupBox("性能指标")
        metrics_layout = QVBoxLayout()
        
        # 技能水平
        skills_layout = QHBoxLayout()
        
        skills = ["推理能力", "记忆能力", "规划能力", "执行能力", "学习能力", "创造力"]
        self.skill_bars = {}
        
        for skill in skills:
            skill_widget = QVBoxLayout()
            skill_widget.addWidget(QLabel(skill))
            progress_bar = QProgressBar()
            progress_bar.setValue(50)
            skill_widget.addWidget(progress_bar)
            skills_layout.addLayout(skill_widget)
            self.skill_bars[skill] = progress_bar
            
        metrics_layout.addLayout(skills_layout)
        
        # 图表
        self.chart_canvas = MplCanvas(self, width=10, height=6)
        metrics_layout.addWidget(self.chart_canvas)
        
        metrics_group.setLayout(metrics_layout)
        layout.addWidget(metrics_group)
        
        # 训练日志
        log_group = QGroupBox("训练日志")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        self.setLayout(layout)
        
        # 训练计时器
        self.training_timer = QTimer()
        self.training_timer.timeout.connect(self.update_training_progress)
        self.training_epoch = 0
        self.is_training = False
        
        # 初始更新
        self.update_performance_chart()
        
    def start_training(self):
        """开始训练"""
        if not self.is_training:
            self.is_training = True
            self.training_epoch = 0
            self.start_training_button.setEnabled(False)
            self.stop_training_button.setEnabled(True)
            self.training_timer.start(1000)  # 每秒更新一次
            
            dataset = self.training_dataset_combo.currentText()
            epochs = self.epochs_spinbox.value()
            
            self.log_text.append(f"[{datetime.now().strftime('%H:%M:%S')}] 开始训练 - 数据集: {dataset}, 轮数: {epochs}")
            
    def stop_training(self):
        """停止训练"""
        if self.is_training:
            self.is_training = False
            self.training_timer.stop()
            self.start_training_button.setEnabled(True)
            self.stop_training_button.setEnabled(False)
            
            self.log_text.append(f"[{datetime.now().strftime('%H:%M:%S')}] 训练停止 - 完成轮数: {self.training_epoch}")
            
    def update_training_progress(self):
        """更新训练进度"""
        if self.is_training:
            self.training_epoch += 1
            
            # 模拟性能提升
            metrics = {
                "accuracy": min(0.95, 0.5 + self.training_epoch * 0.045),
                "loss": max(0.05, 0.5 - self.training_epoch * 0.045),
                "reasoning": min(1.0, 0.5 + self.training_epoch * 0.05),
                "memory": min(1.0, 0.5 + self.training_epoch * 0.04),
                "planning": min(1.0, 0.5 + self.training_epoch * 0.045),
                "execution": min(1.0, 0.5 + self.training_epoch * 0.042),
                "learning": min(1.0, 0.5 + self.training_epoch * 0.048),
                "creativity": min(1.0, 0.3 + self.training_epoch * 0.035)
            }
            
            self.performance_monitor.update_metrics(metrics)
            
            # 更新进度条
            self.skill_bars["推理能力"].setValue(int(metrics["reasoning"] * 100))
            self.skill_bars["记忆能力"].setValue(int(metrics["memory"] * 100))
            self.skill_bars["规划能力"].setValue(int(metrics["planning"] * 100))
            self.skill_bars["执行能力"].setValue(int(metrics["execution"] * 100))
            self.skill_bars["学习能力"].setValue(int(metrics["learning"] * 100))
            self.skill_bars["创造力"].setValue(int(metrics["creativity"] * 100))
            
            # 更新图表
            self.update_performance_chart()
            
            # 更新日志
            if self.training_epoch % 5 == 0:
                self.log_text.append(f"[{datetime.now().strftime('%H:%M:%S')}] 轮次 {self.training_epoch}: "
                                   f"准确率={metrics['accuracy']:.3f}, 损失={metrics['loss']:.3f}")
            
            # 检查是否完成训练
            if self.training_epoch >= self.epochs_spinbox.value():
                self.stop_training()
                
    def update_performance_chart(self):
        """更新性能图表"""
        self.chart_canvas.axes.clear()
        
        recent_metrics = self.performance_monitor.get_recent_metrics(20)
        
        if recent_metrics["accuracy"]:
            epochs = list(range(len(recent_metrics["accuracy"])))
            
            self.chart_canvas.axes.plot(epochs, recent_metrics["accuracy"], 'b-', label='准确率', linewidth=2)
            self.chart_canvas.axes.plot(epochs, recent_metrics["loss"], 'r-', label='损失', linewidth=2)
            self.chart_canvas.axes.plot(epochs, recent_metrics["reasoning"], 'g--', label='推理能力', alpha=0.7)
            self.chart_canvas.axes.plot(epochs, recent_metrics["memory"], 'c--', label='记忆能力', alpha=0.7)
            
            self.chart_canvas.axes.set_xlabel('训练轮次')
            self.chart_canvas.axes.set_ylabel('性能指标')
            self.chart_canvas.axes.set_title('AGI系统性能趋势')
            self.chart_canvas.axes.legend()
            self.chart_canvas.axes.grid(True, alpha=0.3)
            
        self.chart_canvas.draw()

class SystemInteractionTab(QWidget):
    """系统交互标签页"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 交互界面
        interaction_group = QGroupBox("AGI系统交互")
        interaction_layout = QVBoxLayout()
        
        # 输入区域
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("输入问题:"))
        
        self.question_input = QLineEdit()
        self.question_input.setPlaceholderText("输入您的问题...")
        self.question_input.returnPressed.connect(self.ask_question)
        input_layout.addWidget(self.question_input)
        
        self.ask_button = QPushButton("提问")
        self.ask_button.clicked.connect(self.ask_question)
        input_layout.addWidget(self.ask_button)
        
        interaction_layout.addLayout(input_layout)
        
        # 对话历史
        self.conversation_text = QTextEdit()
        self.conversation_text.setReadOnly(True)
        interaction_layout.addWidget(self.conversation_text)
        
        interaction_group.setLayout(interaction_layout)
        layout.addWidget(interaction_group)
        
        # 系统状态
        status_group = QGroupBox("系统状态")
        status_layout = QVBoxLayout()
        
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(150)
        
        # 初始状态信息
        status_info = """
系统状态: 运行中
认知模块: 全部正常
内存使用: 1.2GB / 4.0GB
推理能力: 中等
学习模式: 主动学习
最后训练: 刚刚完成
        """
        self.status_text.setText(status_info.strip())
        
        status_layout.addWidget(self.status_text)
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        self.setLayout(layout)
        
    def ask_question(self):
        """提问处理"""
        question = self.question_input.text().strip()
        if not question:
            return
            
        # 添加用户问题到对话历史
        self.conversation_text.append(f"👤 用户: {question}")
        self.question_input.clear()
        
        # 模拟系统响应
        response = self.generate_response(question)
        self.conversation_text.append(f"🤖 AGI: {response}")
        
        # 滚动到底部
        self.conversation_text.verticalScrollBar().setValue(
            self.conversation_text.verticalScrollBar().maximum()
        )
        
    def generate_response(self, question):
        """生成响应（模拟）"""
        question_lower = question.lower()
        
        # 简单的模式匹配
        if "capital" in question_lower:
            if "france" in question_lower:
                return "The capital of France is Paris. It is located in the north-central part of the country on the Seine River."
            elif "germany" in question_lower:
                return "The capital of Germany is Berlin. It is known for its art scene and modern landmarks."
            elif "japan" in question_lower:
                return "The capital of Japan is Tokyo. It is one of the world's most populous metropolitan areas."
            else:
                return "I can tell you about capital cities. Could you specify which country you're interested in?"
                
        elif "planet" in question_lower:
            return "There are 8 planets in our solar system: Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, and Neptune."
            
        elif "ai" in question_lower or "artificial intelligence" in question_lower:
            return "Artificial Intelligence refers to the simulation of human intelligence in machines that are programmed to think and learn like humans."
            
        elif "learn" in question_lower or "training" in question_lower:
            return "I'm continuously learning from the knowledge provided through the training interface. My performance improves with more diverse and high-quality data."
            
        else:
            return f"I understand you're asking about '{question}'. This is an interesting topic. Based on my current knowledge, I'm processing your query to provide the most accurate response possible."

class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        
        # 初始化管理器
        self.dataset_manager = KnowledgeDatasetManager()
        self.performance_monitor = PerformanceMonitor()
        
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("EigenNet AGI 知识投喂与管理系统")
        self.setGeometry(100, 100, 1400, 900)
        
        # 设置应用样式
        self.set_dark_theme()
        
        # 创建中央部件和标签页
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        # 标题
        title_label = QLabel("EigenNet AGI 知识投喂与管理系统")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("padding: 10px; background-color: #2b2b2b; color: white; border-radius: 5px;")
        layout.addWidget(title_label)
        
        # 创建标签页
        self.tabs = QTabWidget()
        
        # 添加各个标签页
        self.knowledge_tab = KnowledgeFeedingTab(self.dataset_manager)
        self.training_tab = TrainingMonitorTab(self.performance_monitor)
        self.interaction_tab = SystemInteractionTab()
        
        self.tabs.addTab(self.knowledge_tab, "📚 知识投喂")
        self.tabs.addTab(self.training_tab, "📊 训练监控") 
        self.tabs.addTab(self.interaction_tab, "💬 系统交互")
        
        layout.addWidget(self.tabs)
        
        # 状态栏
        self.statusBar().showMessage("系统就绪 - EigenNet AGI 知识管理系统已启动")
        
    def set_dark_theme(self):
        """设置深色主题"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QTabWidget::pane {
                border: 1px solid #555;
                background-color: #323232;
            }
            QTabBar::tab {
                background-color: #404040;
                color: #ffffff;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #505050;
                border-bottom: 2px solid #64b5f6;
            }
            QTabBar::tab:hover {
                background-color: #484848;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: #363636;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #64b5f6;
            }
            QPushButton {
                background-color: #404040;
                color: #ffffff;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 5px 10px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton:pressed {
                background-color: #505050;
            }
            QPushButton:disabled {
                background-color: #333;
                color: #777;
            }
            QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                background-color: #404040;
                color: #ffffff;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 5px;
            }
            QTableWidget {
                background-color: #404040;
                color: #ffffff;
                gridline-color: #555;
                border: 1px solid #555;
            }
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #555;
            }
            QTableWidget::item:selected {
                background-color: #64b5f6;
                color: #000000;
            }
            QHeaderView::section {
                background-color: #505050;
                color: #ffffff;
                padding: 5px;
                border: 1px solid #555;
            }
            QProgressBar {
                border: 1px solid #555;
                border-radius: 3px;
                text-align: center;
                color: #ffffff;
            }
            QProgressBar::chunk {
                background-color: #64b5f6;
                border-radius: 2px;
            }
        """)

def main():
    app = QApplication(sys.argv)
    
    # 设置应用信息
    app.setApplicationName("EigenNet AGI Manager")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("EigenNet")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()