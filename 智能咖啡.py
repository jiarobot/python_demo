import json
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
from pathlib import Path
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import joblib

# ==================== 数据模型定义 ====================

class CoffeeType(Enum):
    ESPRESSO = "espresso"
    AMERICANO = "americano"
    LATTE = "latte"
    CAPPUCCINO = "cappuccino"
    CUSTOM = "custom"

class GrindLevel(Enum):
    EXTRA_FINE = "extra_fine"
    FINE = "fine"
    MEDIUM_FINE = "medium_fine"
    MEDIUM = "medium"
    COARSE = "coarse"

@dataclass
class CoffeeRecipe:
    """咖啡配方数据类"""
    name: str
    coffee_type: CoffeeType
    coffee_weight: float  # 咖啡粉重量(g)
    water_weight: float   # 水量(ml)
    temperature: int      # 水温(℃)
    grind_level: GrindLevel
    extraction_time: int  # 萃取时间(秒)
    pressure: float       # 压力(bar)
    description: str = ""
    rating: float = 0.0
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
    
    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'coffee_type': self.coffee_type.value,
            'coffee_weight': self.coffee_weight,
            'water_weight': self.water_weight,
            'temperature': self.temperature,
            'grind_level': self.grind_level.value,
            'extraction_time': self.extraction_time,
            'pressure': self.pressure,
            'description': self.description,
            'rating': self.rating,
            'tags': self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CoffeeRecipe':
        return cls(
            name=data['name'],
            coffee_type=CoffeeType(data['coffee_type']),
            coffee_weight=data['coffee_weight'],
            water_weight=data['water_weight'],
            temperature=data['temperature'],
            grind_level=GrindLevel(data['grind_level']),
            extraction_time=data['extraction_time'],
            pressure=data['pressure'],
            description=data.get('description', ''),
            rating=data.get('rating', 0.0),
            tags=data.get('tags', [])
        )

@dataclass
class BrewSession:
    """冲泡会话记录"""
    session_id: str
    recipe_name: str
    timestamp: datetime
    actual_params: Dict
    rating: float
    notes: str = ""
    sensory_data: Dict = None
    
    def __post_init__(self):
        if self.sensory_data is None:
            self.sensory_data = {}

# ==================== 核心工具库 ====================

