"""
升维分析系统 - 完整版
====================
功能：
1. 多种数据集生成（线性可分、同心圆、双月牙、高斯混合、高维稀疏）
2. 多种升维方法（多项式、特征交互、RBF核、核PCA）
3. 多模型对比（逻辑回归、SVM、随机森林、梯度提升）
4. 自动评估和报告生成
5. 可视化分析

作者：Dimensionality Analysis System
版本：2.0.0
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Ellipse
import seaborn as sns
from sklearn.datasets import make_classification, make_circles, make_moons, make_blobs
from sklearn.model_selection import train_test_split, cross_val_score, KFold
from sklearn.preprocessing import StandardScaler, PolynomialFeatures
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.decomposition import KernelPCA
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.feature_selection import mutual_info_classif
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any, Callable
from enum import Enum
import time
import warnings
import json
from datetime import datetime
from pathlib import Path
from itertools import product
import hashlib

warnings.filterwarnings('ignore')

# 设置中文和样式
plt.rcParams['font.family'] = 'Microsoft YaHei'
plt.rcParams['axes.unicode_minus'] = False
sns.set_style("whitegrid")
sns.set_palette("husl")


# ======================= 数据模型 =======================

class DatasetType(Enum):
    """数据集类型枚举"""
    LINEAR = "线性可分"
    CIRCLES = "同心圆"
    MOONS = "双月牙"
    BLOBS = "高斯混合"
    SPARSE = "高维稀疏"


class DimensionMethod(Enum):
    """升维方法枚举"""
    ORIGINAL = "原始特征"
    POLY_2 = "2阶多项式"
    POLY_3 = "3阶多项式"
    INTERACTION = "特征交互"
    RBF_FEATURES = "RBF特征"
    KERNEL_PCA_2D = "核PCA(2D)"
    KERNEL_PCA_5D = "核PCA(5D)"


class ModelType(Enum):
    """模型类型枚举"""
    LOGISTIC = "逻辑回归"
    SVM_RBF = "SVM(RBF)"
    RANDOM_FOREST = "随机森林"
    GRADIENT_BOOSTING = "梯度提升"


@dataclass
class ExperimentConfig:
    """实验配置"""
    dataset: DatasetType
    dim_method: DimensionMethod
    model: ModelType
    test_size: float = 0.3
    random_state: int = 42
    
    def get_id(self) -> str:
        """获取实验唯一标识"""
        return f"{self.dataset.value}_{self.dim_method.value}_{self.model.value}"


@dataclass
class ExperimentResult:
    """实验结果"""
    config: ExperimentConfig
    train_accuracy: float
    test_accuracy: float
    train_time: float
    feature_count: int
    generalization_gap: float  # 训练准确率 - 测试准确率
    cv_scores: Optional[List[float]] = None
    
    @property
    def is_overfitting(self) -> bool:
        """是否过拟合（泛化差距大于0.1）"""
        return self.generalization_gap > 0.1
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            '数据集': self.config.dataset.value,
            '升维方法': self.config.dim_method.value,
            '模型': self.config.model.value,
            '训练准确率': round(self.train_accuracy, 4),
            '测试准确率': round(self.test_accuracy, 4),
            '泛化差距': round(self.generalization_gap, 4),
            '训练时间(s)': round(self.train_time, 4),
            '特征数': self.feature_count
        }


# ======================= 数据生成器 =======================

class DataGenerator:
    """数据集生成器"""
    
    @staticmethod
    def generate_linear(n_samples: int = 500, n_features: int = 2, 
                        random_state: int = 42) -> Tuple[np.ndarray, np.ndarray]:
        """生成线性可分数据集"""
        X, y = make_classification(n_samples=n_samples, n_features=n_features,
                                   n_informative=n_features, n_redundant=0,
                                   n_clusters_per_class=1, random_state=random_state)
        return X, y
    
    @staticmethod
    def generate_circles(n_samples: int = 500, noise: float = 0.05,
                         random_state: int = 42) -> Tuple[np.ndarray, np.ndarray]:
        """生成同心圆数据集"""
        X, y = make_circles(n_samples=n_samples, noise=noise, 
                           factor=0.5, random_state=random_state)
        return X, y
    
    @staticmethod
    def generate_moons(n_samples: int = 500, noise: float = 0.05,
                       random_state: int = 42) -> Tuple[np.ndarray, np.ndarray]:
        """生成双月牙数据集"""
        X, y = make_moons(n_samples=n_samples, noise=noise, random_state=random_state)
        return X, y
    
    @staticmethod
    def generate_blobs(n_samples: int = 500, n_features: int = 2,
                       centers: int = 2, random_state: int = 42) -> Tuple[np.ndarray, np.ndarray]:
        """生成高斯混合数据集"""
        X, y = make_blobs(n_samples=n_samples, n_features=n_features,
                         centers=centers, random_state=random_state)
        return X, y
    
    @staticmethod
    def generate_sparse(n_samples: int = 500, n_features: int = 50,
                        n_informative: int = 5, random_state: int = 42) -> Tuple[np.ndarray, np.ndarray]:
        """生成高维稀疏数据集"""
        X, y = make_classification(n_samples=n_samples, n_features=n_features,
                                   n_informative=n_informative, n_redundant=0,
                                   n_repeated=0, n_clusters_per_class=1,
                                   flip_y=0.05, random_state=random_state)
        return X, y
    
    @classmethod
    def get_generator(cls, dataset_type: DatasetType) -> Callable:
        """获取对应的生成函数"""
        generators = {
            DatasetType.LINEAR: cls.generate_linear,
            DatasetType.CIRCLES: cls.generate_circles,
            DatasetType.MOONS: cls.generate_moons,
            DatasetType.BLOBS: cls.generate_blobs,
            DatasetType.SPARSE: cls.generate_sparse
        }
        return generators[dataset_type]


# ======================= 升维方法 =======================

class DimensionExpander:
    """维度扩展器 - 实现各种升维方法"""
    
    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.scaler = StandardScaler()
    
    def original_features(self, X: np.ndarray) -> np.ndarray:
        """原始特征（无升维）"""
        return X
    
    def polynomial_2(self, X: np.ndarray) -> np.ndarray:
        """2阶多项式特征"""
        poly = PolynomialFeatures(degree=2, include_bias=False)
        return poly.fit_transform(X)
    
    def polynomial_3(self, X: np.ndarray) -> np.ndarray:
        """3阶多项式特征"""
        poly = PolynomialFeatures(degree=3, include_bias=False)
        return poly.fit_transform(X)
    
    def interaction_only(self, X: np.ndarray) -> np.ndarray:
        """仅特征交互（无平方项）"""
        poly = PolynomialFeatures(degree=2, include_bias=False, interaction_only=True)
        return poly.fit_transform(X)
    
    def rbf_features(self, X: np.ndarray, n_centers: int = 20) -> np.ndarray:
        """RBF特征映射（使用随机中心）"""
        n_samples = X.shape[0]
        n_features = X.shape[1]
        
        # 随机选择中心点
        np.random.seed(self.random_state)
        centers_idx = np.random.choice(n_samples, min(n_centers, n_samples), replace=False)
        centers = X[centers_idx]
        
        # 计算RBF距离
        gamma = 1.0 / n_features
        rbf_features = np.zeros((n_samples, len(centers)))
        
        for i, center in enumerate(centers):
            distances = np.linalg.norm(X - center, axis=1)
            rbf_features[:, i] = np.exp(-gamma * distances**2)
        
        return rbf_features
    
    def kernel_pca_2d(self, X: np.ndarray) -> np.ndarray:
        """核PCA降维到2维（使用RBF核）"""
        kpca = KernelPCA(n_components=2, kernel='rbf', gamma=0.1, 
                         random_state=self.random_state)
        return kpca.fit_transform(X)
    
    def kernel_pca_5d(self, X: np.ndarray) -> np.ndarray:
        """核PCA降维到5维（使用RBF核）"""
        n_components = min(5, X.shape[1])
        kpca = KernelPCA(n_components=n_components, kernel='rbf', gamma=0.1,
                         random_state=self.random_state)
        return kpca.fit_transform(X)
    
    def apply_method(self, X: np.ndarray, method: DimensionMethod) -> Tuple[np.ndarray, int]:
        """应用指定的升维方法"""
        methods = {
            DimensionMethod.ORIGINAL: self.original_features,
            DimensionMethod.POLY_2: self.polynomial_2,
            DimensionMethod.POLY_3: self.polynomial_3,
            DimensionMethod.INTERACTION: self.interaction_only,
            DimensionMethod.RBF_FEATURES: self.rbf_features,
            DimensionMethod.KERNEL_PCA_2D: self.kernel_pca_2d,
            DimensionMethod.KERNEL_PCA_5D: self.kernel_pca_5d,
        }
        
        X_transformed = methods[method](X)
        return X_transformed, X_transformed.shape[1]


# ======================= 模型包装器 =======================

class ModelWrapper:
    """模型包装器 - 统一接口"""
    
    def __init__(self, random_state: int = 42):
        self.random_state = random_state
    
    def get_model(self, model_type: ModelType):
        """获取模型实例"""
        models = {
            ModelType.LOGISTIC: LogisticRegression(random_state=self.random_state, max_iter=1000),
            ModelType.SVM_RBF: SVC(kernel='rbf', random_state=self.random_state, probability=True),
            ModelType.RANDOM_FOREST: RandomForestClassifier(random_state=self.random_state, n_estimators=100),
            ModelType.GRADIENT_BOOSTING: GradientBoostingClassifier(random_state=self.random_state)
        }
        return models[model_type]


# ======================= 实验运行器 =======================

class ExperimentRunner:
    """实验运行器 - 执行所有实验组合"""
    
    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.data_gen = DataGenerator()
        self.dim_expander = DimensionExpander(random_state=random_state)
        self.model_wrapper = ModelWrapper(random_state=random_state)
        self.results: List[ExperimentResult] = []
        
    def run_single_experiment(self, config: ExperimentConfig) -> ExperimentResult:
        """
        运行单个实验
        
        Args:
            config: 实验配置
            
        Returns:
            实验结果
        """
        # 1. 生成数据
        generator = self.data_gen.get_generator(config.dataset)
        X, y = generator(random_state=config.random_state)
        
        # 2. 标准化
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # 3. 升维
        X_expanded, n_features = self.dim_expander.apply_method(X_scaled, config.dim_method)
        
        # 4. 划分数据集
        X_train, X_test, y_train, y_test = train_test_split(
            X_expanded, y, test_size=config.test_size, 
            random_state=config.random_state, stratify=y
        )
        
        # 5. 训练模型
        model = self.model_wrapper.get_model(config.model)
        
        start_time = time.time()
        model.fit(X_train, y_train)
        train_time = time.time() - start_time
        
        # 6. 评估
        train_pred = model.predict(X_train)
        test_pred = model.predict(X_test)
        
        train_acc = accuracy_score(y_train, train_pred)
        test_acc = accuracy_score(y_test, test_pred)
        generalization_gap = train_acc - test_acc
        
        # 7. 交叉验证
        try:
            cv = KFold(n_splits=5, shuffle=True, random_state=config.random_state)
            cv_scores = cross_val_score(model, X_expanded, y, cv=cv, scoring='accuracy')
        except:
            cv_scores = []
        
        return ExperimentResult(
            config=config,
            train_accuracy=train_acc,
            test_accuracy=test_acc,
            train_time=train_time,
            feature_count=n_features,
            generalization_gap=generalization_gap,
            cv_scores=cv_scores.tolist() if len(cv_scores) > 0 else None
        )
    
    def run_all_experiments(self, 
                           datasets: List[DatasetType] = None,
                           dim_methods: List[DimensionMethod] = None,
                           models: List[ModelType] = None,
                           verbose: bool = True) -> List[ExperimentResult]:
        """
        运行所有实验组合
        
        Args:
            datasets: 数据集列表，None表示全部
            dim_methods: 升维方法列表，None表示全部
            models: 模型列表，None表示全部
            verbose: 是否打印进度
            
        Returns:
            实验结果列表
        """
        if datasets is None:
            datasets = list(DatasetType)
        if dim_methods is None:
            dim_methods = list(DimensionMethod)
        if models is None:
            models = list(ModelType)
        
        total = len(datasets) * len(dim_methods) * len(models)
        
        if verbose:
            print(f"\n{'='*60}")
            print(f"开始运行实验 - 总计 {total} 个组合")
            print(f"{'='*60}\n")
        
        results = []
        for i, (dataset, dim_method, model) in enumerate(product(datasets, dim_methods, models)):
            if verbose:
                print(f"[{i+1}/{total}] {dataset.value} + {dim_method.value} + {model.value}")
            
            config = ExperimentConfig(
                dataset=dataset,
                dim_method=dim_method,
                model=model,
                random_state=self.random_state
            )
            
            try:
                result = self.run_single_experiment(config)
                results.append(result)
            except Exception as e:
                if verbose:
                    print(f"  警告: 实验失败 - {str(e)[:50]}")
        
        self.results = results
        
        if verbose:
            print(f"\n✅ 实验完成！成功: {len(results)}/{total}")
        
        return results


# ======================= 分析器和报告生成 =======================

class Analyzer:
    """分析器 - 分析实验结果并生成报告"""
    
    def __init__(self, results: List[ExperimentResult]):
        self.results = results
        self.df = self._to_dataframe()
    
    def _to_dataframe(self) -> pd.DataFrame:
        """将结果转换为DataFrame"""
        rows = [r.to_dict() for r in self.results]
        return pd.DataFrame(rows)
    
    def get_best_for_dataset(self) -> pd.DataFrame:
        """获取每个数据集的最佳配置"""
        best_configs = []
        
        for dataset in self.df['数据集'].unique():
            df_dataset = self.df[self.df['数据集'] == dataset]
            # 按测试准确率降序，泛化差距升序排序
            best = df_dataset.sort_values(['测试准确率', '泛化差距'], 
                                         ascending=[False, True]).iloc[0]
            best_configs.append(best)
        
        return pd.DataFrame(best_configs)
    
    def get_method_ranking(self) -> pd.DataFrame:
        """升维方法性能排名"""
        ranking = self.df.groupby('升维方法').agg({
            '测试准确率': 'mean',
            '训练时间(s)': 'mean',
            '特征数': 'mean'
        }).round(4).sort_values('测试准确率', ascending=False)
        return ranking
    
    def get_model_ranking(self) -> pd.DataFrame:
        """模型性能排名"""
        ranking = self.df.groupby('模型').agg({
            '测试准确率': 'mean',
            '训练时间(s)': 'mean'
        }).round(4).sort_values('测试准确率', ascending=False)
        return ranking
    
    def get_overfitting_warnings(self, threshold: float = 0.1) -> pd.DataFrame:
        """获取过拟合警告"""
        overfit = self.df[self.df['泛化差距'] > threshold].copy()
        overfit = overfit.sort_values('泛化差距', ascending=False)
        return overfit
    
    def generate_report(self, output_path: Path) -> str:
        """生成Markdown格式报告"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        report = f"""# 升维分析系统基准测试报告

