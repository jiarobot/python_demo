import numpy as np
import math
from scipy import linalg, stats
import random
from collections import defaultdict, deque
import itertools
from dataclasses import dataclass
from typing import List, Dict, Set, Any, Optional
import json

@dataclass
class UnknownLaw:
    """未知性定律的基本结构"""
    premise_pattern: List[str]  # 前提模式
    conclusion_pattern: List[str]  # 结论模式  
    confidence: float  # 置信度
    entropy: float  # 信息熵
    novelty: float  # 新颖性评分
    applicability: float  # 适用性范围

class UnknownLawReasoner:
    """
    基于未知性定律的推理系统
    核心思想：在信息不完全的情况下发现潜在规律
    """
    
    def __init__(self, cognitive_dim=256):
        self.cognitive_dim = cognitive_dim
        self.known_facts = set()
        self.unknown_laws = []
        self.cognitive_map = np.eye(cognitive_dim)  # 认知状态矩阵
        self.uncertainty_field = np.zeros(cognitive_dim)  # 不确定性场
        self.hypothesis_space = defaultdict(list)
        self.counterfactual_memory = deque(maxlen=1000)
        
        # 未知性定律参数
        self.unknown_threshold = 0.3
        self.creativity_factor = 0.7
        self.paradox_tolerance = 0.4
        
        # 添加缓存机制避免递归
        self.concept_cache = {}
        self.novelty_cache = {}
        self.uncertainty_cache = {}
        
    def perceive_fact(self, fact: str, context: List[str], confidence: float = 1.0):
        """
        感知事实，但考虑不确定性
        """
        encoded_fact = self._encode_concept(fact)
        encoded_context = [self._encode_concept(c) for c in context]
        
        # 更新认知地图
        self._update_cognitive_map(encoded_fact, encoded_context, confidence)
        
        # 记录事实但标记不确定性
        if confidence > self.unknown_threshold:
            self.known_facts.add(fact)
        else:
            self._handle_uncertain_fact(fact, context, confidence)
    
    def _encode_concept(self, concept: str) -> np.ndarray:
        """将概念编码为认知向量"""
        # 使用缓存避免重复计算
        if concept in self.concept_cache:
            return self.concept_cache[concept]
            
        # 使用概念的语义哈希作为确定性部分
        deterministic = self._semantic_hash(concept)
        
        # 预先计算不确定性水平，避免递归
        if concept in self.uncertainty_cache:
            uncertainty_level = self.uncertainty_cache[concept]
        else:
            uncertainty_level = self._get_uncertainty_level_simple(concept)
            self.uncertainty_cache[concept] = uncertainty_level
        
        # 添加不确定性噪声
        uncertainty = np.random.normal(0, 0.1, self.cognitive_dim)
        
        # 组合确定性和不确定性
        encoded = deterministic + uncertainty * uncertainty_level
        encoded = encoded / np.linalg.norm(encoded)
        
        # 缓存结果
        self.concept_cache[concept] = encoded
        return encoded
    
    def _semantic_hash(self, concept: str) -> np.ndarray:
        """生成概念的确定性语义哈希"""
        hash_obj = hash(concept)
        np.random.seed(hash_obj % (2**32))
        return np.random.randn(self.cognitive_dim)
    
    def _get_uncertainty_level_simple(self, concept: str) -> float:
        """简化版本的不确定性水平计算，避免递归"""
        # 基于概念的新颖性和复杂度计算不确定性
        words = concept.split()
        complexity = len(words) / 5.0  # 归一化复杂度
        
        # 简化新颖性计算，避免递归调用
        if concept in self.known_facts:
            novelty = 0.0
        else:
            # 使用简单的基于字符串的新颖性估计
            novelty = self._calculate_novelty_simple(concept)
        
        return min(1.0, complexity * 0.3 + novelty * 0.7)
    
    def _calculate_novelty_simple(self, concept: str) -> float:
        """简化版本的新颖性计算，避免递归"""
        if concept in self.novelty_cache:
            return self.novelty_cache[concept]
            
        if concept in self.known_facts:
            self.novelty_cache[concept] = 0.0
            return 0.0
        
        # 基于与已知事实的字符串相似度计算新颖性
        max_similarity = 0.0
        
        for known_fact in list(self.known_facts)[:50]:  # 采样检查
            similarity = self._string_similarity(concept, known_fact)
            max_similarity = max(max_similarity, similarity)
        
        novelty = 1.0 - max_similarity
        self.novelty_cache[concept] = novelty
        return novelty
    
    def _string_similarity(self, str1: str, str2: str) -> float:
        """计算两个字符串的相似度"""
        words1 = set(str1.lower().split())
        words2 = set(str2.lower().split())
        
        if not words1 or not words2:
            return 0.0
            
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    def _update_cognitive_map(self, fact_vec, context_vecs, confidence):
        """更新认知地图"""
        # 认知地图的量子演化
        for context_vec in context_vecs:
            # 构建相互作用哈密顿量
            interaction = np.outer(fact_vec, context_vec)
            interaction = (interaction + interaction.T) / 2  # 确保厄米性
            
            # 更新认知地图
            self.cognitive_map += confidence * 0.1 * interaction
        
        # 归一化认知地图
        norm = np.linalg.norm(self.cognitive_map)
        if norm > 0:
            self.cognitive_map /= norm
    
    def _handle_uncertain_fact(self, fact, context, confidence):
        """处理不确定事实，生成假设"""
        hypotheses = self._generate_hypotheses(fact, context, confidence)
        
        for hypothesis in hypotheses:
            self.hypothesis_space[fact].append({
                'hypothesis': hypothesis,
                'confidence': confidence,
                'context': context,
                'evidence_count': 1
            })
    
    def _generate_hypotheses(self, fact, context, confidence):
        """生成假设"""
        # 简化的假设生成：基于上下文的变体
        hypotheses = []
        if len(context) > 0:
            # 生成一些相关的假设
            for ctx in context[:2]:  # 只取前两个上下文
                hypothesis = f"{fact}（可能与{ctx}相关）"
                hypotheses.append(hypothesis)
        
        return hypotheses if hypotheses else [f"关于{fact}的待验证假设"]
    
    def discover_unknown_laws(self, min_support=2, min_confidence=0.6):
        """
        发现未知性定律
        基于不完全信息和反事实推理
        """
        candidate_laws = []
        
        # 从已知事实和假设中生成候选定律
        all_concepts = list(self.known_facts) + \
                      [h['hypothesis'] for hypotheses in self.hypothesis_space.values() 
                       for h in hypotheses]
        
        # 限制概念数量以避免组合爆炸
        if len(all_concepts) > 20:
            all_concepts = random.sample(all_concepts, 20)
        
        # 生成概念对和三元组
        for i, concept1 in enumerate(all_concepts):
            for j, concept2 in enumerate(all_concepts):
                if i >= j:
                    continue
                
                # 检查二元关系
                law_candidate = self._evaluate_law_candidate([concept1], [concept2])
                if law_candidate and law_candidate.confidence >= min_confidence:
                    candidate_laws.append(law_candidate)
                
                # 限制三元关系数量
                if len(all_concepts) <= 10:
                    for k, concept3 in enumerate(all_concepts):
                        if k <= j:
                            continue
                        
                        law_candidate = self._evaluate_law_candidate(
                            [concept1, concept2], [concept3]
                        )
                        if law_candidate and law_candidate.confidence >= min_confidence:
                            candidate_laws.append(law_candidate)
        
        # 过滤和排序候选定律
        filtered_laws = self._filter_laws(candidate_laws, min_support)
        self.unknown_laws.extend(filtered_laws)
        
        return sorted(filtered_laws, key=lambda x: x.confidence * x.novelty, reverse=True)
    
    def _evaluate_law_candidate(self, premise, conclusion):
        """评估定律候选"""
        # 计算支持度
        support = self._calculate_support(premise, conclusion)
        if support < 0.1:
            return None
        
        # 计算置信度
        confidence = self._calculate_confidence(premise, conclusion)
        
        # 计算信息熵
        entropy = self._calculate_entropy(premise + conclusion)
        
        # 计算新颖性
        novelty = self._calculate_law_novelty(premise, conclusion)
        
        # 计算适用性
        applicability = self._calculate_applicability(premise, conclusion)
        
        return UnknownLaw(
            premise_pattern=premise,
            conclusion_pattern=conclusion,
            confidence=confidence,
            entropy=entropy,
            novelty=novelty,
            applicability=applicability
        )
    
    def _calculate_support(self, premise, conclusion):
        """计算定律的支持度"""
        premise_vecs = [self._encode_concept(p) for p in premise]
        conclusion_vecs = [self._encode_concept(c) for c in conclusion]
        
        # 计算前提和结论在认知空间中的相关性
        premise_matrix = np.column_stack(premise_vecs)
        conclusion_matrix = np.column_stack(conclusion_vecs)
        
        # 使用奇异值分解计算相关性
        correlation = np.linalg.svd(premise_matrix.T @ conclusion_matrix)[1]
        return np.mean(correlation) if len(correlation) > 0 else 0.0
    
    def _calculate_confidence(self, premise, conclusion):
        """计算定律的置信度"""
        # 基于反事实推理的置信度计算
        factual_prob = self._factual_probability(premise, conclusion)
        counterfactual_prob = self._counterfactual_probability(premise, conclusion)
        
        # 置信度 = 事实概率 - 反事实概率
        confidence = factual_prob - counterfactual_prob
        return max(0.0, confidence)
    
    def _factual_probability(self, premise, conclusion):
        """计算事实概率"""
        # 在认知地图中计算条件概率
        premise_state = self._get_combined_state(premise)
        conclusion_state = self._get_combined_state(conclusion)
        
        # 使用投影测量计算概率
        projection = np.outer(conclusion_state, conclusion_state)
        projected_premise = projection @ premise_state
        
        probability = np.abs(np.dot(projected_premise, premise_state)) ** 2
        return probability
    
    def _counterfactual_probability(self, premise, conclusion):
        """计算反事实概率"""
        # 生成反事实前提
        counterfactual_premise = self._generate_counterfactual(premise)
        
        if not counterfactual_premise:
            return 0.0
        
        # 计算反事实前提下的结论概率
        return self._factual_probability(counterfactual_premise, conclusion)
    
    def _generate_counterfactual(self, premise):
        """生成反事实前提"""
        if len(premise) == 0:
            return None
        
        # 随机替换一个前提概念
        counterfactual = premise.copy()
        replace_index = random.randint(0, len(counterfactual) - 1)
        
        # 选择语义相似但不同的概念
        original_concept = counterfactual[replace_index]
        similar_concepts = self._find_similar_concepts(original_concept, exclude=premise)
        
        if similar_concepts:
            counterfactual[replace_index] = random.choice(similar_concepts)
            return counterfactual
        
        return None
    
    def _find_similar_concepts(self, concept, exclude=None, top_k=5):
        """查找语义相似的概念"""
        if exclude is None:
            exclude = set()
        
        concept_vec = self._encode_concept(concept)
        similarities = []
        
        all_concepts = list(self.known_facts) + \
                      [h['hypothesis'] for hypotheses in self.hypothesis_space.values() 
                       for h in hypotheses]
        
        for other_concept in all_concepts:
            if other_concept == concept or other_concept in exclude:
                continue
            
            other_vec = self._encode_concept(other_concept)
            similarity = np.abs(np.dot(concept_vec, other_vec))
            similarities.append((other_concept, similarity))
        
        # 返回最相似的概念
        similarities.sort(key=lambda x: x[1], reverse=True)
        return [concept for concept, sim in similarities[:top_k] if sim > 0.3]
    
    def _calculate_entropy(self, concepts):
        """计算概念集合的信息熵"""
        if len(concepts) == 0:
            return 0.0
        
        concept_vecs = [self._encode_concept(c) for c in concepts]
        concept_matrix = np.column_stack(concept_vecs)
        
        # 计算协方差矩阵的特征值
        if concept_matrix.shape[1] > 1:
            cov_matrix = np.cov(concept_matrix)
            eigenvalues = np.linalg.eigvalsh(cov_matrix)
            eigenvalues = eigenvalues[eigenvalues > 1e-10]  # 过滤极小值
            
            # 计算香农熵
            normalized_eigenvalues = eigenvalues / np.sum(eigenvalues)
            entropy = -np.sum(normalized_eigenvalues * np.log(normalized_eigenvalues))
            return entropy
        else:
            return 0.0
    
    def _calculate_law_novelty(self, premise, conclusion):
        """计算定律的新颖性"""
        # 检查是否与已知定律重复
        for known_law in self.unknown_laws:
            if (set(premise) == set(known_law.premise_pattern) and
                set(conclusion) == set(known_law.conclusion_pattern)):
                return 0.0
        
        # 基于概念的新颖性和组合的新颖性
        premise_novelty = np.mean([self._calculate_novelty_simple(p) for p in premise])
        conclusion_novelty = np.mean([self._calculate_novelty_simple(c) for c in conclusion])
        
        return (premise_novelty + conclusion_novelty) / 2
    
    def _calculate_applicability(self, premise, conclusion):
        """计算定律的适用性范围"""
        # 基于前提和结论的抽象程度
        premise_abstractness = self._calculate_abstractness(premise)
        conclusion_abstractness = self._calculate_abstractness(conclusion)
        
        return (premise_abstractness + conclusion_abstractness) / 2
    
    def _calculate_abstractness(self, concepts):
        """计算概念集合的抽象程度"""
        if len(concepts) == 0:
            return 0.0
        
        # 抽象概念通常有更多的语义关联
        connectivity_scores = []
        for concept in concepts:
            similar_count = len(self._find_similar_concepts(concept, top_k=10))
            connectivity_scores.append(min(1.0, similar_count / 10.0))
        
        return np.mean(connectivity_scores)
    
    def _get_combined_state(self, concepts):
        """获取概念组合的量子态"""
        if len(concepts) == 0:
            return np.ones(self.cognitive_dim) / math.sqrt(self.cognitive_dim)
        
        concept_vecs = [self._encode_concept(c) for c in concepts]
        combined = np.sum(concept_vecs, axis=0)
        
        # 归一化
        norm = np.linalg.norm(combined)
        if norm > 0:
            combined /= norm
        
        return combined
    
    def _filter_laws(self, candidate_laws, min_support):
        """过滤定律候选"""
        # 基于支持度、新颖性和置信度过滤
        filtered = []
        
        for law in candidate_laws:
            # 计算定律的支持实例数
            support_count = self._count_law_support(law)
            
            if (support_count >= min_support and 
                law.confidence > 0.5 and 
                law.novelty > 0.1):
                filtered.append(law)
        
        return filtered
    
    def _count_law_support(self, law):
        """计算定律的支持实例数"""
        count = 0
        all_concepts = list(self.known_facts)
        
        # 简化支持度计算
        if len(all_concepts) >= len(law.premise_pattern) + len(law.conclusion_pattern):
            count = 2  # 简化处理
        
        return min(count, 10)  # 限制最大计数
    
    def reason_with_unknown(self, query: List[str], max_depth=3):
        """
        在未知条件下的推理
        """
        reasoning_paths = []
        self._recursive_reasoning(query, [], reasoning_paths, max_depth, 0)
        
        # 选择最佳推理路径
        if reasoning_paths:
            best_path = max(reasoning_paths, key=lambda x: x['confidence'])
            return best_path
        else:
            return {'path': [], 'conclusion': "无法推理", 'confidence': 0.0}
    
    def _recursive_reasoning(self, current_state, path, results, max_depth, depth):
        """递归推理过程"""
        if depth >= max_depth:
            return
        
        # 应用未知性定律进行推理
        applicable_laws = self._find_applicable_laws(current_state)
        
        for law in applicable_laws:
            # 生成新状态
            new_state = self._apply_law(current_state, law)
            
            # 构建推理路径
            new_path = path + [{
                'from': current_state.copy(),
                'law': law,
                'to': new_state
            }]
            
            # 计算路径置信度
            path_confidence = self._calculate_path_confidence(new_path)
            
            # 记录结果
            results.append({
                'path': new_path,
                'conclusion': new_state,
                'confidence': path_confidence
            })
            
            # 继续递归推理
            self._recursive_reasoning(new_state, new_path, results, max_depth, depth + 1)
    
    def _find_applicable_laws(self, state):
        """查找适用的未知性定律"""
        applicable = []
        
        for law in self.unknown_laws:
            # 简化的模式匹配 - 实际应该更复杂
            if len(law.premise_pattern) <= len(state):
                match_score = self._calculate_pattern_match(state, law.premise_pattern)
                if match_score > 0.6:
                    applicable.append(law)
        
        return sorted(applicable, key=lambda x: x.confidence, reverse=True)[:3]  # 取前3个
    
    def _calculate_pattern_match(self, state, pattern):
        """计算状态与模式的匹配度"""
        if len(pattern) == 0:
            return 1.0
        
        # 使用语义相似度计算匹配度
        match_scores = []
        
        for pattern_concept in pattern:
            best_match = 0.0
            for state_concept in state:
                pattern_vec = self._encode_concept(pattern_concept)
                state_vec = self._encode_concept(state_concept)
                similarity = np.abs(np.dot(pattern_vec, state_vec))
                best_match = max(best_match, similarity)
            match_scores.append(best_match)
        
        return np.mean(match_scores)
    
    def _apply_law(self, state, law):
        """应用定律生成新状态"""
        # 移除匹配的前提概念
        new_state = state.copy()
        
        # 简化的应用 - 实际应该更智能的模式替换
        for premise_concept in law.premise_pattern:
            if premise_concept in new_state:
                new_state.remove(premise_concept)
        
        # 添加结论概念
        for conclusion_concept in law.conclusion_pattern:
            if conclusion_concept not in new_state:
                new_state.append(conclusion_concept)
        
        return new_state
    
    def _calculate_path_confidence(self, path):
        """计算推理路径的总体置信度"""
        if not path:
            return 0.0
        
        confidences = [step['law'].confidence for step in path]
        return np.prod(confidences) ** (1.0 / len(confidences))  # 几何平均
    
    def creative_synthesis(self, domain_concepts: List[str], num_syntheses=3):
        """
        创造性综合：在未知领域生成新概念
        """
        syntheses = []
        
        for _ in range(num_syntheses):
            # 选择随机概念组合
            combo_size = random.randint(2, min(4, len(domain_concepts)))
            selected_concepts = random.sample(domain_concepts, combo_size)
            
            # 生成概念合成
            synthesis = self._synthesize_concepts(selected_concepts)
            if synthesis and synthesis not in syntheses:
                syntheses.append(synthesis)
        
        return syntheses
    
    def _synthesize_concepts(self, concepts):
        """合成新概念"""
        if len(concepts) < 2:
            return None
        
        # 使用认知地图进行概念融合
        concept_vectors = [self._encode_concept(c) for c in concepts]
        fused_vector = np.mean(concept_vectors, axis=0)
        
        # 添加创造性噪声
        creativity_noise = np.random.normal(0, self.creativity_factor, self.cognitive_dim)
        fused_vector += creativity_noise
        fused_vector /= np.linalg.norm(fused_vector)
        
        # 生成概念名称（简化处理）
        combined_name = "-".join(concepts[:2]) + "-fusion"
        
        return combined_name
    
    def paradox_resolution(self, contradictory_facts: List[str]):
        """
        悖论解析：处理矛盾信息
        """
        # 分析矛盾的性质
        contradiction_level = self._analyze_contradiction(contradictory_facts)
        
        if contradiction_level < self.paradox_tolerance:
            # 低矛盾度，尝试调和
            resolution = self._harmonize_contradictions(contradictory_facts)
        else:
            # 高矛盾度，需要创造性解决
            resolution = self._creative_paradox_resolution(contradictory_facts)
        
        return resolution
    
    def _analyze_contradiction(self, facts):
        """分析矛盾程度"""
        if len(facts) < 2:
            return 0.0
        
        # 计算事实间的语义冲突
        conflict_scores = []
        
        for i, fact1 in enumerate(facts):
            for j, fact2 in enumerate(facts):
                if i >= j:
                    continue
                
                vec1 = self._encode_concept(fact1)
                vec2 = self._encode_concept(fact2)
                
                # 使用角度距离测量冲突
                similarity = np.abs(np.dot(vec1, vec2))
                conflict = 1.0 - similarity
                conflict_scores.append(conflict)
        
        return np.mean(conflict_scores) if conflict_scores else 0.0
    
    def _harmonize_contradictions(self, facts):
        """调和矛盾"""
        # 寻找更高层次的统一概念
        unified_concept = self._find_unifying_concept(facts)
        
        if unified_concept:
            return {
                'type': 'harmonization',
                'resolution': f"在更高层次概念 '{unified_concept}' 下统一",
                'confidence': 0.7
            }
        else:
            return {
                'type': 'contextualization', 
                'resolution': "矛盾源于不同语境，需要语境化理解",
                'confidence': 0.6
            }
    
    def _find_unifying_concept(self, facts):
        """寻找统一概念"""
        fact_vectors = [self._encode_concept(f) for f in facts]
        centroid = np.mean(fact_vectors, axis=0)
        
        # 在已知概念中寻找最接近的
        best_concept = None
        best_similarity = 0.0
        
        for concept in self.known_facts:
            concept_vec = self._encode_concept(concept)
            similarity = np.abs(np.dot(centroid, concept_vec))
            
            if similarity > best_similarity and concept not in facts:
                best_similarity = similarity
                best_concept = concept
        
        return best_concept if best_similarity > 0.6 else None
    
    def _creative_paradox_resolution(self, facts):
        """创造性悖论解决"""
        # 生成新的元概念来解决悖论
        meta_concept = self.creative_synthesis(facts, 1)
        
        if meta_concept:
            return {
                'type': 'meta_synthesis',
                'resolution': f"通过元概念 '{meta_concept[0]}' 超越矛盾",
                'confidence': 0.8
            }
        else:
            return {
                'type': 'embrace_paradox',
                'resolution': "接受悖论作为现实的本质特征",
                'confidence': 0.9
            }

