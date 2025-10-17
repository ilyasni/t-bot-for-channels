"""
Feature Flags для A/B тестирования

Best practices:
- Percentage-based rollout
- Per-user consistent assignment
- Easy rollback (disable flag)
- Metrics tracking
"""
import logging
import os
import hashlib
from typing import Optional

logger = logging.getLogger(__name__)


class FeatureFlags:
    """
    Feature flags для постепенного rollout новых фич
    
    Usage:
        ```python
        flags = FeatureFlags()
        
        if flags.is_enabled('hybrid_search', user_id=123):
            # Use hybrid search
            results = await enhanced_search.search_with_graph_context(...)
        else:
            # Use baseline search
            results = await search_service.search(...)
        ```
    """
    
    def __init__(self):
        """Инициализация feature flags"""
        # Feature: Hybrid Search
        self.hybrid_search_enabled = os.getenv("USE_HYBRID_SEARCH", "false").lower() == "true"
        self.hybrid_search_percentage = int(os.getenv("HYBRID_SEARCH_PERCENTAGE", "10"))
        
        # Feature: Query Expansion
        self.query_expansion_enabled = os.getenv("USE_QUERY_EXPANSION", "false").lower() == "true"
        self.query_expansion_percentage = int(os.getenv("QUERY_EXPANSION_PERCENTAGE", "0"))
        
        logger.info("✅ FeatureFlags initialized:")
        logger.info(f"   Hybrid Search: {self.hybrid_search_enabled} ({self.hybrid_search_percentage}%)")
        logger.info(f"   Query Expansion: {self.query_expansion_enabled} ({self.query_expansion_percentage}%)")
    
    def is_enabled(self, feature_name: str, user_id: Optional[int] = None) -> bool:
        """
        Проверить включена ли фича для пользователя
        
        Args:
            feature_name: Название фичи (hybrid_search, query_expansion)
            user_id: ID пользователя (для percentage rollout)
        
        Returns:
            True если фича включена для этого пользователя
        
        Algorithm:
            - Если флаг полностью выключен → False
            - Если percentage=100 → True для всех
            - Если percentage=10 → True для 10% пользователей (consistent hash)
        """
        if feature_name == "hybrid_search":
            if not self.hybrid_search_enabled:
                return False
            
            if self.hybrid_search_percentage >= 100:
                return True
            
            if self.hybrid_search_percentage <= 0:
                return False
            
            # Percentage-based rollout с consistent assignment
            return self._is_in_percentage(user_id, self.hybrid_search_percentage)
        
        elif feature_name == "query_expansion":
            if not self.query_expansion_enabled:
                return False
            
            if self.query_expansion_percentage >= 100:
                return True
            
            if self.query_expansion_percentage <= 0:
                return False
            
            return self._is_in_percentage(user_id, self.query_expansion_percentage)
        
        else:
            logger.warning(f"Unknown feature flag: {feature_name}")
            return False
    
    def _is_in_percentage(self, user_id: Optional[int], percentage: int) -> bool:
        """
        Определить входит ли пользователь в percentage
        
        Использует consistent hashing для стабильного assignment
        
        Args:
            user_id: ID пользователя
            percentage: Процент включения (0-100)
        
        Returns:
            True если пользователь в percentage
        
        Best practice: consistent assignment
        - Один и тот же user всегда в одной группе
        - Используем hash(user_id) % 100 < percentage
        """
        if user_id is None:
            # Если user_id нет, используем random assignment
            import random
            return random.randint(0, 99) < percentage
        
        # Consistent hash-based assignment
        # hash(user_id) % 100 даст число от 0 до 99
        hash_value = hashlib.md5(str(user_id).encode()).hexdigest()
        hash_int = int(hash_value[:8], 16)  # Первые 8 символов hex
        bucket = hash_int % 100
        
        return bucket < percentage


# Singleton instance
feature_flags = FeatureFlags()

