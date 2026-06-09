import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import numpy as np
import re
import json
import math
from typing import List, Dict, Tuple, Any, Optional, Union
from collections import defaultdict, OrderedDict
import random
import matplotlib.pyplot as plt
from datetime import datetime

class AccurateDifferentiableFOL(nn.Module):
    """
    精确版可微分一阶逻辑推理系统
    解决准确性问题
    """
    
    def __init__(self, num_predicates: int, num_constants: int, 
                 embedding_dim: int = 64, temperature: float = 1.0,
                 use_attention: bool = False, max_entities: int = 20):
        super().__init__()
        
        self.num_predicates = num_predicates
        self.num_constants = num_constants
        self.embedding_dim = embedding_dim
        self.temperature = temperature
        self.use_attention = use_attention
        self.max_entities = max_entities
        
        # 精确的嵌入层
        self.predicate_embeddings = nn.Embedding(num_predicates, embedding_dim)
        self.constant_embeddings = nn.Embedding(num_constants, embedding_dim)
        
        # 谓词关系知识库
        self.predicate_knowledge = self._initialize_predicate_knowledge()
        
        # 精确的关系推理网络
        self.relation_net = nn.Sequential(
            nn.Linear(embedding_dim * 3, embedding_dim * 2),
            nn.ReLU(),
            nn.Dropout(0.3),  # 增加dropout防止过拟合
            nn.Linear(embedding_dim * 2, embedding_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(embedding_dim, 1)
        )
        
        # 初始化
        self._initialize_weights()
        
        # 缓存解析的公式
        self.formula_cache = {}
        
        # 推理历史记录
        self.reasoning_history = []
    
    def _initialize_predicate_knowledge(self) -> Dict[str, Dict[str, Any]]:
        """初始化谓词知识库"""
        return {
            'Father': {'type': 'family', 'arity': 2, 'certainty': 0.95, 'inverse': 'Child'},
            'Mother': {'type': 'family', 'arity': 2, 'certainty': 0.95, 'inverse': 'Child'},
            'Parent': {'type': 'family', 'arity': 2, 'certainty': 0.90, 'inverse': 'Child'},
            'Child': {'type': 'family', 'arity': 2, 'certainty': 0.90, 'inverse': 'Parent'},
            'Spouse': {'type': 'family', 'arity': 2, 'certainty': 0.85, 'symmetric': True},
            'Sibling': {'type': 'family', 'arity': 2, 'certainty': 0.80, 'symmetric': True},
            'Grandparent': {'type': 'family', 'arity': 2, 'certainty': 0.75},
            'Brother': {'type': 'family', 'arity': 2, 'certainty': 0.85},
            'Sister': {'type': 'family', 'arity': 2, 'certainty': 0.85},
            'Son': {'type': 'family', 'arity': 2, 'certainty': 0.85},
            'Daughter': {'type': 'family', 'arity': 2, 'certainty': 0.85},
            'Colleague': {'type': 'professional', 'arity': 2, 'certainty': 0.60, 'symmetric': True},
            'Manager': {'type': 'professional', 'arity': 2, 'certainty': 0.70},
            'Friend': {'type': 'social', 'arity': 2, 'certainty': 0.50, 'symmetric': True}
        }
    
    def _initialize_weights(self):
        """精确的权重初始化"""
        nn.init.normal_(self.predicate_embeddings.weight, mean=0.0, std=0.01)
        nn.init.normal_(self.constant_embeddings.weight, mean=0.0, std=0.01)
        
        for layer in self.relation_net:
            if isinstance(layer, nn.Linear):
                nn.init.xavier_uniform_(layer.weight)
                if layer.bias is not None:
                    nn.init.zeros_(layer.bias)
    
    def safe_embedding_lookup(self, embedding_layer, indices):
        """安全的嵌入查找"""
        max_idx = embedding_layer.num_embeddings
        safe_indices = torch.clamp(indices, 0, max_idx - 1)
        return embedding_layer(safe_indices)
    
    def accurate_soft_forall(self, embeddings: torch.Tensor) -> torch.Tensor:
        """精确的软全称量词"""
        # 使用最小值近似，更符合逻辑全称
        return torch.min(embeddings, dim=1)[0]
    
    def accurate_soft_exists(self, embeddings: torch.Tensor) -> torch.Tensor:
        """精确的软存在量词"""
        return torch.max(embeddings, dim=1)[0]
    
    def accurate_and(self, x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
        """精确的逻辑与"""
        return torch.min(x, y)
    
    def accurate_or(self, x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
        """精确的逻辑或"""
        return torch.max(x, y)
    
    def accurate_not(self, x: torch.Tensor) -> torch.Tensor:
        """精确的逻辑非"""
        return 1 - x
    
    def accurate_implies(self, x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
        """精确的蕴含"""
        return torch.max(1 - x, y)
    
    def accurate_relation_score(self, subject_emb: torch.Tensor, predicate_emb: torch.Tensor, 
                               object_emb: torch.Tensor, predicate_name: str = None) -> torch.Tensor:
        """精确的关系评分"""
        batch_size = subject_emb.size(0)
        
        # 处理谓词嵌入维度
        if predicate_emb.dim() == 1:
            predicate_emb = predicate_emb.unsqueeze(0).expand(batch_size, -1)
        elif predicate_emb.dim() == 2 and predicate_emb.size(0) == 1:
            predicate_emb = predicate_emb.expand(batch_size, -1)
        
        # 确保所有张量都是 [batch_size, embed_dim]
        if subject_emb.dim() == 3:
            subject_emb = subject_emb.squeeze(1)
        if object_emb.dim() == 3:
            object_emb = object_emb.squeeze(1)
        
        # 拼接所有嵌入
        combined = torch.cat([subject_emb, predicate_emb, object_emb], dim=-1)
        
        # 通过关系网络
        raw_score = self.relation_net(combined)
        base_score = torch.sigmoid(raw_score).squeeze(-1)
        
        # 应用谓词知识调整
        if predicate_name and predicate_name in self.predicate_knowledge:
            knowledge = self.predicate_knowledge[predicate_name]
            certainty = knowledge.get('certainty', 0.7)
            pred_type = knowledge.get('type', 'unknown')
            
            # 基于谓词类型和确定性调整得分
            if pred_type == 'family':
                # 家庭关系通常更确定
                adjusted_score = base_score * certainty
            elif pred_type == 'professional':
                # 职业关系可能不那么确定
                adjusted_score = base_score * certainty * 0.8
            else:
                adjusted_score = base_score * certainty * 0.6
                
            return torch.clamp(adjusted_score, 0.05, 0.95)  # 避免极端值
        
        return torch.clamp(base_score, 0.05, 0.95)
    
    def parse_accurate_formula(self, formula: str) -> Dict[str, Any]:
        """精确的公式解析"""
        formula = formula.strip()
        
        if formula in self.formula_cache:
            return self.formula_cache[formula]
        
        # 处理括号
        if formula.startswith('(') and formula.endswith(')'):
            return self.parse_accurate_formula(formula[1:-1])
        
        # 原子谓词: P(s, o) 或 P(x)
        atom_match = re.match(r'(\w+)\(([^,)]+)(?:,\s*([^)]+))?\)', formula)
        if atom_match:
            predicate = atom_match.group(1)
            subject = atom_match.group(2)
            obj = atom_match.group(3) if atom_match.group(3) else None
            
            # 添加谓词知识
            knowledge = self.predicate_knowledge.get(predicate, {})
            
            result = {
                'type': 'atom',
                'predicate': predicate,
                'subject': subject,
                'object': obj,
                'knowledge': knowledge
            }
            self.formula_cache[formula] = result
            return result
        
        # 全称量词: ∀x: φ
        if formula.startswith('∀'):
            match = re.match(r'∀([^:]+):(.+)', formula)
            if match:
                var = match.group(1).strip()
                subformula = match.group(2).strip()
                return {
                    'type': 'forall',
                    'variable': var,
                    'subformula': self.parse_accurate_formula(subformula)
                }
        
        # 存在量词: ∃x: φ  
        if formula.startswith('∃'):
            match = re.match(r'∃([^:]+):(.+)', formula)
            if match:
                var = match.group(1).strip()
                subformula = match.group(2).strip()
                return {
                    'type': 'exists',
                    'variable': var,
                    'subformula': self.parse_accurate_formula(subformula)
                }
        
        # 逻辑操作
        operators = ['∧', '∨', '→']
        for op in operators:
            depth = 0
            for i, char in enumerate(formula):
                if char == '(': depth += 1
                elif char == ')': depth -= 1
                elif char == op and depth == 0:
                    left = formula[:i].strip()
                    right = formula[i+1:].strip()
                    
                    if op == '∧':
                        return {
                            'type': 'and',
                            'left': self.parse_accurate_formula(left),
                            'right': self.parse_accurate_formula(right)
                        }
                    elif op == '∨':
                        return {
                            'type': 'or',
                            'left': self.parse_accurate_formula(left),
                            'right': self.parse_accurate_formula(right)
                        }
                    elif op == '→':
                        return {
                            'type': 'implies',
                            'left': self.parse_accurate_formula(left),
                            'right': self.parse_accurate_formula(right)
                        }
        
        # 否定: ¬φ
        if formula.startswith('¬'):
            subformula = formula[1:].strip()
            return {
                'type': 'not',
                'subformula': self.parse_accurate_formula(subformula)
            }
        
        # 简单原子谓词
        knowledge = self.predicate_knowledge.get(formula, {})
        result = {
            'type': 'atom', 
            'predicate': formula,
            'knowledge': knowledge
        }
        self.formula_cache[formula] = result
        return result
    
    def evaluate_accurate_formula(self, parsed_formula: Dict, 
                                 constant_embeddings: torch.Tensor,
                                 constant_map: Dict[str, int],
                                 predicate_map: Dict[str, int],
                                 variable_bindings: Dict[str, int] = None) -> torch.Tensor:
        """评估精确的逻辑公式"""
        if variable_bindings is None:
            variable_bindings = {}
        
        formula_type = parsed_formula['type']
        batch_size, num_constants, embed_dim = constant_embeddings.shape
        
        if formula_type == 'atom':
            atom_data = parsed_formula
            pred_name = atom_data['predicate']
            
            # 获取谓词嵌入
            if pred_name not in predicate_map:
                return torch.ones(batch_size, device=constant_embeddings.device) * 0.1
            
            pred_idx = predicate_map[pred_name]
            pred_emb = self.safe_embedding_lookup(
                self.predicate_embeddings, 
                torch.tensor(pred_idx).to(constant_embeddings.device)
            )
            
            # 处理不同arity的谓词
            if 'subject' in atom_data and atom_data['subject'] and 'object' in atom_data and atom_data['object']:
                # 二元谓词 P(s, o)
                subj_name = atom_data['subject']
                obj_name = atom_data['object']
                
                try:
                    subj_idx = self._resolve_entity(subj_name, constant_map, variable_bindings)
                    obj_idx = self._resolve_entity(obj_name, constant_map, variable_bindings)
                    
                    subj_idx = min(subj_idx, num_constants - 1)
                    obj_idx = min(obj_idx, num_constants - 1)
                    
                    subj_emb = constant_embeddings[:, subj_idx]
                    obj_emb = constant_embeddings[:, obj_idx]
                    
                    score = self.accurate_relation_score(subj_emb, pred_emb, obj_emb, pred_name)
                    
                    step_desc = f"Evaluated {pred_name}({subj_name}, {obj_name})"
                    self._record_reasoning_step(step_desc, score.mean().item())
                    
                    return score
                except (KeyError, IndexError):
                    return torch.ones(batch_size, device=constant_embeddings.device) * 0.1
            else:
                # 一元谓词 P(x)
                entity_name = atom_data.get('subject', 'x')
                try:
                    entity_idx = self._resolve_entity(entity_name, constant_map, variable_bindings)
                    entity_idx = min(entity_idx, num_constants - 1)
                    entity_emb = constant_embeddings[:, entity_idx]
                    
                    pred_emb_expanded = pred_emb.unsqueeze(0).expand(batch_size, -1)
                    similarity = F.cosine_similarity(entity_emb, pred_emb_expanded, dim=-1)
                    result = torch.sigmoid(similarity * 2.0)  # 降低缩放因子
                    
                    step_desc = f"Evaluated {pred_name}({entity_name})"
                    self._record_reasoning_step(step_desc, result.mean().item())
                    
                    return result
                except (KeyError, IndexError):
                    return torch.ones(batch_size, device=constant_embeddings.device) * 0.1
        
        elif formula_type == 'forall':
            results = []
            
            # 精确的绑定策略
            max_bindings = min(num_constants, 3)
            for i in range(max_bindings):
                new_bindings = variable_bindings.copy()
                new_bindings[parsed_formula['variable']] = i
                
                result = self.evaluate_accurate_formula(
                    parsed_formula['subformula'], constant_embeddings, 
                    constant_map, predicate_map, new_bindings
                )
                results.append(result.unsqueeze(1))
            
            if results:
                results = torch.cat(results, dim=1)
                combined_result = self.accurate_soft_forall(results)
                self._record_reasoning_step(f"Applied FORALL on {len(results)} bindings", combined_result.mean().item())
                return combined_result
            else:
                return torch.ones(batch_size, device=constant_embeddings.device) * 0.5
        
        elif formula_type == 'exists':
            results = []
            
            max_bindings = min(num_constants, 3)
            for i in range(max_bindings):
                new_bindings = variable_bindings.copy()
                new_bindings[parsed_formula['variable']] = i
                
                result = self.evaluate_accurate_formula(
                    parsed_formula['subformula'], constant_embeddings,
                    constant_map, predicate_map, new_bindings
                )
                results.append(result.unsqueeze(1))
            
            if results:
                results = torch.cat(results, dim=1)
                combined_result = self.accurate_soft_exists(results)
                self._record_reasoning_step(f"Applied EXISTS on {len(results)} bindings", combined_result.mean().item())
                return combined_result
            else:
                return torch.ones(batch_size, device=constant_embeddings.device) * 0.5
        
        elif formula_type == 'and':
            left_result = self.evaluate_accurate_formula(
                parsed_formula['left'], constant_embeddings,
                constant_map, predicate_map, variable_bindings
            )
            right_result = self.evaluate_accurate_formula(
                parsed_formula['right'], constant_embeddings,
                constant_map, predicate_map, variable_bindings
            )
            result = self.accurate_and(left_result, right_result)
            self._record_reasoning_step("Applied AND operation", result.mean().item())
            return result
        
        elif formula_type == 'or':
            left_result = self.evaluate_accurate_formula(
                parsed_formula['left'], constant_embeddings,
                constant_map, predicate_map, variable_bindings
            )
            right_result = self.evaluate_accurate_formula(
                parsed_formula['right'], constant_embeddings,
                constant_map, predicate_map, variable_bindings
            )
            result = self.accurate_or(left_result, right_result)
            self._record_reasoning_step("Applied OR operation", result.mean().item())
            return result
        
        elif formula_type == 'not':
            sub_result = self.evaluate_accurate_formula(
                parsed_formula['subformula'], constant_embeddings,
                constant_map, predicate_map, variable_bindings
            )
            result = self.accurate_not(sub_result)
            self._record_reasoning_step("Applied NOT operation", result.mean().item())
            return result
        
        elif formula_type == 'implies':
            left_result = self.evaluate_accurate_formula(
                parsed_formula['left'], constant_embeddings,
                constant_map, predicate_map, variable_bindings
            )
            right_result = self.evaluate_accurate_formula(
                parsed_formula['right'], constant_embeddings,
                constant_map, predicate_map, variable_bindings
            )
            result = self.accurate_implies(left_result, right_result)
            self._record_reasoning_step("Applied IMPLIES operation", result.mean().item())
            return result
        
        else:
            return torch.ones(batch_size, device=constant_embeddings.device) * 0.5
    
    def _record_reasoning_step(self, step: str, confidence: float):
        """记录推理步骤"""
        # 避免记录过于相似的步骤
        if len(self.reasoning_history) > 0:
            last_step = self.reasoning_history[-1]['step']
            if step == last_step:
                return
        
        self.reasoning_history.append({
            'step': step,
            'confidence': confidence,
            'timestamp': datetime.now().isoformat()
        })
    
    def get_reasoning_history(self) -> List[Dict]:
        """获取推理历史"""
        return self.reasoning_history
    
    def clear_reasoning_history(self):
        """清空推理历史"""
        self.reasoning_history = []
    
    def _resolve_entity(self, entity_name: str, constant_map: Dict[str, int], 
                       variable_bindings: Dict[str, int]) -> int:
        """解析实体名称到索引"""
        if entity_name in variable_bindings:
            return variable_bindings[entity_name]
        elif entity_name in constant_map:
            return constant_map[entity_name]
        else:
            return 0
    
    def forward(self, entity_indices: torch.Tensor, logical_formula: str,
                constant_map: Dict[str, int], predicate_map: Dict[str, int]) -> torch.Tensor:
        """
        精确的前向传播
        """
        batch_size, num_entities = entity_indices.shape
        
        # 清空推理历史
        self.clear_reasoning_history()
        
        # 获取常量嵌入
        constant_embeds = self.safe_embedding_lookup(
            self.constant_embeddings, entity_indices
        )
        
        # 解析逻辑公式
        try:
            parsed_formula = self.parse_accurate_formula(logical_formula)
        except Exception as e:
            print(f"公式解析失败: {e}")
            parsed_formula = {'type': 'atom', 'predicate': 'Default'}
        
        # 评估公式
        result = self.evaluate_accurate_formula(
            parsed_formula, constant_embeds, constant_map, predicate_map
        )
        
        return result

class AccurateKnowledgeGraphReasoner(nn.Module):
    """
    精确的知识图谱推理系统
    """
    
    def __init__(self, vocab_size: int, num_predicates: int, num_constants: int,
                 embedding_dim: int = 64, hidden_dim: int = 128, 
                 max_entities: int = 10, max_seq_len: int = 50):
        super().__init__()
        
        self.vocab_size = vocab_size
        self.num_predicates = num_predicates
        self.num_constants = num_constants
        self.embedding_dim = embedding_dim
        self.max_entities = max_entities
        self.max_seq_len = max_seq_len
        
        # 精确的文本编码器
        self.text_embedding = nn.Embedding(vocab_size, embedding_dim)
        self.text_encoder = nn.LSTM(embedding_dim, hidden_dim // 2, batch_first=True, bidirectional=True)
        self.text_projection = nn.Linear(hidden_dim, hidden_dim // 2)
        
        # 精确的逻辑推理层
        self.logic_reasoner = AccurateDifferentiableFOL(
            num_predicates, num_constants, hidden_dim // 2, 
            temperature=1.0, use_attention=False,
            max_entities=max_entities
        )
        
        # 精确的融合网络
        self.fusion_net = nn.Sequential(
            nn.Linear(hidden_dim // 2 + 1, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim // 2, hidden_dim // 4),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim // 4, hidden_dim // 8),
            nn.ReLU(),
            nn.Linear(hidden_dim // 8, 1),
            nn.Sigmoid()
        )
    
    def encode_text(self, text_tokens: torch.Tensor) -> torch.Tensor:
        """编码文本"""
        embedded = self.text_embedding(text_tokens)
        lstm_out, (hidden, _) = self.text_encoder(embedded)
        hidden = torch.cat([hidden[0], hidden[1]], dim=-1)
        return self.text_projection(hidden)
    
    def forward(self, text_tokens: torch.Tensor, entity_indices: torch.Tensor,
                logical_formulas: List[str], constant_maps: List[Dict[str, int]],
                predicate_map: Dict[str, int]) -> Dict[str, torch.Tensor]:
        """
        精确的前向传播
        """
        batch_size = text_tokens.size(0)
        
        # 文本编码
        text_embeddings = self.encode_text(text_tokens)
        
        # 逻辑推理
        logic_scores = []
        for i in range(batch_size):
            entity_idx = entity_indices[i].unsqueeze(0)
                
            score = self.logic_reasoner(
                entity_idx,
                logical_formulas[i],
                constant_maps[i],
                predicate_map
            )
            logic_scores.append(score)
        
        # 处理逻辑得分
        logic_scores = torch.stack([score if score.dim() > 0 else score.unsqueeze(0) for score in logic_scores])
        logic_scores = logic_scores.reshape(batch_size)
        
        # 融合文本和逻辑信息
        combined = torch.cat([text_embeddings, logic_scores.unsqueeze(1)], dim=1)
        confidence = self.fusion_net(combined).squeeze(-1)
        
        return {
            'confidence': confidence,
            'logic_scores': logic_scores,
            'reasoning_history': self.logic_reasoner.get_reasoning_history()
        }

class AccurateLogicReasoningSystem:
    """
    精确逻辑推理系统 - 解决准确性问题
    """
    
    def __init__(self, domain: str = "family", max_entities: int = 10, max_seq_len: int = 50):
        self.domain = domain
        self.max_entities = max_entities
        self.max_seq_len = max_seq_len
        self.predicate_map = {}
        self.model = None
        self.entity_vocab = set()
        self.predicate_vocab = set()
        self.vocab_size = 1000
        self.training_history = []
        
        # 初始化领域知识
        self._initialize_domain_knowledge()
    
    def _initialize_domain_knowledge(self):
        """初始化领域知识库"""
        if self.domain == "family":
            base_predicates = ['Father', 'Mother', 'Parent', 'Child', 'Spouse', 
                             'Sibling', 'Grandparent', 'Ancestor', 'Descendant',
                             'Brother', 'Sister', 'Son', 'Daughter']
            self.predicate_vocab.update(base_predicates)
            
            # 领域特定的推理规则
            self.domain_rules = {
                'parent_child': 'Parent(x,y) → Child(y,x)',
                'spouse_symmetric': 'Spouse(x,y) → Spouse(y,x)',
                'sibling_symmetric': 'Sibling(x,y) → Sibling(y,x)',
                'grandparent_rule': 'Grandparent(x,y) → ∃z: Parent(x,z) ∧ Parent(z,y)'
            }
        
        # 构建谓词映射
        self.predicate_map = {pred: idx for idx, pred in enumerate(sorted(self.predicate_vocab))}
    
    def extract_entities_with_context(self, text: str) -> Dict[str, Any]:
        """提取实体及上下文信息"""
        entities = re.findall(r'\b[A-Z][a-z]+\b', text)
        entities = entities[:self.max_entities]
        
        # 上下文分析
        entity_types = {}
        context_clues = {}
        
        for entity in entities:
            # 基于常见名字的性别推断
            male_names = ['John', 'Michael', 'David', 'Robert', 'Thomas', 'George', 'Bob', 'Frank', 'Kevin', 'Ian']
            female_names = ['Mary', 'Jennifer', 'Alice', 'Emma', 'Sarah', 'Helen', 'Karen', 'Lisa', 'Carol', 'Grace']
            
            if entity in male_names:
                entity_types[entity] = 'Male'
                context_clues[entity] = {'gender': 'male', 'confidence': 0.9}
            elif entity in female_names:
                entity_types[entity] = 'Female' 
                context_clues[entity] = {'gender': 'female', 'confidence': 0.9}
            else:
                entity_types[entity] = 'Unknown'
                context_clues[entity] = {'gender': 'unknown', 'confidence': 0.5}
        
        # 分析文本上下文
        text_lower = text.lower()
        if 'work' in text_lower or 'office' in text_lower or 'company' in text_lower:
            context_type = 'professional'
        elif 'family' in text_lower or 'father' in text_lower or 'mother' in text_lower:
            context_type = 'family'
        else:
            context_type = 'general'
        
        unique_entities = list(OrderedDict.fromkeys(entities))
        self.entity_vocab.update(unique_entities)
        
        return {
            'entities': unique_entities,
            'types': entity_types,
            'context_clues': context_clues,
            'context_type': context_type,
            'entity_count': len(unique_entities)
        }
    
    def text_to_tokens(self, text: str) -> torch.Tensor:
        """将文本转换为token张量"""
        tokens = []
        for char in text[:self.max_seq_len]:
            token_id = ord(char) % self.vocab_size
            tokens.append(token_id)
        
        while len(tokens) < self.max_seq_len:
            tokens.append(0)
        
        return torch.tensor(tokens, dtype=torch.long).unsqueeze(0)
    
    def build_constant_map(self, entities: List[str]) -> Dict[str, int]:
        """构建常量映射"""
        constant_map = {}
        for idx, entity in enumerate(entities):
            constant_map[entity] = idx + 1
        
        # 添加逻辑变量
        constant_map['x'] = 0
        constant_map['y'] = 0
        constant_map['z'] = 0
        
        return constant_map
    
    def create_entity_indices(self, entities: List[str]) -> torch.Tensor:
        """创建实体索引张量"""
        indices = [i + 1 for i in range(len(entities))]
        while len(indices) < self.max_entities:
            indices.append(0)
        return torch.tensor(indices, dtype=torch.long).unsqueeze(0)
    
    def create_context_aware_sample(self, text: str, target_relation: str, 
                                   known_facts: List[Tuple[str, str, str]] = None) -> Dict[str, Any]:
        """创建上下文感知的训练样本"""
        # 提取实体及上下文信息
        entity_info = self.extract_entities_with_context(text)
        entities = entity_info['entities']
        constant_map = self.build_constant_map(entities)
        
        # 构建上下文感知的逻辑公式
        logical_formula = self._build_context_aware_formula(target_relation, entities, known_facts, entity_info)
        
        # 创建各种张量
        entity_indices = self.create_entity_indices(entities)
        text_tokens = self.text_to_tokens(text)
        
        return {
            'text': text,
            'text_tokens': text_tokens,
            'entities': entities,
            'entity_info': entity_info,
            'constant_map': constant_map,
            'entity_indices': entity_indices,
            'logical_formula': logical_formula,
            'target_relation': target_relation,
            'known_facts': known_facts or []
        }
    
    def _build_context_aware_formula(self, target_relation: str, entities: List[str],
                                    known_facts: List[Tuple[str, str, str]] = None,
                                    entity_info: Dict[str, Any] = None) -> str:
        """构建上下文感知的逻辑公式"""
        context_type = entity_info.get('context_type', 'general') if entity_info else 'general'
        
        # 基于上下文类型优化公式
        if context_type == 'professional' and target_relation in ['Parent', 'Sibling', 'Spouse']:
            # 在职业上下文中，家庭关系的置信度应该降低
            if target_relation == 'Parent':
                return 'Father(x,y) ∨ Mother(x,y)'  # 但保持原公式，让模型学习
            elif target_relation == 'Sibling':
                return '∃p: Parent(p,x) ∧ Parent(p,y) ∧ ¬(x = y)'
        
        # 默认公式
        formula_rules = {
            'Parent': 'Father(x,y) ∨ Mother(x,y)',
            'Grandparent': '∃z: Parent(x,z) ∧ Parent(z,y)',
            'Sibling': '∃p: Parent(p,x) ∧ Parent(p,y) ∧ ¬(x = y)',
            'Spouse': 'Spouse(x,y)',
            'Ancestor': 'Parent(x,y) ∨ ∃z: (Parent(x,z) ∧ Ancestor(z,y))'
        }
        
        return formula_rules.get(target_relation, f'{target_relation}(x,y)')
    
    def initialize_accurate_model(self):
        """初始化精确模型"""
        num_constants = max(len(self.entity_vocab) + 10, self.max_entities + 5)
        num_predicates = len(self.predicate_map)
        
        self.model = AccurateKnowledgeGraphReasoner(
            vocab_size=self.vocab_size,
            num_predicates=num_predicates,
            num_constants=num_constants,
            embedding_dim=64,
            hidden_dim=128,
            max_entities=self.max_entities,
            max_seq_len=self.max_seq_len
        )
        
        return self.model
    
    def train_accurate(self, training_data: List[Dict], epochs: int = 150, 
                      learning_rate: float = 0.0005, batch_size: int = 2):
        """精确的训练过程"""
        if self.model is None:
            self.initialize_accurate_model()
        
        # 使用更保守的优化器设置
        optimizer = optim.AdamW(self.model.parameters(), lr=learning_rate, weight_decay=0.02)
        criterion = nn.BCELoss()
        
        # 更温和的学习率调度
        scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=30, gamma=0.85)
        
        self.model.train()
        best_loss = float('inf')
        patience = 15
        patience_counter = 0
        
        for epoch in range(epochs):
            total_loss = 0
            correct = 0
            total = 0
            
            random.shuffle(training_data)
            
            for i in range(0, len(training_data), batch_size):
                batch = training_data[i:i+batch_size]
                
                if len(batch) == 0:
                    continue
                
                try:
                    # 准备批次数据
                    text_tokens = torch.cat([sample['text_tokens'] for sample in batch], dim=0)
                    entity_indices = torch.cat([sample['entity_indices'] for sample in batch], dim=0)
                    formulas = [sample['logical_formula'] for sample in batch]
                    constant_maps = [sample['constant_map'] for sample in batch]
                    
                    targets = torch.tensor([1.0 if sample.get('is_true', False) else 0.0 
                                          for sample in batch], dtype=torch.float32)
                    
                    # 前向传播
                    outputs = self.model(text_tokens, entity_indices, formulas, constant_maps, self.predicate_map)
                    confidence = outputs['confidence']
                    
                    # 计算损失
                    loss = criterion(confidence, targets)
                    
                    # 反向传播
                    optimizer.zero_grad()
                    loss.backward()
                    
                    # 更严格的梯度裁剪
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), 0.5)
                    optimizer.step()
                    
                    total_loss += loss.item()
                    
                    # 计算准确率
                    predictions = (confidence > 0.5).float()
                    correct += (predictions == targets).sum().item()
                    total += len(targets)
                    
                except Exception as e:
                    print(f"训练批次时出错: {e}")
                    continue
            
            # 更新学习率
            scheduler.step()
            
            if total > 0:
                accuracy = correct / total
                avg_loss = total_loss / max(1, len(training_data) / batch_size)
                
                # 记录训练历史
                self.training_history.append({
                    'epoch': epoch,
                    'loss': avg_loss,
                    'accuracy': accuracy,
                    'learning_rate': scheduler.get_last_lr()[0]
                })
                
                # 改进的早停机制
                if avg_loss < best_loss:
                    best_loss = avg_loss
                    patience_counter = 0
                else:
                    patience_counter += 1
                
                if epoch % 15 == 0:
                    print(f'Epoch {epoch:3d} | Loss: {avg_loss:.4f} | Accuracy: {accuracy:.4f} | LR: {scheduler.get_last_lr()[0]:.6f}')
                
                # 如果损失很小但准确率不高，可能是过拟合
                if avg_loss < 0.1 and accuracy < 0.8:
                    print(f"检测到可能的过拟合，提前停止训练")
                    break
                    
                if patience_counter >= patience:
                    print(f"早停: 在epoch {epoch}停止训练")
                    break
    
    def predict_accurate(self, text: str, target_relation: str, 
                        known_facts: List[Tuple[str, str, str]] = None) -> Dict[str, Any]:
        """精确的预测方法"""
        if self.model is None:
            raise ValueError("模型未初始化")
        
        self.model.eval()
        
        # 创建样本
        sample = self.create_context_aware_sample(text, target_relation, known_facts)
        
        with torch.no_grad():
            outputs = self.model(
                sample['text_tokens'],
                sample['entity_indices'],
                [sample['logical_formula']],
                [sample['constant_map']],
                self.predicate_map
            )
        
        confidence = outputs['confidence'].item()
        logic_score = outputs['logic_scores'].item()
        reasoning_history = outputs.get('reasoning_history', [])
        
        return {
            'confidence': confidence,
            'logic_score': logic_score,
            'entities': sample['entities'],
            'entity_info': sample['entity_info'],
            'prediction': confidence > 0.5,
            'formula': sample['logical_formula'],
            'reasoning_steps': reasoning_history,
            'known_facts': known_facts or [],
            'target_relation': target_relation
        }
    
    def plot_training_history(self):
        """绘制训练历史"""
        if not self.training_history:
            print("没有训练历史数据")
            return
        
        epochs = [x['epoch'] for x in self.training_history]
        losses = [x['loss'] for x in self.training_history]
        accuracies = [x['accuracy'] for x in self.training_history]
        learning_rates = [x['learning_rate'] for x in self.training_history]
        
        fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 4))
        
        # 损失曲线
        ax1.plot(epochs, losses, 'b-', label='Loss')
        ax1.set_xlabel('Epoch')
        ax1.set_ylabel('Loss')
        ax1.set_title('Training Loss')
        ax1.grid(True)
        ax1.legend()
        
        # 准确率曲线
        ax2.plot(epochs, accuracies, 'r-', label='Accuracy')
        ax2.set_xlabel('Epoch')
        ax2.set_ylabel('Accuracy')
        ax2.set_title('Training Accuracy')
        ax2.grid(True)
        ax2.legend()
        
        # 学习率曲线
        ax3.plot(epochs, learning_rates, 'g-', label='Learning Rate')
        ax3.set_xlabel('Epoch')
        ax3.set_ylabel('Learning Rate')
        ax3.set_title('Learning Rate Schedule')
        ax3.grid(True)
        ax3.legend()
        
        plt.tight_layout()
        plt.show()
    
    def explain_reasoning(self, prediction_result: Dict[str, Any]):
        """详细的推理过程解释"""
        print("\n" + "="*60)
        print("详细推理过程解释")
        print("="*60)
        
        print(f"目标关系: {prediction_result.get('target_relation', 'Unknown')}")
        print(f"最终置信度: {prediction_result['confidence']:.4f}")
        print(f"逻辑推理得分: {prediction_result['logic_score']:.4f}")
        print(f"预测结果: {'✓ 成立' if prediction_result['prediction'] else '✗ 不成立'}")
        print(f"使用的逻辑公式: {prediction_result['formula']}")
        
        # 显示已知事实
        known_facts = prediction_result.get('known_facts', [])
        if known_facts:
            print(f"\n已知事实:")
            for i, fact in enumerate(known_facts):
                print(f"  {i+1}. {fact[0]}({fact[1]}, {fact[2]})")
        
        # 显示实体信息
        entity_info = prediction_result.get('entity_info', {})
        if entity_info:
            print(f"\n上下文分析:")
            entities = prediction_result['entities']
            types = entity_info.get('types', {})
            context_clues = entity_info.get('context_clues', {})
            context_type = entity_info.get('context_type', 'general')
            
            print(f"  上下文类型: {context_type}")
            for entity in entities:
                type_str = types.get(entity, 'Unknown')
                clues = context_clues.get(entity, {})
                gender = clues.get('gender', 'unknown')
                confidence = clues.get('confidence', 0.5)
                print(f"  {entity}: {type_str} (性别: {gender}, 确定性: {confidence:.2f})")
        
        # 显示推理步骤
        reasoning_steps = prediction_result.get('reasoning_steps', [])
        if reasoning_steps:
            print(f"\n推理步骤 (共{len(reasoning_steps)}步):")
            for i, step in enumerate(reasoning_steps):
                confidence = step['confidence']
                if confidence > 0.8:
                    level = "高"
                elif confidence > 0.6:
                    level = "中"
                else:
                    level = "低"
                print(f"  {i+1:2d}. {step['step']} [{level}置信度: {confidence:.4f}]")
        
        confidence = prediction_result['confidence']
        if prediction_result['prediction']:
            print(f"\n总结: 基于{len(prediction_result['entities'])}个实体和{len(known_facts)}个已知事实，")
            print(f"系统以{confidence:.1%}的置信度确认'{prediction_result['target_relation']}'关系成立。")
        else:
            print(f"\n总结: 基于{len(prediction_result['entities'])}个实体和{len(known_facts)}个已知事实，")
            print(f"系统以{1-confidence:.1%}的置信度认为'{prediction_result['target_relation']}'关系不成立。")

# 创建精确的训练数据
def create_accurate_family_data() -> List[Dict]:
    """创建精确的家庭关系数据"""
    samples = []
    
    # 正例样本
    positive_samples = [
        {
            'text': "John is Mary's father. Mary has a son named Tom.",
            'target_relation': 'Grandparent',
            'known_facts': [('Father', 'John', 'Mary'), ('Parent', 'Mary', 'Tom')],
            'is_true': True
        },
        {
            'text': "Alice and Bob are married. They have a daughter Carol.",
            'target_relation': 'Spouse', 
            'known_facts': [('Spouse', 'Alice', 'Bob'), ('Parent', 'Alice', 'Carol')],
            'is_true': True
        },
        {
            'text': "David is the father of Emma. Emma is the mother of Frank.",
            'target_relation': 'Grandparent',
            'known_facts': [('Father', 'David', 'Emma'), ('Mother', 'Emma', 'Frank')],
            'is_true': True
        },
        {
            'text': "George and Helen are siblings. They share the same parents.",
            'target_relation': 'Sibling',
            'known_facts': [('Sibling', 'George', 'Helen')],
            'is_true': True
        },
        {
            'text': "Michael is Jennifer's father.",
            'target_relation': 'Parent',
            'known_facts': [('Father', 'Michael', 'Jennifer')],
            'is_true': True
        }
    ]
    
    # 反例样本 - 增加更多样化的负样本
    negative_samples = [
        {
            'text': "George is Helen's brother. Helen has a son Ian.",
            'target_relation': 'Parent',
            'known_facts': [('Sibling', 'George', 'Helen'), ('Parent', 'Helen', 'Ian')],
            'is_true': False
        },
        {
            'text': "Karen and Lisa are colleagues at work.",
            'target_relation': 'Sibling',
            'known_facts': [('Colleague', 'Karen', 'Lisa')],
            'is_true': False
        },
        {
            'text': "Michael works with Jennifer. They are not related.",
            'target_relation': 'Spouse',
            'known_facts': [('Colleague', 'Michael', 'Jennifer')],
            'is_true': False
        },
        {
            'text': "Robert is Susan's manager at the company.",
            'target_relation': 'Parent',
            'known_facts': [('Manager', 'Robert', 'Susan')],
            'is_true': False
        },
        {
            'text': "David and Emma work together on the project.",
            'target_relation': 'Sibling',
            'known_facts': [('Colleague', 'David', 'Emma')],
            'is_true': False
        },
        {
            'text': "Sarah and Thomas are friends from college.",
            'target_relation': 'Spouse',
            'known_facts': [('Friend', 'Sarah', 'Thomas')],
            'is_true': False
        }
    ]
    
    # 创建训练样本
    system = AccurateLogicReasoningSystem("family", max_entities=8, max_seq_len=50)
    
    for sample in positive_samples + negative_samples:
        training_sample = system.create_context_aware_sample(
            sample['text'], sample['target_relation'], sample['known_facts']
        )
        training_sample['is_true'] = sample['is_true']
        samples.append(training_sample)
    
    return samples

def demo_accurate_system():
    """演示精确系统功能"""
    print("初始化精确逻辑推理系统...")
    system = AccurateLogicReasoningSystem("family", max_entities=8, max_seq_len=50)
    
    print("创建精确训练数据...")
    training_data = create_accurate_family_data()
    print(f"创建了 {len(training_data)} 个训练样本")
    
    print("初始化精确模型...")
    system.initialize_accurate_model()
    
    print("开始精确训练...")
    system.train_accurate(training_data, epochs=150, batch_size=2, learning_rate=0.0005)
    
    print("\n绘制训练历史...")
    system.plot_training_history()
    
    print("\n运行精确推理演示...")
    test_cases = [
        {
            'text': "Michael is Jennifer's father. Jennifer has a son named Kevin.",
            'relation': 'Grandparent',
            'facts': [('Father', 'Michael', 'Jennifer'), ('Parent', 'Jennifer', 'Kevin')]
        },
        {
            'text': "Sarah and Thomas are married for 10 years.",
            'relation': 'Spouse', 
            'facts': [('Spouse', 'Sarah', 'Thomas')]
        },
        {
            'text': "Robert and Susan work in the same office. They are not related.",
            'relation': 'Sibling',
            'facts': [('Colleague', 'Robert', 'Susan')]
        },
        {
            'text': "David and Emma are brother and sister.",
            'relation': 'Sibling',
            'facts': [('Sibling', 'David', 'Emma')]
        },
        {
            'text': "Lisa is Karen's manager at the company.",
            'relation': 'Parent',
            'facts': [('Manager', 'Lisa', 'Karen')]
        }
    ]
    
    for i, test_case in enumerate(test_cases):
        print(f"\n{'='*70}")
        print(f"测试案例 {i+1}")
        print(f"{'='*70}")
        print(f"文本: {test_case['text']}")
        print(f"目标关系: {test_case['relation']}")
        
        result = system.predict_accurate(
            test_case['text'], 
            test_case['relation'],
            test_case['facts']
        )
        
        # 显示详细解释
        system.explain_reasoning(result)

if __name__ == "__main__":
    # 设置设备
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"使用设备: {device}")
    
    # 设置随机种子
    torch.manual_seed(42)
    np.random.seed(42)
    random.seed(42)
    
    # 运行精确演示
    demo_accurate_system()