import numpy as np
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
import seaborn as sns
from mpl_toolkits.mplot3d import Axes3D
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.decomposition import PCA, KernelPCA
from sklearn.manifold import TSNE
from sklearn.datasets import make_classification, make_circles, make_moons
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, mean_squared_error
from sklearn.feature_selection import SelectKBest, f_classif
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

print("=" * 80)
print("高级升维操作可视化与多维分析系统")
print("=" * 80)

class DimensionalityAugmentation:
    """升维操作综合类"""
    
    @staticmethod
    def kronecker_product(A, B):
        """克罗内克积"""
        return np.kron(A, B)
    
    @staticmethod
    def outer_product(u, v):
        """外积"""
        return np.outer(u, v)
    
    @staticmethod
    def polynomial_features(X, degree=2):
        """多项式特征映射"""
        poly = PolynomialFeatures(degree=degree, include_bias=False)
        return poly.fit_transform(X), poly.get_feature_names_out()
    
    @staticmethod
    def kernel_pca_features(X, n_components=3, kernel='rbf'):
        """核PCA特征提取"""
        kpca = KernelPCA(n_components=n_components, kernel=kernel)
        return kpca.fit_transform(X)
    
    @staticmethod
    def tensor_product(*arrays):
        """张量积（多数组外积推广）"""
        result = arrays[0]
        for arr in arrays[1:]:
            result = np.tensordot(result, arr, axes=0)
        return result
    
    @staticmethod
    def feature_interaction(X):
        """特征交互项"""
        n_features = X.shape[1]
        interactions = []
        feature_names = []
        
        for i in range(n_features):
            for j in range(i, n_features):
                interactions.append(X[:, i] * X[:, j])
                feature_names.append(f"x{i}*x{j}")
        
        return np.column_stack(interactions), feature_names

# 1. 增强的克罗内克积可视化
print("\n1. 增强的克罗内克积可视化与动态演示")
def enhanced_kronecker_visualization():
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    plt.subplots_adjust(bottom=0.25)
    
    # 初始矩阵
    A = np.array([[1, 2], [3, 4]])
    B = np.array([[0, 1], [1, 0]])
    kron_result = DimensionalityAugmentation.kronecker_product(A, B)
    
    # 主可视化
    sns.heatmap(A, annot=True, cmap='Blues', cbar=False, ax=ax1, square=True, fmt='d')
    ax1.set_title(f'矩阵 A\n{A.shape}')
    
    sns.heatmap(B, annot=True, cmap='Reds', cbar=False, ax=ax2, square=True, fmt='d')
    ax2.set_title(f'矩阵 B\n{B.shape}')
    
    sns.heatmap(kron_result, annot=True, cmap='viridis', ax=ax3, square=True, fmt='d')
    ax3.set_title(f'克罗内克积 A⊗B\n{kron_result.shape}')
    
    # 维度增长分析
    sizes = range(1, 6)
    growth_data = []
    for size in sizes:
        A_temp = np.random.rand(size, size)
        B_temp = np.random.rand(size, size)
        kron_temp = DimensionalityAugmentation.kronecker_product(A_temp, B_temp)
        growth_data.append(kron_temp.size)
    
    ax4.plot(sizes, growth_data, 'bo-', linewidth=3, markersize=8)
    ax4.set_xlabel('输入矩阵维度 (n×n)')
    ax4.set_ylabel('输出矩阵元素数量')
    ax4.set_title('克罗内克积维度指数增长')
    ax4.grid(True, alpha=0.3)
    
    for i, size in enumerate(sizes):
        ax4.annotate(f'{growth_data[i]}', (size, growth_data[i]), 
                    textcoords="offset points", xytext=(0,10), ha='center')
    
    plt.tight_layout()
    
    # 交互式滑块
    ax_slider = plt.axes([0.2, 0.1, 0.6, 0.03])
    size_slider = Slider(ax_slider, '矩阵大小', 1, 5, valinit=2, valstep=1)
    
    def update(val):
        size = int(size_slider.val)
        A_new = np.random.randint(1, 10, size=(size, size))
        B_new = np.random.randint(0, 2, size=(size, size))
        kron_new = DimensionalityAugmentation.kronecker_product(A_new, B_new)
        
        # 更新热图
        ax1.clear()
        sns.heatmap(A_new, annot=True, cmap='Blues', cbar=False, ax=ax1, square=True, fmt='d')
        ax1.set_title(f'矩阵 A\n{A_new.shape}')
        
        ax2.clear()
        sns.heatmap(B_new, annot=True, cmap='Reds', cbar=False, ax=ax2, square=True, fmt='d')
        ax2.set_title(f'矩阵 B\n{B_new.shape}')
        
        ax3.clear()
        sns.heatmap(kron_new, annot=True, cmap='viridis', ax=ax3, square=True, fmt='d')
        ax3.set_title(f'克罗内克积 A⊗B\n{kron_new.shape}')
        
        plt.draw()
    
    size_slider.on_changed(update)
    plt.show()