生成时间: {timestamp}

测试组合总数: {len(self.results)}

## 各数据集最佳配置

| 数据集 | 最佳升维方法 | 最佳模型 | 测试准确率 | 泛化差距 |
|--------|-------------|----------|-----------|----------|
"""
        
        best_df = self.get_best_for_dataset()
        for _, row in best_df.iterrows():
            report += f"| {row['数据集']} | {row['升维方法']} | {row['模型']} | {row['测试准确率']:.4f} | {row['泛化差距']:.4f} |\n"
        
        report += f"""
## 升维方法平均性能排名

| 升维方法 | 测试准确率 | 训练时间(s) | 特征数 |
|----------|-----------|-------------|--------|
"""
        
        method_ranking = self.get_method_ranking()
        for method, row in method_ranking.iterrows():
            report += f"| {method} | {row['测试准确率']:.4f} | {row['训练时间(s)']:.4f} | {row['特征数']:.1f} |\n"
        
        report += f"""
## 模型平均性能排名

| 模型 | 测试准确率 | 训练时间(s) |
|------|-----------|-------------|
"""
        
        model_ranking = self.get_model_ranking()
        for model, row in model_ranking.iterrows():
            report += f"| {model} | {row['测试准确率']:.4f} | {row['训练时间(s)']:.4f} |\n"
        
        report += f"""
