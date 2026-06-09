import numpy as np
from scipy import linalg
import math
from collections import defaultdict
import random

class QuantumSemanticField:
    def __init__(self, semantic_dimensions=1024):
        """
        量子语义场模型
        semantic_dimensions: 语义场的维度数（希尔伯特空间维度）
        """
        self.dim = semantic_dimensions
        self.semantic_basis = self._initialize_semantic_basis()
        self.word_states = {}
        self.context_operator = None
        
    def _initialize_semantic_basis(self):
        """初始化语义基向量 - 构建正交的语义特征空间"""
        # 使用随机正交矩阵作为语义基
        random_matrix = np.random.randn(self.dim, self.dim)
        q, r = linalg.qr(random_matrix)
        return q
    
    def encode_word(self, word, semantic_vector=None):
        """
        将词语编码为语义场中的量子态
        """
        if semantic_vector is None:
            # 随机生成语义向量，但保持归一化
            semantic_vector = np.random.randn(self.dim)
            semantic_vector = semantic_vector / np.linalg.norm(semantic_vector)
        
        # 量子态表示：复数向量，模长为1
        quantum_state = semantic_vector.astype(complex)
        self.word_states[word] = quantum_state
        return quantum_state
    
    def semantic_overlap(self, word1, word2):
        """计算两个词语的语义重叠度（内积）"""
        if word1 not in self.word_states or word2 not in self.word_states:
            return 0.0
        
        state1 = self.word_states[word1]
        state2 = self.word_states[word2]
        
        # 量子力学中的概率幅
        overlap = np.abs(np.vdot(state1, state2)) ** 2
        return overlap
    
    def contextual_evolution(self, words, context_strength=0.1):
        """
        语境演化：词语在特定语境下的语义演化
        使用薛定谔方程模拟语义演化
        """
        if not words:
            return {}
        
        # 构建语境哈密顿量
        hamiltonian = self._build_context_hamiltonian(words)
        
        evolved_states = {}
        for word in words:
            if word in self.word_states:
                initial_state = self.word_states[word]
                # 时间演化算子: exp(-iHt)
                evolution_operator = linalg.expm(-1j * context_strength * hamiltonian)
                evolved_state = evolution_operator @ initial_state
                evolved_states[word] = evolved_state / np.linalg.norm(evolved_state)
        
        return evolved_states
    
    def _build_context_hamiltonian(self, words):
        """构建语境哈密顿量"""
        hamiltonian = np.zeros((self.dim, self.dim), dtype=complex)
        
        for word in words:
            if word in self.word_states:
                state = self.word_states[word]
                # 投影算子 |ψ⟩⟨ψ|
                projector = np.outer(state, np.conj(state))
                hamiltonian += projector
        
        # 使哈密顿量为厄米算符
        hamiltonian = (hamiltonian + np.conj(hamiltonian.T)) / 2
        return hamiltonian
    