enhanced_kronecker_visualization()

# 2. 多方法升维比较
print("\n2. 多方法升维比较分析")
def comprehensive_dimensionality_comparison():
    # 生成示例数据
    np.random.seed(42)
    X_original = np.random.randn(100, 3)
    
    methods = {
        '原始数据': X_original,
        '2阶多项式': DimensionalityAugmentation.polynomial_features(X_original, 2)[0],
        '3阶多项式': DimensionalityAugmentation.polynomial_features(X_original, 3)[0],
        '特征交互': DimensionalityAugmentation.feature_interaction(X_original)[0],
        '核PCA(RBF)': DimensionalityAugmentation.kernel_pca_features(X_original, 3)
    }
    
    # 可视化比较
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    axes = axes.ravel()
    
    for idx, (method_name, X_transformed) in enumerate(methods.items()):
        if idx >= 6:
            break
            
        ax = axes[idx]
        
        if X_transformed.shape[1] >= 3:
            # 3D可视化
            ax = fig.add_subplot(2, 3, idx+1, projection='3d')
            scatter = ax.scatter(X_transformed[:, 0], X_transformed[:, 1], 
                               X_transformed[:, 2], c=X_original[:, 0], 
                               cmap='viridis', alpha=0.7)
            ax.set_title(f'{method_name}\n{X_transformed.shape}维')
            ax.set_xlabel('维度1')
            ax.set_ylabel('维度2')
            ax.set_zlabel('维度3')
            plt.colorbar(scatter, ax=ax, shrink=0.6)
        else:
            # 2D可视化
            ax.scatter(X_transformed[:, 0], X_transformed[:, 1] if X_transformed.shape[1] > 1 
                      else np.zeros_like(X_transformed[:, 0]), 
                      c=X_original[:, 0], cmap='viridis', alpha=0.7)
            ax.set_title(f'{method_name}\n{X_transformed.shape}维')
            ax.set_xlabel('维度1')
            ax.set_ylabel('维度2' if X_transformed.shape[1] > 1 else '')
    
    # 移除多余的子图
    for idx in range(len(methods), 6):
        axes[idx].set_visible(False)
    
    plt.tight_layout()
    plt.show()
    
    # 维度增长统计
    stats_data = []
    for method_name, X_transformed in methods.items():
        stats_data.append({
            '方法': method_name,
            '原始维度': X_original.shape[1],
            '新维度': X_transformed.shape[1],
            '维度增长率': f"{(X_transformed.shape[1] / X_original.shape[1] - 1) * 100:.1f}%",
            '总特征数': X_transformed.shape[1]
        })
    
    stats_df = pd.DataFrame(stats_data)
    print("\n各升维方法统计比较:")
    print(stats_df.to_string(index=False))

comprehensive_dimensionality_comparison()

