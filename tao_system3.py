"""
《道德经》智能编程系统 - 企业级应用完整实现
Tao Programming System - Enterprise Level Implementation
应用场景：智能合约开发 + AI代码审查 + 项目管理
"""
import os
import sys
import math
import random
import numpy as np
import json
import hashlib
import datetime
from typing import List, Dict, Any, Callable, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import time
from functools import wraps
import re
import ast
import threading
from concurrent.futures import ThreadPoolExecutor
from PyQt5.QtWidgets import QInputDialog
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QTabWidget, QTextEdit, QPushButton, QLabel, QLineEdit, 
                            QComboBox, QSlider, QSpinBox, QDoubleSpinBox, QCheckBox,
                            QGroupBox, QSplitter, QProgressBar, QTableWidget, 
                            QTableWidgetItem, QHeaderView, QMessageBox, QFileDialog,
                            QGraphicsView, QGraphicsScene, QGraphicsItem, QGraphicsEllipseItem,
                            QMenu, QAction, QStatusBar, QToolBar, QDockWidget, QTreeWidget,
                            QTreeWidgetItem, QListWidget, QListWidgetItem, QDialog,
                            QFormLayout, QDialogButtonBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPointF, QRectF, QSize, QDateTime
from PyQt5.QtGui import QFont, QColor, QPen, QBrush, QPainter, QPalette, QKeySequence, QIcon
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QValueAxis

# ==================== 企业级核心组件 ====================


            
class ProjectType(Enum):
    """项目类型枚举"""
    SMART_CONTRACT = "智能合约"
    WEB_APPLICATION = "Web应用"
    MACHINE_LEARNING = "机器学习"
    DATA_ANALYSIS = "数据分析"
    BLOCKCHAIN = "区块链"
    DEFI = "去中心化金融"

class CodeQuality(Enum):
    """代码质量等级"""
    EXCELLENT = "优秀"
    GOOD = "良好" 
    FAIR = "一般"
    POOR = "较差"
    CRITICAL = "危险"

@dataclass
class Project:
    """项目数据结构"""
    project_id: str
    name: str
    project_type: ProjectType
    description: str
    created_date: str
    last_modified: str
    status: str = "进行中"
    progress: float = 0.0
    tao_balance: float = 0.5
    code_quality: CodeQuality = CodeQuality.FAIR
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class CodeReview:
    """代码审查结果"""
    review_id: str
    project_id: str
    reviewer: str
    review_date: str
    score: float
    issues: List[str]
    suggestions: List[str]
    tao_insight: str

class SmartContractGenerator:
    """智能合约生成器"""
    
    def __init__(self):
        self.contract_templates = {
            "ERC20": self._erc20_template(),
            "ERC721": self._erc721_template(),
            "DAO": self._dao_template(),
            "Staking": self._staking_template(),
            "Governance": self._governance_template()
        }
    
    def generate_contract(self, contract_type: str, project: Project, tao_balance: float) -> str:
        """生成智能合约"""
        template = self.contract_templates.get(contract_type, self.contract_templates["ERC20"])
        
        # 根据道德经平衡调整合约特性
        if tao_balance > 0.7:
            security_level = "高"
            gas_optimized = True
            principle = "无为而治"
        elif tao_balance > 0.4:
            security_level = "中"
            gas_optimized = True
            principle = "阴阳平衡"
        else:
            security_level = "标准"
            gas_optimized = False
            principle = "道法自然"
        
        contract_code = template.format(
            project_name=project.name,
            security_level=security_level,
            gas_optimized=str(gas_optimized).lower(),
            principle=principle,
            creation_date=datetime.datetime.now().strftime("%Y-%m-%d"),
            tao_balance=tao_balance
        )
        
        return self._add_tao_comments(contract_code, principle, tao_balance)
    
    def _erc20_template(self) -> str:
        return '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title {project_name} Token
 * @dev 基于道德经原则的ERC20代币合约
 * 安全级别: {security_level}
 * Gas优化: {gas_optimized}
 * 设计原则: {principle}
 * 创建时间: {creation_date}
 * 道平衡度: {tao_balance}
 */

contract {project_name}Token {{
    string public name = "{project_name} Token";
    string public symbol = "TAO";
    uint8 public decimals = 18;
    uint256 public totalSupply;
    
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    
    address public owner;
    bool public paused = false;
    
    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
    event Paused(address account);
    event Unpaused(address account);
    
    modifier onlyOwner() {{
        require(msg.sender == owner, "Only owner can call this");
        _;
    }}
    
    modifier whenNotPaused() {{
        require(!paused, "Contract is paused");
        _;
    }}
    
    constructor(uint256 _totalSupply) {{
        owner = msg.sender;
        totalSupply = _totalSupply * 10 ** uint256(decimals);
        balanceOf[msg.sender] = totalSupply;
        emit Transfer(address(0), msg.sender, totalSupply);
    }}
    
    function transfer(address to, uint256 value) external whenNotPaused returns (bool) {{
        require(balanceOf[msg.sender] >= value, "Insufficient balance");
        
        balanceOf[msg.sender] -= value;
        balanceOf[to] += value;
        
        emit Transfer(msg.sender, to, value);
        return true;
    }}
    
    function approve(address spender, uint256 value) external whenNotPaused returns (bool) {{
        allowance[msg.sender][spender] = value;
        emit Approval(msg.sender, spender, value);
        return true;
    }}
    
    function transferFrom(address from, address to, uint256 value) external whenNotPaused returns (bool) {{
        require(balanceOf[from] >= value, "Insufficient balance");
        require(allowance[from][msg.sender] >= value, "Allowance exceeded");
        
        balanceOf[from] -= value;
        balanceOf[to] += value;
        allowance[from][msg.sender] -= value;
        
        emit Transfer(from, to, value);
        return true;
    }}
    
    function pause() external onlyOwner {{
        paused = true;
        emit Paused(msg.sender);
    }}
    
    function unpause() external onlyOwner {{
        paused = false;
        emit Unpaused(msg.sender);
    }}
    
    // 道德经原则：无为而治，不过度干预
    function burn(uint256 value) external {{
        require(balanceOf[msg.sender] >= value, "Insufficient balance");
        balanceOf[msg.sender] -= value;
        totalSupply -= value;
        emit Transfer(msg.sender, address(0), value);
    }}
}}'''

    def _erc721_template(self) -> str:
        return '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title {project_name} NFT
 * @dev 基于道德经原则的ERC721 NFT合约
 * 设计原则: {principle}
 */

contract {project_name}NFT {{
    // 合约实现...
}}'''

    def _add_tao_comments(self, code: str, principle: str, tao_balance: float) -> str:
        """添加道德经注释"""
        insights = {
            "无为而治": "上善若水，水善利万物而不争。让合约自然运行，不强行干预。",
            "阴阳平衡": "万物负阴而抱阳，冲气以为和。平衡安全性与效率。", 
            "道法自然": "人法地，地法天，天法道，道法自然。遵循区块链的自然规律。"
        }
        
        insight = insights.get(principle, "道可道，非常道。名可名，非常名。")
        
        header = f'''/**
 * 道德经智能合约系统
 * 道平衡度: {tao_balance:.3f}
 * 核心原则: {principle}
 * 智慧启示: {insight}
 */
 
'''
        return header + code

    def _dao_template(self) -> str:
        return '''// SPDX-License-Identifier: MIT
    pragma solidity ^0.8.0;

    /**
    * @title {project_name} DAO
    * @dev 基于道德经原则的DAO治理合约
    * 设计原则: {principle}
    */

    contract {project_name}DAO {{
        // DAO合约实现...
    }}'''

    def _staking_template(self) -> str:
        return '''// SPDX-License-Identifier: MIT
    pragma solidity ^0.8.0;

    /**
    * @title {project_name} Staking
    * @dev 基于道德经原则的质押合约
    * 设计原则: {principle}
    */

    contract {project_name}Staking {{
        // 质押合约实现...
    }}'''

    def _governance_template(self) -> str:
        return '''// SPDX-License-Identifier: MIT
    pragma solidity ^0.8.0;

    /**
    * @title {project_name} Governance
    * @dev 基于道德经原则的治理合约
    * 设计原则: {principle}
    */

    contract {project_name}Governance {{
        // 治理合约实现...
    }}'''

