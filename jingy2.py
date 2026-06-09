import numpy as np
import pandas as pd
import matplotlib
matplotlib.rc("font", family='Microsoft YaHei')
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats, integrate
from scipy.optimize import curve_fit
import matplotlib.gridspec as gridspec
from mpl_toolkits.mplot3d import Axes3D
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings('ignore')

# 设置专业样式

class RealisticSemenAnalysis:
    """基于真实生理模型的精液分析系统"""
    
    def __init__(self):
        # 基于WHO标准和临床研究数据的参数范围
        self.physiological_ranges = {
            'volume_ml': (1.5, 6.0),
            'concentration_million_ml': (15, 200),
            'total_motility_percent': (40, 80),
            'progressive_motility_percent': (32, 70),
            'normal_forms_percent': (4, 15),
            'vitality_percent': (58, 85),
            'ph': (7.2, 8.0),
            'fructose_mg_ml': (1.2, 5.0),
            'zinc_mmol_l': (0.12, 0.25),
            'citric_acid_mg_ml': (20, 50),
            'dna_fragmentation_index': (5, 30)
        }
        
        # 环境影响因素
        self.environmental_factors = {
            'temperature_c': (34, 38),  # 睾丸温度范围
            'bpa_exposure_ng_ml': (0, 10),  # 双酚A暴露
            'phthalates_ng_ml': (0, 50),  # 邻苯二甲酸盐
            'smoking_pack_years': (0, 30),
            'alcohol_units_week': (0, 30),
            'bmi': (18, 35)
        }
        
        # 初始化随机种子
        np.random.seed(42)
    
    def generate_realistic_patient_data(self, n_patients=1000):
        """生成真实的患者数据，考虑参数间的相关性"""
        # 基础人口统计学
        age = np.random.normal(35, 8, n_patients)
        age = np.clip(age, 18, 65)
        
        bmi = np.random.normal(25, 4, n_patients)
        bmi = np.clip(bmi, 18, 40)
        
        # 环境暴露
        smoking = np.random.exponential(5, n_patients)
        smoking = np.clip(smoking, 0, 30)
        
        alcohol = np.random.gamma(2, 2, n_patients)
        alcohol = np.clip(alcohol, 0, 30)
        
        bpa_exposure = np.random.exponential(1, n_patients)
        phthalates = np.random.exponential(10, n_patients)
        
        # 精液参数 - 考虑相关性
        base_quality = np.random.normal(0, 1, n_patients)
        
        # 体积 - 与年龄负相关
        volume = 3.5 + 0.5 * base_quality - 0.02 * (age - 35) + np.random.normal(0, 0.8, n_patients)
        volume = np.clip(volume, *self.physiological_ranges['volume_ml'])
        
        # 浓度 - 与年龄、BMI、吸烟负相关
        concentration_base = 80 + 20 * base_quality - 0.5 * (age - 35) - 0.3 * (bmi - 25)
        concentration = concentration_base - 2 * smoking + np.random.normal(0, 25, n_patients)
        concentration = np.clip(concentration, *self.physiological_ranges['concentration_million_ml'])
        
        # 活力 - 与环境因素负相关
        motility_base = 60 + 10 * base_quality - 0.3 * (age - 35)
        total_motility = motility_base - 0.5 * smoking - 0.3 * alcohol - 2 * bpa_exposure + np.random.normal(0, 8, n_patients)
        total_motility = np.clip(total_motility, *self.physiological_ranges['total_motility_percent'])
        
        progressive_motility = total_motility * 0.8 + np.random.normal(0, 5, n_patients)
        progressive_motility = np.clip(progressive_motility, *self.physiological_ranges['progressive_motility_percent'])
        
        # 形态 - 高度敏感
        morphology_base = 10 + 3 * base_quality - 0.2 * (age - 35)
        normal_forms = morphology_base - 0.3 * smoking - 0.2 * alcohol - 1 * bpa_exposure + np.random.normal(0, 3, n_patients)
        normal_forms = np.clip(normal_forms, *self.physiological_ranges['normal_forms_percent'])
        
        # DNA碎片 - 与环境因素正相关
        dna_frag_base = 15 + 5 * (1 - base_quality) + 0.3 * (age - 35)
        dna_fragmentation = dna_frag_base + 0.8 * smoking + 0.5 * alcohol + 3 * bpa_exposure + np.random.normal(0, 6, n_patients)
        dna_fragmentation = np.clip(dna_fragmentation, *self.physiological_ranges['dna_fragmentation_index'])
        
        # 生化标志物
        fructose = 3.0 + 0.5 * base_quality + np.random.normal(0, 0.8, n_patients)
        fructose = np.clip(fructose, *self.physiological_ranges['fructose_mg_ml'])
        
        zinc = 0.18 + 0.03 * base_quality + np.random.normal(0, 0.03, n_patients)
        zinc = np.clip(zinc, *self.physiological_ranges['zinc_mmol_l'])
        
        # 创建DataFrame
        data = pd.DataFrame({
            'patient_id': range(1, n_patients + 1),
            'age': age,
            'bmi': bmi,
            'smoking_pack_years': smoking,
            'alcohol_units_week': alcohol,
            'bpa_exposure_ng_ml': bpa_exposure,
            'phthalates_ng_ml': phthalates,
            'volume_ml': volume,
            'concentration_million_ml': concentration,
            'total_motility_percent': total_motility,
            'progressive_motility_percent': progressive_motility,
            'normal_forms_percent': normal_forms,
            'dna_fragmentation_index': dna_fragmentation,
            'fructose_mg_ml': fructose,
            'zinc_mmol_l': zinc
        })
        
        # 计算生育力评分
        data['fertility_score'] = self.calculate_fertility_score(data)
        data['fertility_category'] = pd.cut(data['fertility_score'], 
                                          bins=[0, 0.4, 0.6, 0.8, 1.0],
                                          labels=['严重受损', '中度受损', '轻度受损', '正常'])
        
        return data
    
    def calculate_fertility_score(self, data):
        """基于多参数计算综合生育力评分"""
        # 确保数据是DataFrame格式
        if isinstance(data, dict):
            data = pd.DataFrame([data])
        
        # 标准化参数
        volume_score = np.clip((data['volume_ml'] - 1.5) / (6.0 - 1.5), 0, 1)
        concentration_score = np.clip((data['concentration_million_ml'] - 15) / (200 - 15), 0, 1)
        motility_score = np.clip((data['total_motility_percent'] - 40) / (80 - 40), 0, 1)
        morphology_score = np.clip((data['normal_forms_percent'] - 4) / (15 - 4), 0, 1)
        dna_score = 1 - np.clip((data['dna_fragmentation_index'] - 5) / (30 - 5), 0, 1)
        
        # 加权评分 (基于临床重要性)
        fertility_score = (
            0.15 * volume_score +
            0.25 * concentration_score +
            0.25 * motility_score +
            0.20 * morphology_score +
            0.15 * dna_score
        )
        
        # 如果结果是Series，返回第一个元素
        if hasattr(fertility_score, 'iloc'):
            return fertility_score.iloc[0]
        else:
            return fertility_score
    
    def create_comprehensive_dashboard(self, data):
        """创建综合临床仪表板"""
        fig = plt.figure(figsize=(20, 16))
        gs = gridspec.GridSpec(4, 4, figure=fig)
        
        # 1. 生育力评分分布
        ax1 = fig.add_subplot(gs[0, :2])
        categories = data['fertility_category'].value_counts().sort_index()
        colors = ['#FF6B6B', '#FFA726', '#42A5F5', '#66BB6A']
        bars = ax1.bar(categories.index, categories.values, color=colors)
        ax1.set_title('生育力分类分布', fontsize=14, fontweight='bold')
        ax1.set_ylabel('患者数量')
        for bar, count in zip(bars, categories.values):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5, 
                    f'{count}', ha='center', va='bottom', fontweight='bold')
        
        # 2. 年龄与精液参数关系
        ax2 = fig.add_subplot(gs[0, 2:])
        age_bins = [18, 25, 30, 35, 40, 45, 50, 65]
        age_groups = pd.cut(data['age'], bins=age_bins)
        grouped = data.groupby(age_groups).agg({
            'concentration_million_ml': 'mean',
            'total_motility_percent': 'mean',
            'normal_forms_percent': 'mean'
        })
        
        x = np.arange(len(grouped))
        width = 0.25
        
        ax2.bar(x - width, grouped['concentration_million_ml'], width, label='浓度', alpha=0.8)
        ax2.bar(x, grouped['total_motility_percent'], width, label='活力', alpha=0.8)
        ax2.bar(x + width, grouped['normal_forms_percent'], width, label='形态', alpha=0.8)
        
        ax2.set_xlabel('年龄组')
        ax2.set_ylabel('参数值')
        ax2.set_title('年龄对精液参数的影响', fontsize=14, fontweight='bold')
        ax2.set_xticks(x)
        ax2.set_xticklabels([str(interval) for interval in grouped.index])
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 3. 环境因素相关性热图
        ax3 = fig.add_subplot(gs[1, :2])
        env_corr_cols = ['smoking_pack_years', 'alcohol_units_week', 'bpa_exposure_ng_ml', 
                        'bmi', 'fertility_score']
        env_corr = data[env_corr_cols].corr()
        
        im = ax3.imshow(env_corr, cmap='coolwarm', vmin=-1, vmax=1, aspect='auto')
        ax3.set_xticks(range(len(env_corr_cols)))
        ax3.set_yticks(range(len(env_corr_cols)))
        ax3.set_xticklabels(['吸烟', '饮酒', 'BPA暴露', 'BMI', '生育力'], rotation=45)
        ax3.set_yticklabels(['吸烟', '饮酒', 'BPA暴露', 'BMI', '生育力'])
        ax3.set_title('环境因素与生育力的相关性', fontsize=14, fontweight='bold')
        
        # 添加相关系数值
        for i in range(len(env_corr_cols)):
            for j in range(len(env_corr_cols)):
                ax3.text(j, i, f'{env_corr.iloc[i, j]:.2f}', 
                        ha='center', va='center', color='white' if abs(env_corr.iloc[i, j]) > 0.5 else 'black')
        
        plt.colorbar(im, ax=ax3)
        
        # 4. 精液参数分布直方图
        ax4 = fig.add_subplot(gs[1, 2:])
        parameters = ['concentration_million_ml', 'total_motility_percent', 'normal_forms_percent']
        colors = ['#FF9999', '#66B3FF', '#99FF99']
        
        for i, param in enumerate(parameters):
            ax4.hist(data[param], bins=30, alpha=0.7, color=colors[i], 
                    label=param.replace('_', ' ').title(), density=True)
        
        ax4.set_xlabel('参数值')
        ax4.set_ylabel('密度')
        ax4.set_title('精液参数分布', fontsize=14, fontweight='bold')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        
        # 5. DNA碎片与形态关系
        ax5 = fig.add_subplot(gs[2, :2])
        scatter = ax5.scatter(data['dna_fragmentation_index'], data['normal_forms_percent'],
                            c=data['fertility_score'], cmap='viridis', alpha=0.6)
        ax5.set_xlabel('DNA碎片指数 (%)')
        ax5.set_ylabel('正常形态率 (%)')
        ax5.set_title('DNA完整性与精子形态关系', fontsize=14, fontweight='bold')
        plt.colorbar(scatter, ax=ax5, label='生育力评分')
        ax5.grid(True, alpha=0.3)
        
        # 添加趋势线
        z = np.polyfit(data['dna_fragmentation_index'], data['normal_forms_percent'], 1)
        p = np.poly1d(z)
        ax5.plot(data['dna_fragmentation_index'], p(data['dna_fragmentation_index']), 
                "r--", alpha=0.8)
        
        # 6. 生化标志物分析
        ax6 = fig.add_subplot(gs[2, 2:])
        biochemical_data = data[['fructose_mg_ml', 'zinc_mmol_l']].copy()
        biochemical_data['fructose_norm'] = (biochemical_data['fructose_mg_ml'] - biochemical_data['fructose_mg_ml'].min()) / \
                                          (biochemical_data['fructose_mg_ml'].max() - biochemical_data['fructose_mg_ml'].min())
        biochemical_data['zinc_norm'] = (biochemical_data['zinc_mmol_l'] - biochemical_data['zinc_mmol_l'].min()) / \
                                      (biochemical_data['zinc_mmol_l'].max() - biochemical_data['zinc_mmol_l'].min())
        
        x = np.arange(len(biochemical_data))
        ax6.scatter(biochemical_data['fructose_norm'], biochemical_data['zinc_norm'],
                   c=data['fertility_score'], cmap='plasma', alpha=0.6, s=30)
        ax6.set_xlabel('果糖水平 (标准化)')
        ax6.set_ylabel('锌水平 (标准化)')
        ax6.set_title('生化标志物与生育力关系', fontsize=14, fontweight='bold')
        plt.colorbar(scatter, ax=ax6, label='生育力评分')
        ax6.grid(True, alpha=0.3)
        
        # 7. 多参数雷达图示例
        ax7 = fig.add_subplot(gs[3, :], polar=True)

        # 选择几个代表性病例
        sample_cases = data.sample(3)
        parameters_radar = ['volume_ml', 'concentration_million_ml', 'total_motility_percent', 
                        'normal_forms_percent', 'dna_fragmentation_index']
        labels = ['体积', '浓度', '活力', '形态', 'DNA完整性']

        # 计算角度
        angles = np.linspace(0, 2 * np.pi, len(parameters_radar), endpoint=False).tolist()
        angles += angles[:1]  # 闭合

        # 为每个病例计算标准化参数并闭合
        normalized_cases = []
        for i, case in sample_cases.iterrows():
            case_values = []
            for param in parameters_radar:
                min_val = data[param].min()
                max_val = data[param].max()
                value = case[param]
                if param == 'dna_fragmentation_index':
                    # DNA碎片是负向指标，所以用1减
                    normalized_value = 1 - (value - min_val) / (max_val - min_val)
                else:
                    normalized_value = (value - min_val) / (max_val - min_val)
                case_values.append(normalized_value)
            # 闭合
            case_values.append(case_values[0])
            normalized_cases.append(case_values)

        colors_radar = ['#FF6B6B', '#4ECDC4', '#45B7D1']
        for i, case_data in enumerate(normalized_cases):
            ax7.plot(angles, case_data, 'o-', linewidth=2, label=f'病例 {i+1}', color=colors_radar[i])
            ax7.fill(angles, case_data, alpha=0.1, color=colors_radar[i])

        ax7.set_xticks(angles[:-1])
        ax7.set_xticklabels(labels)
        ax7.set_ylim(0, 1)
        ax7.set_title('多参数病例分析雷达图', size=14, fontweight='bold', pad=20)
        ax7.legend(bbox_to_anchor=(1.1, 1.0))
        
        plt.tight_layout()
        return fig

    def simulate_sperm_kinetics(self, n_sperm=1000, time_minutes=120):
        """模拟精子运动动力学"""
        # 基于真实精子运动参数
        motility_types = {
            'rapid_progressive': {'speed': 25, 'linearity': 0.9, 'proportion': 0.4},
            'slow_progressive': {'speed': 10, 'linearity': 0.7, 'proportion': 0.3},
            'non_progressive': {'speed': 5, 'linearity': 0.3, 'proportion': 0.2},
            'immotile': {'speed': 0, 'linearity': 0, 'proportion': 0.1}
        }
        
        # 初始化精子
        sperm_data = []
        for mot_type, params in motility_types.items():
            n_type = int(n_sperm * params['proportion'])
            for i in range(n_type):
                sperm_data.append({
                    'type': mot_type,
                    'speed_um_s': np.random.normal(params['speed'], params['speed'] * 0.2),
                    'linearity': np.random.normal(params['linearity'], 0.1),
                    'initial_vitality': np.random.normal(80, 10)
                })
        
        df_sperm = pd.DataFrame(sperm_data)
        
        # 模拟时间过程
        time_points = np.linspace(0, time_minutes, 50)
        results = []
        
        for t in time_points:
            for idx, sperm in df_sperm.iterrows():
                # 活力衰减模型
                vitality_decay = 0.1 * t  # 基础衰减
                if sperm['type'] == 'immotile':
                    vitality_decay *= 2  # 不动精子衰减更快
                
                current_vitality = max(0, sperm['initial_vitality'] - vitality_decay + np.random.normal(0, 5))
                
                # 运动能力衰减
                current_speed = sperm['speed_um_s'] * (current_vitality / sperm['initial_vitality'])
                
                results.append({
                    'time_min': t,
                    'sperm_id': idx,
                    'type': sperm['type'],
                    'vitality': current_vitality,
                    'speed_um_s': current_speed,
                    'distance_um': current_speed * t * 60  # 转换为微米
                })
        
        return pd.DataFrame(results)

    def create_kinetic_analysis(self, kinetic_data):
        """创建精子运动动力学分析"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        
        # 1. 活力随时间变化
        vitality_over_time = kinetic_data.groupby(['time_min', 'type'])['vitality'].mean().reset_index()
        for mot_type in vitality_over_time['type'].unique():
            type_data = vitality_over_time[vitality_over_time['type'] == mot_type]
            axes[0,0].plot(type_data['time_min'], type_data['vitality'], 
                        label=mot_type.replace('_', ' ').title(), linewidth=2)
        
        axes[0,0].set_xlabel('时间 (分钟)')
        axes[0,0].set_ylabel('活力 (%)')
        axes[0,0].set_title('精子活力随时间衰减', fontsize=12, fontweight='bold')
        axes[0,0].legend()
        axes[0,0].grid(True, alpha=0.3)
        
        # 2. 运动速度分布 - 修复维度问题
        time_snapshot = kinetic_data[kinetic_data['time_min'] == 60]  # 1小时快照
        
        # 确保所有类型都有数据
        unique_types = time_snapshot['type'].unique()
        speed_data = []
        valid_labels = []
        
        for mot_type in unique_types:
            type_data = time_snapshot[time_snapshot['type'] == mot_type]['speed_um_s'].values
            if len(type_data) > 0:  # 只包含有数据的类型
                speed_data.append(type_data)
                valid_labels.append(mot_type.replace('_', '\n').title())
        
        if speed_data:  # 确保有数据可绘制
            axes[0,1].boxplot(speed_data, labels=valid_labels)
            axes[0,1].set_ylabel('运动速度 (μm/s)')
            axes[0,1].set_title('不同类型精子运动速度比较 (60分钟)', fontsize=12, fontweight='bold')
            axes[0,1].grid(True, alpha=0.3)
        else:
            axes[0,1].text(0.5, 0.5, '无数据可用', ha='center', va='center', 
                        transform=axes[0,1].transAxes, fontsize=12)
            axes[0,1].set_title('不同类型精子运动速度比较 (60分钟)', fontsize=12, fontweight='bold')
        
        # 3. 累积距离
        distance_over_time = kinetic_data.groupby(['time_min', 'type'])['distance_um'].mean().reset_index()
        for mot_type in distance_over_time['type'].unique():
            type_data = distance_over_time[distance_over_time['type'] == mot_type]
            axes[1,0].plot(type_data['time_min'], type_data['distance_um'] / 1000,  # 转换为毫米
                        label=mot_type.replace('_', ' ').title(), linewidth=2)
        
        axes[1,0].set_xlabel('时间 (分钟)')
        axes[1,0].set_ylabel('累积距离 (mm)')
        axes[1,0].set_title('精子累积运动距离', fontsize=12, fontweight='bold')
        axes[1,0].legend()
        axes[1,0].grid(True, alpha=0.3)
        
        # 4. 生存分析 - 添加错误处理
        try:
            from sksurv.nonparametric import kaplan_meier_estimator
            
            # 模拟生存数据 (活力 < 50% 视为"死亡")
            survival_data = []
            for sperm_id in kinetic_data['sperm_id'].unique():
                sperm_traj = kinetic_data[kinetic_data['sperm_id'] == sperm_id]
                death_time = sperm_traj[sperm_traj['vitality'] < 50]['time_min']
                if len(death_time) > 0:
                    survival_data.append((False, death_time.iloc[0]))
                else:
                    survival_data.append((True, kinetic_data['time_min'].max()))
            
            survival_df = pd.DataFrame(survival_data, columns=['censored', 'time'])
            
            # Kaplan-Meier曲线
            time, survival_prob = kaplan_meier_estimator(
                survival_df['censored'].values, 
                survival_df['time'].values
            )
            
            axes[1,1].step(time, survival_prob, where="post", linewidth=2)
            axes[1,1].set_xlabel('时间 (分钟)')
            axes[1,1].set_ylabel('存活概率')
            axes[1,1].set_title('精子存活分析 (Kaplan-Meier)', fontsize=12, fontweight='bold')
            axes[1,1].grid(True, alpha=0.3)
            axes[1,1].set_ylim(0, 1)
            
        except ImportError:
            # 如果 scikit-survival 不可用，显示替代图表
            axes[1,1].text(0.5, 0.5, '需要安装 scikit-survival 库\n运行: pip install scikit-survival', 
                        ha='center', va='center', transform=axes[1,1].transAxes, fontsize=10)
            axes[1,1].set_title('精子存活分析 (需要 scikit-survival)', fontsize=12, fontweight='bold')
            axes[1,1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        return fig

    def create_interactive_clinical_tool(self, data):
        """创建交互式临床决策支持工具"""
        # 使用Plotly创建交互式可视化
        fig = make_subplots(
            rows=2, cols=3,
            subplot_titles=(
                '生育力评分分布', '年龄相关变化', '环境因素影响',
                'DNA碎片与形态', '生化标志物', '参数相关性'
            ),
            specs=[
                [{"type": "histogram"}, {"type": "scatter"}, {"type": "scatter"}],
                [{"type": "scatter"}, {"type": "scatter"}, {"type": "heatmap"}]
            ]
        )
        
        # 1. 生育力评分分布
        fig.add_trace(
            go.Histogram(
                x=data['fertility_score'],
                nbinsx=30,
                name='生育力评分',
                marker_color='lightblue'
            ),
            row=1, col=1
        )
        
        # 2. 年龄相关变化
        age_bins = pd.cut(data['age'], bins=8)
        age_grouped = data.groupby(age_bins).agg({
            'concentration_million_ml': 'mean',
            'total_motility_percent': 'mean'
        }).reset_index()
        
        fig.add_trace(
            go.Scatter(
                x=[interval.mid for interval in age_grouped['age']],
                y=age_grouped['concentration_million_ml'],
                mode='lines+markers',
                name='浓度',
                line=dict(color='blue')
            ),
            row=1, col=2
        )
        
        fig.add_trace(
            go.Scatter(
                x=[interval.mid for interval in age_grouped['age']],
                y=age_grouped['total_motility_percent'],
                mode='lines+markers',
                name='活力',
                line=dict(color='red')
            ),
            row=1, col=2
        )
        
        # 3. 环境因素影响
        fig.add_trace(
            go.Scatter(
                x=data['smoking_pack_years'],
                y=data['fertility_score'],
                mode='markers',
                marker=dict(
                    color=data['age'],
                    colorscale='Viridis',
                    showscale=True,
                    size=8,
                    opacity=0.6
                ),
                name='吸烟影响',
                hovertemplate="<b>吸烟</b>: %{x}包年<br><b>生育力</b>: %{y:.2f}<br><b>年龄</b>: %{marker.color}岁<extra></extra>"
            ),
            row=1, col=3
        )
        
        # 4. DNA碎片与形态
        fig.add_trace(
            go.Scatter(
                x=data['dna_fragmentation_index'],
                y=data['normal_forms_percent'],
                mode='markers',
                marker=dict(
                    color=data['fertility_score'],
                    colorscale='Plasma',
                    showscale=True,
                    size=8,
                    opacity=0.6
                ),
                name='DNA完整性',
                hovertemplate="<b>DNA碎片</b>: %{x}%<br><b>正常形态</b>: %{y}%<br><b>生育力</b>: %{marker.color:.2f}<extra></extra>"
            ),
            row=2, col=1
        )
        
        # 5. 生化标志物
        fig.add_trace(
            go.Scatter(
                x=data['fructose_mg_ml'],
                y=data['zinc_mmol_l'],
                mode='markers',
                marker=dict(
                    color=data['fertility_score'],
                    colorscale='Rainbow',
                    showscale=True,
                    size=8,
                    opacity=0.6
                ),
                name='生化标志物',
                hovertemplate="<b>果糖</b>: %{x} mg/mL<br><b>锌</b>: %{y} mmol/L<br><b>生育力</b>: %{marker.color:.2f}<extra></extra>"
            ),
            row=2, col=2
        )
        
        # 6. 参数相关性热图
        corr_cols = ['volume_ml', 'concentration_million_ml', 'total_motility_percent', 
                    'normal_forms_percent', 'dna_fragmentation_index', 'fertility_score']
        corr_matrix = data[corr_cols].corr()
        
        fig.add_trace(
            go.Heatmap(
                z=corr_matrix.values,
                x=[col.replace('_', ' ').title() for col in corr_cols],
                y=[col.replace('_', ' ').title() for col in corr_cols],
                colorscale='RdBu',
                zmin=-1, zmax=1,
                hoverongaps=False,
                colorbar=dict(title="相关系数"),
                text=corr_matrix.round(2).values,
                texttemplate="%{text}"
            ),
            row=2, col=3
        )
        
        fig.update_layout(
            height=800,
            title_text="精液分析临床决策支持系统",
            showlegend=True
        )
        
        return fig

    def predict_treatment_outcome(self, patient_data, treatment_type):
        """预测治疗干预效果"""
        treatment_effects = {
            'antioxidants': {
                'dna_fragmentation_index': -0.15,  # 减少15%
                'total_motility_percent': +0.08,   # 增加8%
                'normal_forms_percent': +0.05      # 增加5%
            },
            'hormonal': {
                'concentration_million_ml': +0.25, # 增加25%
                'volume_ml': +0.10                 # 增加10%
            },
            'lifestyle': {
                'total_motility_percent': +0.12,
                'dna_fragmentation_index': -0.10,
                'normal_forms_percent': +0.08
            },
            'surgical': {
                'concentration_million_ml': +0.40,
                'total_motility_percent': +0.15
            }
        }
        
        effects = treatment_effects.get(treatment_type, {})
        predicted_data = patient_data.copy()
        
        for param, effect in effects.items():
            if param in predicted_data:
                if 'fragmentation' in param:  # 负向指标
                    predicted_data[param] = patient_data[param] * (1 + effect)
                else:  # 正向指标
                    predicted_data[param] = patient_data[param] * (1 + effect)
        
        # 重新计算生育力评分 - 修复Series处理问题
        # 创建一个临时的DataFrame用于计算
        temp_df = pd.DataFrame([{k: v for k, v in predicted_data.items() 
                            if k in ['volume_ml', 'concentration_million_ml', 
                                    'total_motility_percent', 'normal_forms_percent', 
                                    'dna_fragmentation_index']}])
        
        fertility_score = self.calculate_fertility_score(temp_df)
        
        # 确保返回的是单个值而不是Series
        if hasattr(fertility_score, 'iloc'):
            predicted_data['fertility_score'] = fertility_score.iloc[0]
        else:
            predicted_data['fertility_score'] = fertility_score
        
        return predicted_data

# 使用示例
def main():
    print("初始化真实精液分析系统...")
    analyzer = RealisticSemenAnalysis()
    
    print("生成患者数据...")
    patient_data = analyzer.generate_realistic_patient_data(n_patients=1500)
    
    print("创建综合仪表板...")
    dashboard_fig = analyzer.create_comprehensive_dashboard(patient_data)
    dashboard_fig.savefig('comprehensive_semen_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    print("模拟精子运动动力学...")
    kinetic_data = analyzer.simulate_sperm_kinetics(n_sperm=500)
    kinetic_fig = analyzer.create_kinetic_analysis(kinetic_data)
    kinetic_fig.savefig('sperm_kinetics_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    print("创建交互式工具...")
    interactive_fig = analyzer.create_interactive_clinical_tool(patient_data)
    interactive_fig.write_html("interactive_semen_analysis.html")
    
    print("治疗预测示例...")
    sample_patient = patient_data.iloc[0].to_dict()
    treatments = ['antioxidants', 'hormonal', 'lifestyle', 'surgical']
    
    print(f"\n初始患者状态:")
    print(f"浓度: {sample_patient['concentration_million_ml']:.1f} 百万/mL")
    print(f"活力: {sample_patient['total_motility_percent']:.1f}%")
    print(f"形态: {sample_patient['normal_forms_percent']:.1f}%")
    print(f"DNA碎片: {sample_patient['dna_fragmentation_index']:.1f}%")
    print(f"生育力评分: {sample_patient['fertility_score']:.3f}")
    
    for treatment in treatments:
        predicted = analyzer.predict_treatment_outcome(sample_patient, treatment)
        improvement = predicted['fertility_score'] - sample_patient['fertility_score']
        print(f"\n{treatment.title()}治疗后预测:")
        print(f"浓度: {predicted['concentration_million_ml']:.1f} 百万/mL")
        print(f"活力: {predicted['total_motility_percent']:.1f}%")
        print(f"形态: {predicted['normal_forms_percent']:.1f}%")
        print(f"DNA碎片: {predicted['dna_fragmentation_index']:.1f}%")
        print(f"生育力评分: {predicted['fertility_score']:.3f} (+{improvement:.3f})")
    
    # 保存数据用于进一步分析
    patient_data.to_csv('semen_analysis_dataset.csv', index=False)
    kinetic_data.to_csv('sperm_kinetics_data.csv', index=False)
    
    print(f"\n数据分析完成!")
    print(f"数据集大小: {patient_data.shape}")
    print(f"生育力分类统计:")
    print(patient_data['fertility_category'].value_counts().sort_index())

if __name__ == "__main__":
    main()