# 演示函数保持不变...
def demonstrate_unknown_law_reasoning():
    """演示未知性定律推理系统"""
    
    # 初始化推理器
    reasoner = UnknownLawReasoner(cognitive_dim=128)
    
    # 输入基础知识（带有不确定性）
    base_knowledge = [
        ("物体受重力下落", ["物理", "运动"], 0.9),
        ("水在0度结冰", ["温度", "状态变化"], 0.8),
        ("植物需要阳光", ["生物", "能量"], 0.85),
        ("市场供需影响价格", ["经济", "交换"], 0.7),
        ("信息传递需要载体", ["通信", "媒介"], 0.75)
    ]
    
    print("学习基础知识...")
    for fact, context, confidence in base_knowledge:
        reasoner.perceive_fact(fact, context, confidence)
    
    # 发现未知性定律
    print("\n发现未知性定律...")
    discovered_laws = reasoner.discover_unknown_laws()
    
    for i, law in enumerate(discovered_laws[:5]):  # 显示前5个定律
        print(f"定律 {i+1}:")
        print(f"  前提: {law.premise_pattern}")
        print(f"  结论: {law.conclusion_pattern}")
        print(f"  置信度: {law.confidence:.3f}")
        print(f"  新颖性: {law.novelty:.3f}")
        print(f"  适用性: {law.applicability:.3f}")
        print()
    
    # 进行未知条件推理
    print("未知条件推理演示:")
    test_queries = [
        ["重力", "能量"],
        ["信息", "价值"], 
        ["生物", "系统"]
    ]
    
    for query in test_queries:
        print(f"\n查询: {query}")
        result = reasoner.reason_with_unknown(query)
        print(f"推理结论: {result['conclusion']}")
        print(f"推理置信度: {result['confidence']:.3f}")
    
    # 创造性综合演示
    print(f"\n创造性综合演示:")
    domains = [["量子", "信息", "计算"], ["生命", "机器", "智能"]]
    
    for domain in domains:
        syntheses = reasoner.creative_synthesis(domain)
        print(f"领域 {domain} 的新概念: {syntheses}")
    
    # 悖论解析演示
    print(f"\n悖论解析演示:")
    paradoxes = [
        ["光既是粒子又是波", "粒子波性质互斥"],
        ["自由市场最优", "市场需要监管"],
        ["知识越多未知越多", "知识减少未知"]
    ]
    
    for paradox in paradoxes:
        resolution = reasoner.paradox_resolution(paradox)
        print(f"悖论: {paradox}")
        print(f"解析: {resolution['resolution']} (置信度: {resolution['confidence']:.3f})")
        print()

