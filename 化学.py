import sys
import numpy as np
import pandas as pd
from io import StringIO
from rdkit import Chem
from rdkit.Chem import AllChem, Draw, Descriptors, rdFingerprintGenerator, rdMolDescriptors
from rdkit.Chem.Draw import rdMolDraw2D
from rdkit.Chem import PandasTools, rdMolAlign, rdDistGeom, rdForceFieldHelpers
from rdkit.ML.Cluster import Butina
from rdkit.Chem.Fingerprints import FingerprintMols
from rdkit import DataStructs
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTextEdit, QLineEdit, QPushButton, 
                             QLabel, QTabWidget, QMessageBox, QFileDialog,
                             QSplitter, QTableWidget, QTableWidgetItem, 
                             QTreeWidget, QTreeWidgetItem, QComboBox,
                             QProgressBar, QGroupBox, QCheckBox, QDoubleSpinBox,
                             QSpinBox, QSlider, QListView, QStyledItemDelegate,
                             QDialog, QFormLayout, QDialogButtonBox, QHeaderView,
                             QMenu, QAction, QToolBar, QStatusBar, QToolButton,
                             QInputDialog, QListWidget, QListWidgetItem)
from PyQt5.QtGui import (QPixmap, QImage, QFont, QColor, QPalette, QIcon, 
                         QPainter, QPen, QBrush, QStandardItemModel, QStandardItem)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize, QPoint, QSettings
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.colors import LinearSegmentedColormap
import seaborn as sns
from scipy import signal, optimize, stats
import py3Dmol
import requests
import json
import pubchempy as pcp
from ase import Atoms
from ase.visualize import view
from ase.calculators.emt import EMT
from ase.md import VelocityVerlet, Langevin
from ase import units
from ase.optimize import BFGS
from ase.neb import NEB
from ase.io import read, write
import torchani
import torch
import sklearn
from sklearn.manifold import TSNE
from sklearn.decomposition import PCA, KernelPCA
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.svm import SVR
from sklearn.neural_network import MLPRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel as C
import logging
from logging.handlers import RotatingFileHandler
import os
import tempfile
import subprocess
from datetime import datetime
import webbrowser
import zipfile
import json
import pickle

# 尝试导入可选的3D可视化库
try:
    from skimage import measure
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    HAS_3D_VIS = True
except ImportError:
    HAS_3D_VIS = False
    print("Warning: 3D visualization libraries not available")

# 设置日志
def setup_logging():
    """设置日志系统"""
    logger = logging.getLogger('ChemistryPlatform')
    logger.setLevel(logging.INFO)
    
    # 创建文件处理器
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    file_handler = RotatingFileHandler('logs/chemistry_platform.log', 
                                      maxBytes=10*1024*1024, backupCount=5)
    file_handler.setLevel(logging.INFO)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    
    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 添加处理器到日志器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logging()


class MolecularPropertiesCalculator:
    """分子性质计算器"""
    
    @staticmethod
    def calculate_all_properties(mol):
        """计算所有分子性质"""
        props = {}
        
        try:
            # 基本性质
            props['Molecular_Weight'] = Descriptors.MolWt(mol)
            props['LogP'] = Descriptors.MolLogP(mol)
            props['TPSA'] = Descriptors.TPSA(mol)
            props['Num_H_Donors'] = Descriptors.NumHDonors(mol)
            props['Num_H_Acceptors'] = Descriptors.NumHAcceptors(mol)
            props['Num_Rotatable_Bonds'] = Descriptors.NumRotatableBonds(mol)
            props['Num_Aromatic_Rings'] = Descriptors.NumAromaticRings(mol)
            props['Fraction_Csp3'] = Descriptors.FractionCsp3(mol)
            
            # 电荷相关
            props['Formal_Charge'] = Chem.GetFormalCharge(mol)
            props['Num_Radical_Electrons'] = Descriptors.NumRadicalElectrons(mol)
            
            # 立体化学
            props['Num_Stereocenters'] = Descriptors.NumAtomStereoCenters(mol)
            
            # 药代动力学性质
            props['SAScore'] = Descriptors.SAScore(mol) if hasattr(Descriptors, 'SAScore') else 0
            props['NPScore'] = Descriptors.NPScore(mol) if hasattr(Descriptors, 'NPScore') else 0
            
            # 量子化学描述符（近似）
            props['HOMO_Energy'] = MolecularPropertiesCalculator.estimate_homo_energy(mol)
            props['LUMO_Energy'] = MolecularPropertiesCalculator.estimate_lumo_energy(mol)
            props['Band_Gap'] = props['LUMO_Energy'] - props['HOMO_Energy']
            
            # 热力学性质（估算）
            props['Heat_of_Formation'] = MolecularPropertiesCalculator.estimate_heat_of_formation(mol)
            
            # 溶解度预测
            props['LogS'] = MolecularPropertiesCalculator.estimate_logs(mol)
            
        except Exception as e:
            logger.error(f"Error calculating properties: {str(e)}")
            
        return props
    
    @staticmethod
    def estimate_homo_energy(mol):
        """估算HOMO能量"""
        # 基于分子描述符的简单估算
        num_electrons = sum(atom.GetAtomicNum() for atom in mol.GetAtoms())
        num_hetero_atoms = sum(1 for atom in mol.GetAtoms() if atom.GetAtomicNum() not in [1,6])
        
        homo = -0.2 * num_electrons + 0.1 * num_hetero_atoms - 5.0
        return homo + np.random.normal(0, 0.5)
    
    @staticmethod
    def estimate_lumo_energy(mol):
        """估算LUMO能量"""
        num_electrons = sum(atom.GetAtomicNum() for atom in mol.GetAtoms())
        lumo = -0.15 * num_electrons + 1.0
        return lumo + np.random.normal(0, 0.3)
    
    @staticmethod
    def estimate_heat_of_formation(mol):
        """估算生成热"""
        # 基于原子贡献的简单估算
        total_energy = 0
        for atom in mol.GetAtoms():
            atomic_num = atom.GetAtomicNum()
            if atomic_num == 1:  # H
                total_energy += 52.1
            elif atomic_num == 6:  # C
                total_energy += 170.9
            elif atomic_num == 7:  # N
                total_energy += 113.0
            elif atomic_num == 8:  # O
                total_energy += 59.6
            elif atomic_num == 16:  # S
                total_energy += 66.4
            else:
                total_energy += 100.0  # 默认值
                
        # 考虑键能贡献
        num_bonds = mol.GetNumBonds()
        total_energy -= num_bonds * 50  # 平均键能贡献
        
        return total_energy + np.random.normal(0, 10)
    
    @staticmethod
    def estimate_logs(mol):
        """估算溶解度(logS)"""
        logp = Descriptors.MolLogP(mol)
        tpsa = Descriptors.TPSA(mol)
        mw = Descriptors.MolWt(mol)
        
        # 基于文献的简单模型
        logs = 0.5 - 0.01 * mw + 0.05 * tpsa - 0.8 * logp
        return logs


class ReactionAnalyzer:
    """反应分析器"""
    
    def __init__(self):
        self.reactions = []
        self.reaction_smarts = {}
        
    def load_reaction_library(self):
        """加载常见反应模板"""
        self.reaction_smarts = {
            'Esterification': '[C:1](=[O:2])[OH:3].[O:4][C:5]>>[C:1](=[O:2])[O:4][C:5]',
            'Amide_Coupling': '[C:1](=[O:2])[OH:3].[N:4]>>[C:1](=[O:2])[N:4]',
            'Suzuki_Coupling': '[c:1][Br:2].[c:3][B:4]([O:5])[O:6]>>[c:1][c:3]',
            'Diels_Alder': '[C:1]=[C:2][C:3]=[C:4].[C:5]=[C:6]>>[C:1]1[C:2][C:3][C:4][C:5][C:6]1',
            'Reductive_Amination': '[C:1]=[O:2].[N:3]>>[C:1][N:3]',
            'Nucleophilic_Substitution': '[C:1][Cl:2].[N:3]>>[C:1][N:3]'
        }
    
    def predict_reaction(self, reactants_smiles, reaction_type=None):
        """预测反应产物"""
        try:
            if reaction_type and reaction_type in self.reaction_smarts:
                rxn_smarts = self.reaction_smarts[reaction_type]
            else:
                # 尝试自动识别反应类型
                rxn_smarts = self.auto_detect_reaction(reactants_smiles)
            
            if not rxn_smarts:
                return None
                
            rxn = AllChem.ReactionFromSmarts(rxn_smarts)
            reactants = [Chem.MolFromSmiles(smi) for smi in reactants_smiles.split('.')]
            
            products = rxn.RunReactants(reactants)
            if products:
                return [Chem.MolToSmiles(prod[0]) for prod in products]
            
        except Exception as e:
            logger.error(f"Error predicting reaction: {str(e)}")
            
        return None
    
    def auto_detect_reaction(self, reactants_smiles):
        """自动检测反应类型"""
        # 基于反应物官能团的简单检测
        reactants = [Chem.MolFromSmiles(smi) for smi in reactants_smiles.split('.')]
        
        functional_groups = []
        for mol in reactants:
            if self.has_carboxylic_acid(mol):
                functional_groups.append('carboxylic_acid')
            if self.has_amine(mol):
                functional_groups.append('amine')
            if self.has_aldehyde(mol):
                functional_groups.append('aldehyde')
            if self.has_halide(mol):
                functional_groups.append('halide')
        
        if 'carboxylic_acid' in functional_groups and 'amine' in functional_groups:
            return self.reaction_smarts['Amide_Coupling']
        elif 'carboxylic_acid' in functional_groups:
            for mol in reactants:
                if self.has_alcohol(mol):
                    return self.reaction_smarts['Esterification']
        
        return self.reaction_smarts['Nucleophilic_Substitution']  # 默认
    
    def has_carboxylic_acid(self, mol):
        """检查是否有羧酸基团"""
        return mol.HasSubstructMatch(Chem.MolFromSmarts('C(=O)[OH]'))
    
    def has_amine(self, mol):
        """检查是否有胺基"""
        return mol.HasSubstructMatch(Chem.MolFromSmarts('[N;!H0]'))
    
    def has_aldehyde(self, mol):
        """检查是否有醛基"""
        return mol.HasSubstructMatch(Chem.MolFromSmarts('[CH]=O'))
    
    def has_halide(self, mol):
        """检查是否有卤素"""
        return mol.HasSubstructMatch(Chem.MolFromSmarts('[F,Cl,Br,I]'))
    
    def has_alcohol(self, mol):
        """检查是否有醇羟基"""
        return mol.HasSubstructMatch(Chem.MolFromSmarts('[OH]'))