# 3. 非线性数据升维效果演示
print("\n3. 非线性数据升维效果演示")
def nonlinear_data_demonstration():
    # 生成非线性数据集
    np.random.seed(42)
    X_circles, y_circles = make_circles(n_samples=300, noise=0.1, factor=0.3)
    X_moons, y_moons = make_moons(n_samples=300, noise=0.1)
    
    datasets = [
        ('同心圆', X_circles, y_circles),
        ('双月牙', X_moons, y_moons)
    ]
    
    fig = plt.figure(figsize=(20, 12))
    
    for dataset_idx, (dataset_name, X, y) in enumerate(datasets):
        # 应用不同升维方法
        methods = {
            '原始数据': (X, ['x1', 'x2']),
            '2阶多项式': DimensionalityAugmentation.polynomial_features(X, 2),
            '3阶多项式': DimensionalityAugmentation.polynomial_features(X, 3),
            '核PCA': (DimensionalityAugmentation.kernel_pca_features(X, 2), ['PC1', 'PC2'])
        }
        
        # 可视化每个方法
        for method_idx, (method_name, (X_transformed, feature_names)) in enumerate(methods.items()):
            ax = plt.subplot(2, 4, dataset_idx * 4 + method_idx + 1)
            
            if X_transformed.shape[1] >= 2:
                scatter = ax.scatter(X_transformed[:, 0], X_transformed[:, 1], 
                                   c=y, cmap='coolwarm', alpha=0.7, s=50)
                ax.set_xlabel(feature_names[0] if len(feature_names) > 0 else '特征1')
                ax.set_ylabel(feature_names[1] if len(feature_names) > 1 else '特征2')
            else:
                ax.scatter(X_transformed[:, 0], np.zeros_like(X_transformed[:, 0]), 
                          c=y, cmap='coolwarm', alpha=0.7, s=50)
                ax.set_xlabel(feature_names[0] if len(feature_names) > 0 else '特征1')
                ax.set_ylabel('')
            
            ax.set_title(f'{dataset_name} - {method_name}\n{X_transformed.shape}维')
            ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()
    
    # 分类性能比较
    print("\n非线性数据分类性能比较:")
    results = []
    
    for dataset_name, X, y in datasets:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)
        
        for degree in [1, 2, 3, 4]:
            # 多项式特征
            X_poly_train, feature_names = DimensionalityAugmentation.polynomial_features(X_train, degree)
            X_poly_test, _ = DimensionalityAugmentation.polynomial_features(X_test, degree)
            
            # 标准化
            scaler = StandardScaler()
            X_poly_train_scaled = scaler.fit_transform(X_poly_train)
            X_poly_test_scaled = scaler.transform(X_poly_test)
            
            # 训练模型
            model = LogisticRegression(max_iter=1000, random_state=42)
            model.fit(X_poly_train_scaled, y_train)
            
            train_score = accuracy_score(y_train, model.predict(X_poly_train_scaled))
            test_score = accuracy_score(y_test, model.predict(X_poly_test_scaled))
            
            results.append({
                '数据集': dataset_name,
                '多项式阶数': degree,
                '特征数量': X_poly_train.shape[1],
                '训练准确率': train_score,
                '测试准确率': test_score
            })
    
    results_df = pd.DataFrame(results)
    print(results_df.to_string(index=False))

nonlinear_data_demonstration()

