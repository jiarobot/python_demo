import torch
import torch.nn as nn
import torch.nn.functional as F

class DifferentiableFOL(nn.Module):
    """
    可微分一阶逻辑推理层
    实现谓词逻辑的可微分近似
    """
    def __init__(self, num_predicates, num_constants, embedding_dim=64):
        super().__init__()
        self.num_predicates = num_predicates
        self.num_constants = num_constants
        self.embedding_dim = embedding_dim
        
        # 谓词嵌入
        self.predicate_embeddings = nn.Embedding(num_predicates, embedding_dim)
        
        # 常量嵌入
        self.constant_embeddings = nn.Embedding(num_constants, embedding_dim)
        
        # 逻辑连接词参数
        self.conjunction_weights = nn.Parameter(torch.randn(embedding_dim, embedding_dim))
        self.disjunction_weights = nn.Parameter(torch.randn(embedding_dim, embedding_dim))
        self.negation_weights = nn.Parameter(torch.randn(embedding_dim, embedding_dim))
        
        # 量词参数
        self.universal_weights = nn.Parameter(torch.randn(embedding_dim, embedding_dim))
        self.existential_weights = nn.Parameter(torch.randn(embedding_dim, embedding_dim))
        
    def soft_forall(self, embeddings, dim=1):
        """软全称量词实现"""
        # 使用softmin近似全称量词
        weights = F.softmax(-embeddings, dim=dim)
        return torch.sum(weights * embeddings, dim=dim)
    
    def soft_exists(self, embeddings, dim=1):
        """软存在量词实现"""
        # 使用softmax近似存在量词
        weights = F.softmax(embeddings, dim=dim)
        return torch.sum(weights * embeddings, dim=dim)
    
    def soft_and(self, x, y):
        """软逻辑与"""
        return torch.sigmoid(
            torch.matmul(x, self.conjunction_weights) + 
            torch.matmul(y, self.conjunction_weights)
        )
    
    def soft_or(self, x, y):
        """软逻辑或"""
        return torch.sigmoid(
            torch.matmul(x, self.disjunction_weights) + 
            torch.matmul(y, self.disjunction_weights)
        )
    
    def soft_not(self, x):
        """软逻辑非"""
        return torch.sigmoid(torch.matmul(x, self.negation_weights))
    
    def forward(self, input_tokens, logical_formula):
        """
        Args:
            input_tokens: [batch_size, seq_len] 输入token索引
            logical_formula: 逻辑公式的字符串表示
        """
        batch_size, seq_len = input_tokens.shape
        
        # 获取常量嵌入
        constant_embeds = self.constant_embeddings(input_tokens)  # [batch_size, seq_len, embed_dim]
        
        # 解析并执行逻辑公式
        result = self.evaluate_formula(logical_formula, constant_embeds, batch_size)
        
        return result
    
    def evaluate_formula(self, formula, embeddings, batch_size):
        """递归评估逻辑公式"""
        if "∀" in formula:
            # 全称量词处理
            var, subformula = formula.split(":", 1)
            var = var.replace("∀", "").strip()
            # 对每个位置应用子公式
            sub_results = []
            for i in range(embeddings.size(1)):
                sub_embeds = embeddings[:, i:i+1]  # 选择第i个位置
                sub_result = self.evaluate_formula(subformula, sub_embeds, batch_size)
                sub_results.append(sub_result)
            
            sub_results = torch.stack(sub_results, dim=1)  # [batch_size, seq_len, embed_dim]
            return self.soft_forall(sub_results, dim=1)
        
        elif "∃" in formula:
            # 存在量词处理
            var, subformula = formula.split(":", 1)
            var = var.replace("∃", "").strip()
            sub_results = []
            for i in range(embeddings.size(1)):
                sub_embeds = embeddings[:, i:i+1]
                sub_result = self.evaluate_formula(subformula, sub_embeds, batch_size)
                sub_results.append(sub_result)
            
            sub_results = torch.stack(sub_results, dim=1)
            return self.soft_exists(sub_results, dim=1)
        
        elif "∧" in formula:
            # 合取处理
            left, right = formula.split("∧", 1)
            left_result = self.evaluate_formula(left.strip(), embeddings, batch_size)
            right_result = self.evaluate_formula(right.strip(), embeddings, batch_size)
            return self.soft_and(left_result, right_result)
        
        elif "∨" in formula:
            # 析取处理
            left, right = formula.split("∨", 1)
            left_result = self.evaluate_formula(left.strip(), embeddings, batch_size)
            right_result = self.evaluate_formula(right.strip(), embeddings, batch_size)
            return self.soft_or(left_result, right_result)
        
        elif "¬" in formula:
            # 否定处理
            subformula = formula.replace("¬", "").strip()
            sub_result = self.evaluate_formula(subformula, embeddings, batch_size)
            return self.soft_not(sub_result)
        
        else:
            # 原子谓词
            predicate_idx = int(formula.strip())
            predicate_embed = self.predicate_embeddings(
                torch.tensor(predicate_idx).to(embeddings.device)
            )
            # 应用谓词到所有常量
            return torch.matmul(embeddings, predicate_embed.unsqueeze(-1)).squeeze(-1)
    
    def get_attention_weights(self, formula, embeddings):
        """获取逻辑推理的注意力权重（用于可解释性）"""
        # 简化的注意力计算
        if "∀" in formula or "∃" in formula:
            weights = torch.softmax(embeddings.mean(dim=-1), dim=-1)
            return weights
        return None