## 过拟合警告

以下配置存在严重过拟合风险（泛化差距 > 0.1）:

| 序号 | 数据集 | 升维方法 | 模型 | 泛化差距 |
|------|--------|----------|------|----------|
"""
        
        overfit_df = self.get_overfitting_warnings(threshold=0.1)
        for idx, (_, row) in enumerate(overfit_df.iterrows()):
            report += f"| {idx} | {row['数据集']} | {row['升维方法']} | {row['模型']} | {row['泛化差距']:.4f} |\n"
        
        # 保存报告
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        return report


# ======================= 可视化类 =======================

class Visualizer:
    """可视化器"""
    
    def __init__(self, dpi: int = 150):
        self.dpi = dpi
    
    def plot_dataset(self, X: np.ndarray, y: np.ndarray, title: str,
                    save_path: Optional[Path] = None) -> plt.Figure:
        """绘制数据集散点图"""
        fig, ax = plt.subplots(figsize=(8, 6))
        
        colors = ['#FF6B6B', '#4ECDC4']
        for i, label in enumerate(np.unique(y)):
            mask = y == label
            ax.scatter(X[mask, 0], X[mask, 1], c=colors[i], 
                      label=f'类别 {label}', alpha=0.7, s=30)
        
        ax.set_xlabel('特征 1')
        ax.set_ylabel('特征 2')
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            fig.savefig(save_path, dpi=self.dpi, bbox_inches='tight')
            plt.close(fig)
        
        return fig
    
    def plot_comparison_matrix(self, df: pd.DataFrame, 
                               save_path: Optional[Path] = None) -> plt.Figure:
        """绘制方法-模型性能热图"""
        fig, axes = plt.subplots(1, 2, figsize=(16, 8))
        
        # 1. 测试准确率热图
        pivot_acc = df.pivot_table(index='升维方法', columns='模型', 
                                   values='测试准确率', aggfunc='mean')
        
        sns.heatmap(pivot_acc, annot=True, fmt='.3f', cmap='YlOrRd',
                   ax=axes[0], cbar_kws={'label': '测试准确率'})
        axes[0].set_title('各组合测试准确率对比', fontsize=14, fontweight='bold')
        
        # 2. 泛化差距热图
        pivot_gap = df.pivot_table(index='升维方法', columns='模型',
                                   values='泛化差距', aggfunc='mean')
        
        sns.heatmap(pivot_gap, annot=True, fmt='.3f', cmap='RdYlBu_r',
                   ax=axes[1], cbar_kws={'label': '泛化差距'})
        axes[1].set_title('各组合泛化差距（过拟合风险）', fontsize=14, fontweight='bold')
        
        plt.suptitle('升维方法 × 模型 性能对比矩阵', fontsize=16, fontweight='bold', y=1.02)
        plt.tight_layout()
        
        if save_path:
            fig.savefig(save_path, dpi=self.dpi, bbox_inches='tight')
            plt.close(fig)
        
        return fig
    
    def plot_method_performance(self, df: pd.DataFrame,
                                save_path: Optional[Path] = None) -> plt.Figure:
        """绘制升维方法性能对比图"""
        fig, axes = plt.subplots(1, 3, figsize=(18, 5))
        
        method_stats = df.groupby('升维方法').agg({
            '测试准确率': ['mean', 'std'],
            '训练时间(s)': 'mean',
            '特征数': 'mean'
        }).round(4)
        
        method_names = method_stats.index.tolist()
        
        # 1. 准确率柱状图
        acc_means = method_stats[('测试准确率', 'mean')]
        acc_stds = method_stats[('测试准确率', 'std')]
        
        colors = plt.cm.viridis(np.linspace(0.2, 0.9, len(method_names)))
        bars = axes[0].bar(method_names, acc_means, yerr=acc_stds, 
                          capsize=5, color=colors, edgecolor='black')
        axes[0].set_ylabel('平均测试准确率')
        axes[0].set_title('升维方法准确率对比', fontsize=12, fontweight='bold')
        axes[0].tick_params(axis='x', rotation=45)
        axes[0].set_ylim(0, 1)
        axes[0].axhline(y=0.5, color='red', linestyle='--', alpha=0.5)
        
        # 2. 训练时间对比
        times = method_stats[('训练时间(s)', 'mean')]
        axes[1].barh(method_names, times, color=colors, edgecolor='black')
        axes[1].set_xlabel('平均训练时间 (秒)')
        axes[1].set_title('升维方法效率对比', fontsize=12, fontweight='bold')
        
        # 3. 准确率 vs 特征数散点图
        n_features = method_stats[('特征数', 'mean')]
        scatter = axes[2].scatter(n_features, acc_means, s=times * 50, 
                                  c=range(len(method_names)), cmap='viridis',
                                  alpha=0.7, edgecolors='black')
        
        for i, name in enumerate(method_names):
            axes[2].annotate(name, (n_features.iloc[i], acc_means.iloc[i]),
                            fontsize=8, ha='center', va='bottom')
        
        axes[2].set_xlabel('特征数量')
        axes[2].set_ylabel('测试准确率')
        axes[2].set_title('准确率 vs 特征数 (点大小=训练时间)', fontsize=12, fontweight='bold')
        axes[2].set_xscale('log')
        
        plt.tight_layout()
        
        if save_path:
            fig.savefig(save_path, dpi=self.dpi, bbox_inches='tight')
            plt.close(fig)
        
        return fig
    
    def plot_dataset_comparison(self, df: pd.DataFrame,
                                save_path: Optional[Path] = None) -> plt.Figure:
        """绘制不同数据集上的性能对比"""
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        axes = axes.flatten()
        
        datasets = df['数据集'].unique()
        methods = df['升维方法'].unique()
        
        for idx, dataset in enumerate(datasets):
            ax = axes[idx]
            df_dataset = df[df['数据集'] == dataset]
            
            # 计算每个方法在所有模型上的平均准确率
            method_acc = df_dataset.groupby('升维方法')['测试准确率'].mean().sort_values()
            
            colors = ['#4ECDC4' if acc >= 0.9 else '#FF6B6B' if acc >= 0.7 else '#FFD166' 
                      for acc in method_acc.values]
            
            bars = ax.barh(method_acc.index, method_acc.values, color=colors, edgecolor='black')
            ax.set_xlim(0, 1)
            ax.set_xlabel('测试准确率')
            ax.set_title(f'{dataset} 数据集 - 各升维方法性能', fontsize=12, fontweight='bold')
            
            # 添加数值标签
            for bar, acc in zip(bars, method_acc.values):
                ax.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height()/2,
                       f'{acc:.3f}', va='center', fontsize=9)
            
            # 添加基准线
            ax.axvline(x=0.8, color='gray', linestyle='--', alpha=0.5, label='良好基准线')
        
        plt.suptitle('各数据集上不同升维方法的性能对比', fontsize=16, fontweight='bold', y=1.02)
        plt.tight_layout()
        
        if save_path:
            fig.savefig(save_path, dpi=self.dpi, bbox_inches='tight')
            plt.close(fig)
        
        return fig
    
    def create_dashboard(self, df: pd.DataFrame, 
                         save_path: Optional[Path] = None) -> plt.Figure:
        """创建综合仪表板"""
        fig = plt.figure(figsize=(20, 14))
        
        # 1. 最佳配置表格
        ax1 = fig.add_subplot(2, 2, 1)
        ax1.axis('off')
        best_df = df.sort_values('测试准确率', ascending=False).head(10)
        
        table_data = best_df[['数据集', '升维方法', '模型', '测试准确率', '泛化差距']].values
        table = ax1.table(cellText=table_data,
                         colLabels=['数据集', '升维方法', '模型', '准确率', '泛化差距'],
                         cellLoc='center', loc='center',
                         colColours=['#4472C4'] * 5)
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 1.5)
        ax1.set_title('🏆 Top 10 最佳配置', fontsize=14, fontweight='bold', pad=20)
        
        # 2. 方法准确率雷达图
        ax2 = fig.add_subplot(2, 2, 2, projection='polar')
        method_avg = df.groupby('升维方法')['测试准确率'].mean()
        methods = method_avg.index.tolist()
        values = method_avg.values.tolist()
        values += values[:1]
        angles = np.linspace(0, 2 * np.pi, len(methods), endpoint=False).tolist()
        angles += angles[:1]
        
        ax2.plot(angles, values, 'o-', linewidth=2, color='#4472C4')
        ax2.fill(angles, values, alpha=0.25, color='#4472C4')
        ax2.set_xticks(angles[:-1])
        ax2.set_xticklabels(methods, size=8)
        ax2.set_ylim(0, 1)
        ax2.set_title('升维方法准确率雷达图', fontsize=12, fontweight='bold', pad=20)
        
        # 3. 准确率分布箱线图
        ax3 = fig.add_subplot(2, 2, 3)
        methods_unique = df['升维方法'].unique()
        acc_data = [df[df['升维方法'] == m]['测试准确率'].values for m in methods_unique]
        
        bp = ax3.boxplot(acc_data, labels=methods_unique, patch_artist=True)
        for patch, color in zip(bp['boxes'], plt.cm.viridis(np.linspace(0.3, 0.9, len(methods_unique)))):
            patch.set_facecolor(color)
        ax3.set_ylabel('测试准确率')
        ax3.set_title('各升维方法准确率分布', fontsize=12, fontweight='bold')
        ax3.tick_params(axis='x', rotation=45)
        ax3.set_ylim(0, 1)
        
        # 4. 过拟合风险散点图
        ax4 = fig.add_subplot(2, 2, 4)
        df['is_overfit'] = df['泛化差距'] > 0.1
        
        colors = ['#4ECDC4' if not overfit else '#FF6B6B' 
                  for overfit in df['is_overfit']]
        
        scatter = ax4.scatter(df['训练时间(s)'], df['测试准确率'], 
                             s=df['特征数'] / 10, c=colors, alpha=0.6, edgecolors='black')
        
        # 添加标签
        for _, row in df[df['泛化差距'] > 0.15].iterrows():
            ax4.annotate(f"{row['数据集'][:4]}", 
                        (row['训练时间(s)'], row['测试准确率']),
                        fontsize=7, ha='center', va='bottom')
        
        ax4.set_xlabel('训练时间 (秒)')
        ax4.set_ylabel('测试准确率')
        ax4.set_title('过拟合风险分析 (红色=高风险)', fontsize=12, fontweight='bold')
        ax4.grid(True, alpha=0.3)
        
        plt.suptitle('📊 升维分析系统综合仪表板', fontsize=18, fontweight='bold', y=0.98)
        plt.tight_layout()
        
        if save_path:
            fig.savefig(save_path, dpi=self.dpi, bbox_inches='tight')
            plt.close(fig)
        
        return fig


# ======================= 主系统 =======================

class DimensionalityAnalysisSystem:
    """升维分析系统主类"""
    
    def __init__(self, output_dir: str = "dimensionality_analysis_output",
                 random_state: int = 42, dpi: int = 150):
        """
        初始化系统
        
        Args:
            output_dir: 输出目录
            random_state: 随机种子
            dpi: 图像分辨率
        """
        self.output_dir = Path(output_dir)
        self.random_state = random_state
        self.dpi = dpi
        self.runner = ExperimentRunner(random_state=random_state)
        self.visualizer = Visualizer(dpi=dpi)
        self.results: List[ExperimentResult] = []
        self.analyzer: Optional[Analyzer] = None
        
        # 创建输出目录
        self.output_dir.mkdir(exist_ok=True)
        (self.output_dir / "figures").mkdir(exist_ok=True)
        (self.output_dir / "data").mkdir(exist_ok=True)
        
        # 设置随机种子
        np.random.seed(random_state)
    
    def run_analysis(self, 
                    datasets: List[DatasetType] = None,
                    dim_methods: List[DimensionMethod] = None,
                    models: List[ModelType] = None,
                    verbose: bool = True) -> 'DimensionalityAnalysisSystem':
        """
        运行完整分析
        
        Args:
            datasets: 数据集列表
            dim_methods: 升维方法列表
            models: 模型列表
            verbose: 是否打印进度
            
        Returns:
            self (支持链式调用)
        """
        # 运行实验
        self.results = self.runner.run_all_experiments(
            datasets=datasets,
            dim_methods=dim_methods,
            models=models,
            verbose=verbose
        )
        
        # 创建分析器
        self.analyzer = Analyzer(self.results)
        
        return self
    
    def generate_visualizations(self) -> 'DimensionalityAnalysisSystem':
        """生成所有可视化图表"""
        if self.analyzer is None:
            raise ValueError("请先运行 run_analysis()")
        
        print("\n📊 生成可视化图表...")
        
        df = self.analyzer.df
        
        # 1. 性能对比矩阵
        self.visualizer.plot_comparison_matrix(
            df, save_path=self.output_dir / "figures" / "comparison_matrix.png"
        )
        print("  ✓ 性能对比矩阵")
        
        # 2. 方法性能对比
        self.visualizer.plot_method_performance(
            df, save_path=self.output_dir / "figures" / "method_performance.png"
        )
        print("  ✓ 方法性能对比")
        
        # 3. 数据集对比
        self.visualizer.plot_dataset_comparison(
            df, save_path=self.output_dir / "figures" / "dataset_comparison.png"
        )
        print("  ✓ 数据集对比")
        
        # 4. 综合仪表板
        self.visualizer.create_dashboard(
            df, save_path=self.output_dir / "figures" / "dashboard.png"
        )
        print("  ✓ 综合仪表板")
        
        # 5. 生成各数据集的样本图
        data_gen = DataGenerator()
        datasets_info = [
            (DatasetType.LINEAR, "线性可分数据集"),
            (DatasetType.CIRCLES, "同心圆数据集"),
            (DatasetType.MOONS, "双月牙数据集"),
            (DatasetType.BLOBS, "高斯混合数据集"),
            (DatasetType.SPARSE, "高维稀疏数据集（前2维）"),
        ]
        
        for dataset_type, title in datasets_info:
            generator = data_gen.get_generator(dataset_type)
            X, y = generator(random_state=self.random_state)
            
            # 对于高维数据，取前两维可视化
            if X.shape[1] > 2:
                X_viz = X[:, :2]
            else:
                X_viz = X
            
            self.visualizer.plot_dataset(
                X_viz, y, title,
                save_path=self.output_dir / "figures" / f"{dataset_type.value}_sample.png"
            )
        print("  ✓ 数据集样本图")
        
        return self
    
    def generate_report(self) -> 'DimensionalityAnalysisSystem':
        """生成分析报告"""
        if self.analyzer is None:
            raise ValueError("请先运行 run_analysis()")
        
        print("\n📝 生成分析报告...")
        
        # 1. Markdown报告
        report_path = self.output_dir / "dimensionality_report.md"
        self.analyzer.generate_report(report_path)
        print(f"  ✓ 报告已保存: {report_path}")
        
        # 2. CSV结果导出
        csv_path = self.output_dir / "data" / "experiment_results.csv"
        self.analyzer.df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"  ✓ 结果已导出: {csv_path}")
        
        # 3. JSON结果导出（可序列化版本）
        json_path = self.output_dir / "data" / "experiment_results.json"
        results_dict = [r.to_dict() for r in self.results]
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results_dict, f, indent=2, ensure_ascii=False)
        print(f"  ✓ JSON已导出: {json_path}")
        
        # 4. 控制台输出摘要
        self._print_summary()
        
        return self
    
    def _print_summary(self):
        """打印控制台摘要"""
        print("\n" + "="*60)
        print("📈 分析摘要")
        print("="*60)
        
        best_df = self.analyzer.get_best_for_dataset()
        print("\n🏆 各数据集最佳配置:")
        for _, row in best_df.iterrows():
            print(f"  {row['数据集']}: {row['升维方法']} + {row['模型']} = {row['测试准确率']:.4f}")
        
        print("\n📊 升维方法排名:")
        method_ranking = self.analyzer.get_method_ranking()
        for i, (method, row) in enumerate(method_ranking.iterrows(), 1):
            print(f"  {i}. {method}: {row['测试准确率']:.4f} (时间: {row['训练时间(s)']:.4f}s)")
        
        print("\n⚠️ 过拟合风险配置数:", len(self.analyzer.get_overfitting_warnings()))
    
    def save_configuration(self) -> 'DimensionalityAnalysisSystem':
        """保存系统配置"""
        config = {
            'random_state': self.random_state,
            'dpi': self.dpi,
            'output_dir': str(self.output_dir),
            'timestamp': datetime.now().isoformat(),
            'n_experiments': len(self.results)
        }
        
        config_path = self.output_dir / "system_config.json"
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        
        return self
    
    def run_complete(self, verbose: bool = True) -> Path:
        """
        运行完整分析流程
        
        Args:
            verbose: 是否打印进度
            
        Returns:
            输出目录路径
        """
        print("\n" + "="*60)
        print("🧠 升维分析系统 v2.0")
        print("="*60)
        
        # 1. 运行实验
        self.run_analysis(verbose=verbose)
        
        # 2. 生成可视化
        self.generate_visualizations()
        
        # 3. 生成报告
        self.generate_report()
        
        # 4. 保存配置
        self.save_configuration()
        
        print("\n" + "="*60)
        print(f"✅ 分析完成！所有文件保存在: {self.output_dir}")
        print("="*60)
        
        return self.output_dir


# ======================= 快速测试函数 =======================

def quick_test():
    """快速测试函数 - 运行小型实验"""
    print("运行快速测试...")
    
    # 使用较少的数据集和方法进行快速测试
    datasets = [DatasetType.LINEAR, DatasetType.CIRCLES]
    dim_methods = [DimensionMethod.ORIGINAL, DimensionMethod.POLY_2]
    models = [ModelType.LOGISTIC, ModelType.SVM_RBF]
    
    system = DimensionalityAnalysisSystem(output_dir="quick_test_output")
    system.run_analysis(datasets=datasets, dim_methods=dim_methods, models=models, verbose=True)
    system.generate_visualizations()
    system.generate_report()
    
    print("\n✅ 快速测试完成！")


# ======================= 命令行入口 =======================

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='升维分析系统')
    parser.add_argument('--output', '-o', default='dimensionality_analysis_output',
                       help='输出目录')
    parser.add_argument('--seed', type=int, default=42,
                       help='随机种子')
    parser.add_argument('--dpi', type=int, default=150,
                       help='图像分辨率')
    parser.add_argument('--quick', action='store_true',
                       help='运行快速测试')
    
    args = parser.parse_args()
    
    if args.quick:
        quick_test()
    else:
        system = DimensionalityAnalysisSystem(
            output_dir=args.output,
            random_state=args.seed,
            dpi=args.dpi
        )
        system.run_complete()


if __name__ == "__main__":
    main()