class AICodeReviewer:
    """AI代码审查器"""
    
    def __init__(self):
        self.quality_metrics = {
            "security": 0.0,
            "efficiency": 0.0, 
            "readability": 0.0,
            "maintainability": 0.0
        }
        
        self.tao_patterns = {
            "无为": ["简单的逻辑", "最小的状态变更", "自然的流程"],
            "平衡": ["适度的检查", "均衡的资源使用", "对称的设计"],
            "简约": ["清晰的命名", "简化的逻辑", "去除冗余"]
        }
    
    def review_code(self, code: str, project: Project) -> CodeReview:
        """审查代码"""
        # 分析代码质量
        security_score = self._analyze_security(code)
        efficiency_score = self._analyze_efficiency(code)
        readability_score = self._analyze_readability(code)
        
        overall_score = (security_score + efficiency_score + readability_score) / 3
        
        # 识别问题
        issues = self._identify_issues(code)
        suggestions = self._generate_suggestions(code, issues)
        
        # 生成道德经洞见
        tao_insight = self._generate_tao_insight(overall_score, project.tao_balance)
        
        return CodeReview(
            review_id=hashlib.md5(f"{project.project_id}{time.time()}".encode()).hexdigest()[:8],
            project_id=project.project_id,
            reviewer="道德经AI审查器",
            review_date=datetime.datetime.now().isoformat(),
            score=overall_score,
            issues=issues,
            suggestions=suggestions,
            tao_insight=tao_insight
        )
    
    def _analyze_security(self, code: str) -> float:
        """分析安全性"""
        security_issues = [
            "tx.origin", "block.timestamp", "unchecked math",
            "reentrancy", "overflow", "underflow"
        ]
        
        issue_count = sum(1 for issue in security_issues if issue in code.lower())
        return max(0.0, 1.0 - issue_count * 0.2)
    
    def _analyze_efficiency(self, code: str) -> float:
        """分析效率"""
        # 简化的效率分析
        lines = code.split('\n')
        complexity = len([line for line in lines if any(op in line for op in ['for', 'while', 'if', 'else'])]) / max(1, len(lines))
        return max(0.0, 1.0 - complexity * 0.5)
    
    def _analyze_readability(self, code: str) -> float:
        """分析可读性"""
        lines = code.split('\n')
        comment_lines = len([line for line in lines if line.strip().startswith('//') or line.strip().startswith('/*')])
        comment_ratio = comment_lines / max(1, len(lines))
        
        # 检查命名规范
        good_naming = len(re.findall(r'\b([A-Z][a-z]+[A-Z][a-z]+)\b', code)) > 5
        
        score = comment_ratio * 0.7 + (0.3 if good_naming else 0.0)
        return min(1.0, score)
    
    def _identify_issues(self, code: str) -> List[str]:
        """识别问题"""
        issues = []
        
        if "tx.origin" in code:
            issues.append("使用tx.origin可能存在安全问题")
        if "block.timestamp" in code and "random" in code.lower():
            issues.append("使用block.timestamp生成随机数不安全")
        if code.count("if") > code.count("else"):
            issues.append("条件逻辑不平衡")
        if len(code.split('\n')) > 200:
            issues.append("合约过长，建议拆分")
            
        return issues
    
    def _generate_suggestions(self, code: str, issues: List[str]) -> List[str]:
        """生成改进建议"""
        suggestions = []
        
        if "tx.origin" in code:
            suggestions.append("建议使用msg.sender代替tx.origin")
        if len(issues) > 3:
            suggestions.append("建议简化合约逻辑，遵循'大道至简'原则")
        if code.count("require") < 3:
            suggestions.append("建议增加输入验证，体现'知止不殆'的智慧")
            
        return suggestions
    
    def _generate_tao_insight(self, score: float, tao_balance: float) -> str:
        """生成道德经洞见"""
        if score > 0.8:
            return "代码质量优秀，符合'上善若水'的境界，自然流畅而无为。"
        elif score > 0.6:
            return "代码质量良好，体现了'阴阳平衡'的思想，各方面均衡发展。"
        elif score > 0.4:
            return "代码质量一般，建议'为道日损'，去除不必要的复杂性。"
        else:
            return "代码质量需要改进，记住'治大国若烹小鲜'，不要过度干预。"