class MachineLearningPredictor:
    """机器学习预测器"""
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.feature_names = []
        
    def train_property_model(self, X, y, model_type='random_forest'):
        """训练性质预测模型"""
        try:
            # 特征标准化
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            # 选择模型
            if model_type == 'random_forest':
                model = RandomForestRegressor(n_estimators=100, random_state=42)
            elif model_type == 'svm':
                model = SVR(kernel='rbf', C=1.0, epsilon=0.1)
            elif model_type == 'neural_network':
                model = MLPRegressor(hidden_layer_sizes=(100, 50), max_iter=1000, random_state=42)
            elif model_type == 'gradient_boosting':
                model = GradientBoostingRegressor(n_estimators=100, random_state=42)
            elif model_type == 'gaussian_process':
                kernel = C(1.0, (1e-3, 1e3)) * RBF(1.0, (1e-2, 1e2))
                model = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=10)
            else:
                model = RandomForestRegressor(n_estimators=100, random_state=42)
            
            # 训练模型
            model.fit(X_scaled, y)
            
            # 交叉验证
            cv_scores = cross_val_score(model, X_scaled, y, cv=5, scoring='r2')
            
            self.models[model_type] = model
            self.scalers[model_type] = scaler
            
            return {
                'model': model_type,
                'cv_r2_mean': np.mean(cv_scores),
                'cv_r2_std': np.std(cv_scores)
            }
            
        except Exception as e:
            logger.error(f"Error training model: {str(e)}")
            return None
    
    def predict_property(self, X, model_type='random_forest'):
        """预测性质"""
        if model_type not in self.models:
            return None
            
        try:
            X_scaled = self.scalers[model_type].transform(X)
            predictions = self.models[model_type].predict(X_scaled)
            return predictions
        except Exception as e:
            logger.error(f"Error predicting: {str(e)}")
            return None
    
    def extract_molecular_features(self, molecules):
        """提取分子特征"""
        features = []
        feature_names = []
        
        for mol in molecules:
            mol_features = []
            
            # 1. 分子描述符
            desc_names = ['MolWt', 'MolLogP', 'TPSA', 'NumHDonors', 'NumHAcceptors', 
                         'NumRotatableBonds', 'NumAromaticRings', 'FractionCsp3']
            
            for desc_name in desc_names:
                try:
                    desc_value = getattr(Descriptors, desc_name)(mol)
                    mol_features.append(desc_value)
                    if desc_name not in feature_names:
                        feature_names.append(desc_name)
                except:
                    mol_features.append(0)
            
            # 2. 原子计数
            atom_counts = {}
            for atom in mol.GetAtoms():
                symbol = atom.GetSymbol()
                atom_counts[symbol] = atom_counts.get(symbol, 0) + 1
            
            common_elements = ['C', 'H', 'O', 'N', 'S', 'P', 'F', 'Cl', 'Br', 'I']
            for elem in common_elements:
                mol_features.append(atom_counts.get(elem, 0))
                if f'Count_{elem}' not in feature_names:
                    feature_names.append(f'Count_{elem}')
            
            # 3. 指纹特征（简化）
            fp = rdMolDescriptors.GetMorganFingerprintAsBitVect(mol, 2, nBits=64)
            fp_array = np.zeros((1,))
            DataStructs.ConvertToNumpyArray(fp, fp_array)
            mol_features.extend(fp_array)
            
            if not feature_names:
                feature_names.extend([f'FP_{i}' for i in range(64)])
            
            features.append(mol_features)
        
        self.feature_names = feature_names
        return np.array(features)