# 4. 维度灾难与正则化研究
print("\n4. 维度灾难与正则化研究")
def curse_of_dimensionality_study():
    np.random.seed(42)
    
    # 生成不同维度的数据
    dimensions = [2, 5, 10, 20, 50, 100]
    n_samples = 1000
    
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    axes = axes.ravel()
    
    volume_ratios = []
    distance_ratios = []
    
    for idx, dim in enumerate(dimensions):
        if idx >= 6:
            break
            
        # 生成高维数据
        X_high_dim = np.random.randn(n_samples, dim)
        
        # 计算到原点的距离
        distances = np.linalg.norm(X_high_dim, axis=1)
        
        # 可视化距离分布
        axes[idx].hist(distances, bins=30, alpha=0.7, color='skyblue', edgecolor='black')
        axes[idx].axvline(np.mean(distances), color='red', linestyle='--', 
                         label=f'平均距离: {np.mean(distances):.2f}')
        axes[idx].set_xlabel('到原点的距离')
        axes[idx].set_ylabel('频数')
        axes[idx].set_title(f'{dim}维空间\n距离分布')
        axes[idx].legend()
        axes[idx].grid(True, alpha=0.3)
        
        # 计算体积比例（单位超球体与超立方体体积比）
        if dim <= 20:  # 避免数值计算问题
            unit_sphere_volume = (np.pi ** (dim/2)) / (2 * np.math.gamma(dim/2 + 1))
            unit_cube_volume = 2 ** dim
            volume_ratio = unit_sphere_volume / unit_cube_volume
            volume_ratios.append(volume_ratio)
        
        # 计算最近邻距离比例
        if dim <= 10:  # 计算成本考虑
            from sklearn.neighbors import NearestNeighbors
            nbrs = NearestNeighbors(n_neighbors=2).fit(X_high_dim)
            distances, indices = nbrs.kneighbors(X_high_dim)
            avg_nearest_distance = np.mean(distances[:, 1])
            distance_ratios.append(avg_nearest_distance / np.mean(distances))
    
    plt.tight_layout()
    plt.show()
    
    # 维度灾难现象可视化
    plt.figure(figsize=(15, 5))
    
    # 体积比例下降
    plt.subplot(1, 3, 1)
    valid_dims = dimensions[:len(volume_ratios)]
    plt.semilogy(valid_dims, volume_ratios, 'ro-', linewidth=2, markersize=8)
    plt.xlabel('维度')
    plt.ylabel('单位球体/立方体体积比(对数)')
    plt.title('高维空间体积比例急剧下降')
    plt.grid(True, alpha=0.3)
    
    # 数据稀疏性
    plt.subplot(1, 3, 2)
    sample_requirements = [10 ** (d/2) for d in dimensions[:10]]
    plt.plot(dimensions[:10], sample_requirements, 'go-', linewidth=2, markersize=8)
    plt.xlabel('维度')
    plt.ylabel('需要的样本数量')
    plt.title('维度增加需要的样本量指数增长')
    plt.grid(True, alpha=0.3)
    
    # 距离收敛
    plt.subplot(1, 3, 3)
    theoretical_ratios = [np.sqrt(d) for d in dimensions[:len(distance_ratios)]]
    plt.plot(dimensions[:len(distance_ratios)], distance_ratios, 'bo-', 
             label='实际比例', linewidth=2, markersize=8)
    plt.plot(dimensions[:len(distance_ratios)], theoretical_ratios, 'r--', 
             label='理论比例√d', linewidth=2)
    plt.xlabel('维度')
    plt.ylabel('最近邻/平均距离比例')
    plt.title('高维空间距离收敛现象')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()

curse_of_dimensionality_study()

