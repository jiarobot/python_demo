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

class AdvancedDifferentiableFOL(nn.Module):
    """
    高级可微分一阶逻辑推理系统
    修复了所有维度不匹配问题
    """
    
    def __init__(self, num_predicates: int, num_constants: int, 
                 embedding_dim: int = 128, temperature: float = 1.0,
                 use_attention: bool = True, max_entities: int = 20):
        super().__init__()
        
        self.num_predicates = num_predicates
        self.num_constants = num_constants
        self.embedding_dim = embedding_dim
        self.temperature = temperature
        self.use_attention = use_attention
        self.max_entities = max_entities
        
        # 谓词嵌入
        self.predicate_embeddings = nn.Embedding(num_predicates, embedding_dim)
        
        # 常量嵌入
        self.constant_embeddings = nn.Embedding(num_constants, embedding_dim)
        
        # 关系推理网络 - 修复维度问题
        self.relation_net = nn.Sequential(
            nn.Linear(embedding_dim * 3, embedding_dim * 2),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(embedding_dim * 2, embedding_dim),
            nn.ReLU(),
            nn.Linear(embedding_dim, 1)
        )
        
        # 初始化
        self._initialize_weights()
        
        # 缓存解析的公式
        self.formula_cache = {}
    
    def _initialize_weights(self):
        """权重初始化"""
        nn.init.normal_(self.predicate_embeddings.weight, mean=0.0, std=0.02)
        nn.init.normal_(self.constant_embeddings.weight, mean=0.0, std=0.02)
        
        for layer in self.relation_net:
            if isinstance(layer, nn.Linear):
                nn.init.xavier_uniform_(layer.weight)
                nn.init.zeros_(layer.bias)
    
    def safe_embedding_lookup(self, embedding_layer, indices):
        """安全的嵌入查找，处理索引越界"""
        max_idx = embedding_layer.num_embeddings
        safe_indices = torch.clamp(indices, 0, max_idx - 1)
        return embedding_layer(safe_indices)
    
    def soft_forall(self, embeddings: torch.Tensor, dim: int = 1) -> torch.Tensor:
        """软全称量词"""
        # 使用log-sum-exp近似最小值
        return -torch.logsumexp(-embeddings * self.temperature, dim=dim)
    
    def soft_exists(self, embeddings: torch.Tensor, dim: int = 1) -> torch.Tensor:
        """软存在量词"""
        # 使用log-sum-exp近似最大值
        return torch.logsumexp(embeddings * self.temperature, dim=dim) / self.temperature
    
    def soft_and(self, x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
        """软逻辑与"""
        return x * y
    
    def soft_or(self, x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
        """软逻辑或"""
        return 1 - (1 - x) * (1 - y)
    
    def soft_not(self, x: torch.Tensor) -> torch.Tensor:
        """软逻辑非"""
        return 1 - x
    
    def soft_implies(self, x: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
        """软蕴含"""
        return self.soft_or(self.soft_not(x), y)
    
    def relation_score(self, subject_emb: torch.Tensor, predicate_emb: torch.Tensor, 
                      object_emb: torch.Tensor) -> torch.Tensor:
        """计算三元组关系得分 - 修复维度问题"""
        # 确保所有张量都是3D [batch_size, 1, embed_dim]
        if subject_emb.dim() == 2:
            subject_emb = subject_emb.unsqueeze(1)
        if object_emb.dim() == 2:
            object_emb = object_emb.unsqueeze(1)
        if predicate_emb.dim() == 1:
            predicate_emb = predicate_emb.unsqueeze(0).unsqueeze(1)
        elif predicate_emb.dim() == 2:
            predicate_emb = predicate_emb.unsqueeze(1)
        
        # 现在所有张量都是 [batch_size, 1, embed_dim]
        # 拼接所有嵌入
        combined = torch.cat([subject_emb, predicate_emb, object_emb], dim=-1)
        
        # 通过关系网络
        score = self.relation_net(combined)
        return torch.sigmoid(score).squeeze(-1).squeeze(-1)  # 返回 [batch_size]
    
    def parse_formula_advanced(self, formula: str) -> Dict[str, Any]:
        """公式解析器"""
        formula = formula.strip()
        
        # 检查缓存
        if formula in self.formula_cache:
            return self.formula_cache[formula]
        
        # 处理括号
        if formula.startswith('(') and formula.endswith(')'):
            return self.parse_formula_advanced(formula[1:-1])
        
        # 原子谓词: P(s, o) 或 P(x)
        atom_match = re.match(r'(\w+)\(([^,)]+)(?:,\s*([^)]+))?\)', formula)
        if atom_match:
            predicate = atom_match.group(1)
            subject = atom_match.group(2)
            obj = atom_match.group(3) if atom_match.group(3) else None
            
            result = {
                'type': 'atom',
                'predicate': predicate,
                'subject': subject,
                'object': obj
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
                    'subformula': self.parse_formula_advanced(subformula)
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
                    'subformula': self.parse_formula_advanced(subformula)
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
                            'left': self.parse_formula_advanced(left),
                            'right': self.parse_formula_advanced(right)
                        }
                    elif op == '∨':
                        return {
                            'type': 'or',
                            'left': self.parse_formula_advanced(left),
                            'right': self.parse_formula_advanced(right)
                        }
                    elif op == '→':
                        return {
                            'type': 'implies',
                            'left': self.parse_formula_advanced(left),
                            'right': self.parse_formula_advanced(right)
                        }
        
        # 否定: ¬φ
        if formula.startswith('¬'):
            subformula = formula[1:].strip()
            return {
                'type': 'not',
                'subformula': self.parse_formula_advanced(subformula)
            }
        
        # 简单原子谓词
        result = {'type': 'atom', 'predicate': formula}
        self.formula_cache[formula] = result
        return result
    
    def evaluate_parsed_formula(self, parsed_formula: Dict, 
                               constant_embeddings: torch.Tensor,
                               constant_map: Dict[str, int],
                               predicate_map: Dict[str, int],
                               variable_bindings: Dict[str, int] = None) -> torch.Tensor:
        """评估解析后的逻辑公式 - 修复所有维度问题"""
        if variable_bindings is None:
            variable_bindings = {}
        
        formula_type = parsed_formula['type']
        batch_size, num_constants, embed_dim = constant_embeddings.shape
        
        if formula_type == 'atom':
            atom_data = parsed_formula
            pred_name = atom_data['predicate']
            
            # 获取谓词嵌入
            if pred_name not in predicate_map:
                # 如果谓词不存在，返回中性值
                return torch.ones(batch_size, device=constant_embeddings.device) * 0.5
            
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
                
                # 解析主体和客体索引
                try:
                    subj_idx = self._resolve_entity(subj_name, constant_map, variable_bindings)
                    obj_idx = self._resolve_entity(obj_name, constant_map, variable_bindings)
                    
                    # 确保索引在有效范围内
                    subj_idx = min(subj_idx, num_constants - 1)
                    obj_idx = min(obj_idx, num_constants - 1)
                    
                    subj_emb = constant_embeddings[:, subj_idx]  # [batch_size, embed_dim]
                    obj_emb = constant_embeddings[:, obj_idx]    # [batch_size, embed_dim]
                    
                    return self.relation_score(subj_emb, pred_emb, obj_emb)
                except (KeyError, IndexError):
                    # 如果实体不存在，返回中性值
                    return torch.ones(batch_size, device=constant_embeddings.device) * 0.5
            else:
                # 一元谓词 P(x)
                entity_name = atom_data.get('subject', 'x')
                try:
                    entity_idx = self._resolve_entity(entity_name, constant_map, variable_bindings)
                    entity_idx = min(entity_idx, num_constants - 1)
                    entity_emb = constant_embeddings[:, entity_idx]  # [batch_size, embed_dim]
                    
                    # 计算相似度 - 修复维度
                    pred_emb_expanded = pred_emb.unsqueeze(0).expand(batch_size, -1)  # [batch_size, embed_dim]
                    similarity = F.cosine_similarity(entity_emb, pred_emb_expanded, dim=-1)
                    return torch.sigmoid(similarity * 5.0)
                except (KeyError, IndexError):
                    return torch.ones(batch_size, device=constant_embeddings.device) * 0.5
        
        elif formula_type == 'forall':
            results = []
            
            # 为每个可能的变量绑定进行评估
            for i in range(num_constants):
                new_bindings = variable_bindings.copy()
                new_bindings[parsed_formula['variable']] = i
                
                result = self.evaluate_parsed_formula(
                    parsed_formula['subformula'], constant_embeddings, 
                    constant_map, predicate_map, new_bindings
                )
                results.append(result.unsqueeze(1))
            
            if results:
                results = torch.cat(results, dim=1)  # [batch_size, num_constants]
                return self.soft_forall(results, dim=1)
            else:
                return torch.ones(batch_size, device=constant_embeddings.device) * 0.5
        
        elif formula_type == 'exists':
            results = []
            
            for i in range(num_constants):
                new_bindings = variable_bindings.copy()
                new_bindings[parsed_formula['variable']] = i
                
                result = self.evaluate_parsed_formula(
                    parsed_formula['subformula'], constant_embeddings,
                    constant_map, predicate_map, new_bindings
                )
                results.append(result.unsqueeze(1))
            
            if results:
                results = torch.cat(results, dim=1)
                return self.soft_exists(results, dim=1)
            else:
                return torch.ones(batch_size, device=constant_embeddings.device) * 0.5
        
        elif formula_type == 'and':
            left_result = self.evaluate_parsed_formula(
                parsed_formula['left'], constant_embeddings,
                constant_map, predicate_map, variable_bindings
            )
            right_result = self.evaluate_parsed_formula(
                parsed_formula['right'], constant_embeddings,
                constant_map, predicate_map, variable_bindings
            )
            return self.soft_and(left_result, right_result)
        
        elif formula_type == 'or':
            left_result = self.evaluate_parsed_formula(
                parsed_formula['left'], constant_embeddings,
                constant_map, predicate_map, variable_bindings
            )
            right_result = self.evaluate_parsed_formula(
                parsed_formula['right'], constant_embeddings,
                constant_map, predicate_map, variable_bindings
            )
            return self.soft_or(left_result, right_result)
        
        elif formula_type == 'not':
            sub_result = self.evaluate_parsed_formula(
                parsed_formula['subformula'], constant_embeddings,
                constant_map, predicate_map, variable_bindings
            )
            return self.soft_not(sub_result)
        
        elif formula_type == 'implies':
            left_result = self.evaluate_parsed_formula(
                parsed_formula['left'], constant_embeddings,
                constant_map, predicate_map, variable_bindings
            )
            right_result = self.evaluate_parsed_formula(
                parsed_formula['right'], constant_embeddings,
                constant_map, predicate_map, variable_bindings
            )
            return self.soft_implies(left_result, right_result)
        
        else:
            # 未知类型，返回中性值
            return torch.ones(batch_size, device=constant_embeddings.device) * 0.5
    
    def _resolve_entity(self, entity_name: str, constant_map: Dict[str, int], 
                       variable_bindings: Dict[str, int]) -> int:
        """解析实体名称到索引"""
        if entity_name in variable_bindings:
            return variable_bindings[entity_name]
        elif entity_name in constant_map:
            return constant_map[entity_name]
        else:
            # 如果实体不存在，返回0索引
            return 0
    
    def forward(self, entity_indices: torch.Tensor, logical_formula: str,
                constant_map: Dict[str, int], predicate_map: Dict[str, int]) -> torch.Tensor:
        """
        前向传播
        """
        batch_size, num_entities = entity_indices.shape
        
        # 安全地获取常量嵌入
        constant_embeds = self.safe_embedding_lookup(
            self.constant_embeddings, entity_indices
        )  # [batch_size, num_entities, embed_dim]
        
        # 解析逻辑公式
        try:
            parsed_formula = self.parse_formula_advanced(logical_formula)
        except Exception as e:
            print(f"公式解析失败: {e}, 使用默认公式")
            parsed_formula = {'type': 'atom', 'predicate': 'Default'}
        
        # 评估公式
        result = self.evaluate_parsed_formula(
            parsed_formula, constant_embeds, constant_map, predicate_map
        )
        
        return result

class KnowledgeGraphReasoner(nn.Module):
    """
    知识图谱推理系统 - 修复所有维度问题
    """
    
    def __init__(self, vocab_size: int, num_predicates: int, num_constants: int,
                 embedding_dim: int = 128, hidden_dim: int = 256, 
                 max_entities: int = 10, max_seq_len: int = 50):
        super().__init__()
        
        self.vocab_size = vocab_size
        self.num_predicates = num_predicates
        self.num_constants = num_constants
        self.embedding_dim = embedding_dim
        self.max_entities = max_entities
        self.max_seq_len = max_seq_len
        
        # 文本编码器 - 简化版本
        self.text_embedding = nn.Embedding(vocab_size, embedding_dim)
        self.text_encoder = nn.LSTM(embedding_dim, hidden_dim // 2, batch_first=True, bidirectional=True)
        self.text_projection = nn.Linear(hidden_dim, hidden_dim // 2)
        
        # 可微分逻辑推理层
        self.logic_reasoner = AdvancedDifferentiableFOL(
            num_predicates, num_constants, hidden_dim // 2, 
            temperature=2.0, use_attention=False,  # 暂时关闭注意力
            max_entities=max_entities
        )
        
        # 融合网络
        self.fusion_net = nn.Sequential(
            nn.Linear(hidden_dim // 2 + 1, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim // 2, hidden_dim // 4),
            nn.ReLU(),
            nn.Linear(hidden_dim // 4, 1),
            nn.Sigmoid()
        )
    
    def encode_text(self, text_tokens: torch.Tensor) -> torch.Tensor:
        """编码文本"""
        # text_tokens: [batch_size, seq_len]
        embedded = self.text_embedding(text_tokens)  # [batch_size, seq_len, embed_dim]
        
        # 通过LSTM
        lstm_out, (hidden, _) = self.text_encoder(embedded)
        
        # 使用双向LSTM的最后隐藏状态
        hidden = torch.cat([hidden[0], hidden[1]], dim=-1)  # [batch_size, hidden_dim]
        
        return self.text_projection(hidden)  # [batch_size, hidden_dim//2]
    
    def forward(self, text_tokens: torch.Tensor, entity_indices: torch.Tensor,
                logical_formulas: List[str], constant_maps: List[Dict[str, int]],
                predicate_map: Dict[str, int]) -> Dict[str, torch.Tensor]:
        """
        前向传播 - 修复所有维度问题
        """
        batch_size = text_tokens.size(0)
        
        # 文本编码
        text_embeddings = self.encode_text(text_tokens)  # [batch_size, hidden_dim//2]
        
        # 逻辑推理
        logic_scores = []
        for i in range(batch_size):
            # 确保entity_indices有正确的形状 [1, max_entities]
            entity_idx = entity_indices[i].unsqueeze(0)  # [1, max_entities]
                
            score = self.logic_reasoner(
                entity_idx,
                logical_formulas[i],
                constant_maps[i],
                predicate_map
            )
            logic_scores.append(score)
        
        # 确保所有logic_scores都是标量
        logic_scores = torch.stack([score if score.dim() == 0 else score.mean() for score in logic_scores])
        logic_scores = logic_scores.reshape(batch_size)  # [batch_size]
        
        # 融合文本和逻辑信息
        combined = torch.cat([text_embeddings, logic_scores.unsqueeze(1)], dim=1)
        confidence = self.fusion_net(combined).squeeze(-1)
        
        return {
            'confidence': confidence,
            'logic_scores': logic_scores,
        }

# 完整的应用系统
class AdvancedLogicReasoningSystem:
    """
    高级逻辑推理系统 - 完全修复版本
    """
    
    def __init__(self, domain: str = "family", max_entities: int = 10, max_seq_len: int = 50):
        self.domain = domain
        self.max_entities = max_entities
        self.max_seq_len = max_seq_len
        self.predicate_map = {}
        self.constant_map = {}
        self.model = None
        self.entity_vocab = set()
        self.predicate_vocab = set()
        self.vocab_size = 1000
        
        # 初始化领域特定的逻辑规则
        self._initialize_domain_rules()
    
    def _initialize_domain_rules(self):
        """初始化领域特定的逻辑规则"""
        if self.domain == "family":
            base_predicates = ['Father', 'Mother', 'Parent', 'Child', 'Spouse', 
                             'Sibling', 'Grandparent', 'Ancestor', 'Descendant']
            self.predicate_vocab.update(base_predicates)
        
        # 构建谓词映射
        self.predicate_map = {pred: idx for idx, pred in enumerate(sorted(self.predicate_vocab))}
    
    def extract_entities_from_text(self, text: str) -> List[str]:
        """从文本中提取实体"""
        # 简单实体提取：提取大写单词作为实体
        entities = re.findall(r'\b[A-Z][a-z]+\b', text)
        
        # 限制实体数量
        entities = entities[:self.max_entities]
        
        # 去重并添加到词汇表
        unique_entities = list(OrderedDict.fromkeys(entities))
        self.entity_vocab.update(unique_entities)
        
        return unique_entities
    
    def text_to_tokens(self, text: str) -> torch.Tensor:
        """将文本转换为token张量"""
        # 简单的字符级tokenization
        tokens = []
        for char in text[:self.max_seq_len]:
            token_id = ord(char) % self.vocab_size
            tokens.append(token_id)
        
        # 填充到固定长度
        while len(tokens) < self.max_seq_len:
            tokens.append(0)  # 0作为padding
        
        return torch.tensor(tokens, dtype=torch.long).unsqueeze(0)  # [1, max_seq_len]
    
    def build_constant_map(self, entities: List[str]) -> Dict[str, int]:
        """构建常量映射"""
        # 为实体分配索引，从1开始（0保留给padding）
        constant_map = {}
        for idx, entity in enumerate(entities):
            constant_map[entity] = idx + 1  # 从1开始
        
        # 添加默认实体
        constant_map['x'] = 0
        constant_map['y'] = 0
        constant_map['z'] = 0
        
        return constant_map
    
    def create_entity_indices(self, entities: List[str]) -> torch.Tensor:
        """创建实体索引张量"""
        # 创建实体索引，从1开始
        indices = [i + 1 for i in range(len(entities))]
        
        # 填充到最大实体数
        while len(indices) < self.max_entities:
            indices.append(0)  # 0作为padding
        
        return torch.tensor(indices, dtype=torch.long).unsqueeze(0)  # [1, max_entities]
    
    def create_training_sample(self, text: str, target_relation: str, 
                              known_facts: List[Tuple[str, str, str]] = None) -> Dict[str, Any]:
        """创建训练样本"""
        # 提取实体
        entities = self.extract_entities_from_text(text)
        constant_map = self.build_constant_map(entities)
        
        # 构建逻辑公式
        logical_formula = self._build_formula_for_relation(target_relation, entities, known_facts)
        
        # 创建实体索引张量
        entity_indices = self.create_entity_indices(entities)
        
        # 创建文本token
        text_tokens = self.text_to_tokens(text)
        
        return {
            'text': text,
            'text_tokens': text_tokens,
            'entities': entities,
            'constant_map': constant_map,
            'entity_indices': entity_indices,
            'logical_formula': logical_formula,
            'target_relation': target_relation,
            'known_facts': known_facts or []
        }
    
    def _build_formula_for_relation(self, target_relation: str, entities: List[str],
                                   known_facts: List[Tuple[str, str, str]] = None) -> str:
        """为目标关系构建逻辑公式"""
        if target_relation == 'Parent':
            return 'Father(x,y) ∨ Mother(x,y)'
        elif target_relation == 'Grandparent':
            return '∃z: Parent(x,z) ∧ Parent(z,y)'
        elif target_relation == 'Sibling':
            return '∃p: Parent(p,x) ∧ Parent(p,y)'
        elif target_relation == 'Spouse':
            return 'Spouse(x,y)'
        elif target_relation == 'Ancestor':
            return 'Parent(x,y) ∨ ∃z: (Parent(x,z) ∧ Ancestor(z,y))'
        else:
            # 默认使用直接关系
            return f'{target_relation}(x,y)'
    
    def initialize_model(self):
        """初始化模型"""
        num_constants = max(len(self.entity_vocab) + 10, self.max_entities + 5)
        num_predicates = len(self.predicate_map)
        
        self.model = KnowledgeGraphReasoner(
            vocab_size=self.vocab_size,
            num_predicates=num_predicates,
            num_constants=num_constants,
            embedding_dim=64,  # 进一步减少维度
            hidden_dim=128,
            max_entities=self.max_entities,
            max_seq_len=self.max_seq_len
        )
        
        return self.model
    
    def train(self, training_data: List[Dict], epochs: int = 30, 
              learning_rate: float = 0.001, batch_size: int = 2):
        """训练系统"""
        if self.model is None:
            self.initialize_model()
        
        optimizer = optim.Adam(self.model.parameters(), lr=learning_rate)
        criterion = nn.BCELoss()
        
        self.model.train()
        
        for epoch in range(epochs):
            total_loss = 0
            correct = 0
            total = 0
            
            # 随机打乱数据
            random.shuffle(training_data)
            
            # 批次处理
            for i in range(0, len(training_data), batch_size):
                batch = training_data[i:i+batch_size]
                
                if len(batch) == 0:
                    continue
                
                try:
                    # 准备批次数据 - 确保所有张量具有相同的形状
                    text_tokens = torch.cat([sample['text_tokens'] for sample in batch], dim=0)
                    entity_indices = torch.cat([sample['entity_indices'] for sample in batch], dim=0)
                    formulas = [sample['logical_formula'] for sample in batch]
                    constant_maps = [sample['constant_map'] for sample in batch]
                    
                    # 创建目标张量
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
                    optimizer.step()
                    
                    total_loss += loss.item()
                    
                    # 计算准确率
                    predictions = (confidence > 0.5).float()
                    correct += (predictions == targets).sum().item()
                    total += len(targets)
                    
                except Exception as e:
                    print(f"训练批次时出错: {e}")
                    continue
            
            if total > 0:
                accuracy = correct / total
                avg_loss = total_loss / max(1, len(training_data) / batch_size)
                
                if epoch % 5 == 0:
                    print(f'Epoch {epoch:3d} | Loss: {avg_loss:.4f} | Accuracy: {accuracy:.4f}')
    
    def predict(self, text: str, target_relation: str, 
                known_facts: List[Tuple[str, str, str]] = None) -> Dict[str, Any]:
        """预测关系"""
        if self.model is None:
            raise ValueError("模型未初始化，请先训练或加载模型")
        
        self.model.eval()
        
        # 创建样本
        sample = self.create_training_sample(text, target_relation, known_facts)
        
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
        
        return {
            'confidence': confidence,
            'logic_score': logic_score,
            'entities': sample['entities'],
            'prediction': confidence > 0.5,
            'formula': sample['logical_formula']
        }

# 示例使用和测试
def create_sample_family_data() -> List[Dict]:
    """创建示例家庭关系数据"""
    samples = []
    
    # 正例样本
    positive_samples = [
        {
            'text': "John is Mary father. Mary has a son named Tom.",
            'target_relation': 'Grandparent',
            'known_facts': [('Father', 'John', 'Mary'), ('Parent', 'Mary', 'Tom')],
            'is_true': True
        },
        {
            'text': "Alice and Bob are married. They have a daughter Carol.",
            'target_relation': 'Spouse', 
            'known_facts': [('Spouse', 'Alice', 'Bob'), ('Parent', 'Alice', 'Carol')],
            'is_true': True
        }
    ]
    
    # 反例样本
    negative_samples = [
        {
            'text': "George is Helen brother. Helen has a son Ian.",
            'target_relation': 'Parent',
            'known_facts': [('Sibling', 'George', 'Helen'), ('Parent', 'Helen', 'Ian')],
            'is_true': False
        }
    ]
    
    # 创建训练样本
    system = AdvancedLogicReasoningSystem("family", max_entities=8, max_seq_len=40)
    
    for sample in positive_samples + negative_samples:
        training_sample = system.create_training_sample(
            sample['text'], sample['target_relation'], sample['known_facts']
        )
        training_sample['is_true'] = sample['is_true']
        samples.append(training_sample)
    
    return samples

def demo_advanced_system():
    """演示高级系统功能"""
    print("初始化高级逻辑推理系统...")
    system = AdvancedLogicReasoningSystem("family", max_entities=8, max_seq_len=40)
    
    print("创建训练数据...")
    training_data = create_sample_family_data()
    print(f"创建了 {len(training_data)} 个训练样本")
    
    print("初始化模型...")
    system.initialize_model()
    
    print("开始训练...")
    system.train(training_data, epochs=20, batch_size=2, learning_rate=0.001)
    
    print("\n运行推理演示...")
    test_cases = [
        {
            'text': "Michael is Jennifer father. Jennifer has a son named Kevin.",
            'relation': 'Grandparent',
            'facts': [('Father', 'Michael', 'Jennifer'), ('Parent', 'Jennifer', 'Kevin')]
        },
        {
            'text': "Sarah and Thomas are married.",
            'relation': 'Spouse', 
            'facts': [('Spouse', 'Sarah', 'Thomas')]
        }
    ]
    
    for i, test_case in enumerate(test_cases):
        print(f"\n测试案例 {i+1}:")
        print(f"文本: {test_case['text']}")
        print(f"目标关系: {test_case['relation']}")
        
        result = system.predict(
            test_case['text'], 
            test_case['relation'],
            test_case['facts']
        )
        
        print(f"预测结果: {'成立' if result['prediction'] else '不成立'}")
        print(f"置信度: {result['confidence']:.4f}")
        print(f"逻辑得分: {result['logic_score']:.4f}")
        print(f"使用的公式: {result['formula']}")
        print(f"识别到的实体: {', '.join(result['entities'])}")

if __name__ == "__main__":
    # 设置设备
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"使用设备: {device}")
    
    # 设置随机种子
    torch.manual_seed(42)
    np.random.seed(42)
    random.seed(42)
    
    # 运行演示
    demo_advanced_system()