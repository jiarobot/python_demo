"""
精确版可微分一阶逻辑推理系统 v2.2 - 修复递归问题
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import numpy as np
import re
import math
import sys
from typing import List, Dict, Tuple, Any, Optional, Union
from collections import defaultdict, OrderedDict
import random
import matplotlib.pyplot as plt
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# 增加递归限制
sys.setrecursionlimit(10000)

# ============================================================================
# 第一部分：图神经网络层
# ============================================================================

class GraphAttentionLayer(nn.Module):
    """图注意力层"""
    def __init__(self, in_features: int, out_features: int, dropout: float = 0.2, alpha: float = 0.2):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.dropout = dropout
        self.alpha = alpha
        
        self.W = nn.Parameter(torch.zeros(size=(in_features, out_features)))
        self.a = nn.Parameter(torch.zeros(size=(2 * out_features, 1)))
        
        self.leakyrelu = nn.LeakyReLU(self.alpha)
        self.dropout_layer = nn.Dropout(dropout)
        
        self._init_weights()
    
    def _init_weights(self):
        nn.init.xavier_uniform_(self.W.data, gain=1.414)
        nn.init.xavier_uniform_(self.a.data, gain=1.414)
    
    def forward(self, h: torch.Tensor, adj: torch.Tensor = None) -> torch.Tensor:
        batch_size, num_nodes, _ = h.shape
        
        if adj is None:
            adj = torch.ones(batch_size, num_nodes, num_nodes, device=h.device)
        elif adj.dim() == 2:
            adj = adj.unsqueeze(0).expand(batch_size, -1, -1)
        
        Wh = torch.matmul(h, self.W)
        
        Wh1 = Wh.unsqueeze(2).expand(-1, -1, num_nodes, -1)
        Wh2 = Wh.unsqueeze(1).expand(-1, num_nodes, -1, -1)
        
        e = torch.cat([Wh1, Wh2], dim=-1)
        e = torch.matmul(e, self.a).squeeze(-1)
        e = self.leakyrelu(e)
        
        zero_vec = -9e15 * torch.ones_like(e)
        attention = torch.where(adj > 0, e, zero_vec)
        attention = F.softmax(attention, dim=-1)
        attention = self.dropout_layer(attention)
        
        h_prime = torch.matmul(attention, Wh)
        return F.elu(h_prime)


class EnhancedGraphEncoder(nn.Module):
    """增强图编码器"""
    def __init__(self, input_dim: int, hidden_dim: int, output_dim: int, 
                 num_heads: int = 4, dropout: float = 0.2):
        super().__init__()
        self.num_heads = num_heads
        
        self.attention_heads = nn.ModuleList([
            GraphAttentionLayer(input_dim, hidden_dim, dropout) 
            for _ in range(num_heads)
        ])
        
        self.output_proj = nn.Linear(hidden_dim * num_heads, output_dim)
        self.residual_proj = nn.Linear(input_dim, output_dim) if input_dim != output_dim else nn.Identity()
        self.layer_norm = nn.LayerNorm(output_dim)
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, x: torch.Tensor, adj: torch.Tensor = None) -> torch.Tensor:
        head_outputs = []
        for head in self.attention_heads:
            head_outputs.append(head(x, adj))
        
        multi_head = torch.cat(head_outputs, dim=-1)
        output = self.output_proj(multi_head)
        residual = self.residual_proj(x)
        output = self.dropout(output)
        output = self.layer_norm(output + residual)
        return output


# ============================================================================
# 第二部分：可微分一阶逻辑系统
# ============================================================================

class EnhancedDifferentiableFOL(nn.Module):
    """增强版可微分一阶逻辑推理系统"""
    
    def __init__(self, num_predicates: int, num_constants: int, 
                 embedding_dim: int = 64, temperature: float = 1.0,
                 max_entities: int = 20, use_graph_encoder: bool = True):
        super().__init__()
        
        self.num_predicates = num_predicates
        self.num_constants = num_constants
        self.embedding_dim = embedding_dim
        self.temperature = temperature
        self.max_entities = max_entities
        self.use_graph_encoder = use_graph_encoder
        
        self.log_temperature = nn.Parameter(torch.tensor(math.log(temperature)))
        
        self.predicate_embeddings = nn.Embedding(num_predicates, embedding_dim)
        self.constant_embeddings = nn.Embedding(num_constants, embedding_dim)
        self.predicate_type_embeddings = nn.Embedding(10, embedding_dim // 4)
        
        if use_graph_encoder:
            self.graph_encoder = EnhancedGraphEncoder(
                embedding_dim, embedding_dim // 2, embedding_dim,
                num_heads=2, dropout=0.2
            )
        
        # 计算正确的输入维度
        # concat: embed*3 + diff:embed + type:embed//4 + dot:1
        input_dim = embedding_dim * 3 + embedding_dim + embedding_dim // 4 + 1
        self.relation_net = nn.Sequential(
            nn.Linear(input_dim, embedding_dim * 2),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(embedding_dim * 2, embedding_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(embedding_dim, embedding_dim // 2),
            nn.ReLU(),
            nn.Linear(embedding_dim // 2, 1)
        )
        
        self.predicate_knowledge = self._initialize_predicate_knowledge()
        
        self.formula_cache = {}
        self.reasoning_history = []
        
        self._initialize_weights()
    
    def _initialize_predicate_knowledge(self) -> Dict[str, Dict[str, Any]]:
        return {
            'Father': {'type': 'family', 'arity': 2, 'certainty': 0.95, 'type_id': 0},
            'Mother': {'type': 'family', 'arity': 2, 'certainty': 0.95, 'type_id': 0},
            'Parent': {'type': 'family', 'arity': 2, 'certainty': 0.90, 'type_id': 0},
            'Child': {'type': 'family', 'arity': 2, 'certainty': 0.90, 'type_id': 0},
            'Spouse': {'type': 'family', 'arity': 2, 'certainty': 0.85, 'symmetric': True, 'type_id': 1},
            'Sibling': {'type': 'family', 'arity': 2, 'certainty': 0.80, 'symmetric': True, 'type_id': 1},
            'Grandparent': {'type': 'family', 'arity': 2, 'certainty': 0.75, 'type_id': 2},
            'Grandchild': {'type': 'family', 'arity': 2, 'certainty': 0.75, 'type_id': 2},
            'Brother': {'type': 'family', 'arity': 2, 'certainty': 0.85, 'type_id': 0},
            'Sister': {'type': 'family', 'arity': 2, 'certainty': 0.85, 'type_id': 0},
            'Son': {'type': 'family', 'arity': 2, 'certainty': 0.85, 'type_id': 0},
            'Daughter': {'type': 'family', 'arity': 2, 'certainty': 0.85, 'type_id': 0},
            'Ancestor': {'type': 'family', 'arity': 2, 'certainty': 0.70, 'type_id': 2},
            'Descendant': {'type': 'family', 'arity': 2, 'certainty': 0.70, 'type_id': 2},
            'Colleague': {'type': 'professional', 'arity': 2, 'certainty': 0.60, 'symmetric': True, 'type_id': 3},
            'Manager': {'type': 'professional', 'arity': 2, 'certainty': 0.70, 'type_id': 3},
            'Friend': {'type': 'social', 'arity': 2, 'certainty': 0.50, 'symmetric': True, 'type_id': 4}
        }
    
    def _initialize_weights(self):
        nn.init.orthogonal_(self.predicate_embeddings.weight, gain=0.1)
        nn.init.orthogonal_(self.constant_embeddings.weight, gain=0.1)
        
        for module in self.relation_net:
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight, gain=0.5)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
    
    @property
    def effective_temperature(self) -> torch.Tensor:
        return torch.exp(self.log_temperature) + 1e-6
    
    def safe_embedding_lookup(self, embedding_layer, indices):
        max_idx = embedding_layer.num_embeddings
        safe_indices = torch.clamp(indices, 0, max_idx - 1)
        return embedding_layer(safe_indices)
    
    # --------------------------------------------------------------------------
    # 逻辑操作
    # --------------------------------------------------------------------------
    
    def soft_forall(self, embeddings: torch.Tensor, dim: int = 1) -> torch.Tensor:
        temp = self.effective_temperature
        n = max(embeddings.size(dim), 1)
        return -temp * torch.logsumexp(-embeddings / temp, dim=dim) + temp * math.log(n)
    
    def soft_exists(self, embeddings: torch.Tensor, dim: int = 1) -> torch.Tensor:
        temp = self.effective_temperature
        n = max(embeddings.size(dim), 1)
        return temp * torch.logsumexp(embeddings / temp, dim=dim) - temp * math.log(n)
    
    def soft_and(self, x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
        return x * y
    
    def soft_or(self, x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
        return x + y - x * y
    
    def soft_not(self, x: torch.Tensor) -> torch.Tensor:
        return 1.0 - x
    
    def soft_implies(self, x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
        return torch.clamp(1.0 - x + y, 0.0, 1.0)
    
    # --------------------------------------------------------------------------
    # 关系评分（修复递归问题）
    # --------------------------------------------------------------------------
    
    def _compute_base_relation_score(self, subject_emb: torch.Tensor, 
                                     predicate_emb: torch.Tensor,
                                     object_emb: torch.Tensor, 
                                     predicate_name: str = None) -> torch.Tensor:
        """
        计算基础关系评分（无对称性检查，避免递归）
        """
        batch_size = subject_emb.size(0)
        
        # 确保维度正确
        if predicate_emb.dim() == 1:
            predicate_emb = predicate_emb.unsqueeze(0).expand(batch_size, -1)
        
        if subject_emb.dim() == 3:
            subject_emb = subject_emb.squeeze(1)
        if object_emb.dim() == 3:
            object_emb = object_emb.squeeze(1)
        
        # 确保所有张量都是2D
        subject_emb = subject_emb.reshape(batch_size, -1)
        predicate_emb = predicate_emb.reshape(batch_size, -1)
        object_emb = object_emb.reshape(batch_size, -1)
        
        # 多种交互特征
        concat_feat = torch.cat([subject_emb, predicate_emb, object_emb], dim=-1)
        diff_feat = torch.abs(subject_emb - object_emb)
        dot_feat = (subject_emb * object_emb).sum(dim=-1, keepdim=True)
        
        # 谓词类型特征
        if predicate_name and predicate_name in self.predicate_knowledge:
            type_id = self.predicate_knowledge[predicate_name].get('type_id', 0)
            type_emb = self.predicate_type_embeddings(
                torch.tensor(type_id, device=subject_emb.device)
            ).expand(batch_size, -1)
        else:
            type_emb = torch.zeros(batch_size, self.embedding_dim // 4, device=subject_emb.device)
        
        # 组合所有特征
        combined = torch.cat([concat_feat, diff_feat, type_emb, dot_feat], dim=-1)
        
        # 通过评分网络
        raw_score = self.relation_net(combined)
        base_score = torch.sigmoid(raw_score).squeeze(-1)
        
        return base_score
    
    def enhanced_relation_score(self, subject_emb: torch.Tensor, 
                                predicate_emb: torch.Tensor,
                                object_emb: torch.Tensor, 
                                predicate_name: str = None) -> torch.Tensor:
        """
        增强的关系评分（修复递归问题）
        - 对称关系不再递归调用自己，而是分别计算两个方向后取平均
        """
        # 计算基础评分
        base_score = self._compute_base_relation_score(
            subject_emb, predicate_emb, object_emb, predicate_name
        )
        
        # 应用谓词知识调整
        if predicate_name and predicate_name in self.predicate_knowledge:
            knowledge = self.predicate_knowledge[predicate_name]
            certainty = knowledge.get('certainty', 0.7)
            
            if knowledge.get('symmetric', False):
                # 对对称关系，计算反向评分（使用基础评分函数，避免递归）
                reverse_score = self._compute_base_relation_score(
                    object_emb, predicate_emb, subject_emb, predicate_name
                )
                # 取两个方向的平均值
                base_score = (base_score + reverse_score) / 2
            
            adjusted_score = base_score * certainty
            return torch.clamp(adjusted_score, 0.01, 0.99)
        
        return torch.clamp(base_score, 0.01, 0.99)
    
    # --------------------------------------------------------------------------
    # 公式解析
    # --------------------------------------------------------------------------
    
    def parse_formula(self, formula: str) -> Dict[str, Any]:
        """解析逻辑公式"""
        formula = formula.strip()
        
        if formula in self.formula_cache:
            return self.formula_cache[formula]
        
        # 处理括号
        if formula.startswith('(') and formula.endswith(')'):
            depth = 0
            for i, c in enumerate(formula[:-1]):
                if c == '(': depth += 1
                elif c == ')': depth -= 1
                if depth == 0:
                    break
            if depth == 0 and i == len(formula) - 2:
                return self.parse_formula(formula[1:-1])
        
        # 原子谓词: P(s, o) 或 P(x)
        atom_match = re.match(r'(\w+)\(([^,)]+)(?:,\s*([^)]+))?\)', formula)
        if atom_match:
            predicate = atom_match.group(1)
            subject = atom_match.group(2)
            obj = atom_match.group(3) if atom_match.group(3) else None
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
        
        # 全称量词
        if formula.startswith('∀'):
            match = re.match(r'∀([^:]+):(.+)', formula)
            if match:
                var = match.group(1).strip()
                subformula = match.group(2).strip()
                return {
                    'type': 'forall',
                    'variable': var,
                    'subformula': self.parse_formula(subformula)
                }
        
        # 存在量词
        if formula.startswith('∃'):
            match = re.match(r'∃([^:]+):(.+)', formula)
            if match:
                var = match.group(1).strip()
                subformula = match.group(2).strip()
                return {
                    'type': 'exists',
                    'variable': var,
                    'subformula': self.parse_formula(subformula)
                }
        
        # 逻辑操作（按优先级从低到高）
        operators = [('↔', 'equiv'), ('→', 'implies'), ('∨', 'or'), ('∧', 'and')]
        
        for op_symbol, op_type in operators:
            depth = 0
            for i, char in enumerate(formula):
                if char == '(': depth += 1
                elif char == ')': depth -= 1
                elif char == op_symbol and depth == 0:
                    left = formula[:i].strip()
                    right = formula[i+1:].strip()
                    return {
                        'type': op_type,
                        'left': self.parse_formula(left),
                        'right': self.parse_formula(right)
                    }
        
        # 否定
        if formula.startswith('¬'):
            subformula = formula[1:].strip()
            return {
                'type': 'not',
                'subformula': self.parse_formula(subformula)
            }
        
        # 默认作为原子谓词
        knowledge = self.predicate_knowledge.get(formula, {})
        result = {
            'type': 'atom',
            'predicate': formula,
            'knowledge': knowledge
        }
        self.formula_cache[formula] = result
        return result
    
    # --------------------------------------------------------------------------
    # 公式评估
    # --------------------------------------------------------------------------
    
    def _resolve_entity(self, entity_name: str, constant_map: Dict[str, int],
                       variable_bindings: Dict[str, int]) -> int:
        if entity_name in variable_bindings:
            return variable_bindings[entity_name]
        elif entity_name in constant_map:
            return constant_map[entity_name]
        return 0
    
    def _record_step(self, step: str, confidence: float):
        if not self.reasoning_history or self.reasoning_history[-1]['step'] != step:
            self.reasoning_history.append({
                'step': step,
                'confidence': confidence,
                'timestamp': datetime.now().isoformat()
            })
    
    def get_reasoning_history(self) -> List[Dict]:
        return self.reasoning_history
    
    def clear_reasoning_history(self):
        self.reasoning_history = []
    
    def evaluate_formula(self, parsed_formula: Dict,
                        constant_embeddings: torch.Tensor,
                        constant_map: Dict[str, int],
                        predicate_map: Dict[str, int],
                        variable_bindings: Dict[str, int] = None) -> torch.Tensor:
        """评估逻辑公式（非递归实现，使用显式栈）"""
        if variable_bindings is None:
            variable_bindings = {}
        
        formula_type = parsed_formula['type']
        batch_size, num_constants, embed_dim = constant_embeddings.shape
        
        try:
            if formula_type == 'atom':
                return self._evaluate_atom(parsed_formula, constant_embeddings, 
                                          constant_map, predicate_map, variable_bindings)
            elif formula_type == 'forall':
                return self._evaluate_quantifier(parsed_formula, 'forall', constant_embeddings,
                                                constant_map, predicate_map, variable_bindings)
            elif formula_type == 'exists':
                return self._evaluate_quantifier(parsed_formula, 'exists', constant_embeddings,
                                                constant_map, predicate_map, variable_bindings)
            elif formula_type in ('and', 'or', 'implies', 'equiv'):
                return self._evaluate_binary_op(parsed_formula, formula_type, constant_embeddings,
                                               constant_map, predicate_map, variable_bindings)
            elif formula_type == 'not':
                sub_result = self.evaluate_formula(
                    parsed_formula['subformula'], constant_embeddings,
                    constant_map, predicate_map, variable_bindings
                )
                return self.soft_not(sub_result)
        except Exception as e:
            print(f"公式评估错误: {e}, 公式类型: {formula_type}")
        
        return torch.ones(batch_size, device=constant_embeddings.device) * 0.5
    
    def _evaluate_atom(self, atom_data, constant_embeddings, 
                      constant_map, predicate_map, variable_bindings):
        """评估原子公式"""
        pred_name = atom_data['predicate']
        batch_size, num_constants, _ = constant_embeddings.shape
        
        if pred_name not in predicate_map:
            return torch.ones(batch_size, device=constant_embeddings.device) * 0.01
        
        pred_idx = predicate_map[pred_name]
        pred_emb = self.safe_embedding_lookup(
            self.predicate_embeddings,
            torch.tensor(pred_idx, device=constant_embeddings.device)
        )
        
        if 'subject' in atom_data and atom_data['subject'] and \
           'object' in atom_data and atom_data['object']:
            # 二元谓词
            subj_name = atom_data['subject']
            obj_name = atom_data['object']
            
            try:
                subj_idx = self._resolve_entity(subj_name, constant_map, variable_bindings)
                obj_idx = self._resolve_entity(obj_name, constant_map, variable_bindings)
                
                subj_idx = min(subj_idx, num_constants - 1)
                obj_idx = min(obj_idx, num_constants - 1)
                
                subj_emb = constant_embeddings[:, subj_idx]
                obj_emb = constant_embeddings[:, obj_idx]
                
                score = self.enhanced_relation_score(subj_emb, pred_emb, obj_emb, pred_name)
                return score
            except (KeyError, IndexError):
                return torch.ones(batch_size, device=constant_embeddings.device) * 0.01
        else:
            # 一元谓词
            entity_name = atom_data.get('subject', 'x')
            try:
                entity_idx = self._resolve_entity(entity_name, constant_map, variable_bindings)
                entity_idx = min(entity_idx, num_constants - 1)
                entity_emb = constant_embeddings[:, entity_idx]
                
                pred_emb_expanded = pred_emb.unsqueeze(0).expand(batch_size, -1)
                similarity = F.cosine_similarity(entity_emb, pred_emb_expanded, dim=-1)
                result = torch.sigmoid(similarity * 3.0)
                return result
            except (KeyError, IndexError):
                return torch.ones(batch_size, device=constant_embeddings.device) * 0.01
    
    def _evaluate_quantifier(self, parsed_formula, quantifier_type,
                            constant_embeddings, constant_map,
                            predicate_map, variable_bindings):
        """评估量词"""
        batch_size, num_constants, _ = constant_embeddings.shape
        
        results = []
        max_bindings = min(num_constants, self.max_entities)
        
        for i in range(max_bindings):
            new_bindings = variable_bindings.copy()
            new_bindings[parsed_formula['variable']] = i
            
            result = self.evaluate_formula(
                parsed_formula['subformula'], constant_embeddings,
                constant_map, predicate_map, new_bindings
            )
            results.append(result.unsqueeze(1))
        
        if results:
            results_tensor = torch.cat(results, dim=1)
            
            if quantifier_type == 'forall':
                combined = self.soft_forall(results_tensor, dim=1)
            else:
                combined = self.soft_exists(results_tensor, dim=1)
            
            return combined
        
        return torch.ones(batch_size, device=constant_embeddings.device) * 0.5
    
    def _evaluate_binary_op(self, parsed_formula, op_type,
                           constant_embeddings, constant_map,
                           predicate_map, variable_bindings):
        """评估二元操作"""
        left_result = self.evaluate_formula(
            parsed_formula['left'], constant_embeddings,
            constant_map, predicate_map, variable_bindings
        )
        right_result = self.evaluate_formula(
            parsed_formula['right'], constant_embeddings,
            constant_map, predicate_map, variable_bindings
        )
        
        if op_type == 'and':
            return self.soft_and(left_result, right_result)
        elif op_type == 'or':
            return self.soft_or(left_result, right_result)
        elif op_type == 'implies':
            return self.soft_implies(left_result, right_result)
        elif op_type == 'equiv':
            # A ↔ B = (A → B) ∧ (B → A)
            return self.soft_and(
                self.soft_implies(left_result, right_result),
                self.soft_implies(right_result, left_result)
            )
        
        return left_result
    
    def get_entity_embeddings_with_graph(self, entity_indices: torch.Tensor,
                                         adj_matrix: torch.Tensor = None) -> torch.Tensor:
        """使用图编码器增强实体嵌入"""
        entity_embeds = self.safe_embedding_lookup(self.constant_embeddings, entity_indices)
        
        if self.use_graph_encoder and adj_matrix is not None:
            if adj_matrix.dim() == 2:
                adj_matrix = adj_matrix.unsqueeze(0)
            entity_embeds = self.graph_encoder(entity_embeds, adj_matrix)
        
        return entity_embeds
    
    def forward(self, entity_indices: torch.Tensor, logical_formula: str,
                constant_map: Dict[str, int], predicate_map: Dict[str, int],
                adj_matrix: torch.Tensor = None) -> torch.Tensor:
        """前向传播"""
        self.clear_reasoning_history()
        
        # 获取增强的实体嵌入
        constant_embeds = self.get_entity_embeddings_with_graph(entity_indices, adj_matrix)
        
        # 解析公式
        try:
            parsed_formula = self.parse_formula(logical_formula)
        except Exception as e:
            print(f"公式解析失败: {e}")
            batch_size = entity_indices.size(0)
            return torch.ones(batch_size, device=entity_indices.device) * 0.5
        
        # 评估公式
        result = self.evaluate_formula(
            parsed_formula, constant_embeds, constant_map, predicate_map
        )
        
        return result


# ============================================================================
# 第三部分：知识图谱推理系统
# ============================================================================

class EnhancedKnowledgeGraphReasoner(nn.Module):
    """增强的知识图谱推理系统"""
    
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
        
        # 文本编码器（双向LSTM）
        self.text_embedding = nn.Embedding(vocab_size, embedding_dim)
        self.text_encoder = nn.LSTM(
            embedding_dim, hidden_dim // 2, 
            batch_first=True, bidirectional=True
        )
        self.text_projection = nn.Linear(hidden_dim, hidden_dim // 2)
        
        # 逻辑推理器
        self.logic_reasoner = EnhancedDifferentiableFOL(
            num_predicates, num_constants, hidden_dim // 2,
            temperature=1.0, max_entities=max_entities
        )
        
        # 融合网络（输入：文本嵌入 + 逻辑得分 + 辅助预测）
        self.fusion_net = nn.Sequential(
            nn.Linear(hidden_dim // 2 + 2, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim // 2, hidden_dim // 4),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim // 4, 1),
            nn.Sigmoid()
        )
        
        # 辅助预测头
        self.auxiliary_head = nn.Sequential(
            nn.Linear(hidden_dim // 2, hidden_dim // 4),
            nn.ReLU(),
            nn.Linear(hidden_dim // 4, 1),
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
                predicate_map: Dict[str, int],
                adj_matrices: List[torch.Tensor] = None) -> Dict[str, torch.Tensor]:
        """前向传播"""
        batch_size = text_tokens.size(0)
        
        # 文本编码
        text_embeddings = self.encode_text(text_tokens)
        
        # 逻辑推理
        logic_scores = []
        for i in range(batch_size):
            entity_idx = entity_indices[i].unsqueeze(0)
            
            adj = None
            if adj_matrices is not None and i < len(adj_matrices):
                adj = adj_matrices[i]
            
            score = self.logic_reasoner(
                entity_idx, logical_formulas[i],
                constant_maps[i], predicate_map, adj
            )
            
            # 确保score是标量或1D
            if score.dim() == 0:
                score = score.unsqueeze(0)
            elif score.dim() > 1:
                score = score.reshape(-1)
            
            logic_scores.append(score)
        
        # 处理逻辑得分
        logic_scores = torch.stack([s for s in logic_scores])
        logic_scores = logic_scores.reshape(batch_size)
        
        # 辅助预测
        aux_pred = self.auxiliary_head(text_embeddings).squeeze(-1)
        
        # 融合
        combined = torch.cat([
            text_embeddings, 
            logic_scores.unsqueeze(1),
            aux_pred.unsqueeze(1)
        ], dim=1)
        
        confidence = self.fusion_net(combined).squeeze(-1)
        
        return {
            'confidence': confidence,
            'logic_scores': logic_scores,
            'auxiliary_pred': aux_pred,
            'reasoning_history': self.logic_reasoner.get_reasoning_history()
        }


# ============================================================================
# 第四部分：逻辑推理系统
# ============================================================================

class EnhancedLogicReasoningSystem:
    """增强逻辑推理系统 v2.2"""
    
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
        
        self._initialize_domain_knowledge()
    
    def _initialize_domain_knowledge(self):
        """初始化领域知识"""
        base_predicates = [
            'Father', 'Mother', 'Parent', 'Child', 'Spouse',
            'Sibling', 'Grandparent', 'Ancestor', 'Descendant',
            'Brother', 'Sister', 'Son', 'Daughter',
            'Grandchild', 'Colleague', 'Manager', 'Friend'
        ]
        self.predicate_vocab.update(base_predicates)
        self.predicate_map = {pred: idx for idx, pred in enumerate(sorted(self.predicate_vocab))}
    
    def extract_entities_with_context(self, text: str) -> Dict[str, Any]:
        """提取实体"""
        entities = re.findall(r'\b[A-Z][a-z]+\b', text)
        entities = entities[:self.max_entities]
        
        male_names = {'John', 'Michael', 'David', 'Robert', 'Thomas', 'George', 
                     'Bob', 'Frank', 'Kevin', 'Ian', 'James', 'William', 'Richard',
                     'Charles', 'Joseph', 'Daniel', 'Matthew', 'Anthony', 'Mark', 
                     'Tom', 'Jerry'}
        female_names = {'Mary', 'Jennifer', 'Alice', 'Emma', 'Sarah', 'Helen', 
                       'Karen', 'Lisa', 'Carol', 'Grace', 'Linda', 'Barbara',
                       'Susan', 'Jessica', 'Nancy', 'Betty', 'Margaret', 'Dorothy'}
        
        entity_types = {}
        for entity in entities:
            if entity in male_names:
                entity_types[entity] = 'Male'
            elif entity in female_names:
                entity_types[entity] = 'Female'
            else:
                entity_types[entity] = 'Unknown'
        
        # 上下文分析
        text_lower = text.lower()
        family_words = {'father', 'mother', 'son', 'daughter', 'brother', 'sister',
                       'parent', 'child', 'married', 'wife', 'husband', 'family'}
        professional_words = {'work', 'office', 'company', 'manager', 'colleague',
                             'business', 'project', 'employee', 'boss'}
        
        family_score = sum(1 for w in family_words if w in text_lower) * 0.2
        professional_score = sum(1 for w in professional_words if w in text_lower) * 0.2
        
        if family_score > professional_score:
            context_type = 'family'
        elif professional_score > 0:
            context_type = 'professional'
        else:
            context_type = 'general'
        
        unique_entities = list(OrderedDict.fromkeys(entities))
        self.entity_vocab.update(unique_entities)
        
        return {
            'entities': unique_entities,
            'types': entity_types,
            'context_type': context_type,
            'entity_count': len(unique_entities)
        }
    
    def text_to_tokens(self, text: str) -> torch.Tensor:
        """文本转token"""
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
        
        for var in ['x', 'y', 'z', 'p', 'q']:
            constant_map[var] = 0
        
        return constant_map
    
    def create_entity_indices(self, entities: List[str]) -> torch.Tensor:
        """创建实体索引张量"""
        indices = [i + 1 for i in range(len(entities))]
        while len(indices) < self.max_entities:
            indices.append(0)
        return torch.tensor(indices, dtype=torch.long).unsqueeze(0)
    
    def create_adjacency_matrix(self, entities: List[str], 
                                known_facts: List[Tuple[str, str, str]] = None) -> torch.Tensor:
        """创建邻接矩阵"""
        n = self.max_entities
        adj = torch.zeros(n, n)
        
        if known_facts:
            entity_to_idx = {e: i+1 for i, e in enumerate(entities)}
            for pred, subj, obj in known_facts:
                if subj in entity_to_idx and obj in entity_to_idx:
                    i, j = entity_to_idx[subj], entity_to_idx[obj]
                    if i < n and j < n:
                        adj[i, j] = 1.0
                        if pred in ['Spouse', 'Sibling', 'Friend', 'Colleague']:
                            adj[j, i] = 1.0
        
        return adj
    
    def create_sample(self, text: str, target_relation: str,
                     known_facts: List[Tuple[str, str, str]] = None) -> Dict[str, Any]:
        """创建训练样本"""
        entity_info = self.extract_entities_with_context(text)
        entities = entity_info['entities']
        constant_map = self.build_constant_map(entities)
        
        formula_rules = {
            'Parent': 'Father(x,y) ∨ Mother(x,y)',
            'Grandparent': '∃z: Parent(x,z) ∧ Parent(z,y)',
            'Sibling': '∃p: Parent(p,x) ∧ Parent(p,y)',
            'Spouse': 'Spouse(x,y)',
            'Ancestor': 'Parent(x,y) ∨ ∃z: (Parent(x,z) ∧ Ancestor(z,y))',
            'Grandchild': '∃z: Parent(z,x) ∧ Parent(y,z)',
            'Child': 'Child(x,y)',
            'Brother': 'Brother(x,y)',
            'Sister': 'Sister(x,y)',
            'Son': 'Son(x,y)',
            'Daughter': 'Daughter(x,y)',
        }
        
        logical_formula = formula_rules.get(target_relation, f'{target_relation}(x,y)')
        
        return {
            'text': text,
            'text_tokens': self.text_to_tokens(text),
            'entities': entities,
            'entity_info': entity_info,
            'constant_map': constant_map,
            'entity_indices': self.create_entity_indices(entities),
            'logical_formula': logical_formula,
            'adj_matrix': self.create_adjacency_matrix(entities, known_facts),
            'target_relation': target_relation,
            'known_facts': known_facts or []
        }
    
    def initialize_model(self):
        """初始化模型"""
        num_constants = max(len(self.entity_vocab) + 20, self.max_entities + 10)
        num_predicates = len(self.predicate_map)
        
        self.model = EnhancedKnowledgeGraphReasoner(
            vocab_size=self.vocab_size,
            num_predicates=num_predicates,
            num_constants=num_constants,
            embedding_dim=64,
            hidden_dim=128,
            max_entities=self.max_entities,
            max_seq_len=self.max_seq_len
        )
        
        return self.model
    
    def train(self, training_data: List[Dict], epochs: int = 150,
              learning_rate: float = 0.001, batch_size: int = 4):
        """训练过程"""
        if self.model is None:
            self.initialize_model()
        
        optimizer = optim.AdamW(self.model.parameters(), lr=learning_rate, weight_decay=0.01)
        scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(optimizer, T_0=30, T_mult=2)
        criterion = nn.BCELoss()
        
        self.model.train()
        best_loss = float('inf')
        patience = 20
        patience_counter = 0
        best_model_state = None
        
        print(f"\n开始训练 (epochs={epochs}, batch_size={batch_size})...")
        
        for epoch in range(epochs):
            total_loss = 0
            correct = 0
            total = 0
            
            random.shuffle(training_data)
            
            for i in range(0, len(training_data), batch_size):
                batch = training_data[i:i+batch_size]
                
                if len(batch) < 2:
                    continue
                
                try:
                    text_tokens = torch.cat([s['text_tokens'] for s in batch], dim=0)
                    entity_indices = torch.cat([s['entity_indices'] for s in batch], dim=0)
                    formulas = [s['logical_formula'] for s in batch]
                    constant_maps = [s['constant_map'] for s in batch]
                    adj_matrices = [s['adj_matrix'] for s in batch]
                    
                    targets = torch.tensor([1.0 if s.get('is_true', False) else 0.0 
                                          for s in batch], dtype=torch.float32)
                    
                    outputs = self.model(
                        text_tokens, entity_indices, formulas,
                        constant_maps, self.predicate_map, adj_matrices
                    )
                    confidence = outputs['confidence']
                    
                    loss = criterion(confidence, targets)
                    
                    optimizer.zero_grad()
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                    optimizer.step()
                    
                    total_loss += loss.item()
                    
                    predictions = (confidence > 0.5).float()
                    correct += (predictions == targets).sum().item()
                    total += len(targets)
                    
                except Exception as e:
                    print(f"批次错误: {e}")
                    continue
            
            scheduler.step()
            
            if total > 0:
                accuracy = correct / total
                avg_loss = total_loss / max(1, len(training_data) // batch_size)
                
                self.training_history.append({
                    'epoch': epoch,
                    'loss': avg_loss,
                    'accuracy': accuracy,
                    'learning_rate': scheduler.get_last_lr()[0]
                })
                
                if avg_loss < best_loss:
                    best_loss = avg_loss
                    patience_counter = 0
                    best_model_state = {
                        k: v.cpu().clone() for k, v in self.model.state_dict().items()
                    }
                else:
                    patience_counter += 1
                
                if epoch % 25 == 0:
                    print(f'Epoch {epoch:3d} | Loss: {avg_loss:.4f} | Acc: {accuracy:.4f}')
                
                if patience_counter >= patience:
                    print(f"早停于epoch {epoch}")
                    break
        
        if best_model_state:
            self.model.load_state_dict(best_model_state)
            print("已恢复最佳模型")
    
    def predict(self, text: str, target_relation: str,
               known_facts: List[Tuple[str, str, str]] = None) -> Dict[str, Any]:
        """预测"""
        if self.model is None:
            raise ValueError("模型未初始化")
        
        self.model.eval()
        
        sample = self.create_sample(text, target_relation, known_facts)
        
        with torch.no_grad():
            outputs = self.model(
                sample['text_tokens'],
                sample['entity_indices'],
                [sample['logical_formula']],
                [sample['constant_map']],
                self.predicate_map,
                [sample['adj_matrix']]
            )
        
        confidence = outputs['confidence'].item()
        logic_score = outputs['logic_scores'].item() if outputs['logic_scores'].numel() > 0 else 0.5
        
        return {
            'confidence': confidence,
            'logic_score': logic_score,
            'entities': sample['entities'],
            'entity_info': sample['entity_info'],
            'prediction': confidence > 0.5,
            'formula': sample['logical_formula'],
            'reasoning_steps': outputs.get('reasoning_history', []),
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
        
        fig, axes = plt.subplots(1, 2, figsize=(12, 4))
        
        axes[0].plot(epochs, losses, 'b-', linewidth=1.5)
        axes[0].set_xlabel('Epoch')
        axes[0].set_ylabel('Loss')
        axes[0].set_title('Training Loss')
        axes[0].grid(True, alpha=0.3)
        
        axes[1].plot(epochs, accuracies, 'r-', linewidth=1.5)
        axes[1].set_xlabel('Epoch')
        axes[1].set_ylabel('Accuracy')
        axes[1].set_title('Training Accuracy')
        axes[1].grid(True, alpha=0.3)
        axes[1].set_ylim([0, 1])
        
        plt.tight_layout()
        plt.show()
    
    def explain_reasoning(self, prediction_result: Dict[str, Any]):
        """推理解释"""
        print("\n" + "="*60)
        print("推理过程解释")
        print("="*60)
        
        print(f"\n目标关系: {prediction_result.get('target_relation', 'Unknown')}")
        print(f"置信度: {prediction_result['confidence']:.4f}")
        print(f"逻辑得分: {prediction_result['logic_score']:.4f}")
        print(f"预测结果: {'✓ 成立' if prediction_result['prediction'] else '✗ 不成立'}")
        print(f"逻辑公式: {prediction_result['formula']}")
        
        known_facts = prediction_result.get('known_facts', [])
        if known_facts:
            print(f"\n已知事实 ({len(known_facts)}个):")
            for i, fact in enumerate(known_facts):
                print(f"  {i+1}. {fact[0]}({fact[1]}, {fact[2]})")
        
        entity_info = prediction_result.get('entity_info', {})
        if entity_info:
            print(f"\n上下文类型: {entity_info.get('context_type', 'general')}")
            entities = prediction_result['entities']
            types = entity_info.get('types', {})
            for entity in entities:
                print(f"  {entity}: {types.get(entity, 'Unknown')}")
        
        reasoning_steps = prediction_result.get('reasoning_steps', [])
        if reasoning_steps:
            print(f"\n推理步骤:")
            for i, step in enumerate(reasoning_steps[:10]):
                print(f"  {i+1}. {step['step']} ({step['confidence']:.4f})")


# ============================================================================
# 第五部分：数据生成和演示
# ============================================================================

def create_training_data() -> List[Dict]:
    """创建训练数据"""
    system = EnhancedLogicReasoningSystem("family", max_entities=10, max_seq_len=60)
    
    samples = []
    
    # 正例
    positive = [
        ("John is Mary's father. Mary has a son named Tom.", 'Grandparent',
         [('Father', 'John', 'Mary'), ('Parent', 'Mary', 'Tom')], True),
        ("Alice and Bob are married.", 'Spouse',
         [('Spouse', 'Alice', 'Bob')], True),
        ("David is the father of Emma. Emma is the mother of Frank.", 'Grandparent',
         [('Father', 'David', 'Emma'), ('Mother', 'Emma', 'Frank')], True),
        ("George and Helen are siblings.", 'Sibling',
         [('Sibling', 'George', 'Helen')], True),
        ("Michael is Jennifer's father.", 'Parent',
         [('Father', 'Michael', 'Jennifer')], True),
        ("Tom is the son of Mary.", 'Child',
         [('Child', 'Tom', 'Mary')], True),
        ("James is the brother of Emma.", 'Brother',
         [('Brother', 'James', 'Emma')], True),
        ("Grace is the sister of Kevin.", 'Sister',
         [('Sister', 'Grace', 'Kevin')], True),
        ("John is Mary's father. Mary has a son Tom. Tom has a daughter Alice.", 'Ancestor',
         [('Father', 'John', 'Mary'), ('Parent', 'Mary', 'Tom'), ('Parent', 'Tom', 'Alice')], True),
    ]
    
    # 负例
    negative = [
        ("George is Helen's brother. Helen has a son Ian.", 'Parent',
         [('Sibling', 'George', 'Helen'), ('Parent', 'Helen', 'Ian')], False),
        ("Karen and Lisa are colleagues at work.", 'Sibling',
         [('Colleague', 'Karen', 'Lisa')], False),
        ("Michael works with Jennifer.", 'Spouse',
         [('Colleague', 'Michael', 'Jennifer')], False),
        ("Robert is Susan's manager.", 'Parent',
         [('Manager', 'Robert', 'Susan')], False),
        ("David and Emma work together.", 'Sibling',
         [('Colleague', 'David', 'Emma')], False),
        ("Sarah and Thomas are friends.", 'Spouse',
         [('Friend', 'Sarah', 'Thomas')], False),
        ("John is Mary's father.", 'Child',
         [('Father', 'John', 'Mary')], False),
        ("Bob and Frank are old friends.", 'Sibling',
         [('Friend', 'Bob', 'Frank')], False),
    ]
    
    for text, rel, facts, is_true in positive + negative:
        sample = system.create_sample(text, rel, facts)
        sample['is_true'] = is_true
        samples.append(sample)
    
    return samples


def demo():
    """演示系统"""
    print("="*60)
    print("增强版可微分一阶逻辑推理系统 v2.2")
    print("="*60)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"设备: {device}")
    
    torch.manual_seed(42)
    np.random.seed(42)
    random.seed(42)
    
    print("\n初始化系统...")
    system = EnhancedLogicReasoningSystem("family", max_entities=10, max_seq_len=60)
    
    print("创建训练数据...")
    training_data = create_training_data()
    print(f"样本数: {len(training_data)}")
    print(f"正例: {sum(1 for s in training_data if s['is_true'])}")
    print(f"负例: {sum(1 for s in training_data if not s['is_true'])}")
    
    print("\n初始化模型...")
    model = system.initialize_model()
    print(f"参数: {sum(p.numel() for p in model.parameters()):,}")
    
    print("\n开始训练...")
    system.train(training_data, epochs=150, batch_size=4, learning_rate=0.001)
    
    print("\n绘制训练历史...")
    system.plot_training_history()
    
    print("\n运行测试...")
    tests = [
        ("Michael is Jennifer's father. Jennifer has a son named Kevin.", 'Grandparent',
         [('Father', 'Michael', 'Jennifer'), ('Parent', 'Jennifer', 'Kevin')], True),
        ("Sarah and Thomas are married.", 'Spouse',
         [('Spouse', 'Sarah', 'Thomas')], True),
        ("David and Emma are brother and sister.", 'Sibling',
         [('Sibling', 'David', 'Emma')], True),
        ("Robert and Susan work in the same office.", 'Sibling',
         [('Colleague', 'Robert', 'Susan')], False),
        ("Lisa is Karen's manager.", 'Parent',
         [('Manager', 'Lisa', 'Karen')], False),
        ("John is Mary's father.", 'Child',
         [('Father', 'John', 'Mary')], False),
        ("John is Mary's father. Mary has a son Tom. Tom has a daughter Alice.", 'Ancestor',
         [('Father', 'John', 'Mary'), ('Parent', 'Mary', 'Tom'), ('Parent', 'Tom', 'Alice')], True),
    ]
    
    correct = 0
    for i, (text, rel, facts, expected) in enumerate(tests):
        result = system.predict(text, rel, facts)
        is_correct = result['prediction'] == expected
        if is_correct:
            correct += 1
        
        status = "✅" if is_correct else "❌"
        print(f"\n{status} 测试{i+1}: {rel}")
        print(f"   文本: {text[:50]}...")
        print(f"   期望: {expected}, 预测: {result['prediction']}, 置信度: {result['confidence']:.4f}")
    
    print(f"\n准确率: {correct}/{len(tests)} = {correct/len(tests):.2%}")
    
    # 详细解释
    print("\n" + "="*60)
    print("详细推理示例")
    print("="*60)
    result = system.predict(
        "John is Mary's father. Mary has a son Tom. Tom has a daughter Alice.",
        'Ancestor',
        [('Father', 'John', 'Mary'), ('Parent', 'Mary', 'Tom'), ('Parent', 'Tom', 'Alice')]
    )
    system.explain_reasoning(result)
    
    return system, training_data


if __name__ == "__main__":
    system, training_data = demo()