# 5. 高级特征选择与正则化
print("\n5. 高级特征选择与正则化策略")
def feature_selection_regularization():
    # 生成高维数据
    np.random.seed(42)
    X, y = make_classification(n_samples=1000, n_features=50, n_informative=10, 
                              n_redundant=10, n_repeated=0, random_state=42)
    
    # 应用3阶多项式特征
    X_poly, feature_names = DimensionalityAugmentation.polynomial_features(X, 3)
    print(f"原始特征数: {X.shape[1]}, 多项式扩展后: {X_poly.shape[1]}")
    
    # 标准化
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_poly)
    
    # 特征选择方法比较
    selection_methods = {
        '无选择': (X_scaled, list(range(X_scaled.shape[1]))),
        '方差选择': None,  # 将在后面计算
        'F检验选择': None,
        'PCA降维': None
    }
    
    # 计算特征选择
    from sklearn.feature_selection import VarianceThreshold, SelectKBest
    
    # 方差选择
    selector_var = VarianceThreshold(threshold=0.1)
    X_var_selected = selector_var.fit_transform(X_scaled)
    selection_methods['方差选择'] = (X_var_selected, 
                                   [i for i, kept in enumerate(selector_var.get_support()) if kept])
    
    # F检验选择
    selector_f = SelectKBest(score_func=f_classif, k=50)
    X_f_selected = selector_f.fit_transform(X_scaled, y)
    selection_methods['F检验选择'] = (X_f_selected, 
                                    [i for i, kept in enumerate(selector_f.get_support()) if kept])
    
    # PCA降维
    pca = PCA(n_components=20)
    X_pca = pca.fit_transform(X_scaled)
    selection_methods['PCA降维'] = (X_pca, list(range(X_pca.shape[1])))
    
    # 模型性能比较
    results = []
    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.3, random_state=42)
    
    for method_name, (X_selected, selected_indices) in selection_methods.items():
        if method_name == '无选择':
            X_train_sel, X_test_sel = X_train, X_test
        else:
            # 确保测试集也应用相同的选择
            if method_name == 'PCA降维':
                X_train_sel = pca.transform(X_train)
                X_test_sel = pca.transform(X_test)
            else:
                X_train_sel = selector_var.transform(X_train) if method_name == '方差选择' else selector_f.transform(X_train)
                X_test_sel = selector_var.transform(X_test) if method_name == '方差选择' else selector_f.transform(X_test)
        
        # 不同正则化强度的逻辑回归
        for C in [0.001, 0.01, 0.1, 1, 10, 100]:
            model = LogisticRegression(C=C, max_iter=1000, random_state=42)
            model.fit(X_train_sel, y_train)
            
            train_score = accuracy_score(y_train, model.predict(X_train_sel))
            test_score = accuracy_score(y_test, model.predict(X_test_sel))
            
            results.append({
                '方法': method_name,
                '正则化强度C': C,
                '特征数量': X_train_sel.shape[1],
                '训练准确率': train_score,
                '测试准确率': test_score
            })
    
    results_df = pd.DataFrame(results)
    
    # 可视化结果
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # 不同方法的性能
    methods = results_df['方法'].unique()
    for method in methods:
        method_data = results_df[results_df['方法'] == method]
        best_idx = method_data['测试准确率'].idxmax()
        best_row = method_data.loc[best_idx]
        
        ax1.bar(method, best_row['测试准确率'], alpha=0.7, 
               label=f"{method}({best_row['特征数量']}特征)")
        ax1.text(methods.tolist().index(method), best_row['测试准确率'] + 0.01, 
                f"{best_row['测试准确率']:.3f}", ha='center')
    
    ax1.set_ylabel('最佳测试准确率')
    ax1.set_title('不同特征选择方法性能比较')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 正则化强度影响
    for method in ['无选择', 'F检验选择']:
        method_data = results_df[results_df['方法'] == method]
        ax2.semilogx(method_data['正则化强度C'], method_data['训练准确率'], 
                    'o-', label=f'{method}-训练', linewidth=2)
        ax2.semilogx(method_data['正则化强度C'], method_data['测试准确率'], 
                    's--', label=f'{method}-测试', linewidth=2)
    
    ax2.set_xlabel('正则化强度C (对数尺度)')
    ax2.set_ylabel('准确率')
    ax2.set_title('正则化强度对模型性能的影响')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()
    
    print("\n最佳性能配置:")
    best_overall = results_df.loc[results_df['测试准确率'].idxmax()]
    print(best_overall.to_string())

feature_selection_regularization()

