import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import seaborn as sns
from scipy import stats, signal
import sqlite3
import json
import pickle
import warnings
warnings.filterwarnings('ignore')

# 机器学习库
from sklearn.ensemble import RandomForestClassifier, IsolationForest, GradientBoostingClassifier
from sklearn.cluster import KMeans, DBSCAN
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.decomposition import PCA
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from sklearn.linear_model import LogisticRegression
import xgboost as xgb
import lightgbm as lgb

# 深度学习库
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    DEEP_LEARNING_AVAILABLE = True
except ImportError:
    DEEP_LEARNING_AVAILABLE = False

# PyQt5 导入
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtChart import *

# ============================ 增强版血液分析引擎 ============================
class EnhancedBloodAnalysisEngine:
    def __init__(self):
        # 扩展参考范围（包含不同年龄段）
        self.reference_ranges = self._init_reference_ranges()
        
        # 增强疾病模式识别
        self.disease_patterns = self._init_disease_patterns()
        
        # 高级机器学习模型
        self.ml_models = {}
        self.dl_models = {}
        self.scaler = StandardScaler()
        self.feature_selector = None
        self.is_trained = False
        
        # 趋势分析参数
        self.trend_windows = {'short': 5, 'medium': 10, 'long': 20}
        
    def _init_reference_ranges(self):
        """初始化包含不同年龄段的参考范围"""
        ranges = {
            'adult': {
                'WBC': (4.0, 10.0), 'RBC': (4.5, 6.0), 'HGB': (13.5, 17.5),
                'HCT': (40, 50), 'PLT': (150, 400), 'MCV': (80, 100),
                'MCH': (27, 31), 'MCHC': (32, 36), 'NEUT': (40, 75),
                'LYMPH': (20, 50), 'MONO': (2, 10), 'EOS': (0, 6),
                'BASO': (0, 2), 'RDW': (11.5, 14.5), 'MPV': (7.5, 11.5),
                'PCT': (0.15, 0.35), 'PDW': (10, 18)
            },
            'pediatric': {
                'WBC': (5.0, 15.0), 'RBC': (4.0, 5.5), 'HGB': (11.0, 16.0),
                'HCT': (35, 45), 'PLT': (150, 450), 'MCV': (70, 90),
                'MCH': (25, 29), 'MCHC': (31, 35), 'NEUT': (30, 60),
                'LYMPH': (30, 60), 'MONO': (2, 12), 'EOS': (0, 8),
                'BASO': (0, 3), 'RDW': (12.0, 15.0), 'MPV': (7.0, 11.0)
            },
            'geriatric': {
                'WBC': (3.5, 9.0), 'RBC': (4.0, 5.5), 'HGB': (12.0, 16.0),
                'HCT': (36, 48), 'PLT': (140, 380), 'MCV': (82, 102),
                'MCH': (26, 32), 'MCHC': (31, 36), 'NEUT': (35, 70),
                'LYMPH': (20, 45), 'MONO': (2, 10), 'EOS': (0, 6),
                'BASO': (0, 2), 'RDW': (12.0, 15.5), 'MPV': (7.5, 12.0)
            }
        }
        return ranges
    
    def _init_disease_patterns(self):
        """初始化增强疾病模式"""
        patterns = {
            'iron_deficiency_anemia': {
                'conditions': ['HGB < 13', 'MCV < 80', 'MCH < 27', 'RDW > 14.5', 'FER < 15'],
                'confidence': 0.85,
                'severity': 'moderate',
                'suggestions': [
                    '检查铁蛋白和转铁蛋白饱和度',
                    '考虑铁剂治疗',
                    '评估潜在出血源',
                    '检查粪便潜血'
                ],
                'differential': ['慢性病贫血', '地中海贫血']
            },
            'megaloblastic_anemia': {
                'conditions': ['HGB < 13', 'MCV > 100', 'MCH > 31', 'LDH > 250'],
                'confidence': 0.80,
                'severity': 'moderate',
                'suggestions': [
                    '检查维生素B12和叶酸水平',
                    '考虑营养补充治疗',
                    '评估胃肠道吸收功能'
                ],
                'differential': ['骨髓增生异常综合征', '肝病相关贫血']
            },
            'infection_inflammation': {
                'conditions': ['WBC > 10', 'NEUT > 75', 'LYMPH < 20', 'CRP > 10'],
                'confidence': 0.75,
                'severity': 'mild',
                'suggestions': [
                    '检查C反应蛋白和血沉',
                    '评估感染源',
                    '考虑抗生素治疗',
                    '监测体温和症状'
                ],
                'differential': ['应激反应', '药物反应']
            },
            'leukemia_suspect': {
                'conditions': ['WBC > 30', 'PLT < 100', 'HGB < 10', 'BLAST > 5'],
                'confidence': 0.90,
                'severity': 'high',
                'suggestions': [
                    '立即进行骨髓穿刺检查',
                    '请血液科专家会诊',
                    '进行流式细胞术分析',
                    '染色体核型分析'
                ],
                'differential': ['类白血病反应', '骨髓纤维化']
            },
            'thrombocytopenia': {
                'conditions': ['PLT < 150', 'MPV > 11.5', 'PCT < 0.15'],
                'confidence': 0.70,
                'severity': 'moderate',
                'suggestions': [
                    '检查骨髓功能',
                    '评估免疫状态',
                    '考虑血小板输注指征',
                    '检查抗血小板抗体'
                ],
                'differential': ['假性血小板减少', '脾功能亢进']
            }
        }
        return patterns
    
    def set_age_group(self, age_group='adult'):
        """设置年龄组参考范围"""
        self.current_ranges = self.reference_ranges.get(age_group, self.reference_ranges['adult'])
    
    def analyze_sample_comprehensive(self, sample_data, patient_info=None):
        """综合分析样本"""
        # 设置年龄组
        age_group = self._determine_age_group(patient_info)
        self.set_age_group(age_group)
        
        analysis_result = {
            'basic_analysis': self.analyze_sample_basic(sample_data),
            'pattern_analysis': self.analyze_disease_patterns(sample_data),
            'risk_assessment': self.assess_comprehensive_risk(sample_data, patient_info),
            'trend_analysis': {},
            'ml_predictions': {},
            'quality_control': self.check_sample_quality(sample_data),
            'clinical_correlations': self.analyze_clinical_correlations(sample_data, patient_info),
            'timestamp': datetime.now()
        }
        
        # 添加机器学习预测
        if self.is_trained:
            analysis_result['ml_predictions'] = self.advanced_ml_predict(sample_data)
            
            # 深度学习预测（如果可用）
            if DEEP_LEARNING_AVAILABLE and self.dl_models:
                analysis_result['dl_predictions'] = self.deep_learning_predict(sample_data)
        
        return analysis_result
    
    def analyze_sample_basic(self, sample_data):
        """基础样本分析"""
        result = {
            'parameters': {},
            'abnormalities': [],
            'summary': {}
        }
        
        for param, value in sample_data.items():
            if param in self.current_ranges:
                low, high = self.current_ranges[param]
                status = 'Normal'
                deviation = 0
                severity = 'none'
                
                if value < low:
                    status = 'Low'
                    deviation = (low - value) / low * 100
                    severity = self._assess_deviation_severity(deviation, 'low')
                    result['abnormalities'].append({
                        'parameter': param,
                        'value': value,
                        'status': status,
                        'deviation': deviation,
                        'severity': severity,
                        'reference_range': (low, high)
                    })
                elif value > high:
                    status = 'High'
                    deviation = (value - high) / high * 100
                    severity = self._assess_deviation_severity(deviation, 'high')
                    result['abnormalities'].append({
                        'parameter': param,
                        'value': value,
                        'status': status,
                        'deviation': deviation,
                        'severity': severity,
                        'reference_range': (low, high)
                    })
                
                result['parameters'][param] = {
                    'value': value,
                    'range': (low, high),
                    'status': status,
                    'deviation': deviation,
                    'severity': severity
                }
        
        # 计算汇总统计
        result['summary'] = self._calculate_summary_stats(result)
        return result
    
    def _assess_deviation_severity(self, deviation, direction):
        """评估偏离严重程度"""
        abs_deviation = abs(deviation)
        if abs_deviation < 10:
            return 'mild'
        elif abs_deviation < 25:
            return 'moderate'
        elif abs_deviation < 50:
            return 'severe'
        else:
            return 'critical'
    
    def analyze_disease_patterns(self, sample_data):
        """疾病模式识别分析"""
        patterns_detected = []
        
        for disease, pattern in self.disease_patterns.items():
            match_score = self._calculate_pattern_match(sample_data, pattern['conditions'])
            confidence = pattern['confidence'] * match_score
            
            if match_score >= 0.6:  # 60%匹配阈值
                patterns_detected.append({
                    'disease': disease,
                    'display_name': disease.replace('_', ' ').title(),
                    'confidence': confidence,
                    'match_score': match_score,
                    'severity': pattern['severity'],
                    'suggestions': pattern['suggestions'],
                    'differential_diagnosis': pattern.get('differential', []),
                    'urgency': self._determine_urgency(confidence, pattern['severity'])
                })
        
        # 按置信度和紧急程度排序
        patterns_detected.sort(key=lambda x: (x['urgency'], x['confidence']), reverse=True)
        return patterns_detected
    
    def _calculate_pattern_match(self, sample_data, conditions):
        """计算模式匹配度"""
        matched = 0
        total = len(conditions)
        
        for condition in conditions:
            param, op, value = self._parse_condition(condition)
            if param and param in sample_data:
                param_value = sample_data[param]
                
                if op == '<' and param_value < float(value):
                    matched += 1
                elif op == '>' and param_value > float(value):
                    matched += 1
                elif op == '<=' and param_value <= float(value):
                    matched += 1
                elif op == '>=' and param_value >= float(value):
                    matched += 1
        
        return matched / total if total > 0 else 0
    
    def _determine_urgency(self, confidence, severity):
        """确定紧急程度"""
        urgency_score = confidence * 100
        if severity == 'high':
            urgency_score += 50
        elif severity == 'moderate':
            urgency_score += 25
        return urgency_score
    
    def assess_comprehensive_risk(self, sample_data, patient_info=None):
        """综合风险评估"""
        basic_analysis = self.analyze_sample_basic(sample_data)
        
        risk_score = 0
        risk_factors = []
        
        # 基于异常参数
        for abnormality in basic_analysis['abnormalities']:
            severity_weight = {
                'mild': 1, 'moderate': 2, 'severe': 4, 'critical': 8
            }.get(abnormality['severity'], 1)
            
            risk_score += abs(abnormality['deviation']) * 0.1 * severity_weight
            risk_factors.append(f"{abnormality['parameter']} {abnormality['status']}")
        
        # 基于关键参数
        critical_params = ['WBC', 'HGB', 'PLT']
        for param in critical_params:
            if param in basic_analysis['parameters']:
                status = basic_analysis['parameters'][param]['status']
                if status != 'Normal':
                    risk_score += 15
        
        # 基于疾病模式
        patterns = self.analyze_disease_patterns(sample_data)
        for pattern in patterns:
            risk_score += pattern['confidence'] * 20
        
        # 基于患者信息（如果有）
        if patient_info:
            risk_score = self._adjust_risk_by_patient_info(risk_score, patient_info)
        
        risk_level = self._determine_risk_level(risk_score)
        
        return {
            'score': min(risk_score, 100),
            'level': risk_level,
            'factors': risk_factors,
            'recommendations': self._generate_risk_recommendations(risk_level, patterns)
        }
    
    def _adjust_risk_by_patient_info(self, risk_score, patient_info):
        """根据患者信息调整风险分数"""
        # 年龄因素
        age = patient_info.get('age', 0)
        if age < 1 or age > 70:  # 婴儿和老年人风险更高
            risk_score *= 1.2
        
        # 病史因素
        medical_history = patient_info.get('medical_history', {})
        if 'anemia' in medical_history:
            risk_score *= 1.3
        if 'cancer' in medical_history:
            risk_score *= 1.5
        
        return risk_score
    
    def _determine_risk_level(self, score):
        """确定风险等级"""
        if score < 15:
            return 'Low'
        elif score < 40:
            return 'Moderate'
        elif score < 70:
            return 'High'
        else:
            return 'Critical'
    
    def check_sample_quality(self, sample_data):
        """样本质量控制检查"""
        quality_issues = []
        
        # 检查参数完整性
        required_params = ['WBC', 'RBC', 'HGB', 'PLT']
        missing_params = [p for p in required_params if p not in sample_data]
        if missing_params:
            quality_issues.append(f"缺少关键参数: {', '.join(missing_params)}")
        
        # 检查参数一致性
        if 'RBC' in sample_data and 'HGB' in sample_data:
            hgb_rbc_ratio = sample_data['HGB'] / sample_data['RBC']
            if not (2.8 <= hgb_rbc_ratio <= 3.5):
                quality_issues.append("HGB/RBC比率异常，可能样本有问题")
        
        # 检查技术性错误
        for param, value in sample_data.items():
            if value <= 0:
                quality_issues.append(f"{param}值异常低")
            elif value > 1000:  # 不合理的高值
                quality_issues.append(f"{param}值异常高")
        
        return {
            'status': 'Good' if not quality_issues else 'Questionable',
            'issues': quality_issues,
            'score': 100 - len(quality_issues) * 10
        }
    
    def analyze_clinical_correlations(self, sample_data, patient_info=None):
        """临床相关性分析"""
        correlations = []
        
        # 贫血相关分析
        if 'HGB' in sample_data and sample_data['HGB'] < 13:
            correlations.append({
                'type': 'anemia_analysis',
                'findings': self._analyze_anemia_type(sample_data),
                'clinical_significance': '需要进一步评估贫血原因'
            })
        
        # 感染/炎症分析
        if 'WBC' in sample_data and sample_data['WBC'] > 10:
            correlations.append({
                'type': 'infection_analysis',
                'findings': self._analyze_infection_pattern(sample_data),
                'clinical_significance': '提示感染或炎症状态'
            })
        
        # 出血风险分析
        if 'PLT' in sample_data and sample_data['PLT'] < 150:
            correlations.append({
                'type': 'bleeding_risk',
                'findings': self._assess_bleeding_risk(sample_data),
                'clinical_significance': '出血风险增加'
            })
        
        return correlations
    
    def _analyze_anemia_type(self, sample_data):
        """分析贫血类型"""
        findings = []
        
        if 'MCV' in sample_data:
            if sample_data['MCV'] < 80:
                findings.append("小细胞性贫血，提示缺铁性或地中海贫血")
            elif sample_data['MCV'] > 100:
                findings.append("大细胞性贫血，提示巨幼细胞性贫血")
            else:
                findings.append("正细胞性贫血，可能为慢性病或溶血性")
        
        if 'RDW' in sample_data and sample_data['RDW'] > 15:
            findings.append("红细胞分布宽度增加，提示缺铁性贫血可能")
        
        return findings
    
    def advanced_ml_predict(self, sample_data):
        """高级机器学习预测"""
        predictions = {}
        
        try:
            # 准备特征
            features = self._prepare_features(sample_data)
            features_scaled = self.scaler.transform([features])
            
            for model_name, model in self.ml_models.items():
                if hasattr(model, 'predict_proba'):
                    proba = model.predict_proba(features_scaled)[0]
                    prediction = model.predict(features_scaled)[0]
                    
                    predictions[model_name] = {
                        'prediction': prediction,
                        'probability': max(proba),
                        'confidence': 'high' if max(proba) > 0.8 else 'medium' if max(proba) > 0.6 else 'low',
                        'class_probabilities': dict(zip(model.classes_, proba))
                    }
                else:
                    prediction = model.predict(features_scaled)[0]
                    predictions[model_name] = {
                        'prediction': prediction,
                        'probability': 1.0,
                        'confidence': 'unknown'
                    }
                    
        except Exception as e:
            predictions['error'] = str(e)
            
        return predictions
    
    def deep_learning_predict(self, sample_data):
        """深度学习预测"""
        if not DEEP_LEARNING_AVAILABLE or not self.dl_models:
            return {'error': 'Deep learning not available'}
        
        predictions = {}
        
        try:
            features = self._prepare_features(sample_data)
            features_tensor = torch.FloatTensor([features])
            
            for model_name, model in self.dl_models.items():
                model.eval()
                with torch.no_grad():
                    output = model(features_tensor)
                    probabilities = torch.softmax(output, dim=1)
                    pred_prob, pred_class = torch.max(probabilities, 1)
                    
                    predictions[model_name] = {
                        'prediction': pred_class.item(),
                        'probability': pred_prob.item(),
                        'confidence': 'high' if pred_prob.item() > 0.8 else 'medium'
                    }
                    
        except Exception as e:
            predictions['error'] = str(e)
            
        return predictions
    
    def train_advanced_models(self, training_data, target_variables, model_types=None):
        """训练高级机器学习模型"""
        if model_types is None:
            model_types = ['random_forest', 'xgboost', 'svm', 'neural_network']
        
        try:
            # 准备特征数据
            feature_columns = self._get_feature_columns()
            X = training_data[feature_columns].fillna(0)
            y_dict = target_variables
            
            # 标准化特征
            self.scaler.fit(X)
            X_scaled = self.scaler.transform(X)
            
            models_trained = {}
            
            for target_name, y in y_dict.items():
                target_models = {}
                
                # 数据分割
                X_train, X_test, y_train, y_test = train_test_split(
                    X_scaled, y, test_size=0.2, random_state=42, stratify=y
                )
                
                # 训练不同模型
                if 'random_forest' in model_types:
                    rf_model = RandomForestClassifier(
                        n_estimators=200, max_depth=10, random_state=42
                    )
                    rf_model.fit(X_train, y_train)
                    target_models['random_forest'] = rf_model
                
                if 'xgboost' in model_types:
                    xgb_model = xgb.XGBClassifier(
                        n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42
                    )
                    xgb_model.fit(X_train, y_train)
                    target_models['xgboost'] = xgb_model
                
                if 'svm' in model_types:
                    svm_model = SVC(probability=True, random_state=42)
                    svm_model.fit(X_train, y_train)
                    target_models['svm'] = svm_model
                
                if 'neural_network' in model_types and DEEP_LEARNING_AVAILABLE:
                    # 简单的神经网络
                    dl_model = self._create_simple_nn(X_train.shape[1], len(np.unique(y)))
                    dl_model = self._train_pytorch_model(dl_model, X_train, y_train)
                    target_models['neural_network'] = dl_model
                
                # 评估模型
                model_performance = {}
                for model_name, model in target_models.items():
                    if model_name == 'neural_network':
                        # 深度学习模型评估
                        performance = self._evaluate_dl_model(model, X_test, y_test)
                    else:
                        # 传统机器学习模型评估
                        performance = self._evaluate_ml_model(model, X_test, y_test)
                    
                    model_performance[model_name] = performance
                
                # 选择最佳模型
                best_model_name = max(model_performance, 
                                   key=lambda x: model_performance[x].get('accuracy', 0))
                self.ml_models[target_name] = target_models[best_model_name]
                models_trained[target_name] = {
                    'best_model': best_model_name,
                    'performance': model_performance[best_model_name],
                    'all_performance': model_performance
                }
            
            self.is_trained = True
            return models_trained
            
        except Exception as e:
            print(f"模型训练错误: {e}")
            return False
    
    def _create_simple_nn(self, input_size, output_size):
        """创建简单神经网络"""
        class SimpleNN(nn.Module):
            def __init__(self, input_size, hidden_size=64, output_size=2):
                super(SimpleNN, self).__init__()
                self.fc1 = nn.Linear(input_size, hidden_size)
                self.fc2 = nn.Linear(hidden_size, hidden_size//2)
                self.fc3 = nn.Linear(hidden_size//2, output_size)
                self.relu = nn.ReLU()
                self.dropout = nn.Dropout(0.2)
                
            def forward(self, x):
                x = self.relu(self.fc1(x))
                x = self.dropout(x)
                x = self.relu(self.fc2(x))
                x = self.dropout(x)
                x = self.fc3(x)
                return x
        
        return SimpleNN(input_size, output_size=output_size)
    
    def _train_pytorch_model(self, model, X_train, y_train, epochs=100):
        """训练PyTorch模型"""
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(model.parameters(), lr=0.001)
        
        X_tensor = torch.FloatTensor(X_train)
        y_tensor = torch.LongTensor(y_train.values if hasattr(y_train, 'values') else y_train)
        
        for epoch in range(epochs):
            model.train()
            optimizer.zero_grad()
            outputs = model(X_tensor)
            loss = criterion(outputs, y_tensor)
            loss.backward()
            optimizer.step()
        
        return model
    
    def _evaluate_ml_model(self, model, X_test, y_test):
        """评估机器学习模型"""
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test) if hasattr(model, 'predict_proba') else None
        
        accuracy = np.mean(y_pred == y_test)
        report = classification_report(y_test, y_pred, output_dict=True)
        
        performance = {
            'accuracy': accuracy,
            'precision': report['weighted avg']['precision'],
            'recall': report['weighted avg']['recall'],
            'f1_score': report['weighted avg']['f1-score']
        }
        
        if y_pred_proba is not None and len(np.unique(y_test)) == 2:
            performance['auc_roc'] = roc_auc_score(y_test, y_pred_proba[:, 1])
        
        return performance
    
    def _evaluate_dl_model(self, model, X_test, y_test):
        """评估深度学习模型"""
        model.eval()
        X_tensor = torch.FloatTensor(X_test)
        with torch.no_grad():
            outputs = model(X_tensor)
            _, predictions = torch.max(outputs, 1)
        
        accuracy = np.mean(predictions.numpy() == y_test)
        
        return {
            'accuracy': accuracy,
            'precision': 'N/A',  # 简化评估
            'recall': 'N/A',
            'f1_score': 'N/A'
        }
    
    def _prepare_features(self, sample_data):
        """准备特征数据"""
        feature_columns = self._get_feature_columns()
        features = []
        
        for feature in feature_columns:
            features.append(sample_data.get(feature, 0))
        
        return features
    
    def _get_feature_columns(self):
        """获取特征列"""
        return ['WBC', 'RBC', 'HGB', 'HCT', 'PLT', 'MCV', 'MCH', 'MCHC', 
                'NEUT', 'LYMPH', 'MONO', 'EOS', 'BASO', 'RDW', 'MPV']
    
    def _determine_age_group(self, patient_info):
        """确定年龄组"""
        if not patient_info:
            return 'adult'
        
        age = patient_info.get('age', 0)
        if age < 18:
            return 'pediatric'
        elif age > 65:
            return 'geriatric'
        else:
            return 'adult'
    
    def _parse_condition(self, condition):
        """解析条件字符串"""
        import re
        match = re.match(r'([A-Za-z]+)\s*([<>=]+)\s*([0-9.]+)', condition)
        if match:
            return match.group(1), match.group(2), match.group(3)
        return None, None, None
    
    def _calculate_summary_stats(self, analysis_result):
        """计算汇总统计"""
        abnormalities = analysis_result['abnormalities']
        total_params = len(analysis_result['parameters'])
        abnormal_count = len(abnormalities)
        
        severity_counts = {'mild': 0, 'moderate': 0, 'severe': 0, 'critical': 0}
        for ab in abnormalities:
            severity_counts[ab['severity']] += 1
        
        return {
            'total_parameters': total_params,
            'abnormal_count': abnormal_count,
            'abnormal_percentage': (abnormal_count / total_params * 100) if total_params > 0 else 0,
            'severity_breakdown': severity_counts,
            'overall_status': 'Normal' if abnormal_count == 0 else 'Abnormal'
        }
    
    def _generate_risk_recommendations(self, risk_level, patterns):
        """生成风险建议"""
        recommendations = []
        
        if risk_level == 'Critical':
            recommendations.extend([
                "立即进行临床评估",
                "考虑紧急处理措施",
                "通知主治医师"
            ])
        elif risk_level == 'High':
            recommendations.extend([
                "尽快进行详细评估",
                "考虑专科会诊",
                "密切监测参数变化"
            ])
        
        # 基于检测到的模式添加建议
        for pattern in patterns[:2]:  # 只考虑前2个最可能的模式
            recommendations.extend(pattern['suggestions'][:2])
        
        if not recommendations:
            recommendations.append("常规随访观察")
        
        return recommendations

# ============================ 增强版数据库管理器 ============================
class EnhancedBloodDatabaseManager:
    def __init__(self, db_path='enhanced_blood_analysis.db'):
        self.db_path = db_path
        self.init_enhanced_database()
    
    def init_enhanced_database(self):
        """初始化增强数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 增强样本表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS enhanced_samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sample_id TEXT UNIQUE,
                patient_id TEXT,
                timestamp DATETIME,
                sample_data TEXT,
                basic_analysis TEXT,
                pattern_analysis TEXT,
                risk_assessment TEXT,
                quality_control TEXT,
                clinical_correlations TEXT,
                ml_predictions TEXT,
                dl_predictions TEXT,
                comprehensive_result TEXT,
                technician_notes TEXT,
                verification_status TEXT DEFAULT 'unverified',
                created_by TEXT,
                last_modified DATETIME
            )
        ''')
        
        # 增强患者表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS enhanced_patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT UNIQUE,
                name TEXT,
                age INTEGER,
                gender TEXT,
                birth_date DATE,
                contact_info TEXT,
                emergency_contact TEXT,
                medical_history TEXT,
                current_medications TEXT,
                allergies TEXT,
                primary_physician TEXT,
                insurance_info TEXT,
                created_date DATETIME,
                last_visit DATETIME,
                status TEXT DEFAULT 'active'
            )
        ''')
        
        # 用户和权限表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password_hash TEXT,
                role TEXT,
                full_name TEXT,
                email TEXT,
                department TEXT,
                permissions TEXT,
                last_login DATETIME,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        # 审计日志表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                user_id TEXT,
                action TEXT,
                resource_type TEXT,
                resource_id TEXT,
                details TEXT,
                ip_address TEXT
            )
        ''')
        
        # 报告模板表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS report_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_name TEXT,
                template_type TEXT,
                content TEXT,
                styles TEXT,
                created_by TEXT,
                created_date DATETIME,
                is_default INTEGER DEFAULT 0
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_enhanced_sample(self, sample_data, comprehensive_analysis, user_info=None):
        """保存增强样本数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            current_time = datetime.now()
            
            cursor.execute('''
                INSERT OR REPLACE INTO enhanced_samples 
                (sample_id, patient_id, timestamp, sample_data, basic_analysis, 
                 pattern_analysis, risk_assessment, quality_control, clinical_correlations,
                 ml_predictions, dl_predictions, comprehensive_result, technician_notes,
                 created_by, last_modified)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                sample_data.get('sample_id', f"SMP_{current_time.strftime('%Y%m%d_%H%M%S')}"),
                sample_data.get('patient_id', 'UNKNOWN'),
                sample_data.get('timestamp', current_time),
                json.dumps(sample_data, default=str),
                json.dumps(comprehensive_analysis.get('basic_analysis', {}), default=str),
                json.dumps(comprehensive_analysis.get('pattern_analysis', {}), default=str),
                json.dumps(comprehensive_analysis.get('risk_assessment', {}), default=str),
                json.dumps(comprehensive_analysis.get('quality_control', {}), default=str),
                json.dumps(comprehensive_analysis.get('clinical_correlations', {}), default=str),
                json.dumps(comprehensive_analysis.get('ml_predictions', {}), default=str),
                json.dumps(comprehensive_analysis.get('dl_predictions', {}), default=str),
                json.dumps(comprehensive_analysis, default=str),
                sample_data.get('technician_notes', ''),
                user_info.get('username', 'system') if user_info else 'system',
                current_time
            ))
            
            # 记录审计日志
            if user_info:
                self.log_audit_action(
                    user_info['username'],
                    'CREATE_SAMPLE',
                    'sample',
                    cursor.lastrowid,
                    f"Created sample {sample_data.get('sample_id', 'Unknown')}"
                )
            
            conn.commit()
            return True
        except Exception as e:
            print(f"保存样本错误: {e}")
            return False
        finally:
            conn.close()
    
    def log_audit_action(self, username, action, resource_type, resource_id, details):
        """记录审计日志"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO audit_log 
                (timestamp, user_id, action, resource_type, resource_id, details)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now(),
                username,
                action,
                resource_type,
                resource_id,
                details
            ))
            
            conn.commit()
        except Exception as e:
            print(f"审计日志错误: {e}")
        finally:
            conn.close()

# ============================ 高级可视化组件 ============================
class AdvancedBloodChartWidget(FigureCanvas):
    def __init__(self, parent=None, width=10, height=8, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        
        self.axes_dict = {}
        self.current_layout = 'single'
        
    def set_layout(self, rows, cols, layout_type='grid'):
        """设置图表布局"""
        self.fig.clear()
        
        if layout_type == 'grid' and rows * cols > 1:
            self.axes_dict = {}
            for i in range(rows * cols):
                row = i // cols
                col = i % cols
                self.axes_dict[f'ax_{i}'] = self.fig.add_subplot(rows, cols, i+1)
            self.current_layout = f'grid_{rows}x{cols}'
        else:
            self.axes_dict['main'] = self.fig.add_subplot(111)
            self.current_layout = 'single'
        
        self.fig.tight_layout()
        self.draw()
    
    def plot_comprehensive_dashboard(self, samples, patient_info=None):
        """绘制综合仪表盘"""
        self.set_layout(2, 2)
        
        if not samples:
            return
        
        # 1. 参数趋势图
        self._plot_parameter_trends(samples, 'ax_0')
        
        # 2. 风险等级分布
        self._plot_risk_distribution(samples, 'ax_1')
        
        # 3. 异常参数热图
        self._plot_abnormality_heatmap(samples, 'ax_2')
        
        # 4. 疾病模式检测
        self._plot_disease_patterns(samples, 'ax_3')
        
        self.fig.suptitle('血液分析综合仪表盘', fontsize=16, fontweight='bold')
        self.fig.tight_layout(rect=[0, 0, 1, 0.96])
        self.draw()
    
    def _plot_parameter_trends(self, samples, ax_key):
        """绘制参数趋势图"""
        if ax_key not in self.axes_dict:
            return
        
        ax = self.axes_dict[ax_key]
        
        key_params = ['WBC', 'HGB', 'PLT']
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1']
        
        dates = []
        param_values = {param: [] for param in key_params}
        
        for sample in samples:
            timestamp = sample.get('timestamp')
            if isinstance(timestamp, str):
                try:
                    dates.append(datetime.fromisoformat(timestamp.replace('Z', '')))
                except:
                    dates.append(len(dates))
            else:
                dates.append(len(dates))
            
            for param in key_params:
                if 'parameters' in sample and param in sample['parameters']:
                    param_values[param].append(sample['parameters'][param]['value'])
                else:
                    param_values[param].append(np.nan)
        
        # 确保日期排序
        sorted_indices = sorted(range(len(dates)), key=lambda i: dates[i])
        dates = [dates[i] for i in sorted_indices]
        
        for i, param in enumerate(key_params):
            values = [param_values[param][i] for i in sorted_indices]
            ax.plot(dates, values, marker='o', label=param, color=colors[i], linewidth=2, markersize=4)
            
            # 添加趋势线
            if len(values) > 1:
                x_numeric = range(len(values))
                z = np.polyfit(x_numeric, values, 1)
                p = np.poly1d(z)
                ax.plot(dates, p(x_numeric), '--', color=colors[i], alpha=0.7)
        
        ax.set_title('关键参数趋势分析')
        ax.set_ylabel('数值')
        ax.legend()
        ax.grid(True, linestyle='--', alpha=0.7)
        ax.tick_params(axis='x', rotation=45)
    
    def _plot_risk_distribution(self, samples, ax_key):
        """绘制风险等级分布"""
        if ax_key not in self.axes_dict:
            return
        
        ax = self.axes_dict[ax_key]
        
        risk_levels = [s.get('risk_assessment', {}).get('level', 'Unknown') for s in samples]
        risk_counts = {
            'Critical': risk_levels.count('Critical'),
            'High': risk_levels.count('High'),
            'Moderate': risk_levels.count('Moderate'),
            'Low': risk_levels.count('Low')
        }
        
        colors = ['#DC143C', '#FF4500', '#FFD700', '#32CD32']
        bars = ax.bar(risk_counts.keys(), risk_counts.values(), color=colors)
        
        # 添加数值标签
        for bar, count in zip(bars, risk_counts.values()):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                   f'{count}', ha='center', va='bottom')
        
        ax.set_title('风险等级分布')
        ax.set_ylabel('样本数量')
        ax.grid(True, axis='y', linestyle='--', alpha=0.7)
    
    def _plot_abnormality_heatmap(self, samples, ax_key):
        """绘制异常参数热图"""
        if ax_key not in self.axes_dict or len(samples) < 2:
            return
        
        ax = self.axes_dict[ax_key]
        
        # 收集所有参数
        all_params = set()
        for sample in samples:
            if 'parameters' in sample:
                all_params.update(sample['parameters'].keys())
        
        all_params = sorted(list(all_params))
        
        # 创建异常矩阵
        abnormality_matrix = []
        for sample in samples:
            sample_abnormalities = []
            for param in all_params:
                if 'parameters' in sample and param in sample['parameters']:
                    status = sample['parameters'][param]['status']
                    sample_abnormalities.append(1 if status != 'Normal' else 0)
                else:
                    sample_abnormalities.append(0)
            abnormality_matrix.append(sample_abnormalities)
        
        # 转置矩阵以便热图显示
        abnormality_matrix = np.array(abnormality_matrix).T
        
        im = ax.imshow(abnormality_matrix, cmap='Reds', aspect='auto', 
                      interpolation='nearest')
        
        ax.set_xticks(range(len(samples)))
        ax.set_yticks(range(len(all_params)))
        ax.set_xticklabels([s.get('sample_id', 'S')[:8] for s in samples], 
                          rotation=45, fontsize=8)
        ax.set_yticklabels(all_params, fontsize=8)
        
        ax.set_title('异常参数热图')
        self.fig.colorbar(im, ax=ax, shrink=0.6)
    
    def _plot_disease_patterns(self, samples, ax_key):
        """绘制疾病模式检测"""
        if ax_key not in self.axes_dict:
            return
        
        ax = self.axes_dict[ax_key]
        
        pattern_counts = {}
        for sample in samples:
            patterns = sample.get('pattern_analysis', [])
            for pattern in patterns:
                disease = pattern.get('disease', 'Unknown')
                if disease not in pattern_counts:
                    pattern_counts[disease] = 0
                pattern_counts[disease] += 1
        
        if pattern_counts:
            diseases = list(pattern_counts.keys())
            counts = list(pattern_counts.values())
            
            # 简化疾病名称显示
            display_names = [d.replace('_', ' ').title()[:15] for d in diseases]
            
            y_pos = np.arange(len(display_names))
            bars = ax.barh(y_pos, counts, color='#6A5ACD')
            
            ax.set_yticks(y_pos)
            ax.set_yticklabels(display_names)
            ax.set_xlabel('检测次数')
            ax.set_title('疾病模式检测统计')
            
            # 添加数值标签
            for i, (bar, count) in enumerate(zip(bars, counts)):
                width = bar.get_width()
                ax.text(width + 0.1, bar.get_y() + bar.get_height()/2.,
                       f'{count}', ha='left', va='center')
        
        else:
            ax.text(0.5, 0.5, '无疾病模式检测', ha='center', va='center', 
                   transform=ax.transAxes, fontsize=12)
            ax.set_title('疾病模式检测')

# ============================ 增强版主应用程序 ============================
class EnhancedBloodAnalysisApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.analysis_engine = EnhancedBloodAnalysisEngine()
        self.db_manager = EnhancedBloodDatabaseManager()
        
        # 用户会话管理
        self.current_user = None
        self.user_permissions = []
        
        # 数据管理
        self.current_patient = None
        self.current_samples = []
        self.analysis_results = []
        
        # 设置管理
        self.settings = QSettings("BloodAnalysisLab", "EnhancedBloodAnalyzer")
        
        self.initUI()
        self.setupConnections()
        
        # 尝试自动登录或显示登录窗口
        self.attempt_auto_login()
    
    def initUI(self):
        """初始化增强版UI"""
        self.setWindowTitle("智能血液分析系统 v3.0 - 专业版")
        self.setGeometry(50, 50, 1800, 1000)
        
        # 设置应用程序图标和样式
        self.setWindowIcon(self.create_enhanced_icon())
        self.apply_application_style()
        
        # 创建增强菜单栏
        self.createEnhancedMenuBar()
        
        # 创建增强工具栏
        self.createEnhancedToolBar()
        
        # 创建状态栏
        self.createEnhancedStatusBar()
        
        # 设置中心窗口
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建标签页容器
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)
        self.tab_widget.setMovable(True)
        self.tab_widget.setDocumentMode(True)
        main_layout.addWidget(self.tab_widget)
        
        # 初始化各标签页
        self.setupLoginTab()
        self.setupDashboardTab()
        self.setupPatientManagementTab()
        self.setupDataAnalysisTab()
        self.setupAdvancedVizTab()
        self.setupMLTab()
        self.setupReportingTab()
        self.setupAdminTab()
        
        # 初始显示登录标签页
        self.tab_widget.setCurrentIndex(0)
    
    def create_enhanced_icon(self):
        """创建增强版应用程序图标"""
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制更专业的图标
        gradient = QLinearGradient(0, 0, 64, 64)
        gradient.setColorAt(0, QColor(220, 20, 60))
        gradient.setColorAt(1, QColor(139, 0, 0))
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(QColor(100, 0, 0), 3))
        
        # 绘制血滴形状
        drop_points = [
            QPoint(32, 10), QPoint(45, 25), QPoint(40, 45),
            QPoint(32, 55), QPoint(24, 45), QPoint(19, 25)
        ]
        painter.drawPolygon(QPolygon(drop_points))
        
        # 绘制细胞图案
        painter.setPen(QPen(Qt.white, 2))
        painter.drawEllipse(25, 20, 8, 8)
        painter.drawEllipse(35, 30, 6, 6)
        painter.drawEllipse(22, 35, 5, 5)
        
        painter.end()
        return QIcon(pixmap)
    
    def apply_application_style(self):
        """应用应用程序样式"""
        style = """
        QMainWindow {
            background-color: #f5f5f5;
        }
        QTabWidget::pane {
            border: 1px solid #C2C7CB;
            background-color: white;
        }
        QTabBar::tab {
            background-color: #E1E1E1;
            border: 1px solid #C4C4C3;
            padding: 8px 12px;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background-color: #0078D7;
            color: white;
        }
        QGroupBox {
            font-weight: bold;
            border: 2px solid #CCCCCC;
            border-radius: 5px;
            margin-top: 1ex;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        """
        self.setStyleSheet(style)
    
    def createEnhancedMenuBar(self):
        """创建增强菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        new_project = QAction('新建项目', self)
        new_project.setShortcut('Ctrl+Shift+N')
        file_menu.addAction(new_project)
        
        open_project = QAction('打开项目', self)
        open_project.setShortcut('Ctrl+O')
        file_menu.addAction(open_project)
        
        file_menu.addSeparator()
        
        export_menu = file_menu.addMenu('导出')
        export_pdf = QAction('导出为PDF', self)
        export_excel = QAction('导出为Excel', self)
        export_menu.addAction(export_pdf)
        export_menu.addAction(export_excel)
        
        # 患者菜单
        patient_menu = menubar.addMenu('患者')
        
        new_patient = QAction('新建患者', self)
        patient_menu.addAction(new_patient)
        
        search_patient = QAction('搜索患者', self)
        search_patient.setShortcut('Ctrl+F')
        patient_menu.addAction(search_patient)
        
        # 分析菜单
        analysis_menu = menubar.addMenu('分析')
        
        quick_analysis = QAction('快速分析', self)
        quick_analysis.setShortcut('F5')
        analysis_menu.addAction(quick_analysis)
        
        batch_analysis = QAction('批量分析', self)
        analysis_menu.addAction(batch_analysis)
        
        # 视图菜单
        view_menu = menubar.addMenu('视图')
        
        # 工具菜单
        tools_menu = menubar.addMenu('工具')
        
        ml_trainer = QAction('机器学习训练器', self)
        tools_menu.addAction(ml_trainer)
        
        data_cleaner = QAction('数据清洗工具', self)
        tools_menu.addAction(data_cleaner)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        
        user_manual = QAction('用户手册', self)
        help_menu.addAction(user_manual)
        
        about = QAction('关于', self)
        about.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about)
    
    def createEnhancedToolBar(self):
        """创建增强工具栏"""
        # 主工具栏
        main_toolbar = QToolBar("主工具栏")
        main_toolbar.setIconSize(QSize(32, 32))
        self.addToolBar(Qt.TopToolBarArea, main_toolbar)
        
        # 患者管理工具栏
        patient_toolbar = QToolBar("患者工具栏")
        self.addToolBar(Qt.TopToolBarArea, patient_toolbar)
        
        # 分析工具栏
        analysis_toolbar = QToolBar("分析工具栏")
        self.addToolBar(Qt.TopToolBarArea, analysis_toolbar)
        
        # 添加工具按钮
        self.setup_toolbar_buttons(main_toolbar, patient_toolbar, analysis_toolbar)
    
    def setup_toolbar_buttons(self, main_tb, patient_tb, analysis_tb):
        """设置工具栏按钮"""
        # 主工具栏按钮
        login_btn = QAction(QIcon("icons/login.png"), "登录", self)
        main_tb.addAction(login_btn)
        
        main_tb.addSeparator()
        
        dashboard_btn = QAction(QIcon("icons/dashboard.png"), "仪表盘", self)
        main_tb.addAction(dashboard_btn)
        
        # 患者工具栏按钮
        new_patient_btn = QAction(QIcon("icons/new_patient.png"), "新建患者", self)
        patient_tb.addAction(new_patient_btn)
        
        search_patient_btn = QAction(QIcon("icons/search.png"), "搜索", self)
        patient_tb.addAction(search_patient_btn)
        
        # 分析工具栏按钮
        import_btn = QAction(QIcon("icons/import.png"), "导入数据", self)
        analysis_tb.addAction(import_btn)
        
        analyze_btn = QAction(QIcon("icons/analyze.png"), "分析", self)
        analysis_tb.addAction(analyze_btn)
        
        report_btn = QAction(QIcon("icons/report.png"), "生成报告", self)
        analysis_tb.addAction(report_btn)
    
    def createEnhancedStatusBar(self):
        """创建增强状态栏"""
        status_bar = self.statusBar()
        
        # 用户状态
        self.user_status_label = QLabel("未登录")
        status_bar.addWidget(self.user_status_label)
        
        # 系统状态
        self.system_status_label = QLabel("就绪")
        status_bar.addPermanentWidget(self.system_status_label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        status_bar.addPermanentWidget(self.progress_bar)
    
    def setupLoginTab(self):
        """设置登录标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 登录表单容器
        login_container = QWidget()
        login_layout = QVBoxLayout(login_container)
        
        # 标题
        title_label = QLabel("智能血液分析系统")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 24pt; font-weight: bold; color: #0078D7; margin: 20px;")
        login_layout.addWidget(title_label)
        
        subtitle_label = QLabel("专业血液学分析平台")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("font-size: 12pt; color: #666; margin-bottom: 30px;")
        login_layout.addWidget(subtitle_label)
        
        # 登录表单
        form_group = QGroupBox("用户登录")
        form_layout = QFormLayout(form_group)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("请输入用户名")
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("请输入密码")
        
        self.remember_check = QCheckBox("记住登录状态")
        self.auto_login_check = QCheckBox("自动登录")
        
        login_btn = QPushButton("登录")
        login_btn.setStyleSheet("QPushButton { background-color: #0078D7; color: white; padding: 10px; font-size: 12pt; }")
        
        form_layout.addRow("用户名:", self.username_input)
        form_layout.addRow("密码:", self.password_input)
        form_layout.addRow(self.remember_check)
        form_layout.addRow(self.auto_login_check)
        form_layout.addRow(login_btn)
        
        login_layout.addWidget(form_group)
        login_layout.addStretch()
        
        # 版本信息
        version_label = QLabel(f"版本 3.0.0 | © 2024 血液分析实验室")
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet("color: #999; margin-top: 20px;")
        login_layout.addWidget(version_label)
        
        layout.addWidget(login_container)
        
        self.tab_widget.addTab(tab, "登录")
        
        # 连接信号
        login_btn.clicked.connect(self.attempt_login)
        self.password_input.returnPressed.connect(self.attempt_login)
    
    def setupDashboardTab(self):
        """设置仪表盘标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 仪表盘控件将在这里实现
        dashboard_label = QLabel("综合仪表盘 - 正在开发中")
        dashboard_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(dashboard_label)
        
        self.tab_widget.addTab(tab, "仪表盘")
    
    def setupPatientManagementTab(self):
        """设置患者管理标签页"""
        tab = QWidget()
        layout = QHBoxLayout(tab)
        
        # 患者管理界面将在这里实现
        patient_label = QLabel("患者管理 - 正在开发中")
        patient_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(patient_label)
        
        self.tab_widget.addTab(tab, "患者管理")
    
    # 其他标签页的设置方法类似，由于篇幅限制这里省略详细实现
    def setupDataAnalysisTab(self):
        """设置数据分析标签页"""
        pass
    
    def setupAdvancedVizTab(self):
        """设置高级可视化标签页"""
        pass
    
    def setupMLTab(self):
        """设置机器学习标签页"""
        pass
    
    def setupReportingTab(self):
        """设置报告生成标签页"""
        pass
    
    def setupAdminTab(self):
        """设置管理标签页"""
        pass
    
    def attempt_auto_login(self):
        """尝试自动登录"""
        username = self.settings.value("auto_login/username")
        password = self.settings.value("auto_login/password")
        
        if username and password:
            self.username_input.setText(username)
            self.password_input.setText(password)
            if self.settings.value("auto_login/enabled", False, type=bool):
                self.attempt_login()
    
    def attempt_login(self):
        """尝试登录"""
        username = self.username_input.text()
        password = self.password_input.text()
        
        if not username or not password:
            QMessageBox.warning(self, "登录失败", "请输入用户名和密码")
            return
        
        # 模拟登录验证
        if self.authenticate_user(username, password):
            self.current_user = {
                'username': username,
                'role': 'admin' if username == 'admin' else 'user'
            }
            self.user_permissions = self.get_user_permissions(self.current_user['role'])
            
            # 更新UI状态
            self.user_status_label.setText(f"用户: {username} ({self.current_user['role']})")
            self.system_status_label.setText("登录成功")
            
            # 隐藏登录标签页，显示主界面
            self.tab_widget.removeTab(0)  # 移除登录页
            self.tab_widget.setCurrentIndex(0)  # 切换到仪表盘
            
            # 记住登录状态
            if self.remember_check.isChecked():
                self.settings.setValue("auto_login/username", username)
                self.settings.setValue("auto_login/password", password)
                self.settings.setValue("auto_login/enabled", self.auto_login_check.isChecked())
            
            QMessageBox.information(self, "登录成功", f"欢迎回来，{username}！")
        else:
            QMessageBox.warning(self, "登录失败", "用户名或密码错误")
    
    def authenticate_user(self, username, password):
        """用户认证（简化版）"""
        # 在实际应用中，这里应该连接数据库进行验证
        valid_users = {
            'admin': 'admin123',
            'user': 'user123',
            'doctor': 'doctor123'
        }
        return username in valid_users and valid_users[username] == password
    
    def get_user_permissions(self, role):
        """获取用户权限"""
        permissions = {
            'admin': ['read', 'write', 'delete', 'admin'],
            'doctor': ['read', 'write'],
            'user': ['read']
        }
        return permissions.get(role, ['read'])
    
    def show_about_dialog(self):
        """显示关于对话框"""
        about_text = """
        <h2>智能血液分析系统 v3.0</h2>
        <p><b>专业血液学分析平台</b></p>
        <p>本系统提供全面的血液学数据分析功能，包括：</p>
        <ul>
            <li>智能样本分析</li>
            <li>疾病模式识别</li>
            <li>机器学习预测</li>
            <li>高级数据可视化</li>
            <li>专业报告生成</li>
        </ul>
        <p>© 2024 血液分析实验室 - 保留所有权利</p>
        """
        
        QMessageBox.about(self, "关于", about_text)
    
    def setupConnections(self):
        """设置信号连接"""
        # 将在具体功能实现时添加
        pass

# ============================ 应用程序入口 ============================
def main():
    # 创建应用程序
    app = QApplication(sys.argv)
    
    # 设置应用程序属性
    app.setApplicationName("智能血液分析系统")
    app.setApplicationVersion("3.0.0")
    app.setOrganizationName("血液分析实验室")
    
    # 设置全局样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = EnhancedBloodAnalysisApp()
    window.show()
    
    # 应用程序执行
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()