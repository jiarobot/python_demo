"""
精确版可微分一阶逻辑推理系统 v2.3
修复：过拟合、泛化、逻辑推理强度
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import numpy as np
import re
import math
import sys
from typing import List, Dict, Tuple, Any, Optional
from collections import defaultdict, OrderedDict
import random
import matplotlib.pyplot as plt
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

sys.setrecursionlimit(10000)


# ============================================================================
# 可微分一阶逻辑系统（简化但有效）
# ============================================================================

class DifferentiableFOL(nn.Module):
    """简化版可微分一阶逻辑推理系统"""
    
    def __init__(self, num_predicates: int, num_constants: int, 
                 embedding_dim: int = 64, max_entities: int = 20):
        super().__init__()
        
        self.num_predicates = num_predicates
        self.num_constants = num_constants
        self.embedding_dim = embedding_dim
        self.max_entities = max_entities
        
        # 嵌入层 - 使用更小的初始化防止过拟合
        self.predicate_embeddings = nn.Embedding(num_predicates, embedding_dim)
        self.constant_embeddings = nn.Embedding(num_constants, embedding_dim)
        
        # 关系评分网络 - 更简单的架构
        self.relation_scorer = nn.Sequential(
            nn.Linear(embedding_dim * 3, embedding_dim),
            nn.LayerNorm(embedding_dim),
            nn.ReLU(),
            nn.Dropout(0.4),  # 高dropout防止过拟合
            nn.Linear(embedding_dim, embedding_dim // 2),
            nn.LayerNorm(embedding_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(embedding_dim // 2, 1)
        )
        
        # 谓词知识
        self.predicate_knowledge = {
            'Father': {'certainty': 0.95, 'type': 'parent'},
            'Mother': {'certainty': 0.95, 'type': 'parent'},
            'Parent': {'certainty': 0.90, 'type': 'parent'},
            'Child': {'certainty': 0.90, 'type': 'child'},
            'Spouse': {'certainty': 0.85, 'type': 'spouse', 'symmetric': True},
            'Sibling': {'certainty': 0.80, 'type': 'sibling', 'symmetric': True},
            'Grandparent': {'certainty': 0.75, 'type': 'extended'},
            'Grandchild': {'certainty': 0.75, 'type': 'extended'},
            'Brother': {'certainty': 0.85, 'type': 'sibling'},
            'Sister': {'certainty': 0.85, 'type': 'sibling'},
            'Son': {'certainty': 0.85, 'type': 'child'},
            'Daughter': {'certainty': 0.85, 'type': 'child'},
            'Ancestor': {'certainty': 0.70, 'type': 'extended'},
            'Descendant': {'certainty': 0.70, 'type': 'extended'},
            'Colleague': {'certainty': 0.60, 'type': 'professional', 'symmetric': True},
            'Manager': {'certainty': 0.70, 'type': 'professional'},
            'Friend': {'certainty': 0.50, 'type': 'social', 'symmetric': True}
        }
        
        self.formula_cache = {}
        self.reasoning_history = []
        
        self._init_weights()
    
    def _init_weights(self):
        """小权重初始化"""
        nn.init.normal_(self.predicate_embeddings.weight, mean=0, std=0.02)
        nn.init.normal_(self.constant_embeddings.weight, mean=0, std=0.02)
        for m in self.relation_scorer:
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight, gain=0.5)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
    
    def safe_lookup(self, emb_layer, indices):
        max_idx = emb_layer.num_embeddings
        return emb_layer(torch.clamp(indices, 0, max_idx - 1))
    
    # 逻辑操作（使用软版本）
    def soft_and(self, x, y):
        return x * y
    
    def soft_or(self, x, y):
        return x + y - x * y
    
    def soft_not(self, x):
        return 1.0 - x
    
    def soft_implies(self, x, y):
        return torch.clamp(1.0 - x + y, 0.0, 1.0)
    
    def soft_forall(self, x, dim=1):
        """软全称量词"""
        n = x.size(dim)
        if n == 0:
            return torch.ones(x.size(0), device=x.device)
        # 使用几何平均的软版本
        return torch.prod(torch.clamp(x, 1e-7, 1.0), dim=dim) ** (1.0 / n)
    
    def soft_exists(self, x, dim=1):
        """软存在量词"""
        n = x.size(dim)
        if n == 0:
            return torch.zeros(x.size(0), device=x.device)
        # 使用补集的几何平均
        return 1.0 - torch.prod(torch.clamp(1.0 - x, 1e-7, 1.0), dim=dim) ** (1.0 / n)
    
    def compute_relation_score(self, subj_emb, pred_emb, obj_emb, pred_name=None):
        """计算关系评分"""
        batch_size = subj_emb.size(0)
        
        # 确保维度正确
        if pred_emb.dim() == 1:
            pred_emb = pred_emb.unsqueeze(0).expand(batch_size, -1)
        if subj_emb.dim() > 2:
            subj_emb = subj_emb.reshape(batch_size, -1)
        if obj_emb.dim() > 2:
            obj_emb = obj_emb.reshape(batch_size, -1)
        
        # 拼接嵌入
        combined = torch.cat([subj_emb, pred_emb, obj_emb], dim=-1)
        
        # 评分
        raw_score = self.relation_scorer(combined).squeeze(-1)
        score = torch.sigmoid(raw_score)
        
        # 应用谓词知识
        if pred_name and pred_name in self.predicate_knowledge:
            knowledge = self.predicate_knowledge[pred_name]
            certainty = knowledge.get('certainty', 0.7)
            
            if knowledge.get('symmetric', False):
                # 对称关系：检查双向一致性
                rev_combined = torch.cat([obj_emb, pred_emb, subj_emb], dim=-1)
                rev_score = torch.sigmoid(self.relation_scorer(rev_combined).squeeze(-1))
                score = (score + rev_score) / 2
            
            score = score * certainty
        
        return torch.clamp(score, 0.001, 0.999)
    
    def parse_formula(self, formula: str) -> Dict:
        """解析逻辑公式"""
        formula = formula.strip()
        
        if formula in self.formula_cache:
            return self.formula_cache[formula]
        
        # 括号处理
        if formula.startswith('(') and formula.endswith(')'):
            depth = 0
            for i, c in enumerate(formula[:-1]):
                if c == '(': depth += 1
                elif c == ')': depth -= 1
                if depth == 0:
                    break
            if depth == 0 and i == len(formula) - 2:
                return self.parse_formula(formula[1:-1])
        
        # 原子谓词: P(s, o)
        atom_match = re.match(r'(\w+)\(([^,)]+)(?:,\s*([^)]+))?\)', formula)
        if atom_match:
            result = {
                'type': 'atom',
                'predicate': atom_match.group(1),
                'subject': atom_match.group(2),
                'object': atom_match.group(3) if atom_match.group(3) else None
            }
            self.formula_cache[formula] = result
            return result
        
        # 量词
        for prefix, qtype in [('∀', 'forall'), ('∃', 'exists')]:
            if formula.startswith(prefix):
                match = re.match(rf'{prefix}([^:]+):(.+)', formula)
                if match:
                    return {
                        'type': qtype,
                        'variable': match.group(1).strip(),
                        'subformula': self.parse_formula(match.group(2).strip())
                    }
        
        # 逻辑连接词（优先级从低到高）
        for op, optype in [('∨', 'or'), ('∧', 'and'), ('→', 'implies')]:
            depth = 0
            for i, c in enumerate(formula):
                if c == '(': depth += 1
                elif c == ')': depth -= 1
                elif c == op and depth == 0:
                    return {
                        'type': optype,
                        'left': self.parse_formula(formula[:i].strip()),
                        'right': self.parse_formula(formula[i+1:].strip())
                    }
        
        # 否定
        if formula.startswith('¬'):
            return {
                'type': 'not',
                'subformula': self.parse_formula(formula[1:].strip())
            }
        
        # 默认原子
        result = {'type': 'atom', 'predicate': formula}
        self.formula_cache[formula] = result
        return result
    
    def _resolve_entity(self, name, constant_map, bindings):
        if name in bindings:
            return bindings[name]
        if name in constant_map:
            return constant_map[name]
        return 0
    
    def evaluate(self, parsed, const_embeds, const_map, pred_map, bindings=None):
        """评估逻辑公式"""
        if bindings is None:
            bindings = {}
        
        ftype = parsed['type']
        batch_size, num_const, _ = const_embeds.shape
        
        try:
            if ftype == 'atom':
                pred_name = parsed['predicate']
                if pred_name not in pred_map:
                    return torch.full((batch_size,), 0.01, device=const_embeds.device)
                
                pred_idx = pred_map[pred_name]
                pred_emb = self.safe_lookup(
                    self.predicate_embeddings,
                    torch.tensor(pred_idx, device=const_embeds.device)
                )
                
                subj = parsed.get('subject')
                obj = parsed.get('object')
                
                if subj and obj:
                    # 二元谓词
                    s_idx = min(self._resolve_entity(subj, const_map, bindings), num_const - 1)
                    o_idx = min(self._resolve_entity(obj, const_map, bindings), num_const - 1)
                    
                    s_emb = const_embeds[:, s_idx]
                    o_emb = const_embeds[:, o_idx]
                    
                    return self.compute_relation_score(s_emb, pred_emb, o_emb, pred_name)
                else:
                    # 一元谓词
                    entity = subj or 'x'
                    e_idx = min(self._resolve_entity(entity, const_map, bindings), num_const - 1)
                    e_emb = const_embeds[:, e_idx]
                    
                    sim = F.cosine_similarity(e_emb, pred_emb.unsqueeze(0).expand(batch_size, -1))
                    return torch.sigmoid(sim * 2.0)
            
            elif ftype in ('forall', 'exists'):
                results = []
                n = min(num_const, self.max_entities)
                
                for i in range(n):
                    new_bindings = bindings.copy()
                    new_bindings[parsed['variable']] = i
                    r = self.evaluate(parsed['subformula'], const_embeds, const_map, pred_map, new_bindings)
                    results.append(r.unsqueeze(1))
                
                if results:
                    t = torch.cat(results, dim=1)
                    return self.soft_forall(t, 1) if ftype == 'forall' else self.soft_exists(t, 1)
                
                return torch.full((batch_size,), 0.5, device=const_embeds.device)
            
            elif ftype == 'and':
                l = self.evaluate(parsed['left'], const_embeds, const_map, pred_map, bindings)
                r = self.evaluate(parsed['right'], const_embeds, const_map, pred_map, bindings)
                return self.soft_and(l, r)
            
            elif ftype == 'or':
                l = self.evaluate(parsed['left'], const_embeds, const_map, pred_map, bindings)
                r = self.evaluate(parsed['right'], const_embeds, const_map, pred_map, bindings)
                return self.soft_or(l, r)
            
            elif ftype == 'implies':
                l = self.evaluate(parsed['left'], const_embeds, const_map, pred_map, bindings)
                r = self.evaluate(parsed['right'], const_embeds, const_map, pred_map, bindings)
                return self.soft_implies(l, r)
            
            elif ftype == 'not':
                s = self.evaluate(parsed['subformula'], const_embeds, const_map, pred_map, bindings)
                return self.soft_not(s)
        
        except Exception as e:
            pass
        
        return torch.full((batch_size,), 0.5, device=const_embeds.device)
    
    def get_reasoning_history(self):
        return self.reasoning_history
    
    def clear_history(self):
        self.reasoning_history = []
    
    def forward(self, entity_indices, formula, const_map, pred_map):
        """前向传播"""
        self.clear_history()
        
        const_embeds = self.safe_lookup(self.constant_embeddings, entity_indices)
        
        try:
            parsed = self.parse_formula(formula)
        except:
            return torch.full((entity_indices.size(0),), 0.5, device=entity_indices.device)
        
        return self.evaluate(parsed, const_embeds, const_map, pred_map)


# ============================================================================
# 知识图谱推理系统（增强泛化能力）
# ============================================================================

class KGReasoner(nn.Module):
    """知识图谱推理系统"""
    
    def __init__(self, vocab_size, num_predicates, num_constants,
                 embed_dim=64, hidden_dim=128, max_entities=10, max_seq_len=50):
        super().__init__()
        
        # 文本编码器
        self.text_embedding = nn.Embedding(vocab_size, embed_dim)
        self.text_lstm = nn.LSTM(embed_dim, hidden_dim // 2, batch_first=True, bidirectional=True)
        self.text_dropout = nn.Dropout(0.4)
        self.text_proj = nn.Linear(hidden_dim, hidden_dim // 2)
        
        # 逻辑推理器
        self.logic = DifferentiableFOL(num_predicates, num_constants, hidden_dim // 2, max_entities)
        
        # 融合网络 - 加入更多正则化
        self.fusion = nn.Sequential(
            nn.Linear(hidden_dim // 2 + 1, hidden_dim // 2),
            nn.BatchNorm1d(hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(hidden_dim // 2, hidden_dim // 4),
            nn.BatchNorm1d(hidden_dim // 4),
            nn.ReLU(),
            nn.Dropout(0.4),
            nn.Linear(hidden_dim // 4, 1),
            nn.Sigmoid()
        )
    
    def encode_text(self, tokens):
        emb = self.text_embedding(tokens)
        emb = self.text_dropout(emb)
        _, (h, _) = self.text_lstm(emb)
        h = torch.cat([h[0], h[1]], dim=-1)
        return self.text_proj(h)
    
    def forward(self, text_tokens, entity_indices, formulas, const_maps, pred_map):
        batch_size = text_tokens.size(0)
        
        # 文本编码
        text_emb = self.encode_text(text_tokens)
        
        # 逻辑推理
        logic_scores = []
        for i in range(batch_size):
            s = self.logic(entity_indices[i].unsqueeze(0), formulas[i], const_maps[i], pred_map)
            logic_scores.append(s.reshape(-1))
        
        logic_scores = torch.stack(logic_scores).reshape(batch_size)
        
        # 融合
        combined = torch.cat([text_emb, logic_scores.unsqueeze(1)], dim=-1)
        confidence = self.fusion(combined).squeeze(-1)
        
        return {
            'confidence': confidence,
            'logic_scores': logic_scores,
            'reasoning_history': self.logic.get_reasoning_history()
        }


# ============================================================================
# 主系统
# ============================================================================

class LogicReasoningSystem:
    """逻辑推理系统 v2.3"""
    
    def __init__(self, domain="family", max_entities=10, max_seq_len=50):
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
                'Matthew','Anthony','Mark','Tom','Jerry'}
        female = {'Mary','Jennifer','Alice','Emma','Sarah','Helen','Karen','Lisa',
                  'Carol','Grace','Linda','Barbara','Susan','Jessica','Nancy','Betty',
                  'Margaret','Dorothy'}
        
        types = {}
        for e in entities:
            if e in male: types[e] = 'Male'
            elif e in female: types[e] = 'Female'
            else: types[e] = 'Unknown'
        
        # 上下文
        tl = text.lower()
        family_w = {'father','mother','son','daughter','brother','sister',
                    'parent','child','married','wife','husband','family'}
        prof_w = {'work','office','company','manager','colleague','business','project','employee'}
        
        f_score = sum(0.2 for w in family_w if w in tl)
        p_score = sum(0.2 for w in prof_w if w in tl)
        
        if f_score > p_score: ctx = 'family'
        elif p_score > 0: ctx = 'professional'
        else: ctx = 'general'
        
        self.entity_vocab.update(entities)
        
        return {'entities': entities, 'types': types, 'context': ctx}
    
    def text_to_tokens(self, text):
        tokens = [ord(c) % self.vocab_size for c in text[:self.max_seq_len]]
        while len(tokens) < self.max_seq_len:
            tokens.append(0)
        return torch.tensor(tokens, dtype=torch.long).unsqueeze(0)
    
    def build_const_map(self, entities):
        cmap = {e: i+1 for i, e in enumerate(entities)}
        for v in ['x','y','z','p','q']:
            cmap[v] = 0
        return cmap
    
    def entity_indices(self, entities):
        idx = [i+1 for i in range(len(entities))]
        while len(idx) < self.max_entities:
            idx.append(0)
        return torch.tensor(idx, dtype=torch.long).unsqueeze(0)
    
    def create_sample(self, text, target_rel, facts=None):
        info = self.extract_entities(text)
        entities = info['entities']
        
        formulas = {
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
        
        formula = formulas.get(target_rel, f'{target_rel}(x,y)')
        
        return {
            'text': text,
            'text_tokens': self.text_to_tokens(text),
            'entities': entities,
            'entity_info': info,
            'constant_map': self.build_const_map(entities),
            'entity_indices': self.entity_indices(entities),
            'logical_formula': formula,
            'target_relation': target_rel,
            'known_facts': facts or []
        }
    
    def init_model(self):
        n_const = max(len(self.entity_vocab) + 20, self.max_entities + 10)
        n_pred = len(self.predicate_map)
        
        self.model = KGReasoner(
            vocab_size=self.vocab_size,
            num_predicates=n_pred,
            num_constants=n_const,
            embed_dim=64,
            hidden_dim=128,
            max_entities=self.max_entities,
            max_seq_len=self.max_seq_len
        )
        return self.model
    
    def train(self, data, epochs=200, lr=0.0005, batch_size=4):
        if self.model is None:
            self.init_model()
        
        # 使用较强的权重衰减和较保守的学习率
        optimizer = optim.AdamW(self.model.parameters(), lr=lr, weight_decay=0.05)
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
        criterion = nn.BCELoss()
        
        self.model.train()
        best_loss = float('inf')
        patience = 30
        p_counter = 0
        best_state = None
        
        print(f"\n训练配置: lr={lr}, weight_decay=0.05, epochs={epochs}")
        
        for epoch in range(epochs):
            total_loss = 0
            correct = 0
            total = 0
            
            random.shuffle(data)
            
            for i in range(0, len(data), batch_size):
                batch = data[i:i+batch_size]
                if len(batch) < 2:
                    continue
                
                try:
                    tokens = torch.cat([s['text_tokens'] for s in batch])
                    entities = torch.cat([s['entity_indices'] for s in batch])
                    formulas = [s['logical_formula'] for s in batch]
                    cmaps = [s['constant_map'] for s in batch]
                    
                    targets = torch.tensor([1.0 if s.get('is_true') else 0.0 for s in batch],
                                          dtype=torch.float32)
                    
                    outputs = self.model(tokens, entities, formulas, cmaps, self.predicate_map)
                    conf = outputs['confidence']
                    
                    # 添加标签平滑
                    smooth_targets = targets * 0.9 + 0.05
                    loss = criterion(conf, smooth_targets)
                    
                    optimizer.zero_grad()
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), 0.5)
                    optimizer.step()
                    
                    total_loss += loss.item()
                    preds = (conf > 0.5).float()
                    correct += (preds == targets).sum().item()
                    total += len(targets)
                    
                except Exception as e:
                    continue
            
            scheduler.step()
            
            if total > 0:
                acc = correct / total
                avg_loss = total_loss / max(1, len(data) // batch_size)
                
                self.training_history.append({
                    'epoch': epoch, 'loss': avg_loss, 'accuracy': acc
                })
                
                if avg_loss < best_loss:
                    best_loss = avg_loss
                    p_counter = 0
                    best_state = {k: v.cpu().clone() for k, v in self.model.state_dict().items()}
                else:
                    p_counter += 1
                
                if epoch % 30 == 0:
                    print(f'Epoch {epoch:3d} | Loss: {avg_loss:.4f} | Acc: {acc:.4f}')
                
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
                sample['entity_indices'],
                [sample['logical_formula']],
                [sample['constant_map']],
                self.predicate_map
            )
        
        conf = outputs['confidence'].item()
        logic = outputs['logic_scores'].item()
        
        return {
            'confidence': conf,
            'logic_score': logic,
            'prediction': conf > 0.5,
            'entities': sample['entities'],
            'entity_info': sample['entity_info'],
            'formula': sample['logical_formula'],
            'known_facts': facts or [],
            'target_relation': target_rel,
            'reasoning_steps': outputs.get('reasoning_history', [])
        }
    
    def plot_history(self):
        if not self.training_history:
            print("无训练历史")
            return
        
        epochs = [x['epoch'] for x in self.training_history]
        losses = [x['loss'] for x in self.training_history]
        accs = [x['accuracy'] for x in self.training_history]
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
        
        ax1.plot(epochs, losses, 'b-')
        ax1.set_xlabel('Epoch'); ax1.set_ylabel('Loss')
        ax1.set_title('Training Loss'); ax1.grid(True, alpha=0.3)
        
        ax2.plot(epochs, accs, 'r-')
        ax2.set_xlabel('Epoch'); ax2.set_ylabel('Accuracy')
        ax2.set_title('Training Accuracy'); ax2.grid(True, alpha=0.3)
        ax2.set_ylim([0, 1.05])
        
        plt.tight_layout()
        plt.show()
    
    def explain(self, result):
        print("\n" + "="*60)
        print("推理过程解释")
        print("="*60)
        print(f"\n目标关系: {result['target_relation']}")
        print(f"置信度: {result['confidence']:.4f}")
        print(f"逻辑得分: {result['logic_score']:.4f}")
        print(f"预测: {'✓ 成立' if result['prediction'] else '✗ 不成立'}")
        print(f"公式: {result['formula']}")
        
        if result['known_facts']:
            print(f"\n已知事实 ({len(result['known_facts'])}个):")
            for f in result['known_facts']:
                print(f"  {f[0]}({f[1]}, {f[2]})")
        
        if result['entities']:
            print(f"\n实体: {', '.join(result['entities'])}")
            print(f"上下文: {result['entity_info'].get('context', 'unknown')}")


# ============================================================================
# 数据生成（增加多样性和数据增强）
# ============================================================================

def create_data():
    """创建更丰富的训练数据"""
    system = LogicReasoningSystem("family", max_entities=10, max_seq_len=60)
    
    samples = []
    
    # ========== 正例 ==========
    positives = [
        # Grandparent (多代推理)
        ("John is Mary's father. Mary has a son named Tom.", 'Grandparent',
         [('Father','John','Mary'), ('Parent','Mary','Tom')]),
        ("David is Emma's father. Emma has a daughter Lisa.", 'Grandparent',
         [('Father','David','Emma'), ('Parent','Emma','Lisa')]),
        ("Anna is Bob's mother. Bob has a son Charlie.", 'Grandparent',
         [('Mother','Anna','Bob'), ('Parent','Bob','Charlie')]),
        
        # Spouse (对称关系)
        ("Alice and Bob are married.", 'Spouse',
         [('Spouse','Alice','Bob')]),
        ("Sarah is Thomas's wife.", 'Spouse',
         [('Spouse','Sarah','Thomas')]),
        
        # Sibling (共享父母)
        ("George and Helen are brother and sister.", 'Sibling',
         [('Sibling','George','Helen')]),
        ("Lisa and Karen are sisters.", 'Sibling',
         [('Sibling','Lisa','Karen')]),
        ("Mike and Steve are brothers.", 'Sibling',
         [('Sibling','Mike','Steve')]),
        
        # Parent (直接关系)
        ("Michael is Jennifer's father.", 'Parent',
         [('Father','Michael','Jennifer')]),
        ("Mary is the mother of Tom.", 'Parent',
         [('Mother','Mary','Tom')]),
        ("Robert is Susan's father.", 'Parent',
         [('Father','Robert','Susan')]),
        
        # Child (反向关系)
        ("Tom is Mary's son.", 'Child',
         [('Child','Tom','Mary')]),
        ("Lisa is Anna's daughter.", 'Child',
         [('Child','Lisa','Anna')]),
        
        # Brother/Sister
        ("James is Emma's brother.", 'Brother',
         [('Brother','James','Emma')]),
        ("Grace is Kevin's sister.", 'Sister',
         [('Sister','Grace','Kevin')]),
        
        # Ancestor (传递闭包)
        ("John is Mary's father. Mary has a son Tom.", 'Ancestor',
         [('Father','John','Mary'), ('Parent','Mary','Tom')]),
        ("Grandma Alice has a daughter Barbara. Barbara has a son Charlie.", 'Ancestor',
         [('Mother','Alice','Barbara'), ('Parent','Barbara','Charlie')]),
    ]
    
    # ========== 负例（精心设计的反例） ==========
    negatives = [
        # 兄弟不是父母
        ("George is Helen's brother. Helen has a son Ian.", 'Parent',
         [('Sibling','George','Helen'), ('Parent','Helen','Ian')]),
        ("Mike is Steve's brother. Steve has a daughter.", 'Parent',
         [('Sibling','Mike','Steve')]),
        
        # 同事不是兄弟姐妹
        ("Karen and Lisa are colleagues at work.", 'Sibling',
         [('Colleague','Karen','Lisa')]),
        ("David and Emma work together.", 'Sibling',
         [('Colleague','David','Emma')]),
        
        # 同事不是配偶
        ("Michael works with Jennifer.", 'Spouse',
         [('Colleague','Michael','Jennifer')]),
        
        # 经理不是父母
        ("Robert is Susan's manager.", 'Parent',
         [('Manager','Robert','Susan')]),
        ("Linda manages a team of ten people.", 'Parent', []),
        
        # 朋友不是兄弟姐妹
        ("Sarah and Thomas are friends from college.", 'Sibling',
         [('Friend','Sarah','Thomas')]),
        ("Bob and Frank are old friends.", 'Sibling',
         [('Friend','Bob','Frank')]),
        
        # 朋友不是配偶
        ("Sarah and Thomas are good friends.", 'Spouse',
         [('Friend','Sarah','Thomas')]),
        
        # 反向关系错误
        ("John is Mary's father.", 'Child',
         [('Father','John','Mary')]),
        ("Mary is Tom's mother.", 'Child',
         [('Mother','Mary','Tom')]),
        
        # 跨度不够
        ("Alice is Bob's mother. Bob is Charlie's father.", 'Sibling',
         [('Mother','Alice','Bob'), ('Father','Bob','Charlie')]),
        
        # 单代不是祖辈
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
    print("可微分一阶逻辑推理系统 v2.3")
    print("="*60)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"设备: {device}")
    
    torch.manual_seed(42)
    np.random.seed(42)
    random.seed(42)
    
    system = LogicReasoningSystem("family", max_entities=10, max_seq_len=60)
    
    data = create_data()
    print(f"\n训练样本: {len(data)}")
    print(f"正例: {sum(1 for s in data if s['is_true'])}")
    print(f"负例: {sum(1 for s in data if not s['is_true'])}")
    
    model = system.init_model()
    print(f"参数: {sum(p.numel() for p in model.parameters()):,}")
    
    system.train(data, epochs=200, lr=0.0005, batch_size=4)
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
        ("John is Mary's father.", 'Child',
         [('Father','John','Mary')], False),
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
        print(f"{status} 测试{i+1}: {rel} | 期望:{expected} | 预测:{result['prediction']} | "
              f"置信度:{result['confidence']:.4f} | 逻辑:{result['logic_score']:.4f}")
    
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
    
    return system, data


if __name__ == "__main__":
    system, data = demo()