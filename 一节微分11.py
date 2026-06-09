"""
可微分一阶逻辑推理系统 v2.4
核心修复：让逻辑推理真正工作
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import numpy as np
import re
import math
from typing import List, Dict, Tuple, Any, Optional
from collections import OrderedDict
import random
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')


# ============================================================================
# 核心：基于规则的知识图谱推理（确定性逻辑，非神经网络）
# ============================================================================

class SymbolicRuleEngine:
    """
    符号规则引擎 - 基于确定性规则进行推理
    这是系统的核心，确保逻辑推理真正有效
    """
    
    def __init__(self):
        # 定义推理规则
        self.rules = {
            # 直接关系推导
            ('Father', 'Child'): lambda s, o, kg: ('Child', o, s),
            ('Mother', 'Child'): lambda s, o, kg: ('Child', o, s),
            ('Child', 'Parent'): lambda s, o, kg: ('Parent', o, s),
            ('Parent', 'Child'): lambda s, o, kg: ('Child', o, s),
            
            # Father/Mother -> Parent
            ('Father', 'Parent'): lambda s, o, kg: ('Parent', s, o),
            ('Mother', 'Parent'): lambda s, o, kg: ('Parent', s, o),
            
            # Spouse对称
            ('Spouse', 'Spouse'): lambda s, o, kg: ('Spouse', o, s),
            # Sibling对称
            ('Sibling', 'Sibling'): lambda s, o, kg: ('Sibling', o, s),
        }
        
        # 多跳推理规则
        self.multi_hop_rules = {
            'Grandparent': self._check_grandparent,
            'Grandchild': self._check_grandchild,
            'Ancestor': self._check_ancestor,
            'Sibling': self._check_sibling,
        }
    
    def _check_grandparent(self, subject, object_, kg):
        """检查 Grandparent(s, o)：存在z使得 Parent(s,z) ∧ Parent(z,o)"""
        for (pred, s, o) in kg:
            if s == subject and pred in ('Father', 'Mother', 'Parent'):
                intermediate = o
                for (pred2, s2, o2) in kg:
                    if s2 == intermediate and o2 == object_ and pred2 in ('Father', 'Mother', 'Parent'):
                        return True
        return False
    
    def _check_grandchild(self, subject, object_, kg):
        """检查 Grandchild(s, o)：存在z使得 Parent(z,s) ∧ Parent(o,z)"""
        return self._check_grandparent(object_, subject, kg)
    
    def _check_ancestor(self, subject, object_, kg, visited=None, depth=0):
        """递归检查 Ancestor(s, o)"""
        if depth > 5:  # 限制深度
            return False
        if visited is None:
            visited = set()
        if subject in visited:
            return False
        visited.add(subject)
        
        # 直接Parent关系
        for (pred, s, o) in kg:
            if s == subject and o == object_ and pred in ('Father', 'Mother', 'Parent'):
                return True
        
        # 传递：Parent(s, z) ∧ Ancestor(z, o)
        for (pred, s, o) in kg:
            if s == subject and pred in ('Father', 'Mother', 'Parent'):
                if self._check_ancestor(o, object_, kg, visited.copy(), depth + 1):
                    return True
        
        return False
    
    def _check_sibling(self, subject, object_, kg):
        """检查 Sibling(s, o)：存在p使得 Parent(p,s) ∧ Parent(p,o)"""
        subject_parents = set()
        object_parents = set()
        
        for (pred, s, o) in kg:
            if o == subject and pred in ('Father', 'Mother', 'Parent'):
                subject_parents.add(s)
            if o == object_ and pred in ('Father', 'Mother', 'Parent'):
                object_parents.add(s)
        
        return len(subject_parents & object_parents) > 0 and subject != object_
    
    def infer(self, target_relation, facts, entities):
        """
        基于已知事实推理目标关系
        
        Args:
            target_relation: 目标关系名
            facts: 已知事实列表 [(predicate, subject, object), ...]
            entities: 实体列表
        
        Returns:
            (exists, confidence) - 是否存在满足关系的实体对，以及置信度
        """
        kg = set(facts)
        
        # 扩展知识图谱（应用单跳规则）
        extended_kg = set(kg)
        for (pred, s, o) in kg:
            for (rule_pred, target_pred), rule_fn in self.rules.items():
                if pred == rule_pred:
                    new_fact = rule_fn(s, o, kg)
                    if new_fact:
                        extended_kg.add(new_fact)
        
        # 检查目标关系
        found = False
        matched_pairs = []
        
        if target_relation in self.multi_hop_rules:
            checker = self.multi_hop_rules[target_relation]
            for s in entities:
                for o in entities:
                    if s != o and checker(s, o, extended_kg):
                        found = True
                        matched_pairs.append((s, o))
        else:
            # 直接查找
            for (pred, s, o) in extended_kg:
                if pred == target_relation:
                    found = True
                    matched_pairs.append((s, o))
        
        # 计算置信度
        if found:
            confidence = min(0.95, 0.5 + 0.1 * len(matched_pairs))
        else:
            # 检查是否有部分证据
            partial_evidence = self._check_partial(target_relation, extended_kg, entities)
            if partial_evidence:
                confidence = 0.3
            else:
                # 检查是否是不同类型的关系（职业vs家庭）
                type_mismatch = self._check_type_mismatch(target_relation, facts)
                if type_mismatch:
                    confidence = 0.05
                else:
                    confidence = 0.15
        
        return found, confidence, extended_kg
    
    def _check_partial(self, target_relation, kg, entities):
        """检查部分证据"""
        if target_relation == 'Grandparent':
            for (pred, s, o) in kg:
                if pred in ('Father', 'Mother', 'Parent'):
                    return True
        elif target_relation == 'Sibling':
            for (pred, s, o) in kg:
                if pred in ('Father', 'Mother', 'Parent'):
                    return True
        elif target_relation == 'Ancestor':
            for (pred, s, o) in kg:
                if pred in ('Father', 'Mother', 'Parent'):
                    return True
        return False
    
    def _check_type_mismatch(self, target_relation, facts):
        """检查关系类型不匹配"""
        family_relations = {'Father', 'Mother', 'Parent', 'Child', 'Spouse', 
                           'Sibling', 'Grandparent', 'Ancestor', 'Brother', 'Sister'}
        professional_relations = {'Colleague', 'Manager'}
        social_relations = {'Friend'}
        
        target_type = None
        if target_relation in family_relations:
            target_type = 'family'
        elif target_relation in professional_relations:
            target_type = 'professional'
        elif target_relation in social_relations:
            target_type = 'social'
        
        if target_type is None:
            return False
        
        fact_types = set()
        for (pred, s, o) in facts:
            if pred in family_relations:
                fact_types.add('family')
            elif pred in professional_relations:
                fact_types.add('professional')
            elif pred in social_relations:
                fact_types.add('social')
        
        # 如果已知事实类型与目标关系类型完全不同
        if fact_types and target_type not in fact_types:
            return True
        
        return False


# ============================================================================
# 混合推理系统（符号+神经网络）
# ============================================================================

class HybridReasoner(nn.Module):
    """
    混合推理器：结合符号规则引擎和神经网络
    """
    
    def __init__(self, vocab_size, num_predicates, num_constants,
                 embed_dim=64, hidden_dim=128, max_entities=10, max_seq_len=50):
        super().__init__()
        
        self.max_entities = max_entities
        self.max_seq_len = max_seq_len
        
        # 文本编码器（轻量级）
        self.text_embedding = nn.Embedding(vocab_size, embed_dim)
        self.text_lstm = nn.LSTM(embed_dim, hidden_dim // 2, batch_first=True, bidirectional=True)
        self.text_proj = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.3)
        )
        
        # 符号规则引擎
        self.rule_engine = SymbolicRuleEngine()
        
        # 文本特征 -> 关系类型预测（辅助任务）
        self.relation_type_classifier = nn.Sequential(
            nn.Linear(hidden_dim // 2, 32),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(32, 3),  # family, professional, social
        )
        
        # 最终融合网络
        # 输入：文本特征(hidden//2) + 符号推理得分(1) + 关系类型(3) = hidden//2 + 4
        self.fusion = nn.Sequential(
            nn.Linear(hidden_dim // 2 + 4, hidden_dim // 2),
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
        
        # 谓词嵌入（用于文本中的关系词检测）
        self.predicate_embeddings = nn.Embedding(num_predicates, embed_dim)
    
    def encode_text(self, tokens):
        emb = self.text_embedding(tokens)
        _, (h, _) = self.text_lstm(emb)
        h = torch.cat([h[0], h[1]], dim=-1)
        return self.text_proj(h)
    
    def symbolic_inference(self, target_relation, facts_list, entities_list):
        """
        对批次中的每个样本进行符号推理
        """
        batch_size = len(target_relation)
        scores = torch.zeros(batch_size)
        
        for i in range(batch_size):
            rel = target_relation[i] if isinstance(target_relation, list) else target_relation
            if isinstance(target_relation, list):
                rel = target_relation[i]
            
            facts = facts_list[i] if i < len(facts_list) else []
            entities = entities_list[i] if i < len(entities_list) else []
            
            found, confidence, _ = self.rule_engine.infer(rel, facts, entities)
            scores[i] = confidence
        
        return scores
    
    def forward(self, text_tokens, target_relations, facts_list, entities_list):
        """
        前向传播
        
        Args:
            text_tokens: 文本token [batch, seq_len]
            target_relations: 目标关系列表
            facts_list: 已知事实列表的列表
            entities_list: 实体列表的列表
        """
        batch_size = text_tokens.size(0)
        
        # 1. 文本编码
        text_feat = self.encode_text(text_tokens)  # [batch, hidden//2]
        
        # 2. 符号推理
        symbolic_scores = self.symbolic_inference(
            target_relations, facts_list, entities_list
        ).to(text_tokens.device)  # [batch]
        
        # 3. 关系类型预测
        relation_type_logits = self.relation_type_classifier(text_feat)  # [batch, 3]
        relation_type_probs = F.softmax(relation_type_logits, dim=-1)
        
        # 4. 融合
        combined = torch.cat([
            text_feat,
            symbolic_scores.unsqueeze(1),
            relation_type_probs
        ], dim=-1)
        
        confidence = self.fusion(combined).squeeze(-1)
        
        return {
            'confidence': confidence,
            'symbolic_score': symbolic_scores,
            'relation_type': relation_type_probs
        }


# ============================================================================
# 主系统
# ============================================================================

class LogicReasoningSystem:
    """混合逻辑推理系统 v2.4"""
    
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
        
        print(f"\n训练: lr={lr}, epochs={epochs}, batch={batch_size}")
        
        for epoch in range(epochs):
            total_loss = 0
            correct_sym = 0
            correct_hybrid = 0
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
                    
                    targets = torch.tensor([1.0 if s.get('is_true') else 0.0 for s in batch],
                                          dtype=torch.float32)
                    
                    outputs = self.model(tokens, relations, facts, entities)
                    conf = outputs['confidence']
                    sym_score = outputs['symbolic_score']
                    
                    # 损失 = 融合损失 + 符号推理辅助损失
                    fusion_loss = criterion(conf, targets)
                    sym_loss = criterion(
                        torch.clamp(sym_score, 0.001, 0.999), 
                        targets
                    )
                    loss = fusion_loss + 0.3 * sym_loss
                    
                    optimizer.zero_grad()
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                    optimizer.step()
                    
                    total_loss += loss.item()
                    
                    preds = (conf > 0.5).float()
                    sym_preds = (sym_score > 0.5).float()
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
                    'epoch': epoch,
                    'loss': avg_loss,
                    'accuracy': acc_h,
                    'symbolic_accuracy': acc_s
                })
                
                if avg_loss < best_loss:
                    best_loss = avg_loss
                    p_counter = 0
                    best_state = {k: v.cpu().clone() for k, v in self.model.state_dict().items()}
                else:
                    p_counter += 1
                
                if epoch % 20 == 0:
                    print(f'Epoch {epoch:3d} | Loss: {avg_loss:.4f} | '
                          f'Hybrid Acc: {acc_h:.4f} | Sym Acc: {acc_s:.4f}')
                
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
        sym_score = outputs['symbolic_score'].item()
        
        # 获取符号推理详情
        rule_engine = self.model.rule_engine
        found, sym_conf, extended_kg = rule_engine.infer(
            target_rel, facts or [], sample['entities']
        )
        
        return {
            'confidence': conf,
            'symbolic_score': sym_score,
            'symbolic_found': found,
            'symbolic_confidence': sym_conf,
            'prediction': conf > 0.5,
            'entities': sample['entities'],
            'formula': self._get_formula(target_rel),
            'known_facts': facts or [],
            'target_relation': target_rel,
            'extended_facts': list(extended_kg - set(facts or []))
        }
    
    def _get_formula(self, target_rel):
        formulas = {
            'Parent': 'Father(x,y) ∨ Mother(x,y)',
            'Grandparent': '∃z: Parent(x,z) ∧ Parent(z,y)',
            'Sibling': '∃p: Parent(p,x) ∧ Parent(p,y)',
            'Spouse': 'Spouse(x,y)',
            'Ancestor': 'Parent+(x,y) (传递闭包)',
            'Child': 'Parent(y,x)',
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
        ax2.legend()
        ax2.set_ylim([0, 1.05])
        
        plt.tight_layout()
        plt.show()
    
    def explain(self, result):
        print("\n" + "="*60)
        print("推理过程解释")
        print("="*60)
        print(f"\n目标关系: {result['target_relation']}")
        print(f"逻辑公式: {result['formula']}")
        print(f"\n混合置信度: {result['confidence']:.4f}")
        print(f"符号推理得分: {result['symbolic_score']:.4f}")
        print(f"符号推理发现关系: {'是' if result['symbolic_found'] else '否'}")
        print(f"符号推理置信度: {result['symbolic_confidence']:.4f}")
        print(f"最终预测: {'✓ 成立' if result['prediction'] else '✗ 不成立'}")
        
        if result['known_facts']:
            print(f"\n已知事实 ({len(result['known_facts'])}个):")
            for f in result['known_facts']:
                print(f"  • {f[0]}({f[1]}, {f[2]})")
        
        if result.get('extended_facts'):
            print(f"\n推理出新事实 ({len(result['extended_facts'])}个):")
            for f in result['extended_facts']:
                print(f"  • {f[0]}({f[1]}, {f[2]})")
        
        if result['entities']:
            print(f"\n实体: {', '.join(result['entities'])}")


# ============================================================================
# 数据生成
# ============================================================================

def create_data():
    system = LogicReasoningSystem("family", max_entities=10, max_seq_len=60)
    
    samples = []
    
    # ===== 正例 =====
    positives = [
        # Grandparent
        ("John is Mary's father. Mary has a son named Tom.", 'Grandparent',
         [('Father','John','Mary'), ('Parent','Mary','Tom')]),
        ("David is Emma's father. Emma has a daughter Lisa.", 'Grandparent',
         [('Father','David','Emma'), ('Parent','Emma','Lisa')]),
        ("Anna is Bob's mother. Bob has a son Charlie.", 'Grandparent',
         [('Mother','Anna','Bob'), ('Parent','Bob','Charlie')]),
        
        # Spouse
        ("Alice and Bob are married.", 'Spouse',
         [('Spouse','Alice','Bob')]),
        ("Sarah is Thomas's wife.", 'Spouse',
         [('Spouse','Sarah','Thomas')]),
        
        # Sibling
        ("George and Helen are brother and sister.", 'Sibling',
         [('Sibling','George','Helen'), ('Parent','John','George'), ('Parent','John','Helen')]),
        ("Lisa and Karen are sisters.", 'Sibling',
         [('Sibling','Lisa','Karen'), ('Parent','Mary','Lisa'), ('Parent','Mary','Karen')]),
        
        # Parent
        ("Michael is Jennifer's father.", 'Parent',
         [('Father','Michael','Jennifer')]),
        ("Mary is the mother of Tom.", 'Parent',
         [('Mother','Mary','Tom')]),
        ("Robert is Susan's father.", 'Parent',
         [('Father','Robert','Susan')]),
        
        # Child
        ("Tom is Mary's son.", 'Child',
         [('Child','Tom','Mary')]),
        
        # Ancestor
        ("John is Mary's father. Mary has a son Tom.", 'Ancestor',
         [('Father','John','Mary'), ('Parent','Mary','Tom')]),
        ("Grandma Alice has a daughter Barbara. Barbara has a son Charlie.", 'Ancestor',
         [('Mother','Alice','Barbara'), ('Parent','Barbara','Charlie')]),
        
        # Brother/Sister
        ("James is Emma's brother.", 'Brother',
         [('Brother','James','Emma')]),
        ("Grace is Kevin's sister.", 'Sister',
         [('Sister','Grace','Kevin')]),
    ]
    
    # ===== 负例 =====
    negatives = [
        # 兄弟不是父母
        ("George is Helen's brother. Helen has a son Ian.", 'Parent',
         [('Sibling','George','Helen'), ('Parent','Helen','Ian')]),
        
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
    print("混合逻辑推理系统 v2.4 (符号+神经网络)")
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
    
    # 先测试纯符号推理
    print("\n--- 纯符号推理测试 ---")
    rule_engine = SymbolicRuleEngine()
    test_facts = [('Father','John','Mary'), ('Parent','Mary','Tom'), ('Parent','Tom','Alice')]
    test_entities = ['John','Mary','Tom','Alice']
    
    for rel in ['Grandparent', 'Ancestor', 'Parent', 'Sibling', 'Spouse']:
        found, conf, _ = rule_engine.infer(rel, test_facts, test_entities)
        print(f"  {rel}: found={found}, conf={conf:.4f}")
    
    print("\n--- 训练混合模型 ---")
    system.train(data, epochs=100, lr=0.001, batch_size=4)
    system.plot_history()
    
    # 测试
    tests = [
        ("Michael is Jennifer's father. Jennifer has a son named Kevin.", 'Grandparent',
         [('Father','Michael','Jennifer'), ('Parent','Jennifer','Kevin')], True),
        ("Sarah and Thomas are married.", 'Spouse',
         [('Spouse','Sarah','Thomas')], True),
        ("David and Emma are brother and sister.", 'Sibling',
         [('Sibling','David','Emma'), ('Parent','John','David'), ('Parent','John','Emma')], True),
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
        print(f"{status} 测试{i+1}: {rel:12s} | 期望:{str(expected):5s} | "
              f"混合:{result['confidence']:.4f} | 符号:{result['symbolic_score']:.4f} | "
              f"符号发现:{result['symbolic_found']}")
    
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