# 6. 实际应用案例：图像特征扩展
print("\n6. 实际应用案例：图像块特征扩展")
def image_patch_feature_expansion():
    # 模拟图像块数据
    np.random.seed(42)
    
    # 生成简单的图像块 (8x8像素)
    n_patches = 50
    patch_size = 8
    image_patches = np.random.rand(n_patches, patch_size, patch_size)
    
    # 不同的特征提取方法
    feature_methods = {}
    
    # 1. 原始像素特征
    flat_patches = image_patches.reshape(n_patches, -1)
    feature_methods['原始像素'] = flat_patches
    
    # 2. 多项式特征扩展
    poly_features, poly_names = DimensionalityAugmentation.polynomial_features(flat_patches, 2)
    feature_methods['2阶多项式'] = poly_features
    
    # 3. 梯度特征 (模拟)
    gradient_features = np.array([np.gradient(patch) for patch in image_patches])
    gradient_features = gradient_features.reshape(n_patches, -1)
    feature_methods['梯度特征'] = gradient_features
    
    # 4. 统计特征
    statistical_features = np.column_stack([
        flat_patches.mean(axis=1),      # 均值
        flat_patches.std(axis=1),       # 标准差
        flat_patches.max(axis=1),       # 最大值
        flat_patches.min(axis=1),       # 最小值
    ])
    feature_methods['统计特征'] = statistical_features
    
    # 可视化特征分布
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    
    # 原始图像块示例
    ax = axes[0, 0]
    sample_patch = image_patches[0]
    im = ax.imshow(sample_patch, cmap='gray', interpolation='nearest')
    ax.set_title('示例图像块 (8×8像素)')
    plt.colorbar(im, ax=ax)
    
    # 不同方法的特征维度
    method_names = list(feature_methods.keys())
    dimensions = [features.shape[1] for features in feature_methods.values()]
    
    axes[0, 1].bar(method_names, dimensions, color=['skyblue', 'lightcoral', 'lightgreen', 'gold'])
    axes[0, 1].set_title('不同特征提取方法的维度')
    axes[0, 1].set_ylabel('特征数量')
    for i, dim in enumerate(dimensions):
        axes[0, 1].text(i, dim + 5, str(dim), ha='center')
    
    # 特征相关性热图 (原始像素)
    ax = axes[0, 2]
    correlation_matrix = np.corrcoef(flat_patches.T)
    sns.heatmap(correlation_matrix[:20, :20], ax=ax, cmap='coolwarm', 
                center=0, square=True)
    ax.set_title('原始像素特征相关性 (前20个)')
    
    # PCA可视化不同特征集
    for idx, (method_name, features) in enumerate(list(feature_methods.items())[:3]):
        ax = axes[1, idx]
        
        if features.shape[1] >= 2:
            # 使用PCA降维到2D可视化
            if features.shape[1] > 2:
                pca = PCA(n_components=2)
                features_2d = pca.fit_transform(features)
                variance_explained = pca.explained_variance_ratio_.sum()
            else:
                features_2d = features
                variance_explained = 1.0
            
            scatter = ax.scatter(features_2d[:, 0], features_2d[:, 1], 
                               c=flat_patches.mean(axis=1), cmap='viridis', alpha=0.7)
            ax.set_xlabel(f'PC1 ({variance_explained*100:.1f}%方差)')
            ax.set_ylabel('PC2')
            ax.set_title(f'{method_name}的PCA投影')
            plt.colorbar(scatter, ax=ax)
    
    plt.tight_layout()
    plt.show()
    
    # 特征有效性分析
    print("\n图像特征扩展分析:")
    analysis_data = []
    for method_name, features in feature_methods.items():
        # 计算特征方差
        total_variance = np.var(features, axis=0).sum()
        analysis_data.append({
            '方法': method_name,
            '特征数量': features.shape[1],
            '总方差': total_variance,
            '平均特征方差': total_variance / features.shape[1],
            '内存占用(MB)': features.nbytes / (1024 * 1024)
        })
    
    analysis_df = pd.DataFrame(analysis_data)
    print(analysis_df.to_string(index=False, float_format='%.3f'))

image_patch_feature_expansion()