def advanced_demonstration():
    """高级演示：模拟科学发现过程"""
    
    reasoner = UnknownLawReasoner(cognitive_dim=256)
    
    # 模拟科学观察数据
    scientific_observations = [
        ("行星轨道是椭圆", ["天体", "运动"], 0.95),
        ("物种随时间变化", ["生物", "时间"], 0.8),
        ("能量守恒", ["物理", "转化"], 0.9),
        ("信息熵增", ["系统", "无序"], 0.75),
        ("量子叠加", ["微观", "状态"], 0.7)
    ]
    
    print("=== 科学发现模拟 ===")
    print("输入观察数据...")
    for obs, context, conf in scientific_observations:
        reasoner.perceive_fact(obs, context, conf)
    
    # 发现科学定律
    print("\n发现潜在科学定律...")
    science_laws = reasoner.discover_unknown_laws(min_confidence=0.7)
    
    for i, law in enumerate(science_laws[:3]):
        print(f"潜在定律 {i+1}:")
        print(f"  模式: {law.premise_pattern} -> {law.conclusion_pattern}")
        print(f"  置信度: {law.confidence:.3f}, 新颖性: {law.novelty:.3f}")
        
        # 测试定律的预测能力
        prediction = reasoner.reason_with_unknown(law.premise_pattern)
        print(f"  预测示例: {law.premise_pattern} => {prediction['conclusion']}")
        print()
    
    # 生成研究假设
    print("生成研究假设...")
    research_domains = [["量子", "引力", "统一"], ["意识", "计算", "实现"]]
    
    for domain in research_domains:
        hypotheses = reasoner.creative_synthesis(domain, num_syntheses=2)
        print(f"领域 {domain} 的研究假设: {hypotheses}")

if __name__ == "__main__":
    demonstrate_unknown_law_reasoning()
    advanced_demonstration()