class SemanticResonanceProcessor:
    def __init__(self, field_dim=1024):
        self.semantic_field = QuantumSemanticField(field_dim)
        self.resonance_memory = defaultdict(list)
        
    def learn_corpus(self, corpus):
        """从语料库学习语义场"""
        word_frequencies = defaultdict(int)
        cooccurrence = defaultdict(lambda: defaultdict(int))
        
        # 分析语料库
        for document in corpus:
            words = self._tokenize(document)
            for i, word in enumerate(words):
                word_frequencies[word] += 1
                # 构建共现矩阵
                for j in range(max(0, i-3), min(len(words), i+4)):
                    if i != j:
                        cooccurrence[word][words[j]] += 1
        
        # 基于共现关系编码词语
        for word in word_frequencies:
            semantic_vector = self._compute_semantic_vector(word, cooccurrence)
            self.semantic_field.encode_word(word, semantic_vector)
    
    def _compute_semantic_vector(self, word, cooccurrence):
        """基于共现关系计算语义向量"""
        vector = np.zeros(self.semantic_field.dim)
        
        if word not in cooccurrence:
            return np.random.randn(self.semantic_field.dim)
        
        context_words = list(cooccurrence[word].keys())
        weights = [cooccurrence[word][w] for w in context_words]
        
        # 使用语义基向量的线性组合
        for i, (context_word, weight) in enumerate(zip(context_words, weights)):
            basis_index = i % self.semantic_field.dim
            vector[basis_index] += weight / (i + 1)  # 距离衰减
        
        # 归一化
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        
        return vector
    
    def semantic_resonance(self, query, context_words, threshold=0.1):
        """
        语义共振理解：查询与语境的共振程度
        """
        # 语境演化
        evolved_states = self.semantic_field.contextual_evolution(context_words)
        
        if query not in self.semantic_field.word_states:
            return 0.0
        
        query_state = self.semantic_field.word_states[query]
        total_resonance = 0.0
        resonance_count = 0
        
        for word, evolved_state in evolved_states.items():
            resonance = np.abs(np.vdot(query_state, evolved_state)) ** 2
            if resonance > threshold:
                total_resonance += resonance
                resonance_count += 1
        
        return total_resonance / max(resonance_count, 1)
    
    def understand_sentence(self, sentence, max_iterations=10):
        """
        句子理解：通过语义共振迭代理解
        """
        words = self._tokenize(sentence)
        if not words:
            return {}
        
        # 初始化理解状态
        understanding = {word: 0.5 for word in words}  # 初始理解度0.5
        
        for iteration in range(max_iterations):
            new_understanding = understanding.copy()
            
            for i, target_word in enumerate(words):
                context = [words[j] for j in range(len(words)) if j != i]
                resonance = self.semantic_resonance(target_word, context)
                
                # 共振驱动的理解更新
                new_understanding[target_word] = (
                    0.7 * understanding[target_word] + 
                    0.3 * resonance
                )
            
            # 检查收敛
            changes = [abs(new_understanding[w] - understanding[w]) for w in words]
            if max(changes) < 0.01:
                break
                
            understanding = new_understanding
        
        return understanding
    
    def _tokenize(self, text):
        """简单的分词"""
        return [word.lower().strip('.,!?;') for word in text.split() if word.strip()]
    
    def creative_generation(self, seed_words, num_concepts=5):
        """
        创造性生成：基于语义场的概念组合
        """
        concepts = []
        
        for _ in range(num_concepts):
            # 选择种子词的语义叠加
            superposed_state = np.zeros(self.semantic_field.dim, dtype=complex)
            
            for word in seed_words:
                if word in self.semantic_field.word_states:
                    state = self.semantic_field.word_states[word]
                    # 量子叠加
                    superposed_state += state * (1.0 / len(seed_words))
            
            if np.linalg.norm(superposed_state) > 0:
                superposed_state = superposed_state / np.linalg.norm(superposed_state)
                
                # 寻找最接近的现有概念
                best_match = None
                best_similarity = 0
                
                for word, state in self.semantic_field.word_states.items():
                    similarity = np.abs(np.vdot(superposed_state, state)) ** 2
                    if similarity > best_similarity and word not in seed_words:
                        best_similarity = similarity
                        best_match = word
                
                if best_match and best_similarity > 0.3:
                    concepts.append((best_match, best_similarity))
        
        return sorted(concepts, key=lambda x: x[1], reverse=True)
    
def demo_quantum_semantics():
    """演示量子语义场算法"""
    
    # 初始化处理器
    processor = SemanticResonanceProcessor(field_dim=512)
    
    # 训练语料
    corpus = [
        "人工智能正在改变世界",
        "机器学习是人工智能的重要分支",
        "深度学习让计算机能够理解复杂模式",
        "自然语言处理帮助机器理解人类语言",
        "量子计算提供新的计算范式",
        "语义理解是自然语言处理的核心",
        "算法优化提升机器学习性能"
    ]
    
    print("学习语料库...")
    processor.learn_corpus(corpus)
    
    # 测试语义理解
    test_sentences = [
        "机器学习理解自然语言",
        "量子人工智能算法",
        "深度学习优化语义理解"
    ]
    
    for sentence in test_sentences:
        print(f"\n理解句子: '{sentence}'")
        understanding = processor.understand_sentence(sentence)
        for word, score in understanding.items():
            print(f"  {word}: {score:.3f}")
    
    # 测试创造性生成
    print(f"\n创造性概念生成:")
    seed_concepts = ["量子", "语义", "学习"]
    new_concepts = processor.creative_generation(seed_concepts, 3)
    for concept, confidence in new_concepts:
        print(f"  新概念: {concept} (置信度: {confidence:.3f})")
    
    # 测试语义相似度
    print(f"\n语义相似度分析:")
    word_pairs = [("人工智能", "机器学习"), ("量子", "计算"), ("语言", "算法")]
    for word1, word2 in word_pairs:
        similarity = processor.semantic_field.semantic_overlap(word1, word2)
        print(f"  '{word1}' vs '{word2}': {similarity:.3f}")

if __name__ == "__main__":
    demo_quantum_semantics()