# 7. 综合性能基准测试
print("\n7. 综合性能基准测试")
def comprehensive_benchmark():
    np.random.seed(42)
    
    # 生成不同复杂度的数据集
    datasets = {
        '线性可分': make_classification(n_samples=1000, n_features=10, n_informative=8, 
                                      n_redundant=2, n_clusters_per_class=1, random_state=42),
        '非线性': make_circles(n_samples=1000, noise=0.1, factor=0.5, random_state=42),
        '高维稀疏': make_classification(n_samples=500, n_features=100, n_informative=10, 
                                      n_redundant=90, random_state=42)
    }
    
    # 升维方法
    augmentation_methods = {
        '原始特征': lambda X: (X, ['原始']),
        '2阶多项式': lambda X: DimensionalityAugmentation.polynomial_features(X, 2),
        '3阶多项式': lambda X: DimensionalityAugmentation.polynomial_features(X, 3),
        '特征交互': lambda X: DimensionalityAugmentation.feature_interaction(X),
        '核PCA': lambda X: (DimensionalityAugmentation.kernel_pca_features(X, min(10, X.shape[1])), ['核PCA'])
    }
    
    # 模型
    models = {
        '逻辑回归': LogisticRegression(max_iter=1000, random_state=42),
        'SVM(线性)': SVC(kernel='linear', random_state=42),
        'SVM(RBF)': SVC(kernel='rbf', random_state=42)
    }
    
    benchmark_results = []
    
    for dataset_name, (X, y) in datasets.items():
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)
        
        for aug_name, aug_func in augmentation_methods.items():
            try:
                X_aug_train, feature_names = aug_func(X_train)
                X_aug_test, _ = aug_func(X_test)
                
                # 标准化
                scaler = StandardScaler()
                X_train_scaled = scaler.fit_transform(X_aug_train)
                X_test_scaled = scaler.transform(X_aug_test)
                
                for model_name, model in models.items():
                    # 训练模型
                    model.fit(X_train_scaled, y_train)
                    
                    # 预测
                    train_score = accuracy_score(y_train, model.predict(X_train_scaled))
                    test_score = accuracy_score(y_test, model.predict(X_test_scaled))
                    
                    benchmark_results.append({
                        '数据集': dataset_name,
                        '升维方法': aug_name,
                        '模型': model_name,
                        '特征数量': X_aug_train.shape[1],
                        '训练准确率': train_score,
                        '测试准确率': test_score,
                        '泛化差距': train_score - test_score
                    })
                    
            except Exception as e:
                print(f"错误: {dataset_name}-{aug_name}-{model_name}: {str(e)}")
                continue
    
    benchmark_df = pd.DataFrame(benchmark_results)
    
    # 找出每个数据集的最佳组合
    print("\n各数据集最佳性能配置:")
    best_configs = []
    for dataset in benchmark_df['数据集'].unique():
        dataset_data = benchmark_df[benchmark_df['数据集'] == dataset]
        best_idx = dataset_data['测试准确率'].idxmax()
        best_config = dataset_data.loc[best_idx]
        best_configs.append(best_config)
        print(f"{dataset}: {best_config['升维方法']} + {best_config['模型']} "
              f"(测试准确率: {best_config['测试准确率']:.3f})")
    
    # 性能热图可视化
    pivot_data = benchmark_df.pivot_table(values='测试准确率', 
                                        index='升维方法', 
                                        columns=['数据集', '模型'])
    
    plt.figure(figsize=(16, 8))
    sns.heatmap(pivot_data, annot=True, cmap='YlOrRd', fmt='.3f', 
                center=0.5, cbar_kws={'label': '测试准确率'})
    plt.title('不同升维方法+模型组合的性能热图')
    plt.tight_layout()
    plt.show()
    
    # 泛化差距分析
    plt.figure(figsize=(12, 6))
    generalization_data = benchmark_df.groupby('升维方法')['泛化差距'].mean().sort_values()
    plt.bar(generalization_data.index, generalization_data.values, 
            color=['red' if x > 0.1 else 'yellow' if x > 0.05 else 'green' 
                  for x in generalization_data.values])
    plt.axhline(y=0.1, color='r', linestyle='--', label='过拟合阈值')
    plt.axhline(y=0.05, color='y', linestyle='--', label='适度过拟合')
    plt.xlabel('升维方法')
    plt.ylabel('平均泛化差距')
    plt.title('各升维方法的平均过拟合程度')
    plt.legend()
    plt.xticks(rotation=45)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()

comprehensive_benchmark()

print("\n" + "=" * 80)
print("高级升维分析系统完成！")
print("=" * 80)
print("关键发现总结:")
print("1. 克罗内克积导致维度乘积级增长，适合张量运算")
print("2. 多项式特征能有效处理非线性问题，但需注意过拟合")
print("3. 高维空间存在维度灾难：数据稀疏、距离收敛等现象")
print("4. 特征选择和正则化是应对高维问题的关键策略")
print("5. 不同数据集和任务需要不同的升维方法组合")
print("6. 核方法能在保持可解释性的同时处理非线性")
print("=" * 80)