class CoffeeRecipeManager:
    """咖啡配方管理器"""
    
    def __init__(self, db_path: str = "coffee_recipes.db"):
        self.db_path = db_path
        self._init_database()
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger('CoffeeRecipeManager')
        logger.setLevel(logging.INFO)
        return logger
    
    def _init_database(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS recipes (
                    name TEXT PRIMARY KEY,
                    coffee_type TEXT,
                    coffee_weight REAL,
                    water_weight REAL,
                    temperature INTEGER,
                    grind_level TEXT,
                    extraction_time INTEGER,
                    pressure REAL,
                    description TEXT,
                    rating REAL,
                    tags TEXT,
                    created_date TEXT,
                    modified_date TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS brew_sessions (
                    session_id TEXT PRIMARY KEY,
                    recipe_name TEXT,
                    timestamp TEXT,
                    actual_params TEXT,
                    rating REAL,
                    notes TEXT,
                    sensory_data TEXT
                )
            ''')
    
    def save_recipe(self, recipe: CoffeeRecipe) -> bool:
        """保存配方"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO recipes 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    recipe.name,
                    recipe.coffee_type.value,
                    recipe.coffee_weight,
                    recipe.water_weight,
                    recipe.temperature,
                    recipe.grind_level.value,
                    recipe.extraction_time,
                    recipe.pressure,
                    recipe.description,
                    recipe.rating,
                    json.dumps(recipe.tags),
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))
            self.logger.info(f"配方保存成功: {recipe.name}")
            return True
        except Exception as e:
            self.logger.error(f"保存配方失败: {e}")
            return False
    
    def load_recipe(self, name: str) -> Optional[CoffeeRecipe]:
        """加载配方"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    'SELECT * FROM recipes WHERE name = ?', (name,)
                )
                row = cursor.fetchone()
                if row:
                    recipe_data = {
                        'name': row[0],
                        'coffee_type': row[1],
                        'coffee_weight': row[2],
                        'water_weight': row[3],
                        'temperature': row[4],
                        'grind_level': row[5],
                        'extraction_time': row[6],
                        'pressure': row[7],
                        'description': row[8],
                        'rating': row[9],
                        'tags': json.loads(row[10])
                    }
                    return CoffeeRecipe.from_dict(recipe_data)
        except Exception as e:
            self.logger.error(f"加载配方失败: {e}")
        return None
    
    def get_all_recipes(self) -> List[CoffeeRecipe]:
        """获取所有配方"""
        recipes = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('SELECT * FROM recipes')
                for row in cursor.fetchall():
                    recipe_data = {
                        'name': row[0],
                        'coffee_type': row[1],
                        'coffee_weight': row[2],
                        'water_weight': row[3],
                        'temperature': row[4],
                        'grind_level': row[5],
                        'extraction_time': row[6],
                        'pressure': row[7],
                        'description': row[8],
                        'rating': row[9],
                        'tags': json.loads(row[10])
                    }
                    recipes.append(CoffeeRecipe.from_dict(recipe_data))
        except Exception as e:
            self.logger.error(f"获取配方列表失败: {e}")
        return recipes
    
    def delete_recipe(self, name: str) -> bool:
        """删除配方"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('DELETE FROM recipes WHERE name = ?', (name,))
            self.logger.info(f"配方删除成功: {name}")
            return True
        except Exception as e:
            self.logger.error(f"删除配方失败: {e}")
            return False

class CoffeeBrewingSimulator:
    """咖啡冲泡模拟器"""
    
    def __init__(self):
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger('CoffeeBrewingSimulator')
        logger.setLevel(logging.INFO)
        return logger
    
    def simulate_brew(self, recipe: CoffeeRecipe) -> Dict:
        """模拟冲泡过程"""
        try:
            # 模拟冲泡参数计算
            extraction_yield = self._calculate_extraction_yield(recipe)
            strength = self._calculate_strength(recipe)
            quality_score = self._calculate_quality_score(recipe, extraction_yield, strength)
            
            # 模拟实时数据
            timeline_data = self._generate_timeline_data(recipe)
            
            result = {
                'success': True,
                'extraction_yield': extraction_yield,
                'strength': strength,
                'quality_score': quality_score,
                'timeline_data': timeline_data,
                'recommendations': self._generate_recommendations(recipe, extraction_yield, strength)
            }
            
            self.logger.info(f"冲泡模拟完成: {recipe.name}")
            return result
            
        except Exception as e:
            self.logger.error(f"冲泡模拟失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def _calculate_extraction_yield(self, recipe: CoffeeRecipe) -> float:
        """计算萃取率"""
        base_yield = 0.18  # 基础萃取率
        # 基于参数的调整
        temp_factor = (recipe.temperature - 90) / 10 * 0.02
        time_factor = (recipe.extraction_time - 25) / 10 * 0.015
        grind_factor = {
            GrindLevel.EXTRA_FINE: 0.03,
            GrindLevel.FINE: 0.02,
            GrindLevel.MEDIUM_FINE: 0.01,
            GrindLevel.MEDIUM: 0.0,
            GrindLevel.COARSE: -0.02
        }[recipe.grind_level]
        
        return base_yield + temp_factor + time_factor + grind_factor
    
    def _calculate_strength(self, recipe: CoffeeRecipe) -> float:
        """计算咖啡浓度"""
        ratio = recipe.water_weight / recipe.coffee_weight
        base_strength = 1.3 - (ratio - 16) * 0.02
        return max(0.8, min(2.0, base_strength))
    
    def _calculate_quality_score(self, recipe: CoffeeRecipe, extraction: float, strength: float) -> float:
        """计算质量评分"""
        # 理想萃取率范围 18%-22%
        extraction_score = 1.0 - abs(extraction - 0.20) * 10
        
        # 理想浓度范围 1.2%-1.5%
        strength_score = 1.0 - abs(strength - 1.35) * 2
        
        # 参数平衡评分
        balance_score = self._calculate_balance_score(recipe)
        
        return (extraction_score + strength_score + balance_score) / 3 * 10
    
    def _calculate_balance_score(self, recipe: CoffeeRecipe) -> float:
        """计算参数平衡评分"""
        score = 1.0
        
        # 水温合理性
        if recipe.temperature < 88 or recipe.temperature > 96:
            score -= 0.2
        
        # 粉水比合理性
        ratio = recipe.water_weight / recipe.coffee_weight
        if ratio < 15 or ratio > 18:
            score -= 0.2
        
        # 时间合理性
        if recipe.extraction_time < 20 or recipe.extraction_time > 35:
            score -= 0.2
            
        return max(0, score)
    
    def _generate_timeline_data(self, recipe: CoffeeRecipe) -> List[Dict]:
        """生成时间线数据"""
        timeline = []
        time_points = np.linspace(0, recipe.extraction_time, 50)
        
        for t in time_points:
            progress = t / recipe.extraction_time
            
            # 模拟压力曲线
            pressure = recipe.pressure * (1 - np.exp(-progress * 3))
            
            # 模拟流量曲线
            flow_rate = 2.0 * (1 - progress * 0.5)
            
            timeline.append({
                'time': t,
                'pressure': pressure,
                'flow_rate': flow_rate,
                'temperature': recipe.temperature - (1 - progress) * 2
            })
        
        return timeline
    
    def _generate_recommendations(self, recipe: CoffeeRecipe, extraction: float, strength: float) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        if extraction < 0.18:
            recommendations.append("萃取不足，建议增加研磨细度或延长萃取时间")
        elif extraction > 0.22:
            recommendations.append("过度萃取，建议调粗研磨或缩短萃取时间")
        
        if strength < 1.2:
            recommendations.append("浓度偏低，建议减少水量或增加咖啡粉量")
        elif strength > 1.5:
            recommendations.append("浓度偏高，建议增加水量或减少咖啡粉量")
        
        if not recommendations:
            recommendations.append("参数设置合理，继续保持！")
        
        return recommendations

class CoffeeDataAnalyzer:
    """咖啡数据分析器"""
    
    def __init__(self, recipe_manager: CoffeeRecipeManager):
        self.recipe_manager = recipe_manager
        self.scaler = StandardScaler()
        self.model = None
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger('CoffeeDataAnalyzer')
        logger.setLevel(logging.INFO)
        return logger
    
    def analyze_recipe_trends(self) -> Dict:
        """分析配方趋势"""
        recipes = self.recipe_manager.get_all_recipes()
        if not recipes:
            return {}
        
        df = pd.DataFrame([recipe.to_dict() for recipe in recipes])
        
        analysis = {
            'coffee_type_distribution': df['coffee_type'].value_counts().to_dict(),
            'parameter_stats': {
                'temperature': {
                    'mean': df['temperature'].mean(),
                    'std': df['temperature'].std()
                },
                'extraction_time': {
                    'mean': df['extraction_time'].mean(),
                    'std': df['extraction_time'].std()
                },
                'coffee_weight': {
                    'mean': df['coffee_weight'].mean(),
                    'std': df['coffee_weight'].std()
                }
            },
            'rating_correlations': self._calculate_correlations(df)
        }
        
        return analysis
    
    def _calculate_correlations(self, df: pd.DataFrame) -> Dict:
        """计算参数与评分的相关性"""
        numeric_columns = ['coffee_weight', 'water_weight', 'temperature', 
                          'extraction_time', 'pressure', 'rating']
        
        try:
            numeric_df = df[numeric_columns]
            correlations = numeric_df.corr()['rating'].to_dict()
            return {k: v for k, v in correlations.items() if k != 'rating'}
        except:
            return {}
    
    def train_quality_predictor(self) -> bool:
        """训练质量预测模型"""
        try:
            recipes = self.recipe_manager.get_all_recipes()
            if len(recipes) < 10:
                self.logger.warning("数据量不足，无法训练模型")
                return False
            
            # 准备特征数据
            X = []
            y = []
            
            for recipe in recipes:
                features = [
                    recipe.coffee_weight,
                    recipe.water_weight,
                    recipe.temperature,
                    recipe.extraction_time,
                    recipe.pressure
                ]
                X.append(features)
                y.append(recipe.rating)
            
            # 标准化特征
            X_scaled = self.scaler.fit_transform(X)
            
            # 训练模型
            self.model = RandomForestRegressor(n_estimators=100, random_state=42)
            self.model.fit(X_scaled, y)
            
            self.logger.info("质量预测模型训练完成")
            return True
            
        except Exception as e:
            self.logger.error(f"模型训练失败: {e}")
            return False
    
    def predict_quality(self, recipe: CoffeeRecipe) -> float:
        """预测咖啡质量评分"""
        if self.model is None:
            if not self.train_quality_predictor():
                return 0.0
        
        try:
            features = [
                recipe.coffee_weight,
                recipe.water_weight,
                recipe.temperature,
                recipe.extraction_time,
                recipe.pressure
            ]
            
            features_scaled = self.scaler.transform([features])
            prediction = self.model.predict(features_scaled)[0]
            return max(0.0, min(10.0, prediction))
            
        except Exception as e:
            self.logger.error(f"质量预测失败: {e}")
            return 0.0

class CoffeeRecipeOptimizer:
    """咖啡配方优化器"""
    
    def __init__(self, recipe_manager: CoffeeRecipeManager):
        self.recipe_manager = recipe_manager
        self.analyzer = CoffeeDataAnalyzer(recipe_manager)
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger('CoffeeRecipeOptimizer')
        logger.setLevel(logging.INFO)
        return logger
    
    def optimize_recipe(self, base_recipe: CoffeeRecipe, target_type: CoffeeType = None) -> CoffeeRecipe:
        """优化配方"""
        optimized_recipe = CoffeeRecipe(
            name=f"{base_recipe.name}_optimized",
            coffee_type=target_type or base_recipe.coffee_type,
            coffee_weight=base_recipe.coffee_weight,
            water_weight=base_recipe.water_weight,
            temperature=base_recipe.temperature,
            grind_level=base_recipe.grind_level,
            extraction_time=base_recipe.extraction_time,
            pressure=base_recipe.pressure,
            description=f"基于{base_recipe.name}的优化版本"
        )
        
        # 基于咖啡类型的标准参数优化
        if target_type:
            optimized_recipe = self._apply_type_optimization(optimized_recipe, target_type)
        
        # 基于数据驱动的优化
        optimized_recipe = self._apply_data_optimization(optimized_recipe)
        
        # 预测优化后的评分
        predicted_rating = self.analyzer.predict_quality(optimized_recipe)
        optimized_recipe.rating = predicted_rating
        
        return optimized_recipe
    
    def _apply_type_optimization(self, recipe: CoffeeRecipe, target_type: CoffeeType) -> CoffeeRecipe:
        """应用基于咖啡类型的优化"""
        type_guidelines = {
            CoffeeType.ESPRESSO: {
                'coffee_weight': (18, 20),
                'water_weight': (36, 40),
                'temperature': (92, 94),
                'extraction_time': (25, 30),
                'pressure': (9, 10)
            },
            CoffeeType.AMERICANO: {
                'coffee_weight': (15, 18),
                'water_weight': (180, 240),
                'temperature': (92, 96),
                'extraction_time': (20, 25),
                'pressure': (8, 9)
            }
        }
        
        if target_type in type_guidelines:
            guidelines = type_guidelines[target_type]
            recipe.coffee_weight = np.mean(guidelines['coffee_weight'])
            recipe.water_weight = np.mean(guidelines['water_weight'])
            recipe.temperature = np.mean(guidelines['temperature'])
            recipe.extraction_time = np.mean(guidelines['extraction_time'])
            recipe.pressure = np.mean(guidelines['pressure'])
        
        return recipe
    
    def _apply_data_optimization(self, recipe: CoffeeRecipe) -> CoffeeRecipe:
        """应用数据驱动的优化"""
        # 简单的参数微调逻辑
        # 在实际应用中可以使用更复杂的优化算法
        
        # 调整粉水比到理想范围 (1:15 - 1:18)
        current_ratio = recipe.water_weight / recipe.coffee_weight
        if current_ratio < 15:
            recipe.water_weight = recipe.coffee_weight * 16
        elif current_ratio > 18:
            recipe.water_weight = recipe.coffee_weight * 17
        
        # 调整水温到理想范围
        if recipe.temperature < 90:
            recipe.temperature = 92
        elif recipe.temperature > 96:
            recipe.temperature = 94
        
        return recipe

# ==================== PyQt5 界面组件 ====================

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
                             QLabel, QLineEdit, QComboBox, QDoubleSpinBox, 
                             QSpinBox, QTextEdit, QSlider, QPushButton,
                             QListWidget, QTabWidget, QTableWidget,
                             QTableWidgetItem, QProgressBar, QSplitter,
                             QFrame, QMessageBox, QFileDialog)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QValueAxis
from PyQt5.QtGui import QFont, QPainter

class ParameterControl(QWidget):
    """参数控制组件"""
    valueChanged = pyqtSignal(str, float)
    
    def __init__(self, param_name: str, param_key: str, min_val: float, max_val: float, 
                 default_val: float, unit: str = "", step: float = 1.0):
        super().__init__()
        self.param_name = param_name
        self.param_key = param_key
        self.unit = unit
        self._setup_ui(min_val, max_val, default_val, step)
    
    def _setup_ui(self, min_val: float, max_val: float, default_val: float, step: float):
        layout = QVBoxLayout()
        
        # 参数标签
        self.label = QLabel(f"{self.param_name}: {default_val}{self.unit}")
        layout.addWidget(self.label)
        
        # 滑动条
        slider_layout = QHBoxLayout()
        
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(int(min_val * 10))
        self.slider.setMaximum(int(max_val * 10))
        self.slider.setValue(int(default_val * 10))
        self.slider.valueChanged.connect(self._on_slider_changed)
        
        self.spinbox = QDoubleSpinBox()
        self.spinbox.setRange(min_val, max_val)
        self.spinbox.setValue(default_val)
        self.spinbox.setSingleStep(step)
        self.spinbox.valueChanged.connect(self._on_spinbox_changed)
        
        slider_layout.addWidget(self.slider)
        slider_layout.addWidget(self.spinbox)
        layout.addLayout(slider_layout)
        
        self.setLayout(layout)
    
    def _on_slider_changed(self, value):
        actual_value = value / 10.0
        self.spinbox.setValue(actual_value)
        self._update_display(actual_value)
        self.valueChanged.emit(self.param_key, actual_value)  # 使用 param_key
    
    def _on_spinbox_changed(self, value):
        self.slider.setValue(int(value * 10))
        self._update_display(value)
        self.valueChanged.emit(self.param_key, value)  # 使用 param_key
    
    def _update_display(self, value):
        self.label.setText(f"{self.param_name}: {value}{self.unit}")
    
    def get_value(self) -> float:
        return self.spinbox.value()

class BrewingChartWidget(QWidget):
    """冲泡过程图表组件"""
    
    def __init__(self):
        super().__init__()
        self.series_pressure = QLineSeries()
        self.series_flow = QLineSeries()
        self._setup_chart()
    
    def _setup_chart(self):
        layout = QVBoxLayout()
        
        # 创建图表
        self.chart = QChart()
        self.chart.setTitle("冲泡过程监控")
        self.chart.setAnimationOptions(QChart.SeriesAnimations)
        
        # 添加数据系列
        self.series_pressure.setName("压力 (bar)")
        self.series_flow.setName("流速 (ml/s)")
        
        self.chart.addSeries(self.series_pressure)
        self.chart.addSeries(self.series_flow)
        
        # 设置坐标轴
        axis_x = QValueAxis()
        axis_x.setTitleText("时间 (秒)")
        axis_x.setRange(0, 30)
        
        axis_y = QValueAxis()
        axis_y.setTitleText("数值")
        axis_y.setRange(0, 12)
        
        self.chart.addAxis(axis_x, Qt.AlignBottom)
        self.chart.addAxis(axis_y, Qt.AlignLeft)
        
        self.series_pressure.attachAxis(axis_x)
        self.series_pressure.attachAxis(axis_y)
        self.series_flow.attachAxis(axis_x)
        self.series_flow.attachAxis(axis_y)
        
        # 图表视图
        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.Antialiasing)
        
        layout.addWidget(self.chart_view)
        self.setLayout(layout)
    
    def update_data(self, timeline_data: List[Dict]):
        """更新图表数据"""
        self.series_pressure.clear()
        self.series_flow.clear()
        
        for data_point in timeline_data:
            self.series_pressure.append(data_point['time'], data_point['pressure'])
            self.series_flow.append(data_point['time'], data_point['flow_rate'])

class RecipeEditorWidget(QWidget):
    """配方编辑器组件"""
    
    def __init__(self, recipe_manager: CoffeeRecipeManager):
        super().__init__()
        self.recipe_manager = recipe_manager
        self.current_recipe = None
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout()
        
        # 基本信息组
        info_group = QGroupBox("基本信息")
        info_layout = QVBoxLayout()
        
        # 配方名称
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("配方名称:"))
        self.name_edit = QLineEdit()
        name_layout.addWidget(self.name_edit)
        info_layout.addLayout(name_layout)
        
        # 咖啡类型
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("咖啡类型:"))
        self.type_combo = QComboBox()
        for coffee_type in CoffeeType:
            self.type_combo.addItem(coffee_type.value, coffee_type)
        type_layout.addWidget(self.type_combo)
        info_layout.addLayout(type_layout)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # 参数控制组
        params_group = QGroupBox("冲泡参数")
        params_layout = QVBoxLayout()
        
        # 创建参数控制器
        self.param_controls = {}
        
        parameters = [
            ("咖啡粉量", "coffee_weight", 10, 30, 18, "g", 0.1),
            ("水量", "water_weight", 100, 300, 36, "ml", 1),
            ("水温", "temperature", 85, 100, 92, "℃", 1),
            ("萃取时间", "extraction_time", 15, 45, 25, "秒", 1),
            ("压力", "pressure", 6, 12, 9, "bar", 0.1),
        ]
        
        for param_info in parameters:
            control = ParameterControl(*param_info)
            control.valueChanged.connect(self._on_parameter_changed)
            params_layout.addWidget(control)
            self.param_controls[param_info[1]] = control
        
        params_group.setLayout(params_layout)
        layout.addWidget(params_group)
        
        # 研磨度选择
        grind_group = QGroupBox("研磨设置")
        grind_layout = QHBoxLayout()
        grind_layout.addWidget(QLabel("研磨度:"))
        self.grind_combo = QComboBox()
        for grind_level in GrindLevel:
            self.grind_combo.addItem(grind_level.value, grind_level)
        grind_layout.addWidget(self.grind_combo)
        grind_group.setLayout(grind_layout)
        layout.addWidget(grind_group)
        
        # 描述和标签
        desc_group = QGroupBox("描述和标签")
        desc_layout = QVBoxLayout()
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("输入配方描述...")
        desc_layout.addWidget(self.desc_edit)
        desc_group.setLayout(desc_layout)
        layout.addWidget(desc_group)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        self.save_btn = QPushButton("保存配方")
        self.save_btn.clicked.connect(self._save_recipe)
        self.simulate_btn = QPushButton("模拟冲泡")
        self.simulate_btn.clicked.connect(self._simulate_brew)
        
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.simulate_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _on_parameter_changed(self, param_name: str, value: float):
        """参数变化处理"""
        # 可以在这里添加参数联动逻辑
        pass
    
    def load_recipe(self, recipe_name: str):
        """加载配方到编辑器"""
        recipe = self.recipe_manager.load_recipe(recipe_name)
        if recipe:
            self.current_recipe = recipe
            self._populate_fields(recipe)
    
    def _populate_fields(self, recipe: CoffeeRecipe):
        """填充表单字段"""
        self.name_edit.setText(recipe.name)
        self.type_combo.setCurrentText(recipe.coffee_type.value)
        self.param_controls['coffee_weight'].spinbox.setValue(recipe.coffee_weight)
        self.param_controls['water_weight'].spinbox.setValue(recipe.water_weight)
        self.param_controls['temperature'].spinbox.setValue(recipe.temperature)
        self.param_controls['extraction_time'].spinbox.setValue(recipe.extraction_time)
        self.param_controls['pressure'].spinbox.setValue(recipe.pressure)
        self.grind_combo.setCurrentText(recipe.grind_level.value)
        self.desc_edit.setText(recipe.description)
    
    def get_current_recipe(self) -> CoffeeRecipe:
        """获取当前编辑的配方"""
        return CoffeeRecipe(
            name=self.name_edit.text() or "未命名配方",
            coffee_type=CoffeeType(self.type_combo.currentData()),
            coffee_weight=self.param_controls['coffee_weight'].get_value(),
            water_weight=self.param_controls['water_weight'].get_value(),
            temperature=int(self.param_controls['temperature'].get_value()),
            grind_level=GrindLevel(self.grind_combo.currentData()),
            extraction_time=int(self.param_controls['extraction_time'].get_value()),
            pressure=self.param_controls['pressure'].get_value(),
            description=self.desc_edit.toPlainText()
        )
    
    def _save_recipe(self):
        """保存配方"""
        recipe = self.get_current_recipe()
        if self.recipe_manager.save_recipe(recipe):
            QMessageBox.information(self, "成功", f"配方 '{recipe.name}' 保存成功！")
    
    def _simulate_brew(self):
        """模拟冲泡"""
        recipe = self.get_current_recipe()
        simulator = CoffeeBrewingSimulator()
        result = simulator.simulate_brew(recipe)
        
        if result['success']:
            msg = f"""
模拟结果:
萃取率: {result['extraction_yield']:.1%}
浓度: {result['strength']:.2f}%
质量评分: {result['quality_score']:.1f}/10.0

建议:
{chr(10).join(result['recommendations'])}
            """
            QMessageBox.information(self, "模拟结果", msg)
        else:
            QMessageBox.warning(self, "错误", f"模拟失败: {result['error']}")

# ==================== 主应用程序 ====================

class IntelligentCoffeeSystem(QWidget):
    """智能咖啡系统主界面"""
    
    def __init__(self):
        super().__init__()
        self.recipe_manager = CoffeeRecipeManager()
        self.analyzer = CoffeeDataAnalyzer(self.recipe_manager)
        self.optimizer = CoffeeRecipeOptimizer(self.recipe_manager)
        self.simulator = CoffeeBrewingSimulator()
        
        self._setup_ui()
        self._load_sample_data()
    
    def _setup_ui(self):
        self.setWindowTitle("智能咖啡研制系统")
        self.setGeometry(100, 100, 1200, 800)
        
        main_layout = QHBoxLayout()
        
        # 左侧导航
        left_panel = self._create_left_panel()
        main_layout.addWidget(left_panel, 1)
        
        # 右侧主区域
        right_panel = self._create_right_panel()
        main_layout.addWidget(right_panel, 3)
        
        self.setLayout(main_layout)
    
    def _create_left_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout()
        
        # 配方列表
        recipe_group = QGroupBox("配方库")
        recipe_layout = QVBoxLayout()
        
        self.recipe_list = QListWidget()
        self._refresh_recipe_list()
        self.recipe_list.currentTextChanged.connect(self._on_recipe_selected)
        
        recipe_layout.addWidget(self.recipe_list)
        
        # 配方操作按钮
        btn_layout = QHBoxLayout()
        new_btn = QPushButton("新建")
        new_btn.clicked.connect(self._new_recipe)
        delete_btn = QPushButton("删除")
        delete_btn.clicked.connect(self._delete_recipe)
        
        btn_layout.addWidget(new_btn)
        btn_layout.addWidget(delete_btn)
        recipe_layout.addLayout(btn_layout)
        
        recipe_group.setLayout(recipe_layout)
        layout.addWidget(recipe_group)
        
        # 快速操作
        quick_group = QGroupBox("快速操作")
        quick_layout = QVBoxLayout()
        
        analyze_btn = QPushButton("分析数据")
        analyze_btn.clicked.connect(self._update_analysis)
        optimize_btn = QPushButton("优化配方")
        optimize_btn.clicked.connect(self._optimize_recipe)
        
        quick_layout.addWidget(analyze_btn)
        quick_layout.addWidget(optimize_btn)
        quick_group.setLayout(quick_layout)
        layout.addWidget(quick_group)
        
        panel.setLayout(layout)
        return panel
    
    def _create_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout()
        
        # 标签页
        self.tabs = QTabWidget()
        
        # 配方编辑标签页
        self.recipe_editor = RecipeEditorWidget(self.recipe_manager)
        self.tabs.addTab(self.recipe_editor, "配方编辑")
        
        # 冲泡监控标签页
        self.brewing_chart = BrewingChartWidget()
        self.tabs.addTab(self.brewing_chart, "冲泡监控")
        
        # 数据分析标签页
        self.analysis_widget = self._create_analysis_widget()
        self.tabs.addTab(self.analysis_widget, "数据分析")
        
        layout.addWidget(self.tabs)
        panel.setLayout(layout)
        return panel
    
    def _create_analysis_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 统计信息显示
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(3)
        self.stats_table.setHorizontalHeaderLabels(["参数", "平均值", "标准差"])
        layout.addWidget(self.stats_table)
        
        # 分析按钮
        analyze_btn = QPushButton("更新分析")
        analyze_btn.clicked.connect(self._update_analysis)
        layout.addWidget(analyze_btn)
        
        widget.setLayout(layout)
        return widget
    
    def _refresh_recipe_list(self):
        """刷新配方列表"""
        self.recipe_list.clear()
        recipes = self.recipe_manager.get_all_recipes()
        for recipe in recipes:
            self.recipe_list.addItem(recipe.name)
    
    def _load_sample_data(self):
        """加载示例数据"""
        sample_recipes = [
            CoffeeRecipe(
                name="经典意式浓缩",
                coffee_type=CoffeeType.ESPRESSO,
                coffee_weight=18.0,
                water_weight=36.0,
                temperature=92,
                grind_level=GrindLevel.FINE,
                extraction_time=25,
                pressure=9.0,
                description="标准的意式浓缩咖啡配方",
                rating=8.5,
                tags=["经典", "浓缩"]
            ),
            CoffeeRecipe(
                name="美式咖啡",
                coffee_type=CoffeeType.AMERICANO,
                coffee_weight=15.0,
                water_weight=180.0,
                temperature=94,
                grind_level=GrindLevel.MEDIUM,
                extraction_time=30,
                pressure=8.5,
                description="清淡的美式咖啡",
                rating=7.8,
                tags=["清淡", "美式"]
            )
        ]
        
        for recipe in sample_recipes:
            self.recipe_manager.save_recipe(recipe)
        
        self._refresh_recipe_list()
    
    def _on_recipe_selected(self, recipe_name: str):
        """配方选择处理"""
        if recipe_name:
            self.recipe_editor.load_recipe(recipe_name)
    
    def _new_recipe(self):
        """新建配方"""
        self.recipe_editor.current_recipe = None
        self.recipe_editor.name_edit.clear()
        self.recipe_editor.desc_edit.clear()
    
    def _delete_recipe(self):
        """删除配方"""
        current_item = self.recipe_list.currentItem()
        if current_item:
            recipe_name = current_item.text()
            reply = QMessageBox.question(self, "确认删除", 
                                       f"确定要删除配方 '{recipe_name}' 吗？")
            if reply == QMessageBox.Yes:
                if self.recipe_manager.delete_recipe(recipe_name):
                    self._refresh_recipe_list()
    
    def _update_analysis(self):
        """分析数据"""
        analysis = self.analyzer.analyze_recipe_trends()
        if analysis:
            # 更新统计表格
            self.stats_table.setRowCount(len(analysis['parameter_stats']))
            
            for i, (param, stats) in enumerate(analysis['parameter_stats'].items()):
                self.stats_table.setItem(i, 0, QTableWidgetItem(param))
                self.stats_table.setItem(i, 1, QTableWidgetItem(f"{stats['mean']:.2f}"))
                self.stats_table.setItem(i, 2, QTableWidgetItem(f"{stats['std']:.2f}"))
            
            QMessageBox.information(self, "分析完成", "数据分析已完成！")
    
    def _optimize_recipe(self):
        """优化配方"""
        current_recipe = self.recipe_editor.get_current_recipe()
        optimized = self.optimizer.optimize_recipe(current_recipe)
        
        msg = f"""
优化完成！
原配方评分: {current_recipe.rating:.1f}
优化后评分: {optimized.rating:.1f}

优化参数:
咖啡粉量: {optimized.coffee_weight}g
水量: {optimized.water_weight}ml
水温: {optimized.temperature}℃
萃取时间: {optimized.extraction_time}秒
压力: {optimized.pressure}bar
        """
        
        QMessageBox.information(self, "优化结果", msg)
        
        # 将优化后的配方加载到编辑器
        self.recipe_editor.current_recipe = optimized
        self.recipe_editor._populate_fields(optimized)

# ==================== 使用示例 ====================

if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    # 设置日志
    logging.basicConfig(level=logging.INFO)
    
    app = QApplication(sys.argv)
    
    # 创建系统实例
    coffee_system = IntelligentCoffeeSystem()
    coffee_system.show()
    
    sys.exit(app.exec_())