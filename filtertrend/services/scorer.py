import math
import numpy as np

class TrendScorer:
    def __init__(self):
        # Веса из документа Aristotle
        self.w1 = 0.4  # Similarity (Схожесть)
        self.w2 = 0.4  # Uplift (Эффективность)
        self.w3 = 0.2  # Reach (Охват)

    def calculate_normalized_reach(self, views: int, followers: int) -> float:
        """
        Формула 3.2: Log-Normal Reach
        Справедливое сравнение маленьких и больших аккаунтов.
        """
        if followers < 1: followers = 1
        if views < 1: views = 1
        
        # log(views + 1) / log(followers + 1)
        return math.log(views + 1) / math.log(followers + 1)

    def calculate_similarity(self, vec1: list, vec2: list) -> float:
        """
        Формула 3.1: Косинусное сходство [-1, 1]
        """
        if not vec1 or not vec2:
            return 0.0
        
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        
        dot_product = np.dot(v1, v2)
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)
        
        if norm_v1 == 0 or norm_v2 == 0:
            return 0.0
            
        return float(dot_product / (norm_v1 * norm_v2))

    def calculate_transfer_score(self, similarity: float, uplift: float, reach: float) -> float:
        """
        Формула 3.4: Transfer Score (UTS)
        Предсказывает успех шаблона для конкретного бизнеса.
        """
        # UTS = w1*S + w2*U + w3*R
        score = (self.w1 * similarity) + (self.w2 * uplift) + (self.w3 * reach)
        return round(score, 3)