class ProjectManager:
    """项目管理器"""
    
    def __init__(self):
        self.projects: Dict[str, Project] = {}
        self.code_reviews: Dict[str, List[CodeReview]] = {}
        self.load_projects()
    
    def create_project(self, name: str, project_type: ProjectType, description: str) -> Project:
        """创建新项目"""
        project_id = hashlib.md5(f"{name}{time.time()}".encode()).hexdigest()[:8]
        now = datetime.datetime.now().isoformat()
        
        project = Project(
            project_id=project_id,
            name=name,
            project_type=project_type,
            description=description,
            created_date=now,
            last_modified=now
        )
        
        self.projects[project_id] = project
        self.code_reviews[project_id] = []
        self.save_projects()
        
        return project
    
    def update_project_progress(self, project_id: str, progress: float):
        """更新项目进度"""
        if project_id in self.projects:
            self.projects[project_id].progress = progress
            self.projects[project_id].last_modified = datetime.datetime.now().isoformat()
            self.save_projects()
    
    def add_code_review(self, project_id: str, review: CodeReview):
        """添加代码审查"""
        if project_id in self.code_reviews:
            self.code_reviews[project_id].append(review)
            
            # 根据审查结果更新项目质量
            if review.score > 0.8:
                self.projects[project_id].code_quality = CodeQuality.EXCELLENT
            elif review.score > 0.6:
                self.projects[project_id].code_quality = CodeQuality.GOOD
            elif review.score > 0.4:
                self.projects[project_id].code_quality = CodeQuality.FAIR
            else:
                self.projects[project_id].code_quality = CodeQuality.POOR
                
            self.save_projects()
    
    def get_project_stats(self) -> Dict[str, Any]:
        """获取项目统计"""
        total_projects = len(self.projects)
        completed_projects = sum(1 for p in self.projects.values() if p.progress >= 1.0)
        quality_values = {
            CodeQuality.EXCELLENT: 5,
            CodeQuality.GOOD: 4,
            CodeQuality.FAIR: 3,
            CodeQuality.POOR: 2,
            CodeQuality.CRITICAL: 1
        }
        avg_quality = np.mean([quality_values[p.code_quality] for p in self.projects.values()]) if self.projects else 3.0
        
        return {
            "total_projects": total_projects,
            "completed_projects": completed_projects,
            "completion_rate": completed_projects / max(1, total_projects),
            "average_quality": avg_quality,
            "project_types": {pt.value: sum(1 for p in self.projects.values() if p.project_type == pt) 
                            for pt in ProjectType}
        }
    
    def save_projects(self):
        """保存项目数据"""
        # 转换枚举为可序列化的字符串
        projects_data = {}
        for pid, project in self.projects.items():
            project_dict = asdict(project)
            project_dict['project_type'] = project.project_type.value
            project_dict['code_quality'] = project.code_quality.value
            projects_data[pid] = project_dict
        
        reviews_data = {}
        for pid, reviews in self.code_reviews.items():
            reviews_data[pid] = [asdict(review) for review in reviews]
        
        data = {
            "projects": projects_data,
            "reviews": reviews_data,
            "version": "1.0",
            "saved_at": datetime.datetime.now().isoformat()
        }
        
        try:
            with open("tao_projects.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存项目数据失败: {e}")
    
    def load_projects(self):
        """加载项目数据"""
        try:
            # 检查文件是否存在且不为空
            if not os.path.exists("tao_projects.json"):
                print("未找到项目数据文件，将创建新文件")
                return
                
            file_size = os.path.getsize("tao_projects.json")
            if file_size == 0:
                print("项目数据文件为空，将创建新数据")
                return
                
            with open("tao_projects.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                
            # 检查数据格式
            if not isinstance(data, dict):
                print("项目数据文件格式错误，将创建新数据")
                return
                
            # 加载项目
            projects_data = data.get("projects", {})
            for pid, proj_data in projects_data.items():
                try:
                    # 将字符串转换回枚举
                    if 'project_type' in proj_data:
                        proj_data['project_type'] = ProjectType(proj_data['project_type'])
                    if 'code_quality' in proj_data:
                        proj_data['code_quality'] = CodeQuality(proj_data['code_quality'])
                    
                    self.projects[pid] = Project(**proj_data)
                except Exception as e:
                    print(f"加载项目 {pid} 失败: {e}")
                    continue
            
            # 加载审查记录
            reviews_data = data.get("reviews", {})
            for pid, review_list in reviews_data.items():
                try:
                    self.code_reviews[pid] = [CodeReview(**review_data) for review_data in review_list]
                except Exception as e:
                    print(f"加载项目 {pid} 的审查记录失败: {e}")
                    self.code_reviews[pid] = []
                    
        except json.JSONDecodeError as e:
            print(f"JSON 解析错误: {e}")
            print("项目数据文件可能已损坏，将创建新数据")
            # 备份损坏的文件
            try:
                if os.path.exists("tao_projects.json"):
                    backup_name = f"tao_projects_backup_{int(time.time())}.json"
                    os.rename("tao_projects.json", backup_name)
                    print(f"已备份损坏的文件为: {backup_name}")
            except:
                pass
        except Exception as e:
            print(f"加载项目数据失败: {e}")

# ==================== 道德经核心系统 ====================

class YinYangState(Enum):
    YIN = -1
    YANG = 1
    BALANCE = 0

@dataclass
class TaoVector:
    yin: float
    yang: float
    
    def __post_init__(self):
        self.yin = max(0.0, min(1.0, self.yin))
        self.yang = max(0.0, min(1.0, self.yang))
    
    @property
    def balance(self) -> float:
        return 1 - abs(self.yin - self.yang)
    
    @property
    def dominance(self) -> YinYangState:
        diff = self.yang - self.yin
        if diff < -0.3:
            return YinYangState.YIN
        elif diff > 0.3:
            return YinYangState.YANG
        return YinYangState.BALANCE
    
    def to_symbol(self) -> str:
        symbols = {
            (0.8, 0.2): "☵", (0.2, 0.8): "☲", (0.5, 0.5): "☯",
            (0.7, 0.3): "☴", (0.3, 0.7): "☱", (0.9, 0.1): "☷",
            (0.1, 0.9): "☰", (0.6, 0.4): "☳", (0.4, 0.6): "☶",
        }
        return symbols.get((round(self.yin, 1), round(self.yang, 1)), "⚋")
    
    def to_color(self) -> QColor:
        if self.dominance == YinYangState.YIN:
            return QColor(0, int(100 + 155 * self.yin), int(200 + 55 * self.yin))
        elif self.dominance == YinYangState.YANG:
            return QColor(int(200 + 55 * self.yang), int(100 + 155 * self.yang), 0)
        else:
            return QColor(int(100 + 155 * self.balance), 
                         int(200 + 55 * self.balance), 
                         int(100 + 155 * self.balance))
    
    def to_hexagram(self) -> str:
        """转换为易经卦象"""
        if self.yin > 0.8:
            return "坤卦"
        elif self.yang > 0.8:
            return "乾卦"
        elif self.yin > 0.6:
            return "坎卦"
        elif self.yang > 0.6:
            return "离卦"
        elif self.balance > 0.7:
            return "泰卦"
        else:
            return "未济卦"

class TaoAICodeGenerator:
    """AI驱动的道德经代码生成器"""
    
    def __init__(self):
        self.tao_knowledge_base = self._build_tao_knowledge()
        self.code_templates = self._build_templates()
        self.learned_patterns: Dict[str, float] = {}
    
    def _build_tao_knowledge(self) -> Dict[str, List[str]]:
        return {
            "无为": ["顺其自然，不强行干预", "让事物按其本性发展", "避免过度设计和控制"],
            "柔弱": ["柔软胜过刚强", "灵活性优于僵化", "适应变化的能力"],
            "平衡": ["阴阳调和，不偏不倚", "保持适度和中庸", "动态平衡而非静态"],
            "简约": ["大道至简", "去除不必要的复杂性", "本质优于表象"],
            "自然": ["道法自然", "符合事物本性", "自发秩序的形成"]
        }
    
    def _build_templates(self) -> Dict[str, str]:
        return {
            "algorithm": """
def {name}(data):
    \"\"\"{tao_principle}\"\"\"
    {initialization}
    
    # {tao_insight}
    {core_logic}
    
    return {result}
"""
        }
    
    def generate_tao_algorithm(self, tao_vector: TaoVector, complexity: int = 3) -> str:
        principle = self._select_principle(tao_vector)
        name = self._generate_tao_name(tao_vector)
        
        template = self.code_templates["algorithm"]
        components = self._generate_algorithm_components(tao_vector, complexity)
        
        code = template.format(
            name=name,
            tao_principle=principle,
            tao_insight=self._get_tao_insight(tao_vector),
            **components
        )
        
        return self._add_tao_comments(code, tao_vector)
    
    def _select_principle(self, tao_vector: TaoVector) -> str:
        if tao_vector.dominance == YinYangState.YIN:
            principles = ["无为", "柔弱", "简约"]
        elif tao_vector.dominance == YinYangState.YANG:
            principles = ["自然", "平衡"] 
        else:
            principles = ["平衡", "自然", "简约"]
        return random.choice(principles)
    
    def _generate_tao_name(self, tao_vector: TaoVector) -> str:
        base_names = {
            YinYangState.YIN: ["静", "柔", "虚", "纳", "容"],
            YinYangState.YANG: ["动", "刚", "实", "创", "发"],
            YinYangState.BALANCE: ["和", "中", "平", "调", "衡"]
        }
        prefixes = ["道", "德", "自", "天", "地"]
        name1 = random.choice(prefixes)
        name2 = random.choice(base_names[tao_vector.dominance])
        return f"{name1}{name2}_algorithm"
    
    def _generate_algorithm_components(self, tao_vector: TaoVector, complexity: int) -> Dict[str, str]:
        if tao_vector.dominance == YinYangState.YIN:
            initialization = "state = data"
            core_logic = self._generate_yin_logic(complexity)
            result = "state"
        elif tao_vector.dominance == YinYangState.YANG:
            initialization = "result = []\n    for item in data:"
            core_logic = self._generate_yang_logic(complexity)
            result = "result"
        else:
            initialization = "# 平衡初始化\n    working_data = data.copy()"
            core_logic = self._generate_balance_logic(complexity)
            result = "working_data"
        
        return {
            "initialization": initialization,
            "core_logic": core_logic,
            "result": result
        }
    
    def _generate_yin_logic(self, complexity: int) -> str:
        operations = [
            "# 阴之静：过滤与转化\n        state = list(filter(lambda x: x > 0, state))",
            "# 阴之柔：映射转换\n        state = list(map(lambda x: x * 0.5, state))",
            "# 阴之纳：累积吸收\n        state = [sum(state[:i+1]) for i in range(len(state))]",
            "# 阴之容：去重包容\n        state = list(set(state))"
        ]
        return '\n    '.join(random.sample(operations, min(complexity, len(operations))))
    
    def _generate_yang_logic(self, complexity: int) -> str:
        operations = [
            "# 阳之动：积极处理\n        result.append(item * 2)",
            "# 阳之创：创造新值\n        result.append(item ** 2)",
            "# 阳之发：扩展发散\n        result.extend([item, item + 1])",
            "# 阳之实：条件创造\n        if item % 2 == 0:\n            result.append(item)"
        ]
        return '\n        '.join(random.sample(operations, min(complexity, len(operations))))
    
    def _generate_balance_logic(self, complexity: int) -> str:
        operations = [
            "# 阴阳调和：过滤与映射\n        working_data = [x*2 for x in working_data if x > 0]",
            "# 动态平衡：条件处理\n        if len(working_data) > 1:\n            working_data = sorted(working_data)",
            "# 中庸之道：取中值\n        mid = len(working_data) // 2\n        working_data = working_data[max(0, mid-1):min(len(working_data), mid+2)]"
        ]
        return '\n    '.join(random.sample(operations, min(complexity, len(operations))))
    
    def _get_tao_insight(self, tao_vector: TaoVector) -> str:
        insights = {
            YinYangState.YIN: [
                "上善若水，水善利万物而不争",
                "柔弱胜刚强，无为而无所不为",
                "知其雄，守其雌，为天下溪"
            ],
            YinYangState.YANG: [
                "道生一，一生二，二生三，三生万物",
                "反者道之动，弱者道之用", 
                "大方无隅，大器晚成，大音希声"
            ],
            YinYangState.BALANCE: [
                "万物负阴而抱阳，冲气以为和",
                "知足不辱，知止不殆，可以长久",
                "治大国若烹小鲜"
            ]
        }
        return random.choice(insights[tao_vector.dominance])
    
    def _add_tao_comments(self, code: str, tao_vector: TaoVector) -> str:
        symbol = tao_vector.to_symbol()
        hexagram = tao_vector.to_hexagram()
        
        header = f'''"""
{symbol} 《道德经》编程系统
卦象: {hexagram}
阴阳状态: 阴({tao_vector.yin:.3f}) 阳({tao_vector.yang:.3f}) 平衡({tao_vector.balance:.3f})
生成时间: {time.strftime("%Y-%m-%d %H:%M:%S")}
原则: {self._select_principle(tao_vector)}
"""\n\n'''
        
        return header + code
    
class CompleteTaoSystem:
    """完整的道德经系统"""
    
    def __init__(self, num_cells: int = 16):
        self.cells = [AdvancedTaoCell(i, (random.uniform(0, 10), random.uniform(0, 10))) 
                     for i in range(num_cells)]
        
        self._connect_tao_network()
        
        self.code_generator = TaoAICodeGenerator()
        self.chatbot = TaoAIChatbot()
        
        self.evolution_steps = 0
        self.generated_codes = []
        self.system_health = 1.0
    
    def _connect_tao_network(self):
        """连接道德经网络"""
        for i, cell in enumerate(self.cells):
            num_neighbors = random.randint(3, 5)
            possible_neighbors = [c for j, c in enumerate(self.cells) if j != i]
            cell.neighbors = random.sample(possible_neighbors, 
                                         min(num_neighbors, len(possible_neighbors)))
            
class AdvancedTaoCell:
    def __init__(self, cell_id: int, position: Tuple[float, float] = (0, 0)):
        self.cell_id = cell_id
        self.position = position
        self.velocity = (random.uniform(-0.1, 0.1), random.uniform(-0.1, 0.1))
        
        self.lorenz_state = np.array([random.uniform(0.1, 1.0) for _ in range(3)])
        self.rossler_state = np.array([random.uniform(0.1, 1.0) for _ in range(3)])
        
        self.energy = 1.0
        self.neighbors: List['AdvancedTaoCell'] = []
        
        self.trajectory = [position]
        self.tao_history: List[TaoVector] = []
    
    @property
    def current_tao(self) -> TaoVector:
        lorenz_yang = np.mean(self.lorenz_state)
        rossler_yin = 1.0 - np.mean(self.rossler_state)
        
        return TaoVector(
            yin=rossler_yin,
            yang=lorenz_yang
        )
    
    def multi_chaos_update(self, dt: float = 0.01):
        sigma, rho, beta = 10.0, 28.0, 8.0/3.0
        x, y, z = self.lorenz_state
        self.lorenz_state += dt * np.array([
            sigma * (y - x),
            x * (rho - z) - y,
            x * y - beta * z
        ])
        
        a, b, c = 0.2, 0.2, 5.7
        x_r, y_r, z_r = self.rossler_state
        self.rossler_state += dt * np.array([
            -y_r - z_r,
            x_r + a * y_r,
            b + z_r * (x_r - c)
        ])
        
        self._update_position(dt)
        self.tao_history.append(self.current_tao)
        
        if len(self.tao_history) > 1000:
            self.tao_history.pop(0)
    
    def _update_position(self, dt: float):
        x, y = self.position
        vx, vy = self.velocity
        
        tao = self.current_tao
        vx += (tao.yang - 0.5) * 0.1
        vy += (tao.yin - 0.5) * 0.1
        
        x = (x + vx * dt) % 10.0
        y = (y + vy * dt) % 10.0
        
        self.position = (x, y)
        self.velocity = (vx * 0.99, vy * 0.99)
        self.trajectory.append(self.position)
    
    def compute_tao_entropy(self) -> float:
        if len(self.tao_history) < 2:
            return 0.0
        
        changes = []
        for i in range(1, len(self.tao_history)):
            prev = self.tao_history[i-1]
            curr = self.tao_history[i]
            change = abs(prev.yin - curr.yin) + abs(prev.yang - curr.yang)
            changes.append(change)
        
        return np.std(changes) if changes else 0.0

class TaoAIChatbot:
    def __init__(self):
        self.tao_wisdom = self._load_tao_wisdom()
        self.conversation_history: List[Dict[str, str]] = []
        self.understanding_level = 0.0
    
    def _load_tao_wisdom(self) -> Dict[str, List[str]]:
        return {
            "无为": ["无为而无所不为。", "道常无为而无不为。", "为无为，事无事，味无味。"],
            "自然": ["人法地，地法天，天法道，道法自然。", "辅万物之自然而不敢为。"],
            "平衡": ["万物负阴而抱阳，冲气以为和。", "知足不辱，知止不殆，可以长久。"],
            "简约": ["少则得，多则惑。", "大道至简。", "为学日益，为道日损。"]
        }
    
    def chat(self, user_input: str) -> str:
        intent = self._analyze_intent(user_input)
        tao_context = self._get_tao_context(intent)
        response = self._generate_response(user_input, intent, tao_context)
        
        self.conversation_history.append({
            "user": user_input,
            "ai": response,
            "intent": intent,
            "timestamp": time.time()
        })
        
        self.understanding_level = min(1.0, self.understanding_level + 0.01)
        return response
    
    def _analyze_intent(self, text: str) -> str:
        text = text.lower()
        if any(word in text for word in ["如何", "怎样", "怎么", "方法"]):
            return "method"
        elif any(word in text for word in ["为什么", "原因", "道理"]):
            return "why" 
        elif any(word in text for word in ["是什么", "定义", "意思"]):
            return "definition"
        else:
            return "general"
    
    def _get_tao_context(self, intent: str) -> Dict[str, Any]:
        if self.conversation_history:
            available_principles = [p for p in self.tao_wisdom.keys() 
                                  if not any(p in msg["ai"] for msg in self.conversation_history[-3:])]
        else:
            available_principles = list(self.tao_wisdom.keys())
        
        principle = random.choice(available_principles) if available_principles else "无为"
        wisdom = random.choice(self.tao_wisdom[principle])
        
        return {
            "principle": principle,
            "wisdom": wisdom,
            "intent": intent,
            "understanding": self.understanding_level
        }
    
    def _generate_response(self, user_input: str, intent: str, context: Dict[str, Any]) -> str:
        principle = context["principle"]
        wisdom = context["wisdom"]
        
        if intent == "method":
            responses = [
                f"关于'{user_input}'，道德经教导我们：{wisdom}\n\n应用方法：{self._get_method_advice(principle)}",
                f"从《道德经》的角度，处理'{user_input}'应该：{self._get_tao_approach(principle)}\n\n经典智慧：{wisdom}"
            ]
        elif intent == "why":
            responses = [
                f"道德经对此的洞见是：{wisdom}\n\n这是因为{self._get_tao_reasoning(principle)}",
                f"《道德经》告诉我们：{wisdom}\n\n其中的道理在于：{self._get_deeper_meaning(principle)}"
            ]
        else:
            responses = [
                f"{wisdom}\n\n这对'{user_input}'的启示是：{self._get_general_insight(principle)}",
                f"想起道德经的教导：{wisdom}\n\n或许这对您思考'{user_input}'有所启发"
            ]
        
        response = random.choice(responses)
        
        if self.understanding_level > 0.5:
            response += f"\n\n（基于您之前的对话，我注意到您对道德经的理解正在深化）"
        
        return response
    
    def _get_method_advice(self, principle: str) -> str:
        advice = {
            "无为": "顺应事物本性，不强求不控制，让解决方案自然显现",
            "自然": "找到最符合事物本质的方法，避免人为复杂化",
            "平衡": "在各种因素间找到中点，保持动态平衡",
            "简约": "从简单处着手，去除不必要的复杂性"
        }
        return advice.get(principle, "静心思考，答案自现")

    def _get_tao_approach(self, principle: str) -> str:
        approaches = {
            "无为": "以不干预为干预，以无为实现有为",
            "自然": "效法自然规律，如水之就下",
            "平衡": "执两用中，不偏不倚",
            "简约": "返璞归真，抓住本质"
        }
        return approaches.get(principle, "顺应道的方式")

    def _get_tao_reasoning(self, principle: str) -> str:
        reasoning = {
            "无为": "过度干预反而破坏事物的自然秩序",
            "自然": "道法自然，违背自然规律必受其害", 
            "平衡": "物极必反，唯有平衡可以长久",
            "简约": "简单之中蕴含着深刻的真理"
        }
        return reasoning.get(principle, "这是道的运行规律")

    def _get_general_insight(self, principle: str) -> str:
        insights = {
            "无为": "不强求，不控制，顺应自然规律",
            "自然": "遵循事物本性，不人为干预",
            "平衡": "保持适度，避免极端",
            "简约": "回归简单，去除不必要的复杂"
        }
        return insights.get(principle, "道法自然，无为而治")

    def _get_deeper_meaning(self, principle: str) -> str:
        meanings = {
            "无为": "不是不作为，而是不违背自然规律的作为",
            "自然": "万物本来的样子，道的运行方式",
            "平衡": "阴阳调和，动态稳定的状态",
            "简约": "本质的体现，去除表象的干扰"
        }
        return meanings.get(principle, "道的深远智慧")

    def _get_principle_definition(self, principle: str) -> str:
        definitions = {
            "无为": "顺应自然，不强求不干预的智慧",
            "自然": "道的本质，万物运行的规律",
            "平衡": "阴阳调和，不偏不倚的状态",
            "简约": "去除复杂，回归本真的方法"
        }
        return definitions.get(principle, "道德经的核心原则")

    def _get_tao_explanation(self, principle: str) -> str:
        explanations = {
            "无为": "道常无为而无不为，侯王若能守之，万物将自化",
            "自然": "人法地，地法天，天法道，道法自然",
            "平衡": "万物负阴而抱阳，冲气以为和",
            "简约": "为学日益，为道日损。损之又损，以至于无为"
        }
        return explanations.get(principle, "道德经的深邃智慧")

# ==================== PyQt5图形界面 ====================

class CreateProjectDialog(QDialog):
    """创建项目对话框"""
    
    project_created = pyqtSignal(Project)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("创建新项目")
        self.setModal(True)
        self.init_ui()
    
    def init_ui(self):
        layout = QFormLayout()
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("输入项目名称")
        
        self.type_combo = QComboBox()
        for project_type in ProjectType:
            self.type_combo.addItem(project_type.value, project_type)
        
        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(100)
        self.desc_edit.setPlaceholderText("输入项目描述...")
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        
        layout.addRow("项目名称:", self.name_edit)
        layout.addRow("项目类型:", self.type_combo)
        layout.addRow("项目描述:", self.desc_edit)
        layout.addRow(buttons)
        
        self.setLayout(layout)
    
    def accept(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "输入错误", "请输入项目名称")
            return
        
        project_type = self.type_combo.currentData()
        description = self.desc_edit.toPlainText().strip()
        
        self.project_created.emit(ProjectManager().create_project(name, project_type, description))
        super().accept()

class ProjectTreeWidget(QTreeWidget):
    """项目树形控件"""
    
    project_selected = pyqtSignal(Project)
    
    def __init__(self):
        super().__init__()
        self.setHeaderLabels(["项目", "状态", "进度"])
        self.setColumnCount(3)
        self.project_manager = ProjectManager()
        self.refresh_projects()
        
        self.itemDoubleClicked.connect(self.on_item_double_clicked)
    
    def refresh_projects(self):
        """刷新项目列表"""
        self.clear()
        
        for project in self.project_manager.projects.values():
            item = QTreeWidgetItem([
                project.name,
                project.status,
                f"{project.progress:.1%}"
            ])
            item.setData(0, Qt.UserRole, project.project_id)
            
            # 根据质量设置颜色
            if project.code_quality == CodeQuality.EXCELLENT:
                item.setForeground(0, QColor(0, 128, 0))
            elif project.code_quality == CodeQuality.POOR:
                item.setForeground(0, QColor(255, 0, 0))
                
            self.addTopLevelItem(item)
    
    def on_item_double_clicked(self, item, column):
        """项目双击事件"""
        project_id = item.data(0, Qt.UserRole)
        project = self.project_manager.projects.get(project_id)
        if project:
            self.project_selected.emit(project)

class CodeReviewWidget(QWidget):
    """代码审查组件"""
    
    def __init__(self):
        super().__init__()
        self.current_project = None
        self.ai_reviewer = AICodeReviewer()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 代码编辑器
        code_group = QGroupBox("代码编辑器")
        code_layout = QVBoxLayout()
        
        self.code_editor = QTextEdit()
        self.code_editor.setFont(QFont("Consolas", 10))
        self.code_editor.setPlaceholderText("在此输入Solidity代码...")
        
        code_buttons = QHBoxLayout()
        self.review_btn = QPushButton("AI代码审查")
        self.generate_btn = QPushButton("生成智能合约")
        self.save_btn = QPushButton("保存代码")
        
        code_buttons.addWidget(self.review_btn)
        code_buttons.addWidget(self.generate_btn)
        code_buttons.addWidget(self.save_btn)
        code_buttons.addStretch()
        
        code_layout.addWidget(self.code_editor)
        code_layout.addLayout(code_buttons)
        code_group.setLayout(code_layout)
        
        # 审查结果
        review_group = QGroupBox("审查结果")
        review_layout = QVBoxLayout()
        
        self.review_result = QTextEdit()
        self.review_result.setReadOnly(True)
        self.review_result.setFont(QFont("微软雅黑", 9))
        
        review_layout.addWidget(self.review_result)
        review_group.setLayout(review_layout)
        
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(code_group)
        splitter.addWidget(review_group)
        splitter.setSizes([400, 300])
        
        layout.addWidget(splitter)
        self.setLayout(layout)
        
        # 连接信号
        self.review_btn.clicked.connect(self.review_code)
        self.generate_btn.clicked.connect(self.generate_contract)
        self.save_btn.clicked.connect(self.save_code)
    
    def set_project(self, project: Project):
        """设置当前项目"""
        self.current_project = project
    
    def review_code(self):
        """审查代码"""
        if not self.current_project:
            QMessageBox.warning(self, "警告", "请先选择项目")
            return
        
        code = self.code_editor.toPlainText().strip()
        if not code:
            QMessageBox.warning(self, "警告", "请输入要审查的代码")
            return
        
        # 执行审查
        review = self.ai_reviewer.review_code(code, self.current_project)
        ProjectManager().add_code_review(self.current_project.project_id, review)
        
        # 显示结果
        result_text = f"""代码审查报告
================
项目: {self.current_project.name}
审查者: {review.reviewer}
审查时间: {review.review_date}
综合评分: {review.score:.2f}

道德经洞见:
{review.tao_insight}

发现的问题:
"""
        for i, issue in enumerate(review.issues, 1):
            result_text += f"{i}. {issue}\n"
        
        result_text += "\n改进建议:\n"
        for i, suggestion in enumerate(review.suggestions, 1):
            result_text += f"{i}. {suggestion}\n"
        
        self.review_result.setText(result_text)
    
    def generate_contract(self):
        """生成智能合约"""
        if not self.current_project:
            QMessageBox.warning(self, "警告", "请先选择项目")
            return
        
        contract_type, ok = QInputDialog.getItem(
            self, "选择合约类型", "合约类型:",
            ["ERC20", "ERC721", "DAO", "Staking", "Governance"], 0, False
        )
        
        if ok and contract_type:
            generator = SmartContractGenerator()
            contract_code = generator.generate_contract(
                contract_type, self.current_project, self.current_project.tao_balance
            )
            self.code_editor.setPlainText(contract_code)
    
    def save_code(self):
        """保存代码"""
        code = self.code_editor.toPlainText()
        if not code:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存代码", f"{self.current_project.name}.sol", "Solidity Files (*.sol)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(code)
                QMessageBox.information(self, "成功", f"代码已保存到: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败: {e}")

class TaoSystemDashboard(QWidget):
    """系统仪表盘"""
    
    def __init__(self):
        super().__init__()
        self.project_manager = ProjectManager()
        self.init_ui()
        self.update_dashboard()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 项目统计
        stats_group = QGroupBox("项目统计")
        stats_layout = QHBoxLayout()
        
        self.total_projects_label = QLabel("总项目: 0")
        self.completed_projects_label = QLabel("已完成: 0")
        self.completion_rate_label = QLabel("完成率: 0%")
        self.avg_quality_label = QLabel("平均质量: --")
        
        stats_layout.addWidget(self.total_projects_label)
        stats_layout.addWidget(self.completed_projects_label)
        stats_layout.addWidget(self.completion_rate_label)
        stats_layout.addWidget(self.avg_quality_label)
        stats_layout.addStretch()
        
        stats_group.setLayout(stats_layout)
        
        # 质量分布
        quality_group = QGroupBox("代码质量分布")
        quality_layout = QHBoxLayout()
        
        self.quality_bars = {}
        for quality in CodeQuality:
            bar_widget = QWidget()
            bar_layout = QVBoxLayout()
            
            label = QLabel(quality.value)
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(0)
            
            bar_layout.addWidget(label)
            bar_layout.addWidget(bar)
            bar_widget.setLayout(bar_layout)
            
            quality_layout.addWidget(bar_widget)
            self.quality_bars[quality] = bar
        
        quality_group.setLayout(quality_layout)
        
        # 项目类型分布
        type_group = QGroupBox("项目类型分布")
        type_layout = QVBoxLayout()
        
        self.type_labels = {}
        for project_type in ProjectType:
            label = QLabel(f"{project_type.value}: 0")
            type_layout.addWidget(label)
            self.type_labels[project_type] = label
        
        type_group.setLayout(type_layout)
        
        layout.addWidget(stats_group)
        layout.addWidget(quality_group)
        layout.addWidget(type_group)
        layout.addStretch()
        
        self.setLayout(layout)
    
    def update_dashboard(self):
        """更新仪表盘"""
        stats = self.project_manager.get_project_stats()
        
        self.total_projects_label.setText(f"总项目: {stats['total_projects']}")
        self.completed_projects_label.setText(f"已完成: {stats['completed_projects']}")
        self.completion_rate_label.setText(f"完成率: {stats['completion_rate']:.1%}")
        self.avg_quality_label.setText(f"平均质量: {stats['average_quality']:.2f}")
        
        # 更新质量分布
        quality_counts = {quality: 0 for quality in CodeQuality}
        for project in self.project_manager.projects.values():
            quality_counts[project.code_quality] += 1
        
        total = max(1, stats['total_projects'])
        for quality, bar in self.quality_bars.items():
            count = quality_counts[quality]
            percentage = (count / total) * 100
            bar.setValue(int(percentage))
        
        # 更新类型分布
        for project_type, label in self.type_labels.items():
            count = stats['project_types'].get(project_type.value, 0)
            label.setText(f"{project_type.value}: {count}")

class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.project_manager = ProjectManager()
        self.tao_system = CompleteTaoSystem()
        self.init_ui()
        self.connect_signals()
    
    def init_ui(self):
        self.setWindowTitle("《道德经》智能编程系统 - 企业版")
        self.setGeometry(100, 100, 1600, 1000)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        
        # 左侧项目树
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        
        self.project_tree = ProjectTreeWidget()
        self.create_project_btn = QPushButton("创建新项目")
        self.refresh_btn = QPushButton("刷新项目")
        
        left_layout.addWidget(QLabel("项目管理"))
        left_layout.addWidget(self.project_tree)
        left_layout.addWidget(self.create_project_btn)
        left_layout.addWidget(self.refresh_btn)
        
        left_widget.setLayout(left_layout)
        left_widget.setMaximumWidth(400)
        
        # 右侧选项卡
        self.tab_widget = QTabWidget()
        
        # 创建各个选项卡
        self.create_dashboard_tab()
        self.create_development_tab()
        self.create_analysis_tab()
        self.create_chat_tab()
        
        main_layout.addWidget(left_widget)
        main_layout.addWidget(self.tab_widget)
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("系统就绪 - 道法自然，无为而治")
        
        # 创建菜单栏
        self.create_menus()
    
    def create_menus(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        new_project_action = QAction('新建项目', self)
        new_project_action.triggered.connect(self.create_project_btn.click)
        file_menu.addAction(new_project_action)
        
        export_action = QAction('导出数据', self)
        export_action.triggered.connect(self.export_data)
        file_menu.addAction(export_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu('工具')
        
        code_review_action = QAction('批量代码审查', self)
        code_review_action.triggered.connect(self.batch_code_review)
        tools_menu.addAction(code_review_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        
        about_action = QAction('关于系统', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_dashboard_tab(self):
        """创建仪表盘选项卡"""
        self.dashboard = TaoSystemDashboard()
        self.tab_widget.addTab(self.dashboard, "📊 项目仪表盘")
    
    def create_development_tab(self):
        """创建开发选项卡"""
        self.code_review_widget = CodeReviewWidget()
        self.tab_widget.addTab(self.code_review_widget, "💻 智能开发")
    
    def create_analysis_tab(self):
        """创建分析选项卡"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # 项目详细分析
        analysis_group = QGroupBox("项目详细分析")
        analysis_layout = QVBoxLayout()
        
        self.analysis_table = QTableWidget()
        self.analysis_table.setColumnCount(6)
        self.analysis_table.setHorizontalHeaderLabels([
            "项目名称", "类型", "进度", "质量", "创建时间", "最后修改"
        ])
        
        analysis_layout.addWidget(self.analysis_table)
        analysis_group.setLayout(analysis_layout)
        
        layout.addWidget(analysis_group)
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "📈 项目分析")
    
    def create_chat_tab(self):
        """创建聊天选项卡"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        self.chat_widget = ChatWidget()
        layout.addWidget(self.chat_widget)
        
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "💭 AI助手")
    
    def connect_signals(self):
        """连接信号"""
        self.create_project_btn.clicked.connect(self.show_create_project_dialog)
        self.refresh_btn.clicked.connect(self.refresh_projects)
        self.project_tree.project_selected.connect(self.on_project_selected)
    
    def show_create_project_dialog(self):
        """显示创建项目对话框"""
        dialog = CreateProjectDialog(self)
        dialog.project_created.connect(self.on_project_created)
        dialog.exec_()
    
    def on_project_created(self, project: Project):
        """项目创建完成"""
        self.refresh_projects()
        self.status_bar.showMessage(f"项目 '{project.name}' 创建成功")
    
    def refresh_projects(self):
        """刷新项目列表"""
        self.project_tree.refresh_projects()
        self.dashboard.update_dashboard()
        self.update_analysis_table()
    
    def on_project_selected(self, project: Project):
        """项目选择事件"""
        self.code_review_widget.set_project(project)
        self.status_bar.showMessage(f"已选择项目: {project.name}")
    
    def update_analysis_table(self):
        """更新分析表格"""
        self.analysis_table.setRowCount(len(self.project_manager.projects))
        
        for i, project in enumerate(self.project_manager.projects.values()):
            self.analysis_table.setItem(i, 0, QTableWidgetItem(project.name))
            self.analysis_table.setItem(i, 1, QTableWidgetItem(project.project_type.value))
            self.analysis_table.setItem(i, 2, QTableWidgetItem(f"{project.progress:.1%}"))
            self.analysis_table.setItem(i, 3, QTableWidgetItem(project.code_quality.value))
            self.analysis_table.setItem(i, 4, QTableWidgetItem(project.created_date[:10]))
            self.analysis_table.setItem(i, 5, QTableWidgetItem(project.last_modified[:10]))
    
    def export_data(self):
        """导出数据"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出项目数据", "tao_projects_export.json", "JSON Files (*.json)"
        )
        
        if file_path:
            self.project_manager.save_projects()
            QMessageBox.information(self, "成功", "项目数据已导出")
    
    def batch_code_review(self):
        """批量代码审查"""
        if not self.project_manager.projects:
            QMessageBox.information(self, "提示", "没有可审查的项目")
            return
        
        QMessageBox.information(self, "批量审查", "批量代码审查功能开发中...")
    
    def show_about(self):
        """显示关于信息"""
        about_text = """
《道德经》智能编程系统 - 企业版

版本: 2.0.0
作者: 道德经AI研究团队

系统特色:
• 基于道德经哲学的智能合约生成
• AI驱动的代码质量审查
• 可视化项目管理和分析
• 智能开发助手和代码优化

核心理念:
道法自然，无为而治
阴阳平衡，简约高效
        """
        QMessageBox.about(self, "关于系统", about_text)

# ==================== 辅助组件 ====================

class ChatWidget(QWidget):
    """聊天组件"""
    
    def __init__(self):
        super().__init__()
        self.chatbot = TaoAIChatbot()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 聊天历史
        self.history = QTextEdit()
        self.history.setReadOnly(True)
        self.history.setFont(QFont("微软雅黑", 9))
        layout.addWidget(QLabel("道德经AI助手"))
        layout.addWidget(self.history)
        
        # 输入区域
        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("输入关于编程、项目或道德经的问题...")
        self.input_field.returnPressed.connect(self.send_message)
        
        self.send_btn = QPushButton("发送")
        self.send_btn.clicked.connect(self.send_message)
        
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_btn)
        layout.addLayout(input_layout)
        
        self.setLayout(layout)
    
    def send_message(self):
        message = self.input_field.text().strip()
        if message:
            self.add_message("您", message)
            response = self.chatbot.chat(message)
            self.add_message("道德经AI", response)
            self.input_field.clear()
    
    def add_message(self, sender: str, message: str):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {sender}: {message}\n"
        self.history.append(formatted_message)
        
        # 自动滚动到底部
        scrollbar = self.history.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 创建并显示主窗口
    window = MainWindow()
    window.show()
    
    # 显示启动消息
    QMessageBox.information(window, "欢迎", 
        "欢迎使用《道德经》智能编程系统！\n\n"
        "这是一个融合东方哲学与现代软件工程的创新平台。\n"
        "系统基于道德经原理，实现智能合约生成、代码审查和项目管理。\n\n"
        "道法自然，无为而治。")
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()