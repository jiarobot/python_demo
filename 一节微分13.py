"""
混合逻辑推理系统 v3.0 Final
============================
最终优化版：增强边界决策、可配置推理策略、完整的评估体系

核心架构：
1. 符号规则引擎 - 确定性逻辑推理
2. 神经网络 - 文本语义理解
3. 自适应融合 - 动态权重调整
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import numpy as np
import re
import math
from typing import List, Dict, Tuple, Any, Optional, Set, Union
from collections import OrderedDict, defaultdict
import random
import matplotlib.pyplot as plt
from dataclasses import dataclass, field
import warnings
import json
from datetime import datetime

warnings.filterwarnings('ignore')


# ============================================================================
# 数据结构定义
# ============================================================================

@dataclass
class Fact:
    """知识图谱事实"""
    predicate: str
    subject: str
    object: str
    
    def to_tuple(self) -> Tuple[str, str, str]:
        return (self.predicate, self.subject, self.object)
    
    def __hash__(self):
        return hash(self.to_tuple())
    
    def __eq__(self, other):
        return self.to_tuple() == (other if isinstance(other, tuple) else other.to_tuple())


@dataclass
class InferenceResult:
    """推理结果"""
    found: bool
    confidence: float
    evidence: List[Dict] = field(default_factory=list)
    derived_facts: Set[Tuple] = field(default_factory=set)
    type_conflict: bool = False
    partial_evidence: bool = False
    inference_depth: int = 0
    rule_used: str = ""


@dataclass
class PredictionResult:
    """预测结果"""
    confidence: float
    symbolic_confidence: float
    symbolic_found: bool
    prediction: bool
    entities: List[str]
    formula: str
    known_facts: List[Tuple]
    target_relation: str
    inference_detail: InferenceResult = None
    semantic_type: str = "unknown"
    decision_boundary: float = 0.5


# ============================================================================
# 符号规则引擎 v3.0
# ============================================================================

class SymbolicRuleEngine:
    """
    符号规则引擎 v3.0
    
    改进：
    - 完整的规则链
    - 精确的置信度衰减
    - 可配置的推理策略
    """
    
    # 关系分类体系
    RELATION_HIERARCHY = {
        'family': {
            'direct': {'Father', 'Mother', 'Son', 'Daughter', 'Brother', 'Sister'},
            'derived': {'Parent', 'Child', 'Spouse', 'Sibling'},
            'extended': {'Grandparent', 'Grandchild', 'Ancestor', 'Descendant',
                        'Uncle', 'Aunt', 'Nephew', 'Niece', 'Cousin'}
        },
        'professional': {
            'direct': {'Colleague', 'Manager', 'Employee', 'Supervisor'},
            'derived': {'Coworker', 'TeamMember'}
        },
        'social': {
            'direct': {'Friend', 'Neighbor', 'Acquaintance'},
            'derived': set()
        }
    }
    
    # 推理规则定义
    INFERENCE_RULES = {
        # 直接推导规则：已知 P(s,o) → Q(s,o)
        'direct': [
            ('Father', 'Parent', 0.95, 'father_to_parent'),
            ('Mother', 'Parent', 0.95, 'mother_to_parent'),
            ('Son', 'Child', 0.90, 'son_to_child'),
            ('Daughter', 'Child', 0.90, 'daughter_to_child'),
            ('Brother', 'Sibling', 0.85, 'brother_to_sibling'),
            ('Sister', 'Sibling', 0.85, 'sister_to_sibling'),
        ],
        # 逆推导规则：已知 P(s,o) → Q(o,s)
        'inverse': [
            ('Father', 'Child', 0.90, 'father_to_child_inverse'),
            ('Mother', 'Child', 0.90, 'mother_to_child_inverse'),
            ('Parent', 'Child', 0.95, 'parent_to_child_inverse'),
            ('Son', 'Parent', 0.85, 'son_to_parent_inverse'),
            ('Daughter', 'Parent', 0.85, 'daughter_to_parent_inverse'),
        ],
        # 对称规则
        'symmetric': ['Spouse', 'Sibling', 'Colleague', 'Friend', 'Coworker'],
        # 传递规则（多跳）
        'transitive': {
            'Grandparent': {
                'pattern': [('Parent', 0.95), ('Parent', 0.95)],
                'confidence': 0.80,
                'rule': 'grandparent_chain'
            },
            'Grandchild': {
                'pattern': [('Child', 0.95), ('Child', 0.95)],
                'confidence': 0.80,
                'rule': 'grandchild_chain'
            },
            'Ancestor': {
                'pattern': [('Parent', 0.95)],  # 传递闭包
                'confidence': 0.75,
                'rule': 'ancestor_transitive'
            },
            'Descendant': {
                'pattern': [('Child', 0.95)],
                'confidence': 0.75,
                'rule': 'descendant_transitive'
            }
        }
    }
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.max_depth = self.config.get('max_inference_depth', 5)
        self.confidence_threshold = self.config.get('confidence_threshold', 0.1)
    
    def get_relation_category(self, relation: str) -> Optional[str]:
        """获取关系类别"""
        for category, subcats in self.RELATION_HIERARCHY.items():
            for subcat, relations in subcats.items():
                if relation in relations:
                    return category
        return None
    
    def get_relation_subcategory(self, relation: str) -> Optional[str]:
        """获取关系子类别"""
        for category, subcats in self.RELATION_HIERARCHY.items():
            for subcat, relations in subcats.items():
                if relation in relations:
                    return subcat
        return None
    
    def infer(self, target_relation: str, facts: List[Tuple],
              entities: List[str]) -> InferenceResult:
        """
        执行符号推理
        
        Args:
            target_relation: 目标关系
            facts: 已知事实列表
            entities: 实体列表
        
        Returns:
            InferenceResult
        """
        # 转换为内部表示
        kg = {Fact(p, s, o) for p, s, o in facts}
        entity_set = set(entities)
        
        # Step 1: 扩展知识图谱
        expanded_kg = self._expand_knowledge_graph(kg)
        
        # Step 2: 根据关系类型选择推理策略
        target_category = self.get_relation_category(target_relation)
        target_subcat = self.get_relation_subcategory(target_relation)
        
        if target_relation in self.INFERENCE_RULES['transitive']:
            result = self._transitive_inference(target_relation, expanded_kg, entity_set)
        elif target_subcat == 'derived':
            result = self._derived_inference(target_relation, expanded_kg, kg, entity_set)
        elif target_relation in self.INFERENCE_RULES['symmetric']:
            result = self._symmetric_inference(target_relation, expanded_kg, entity_set)
        else:
            result = self._direct_inference(target_relation, expanded_kg, entity_set)
        
        # Step 3: 类型冲突检测
        result = self._detect_type_conflict(result, target_relation, kg, facts)
        
        # Step 4: 部分证据检测
        if not result.found:
            result = self._check_partial_evidence(result, target_relation, expanded_kg, entity_set)
        
        return result
    
    def _expand_knowledge_graph(self, kg: Set[Fact]) -> Set[Tuple]:
        """扩展知识图谱"""
        expanded = {(f.predicate, f.subject, f.object) for f in kg}
        
        # 应用直接推导规则
        for fact in kg:
            for src, tgt, conf, rule in self.INFERENCE_RULES['direct']:
                if fact.predicate == src:
                    expanded.add((tgt, fact.subject, fact.object))
            
            for src, tgt, conf, rule in self.INFERENCE_RULES['inverse']:
                if fact.predicate == src:
                    expanded.add((tgt, fact.object, fact.subject))
            
            if fact.predicate in self.INFERENCE_RULES['symmetric']:
                expanded.add((fact.predicate, fact.object, fact.subject))
        
        return expanded
    
    def _transitive_inference(self, target: str, kg: Set[Tuple],
                              entities: Set[str]) -> InferenceResult:
        """传递推理"""
        if target == 'Grandparent':
            return self._infer_grandparent(kg, entities)
        elif target == 'Grandchild':
            return self._infer_grandchild(kg, entities)
        elif target == 'Ancestor':
            return self._infer_ancestor(kg, entities)
        elif target == 'Descendant':
            return self._infer_descendant(kg, entities)
        
        return InferenceResult(found=False, confidence=0.1)
    
    def _infer_grandparent(self, kg: Set[Tuple], entities: Set[str]) -> InferenceResult:
        """Grandparent(x,y) = ∃z: Parent(x,z) ∧ Parent(z,y)"""
        evidence = []
        
        # 构建父辈映射
        parents_of = defaultdict(set)
        children_of = defaultdict(set)
        
        for pred, subj, obj in kg:
            if pred in ('Father', 'Mother', 'Parent'):
                parents_of[obj].add(subj)
                children_of[subj].add(obj)
        
        for z in entities:
            if z in parents_of and z in children_of:
                for x in parents_of[z]:
                    for y in children_of[z]:
                        if x != y and x in entities and y in entities:
                            evidence.append({
                                'x': x, 'z': z, 'y': y,
                                'path': f'{x} → Parent → {z} → Parent → {y}'
                            })
        
        if evidence:
            return InferenceResult(
                found=True,
                confidence=0.80,
                evidence=evidence,
                inference_depth=2,
                rule_used='grandparent_chain'
            )
        
        # 部分证据
        if parents_of:
            return InferenceResult(
                found=False, confidence=0.25, partial_evidence=True
            )
        
        return InferenceResult(found=False, confidence=0.10)
    
    def _infer_grandchild(self, kg: Set[Tuple], entities: Set[str]) -> InferenceResult:
        """Grandchild(x,y) = Grandparent(y,x)"""
        result = self._infer_grandparent(kg, entities)
        if result.found:
            for e in result.evidence:
                e['x'], e['y'] = e['y'], e['x']
                e['path'] = e['path'].replace('Grandparent', 'Grandchild')
            result.rule_used = 'grandchild_chain'
        return result
    
    def _infer_ancestor(self, kg: Set[Tuple], entities: Set[str]) -> InferenceResult:
        """Ancestor(x,y) = Parent+(x,y)"""
        evidence = []
        
        # 构建图
        children = defaultdict(set)
        for pred, subj, obj in kg:
            if pred in ('Father', 'Mother', 'Parent'):
                children[subj].add(obj)
        
        # BFS找所有后代
        for start in entities:
            if start in children:
                visited = {start}
                queue = [(child, 1) for child in children[start]]
                
                while queue:
                    node, depth = queue.pop(0)
                    if node in entities and node not in visited:
                        visited.add(node)
                        evidence.append({
                            'x': start, 'y': node, 'depth': depth,
                            'path': f'{start} --{depth}步→ {node}'
                        })
                        if node in children:
                            for child in children[node]:
                                if child not in visited:
                                    queue.append((child, depth + 1))
        
        if evidence:
            max_depth = max(e['depth'] for e in evidence)
            confidence = min(0.95, 0.60 + 0.15 * max_depth)
            
            return InferenceResult(
                found=True,
                confidence=confidence,
                evidence=evidence,
                inference_depth=max_depth,
                rule_used='ancestor_transitive'
            )
        
        if children:
            return InferenceResult(
                found=False, confidence=0.20, partial_evidence=True
            )
        
        return InferenceResult(found=False, confidence=0.10)
    
    def _infer_descendant(self, kg: Set[Tuple], entities: Set[str]) -> InferenceResult:
        """Descendant(x,y) = Ancestor(y,x)"""
        result = self._infer_ancestor(kg, entities)
        if result.found:
            for e in result.evidence:
                e['x'], e['y'] = e['y'], e['x']
            result.rule_used = 'descendant_transitive'
        return result
    
    def _derived_inference(self, target: str, expanded_kg: Set[Tuple],
                           original_kg: Set[Fact], entities: Set[str]) -> InferenceResult:
        """推导关系推理"""
        evidence = []
        direct_count = 0
        derived_count = 0
        
        for pred, subj, obj in expanded_kg:
            if pred == target and subj in entities and obj in entities:
                is_direct = Fact(pred, subj, obj) in original_kg
                if is_direct:
                    direct_count += 1
                else:
                    derived_count += 1
                evidence.append({
                    'subj': subj, 'obj': obj, 'is_direct': is_direct
                })
        
        if evidence:
            if direct_count > 0:
                confidence = min(0.95, 0.70 + 0.05 * direct_count)
            else:
                confidence = min(0.70, 0.40 + 0.05 * derived_count)
            
            return InferenceResult(
                found=True,
                confidence=confidence,
                evidence=evidence,
                derived_facts=expanded_kg - {(f.predicate, f.subject, f.object) for f in original_kg},
                rule_used='derived_relation'
            )
        
        return InferenceResult(found=False, confidence=0.10)
    
    def _symmetric_inference(self, target: str, kg: Set[Tuple],
                             entities: Set[str]) -> InferenceResult:
        """对称关系推理"""
        evidence = []
        for pred, subj, obj in kg:
            if pred == target and subj in entities and obj in entities:
                evidence.append({'subj': subj, 'obj': obj})
        
        if evidence:
            return InferenceResult(
                found=True,
                confidence=min(0.90, 0.60 + 0.05 * len(evidence)),
                evidence=evidence,
                rule_used='symmetric'
            )
        
        return InferenceResult(found=False, confidence=0.10)
    
    def _direct_inference(self, target: str, kg: Set[Tuple],
                          entities: Set[str]) -> InferenceResult:
        """直接关系推理"""
        evidence = []
        for pred, subj, obj in kg:
            if pred == target and subj in entities and obj in entities:
                evidence.append({'subj': subj, 'obj': obj})
        
        if evidence:
            return InferenceResult(
                found=True,
                confidence=min(0.95, 0.70 + 0.05 * len(evidence)),
                evidence=evidence
            )
        
        return InferenceResult(found=False, confidence=0.10)
    
    def _detect_type_conflict(self, result: InferenceResult, target: str,
                               original_kg: Set[Fact], facts: List[Tuple]) -> InferenceResult:
        """检测类型冲突"""
        target_category = self.get_relation_category(target)
        if target_category is None:
            return result
        
        # 收集已知事实的关系类别
        fact_categories = set()
        for pred, _, _ in facts:
            cat = self.get_relation_category(pred)
            if cat:
                fact_categories.add(cat)
        
        # 定义冲突对
        conflict_pairs = {
            ('family', 'professional'),
            ('family', 'social'),
            ('professional', 'family'),
        }
        
        for fc in fact_categories:
            if (target_category, fc) in conflict_pairs:
                result.type_conflict = True
                result.confidence = min(result.confidence, 0.05)
                break
        
        return result
    
    def _check_partial_evidence(self, result: InferenceResult, target: str,
                                 kg: Set[Tuple], entities: Set[str]) -> InferenceResult:
        """检查部分证据"""
        target_category = self.get_relation_category(target)
        
        if target_category == 'family':
            family_indicators = {'Father', 'Mother', 'Parent', 'Child', 'Son', 'Daughter'}
            for pred, subj, obj in kg:
                if pred in family_indicators and subj in entities and obj in entities:
                    result.partial_evidence = True
                    result.confidence = max(result.confidence, 0.20)
                    break
        
        return result


# ============================================================================
# 混合推理模型 v3.0
# ============================================================================

class HybridReasoner(nn.Module):
    """混合推理器 v3.0"""
    
    def __init__(self, vocab_size: int, num_predicates: int, num_constants: int,
                 embed_dim: int = 64, hidden_dim: int = 128,
                 max_entities: int = 10, max_seq_len: int = 60):
        super().__init__()
        
        # 文本编码器
        self.text_embedding = nn.Embedding(vocab_size, embed_dim)
        self.text_lstm = nn.LSTM(
            embed_dim, hidden_dim // 2,
            batch_first=True, bidirectional=True
        )
        self.text_proj = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.LayerNorm(hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.3)
        )
        
        # 符号规则引擎
        self.rule_engine = SymbolicRuleEngine()
        
        # 语义分析器
        self.semantic_analyzer = nn.Sequential(
            nn.Linear(hidden_dim // 2, 64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, 4)  # family, professional, social, uncertain
        )
        
        # 自适应融合网络
        # 输入: text_feat + sym_conf + sym_found + semantic_type + type_conflict + partial_evidence
        input_dim = hidden_dim // 2 + 1 + 1 + 4 + 1 + 1
        self.fusion = nn.Sequential(
            nn.Linear(input_dim, hidden_dim // 2),
            nn.BatchNorm1d(hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.4),
            nn.Linear(hidden_dim // 2, hidden_dim // 4),
            nn.BatchNorm1d(hidden_dim // 4),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim // 4, 1),
            nn.Sigmoid()
        )
        
        # 置信度校准器（解决边界模糊问题）
        self.calibrator = nn.Sequential(
            nn.Linear(1, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
            nn.Sigmoid()
        )
    
    def encode_text(self, tokens: torch.Tensor) -> torch.Tensor:
        """文本编码"""
        emb = self.text_embedding(tokens)
        _, (h, _) = self.text_lstm(emb)
        h = torch.cat([h[0], h[1]], dim=-1)
        return self.text_proj(h)
    
    def forward(self, text_tokens: torch.Tensor,
                target_relations: List[str],
                facts_list: List[List[Tuple]],
                entities_list: List[List[str]]) -> Dict[str, torch.Tensor]:
        """前向传播"""
        batch_size = text_tokens.size(0)
        device = text_tokens.device
        
        # 1. 文本编码
        text_feat = self.encode_text(text_tokens)
        
        # 2. 语义分析
        semantic_logits = self.semantic_analyzer(text_feat)
        semantic_probs = F.softmax(semantic_logits, dim=-1)
        
        # 3. 符号推理
        sym_confs = torch.zeros(batch_size, device=device)
        sym_founds = torch.zeros(batch_size, device=device)
        type_conflicts = torch.zeros(batch_size, device=device)
        partial_evidences = torch.zeros(batch_size, device=device)
        
        for i in range(batch_size):
            rel = target_relations[i]
            facts = facts_list[i] if i < len(facts_list) else []
            entities = entities_list[i] if i < len(entities_list) else []
            
            result = self.rule_engine.infer(rel, facts, entities)
            sym_confs[i] = result.confidence
            sym_founds[i] = 1.0 if result.found else 0.0
            type_conflicts[i] = 1.0 if result.type_conflict else 0.0
            partial_evidences[i] = 1.0 if result.partial_evidence else 0.0
        
        # 4. 融合所有特征
        combined = torch.cat([
            text_feat,
            sym_confs.unsqueeze(1),
            sym_founds.unsqueeze(1),
            semantic_probs,
            type_conflicts.unsqueeze(1),
            partial_evidences.unsqueeze(1),
        ], dim=-1)
        
        raw_confidence = self.fusion(combined)
        
        # 5. 置信度校准
        calibrated_confidence = self.calibrator(raw_confidence).squeeze(-1)
        
        # 6. 类型冲突时强制降低置信度
        final_confidence = torch.where(
            type_conflicts > 0.5,
            calibrated_confidence * 0.1,  # 类型冲突时大幅降低
            calibrated_confidence
        )
        
        return {
            'confidence': final_confidence,
            'raw_confidence': raw_confidence.squeeze(-1),
            'symbolic_confidence': sym_confs,
            'symbolic_found': sym_founds,
            'semantic_type': semantic_probs,
            'type_conflict': type_conflicts,
            'partial_evidence': partial_evidences,
        }


# ============================================================================
# 主系统 v3.0
# ============================================================================

class LogicReasoningSystem:
    """混合逻辑推理系统 v3.0 Final"""
    
    def __init__(self, domain: str = "family", max_entities: int = 10, max_seq_len: int = 60):
        self.domain = domain
        self.max_entities = max_entities
        self.max_seq_len = max_seq_len
        self.vocab_size = 1000
        self.predicate_map = {}
        self.model = None
        self.entity_vocab = set()
        self.training_history = []
        self.eval_results = []
        
        self._init_knowledge()
    
    def _init_knowledge(self):
        predicates = [
            'Father', 'Mother', 'Parent', 'Child', 'Spouse', 'Sibling',
            'Grandparent', 'Grandchild', 'Ancestor', 'Descendant',
            'Brother', 'Sister', 'Son', 'Daughter',
            'Uncle', 'Aunt', 'Nephew', 'Niece', 'Cousin',
            'Colleague', 'Manager', 'Employee', 'Friend', 'Neighbor'
        ]
        self.predicate_map = {p: i for i, p in enumerate(sorted(predicates))}
    
    def extract_entities(self, text: str) -> Dict:
        entities = re.findall(r'\b[A-Z][a-z]+\b', text)
        entities = list(OrderedDict.fromkeys(entities))[:self.max_entities]
        
        male = {'John','Michael','David','Robert','Thomas','George','Bob','Frank',
                'Kevin','Ian','James','William','Richard','Charles','Joseph','Daniel',
                'Matthew','Anthony','Mark','Tom','Jerry','Mike','Steve','Charlie','Henry'}
        female = {'Mary','Jennifer','Alice','Emma','Sarah','Helen','Karen','Lisa',
                  'Carol','Grace','Linda','Barbara','Susan','Jessica','Nancy','Betty',
                  'Margaret','Dorothy','Anna','Diana','Julia'}
        
        types = {}
        for e in entities:
            if e in male: types[e] = 'Male'
            elif e in female: types[e] = 'Female'
            else: types[e] = 'Unknown'
        
        self.entity_vocab.update(entities)
        return {'entities': entities, 'types': types}
    
    def text_to_tokens(self, text: str) -> torch.Tensor:
        tokens = [ord(c) % self.vocab_size for c in text[:self.max_seq_len]]
        while len(tokens) < self.max_seq_len:
            tokens.append(0)
        return torch.tensor(tokens, dtype=torch.long).unsqueeze(0)
    
    def create_sample(self, text: str, target_rel: str,
                      facts: List[Tuple] = None) -> Dict:
        info = self.extract_entities(text)
        return {
            'text': text,
            'text_tokens': self.text_to_tokens(text),
            'entities': info['entities'],
            'entity_types': info['types'],
            'target_relation': target_rel,
            'known_facts': facts or []
        }
    
    def init_model(self):
        n_const = max(len(self.entity_vocab) + 20, self.max_entities + 10)
        n_pred = len(self.predicate_map)
        
        self.model = HybridReasoner(
            vocab_size=self.vocab_size,
            num_predicates=n_pred,
            num_constants=n_const,
            embed_dim=64,
            hidden_dim=128,
            max_entities=self.max_entities,
            max_seq_len=self.max_seq_len
        )
        return self.model
    
    def train(self, data: List[Dict], epochs: int = 100,
              lr: float = 0.001, batch_size: int = 4,
              val_split: float = 0.15):
        """训练模型"""
        if self.model is None:
            self.init_model()
        
        # 划分训练/验证集
        random.shuffle(data)
        split_idx = int(len(data) * (1 - val_split))
        train_data = data[:split_idx]
        val_data = data[split_idx:]
        
        optimizer = optim.AdamW(self.model.parameters(), lr=lr, weight_decay=0.01)
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
        criterion = nn.BCELoss()
        
        self.model.train()
        best_val_acc = 0
        best_state = None
        patience = 25
        p_counter = 0
        
        print(f"\n训练配置: lr={lr}, epochs={epochs}, batch={batch_size}")
        print(f"训练集: {len(train_data)}, 验证集: {len(val_data)}")
        
        for epoch in range(epochs):
            # 训练
            self.model.train()
            train_loss = 0
            train_correct = 0
            train_total = 0
            
            random.shuffle(train_data)
            
            for i in range(0, len(train_data), batch_size):
                batch = train_data[i:i+batch_size]
                if len(batch) < 2:
                    continue
                
                try:
                    tokens = torch.cat([s['text_tokens'] for s in batch])
                    relations = [s['target_relation'] for s in batch]
                    facts = [s['known_facts'] for s in batch]
                    entities = [s['entities'] for s in batch]
                    
                    targets = torch.tensor(
                        [1.0 if s.get('is_true') else 0.0 for s in batch],
                        dtype=torch.float32
                    )
                    
                    outputs = self.model(tokens, relations, facts, entities)
                    conf = outputs['confidence']
                    sym_conf = outputs['symbolic_confidence']
                    
                    # 损失 = 融合损失 + 符号损失 + 校准损失
                    fusion_loss = criterion(conf, targets)
                    sym_loss = criterion(torch.clamp(sym_conf, 0.001, 0.999), targets)
                    
                    # 类型冲突惩罚
                    type_conflict = outputs['type_conflict']
                    conflict_penalty = (type_conflict * (1 - targets.abs() - 0.5).abs()).mean() * 0.5
                    
                    loss = fusion_loss + 0.3 * sym_loss + conflict_penalty
                    
                    optimizer.zero_grad()
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                    optimizer.step()
                    
                    train_loss += loss.item()
                    preds = (conf > 0.5).float()
                    train_correct += (preds == targets).sum().item()
                    train_total += len(targets)
                    
                except Exception as e:
                    continue
            
            # 验证
            val_acc = 0
            if val_data:
                val_acc = self._evaluate(val_data)
            
            scheduler.step()
            
            if train_total > 0:
                train_acc = train_correct / train_total
                avg_loss = train_loss / max(1, len(train_data) // batch_size)
                
                self.training_history.append({
                    'epoch': epoch, 'loss': avg_loss,
                    'train_acc': train_acc, 'val_acc': val_acc,
                    'lr': scheduler.get_last_lr()[0]
                })
                
                if val_acc > best_val_acc:
                    best_val_acc = val_acc
                    p_counter = 0
                    best_state = {k: v.cpu().clone() for k, v in self.model.state_dict().items()}
                else:
                    p_counter += 1
                
                if epoch % 20 == 0:
                    print(f'Epoch {epoch:3d} | Loss: {avg_loss:.4f} | '
                          f'Train: {train_acc:.4f} | Val: {val_acc:.4f}')
                
                if p_counter >= patience:
                    print(f"早停于epoch {epoch}, 最佳验证准确率: {best_val_acc:.4f}")
                    break
        
        if best_state:
            self.model.load_state_dict(best_state)
            print(f"已恢复最佳模型 (验证准确率: {best_val_acc:.4f})")
    
    def _evaluate(self, data: List[Dict]) -> float:
        """评估"""
        self.model.eval()
        correct = 0
        total = 0
        
        with torch.no_grad():
            for i in range(0, len(data), 4):
                batch = data[i:i+4]
                if not batch:
                    continue
                
                try:
                    tokens = torch.cat([s['text_tokens'] for s in batch])
                    relations = [s['target_relation'] for s in batch]
                    facts = [s['known_facts'] for s in batch]
                    entities = [s['entities'] for s in batch]
                    
                    targets = torch.tensor(
                        [1.0 if s.get('is_true') else 0.0 for s in batch],
                        dtype=torch.float32
                    )
                    
                    outputs = self.model(tokens, relations, facts, entities)
                    preds = (outputs['confidence'] > 0.5).float()
                    correct += (preds == targets).sum().item()
                    total += len(targets)
                except:
                    continue
        
        return correct / total if total > 0 else 0
    
    def predict(self, text: str, target_rel: str,
                facts: List[Tuple] = None) -> PredictionResult:
        """预测"""
        if self.model is None:
            raise ValueError("模型未初始化")
        
        self.model.eval()
        sample = self.create_sample(text, target_rel, facts)
        
        with torch.no_grad():
            outputs = self.model(
                sample['text_tokens'],
                [sample['target_relation']],
                [sample['known_facts']],
                [sample['entities']]
            )
        
        conf = outputs['confidence'].item()
        sym_conf = outputs['symbolic_confidence'].item()
        sym_found = outputs['symbolic_found'].item() > 0.5
        
        # 获取推理详情
        inference_detail = self.model.rule_engine.infer(
            target_rel, facts or [], sample['entities']
        )
        
        # 判断语义类型
        semantic_idx = outputs['semantic_type'][0].argmax().item()
        semantic_labels = ['family', 'professional', 'social', 'uncertain']
        semantic_type = semantic_labels[semantic_idx]
        
        return PredictionResult(
            confidence=conf,
            symbolic_confidence=sym_conf,
            symbolic_found=sym_found,
            prediction=conf > 0.5,
            entities=sample['entities'],
            formula=self._get_formula(target_rel),
            known_facts=facts or [],
            target_relation=target_rel,
            inference_detail=inference_detail,
            semantic_type=semantic_type
        )
    
    def _get_formula(self, target_rel: str) -> str:
        formulas = {
            'Parent': 'Father(x,y) ∨ Mother(x,y)',
            'Child': '∃p∈{Father,Mother}: p(y,x)',
            'Grandparent': '∃z: Parent(x,z) ∧ Parent(z,y)',
            'Grandchild': '∃z: Parent(z,x) ∧ Parent(y,z)',
            'Sibling': '∃p: Parent(p,x) ∧ Parent(p,y) ∧ x≠y',
            'Spouse': 'Spouse(x,y) ∧ Spouse(y,x)',
            'Ancestor': 'Parent⁺(x,y) (传递闭包)',
            'Descendant': 'Child⁺(x,y) (传递闭包)',
        }
        return formulas.get(target_rel, f'{target_rel}(x,y)')
    
    def plot_history(self):
        """绘制训练历史"""
        if not self.training_history:
            print("无训练历史")
            return
        
        epochs = [x['epoch'] for x in self.training_history]
        losses = [x['loss'] for x in self.training_history]
        train_accs = [x['train_acc'] for x in self.training_history]
        val_accs = [x['val_acc'] for x in self.training_history]
        lrs = [x['lr'] for x in self.training_history]
        
        fig, axes = plt.subplots(1, 3, figsize=(16, 4))
        
        axes[0].plot(epochs, losses, 'b-', linewidth=1.5)
        axes[0].set_xlabel('Epoch'); axes[0].set_ylabel('Loss')
        axes[0].set_title('Training Loss'); axes[0].grid(True, alpha=0.3)
        
        axes[1].plot(epochs, train_accs, 'r-', label='Train', linewidth=1.5)
        axes[1].plot(epochs, val_accs, 'g-', label='Val', linewidth=1.5)
        axes[1].set_xlabel('Epoch'); axes[1].set_ylabel('Accuracy')
        axes[1].set_title('Accuracy'); axes[1].grid(True, alpha=0.3)
        axes[1].legend(); axes[1].set_ylim([0, 1.05])
        
        axes[2].plot(epochs, lrs, 'm-', linewidth=1.5)
        axes[2].set_xlabel('Epoch'); axes[2].set_ylabel('LR')
        axes[2].set_title('Learning Rate'); axes[2].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
    
    def explain(self, result: PredictionResult):
        """详细解释"""
        print("\n" + "="*70)
        print("推理过程解释 v3.0")
        print("="*70)
        
        print(f"\n📋 目标关系: {result.target_relation}")
        print(f"📝 逻辑公式: {result.formula}")
        print(f"🏷️  语义类型: {result.semantic_type}")
        print(f"\n📊 最终置信度: {result.confidence:.4f}")
        print(f"🧠 符号推理置信度: {result.symbolic_confidence:.4f}")
        print(f"🔍 符号推理发现: {'✅ 是' if result.symbolic_found else '❌ 否'}")
        print(f"🎯 预测结果: {'✅ 成立' if result.prediction else '❌ 不成立'}")
        
        detail = result.inference_detail
        if detail:
            if detail.type_conflict:
                print(f"\n⚠️  检测到类型冲突（符号推理自动降低置信度）")
            if detail.partial_evidence:
                print(f"\n📎 存在部分证据（但不足以确认关系）")
            if detail.evidence:
                print(f"\n📚 证据链 ({len(detail.evidence)}条):")
                for i, e in enumerate(detail.evidence[:5]):
                    path = e.get('path', f"{e.get('subj','?')}-{e.get('obj','?')}")
                    print(f"  {i+1}. {path}")
            if detail.derived_facts:
                print(f"\n🔄 推导事实 ({len(detail.derived_facts)}个):")
                for f in list(detail.derived_facts)[:5]:
                    print(f"  • {f[0]}({f[1]}, {f[2]})")
        
        if result.known_facts:
            print(f"\n📥 已知事实 ({len(result.known_facts)}个):")
            for f in result.known_facts:
                print(f"  • {f[0]}({f[1]}, {f[2]})")
        
        if result.entities:
            print(f"\n👥 实体: {', '.join(result.entities)}")
        
        # 决策解释
        print(f"\n{'─'*70}")
        print("决策分析:")
        if result.confidence > 0.8:
            print("  高置信度预测 - 推理证据充分")
        elif result.confidence > 0.6:
            print("  中等置信度预测 - 证据较好但存在不确定性")
        elif result.confidence > 0.4:
            print("  边界预测 - 证据不足或存在矛盾")
            if result.symbolic_found and result.confidence < 0.5:
                print("  ⚠️ 符号引擎发现证据但融合模型降低了置信度")
        else:
            print("  低置信度预测 - 缺乏证据或存在类型冲突")
        
        print("─"*70)


# ============================================================================
# 数据生成 v3.0
# ============================================================================

def create_comprehensive_data() -> List[Dict]:
    """创建全面的训练数据"""
    system = LogicReasoningSystem("family", max_entities=10, max_seq_len=60)
    samples = []
    
    # ===== 正例 =====
    positives = [
        # Grandparent (2跳)
        ("John is Mary's father. Mary has a son named Tom.", 'Grandparent',
         [('Father','John','Mary'), ('Parent','Mary','Tom')]),
        ("David is Emma's father. Emma has a daughter Lisa.", 'Grandparent',
         [('Father','David','Emma'), ('Parent','Emma','Lisa')]),
        ("Anna is Bob's mother. Bob has a son Charlie.", 'Grandparent',
         [('Mother','Anna','Bob'), ('Parent','Bob','Charlie')]),
        ("Grandpa Henry has a son Michael. Michael has a daughter Sarah.", 'Grandparent',
         [('Father','Henry','Michael'), ('Parent','Michael','Sarah')]),
        
        # Spouse (对称)
        ("Alice and Bob are married.", 'Spouse', [('Spouse','Alice','Bob')]),
        ("Sarah is Thomas's wife.", 'Spouse', [('Spouse','Sarah','Thomas')]),
        ("Diana and Charles are a married couple.", 'Spouse', [('Spouse','Diana','Charles')]),
        
        # Sibling (共享父母)
        ("George and Helen are brother and sister.", 'Sibling',
         [('Sibling','George','Helen'), ('Father','John','George'), ('Father','John','Helen')]),
        ("Lisa and Karen are sisters.", 'Sibling',
         [('Sibling','Lisa','Karen'), ('Mother','Mary','Lisa'), ('Mother','Mary','Karen')]),
        ("Mike and Steve are brothers.", 'Sibling',
         [('Sibling','Mike','Steve'), ('Parent','Bob','Mike'), ('Parent','Bob','Steve')]),
        
        # Parent (直接)
        ("Michael is Jennifer's father.", 'Parent', [('Father','Michael','Jennifer')]),
        ("Mary is the mother of Tom.", 'Parent', [('Mother','Mary','Tom')]),
        ("Robert is Susan's father.", 'Parent', [('Father','Robert','Susan')]),
        
        # Child
        ("Tom is Mary's son.", 'Child', [('Son','Tom','Mary')]),
        ("Lisa is Anna's daughter.", 'Child', [('Daughter','Lisa','Anna')]),
        
        # Ancestor (多跳)
        ("John is Mary's father. Mary has a son Tom.", 'Ancestor',
         [('Father','John','Mary'), ('Parent','Mary','Tom')]),
        ("Grandma Alice has a daughter Barbara. Barbara has a son Charlie.", 'Ancestor',
         [('Mother','Alice','Barbara'), ('Parent','Barbara','Charlie')]),
        ("Henry is Michael's father. Michael is Sarah's father. Sarah has a son James.", 'Ancestor',
         [('Father','Henry','Michael'), ('Father','Michael','Sarah'), ('Parent','Sarah','James')]),
        
        # Brother/Sister
        ("James is Emma's brother.", 'Brother', [('Brother','James','Emma')]),
        ("Grace is Kevin's sister.", 'Sister', [('Sister','Grace','Kevin')]),
    ]
    
    # ===== 负例 =====
    negatives = [
        # 兄弟不是父母
        ("George is Helen's brother. Helen has a son Ian.", 'Parent',
         [('Sibling','George','Helen'), ('Parent','Helen','Ian')]),
        ("Mike is Steve's brother. Steve has a daughter.", 'Parent',
         [('Sibling','Mike','Steve')]),
        
        # 同事关系混淆
        ("Karen and Lisa are colleagues at work.", 'Sibling',
         [('Colleague','Karen','Lisa')]),
        ("David and Emma work together on the same team.", 'Sibling',
         [('Colleague','David','Emma')]),
        ("Michael works with Jennifer in the office.", 'Spouse',
         [('Colleague','Michael','Jennifer')]),
        ("Robert is Susan's manager at the company.", 'Parent',
         [('Manager','Robert','Susan')]),
        ("Linda manages a team of ten people at work.", 'Parent', []),
        
        # 朋友关系混淆
        ("Sarah and Thomas are friends from college.", 'Sibling',
         [('Friend','Sarah','Thomas')]),
        ("Bob and Frank are old friends from the neighborhood.", 'Sibling',
         [('Friend','Bob','Frank')]),
        ("Sarah and Thomas are good friends, nothing more.", 'Spouse',
         [('Friend','Sarah','Thomas')]),
        
        # 反向关系错误
        ("John is Mary's father.", 'Child',
         [('Father','John','Mary')]),
        ("Mary is Tom's mother, not his child.", 'Child',
         [('Mother','Mary','Tom')]),
        
        # 跨度不够
        ("Alice is Bob's mother. Bob is Charlie's father.", 'Sibling',
         [('Mother','Alice','Bob'), ('Father','Bob','Charlie')]),
        ("Michael is Jennifer's father.", 'Grandparent',
         [('Father','Michael','Jennifer')]),
        
        # 职业关系不是家庭关系
        ("John is Mary's manager at the office.", 'Child',
         [('Manager','John','Mary')]),
        ("Lisa works as Karen's employee.", 'Parent',
         [('Employee','Lisa','Karen')]),
    ]
    
    for text, rel, facts in positives:
        s = system.create_sample(text, rel, facts)
        s['is_true'] = True
        samples.append(s)
    
    for text, rel, facts in negatives:
        s = system.create_sample(text, rel, facts)
        s['is_true'] = False
        samples.append(s)
    
    return samples


# ============================================================================
# 演示
# ============================================================================

def demo():
    print("="*70)
    print("混合逻辑推理系统 v3.0 Final")
    print("基于符号规则引擎 + 神经网络融合")
    print("="*70)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"设备: {device}")
    
    torch.manual_seed(42)
    np.random.seed(42)
    random.seed(42)
    
    system = LogicReasoningSystem("family", max_entities=10, max_seq_len=60)
    data = create_comprehensive_data()
    
    pos_count = sum(1 for s in data if s['is_true'])
    neg_count = sum(1 for s in data if not s['is_true'])
    print(f"\n数据集: {len(data)} 样本 (正例: {pos_count}, 负例: {neg_count})")
    
    model = system.init_model()
    print(f"模型参数: {sum(p.numel() for p in model.parameters()):,}")
    
    # 符号引擎测试
    print("\n" + "="*70)
    print("符号引擎验证")
    print("="*70)
    
    reng = SymbolicRuleEngine()
    test_cases_sym = [
        ('Grandparent', [('Father','John','Mary'),('Parent','Mary','Tom')], True),
        ('Ancestor', [('Father','John','Mary'),('Parent','Mary','Tom'),('Parent','Tom','Alice')], True),
        ('Child', [('Father','John','Mary')], True),
        ('Child', [('Manager','John','Mary')], False),
        ('Parent', [('Colleague','A','B')], False),
        ('Sibling', [('Sibling','A','B'),('Father','X','A'),('Father','X','B')], True),
        ('Sibling', [('Colleague','A','B')], False),
    ]
    
    for rel, facts, expected in test_cases_sym:
        r = reng.infer(rel, facts, ['John','Mary','Tom','Alice','A','B','X'])
        ok = r.found == expected
        detail = ""
        if r.type_conflict: detail = " [类型冲突]"
        if r.partial_evidence: detail = " [部分证据]"
        print(f"  {'✅' if ok else '❌'} {rel:12s} found={r.found} conf={r.confidence:.3f}{detail}")
    
    # 训练
    print("\n" + "="*70)
    print("模型训练")
    print("="*70)
    
    system.train(data, epochs=120, lr=0.001, batch_size=4, val_split=0.15)
    system.plot_history()
    
    # 测试
    print("\n" + "="*70)
    print("综合测试")
    print("="*70)
    
    tests = [
        ("Michael is Jennifer's father. Jennifer has a son named Kevin.", 'Grandparent',
         [('Father','Michael','Jennifer'), ('Parent','Jennifer','Kevin')], True),
        ("Sarah and Thomas are married.", 'Spouse',
         [('Spouse','Sarah','Thomas')], True),
        ("David and Emma are brother and sister.", 'Sibling',
         [('Sibling','David','Emma'), ('Father','John','David'), ('Father','John','Emma')], True),
        ("Robert and Susan work in the same office.", 'Sibling',
         [('Colleague','Robert','Susan')], False),
        ("Lisa is Karen's manager at the company.", 'Parent',
         [('Manager','Lisa','Karen')], False),
        ("John is Mary's manager, not her father.", 'Child',
         [('Manager','John','Mary')], False),
        ("John is Mary's father. Mary has a son Tom. Tom has a daughter Alice.", 'Ancestor',
         [('Father','John','Mary'), ('Parent','Mary','Tom'), ('Parent','Tom','Alice')], True),
        ("Alice is Bob's mother. Bob is Charlie's father.", 'Sibling',
         [('Mother','Alice','Bob'), ('Father','Bob','Charlie')], False),
        ("Michael is Jennifer's father.", 'Grandparent',
         [('Father','Michael','Jennifer')], False),
        ("Linda manages a team at work. She is not anyone's mother here.", 'Parent',
         [], False),
        ("Henry is Michael's father. Michael is Sarah's father. Sarah has a son James.", 'Ancestor',
         [('Father','Henry','Michael'), ('Father','Michael','Sarah'), ('Parent','Sarah','James')], True),
        ("Bob and Frank are old friends from college.", 'Sibling',
         [('Friend','Bob','Frank')], False),
    ]
    
    correct = 0
    results_detail = []
    
    for i, (text, rel, facts, expected) in enumerate(tests):
        result = system.predict(text, rel, facts)
        ok = result.prediction == expected
        if ok: correct += 1
        
        status = "✅" if ok else "❌"
        boundary = "⚠️" if 0.35 < result.confidence < 0.65 else "  "
        
        print(f"{status}{boundary} 测试{i+1:2d}: {rel:12s} | "
              f"期望:{'True ' if expected else 'False':5s} | "
              f"预测:{'True ' if result.prediction else 'False':5s} | "
              f"置信度:{result.confidence:.4f} | 符号:{result.symbolic_confidence:.4f}")
        
        if not ok:
            results_detail.append(result)
    
    acc = correct / len(tests)
    print(f"\n{'='*70}")
    print(f"准确率: {correct}/{len(tests)} = {acc:.2%}")
    
    if acc >= 0.90:
        print("🎉 优秀！系统达到90%以上准确率")
    elif acc >= 0.80:
        print("👍 良好！系统达到80%以上准确率")
    else:
        print("🔧 需要进一步优化")
    
    print(f"{'='*70}")
    
    # 错误分析
    if results_detail:
        print(f"\n{'='*70}")
        print(f"错误案例分析 ({len(results_detail)}个)")
        print(f"{'='*70}")
        for i, result in enumerate(results_detail):
            system.explain(result)
    
    # 正确案例示例
    print(f"\n{'='*70}")
    print("正确案例示例 - Ancestor推理")
    print(f"{'='*70}")
    result_ok = system.predict(
        "John is Mary's father. Mary has a son Tom. Tom has a daughter Alice.",
        'Ancestor',
        [('Father','John','Mary'), ('Parent','Mary','Tom'), ('Parent','Tom','Alice')]
    )
    system.explain(result_ok)
    
    return system, data


if __name__ == "__main__":
    system, data = demo()