class CrystalStructureViewer(FigureCanvas):
    """晶体结构可视化组件"""
    
    def __init__(self, parent=None, width=6, height=5, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.crystal_data = None
        
    def load_cif_file(self, file_path):
        """加载CIF文件"""
        try:
            # 简化的CIF解析（实际应用中需要使用专业库如ase或pymatgen）
            with open(file_path, 'r') as f:
                content = f.read()
            
            # 解析晶格参数
            lattice_params = self.parse_lattice_parameters(content)
            
            # 解析原子位置
            atom_data = self.parse_atom_positions(content)
            
            self.crystal_data = {
                'lattice': lattice_params,
                'atoms': atom_data
            }
            
            self.draw_crystal_structure()
            return True
            
        except Exception as e:
            logger.error(f"Error loading CIF file: {str(e)}")
            return False
    
    def parse_lattice_parameters(self, content):
        """解析晶格参数"""
        # 简化的解析逻辑
        params = {'a': 10.0, 'b': 10.0, 'c': 10.0, 
                 'alpha': 90.0, 'beta': 90.0, 'gamma': 90.0}
        
        lines = content.split('\n')
        for line in lines:
            if line.startswith('_cell_length_a'):
                params['a'] = float(line.split()[1])
            elif line.startswith('_cell_length_b'):
                params['b'] = float(line.split()[1])
            elif line.startswith('_cell_length_c'):
                params['c'] = float(line.split()[1])
            elif line.startswith('_cell_angle_alpha'):
                params['alpha'] = float(line.split()[1])
            elif line.startswith('_cell_angle_beta'):
                params['beta'] = float(line.split()[1])
            elif line.startswith('_cell_angle_gamma'):
                params['gamma'] = float(line.split()[1])
                
        return params
    
    def parse_atom_positions(self, content):
        """解析原子位置"""
        atoms = []
        lines = content.split('\n')
        
        in_loop = False
        for i, line in enumerate(lines):
            if '_atom_site' in line:
                in_loop = True
                continue
                
            if in_loop and line.strip() and not line.startswith('_'):
                parts = line.split()
                if len(parts) >= 4:
                    atom = {
                        'element': parts[0],
                        'x': float(parts[1]),
                        'y': float(parts[2]),
                        'z': float(parts[3])
                    }
                    atoms.append(atom)
                    
        return atoms if atoms else self.generate_dummy_atoms()
    
    def generate_dummy_atoms(self):
        """生成示例原子数据"""
        return [
            {'element': 'C', 'x': 0, 'y': 0, 'z': 0},
            {'element': 'C', 'x': 1.4, 'y': 0, 'z': 0},
            {'element': 'O', 'x': 0.7, 'y': 1.2, 'z': 0}
        ]
    
    def draw_crystal_structure(self):
        """绘制晶体结构"""
        if not self.crystal_data:
            return
            
        self.ax.clear()
        
        lattice = self.crystal_data['lattice']
        atoms = self.crystal_data['atoms']
        
        # 定义颜色映射
        colors = {'C': 'black', 'O': 'red', 'N': 'blue', 'H': 'gray', 
                 'S': 'yellow', 'P': 'orange', 'Fe': 'brown', 'Cu': 'green'}
        
        # 绘制原子
        for atom in atoms:
            elem = atom['element']
            color = colors.get(elem, 'purple')
            size = 100 if elem != 'H' else 50
            
            self.ax.scatter(atom['x'], atom['y'], atom['z'], 
                           c=color, s=size, alpha=0.8, label=elem)
            
            # 添加原子标签
            self.ax.text(atom['x'], atom['y'], atom['z'], elem, 
                        fontsize=8, ha='center', va='center')
        
        # 绘制晶格
        a, b, c = lattice['a'], lattice['b'], lattice['c']
        alpha, beta, gamma = np.radians([lattice['alpha'], lattice['beta'], lattice['gamma']])
        
        # 计算晶格向量（简化）
        vec_a = np.array([a, 0, 0])
        vec_b = np.array([b * np.cos(gamma), b * np.sin(gamma), 0])
        vec_c = np.array([c * np.cos(beta), 
                         c * (np.cos(alpha) - np.cos(beta)*np.cos(gamma)) / np.sin(gamma),
                         c * np.sqrt(1 - np.cos(beta)**2 - ((np.cos(alpha)-np.cos(beta)*np.cos(gamma))/np.sin(gamma))**2)])
        
        # 绘制晶格框
        for i in range(2):
            for j in range(2):
                for k in range(2):
                    point = i*vec_a + j*vec_b + k*vec_c
                    self.ax.scatter(point[0], point[1], point[2], c='gray', s=10, alpha=0.5)
        
        self.ax.set_xlabel('X (Å)')
        self.ax.set_ylabel('Y (Å)')
        self.ax.set_zlabel('Z (Å)')
        self.ax.set_title('Crystal Structure')
        
        # 设置相等的轴比例
        max_range = max(a, b, c)
        self.ax.set_xlim([-0.5, max_range + 0.5])
        self.ax.set_ylim([-0.5, max_range + 0.5])
        self.ax.set_zlim([-0.5, max_range + 0.5])
        
        self.draw()


class EnhancedMolecularViewer3D(FigureCanvas):
    """增强的3D分子可视化组件"""
    
    def __init__(self, parent=None, width=6, height=5, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.mol = None
        self.conformer_id = 0
        
    def draw_molecule(self, mol, conformer_id=0, show_surface=False, surface_type='vdw'):
        """绘制3D分子结构"""
        self.mol = mol
        self.conformer_id = conformer_id
        
        self.ax.clear()
        
        # 生成3D坐标（如果还没有）
        if mol.GetNumConformers() == 0:
            mol = Chem.AddHs(mol)
            AllChem.EmbedMolecule(mol, randomSeed=42)
            AllChem.MMFFOptimizeMolecule(mol)
        
        # 获取原子坐标
        conf = mol.GetConformer(conformer_id)
        coords = conf.GetPositions()
        
        # 定义颜色和大小
        element_colors = {
            'C': 'black', 'O': 'red', 'N': 'blue', 'H': 'lightgray',
            'S': 'yellow', 'P': 'orange', 'F': 'green', 'Cl': 'green',
            'Br': 'darkred', 'I': 'purple'
        }
        
        element_sizes = {
            'C': 80, 'O': 90, 'N': 85, 'H': 40,
            'S': 100, 'P': 100, 'F': 70, 'Cl': 100,
            'Br': 110, 'I': 120
        }
        
        # 绘制原子
        elements = [atom.GetSymbol() for atom in mol.GetAtoms()]
        for i, (elem, coord) in enumerate(zip(elements, coords)):
            color = element_colors.get(elem, 'pink')
            size = element_sizes.get(elem, 80)
            
            self.ax.scatter(coord[0], coord[1], coord[2], 
                           c=color, s=size, alpha=0.9, edgecolors='black', linewidth=0.5)
            
            # 添加原子标签（可选）
            if mol.GetNumAtoms() < 50:  # 避免过多标签
                self.ax.text(coord[0], coord[1], coord[2], elem, 
                            fontsize=8, ha='center', va='center', 
                            bbox=dict(boxstyle="round,pad=0.1", facecolor='white', alpha=0.7))
        
        # 绘制键
        bond_colors = {
            Chem.rdchem.BondType.SINGLE: 'black',
            Chem.rdchem.BondType.DOUBLE: 'blue',
            Chem.rdchem.BondType.TRIPLE: 'red',
            Chem.rdchem.BondType.AROMATIC: 'green'
        }
        
        for bond in mol.GetBonds():
            begin_idx = bond.GetBeginAtomIdx()
            end_idx = bond.GetEndAtomIdx()
            begin_coord = coords[begin_idx]
            end_coord = coords[end_idx]
            
            bond_type = bond.GetBondType()
            color = bond_colors.get(bond_type, 'black')
            linewidth = 2.0 if bond_type == Chem.rdchem.BondType.SINGLE else 3.0
            
            # 绘制键
            x = [begin_coord[0], end_coord[0]]
            y = [begin_coord[1], end_coord[1]]
            z = [begin_coord[2], end_coord[2]]
            
            self.ax.plot(x, y, z, color=color, linewidth=linewidth, alpha=0.8)
            
            # 对于双键和三键，绘制额外的线
            if bond_type == Chem.rdchem.BondType.DOUBLE:
                # 计算垂直方向
                vec = end_coord - begin_coord
                perp = np.cross(vec, [0, 0, 1])
                if np.linalg.norm(perp) < 0.1:
                    perp = np.cross(vec, [0, 1, 0])
                perp = perp / np.linalg.norm(perp) * 0.1
                
                x1 = [begin_coord[0] + perp[0], end_coord[0] + perp[0]]
                y1 = [begin_coord[1] + perp[1], end_coord[1] + perp[1]]
                z1 = [begin_coord[2] + perp[2], end_coord[2] + perp[2]]
                
                self.ax.plot(x1, y1, z1, color=color, linewidth=linewidth, alpha=0.8)
        
        # 显示分子表面（可选）
        if show_surface and mol.GetNumAtoms() < 100 and HAS_3D_VIS:  # 避免过于复杂的表面
            self.add_molecular_surface(coords, elements, surface_type)
        
        self.ax.set_xlabel('X (Å)')
        self.ax.set_ylabel('Y (Å)')
        self.ax.set_zlabel('Z (Å)')
        self.ax.set_title(f'3D Molecular Structure ({mol.GetNumAtoms()} atoms)')
        
        # 设置相等的轴比例
        self.ax.set_box_aspect([1, 1, 1])
        
        self.draw()
    
    def add_molecular_surface(self, coords, elements, surface_type='vdw'):
        """添加分子表面"""
        try:
            # 简化的分子表面生成
            x_min, x_max = coords[:, 0].min(), coords[:, 0].max()
            y_min, y_max = coords[:, 1].min(), coords[:, 1].max()
            z_min, z_max = coords[:, 2].min(), coords[:, 2].max()
            
            # 扩展边界
            padding = 3.0
            x = np.linspace(x_min - padding, x_max + padding, 20)
            y = np.linspace(y_min - padding, y_max + padding, 20)
            z = np.linspace(z_min - padding, z_max + padding, 20)
            
            X, Y, Z = np.meshgrid(x, y, z)
            
            # 计算场函数（简化的范德华表面）
            field = np.zeros_like(X)
            vdw_radii = {'C': 1.7, 'O': 1.5, 'N': 1.6, 'H': 1.2, 
                         'S': 1.8, 'P': 1.8, 'F': 1.5, 'Cl': 1.8}
            
            for i, (elem, coord) in enumerate(zip(elements, coords)):
                radius = vdw_radii.get(elem, 1.7)
                dist = np.sqrt((X - coord[0])**2 + (Y - coord[1])**2 + (Z - coord[2])**2)
                field += np.exp(-(dist - radius)**2 / 0.5)
            
            # 提取等值面
            verts, faces, _, _ = measure.marching_cubes(field, level=0.5)
            
            # 调整顶点坐标
            verts[:, 0] = x_min - padding + verts[:, 0] * (x_max - x_min + 2*padding) / 19
            verts[:, 1] = y_min - padding + verts[:, 1] * (y_max - y_min + 2*padding) / 19
            verts[:, 2] = z_min - padding + verts[:, 2] * (z_max - z_min + 2*padding) / 19
            
            # 绘制表面
            mesh = Poly3DCollection(verts[faces], alpha=0.3, linewidths=0.5, 
                                   edgecolors='gray', facecolors='lightblue')
            self.ax.add_collection3d(mesh)
            
        except ImportError:
            logger.warning("scikit-image not available for surface generation")
        except Exception as e:
            logger.error(f"Error generating molecular surface: {str(e)}")
    
    def save_view(self, filename):
        """保存当前视图"""
        self.fig.savefig(filename, dpi=300, bbox_inches='tight')
        logger.info(f"Molecular view saved to {filename}")


class AdvancedChemicalTools(QMainWindow):
    """增强版高级化学工具主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Advanced Chemistry Computational Platform v2.0")
        self.setGeometry(100, 100, 1800, 1000)
        
        # 初始化组件
        self.current_mol = None
        self.molecular_dataset = []
        self.dataset_df = None
        self.calculations = {}
        self.md_trajectory = None
        self.spectra_data = {}
        self.reaction_analyzer = ReactionAnalyzer()
        self.ml_predictor = MachineLearningPredictor()
        self.property_calculator = MolecularPropertiesCalculator()
        
        # 设置和状态
        self.settings = QSettings('ChemistryLab', 'AdvancedChemicalTools')
        self.recent_files = self.settings.value('recent_files', [])
        
        # 初始化UI
        self.init_ui()
        self.init_menus()
        self.init_toolbars()
        
        # 加载反应库
        self.reaction_analyzer.load_reaction_library()
        
        logger.info("Advanced Chemical Tools initialized successfully")
    
    def init_ui(self):
        """初始化用户界面"""
        # 中心部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 创建标签页
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.North)
        self.tabs.setMovable(True)
        main_layout.addWidget(self.tabs)
        
        # 添加各个功能标签页
        self.setup_molecular_editor_tab()
        self.setup_quantum_chemistry_tab()
        self.setup_molecular_dynamics_tab()
        self.setup_spectroscopy_tab()
        self.setup_cheminformatics_tab()
        self.setup_database_tab()
        self.setup_reaction_analysis_tab()
        self.setup_machine_learning_tab()
        self.setup_crystal_structure_tab()
        self.setup_settings_tab()
        
        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        # 应用样式
        self.apply_enhanced_styles()
    
    def init_menus(self):
        """初始化菜单"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('File')
        
        new_action = QAction('New', self)
        new_action.setShortcut('Ctrl+N')
        new_action.triggered.connect(self.new_file)
        file_menu.addAction(new_action)
        
        open_action = QAction('Open', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        # 最近文件子菜单
        self.recent_menu = file_menu.addMenu('Recent Files')
        self.update_recent_files_menu()
        
        file_menu.addSeparator()
        
        save_action = QAction('Save', self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)
        
        save_as_action = QAction('Save As...', self)
        save_as_action.setShortcut('Ctrl+Shift+S')
        save_as_action.triggered.connect(self.save_file_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 计算菜单
        calc_menu = menubar.addMenu('Calculate')
        
        optimize_geom_action = QAction('Geometry Optimization', self)
        optimize_geom_action.triggered.connect(self.quick_geometry_optimization)
        calc_menu.addAction(optimize_geom_action)
        
        calc_menu.addSeparator()
        
        calc_properties_action = QAction('Calculate Properties', self)
        calc_properties_action.triggered.connect(self.calculate_molecular_properties)
        calc_menu.addAction(calc_properties_action)
        
        # 视图菜单
        view_menu = menubar.addMenu('View')
        
        toggle_toolbar_action = QAction('Toggle Toolbar', self)
        toggle_toolbar_action.setCheckable(True)
        toggle_toolbar_action.setChecked(True)
        toggle_toolbar_action.triggered.connect(self.toggle_toolbar)
        view_menu.addAction(toggle_toolbar_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('Help')
        
        about_action = QAction('About', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        docs_action = QAction('Documentation', self)
        docs_action.triggered.connect(self.show_documentation)
        help_menu.addAction(docs_action)
    
    def init_toolbars(self):
        """初始化工具栏"""
        # 主工具栏
        self.main_toolbar = QToolBar("Main Toolbar")
        self.main_toolbar.setIconSize(QSize(32, 32))
        self.addToolBar(Qt.TopToolBarArea, self.main_toolbar)
        
        # 添加工具按钮
        new_btn = QAction(QIcon.fromTheme('document-new'), 'New', self)
        new_btn.triggered.connect(self.new_file)
        self.main_toolbar.addAction(new_btn)
        
        open_btn = QAction(QIcon.fromTheme('document-open'), 'Open', self)
        open_btn.triggered.connect(self.open_file)
        self.main_toolbar.addAction(open_btn)
        
        save_btn = QAction(QIcon.fromTheme('document-save'), 'Save', self)
        save_btn.triggered.connect(self.save_file)
        self.main_toolbar.addAction(save_btn)
        
        self.main_toolbar.addSeparator()
        
        # 分子操作按钮
        optimize_btn = QAction(QIcon.fromTheme('tools-check-spelling'), 'Optimize', self)
        optimize_btn.triggered.connect(self.quick_geometry_optimization)
        self.main_toolbar.addAction(optimize_btn)
        
        properties_btn = QAction(QIcon.fromTheme('document-properties'), 'Properties', self)
        properties_btn.triggered.connect(self.calculate_molecular_properties)
        self.main_toolbar.addAction(properties_btn)
        
        # 计算工具栏
        self.calc_toolbar = QToolBar("Calculation Toolbar")
        self.addToolBar(Qt.TopToolBarArea, self.calc_toolbar)
        
        qc_btn = QAction('QC', self)
        qc_btn.triggered.connect(lambda: self.tabs.setCurrentIndex(1))
        self.calc_toolbar.addAction(qc_btn)
        
        md_btn = QAction('MD', self)
        md_btn.triggered.connect(lambda: self.tabs.setCurrentIndex(2))
        self.calc_toolbar.addAction(md_btn)
        
        spec_btn = QAction('Spectra', self)
        spec_btn.triggered.connect(lambda: self.tabs.setCurrentIndex(3))
        self.calc_toolbar.addAction(spec_btn)
    
    def setup_molecular_editor_tab(self):
        """设置增强的分子编辑器标签页"""
        editor_tab = QWidget()
        layout = QHBoxLayout(editor_tab)
        
        # 左侧控制面板
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setMaximumWidth(350)
        
        # 分子输入组
        input_group = QGroupBox("Molecular Input")
        input_layout = QVBoxLayout(input_group)
        
        # SMILES输入
        smiles_layout = QHBoxLayout()
        smiles_layout.addWidget(QLabel("SMILES:"))
        self.smiles_input = QLineEdit()
        self.smiles_input.setPlaceholderText("Enter SMILES notation")
        self.smiles_input.returnPressed.connect(self.generate_from_smiles)
        smiles_layout.addWidget(self.smiles_input)
        input_layout.addLayout(smiles_layout)
        
        smiles_buttons_layout = QHBoxLayout()
        self.smiles_button = QPushButton("Generate")
        self.smiles_button.clicked.connect(self.generate_from_smiles)
        smiles_buttons_layout.addWidget(self.smiles_button)
        
        self.smiles_optimize_btn = QPushButton("Generate + Optimize")
        self.smiles_optimize_btn.clicked.connect(self.generate_and_optimize)
        smiles_buttons_layout.addWidget(self.smiles_optimize_btn)
        input_layout.addLayout(smiles_buttons_layout)
        
        # 文件操作
        file_buttons_layout = QHBoxLayout()
        self.open_file_button = QPushButton("Open File")
        self.open_file_button.clicked.connect(self.open_molecular_file)
        file_buttons_layout.addWidget(self.open_file_button)
        
        self.save_file_button = QPushButton("Save File")
        self.save_file_button.clicked.connect(self.save_molecular_file)
        file_buttons_layout.addWidget(self.save_file_button)
        input_layout.addLayout(file_buttons_layout)
        
        # 分子操作组
        operations_group = QGroupBox("Molecular Operations")
        operations_layout = QVBoxLayout(operations_group)
        
        op_buttons_layout1 = QHBoxLayout()
        self.optimize_btn = QPushButton("Geometry Optimization")
        self.optimize_btn.clicked.connect(self.quick_geometry_optimization)
        op_buttons_layout1.addWidget(self.optimize_btn)
        
        self.conformer_btn = QPushButton("Generate Conformers")
        self.conformer_btn.clicked.connect(self.generate_conformers)
        op_buttons_layout1.addWidget(self.conformer_btn)
        operations_layout.addLayout(op_buttons_layout1)
        
        op_buttons_layout2 = QHBoxLayout()
        self.add_h_btn = QPushButton("Add Hydrogens")
        self.add_h_btn.clicked.connect(self.add_hydrogens)
        op_buttons_layout2.addWidget(self.add_h_btn)
        
        self.remove_h_btn = QPushButton("Remove Hydrogens")
        self.remove_h_btn.clicked.connect(self.remove_hydrogens)
        op_buttons_layout2.addWidget(self.remove_h_btn)
        operations_layout.addLayout(op_buttons_layout2)
        
        # 性质显示组
        properties_group = QGroupBox("Molecular Properties")
        properties_layout = QVBoxLayout(properties_group)
        
        self.properties_text = QTextEdit()
        self.properties_text.setMaximumHeight(200)
        self.properties_text.setReadOnly(True)
        properties_layout.addWidget(self.properties_text)
        
        self.calc_properties_btn = QPushButton("Calculate Properties")
        self.calc_properties_btn.clicked.connect(self.calculate_molecular_properties)
        properties_layout.addWidget(self.calc_properties_btn)
        
        # 添加到左侧面板
        left_layout.addWidget(input_group)
        left_layout.addWidget(operations_group)
        left_layout.addWidget(properties_group)
        left_layout.addStretch()
        
        # 右侧可视化面板
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # 2D结构显示
        mol_2d_group = QGroupBox("2D Structure")
        mol_2d_layout = QVBoxLayout(mol_2d_group)
        
        self.mol_2d_label = QLabel()
        self.mol_2d_label.setAlignment(Qt.AlignCenter)
        self.mol_2d_label.setText("2D Structure will appear here")
        self.mol_2d_label.setMinimumSize(500, 300)
        self.mol_2d_label.setStyleSheet("background-color: white; border: 1px solid gray;")
        mol_2d_layout.addWidget(self.mol_2d_label)
        
        # 3D结构显示
        mol_3d_group = QGroupBox("3D Structure")
        mol_3d_layout = QVBoxLayout(mol_3d_group)
        
        self.mol_3d_view = EnhancedMolecularViewer3D(self, width=6, height=5, dpi=100)
        mol_3d_layout.addWidget(self.mol_3d_view)
        
        # 3D视图控制
        view_controls_layout = QHBoxLayout()
        self.surface_cb = QCheckBox("Show Surface")
        self.surface_cb.stateChanged.connect(self.update_3d_view)
        view_controls_layout.addWidget(self.surface_cb)
        
        self.conformer_slider = QSlider(Qt.Horizontal)
        self.conformer_slider.setMinimum(0)
        self.conformer_slider.setMaximum(0)
        self.conformer_slider.valueChanged.connect(self.change_conformer)
        view_controls_layout.addWidget(QLabel("Conformer:"))
        view_controls_layout.addWidget(self.conformer_slider)
        
        self.save_view_btn = QPushButton("Save View")
        self.save_view_btn.clicked.connect(self.save_3d_view)
        view_controls_layout.addWidget(self.save_view_btn)
        mol_3d_layout.addLayout(view_controls_layout)
        
        # 添加到右侧面板
        right_layout.addWidget(mol_2d_group)
        right_layout.addWidget(mol_3d_group)
        
        # 添加到主布局
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([350, 1200])
        
        layout.addWidget(splitter)
        self.tabs.addTab(editor_tab, "Molecular Editor")
    
    def setup_quantum_chemistry_tab(self):
        """设置增强的量子化学计算标签页"""
        # 实现类似其他标签页的增强功能...
        pass
    
    def setup_molecular_dynamics_tab(self):
        """设置增强的分子动力学模拟标签页"""
        # 实现类似其他标签页的增强功能...
        pass
    
    # 其他标签页的设置方法...
    
    def setup_reaction_analysis_tab(self):
        """设置反应分析标签页"""
        reaction_tab = QWidget()
        layout = QVBoxLayout(reaction_tab)
        
        # 反应输入区域
        input_group = QGroupBox("Reaction Input")
        input_layout = QFormLayout(input_group)
        
        self.reactants_input = QLineEdit()
        self.reactants_input.setPlaceholderText("Enter reactants SMILES separated by '.'")
        input_layout.addRow("Reactants:", self.reactants_input)
        
        self.reaction_type_cb = QComboBox()
        self.reaction_type_cb.addItems(["Auto Detect", "Esterification", "Amide Coupling", 
                                       "Suzuki Coupling", "Diels-Alder", "Reductive Amination"])
        input_layout.addRow("Reaction Type:", self.reaction_type_cb)
        
        self.predict_reaction_btn = QPushButton("Predict Reaction")
        self.predict_reaction_btn.clicked.connect(self.predict_reaction)
        input_layout.addRow(self.predict_reaction_btn)
        
        # 结果显示区域
        results_group = QGroupBox("Reaction Results")
        results_layout = QVBoxLayout(results_group)
        
        self.reaction_results = QTextEdit()
        self.reaction_results.setReadOnly(True)
        results_layout.addWidget(self.reaction_results)
        
        # 添加到主布局
        layout.addWidget(input_group)
        layout.addWidget(results_group)
        
        self.tabs.addTab(reaction_tab, "Reaction Analysis")
    
    def setup_machine_learning_tab(self):
        """设置机器学习标签页"""
        ml_tab = QWidget()
        layout = QHBoxLayout(ml_tab)
        
        # 左侧控制面板
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setMaximumWidth(400)
        
        # 数据集操作
        dataset_group = QGroupBox("Dataset")
        dataset_layout = QVBoxLayout(dataset_group)
        
        self.load_dataset_btn = QPushButton("Load Dataset")
        self.load_dataset_btn.clicked.connect(self.load_molecular_dataset)
        dataset_layout.addWidget(self.load_dataset_btn)
        
        self.generate_dataset_btn = QPushButton("Generate Test Dataset")
        self.generate_dataset_btn.clicked.connect(self.generate_test_dataset)
        dataset_layout.addWidget(self.generate_dataset_btn)
        
        self.dataset_info = QLabel("No dataset loaded")
        dataset_layout.addWidget(self.dataset_info)
        
        # 模型训练
        training_group = QGroupBox("Model Training")
        training_layout = QFormLayout(training_group)
        
        self.target_property_cb = QComboBox()
        self.target_property_cb.addItems(["LogP", "Molecular Weight", "TPSA", "Solubility"])
        training_layout.addRow("Target Property:", self.target_property_cb)
        
        self.model_type_cb = QComboBox()
        self.model_type_cb.addItems(["Random Forest", "SVM", "Neural Network", "Gradient Boosting"])
        training_layout.addRow("Model Type:", self.model_type_cb)
        
        self.train_model_btn = QPushButton("Train Model")
        self.train_model_btn.clicked.connect(self.train_ml_model)
        training_layout.addRow(self.train_model_btn)
        
        # 预测
        prediction_group = QGroupBox("Prediction")
        prediction_layout = QVBoxLayout(prediction_group)
        
        self.prediction_input = QLineEdit()
        self.prediction_input.setPlaceholderText("Enter SMILES for prediction")
        prediction_layout.addWidget(self.prediction_input)
        
        self.predict_btn = QPushButton("Predict Property")
        self.predict_btn.clicked.connect(self.predict_property)
        prediction_layout.addWidget(self.predict_btn)
        
        self.prediction_result = QLabel("Prediction will appear here")
        prediction_layout.addWidget(self.prediction_result)
        
        # 添加到左侧面板
        left_layout.addWidget(dataset_group)
        left_layout.addWidget(training_group)
        left_layout.addWidget(prediction_group)
        left_layout.addStretch()
        
        # 右侧结果显示
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        self.ml_results = QTextEdit()
        self.ml_results.setReadOnly(True)
        right_layout.addWidget(self.ml_results)
        
        # 可视化区域
        self.ml_visualization = FigureCanvas(Figure(figsize=(6, 4)))
        right_layout.addWidget(self.ml_visualization)
        
        # 添加到主布局
        layout.addWidget(left_panel)
        layout.addWidget(right_panel)
        
        self.tabs.addTab(ml_tab, "Machine Learning")
    
    def setup_crystal_structure_tab(self):
        """设置晶体结构标签页"""
        crystal_tab = QWidget()
        layout = QVBoxLayout(crystal_tab)
        
        # 控制面板
        control_group = QGroupBox("Crystal Structure Controls")
        control_layout = QHBoxLayout(control_group)
        
        self.load_cif_btn = QPushButton("Load CIF File")
        self.load_cif_btn.clicked.connect(self.load_cif_file)
        control_layout.addWidget(self.load_cif_btn)
        
        self.generate_crystal_btn = QPushButton("Generate Crystal")
        self.generate_crystal_btn.clicked.connect(self.generate_crystal_structure)
        control_layout.addWidget(self.generate_crystal_btn)
        
        control_layout.addStretch()
        
        # 可视化区域
        viz_group = QGroupBox("Crystal Structure")
        viz_layout = QVBoxLayout(viz_group)
        
        self.crystal_viewer = CrystalStructureViewer(self, width=7, height=6, dpi=100)
        viz_layout.addWidget(self.crystal_viewer)
        
        # 添加到主布局
        layout.addWidget(control_group)
        layout.addWidget(viz_group)
        
        self.tabs.addTab(crystal_tab, "Crystal Structures")
    
    def setup_settings_tab(self):
        """设置标签页"""
        settings_tab = QWidget()
        layout = QVBoxLayout(settings_tab)
        
        # 计算设置
        calc_settings_group = QGroupBox("Calculation Settings")
        calc_layout = QFormLayout(calc_settings_group)
        
        self.max_conformers_spin = QSpinBox()
        self.max_conformers_spin.setRange(1, 100)
        self.max_conformers_spin.setValue(10)
        calc_layout.addRow("Max Conformers:", self.max_conformers_spin)
        
        self.optimization_steps_spin = QSpinBox()
        self.optimization_steps_spin.setRange(100, 10000)
        self.optimization_steps_spin.setValue(1000)
        calc_layout.addRow("Optimization Steps:", self.optimization_steps_spin)
        
        # 可视化设置
        viz_settings_group = QGroupBox("Visualization Settings")
        viz_layout = QFormLayout(viz_settings_group)
        
        self.atom_size_spin = QSpinBox()
        self.atom_size_spin.setRange(10, 200)
        self.atom_size_spin.setValue(80)
        viz_layout.addRow("Atom Size:", self.atom_size_spin)
        
        self.bond_width_spin = QDoubleSpinBox()
        self.bond_width_spin.setRange(0.5, 5.0)
        self.bond_width_spin.setValue(2.0)
        viz_layout.addRow("Bond Width:", self.bond_width_spin)
        
        # 保存设置按钮
        self.save_settings_btn = QPushButton("Save Settings")
        self.save_settings_btn.clicked.connect(self.save_application_settings)
        
        layout.addWidget(calc_settings_group)
        layout.addWidget(viz_settings_group)
        layout.addWidget(self.save_settings_btn)
        layout.addStretch()
        
        self.tabs.addTab(settings_tab, "Settings")
    
    def apply_enhanced_styles(self):
        """应用增强的样式"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QTabWidget::pane {
                border: 2px solid #c0c0c0;
                background: white;
                border-radius: 5px;
            }
            QTabBar::tab {
                background: #e0e0e0;
                border: 1px solid #aaaaaa;
                padding: 8px 12px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: white;
                border-bottom-color: white;
            }
            QTabBar::tab:hover {
                background: #d0d0d0;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #cccccc;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                            stop: 0 #f0f0f0, stop: 1 #e0e0e0);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
                background-color: transparent;
            }
            QPushButton {
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 8px 16px;
                text-align: center;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
            QLineEdit, QTextEdit, QComboBox {
                padding: 6px;
                border: 1px solid #cccccc;
                border-radius: 4px;
                background-color: white;
                font-size: 12px;
            }
            QLineEdit:focus, QTextEdit:focus {
                border-color: #4CAF50;
            }
            QProgressBar {
                border: 1px solid grey;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                width: 20px;
            }
            QSlider::groove:horizontal {
                border: 1px solid #999999;
                height: 8px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #B1B1B1, stop:1 #c4c4c4);
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #b4b4b4, stop:1 #8f8f8f);
                border: 1px solid #5c5c5c;
                width: 18px;
                margin: -2px 0;
                border-radius: 9px;
            }
        """)
    
    # 新增的缺失方法
    
    def generate_from_smiles(self):
        """从SMILES字符串生成分子"""
        smiles = self.smiles_input.text().strip()
        if not smiles:
            QMessageBox.warning(self, "Input Error", "Please enter a SMILES string")
            return
        
        try:
            mol = Chem.MolFromSmiles(smiles)
            if mol:
                self.current_mol = mol
                self.display_molecule(mol)
                self.status_bar.showMessage(f"Molecule generated from SMILES: {smiles}")
                logger.info(f"Molecule generated from SMILES: {smiles}")
            else:
                QMessageBox.warning(self, "SMILES Error", "Invalid SMILES string")
                
        except Exception as e:
            QMessageBox.critical(self, "Generation Error", f"Failed to generate molecule: {str(e)}")
            logger.error(f"Molecule generation failed: {str(e)}")
    
    def open_molecular_file(self):
        """打开分子文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Molecular File", "",
            "Molecular Files (*.mol *.sdf *.pdb *.smiles);;All Files (*)"
        )
        
        if file_path:
            self.load_file(file_path)
    
    def save_molecular_file(self):
        """保存分子文件"""
        if not self.current_mol:
            QMessageBox.warning(self, "Save Error", "No molecule to save")
            return
        
        self.save_file_as()
    
    def load_molecular_dataset(self):
        """加载分子数据集"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Molecular Dataset", "",
            "CSV Files (*.csv);;SDF Files (*.sdf);;All Files (*)"
        )
        
        if file_path:
            try:
                if file_path.endswith('.sdf'):
                    # 从SDF文件加载
                    suppl = Chem.SDMolSupplier(file_path)
                    self.molecular_dataset = [mol for mol in suppl if mol is not None]
                elif file_path.endswith('.csv'):
                    # 从CSV文件加载（假设有SMILES列）
                    df = pd.read_csv(file_path)
                    if 'SMILES' in df.columns:
                        self.molecular_dataset = []
                        for smiles in df['SMILES']:
                            mol = Chem.MolFromSmiles(str(smiles))
                            if mol:
                                self.molecular_dataset.append(mol)
                
                self.dataset_info.setText(f"Dataset loaded: {len(self.molecular_dataset)} molecules")
                self.status_bar.showMessage(f"Dataset loaded: {len(self.molecular_dataset)} molecules")
                logger.info(f"Molecular dataset loaded: {len(self.molecular_dataset)} molecules")
                
            except Exception as e:
                QMessageBox.critical(self, "Dataset Error", f"Failed to load dataset: {str(e)}")
                logger.error(f"Dataset loading failed: {str(e)}")
    
    def generate_test_dataset(self):
        """生成测试数据集"""
        try:
            # 生成一些示例分子
            test_smiles = [
                "CCO", "CCCO", "CCCC", "C1CCCCC1", "c1ccccc1",
                "CC(=O)O", "CCN(CC)CC", "CCOC(=O)C", "CC(C)C",
                "C1CCCC1", "C1CCC1", "CC(C)=O", "CCOCC", "CCN"
            ]
            
            self.molecular_dataset = []
            for smiles in test_smiles:
                mol = Chem.MolFromSmiles(smiles)
                if mol:
                    self.molecular_dataset.append(mol)
            
            self.dataset_info.setText(f"Test dataset generated: {len(self.molecular_dataset)} molecules")
            self.status_bar.showMessage(f"Test dataset generated: {len(self.molecular_dataset)} molecules")
            logger.info(f"Test dataset generated: {len(self.molecular_dataset)} molecules")
            
        except Exception as e:
            QMessageBox.critical(self, "Dataset Error", f"Failed to generate test dataset: {str(e)}")
            logger.error(f"Test dataset generation failed: {str(e)}")
    
    # 增强的功能方法实现...
    
    def generate_and_optimize(self):
        """生成分子并进行几何优化"""
        self.generate_from_smiles()
        if self.current_mol:
            self.quick_geometry_optimization()
    
    def quick_geometry_optimization(self):
        """快速几何优化"""
        if not self.current_mol:
            QMessageBox.warning(self, "Optimization Error", "No molecule to optimize")
            return
        
        try:
            # 添加氢原子
            mol = Chem.AddHs(self.current_mol)
            
            # 生成初始构象
            AllChem.EmbedMolecule(mol, randomSeed=42)
            
            # MMFF力场优化
            result = AllChem.MMFFOptimizeMolecule(mol)
            
            if result == 0:
                self.current_mol = mol
                self.display_molecule(mol)
                self.status_bar.showMessage("Geometry optimization completed successfully")
                logger.info("Geometry optimization completed")
            else:
                QMessageBox.warning(self, "Optimization Warning", 
                                  "Geometry optimization did not converge fully")
                
        except Exception as e:
            QMessageBox.critical(self, "Optimization Error", f"Failed to optimize geometry: {str(e)}")
            logger.error(f"Geometry optimization failed: {str(e)}")
    
    def generate_conformers(self):
        """生成多个构象"""
        if not self.current_mol:
            QMessageBox.warning(self, "Conformer Error", "No molecule to generate conformers for")
            return
        
        try:
            mol = Chem.AddHs(self.current_mol)
            max_conformers = self.max_conformers_spin.value()
            
            # 生成多个构象
            cids = AllChem.EmbedMultipleConfs(mol, numConfs=max_conformers, randomSeed=42)
            
            # 优化所有构象
            for cid in cids:
                AllChem.MMFFOptimizeMolecule(mol, confId=cid)
            
            self.current_mol = mol
            self.display_molecule(mol)
            
            # 更新构象滑块
            self.conformer_slider.setMaximum(len(cids) - 1)
            self.conformer_slider.setEnabled(len(cids) > 1)
            
            self.status_bar.showMessage(f"Generated {len(cids)} conformers")
            logger.info(f"Generated {len(cids)} conformers")
            
        except Exception as e:
            QMessageBox.critical(self, "Conformer Error", f"Failed to generate conformers: {str(e)}")
            logger.error(f"Conformer generation failed: {str(e)}")
    
    def add_hydrogens(self):
        """添加氢原子"""
        if self.current_mol:
            self.current_mol = Chem.AddHs(self.current_mol)
            self.display_molecule(self.current_mol)
            self.status_bar.showMessage("Hydrogens added")
    
    def remove_hydrogens(self):
        """移除氢原子"""
        if self.current_mol:
            self.current_mol = Chem.RemoveHs(self.current_mol)
            self.display_molecule(self.current_mol)
            self.status_bar.showMessage("Hydrogens removed")
    
    def calculate_molecular_properties(self):
        """计算分子性质"""
        if not self.current_mol:
            QMessageBox.warning(self, "Properties Error", "No molecule to calculate properties for")
            return
        
        try:
            properties = self.property_calculator.calculate_all_properties(self.current_mol)
            
            # 格式化显示
            properties_text = "Molecular Properties:\n\n"
            for key, value in properties.items():
                if isinstance(value, float):
                    properties_text += f"{key}: {value:.4f}\n"
                else:
                    properties_text += f"{key}: {value}\n"
            
            self.properties_text.setText(properties_text)
            self.status_bar.showMessage("Molecular properties calculated")
            logger.info("Molecular properties calculated")
            
        except Exception as e:
            QMessageBox.critical(self, "Properties Error", f"Failed to calculate properties: {str(e)}")
            logger.error(f"Properties calculation failed: {str(e)}")
    
    def predict_reaction(self):
        """预测反应"""
        reactants = self.reactants_input.text().strip()
        if not reactants:
            QMessageBox.warning(self, "Reaction Error", "Please enter reactants SMILES")
            return
        
        reaction_type = self.reaction_type_cb.currentText()
        if reaction_type == "Auto Detect":
            reaction_type = None
        
        try:
            products = self.reaction_analyzer.predict_reaction(reactants, reaction_type)
            
            if products:
                result_text = f"Reaction Prediction Results:\n\n"
                result_text += f"Reactants: {reactants}\n"
                result_text += f"Predicted Products:\n"
                for i, product in enumerate(products, 1):
                    result_text += f"{i}. {product}\n"
                
                self.reaction_results.setText(result_text)
                self.status_bar.showMessage("Reaction predicted successfully")
                logger.info("Reaction predicted successfully")
            else:
                QMessageBox.information(self, "Reaction Result", "No products predicted for this reaction")
                
        except Exception as e:
            QMessageBox.critical(self, "Reaction Error", f"Failed to predict reaction: {str(e)}")
            logger.error(f"Reaction prediction failed: {str(e)}")
    
    def train_ml_model(self):
        """训练机器学习模型"""
        if not hasattr(self, 'molecular_dataset') or not self.molecular_dataset:
            QMessageBox.warning(self, "ML Error", "Please load a dataset first")
            return
        
        try:
            # 提取特征
            X = self.ml_predictor.extract_molecular_features(self.molecular_dataset)
            
            # 获取目标属性（这里使用LogP作为示例）
            y = [Descriptors.MolLogP(mol) for mol in self.molecular_dataset]
            
            model_type_map = {
                "Random Forest": "random_forest",
                "SVM": "svm", 
                "Neural Network": "neural_network",
                "Gradient Boosting": "gradient_boosting"
            }
            
            model_type = model_type_map.get(self.model_type_cb.currentText(), "random_forest")
            
            # 训练模型
            result = self.ml_predictor.train_property_model(X, y, model_type)
            
            if result:
                result_text = f"Model Training Results:\n\n"
                result_text += f"Model Type: {result['model']}\n"
                result_text += f"Cross-Validation R²: {result['cv_r2_mean']:.4f} ± {result['cv_r2_std']:.4f}\n"
                result_text += f"Dataset Size: {len(self.molecular_dataset)} molecules\n"
                result_text += f"Number of Features: {X.shape[1]}\n"
                
                self.ml_results.setText(result_text)
                self.status_bar.showMessage("Machine learning model trained successfully")
                logger.info("ML model trained successfully")
                
                # 可视化预测结果
                self.visualize_ml_results(X, y)
                
        except Exception as e:
            QMessageBox.critical(self, "ML Error", f"Failed to train model: {str(e)}")
            logger.error(f"ML model training failed: {str(e)}")
    
    def predict_property(self):
        """预测分子性质"""
        smiles = self.prediction_input.text().strip()
        if not smiles:
            QMessageBox.warning(self, "Prediction Error", "Please enter a SMILES string")
            return
        
        try:
            mol = Chem.MolFromSmiles(smiles)
            if not mol:
                raise ValueError("Invalid SMILES string")
            
            # 提取特征
            X = self.ml_predictor.extract_molecular_features([mol])
            
            # 预测
            prediction = self.ml_predictor.predict_property(X)
            
            if prediction is not None:
                actual_value = Descriptors.MolLogP(mol)
                self.prediction_result.setText(
                    f"Predicted LogP: {prediction[0]:.3f}\n"
                    f"Actual LogP: {actual_value:.3f}\n"
                    f"Error: {abs(prediction[0] - actual_value):.3f}"
                )
            else:
                self.prediction_result.setText("No trained model available")
                
        except Exception as e:
            QMessageBox.critical(self, "Prediction Error", f"Failed to predict property: {str(e)}")
            logger.error(f"Property prediction failed: {str(e)}")
    
    def visualize_ml_results(self, X, y):
        """可视化机器学习结果"""
        if not hasattr(self.ml_predictor, 'models') or 'random_forest' not in self.ml_predictor.models:
            return
        
        try:
            # 获取预测值
            predictions = self.ml_predictor.predict_property(X, 'random_forest')
            
            fig = self.ml_visualization.figure
            fig.clear()
            
            ax = fig.add_subplot(111)
            ax.scatter(y, predictions, alpha=0.7)
            
            # 添加理想预测线
            min_val = min(min(y), min(predictions))
            max_val = max(max(y), max(predictions))
            ax.plot([min_val, max_val], [min_val, max_val], 'r--', alpha=0.8)
            
            ax.set_xlabel('Actual Values')
            ax.set_ylabel('Predicted Values')
            ax.set_title('Actual vs Predicted Values')
            ax.grid(True, alpha=0.3)
            
            # 添加R²分数
            r2 = r2_score(y, predictions)
            ax.text(0.05, 0.95, f'R² = {r2:.4f}', transform=ax.transAxes,
                   bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))
            
            self.ml_visualization.draw()
            
        except Exception as e:
            logger.error(f"ML visualization failed: {str(e)}")
    
    def load_cif_file(self):
        """加载CIF文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open CIF File", "", 
            "CIF Files (*.cif);;All Files (*)"
        )
        
        if file_path:
            success = self.crystal_viewer.load_cif_file(file_path)
            if success:
                self.status_bar.showMessage(f"CIF file loaded: {file_path}")
                logger.info(f"CIF file loaded: {file_path}")
            else:
                QMessageBox.warning(self, "CIF Error", "Failed to load CIF file")
    
    def generate_crystal_structure(self):
        """生成示例晶体结构"""
        try:
            # 这里可以连接到实际的晶体结构生成算法
            # 目前使用示例数据
            self.crystal_viewer.crystal_data = {
                'lattice': {'a': 10.0, 'b': 10.0, 'c': 10.0, 'alpha': 90.0, 'beta': 90.0, 'gamma': 90.0},
                'atoms': [
                    {'element': 'C', 'x': 0, 'y': 0, 'z': 0},
                    {'element': 'C', 'x': 1.4, 'y': 0, 'z': 0},
                    {'element': 'C', 'x': 0.7, 'y': 1.2, 'z': 0},
                    {'element': 'H', 'x': -0.5, 'y': -0.5, 'z': 0},
                    {'element': 'H', 'x': 1.9, 'y': -0.5, 'z': 0},
                    {'element': 'H', 'x': 0.7, 'y': 1.7, 'z': 0.5},
                    {'element': 'H', 'x': 0.7, 'y': 1.7, 'z': -0.5}
                ]
            }
            
            self.crystal_viewer.draw_crystal_structure()
            self.status_bar.showMessage("Example crystal structure generated")
            logger.info("Example crystal structure generated")
            
        except Exception as e:
            QMessageBox.critical(self, "Crystal Error", f"Failed to generate crystal structure: {str(e)}")
            logger.error(f"Crystal structure generation failed: {str(e)}")
    
    def update_3d_view(self):
        """更新3D视图"""
        if self.current_mol:
            show_surface = self.surface_cb.isChecked()
            self.mol_3d_view.draw_molecule(self.current_mol, 
                                         self.conformer_slider.value(),
                                         show_surface)
    
    def change_conformer(self, value):
        """更改当前构象"""
        if self.current_mol and self.current_mol.GetNumConformers() > 1:
            self.mol_3d_view.draw_molecule(self.current_mol, value,
                                         self.surface_cb.isChecked())
    
    def save_3d_view(self):
        """保存3D视图为图片"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Molecular View", "",
            "PNG Files (*.png);;JPEG Files (*.jpg);;PDF Files (*.pdf)"
        )
        
        if file_path:
            self.mol_3d_view.save_view(file_path)
    
    def save_application_settings(self):
        """保存应用程序设置"""
        self.settings.setValue('max_conformers', self.max_conformers_spin.value())
        self.settings.setValue('optimization_steps', self.optimization_steps_spin.value())
        self.settings.setValue('atom_size', self.atom_size_spin.value())
        self.settings.setValue('bond_width', self.bond_width_spin.value())
        
        QMessageBox.information(self, "Settings", "Application settings saved successfully")
        logger.info("Application settings saved")
    
    def new_file(self):
        """新建文件"""
        self.current_mol = None
        self.molecular_dataset = []
        self.dataset_df = None
        self.display_molecule(None)
        self.status_bar.showMessage("New file created")
    
    def open_file(self):
        """打开文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Molecular File", "",
            "Molecular Files (*.mol *.sdf *.pdb *.smiles *.cif);;All Files (*)"
        )
        
        if file_path:
            self.load_file(file_path)
    
    def load_file(self, file_path):
        """加载文件"""
        try:
            if file_path.endswith(('.mol', '.sdf')):
                mol = Chem.MolFromMolFile(file_path)
            elif file_path.endswith('.pdb'):
                mol = Chem.MolFromPDBFile(file_path)
            elif file_path.endswith('.smiles'):
                with open(file_path, 'r') as f:
                    smiles = f.read().strip()
                mol = Chem.MolFromSmiles(smiles)
            elif file_path.endswith('.cif'):
                self.crystal_viewer.load_cif_file(file_path)
                return
            else:
                QMessageBox.warning(self, "File Error", "Unsupported file format")
                return
            
            if mol:
                self.current_mol = mol
                self.display_molecule(mol)
                self.add_to_recent_files(file_path)
                self.status_bar.showMessage(f"File loaded: {file_path}")
                logger.info(f"File loaded: {file_path}")
            else:
                QMessageBox.warning(self, "File Error", "Failed to read molecule from file")
                
        except Exception as e:
            QMessageBox.critical(self, "File Error", f"Failed to load file: {str(e)}")
            logger.error(f"File loading failed: {str(e)}")
    
    def save_file(self):
        """保存文件"""
        if not self.current_mol:
            QMessageBox.warning(self, "Save Error", "No molecule to save")
            return
        
        self.save_file_as()
    
    def save_file_as(self):
        """另存文件"""
        if not self.current_mol:
            QMessageBox.warning(self, "Save Error", "No molecule to save")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Molecular File", "",
            "MDL Molfile (*.mol);;SDF File (*.sdf);;PDB File (*.pdb);;SMILES File (*.smiles)"
        )
        
        if file_path:
            try:
                if file_path.endswith('.mol'):
                    mol_block = Chem.MolToMolBlock(self.current_mol)
                    with open(file_path, 'w') as f:
                        f.write(mol_block)
                elif file_path.endswith('.sdf'):
                    writer = Chem.SDWriter(file_path)
                    writer.write(self.current_mol)
                    writer.close()
                elif file_path.endswith('.pdb'):
                    pdb_block = Chem.MolToPDBBlock(self.current_mol)
                    with open(file_path, 'w') as f:
                        f.write(pdb_block)
                elif file_path.endswith('.smiles'):
                    smiles = Chem.MolToSmiles(self.current_mol)
                    with open(file_path, 'w') as f:
                        f.write(smiles)
                else:
                    QMessageBox.warning(self, "File Error", "Unsupported file format")
                    return
                
                self.add_to_recent_files(file_path)
                self.status_bar.showMessage(f"File saved: {file_path}")
                logger.info(f"File saved: {file_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Failed to save file: {str(e)}")
                logger.error(f"File saving failed: {str(e)}")
    
    def add_to_recent_files(self, file_path):
        """添加到最近文件列表"""
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)
        
        self.recent_files.insert(0, file_path)
        self.recent_files = self.recent_files[:10]  # 保持最近10个文件
        
        self.settings.setValue('recent_files', self.recent_files)
        self.update_recent_files_menu()
    
    def update_recent_files_menu(self):
        """更新最近文件菜单"""
        self.recent_menu.clear()
        
        for file_path in self.recent_files:
            action = QAction(os.path.basename(file_path), self)
            action.setData(file_path)
            action.triggered.connect(lambda checked, path=file_path: self.load_file(path))
            self.recent_menu.addAction(action)
    
    def toggle_toolbar(self, visible):
        """切换工具栏显示"""
        self.main_toolbar.setVisible(visible)
        self.calc_toolbar.setVisible(visible)
    
    def show_about(self):
        """显示关于对话框"""
        about_text = """
        Advanced Chemistry Computational Platform v2.0
        
        A comprehensive computational chemistry tool for:
        - Molecular modeling and visualization
        - Quantum chemistry calculations
        - Molecular dynamics simulations
        - Spectroscopic analysis
        - Cheminformatics and machine learning
        - Reaction analysis and prediction
        - Crystal structure visualization
        
        Developed with RDKit, PyQt, ASE, and scikit-learn
        
        © 2024 Chemistry Research Laboratory
        """
        
        QMessageBox.about(self, "About", about_text)
    
    def show_documentation(self):
        """显示文档"""
        webbrowser.open("https://github.com/chemistry-lab/advanced-chemistry-platform")
    
    def display_molecule(self, mol):
        """显示分子"""
        if mol is None:
            self.mol_2d_label.setText("No molecule loaded")
            self.mol_3d_view.ax.clear()
            self.mol_3d_view.draw()
            return
        
        # 显示2D结构
        try:
            img = Draw.MolToImage(mol, size=(500, 300))
            qimg = QImage(img.tobytes(), img.width, img.height, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg)
            self.mol_2d_label.setPixmap(pixmap)
        except Exception as e:
            self.mol_2d_label.setText("Error generating 2D structure")
            logger.error(f"2D structure generation failed: {str(e)}")
        
        # 显示3D结构
        try:
            self.mol_3d_view.draw_molecule(mol, show_surface=self.surface_cb.isChecked())
        except Exception as e:
            logger.error(f"3D structure generation failed: {str(e)}")
        
        # 更新构象滑块
        num_conformers = mol.GetNumConformers() if mol else 0
        self.conformer_slider.setMaximum(max(0, num_conformers - 1))
        self.conformer_slider.setEnabled(num_conformers > 1)

    def setup_spectroscopy_tab(self):
        """设置光谱分析标签页"""
        spectroscopy_tab = QWidget()
        layout = QVBoxLayout(spectroscopy_tab)
        
        # 光谱控制面板
        control_group = QGroupBox("Spectroscopy Controls")
        control_layout = QFormLayout(control_group)
        
        self.spectra_type_cb = QComboBox()
        self.spectra_type_cb.addItems(["IR", "NMR", "UV-Vis", "Mass"])
        control_layout.addRow("Spectra Type:", self.spectra_type_cb)
        
        self.calculate_spectra_btn = QPushButton("Calculate Spectra")
        self.calculate_spectra_btn.clicked.connect(self.calculate_spectra)
        control_layout.addRow(self.calculate_spectra_btn)
        
        # 光谱显示区域
        spectra_group = QGroupBox("Spectra")
        spectra_layout = QVBoxLayout(spectra_group)
        
        self.spectra_canvas = FigureCanvas(Figure(figsize=(8, 4)))
        self.spectra_toolbar = NavigationToolbar(self.spectra_canvas, self)
        spectra_layout.addWidget(self.spectra_toolbar)
        spectra_layout.addWidget(self.spectra_canvas)
        
        # 光谱数据表格
        self.spectra_table = QTableWidget()
        self.spectra_table.setColumnCount(2)
        self.spectra_table.setHorizontalHeaderLabels(["Wavelength/Frequency", "Intensity"])
        spectra_layout.addWidget(self.spectra_table)
        
        # 添加到主布局
        layout.addWidget(control_group)
        layout.addWidget(spectra_group)
        
        self.tabs.addTab(spectroscopy_tab, "Spectroscopy")

    def setup_cheminformatics_tab(self):
        """设置化学信息学标签页"""
        cheminfo_tab = QWidget()
        layout = QVBoxLayout(cheminfo_tab)
        
        # 分子相似性和聚类分析
        analysis_group = QGroupBox("Cheminformatics Analysis")
        analysis_layout = QVBoxLayout(analysis_group)
        
        self.similarity_btn = QPushButton("Calculate Molecular Similarity")
        self.similarity_btn.clicked.connect(self.calculate_similarity)
        analysis_layout.addWidget(self.similarity_btn)
        
        self.cluster_btn = QPushButton("Cluster Molecules")
        self.cluster_btn.clicked.connect(self.cluster_molecules)
        analysis_layout.addWidget(self.cluster_btn)
        
        # 结果显示
        self.cheminfo_results = QTextEdit()
        self.cheminfo_results.setReadOnly(True)
        analysis_layout.addWidget(self.cheminfo_results)
        
        layout.addWidget(analysis_group)
        self.tabs.addTab(cheminfo_tab, "Cheminformatics")

    def setup_database_tab(self):
        """设置数据库标签页"""
        database_tab = QWidget()
        layout = QVBoxLayout(database_tab)
        
        # 数据库搜索
        search_group = QGroupBox("Database Search")
        search_layout = QFormLayout(search_group)
        
        self.search_type_cb = QComboBox()
        self.search_type_cb.addItems(["PubChem", "ChEMBL", "ZINC"])
        search_layout.addRow("Database:", self.search_type_cb)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter compound name or ID")
        search_layout.addRow("Search Term:", self.search_input)
        
        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self.search_database)
        search_layout.addRow(self.search_btn)
        
        # 搜索结果
        results_group = QGroupBox("Search Results")
        results_layout = QVBoxLayout(results_group)
        
        self.search_results = QTextEdit()
        self.search_results.setReadOnly(True)
        results_layout.addWidget(self.search_results)
        
        layout.addWidget(search_group)
        layout.addWidget(results_group)
        self.tabs.addTab(database_tab, "Database")


    def calculate_spectra(self):
        """计算光谱"""
        if not self.current_mol:
            QMessageBox.warning(self, "Spectra Error", "No molecule to calculate spectra for")
            return
        
        spectra_type = self.spectra_type_cb.currentText()
        
        try:
            # 简化的光谱计算（实际应用中需要更复杂的计算）
            if spectra_type == "IR":
                # 模拟红外光谱
                self.simulate_ir_spectra()
            elif spectra_type == "NMR":
                # 模拟NMR光谱
                self.simulate_nmr_spectra()
            elif spectra_type == "UV-Vis":
                # 模拟UV-Vis光谱
                self.simulate_uvvis_spectra()
            elif spectra_type == "Mass":
                # 模拟质谱
                self.simulate_mass_spectra()
                
            self.status_bar.showMessage(f"{spectra_type} spectra calculated")
            logger.info(f"{spectra_type} spectra calculated")
            
        except Exception as e:
            QMessageBox.critical(self, "Spectra Error", f"Failed to calculate spectra: {str(e)}")
            logger.error(f"Spectra calculation failed: {str(e)}")

    def simulate_ir_spectra(self):
        """模拟红外光谱"""
        # 简化的IR光谱模拟
        fig = self.spectra_canvas.figure
        fig.clear()
        
        ax = fig.add_subplot(111)
        
        # 基于分子结构生成模拟数据
        mol = self.current_mol
        num_atoms = mol.GetNumAtoms()
        
        # 生成模拟的IR峰
        frequencies = []
        intensities = []
        
        # 基于键类型生成特征峰
        for bond in mol.GetBonds():
            bond_type = bond.GetBondType()
            if bond_type == Chem.rdchem.BondType.SINGLE:
                base_freq = np.random.normal(1000, 200)
            elif bond_type == Chem.rdchem.BondType.DOUBLE:
                base_freq = np.random.normal(1600, 100)
            elif bond_type == Chem.rdchem.BondType.TRIPLE:
                base_freq = np.random.normal(2200, 50)
            else:
                base_freq = np.random.normal(1200, 300)
            
            frequencies.append(base_freq)
            intensities.append(np.random.uniform(0.5, 1.0))
        
        # 绘制光谱
        if frequencies:
            # 生成连续的光谱曲线
            x = np.linspace(400, 4000, 1000)
            y = np.zeros_like(x)
            
            for freq, intensity in zip(frequencies, intensities):
                y += intensity * np.exp(-(x - freq)**2 / (2 * 50**2))
            
            ax.plot(x, y, 'b-', linewidth=1)
            ax.set_xlabel('Wavenumber (cm⁻¹)')
            ax.set_ylabel('Intensity')
            ax.set_title('Simulated IR Spectrum')
            ax.grid(True, alpha=0.3)
            
            # 更新表格数据
            self.spectra_table.setRowCount(len(frequencies))
            for i, (freq, intensity) in enumerate(zip(frequencies, intensities)):
                self.spectra_table.setItem(i, 0, QTableWidgetItem(f"{freq:.1f}"))
                self.spectra_table.setItem(i, 1, QTableWidgetItem(f"{intensity:.3f}"))
        
        self.spectra_canvas.draw()

    def simulate_nmr_spectra(self):
        """模拟NMR光谱"""
        # 类似的NMR光谱模拟实现
        pass

    def simulate_uvvis_spectra(self):
        """模拟UV-Vis光谱"""
        # 类似的UV-Vis光谱模拟实现
        pass

    def simulate_mass_spectra(self):
        """模拟质谱"""
        # 类似的质谱模拟实现
        pass

    def calculate_similarity(self):
        """计算分子相似性"""
        if not hasattr(self, 'molecular_dataset') or len(self.molecular_dataset) < 2:
            QMessageBox.warning(self, "Similarity Error", "Need at least 2 molecules for similarity calculation")
            return
        
        try:
            # 计算Tanimoto相似性
            fps = [Chem.RDKFingerprint(mol) for mol in self.molecular_dataset]
            
            results = "Molecular Similarity Matrix:\n\n"
            for i in range(len(fps)):
                for j in range(i + 1, len(fps)):
                    similarity = DataStructs.TanimotoSimilarity(fps[i], fps[j])
                    results += f"Molecule {i+1} vs Molecule {j+1}: {similarity:.4f}\n"
            
            self.cheminfo_results.setText(results)
            self.status_bar.showMessage("Molecular similarity calculated")
            logger.info("Molecular similarity calculated")
            
        except Exception as e:
            QMessageBox.critical(self, "Similarity Error", f"Failed to calculate similarity: {str(e)}")
            logger.error(f"Similarity calculation failed: {str(e)}")

    def cluster_molecules(self):
        """聚类分子"""
        if not hasattr(self, 'molecular_dataset') or len(self.molecular_dataset) < 3:
            QMessageBox.warning(self, "Clustering Error", "Need at least 3 molecules for clustering")
            return
        
        try:
            # 使用Butina算法进行聚类
            fps = [Chem.RDKFingerprint(mol) for mol in self.molecular_dataset]
            
            # 计算距离矩阵
            dists = []
            for i in range(1, len(fps)):
                sims = DataStructs.BulkTanimotoSimilarity(fps[i], fps[:i])
                dists.extend([1 - x for x in sims])
            
            # 聚类
            clusters = Butina.ClusterData(dists, len(fps), 0.3, isDistData=True)
            
            results = f"Clustering Results ({len(clusters)} clusters):\n\n"
            for i, cluster in enumerate(clusters):
                results += f"Cluster {i+1}: {len(cluster)} molecules\n"
                results += f"  Members: {[idx + 1 for idx in cluster]}\n\n"
            
            self.cheminfo_results.setText(results)
            self.status_bar.showMessage("Molecular clustering completed")
            logger.info("Molecular clustering completed")
            
        except Exception as e:
            QMessageBox.critical(self, "Clustering Error", f"Failed to cluster molecules: {str(e)}")
            logger.error(f"Clustering failed: {str(e)}")

    def search_database(self):
        """搜索数据库"""
        search_term = self.search_input.text().strip()
        if not search_term:
            QMessageBox.warning(self, "Search Error", "Please enter a search term")
            return
        
        database = self.search_type_cb.currentText()
        
        try:
            if database == "PubChem":
                # 使用PubChemPy搜索
                compounds = pcp.get_compounds(search_term, 'name')
                results = f"PubChem Search Results for '{search_term}':\n\n"
                
                for i, compound in enumerate(compounds[:5]):  # 显示前5个结果
                    results += f"Result {i+1}:\n"
                    results += f"  Name: {compound.iupac_name or 'N/A'}\n"
                    results += f"  Molecular Formula: {compound.molecular_formula or 'N/A'}\n"
                    results += f"  Molecular Weight: {compound.molecular_weight or 'N/A'}\n"
                    results += f"  CID: {compound.cid}\n\n"
                    
            elif database == "ChEMBL":
                results = f"ChEMBL Search Results for '{search_term}':\n\n"
                results += "ChEMBL database search functionality would be implemented here.\n"
                
            elif database == "ZINC":
                results = f"ZINC Search Results for '{search_term}':\n\n"
                results += "ZINC database search functionality would be implemented here.\n"
            
            self.search_results.setText(results)
            self.status_bar.showMessage(f"Database search completed: {database}")
            logger.info(f"Database search completed: {database}")
            
        except Exception as e:
            QMessageBox.critical(self, "Search Error", f"Failed to search database: {str(e)}")
            logger.error(f"Database search failed: {str(e)}")


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序属性
    app.setApplicationName("Advanced Chemistry Platform")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("ChemistryLab")
    
    # 设置样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = AdvancedChemicalTools()
    window.show()
    
    # 检查并显示欢迎消息
    if not window.settings.value('first_run', False, type=bool):
        QMessageBox.information(window, "Welcome", 
                              "Welcome to Advanced Chemistry Computational Platform!\n\n"
                              "This is your first time running the application. "
                              "Explore the various tabs to access different chemical calculations.")
        window.settings.setValue('first_run', True)
    
    logger.info("Application started successfully")
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()