"""
混合逻辑推理系统 v2.5
优化：精确的符号推理 + 更好的关系语义理解
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import numpy as np
import re
import math
from typing import List, Dict, Tuple, Any, Optional, Set
from collections import OrderedDict
import random
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')


# ============================================================================
# 精确的符号规则引擎
# ============================================================================

class SymbolicRuleEngine:
    """
    精确的符号规则引擎
    
    关键设计原则：
    1. 区分"语义蕴含"和"直接断言"
    2. 推理链有明确的置信度衰减
    3. 区分不同关系类型（家庭/职业/社交）
    """
    
    # 关系类型分类
    FAMILY_DIRECT = {'Father', 'Mother', 'Son', 'Daughter', 'Brother', 'Sister'}
    FAMILY_DERIVED = {'Parent', 'Child', 'Spouse', 'Sibling'}
    FAMILY_EXTENDED = {'Grandparent', 'Grandchild', 'Ancestor', 'Descendant'}
    PROFESSIONAL = {'Colleague', 'Manager', 'Employee'}
    SOCIAL = {'Friend', 'Neighbor'}
    
    # 语义等价映射（双向）
    SEMANTIC_EQUIVALENCE = {
        # Father(x,y) 语义上蕴含 Parent(x,y) 和 Child(y,x)
        'Father': {'implies': ['Parent'], 'inverse_implies': ['Child']},
        'Mother': {'implies': ['Parent'], 'inverse_implies': ['Child']},
        'Son': {'implies': ['Child'], 'inverse_implies': ['Parent']},
        'Daughter': {'implies': ['Child'], 'inverse_implies': ['Parent']},
        'Brother': {'implies': ['Sibling']},
        'Sister': {'implies': ['Sibling']},
    }
    
    # 对称关系
    SYMMETRIC = {'Spouse', 'Sibling', 'Colleague', 'Friend'}
    
    def __init__(self):
        pass
    
    def get_relation_type(self, relation: str) -> str:
        if relation in self.FAMILY_DIRECT:
            return 'family_direct'
        elif relation in self.FAMILY_DERIVED:
            return 'family_derived'
        elif relation in self.FAMILY_EXTENDED:
            return 'family_extended'
        elif relation in self.PROFESSIONAL:
            return 'professional'
        elif relation in self.SOCIAL:
            return 'social'
        return 'unknown'
    
    def infer(self, target_relation: str, facts: List[Tuple], 
              entities: List[str]) -> Dict[str, Any]:
        """
        推理目标关系
        
        返回：
        - found: 是否找到
        - confidence: 符号推理置信度
        - evidence: 证据链
        - derived_facts: 推导出的事实
        """
        kg = set(facts)
        target_type = self.get_relation_type(target_relation)
        
        # Step 1: 扩展知识图谱（单步推导）
        derived = self._derive_facts(kg)
        all_facts = kg | derived
        
        # Step 2: 针对目标关系进行推理
        if target_relation in self.FAMILY_EXTENDED:
            # 多跳推理
            result = self._check_extended_relation(target_relation, all_facts, entities)
        elif target_relation in self.FAMILY_DIRECT or target_relation in self.FAMILY_DERIVED:
            # 直接匹配或推导
            result = self._check_direct_relation(target_relation, all_facts, entities, kg)
        elif target_relation in self.SYMMETRIC:
            # 对称关系检查
            result = self._check_symmetric_relation(target_relation, all_facts, entities)
        else:
            # 通用检查
            result = self._check_general_relation(target_relation, all_facts, entities)
        
        # Step 3: 类型不匹配惩罚
        result = self._apply_type_check(result, target_relation, target_type, kg, facts)
        
        return result
    
    def _derive_facts(self, kg: Set[Tuple]) -> Set[Tuple]:
        """从已知事实推导新事实"""
        derived = set()
        
        for pred, subj, obj in kg:
            # 应用语义等价规则
            if pred in self.SEMANTIC_EQUIVALENCE:
                rules = self.SEMANTIC_EQUIVALENCE[pred]
                # 蕴含关系
                for implied in rules.get('implies', []):
                    derived.add((implied, subj, obj))
                # 逆蕴含关系
                for inv_implied in rules.get('inverse_implies', []):
                    derived.add((inv_implied, obj, subj))
            
            # 对称关系
            if pred in self.SYMMETRIC:
                derived.add((pred, obj, subj))
        
        return derived
    
    def _check_extended_relation(self, target: str, kg: Set[Tuple], 
                                  entities: List[str]) -> Dict:
        """检查扩展关系（多跳）"""
        if target == 'Grandparent':
            return self._check_grandparent(kg, entities)
        elif target == 'Grandchild':
            return self._check_grandchild(kg, entities)
        elif target == 'Ancestor':
            return self._check_ancestor(kg, entities)
        elif target == 'Descendant':
            return self._check_descendant(kg, entities)
        
        return {'found': False, 'confidence': 0.15, 'evidence': []}
    
    def _check_grandparent(self, kg: Set[Tuple], entities: List[str]) -> Dict:
        """Grandparent(x,y) = ∃z: Parent(x,z) ∧ Parent(z,y)"""
        evidence = []
        parents = {}  # entity -> set of parents
        
        for pred, subj, obj in kg:
            if pred in ('Father', 'Mother', 'Parent'):
                if obj not in parents:
                    parents[obj] = set()
                parents[obj].add(subj)
        
        for z in parents:
            for x in parents[z]:
                for y in entities:
                    if y != x and y != z:
                        # 检查 z 是否是 y 的父辈
                        for pred2, subj2, obj2 in kg:
                            if subj2 == z and obj2 == y and pred2 in ('Father', 'Mother', 'Parent'):
                                evidence.append({
                                    'type': 'grandparent',
                                    'x': x, 'z': z, 'y': y,
                                    'path': f'{x} -> Parent -> {z} -> Parent -> {y}'
                                })
        
        if evidence:
            return {
                'found': True,
                'confidence': 0.80,
                'evidence': evidence,
                'match_count': len(evidence)
            }
        
        # 部分证据
        if parents:
            return {'found': False, 'confidence': 0.25, 'evidence': [], 
                    'partial': 'has_parent_info'}
        
        return {'found': False, 'confidence': 0.10, 'evidence': []}
    
    def _check_grandchild(self, kg: Set[Tuple], entities: List[str]) -> Dict:
        """Grandchild(x,y) = Grandparent(y,x)"""
        result = self._check_grandparent(kg, entities)
        if result['found']:
            # 交换主体
            new_evidence = []
            for e in result['evidence']:
                new_evidence.append({
                    'type': 'grandchild',
                    'x': e['y'], 'y': e['x'],
                    'path': f"{e['y']} -> Parent -> {e['z']} -> Parent -> {e['x']}"
                })
            result['evidence'] = new_evidence
        
        return result
    
    def _check_ancestor(self, kg: Set[Tuple], entities: List[str]) -> Dict:
        """Ancestor(x,y) = Parent+(x,y)"""
        evidence = []
        
        # 构建Parent图
        parent_of = {}  # x -> set of y where Parent(x,y)
        for pred, subj, obj in kg:
            if pred in ('Father', 'Mother', 'Parent'):
                if subj not in parent_of:
                    parent_of[subj] = set()
                parent_of[subj].add(obj)
        
        # 对每对实体检查传递闭包
        for x in entities:
            if x in parent_of:
                descendants = self._get_descendants(x, parent_of, set(), 0)
                for y, depth in descendants.items():
                    if y != x and y in entities:
                        evidence.append({
                            'type': 'ancestor',
                            'x': x, 'y': y, 'depth': depth,
                            'path': f'{x} --{depth}步--> {y}'
                        })
        
        if evidence:
            # 根据最短路径深度调整置信度
            min_depth = min(e['depth'] for e in evidence)
            if min_depth == 1:
                conf = 0.70
            elif min_depth == 2:
                conf = 0.85
            else:
                conf = 0.95
            
            return {
                'found': True,
                'confidence': conf,
                'evidence': evidence,
                'match_count': len(evidence)
            }
        
        if parent_of:
            return {'found': False, 'confidence': 0.20, 'evidence': [],
                    'partial': 'has_parent_info'}
        
        return {'found': False, 'confidence': 0.10, 'evidence': []}
    
    def _get_descendants(self, node: str, parent_of: Dict, 
                         visited: Set[str], depth: int) -> Dict[str, int]:
        """递归获取所有后代"""
        if depth > 5 or node in visited:
            return {}
        
        visited.add(node)
        descendants = {}
        
        if node in parent_of:
            for child in parent_of[node]:
                if child not in visited:
                    descendants[child] = depth + 1
                    deeper = self._get_descendants(child, parent_of, visited.copy(), depth + 1)
                    for d, dd in deeper.items():
                        if d not in descendants or dd < descendants[d]:
                            descendants[d] = dd
        
        return descendants
    
    def _check_descendant(self, kg: Set[Tuple], entities: List[str]) -> Dict:
        """Descendant(x,y) = Ancestor(y,x)"""
        result = self._check_ancestor(kg, entities)
        if result['found']:
            for e in result['evidence']:
                e['x'], e['y'] = e['y'], e['x']
                e['type'] = 'descendant'
        return result
    
    def _check_direct_relation(self, target: str, all_facts: Set[Tuple], 
                                entities: List[str], original_kg: Set[Tuple]) -> Dict:
        """检查直接关系和语义推导关系"""
        evidence = []
        
        # 1. 直接匹配
        for pred, subj, obj in all_facts:
            if pred == target:
                # 判断是直接事实还是推导的
                is_direct = (pred, subj, obj) in original_kg
                evidence.append({
                    'type': 'direct' if is_direct else 'derived',
                    'pred': pred, 'subj': subj, 'obj': obj,
                    'is_direct': is_direct
                })
        
        if evidence:
            # 直接事实置信度更高
            direct_count = sum(1 for e in evidence if e['is_direct'])
            derived_count = sum(1 for e in evidence if not e['is_direct'])
            
            if direct_count > 0:
                conf = min(0.95, 0.70 + 0.1 * direct_count)
            else:
                # 仅推导出的，置信度降低
                conf = min(0.70, 0.40 + 0.1 * derived_count)
            
            return {
                'found': True,
                'confidence': conf,
                'evidence': evidence,
                'direct_count': direct_count,
                'derived_count': derived_count
            }
        
        # 2. 检查语义蕴含
        # 例如：Father蕴含Parent, Child蕴含Parent(逆)
        if target == 'Parent':
            for pred, subj, obj in all_facts:
                if pred in ('Father', 'Mother'):
                    evidence.append({
                        'type': 'semantic',
                        'pred': pred, 'subj': subj, 'obj': obj,
                        'note': f'{pred}蕴含Parent'
                    })
            if evidence:
                return {
                    'found': True,
                    'confidence': 0.75,
                    'evidence': evidence,
                    'note': '通过语义蕴含推导'
                }
        
        elif target == 'Child':
            for pred, subj, obj in all_facts:
                if pred in ('Father', 'Mother') and obj in entities:
                    evidence.append({
                        'type': 'semantic_inverse',
                        'pred': pred, 'subj': obj, 'obj': subj,
                        'note': f'{pred}({subj},{obj}) 蕴含 Child({obj},{subj})'
                    })
            if evidence:
                return {
                    'found': True,
                    'confidence': 0.65,
                    'evidence': evidence,
                    'note': '通过逆语义蕴含推导'
                }
        
        # 3. 部分证据
        if target in ('Parent', 'Child'):
            for pred, subj, obj in all_facts:
                if pred in ('Father', 'Mother', 'Son', 'Daughter'):
                    return {
                        'found': False,
                        'confidence': 0.20,
                        'evidence': [],
                        'partial': 'has_family_info'
                    }
        
        return {'found': False, 'confidence': 0.10, 'evidence': []}
    
    def _check_symmetric_relation(self, target: str, all_facts: Set[Tuple], 
                                   entities: List[str]) -> Dict:
        """检查对称关系"""
        evidence = []
        
        for pred, subj, obj in all_facts:
            if pred == target:
                evidence.append({'subj': subj, 'obj': obj})
            elif pred == target and (obj, subj, pred) in all_facts:
                evidence.append({'subj': obj, 'obj': subj})
        
        if evidence:
            return {
                'found': True,
                'confidence': min(0.90, 0.60 + 0.1 * len(evidence)),
                'evidence': evidence
            }
        
        return {'found': False, 'confidence': 0.10, 'evidence': []}
    
    def _check_general_relation(self, target: str, all_facts: Set[Tuple], 
                                 entities: List[str]) -> Dict:
        """通用关系检查"""
        for pred, subj, obj in all_facts:
            if pred == target:
                return {'found': True, 'confidence': 0.70, 'evidence': [(subj, obj)]}
        
        return {'found': False, 'confidence': 0.10, 'evidence': []}
    
    def _apply_type_check(self, result: Dict, target: str, target_type: str,
                           all_facts: Set[Tuple], original_facts: Set[Tuple]) -> Dict:
        """应用类型不匹配检查"""
        
        # 提取原始事实中的关系类型
        fact_types = set()
        for pred, _, _ in original_facts:
            fact_types.add(self.get_relation_type(pred))
        
        # 检查类型冲突
        type_conflicts = {
            ('family_direct', 'professional'): True,
            ('family_derived', 'professional'): True,
            ('family_extended', 'professional'): True,
            ('professional', 'family_direct'): True,
            ('professional', 'family_derived'): True,
            ('professional', 'family_extended'): True,
        }
        
        for ft in fact_types:
            if (target_type, ft) in type_conflicts:
                # 类型冲突：大幅降低置信度
                result['confidence'] = min(result['confidence'], 0.05)
                result['type_conflict'] = True
                result['conflict_detail'] = f'{target_type} vs {ft}'
                break
        
        return result


# ============================================================================
# 混合推理模型
# ============================================================================

class HybridReasoner(nn.Module):
    """混合推理器"""
    
    def __init__(self, vocab_size, num_predicates, num_constants,
                 embed_dim=64, hidden_dim=128, max_entities=10, max_seq_len=50):
        super().__init__()
        
        # 文本编码器
        self.text_embedding = nn.Embedding(vocab_size, embed_dim)
        self.text_lstm = nn.LSTM(embed_dim, hidden_dim // 2, batch_first=True, bidirectional=True)
        self.text_proj = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.LayerNorm(hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.3)
        )
        
        # 符号规则引擎
        self.rule_engine = SymbolicRuleEngine()
        
        # 语义特征提取器：从文本中提取关系线索
        self.semantic_extractor = nn.Sequential(
            nn.Linear(hidden_dim // 2, 64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, 3)  # family / professional / social / uncertain
        )
        
        # 融合网络
        # 输入: text_feat(hidden//2) + sym_conf(1) + sym_found(1) + semantic_type(3)
        input_dim = hidden_dim // 2 + 1 + 1 + 3
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
    
    def encode_text(self, tokens):
        emb = self.text_embedding(tokens)
        _, (h, _) = self.text_lstm(emb)
        h = torch.cat([h[0], h[1]], dim=-1)
        return self.text_proj(h)
    
    def forward(self, text_tokens, target_relations, facts_list, entities_list):
        batch_size = text_tokens.size(0)
        device = text_tokens.device
        
        # 1. 文本编码
        text_feat = self.encode_text(text_tokens)
        
        # 2. 语义类型预测
        semantic_logits = self.semantic_extractor(text_feat)
        semantic_probs = F.softmax(semantic_logits, dim=-1)
        
        # 3. 符号推理
        sym_confs = torch.zeros(batch_size, device=device)
        sym_founds = torch.zeros(batch_size, device=device)
        
        for i in range(batch_size):
            rel = target_relations[i]
            facts = facts_list[i] if i < len(facts_list) else []
            entities = entities_list[i] if i < len(entities_list) else []
            
            result = self.rule_engine.infer(rel, facts, entities)
            sym_confs[i] = result['confidence']
            sym_founds[i] = 1.0 if result['found'] else 0.0
        
        # 4. 融合
        combined = torch.cat([
            text_feat,
            sym_confs.unsqueeze(1),
            sym_founds.unsqueeze(1),
            semantic_probs
        ], dim=-1)
        
        confidence = self.fusion(combined).squeeze(-1)
        
        return {
            'confidence': confidence,
            'symbolic_confidence': sym_confs,
            'symbolic_found': sym_founds,
            'semantic_type': semantic_probs
        }


# ============================================================================
# 主系统
# ============================================================================

class LogicReasoningSystem:
    """混合逻辑推理系统 v2.5"""
    
    def __init__(self, domain="family", max_entities=10, max_seq_len=60):
        self.domain = domain
        self.max_entities = max_entities
        self.max_seq_len = max_seq_len
        self.vocab_size = 1000
        self.predicate_map = {}
        self.model = None
        self.entity_vocab = set()
        self.training_history = []
        
        self._init_knowledge()
    
    def _init_knowledge(self):
        predicates = [
            'Father', 'Mother', 'Parent', 'Child', 'Spouse', 'Sibling',
            'Grandparent', 'Grandchild', 'Ancestor', 'Descendant',
            'Brother', 'Sister', 'Son', 'Daughter',
            'Colleague', 'Manager', 'Friend'
        ]
        self.predicate_map = {p: i for i, p in enumerate(sorted(predicates))}
    
    def extract_entities(self, text):
        entities = re.findall(r'\b[A-Z][a-z]+\b', text)
        entities = list(OrderedDict.fromkeys(entities))[:self.max_entities]
        
        male = {'John','Michael','David','Robert','Thomas','George','Bob','Frank',
                'Kevin','Ian','James','William','Richard','Charles','Joseph','Daniel',
                'Matthew','Anthony','Mark','Tom','Jerry','Mike','Steve','Charlie'}
        female = {'Mary','Jennifer','Alice','Emma','Sarah','Helen','Karen','Lisa',
                  'Carol','Grace','Linda','Barbara','Susan','Jessica','Nancy','Betty',
                  'Margaret','Dorothy','Anna'}
        
        types = {}
        for e in entities:
            if e in male: types[e] = 'Male'
            elif e in female: types[e] = 'Female'
            else: types[e] = 'Unknown'
        
        self.entity_vocab.update(entities)
        
        return {
            'entities': entities,
            'types': types,
            'count': len(entities)
        }
    
    def text_to_tokens(self, text):
        tokens = [ord(c) % self.vocab_size for c in text[:self.max_seq_len]]
        while len(tokens) < self.max_seq_len:
            tokens.append(0)
        return torch.tensor(tokens, dtype=torch.long).unsqueeze(0)
    
    def create_sample(self, text, target_rel, facts=None):
        info = self.extract_entities(text)
        return {
            'text': text,
            'text_tokens': self.text_to_tokens(text),
            'entities': info['entities'],
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
    
    def train(self, data, epochs=100, lr=0.001, batch_size=4):
        if self.model is None:
            self.init_model()
        
        optimizer = optim.AdamW(self.model.parameters(), lr=lr, weight_decay=0.01)
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
        criterion = nn.BCELoss()
        
        self.model.train()
        best_loss = float('inf')
        best_state = None
        patience = 25
        p_counter = 0
        
        print(f"\n训练: lr={lr}, epochs={epochs}")
        
        for epoch in range(epochs):
            total_loss = 0
            correct_hybrid = 0
            correct_sym = 0
            total = 0
            
            random.shuffle(data)
            
            for i in range(0, len(data), batch_size):
                batch = data[i:i+batch_size]
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
                    
                    # 双重损失
                    fusion_loss = criterion(conf, targets)
                    sym_loss = criterion(
                        torch.clamp(sym_conf, 0.001, 0.999), targets
                    )
                    loss = fusion_loss + 0.3 * sym_loss
                    
                    optimizer.zero_grad()
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                    optimizer.step()
                    
                    total_loss += loss.item()
                    
                    preds = (conf > 0.5).float()
                    sym_preds = (sym_conf > 0.5).float()
                    correct_hybrid += (preds == targets).sum().item()
                    correct_sym += (sym_preds == targets).sum().item()
                    total += len(targets)
                    
                except Exception as e:
                    continue
            
            scheduler.step()
            
            if total > 0:
                acc_h = correct_hybrid / total
                acc_s = correct_sym / total
                avg_loss = total_loss / max(1, len(data) // batch_size)
                
                self.training_history.append({
                    'epoch': epoch, 'loss': avg_loss,
                    'accuracy': acc_h, 'symbolic_accuracy': acc_s
                })
                
                if avg_loss < best_loss - 1e-4:
                    best_loss = avg_loss
                    p_counter = 0
                    best_state = {k: v.cpu().clone() for k, v in self.model.state_dict().items()}
                else:
                    p_counter += 1
                
                if epoch % 20 == 0:
                    print(f'Epoch {epoch:3d} | Loss: {avg_loss:.4f} | '
                          f'Acc: {acc_h:.4f} | Sym: {acc_s:.4f}')
                
                if p_counter >= patience:
                    print(f"早停于epoch {epoch}")
                    break
        
        if best_state:
            self.model.load_state_dict(best_state)
    
    def predict(self, text, target_rel, facts=None):
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
        
        # 获取符号推理详情
        rule_engine = self.model.rule_engine
        detail = rule_engine.infer(target_rel, facts or [], sample['entities'])
        
        return {
            'confidence': conf,
            'symbolic_confidence': sym_conf,
            'symbolic_found': sym_found,
            'symbolic_detail': detail,
            'prediction': conf > 0.5,
            'entities': sample['entities'],
            'formula': self._get_formula(target_rel),
            'known_facts': facts or [],
            'target_relation': target_rel,
        }
    
    def _get_formula(self, target_rel):
        formulas = {
            'Parent': 'Father(x,y) ∨ Mother(x,y)',
            'Grandparent': '∃z: Parent(x,z) ∧ Parent(z,y)',
            'Sibling': '∃p: Parent(p,x) ∧ Parent(p,y)',
            'Spouse': 'Spouse(x,y)',
            'Ancestor': 'Parent+(x,y)',
            'Child': '∃p: p ∈ {Father,Mother} ∧ p(y,x)',
        }
        return formulas.get(target_rel, f'{target_rel}(x,y)')
    
    def plot_history(self):
        if not self.training_history:
            print("无训练历史")
            return
        
        epochs = [x['epoch'] for x in self.training_history]
        losses = [x['loss'] for x in self.training_history]
        accs = [x['accuracy'] for x in self.training_history]
        sym_accs = [x.get('symbolic_accuracy', 0) for x in self.training_history]
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
        
        ax1.plot(epochs, losses, 'b-')
        ax1.set_xlabel('Epoch'); ax1.set_ylabel('Loss')
        ax1.set_title('Training Loss'); ax1.grid(True, alpha=0.3)
        
        ax2.plot(epochs, accs, 'r-', label='Hybrid')
        ax2.plot(epochs, sym_accs, 'g--', label='Symbolic')
        ax2.set_xlabel('Epoch'); ax2.set_ylabel('Accuracy')
        ax2.set_title('Accuracy'); ax2.grid(True, alpha=0.3)
        ax2.legend(); ax2.set_ylim([0, 1.05])
        
        plt.tight_layout()
        plt.show()
    
    def explain(self, result):
        print("\n" + "="*60)
        print("推理过程解释")
        print("="*60)
        print(f"\n目标关系: {result['target_relation']}")
        print(f"逻辑公式: {result['formula']}")
        print(f"\n最终置信度: {result['confidence']:.4f}")
        print(f"符号推理置信度: {result['symbolic_confidence']:.4f}")
        print(f"符号推理发现: {'是' if result['symbolic_found'] else '否'}")
        print(f"预测结果: {'✓ 成立' if result['prediction'] else '✗ 不成立'}")
        
        detail = result.get('symbolic_detail', {})
        if detail.get('evidence'):
            print(f"\n证据 ({len(detail['evidence'])}条):")
            for e in detail['evidence'][:5]:
                if isinstance(e, dict):
                    print(f"  • {e.get('path', str(e))}")
                else:
                    print(f"  • {e}")
        
        if detail.get('type_conflict'):
            print(f"\n⚠️ 类型冲突: {detail.get('conflict_detail', '')}")
        
        if detail.get('partial'):
            print(f"\n📎 部分证据: {detail['partial']}")
        
        if result['known_facts']:
            print(f"\n已知事实 ({len(result['known_facts'])}个):")
            for f in result['known_facts']:
                print(f"  • {f[0]}({f[1]}, {f[2]})")
        
        if result['entities']:
            print(f"\n实体: {', '.join(result['entities'])}")


# ============================================================================
# 数据生成
# ============================================================================

def create_data():
    system = LogicReasoningSystem("family", max_entities=10, max_seq_len=60)
    samples = []
    
    positives = [
        ("John is Mary's father. Mary has a son named Tom.", 'Grandparent',
         [('Father','John','Mary'), ('Parent','Mary','Tom')]),
        ("David is Emma's father. Emma has a daughter Lisa.", 'Grandparent',
         [('Father','David','Emma'), ('Parent','Emma','Lisa')]),
        ("Anna is Bob's mother. Bob has a son Charlie.", 'Grandparent',
         [('Mother','Anna','Bob'), ('Parent','Bob','Charlie')]),
        ("Alice and Bob are married.", 'Spouse',
         [('Spouse','Alice','Bob')]),
        ("Sarah is Thomas's wife.", 'Spouse',
         [('Spouse','Sarah','Thomas')]),
        ("George and Helen are brother and sister.", 'Sibling',
         [('Sibling','George','Helen')]),
        ("Lisa and Karen are sisters.", 'Sibling',
         [('Sibling','Lisa','Karen')]),
        ("Michael is Jennifer's father.", 'Parent',
         [('Father','Michael','Jennifer')]),
        ("Mary is the mother of Tom.", 'Parent',
         [('Mother','Mary','Tom')]),
        ("Tom is Mary's son.", 'Child',
         [('Son','Tom','Mary')]),
        ("John is Mary's father. Mary has a son Tom.", 'Ancestor',
         [('Father','John','Mary'), ('Parent','Mary','Tom')]),
        ("Grandma Alice has a daughter Barbara. Barbara has a son Charlie.", 'Ancestor',
         [('Mother','Alice','Barbara'), ('Parent','Barbara','Charlie')]),
        ("James is Emma's brother.", 'Brother',
         [('Brother','James','Emma')]),
        ("Grace is Kevin's sister.", 'Sister',
         [('Sister','Grace','Kevin')]),
    ]
    
    negatives = [
        ("George is Helen's brother. Helen has a son Ian.", 'Parent',
         [('Sibling','George','Helen'), ('Parent','Helen','Ian')]),
        ("Karen and Lisa are colleagues at work.", 'Sibling',
         [('Colleague','Karen','Lisa')]),
        ("David and Emma work together.", 'Sibling',
         [('Colleague','David','Emma')]),
        ("Michael works with Jennifer.", 'Spouse',
         [('Colleague','Michael','Jennifer')]),
        ("Robert is Susan's manager.", 'Parent',
         [('Manager','Robert','Susan')]),
        ("Sarah and Thomas are friends from college.", 'Sibling',
         [('Friend','Sarah','Thomas')]),
        ("Bob and Frank are old friends.", 'Sibling',
         [('Friend','Bob','Frank')]),
        ("Sarah and Thomas are good friends.", 'Spouse',
         [('Friend','Sarah','Thomas')]),
        # 修复：Child负例 - Father意味着Child(y,x)成立，所以这里用非家庭关系
        ("John is Mary's manager.", 'Child',
         [('Manager','John','Mary')]),
        ("Alice is Bob's mother. Bob is Charlie's father.", 'Sibling',
         [('Mother','Alice','Bob'), ('Father','Bob','Charlie')]),
        ("Michael is Jennifer's father.", 'Grandparent',
         [('Father','Michael','Jennifer')]),
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
    print("="*60)
    print("混合逻辑推理系统 v2.5")
    print("="*60)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"设备: {device}")
    
    torch.manual_seed(42)
    np.random.seed(42)
    random.seed(42)
    
    system = LogicReasoningSystem("family", max_entities=10, max_seq_len=60)
    data = create_data()
    print(f"\n样本: {len(data)} (正:{sum(1 for s in data if s['is_true'])} 负:{sum(1 for s in data if not s['is_true'])})")
    
    model = system.init_model()
    print(f"参数: {sum(p.numel() for p in model.parameters()):,}")
    
    # 测试符号引擎
    print("\n--- 符号引擎测试 ---")
    reng = SymbolicRuleEngine()
    for rel, facts, expected in [
        ('Grandparent', [('Father','John','Mary'),('Parent','Mary','Tom')], True),
        ('Ancestor', [('Father','John','Mary'),('Parent','Mary','Tom'),('Parent','Tom','Alice')], True),
        ('Child', [('Father','John','Mary')], True),  # Father蕴含Child
        ('Child', [('Manager','John','Mary')], False),  # 职业关系不蕴含Child
        ('Parent', [('Colleague','A','B')], False),
    ]:
        r = reng.infer(rel, facts, ['John','Mary','Tom','Alice'])
        ok = r['found'] == expected
        print(f"  {'✅' if ok else '❌'} {rel}: found={r['found']}, conf={r['confidence']:.4f}")
    
    # 训练
    print("\n--- 训练 ---")
    system.train(data, epochs=100, lr=0.001, batch_size=4)
    system.plot_history()
    
    # 测试
    tests = [
        ("Michael is Jennifer's father. Jennifer has a son named Kevin.", 'Grandparent',
         [('Father','Michael','Jennifer'), ('Parent','Jennifer','Kevin')], True),
        ("Sarah and Thomas are married.", 'Spouse',
         [('Spouse','Sarah','Thomas')], True),
        ("David and Emma are brother and sister.", 'Sibling',
         [('Sibling','David','Emma')], True),
        ("Robert and Susan work in the same office.", 'Sibling',
         [('Colleague','Robert','Susan')], False),
        ("Lisa is Karen's manager.", 'Parent',
         [('Manager','Lisa','Karen')], False),
        ("John is Mary's manager, not her father.", 'Child',
         [('Manager','John','Mary')], False),
        ("John is Mary's father. Mary has a son Tom. Tom has a daughter Alice.", 'Ancestor',
         [('Father','John','Mary'), ('Parent','Mary','Tom'), ('Parent','Tom','Alice')], True),
        ("Alice is Bob's mother. Bob is Charlie's father.", 'Sibling',
         [('Mother','Alice','Bob'), ('Father','Bob','Charlie')], False),
        ("Michael is Jennifer's father.", 'Grandparent',
         [('Father','Michael','Jennifer')], False),
    ]
    
    print("\n" + "="*60)
    print("测试结果")
    print("="*60)
    
    correct = 0
    for i, (text, rel, facts, expected) in enumerate(tests):
        result = system.predict(text, rel, facts)
        ok = result['prediction'] == expected
        if ok: correct += 1
        
        status = "✅" if ok else "❌"
        print(f"{status} 测试{i+1}: {rel:12s} | 期望:{str(expected):5s} | "
              f"混合:{result['confidence']:.4f} | 符号:{result['symbolic_confidence']:.4f}")
    
    print(f"\n准确率: {correct}/{len(tests)} = {correct/len(tests):.2%}")
    
    # 详细示例
    print("\n" + "="*60)
    print("详细推理示例")
    print("="*60)
    result = system.predict(
        "John is Mary's father. Mary has a son Tom. Tom has a daughter Alice.",
        'Ancestor',
        [('Father','John','Mary'), ('Parent','Mary','Tom'), ('Parent','Tom','Alice')]
    )
    system.explain(result)
    
    # Child负例解释
    print("\n" + "="*60)
    print("Child负例推理")
    print("="*60)
    result2 = system.predict(
        "John is Mary's manager, not her father.",
        'Child',
        [('Manager','John','Mary')]
    )
    system.explain(result2)
    
    return system, data


if __name__ == "__main__":
    system, data = demo()