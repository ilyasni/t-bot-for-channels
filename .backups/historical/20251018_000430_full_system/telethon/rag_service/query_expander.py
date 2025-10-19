"""
Query Expander
Расширение запросов через Neo4j tag relationships

Best practices:
- Использовать tag co-occurrence из графа
- Избегать over-expansion (max 3-5 терминов)
- Graceful degradation (работает без Neo4j)
"""
import logging
import re
from typing import List, Set, Optional
import os

# Импорты
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from graph.neo4j_client import neo4j_client

logger = logging.getLogger(__name__)


class QueryExpander:
    """
    Расширение пользовательских запросов через Neo4j tag relationships
    
    Example:
        ```python
        expander = QueryExpander()
        
        original = "AI новости"
        expanded = await expander.expand_query(original)
        # → "AI новости машинное обучение нейросети ChatGPT"
        ```
    
    Best practice: Query expansion улучшает recall при векторном поиске
    """
    
    def __init__(self):
        """Инициализация query expander"""
        self.enabled = neo4j_client.enabled
        self.max_expansions = int(os.getenv("QUERY_EXPANSION_MAX_TERMS", "3"))
        
        # Стоп-слова (не расширяем их)
        self.stop_words = {
            'что', 'где', 'когда', 'как', 'почему', 'какие', 'какой', 'какая',
            'про', 'для', 'был', 'были', 'было', 'есть', 'это', 'эти', 'этот',
            'можно', 'нужно', 'расскажи', 'сделай', 'покажи', 'дай',
            'писали', 'говорили', 'произошло', 'случилось', 'за', 'на', 'в', 'с',
            'и', 'или', 'но', 'а', 'то'
        }
        
        logger.info(f"✅ QueryExpander initialized (enabled: {self.enabled}, max_expansions: {self.max_expansions})")
    
    async def expand_query(
        self,
        query: str,
        user_id: Optional[int] = None,
        max_terms: Optional[int] = None
    ) -> str:
        """
        Расширить запрос через tag relationships из графа
        
        Args:
            query: Исходный запрос пользователя
            user_id: ID пользователя (для персонализации в будущем)
            max_terms: Максимум терминов для добавления (default: из config)
        
        Returns:
            Расширенный запрос или исходный (если расширение невозможно)
        
        Algorithm:
            1. Извлечь ключевые слова из запроса
            2. Для каждого ключевого слова найти related tags в Neo4j
            3. Добавить top N related tags к запросу
            4. Return expanded query
        """
        if not self.enabled:
            return query
        
        if max_terms is None:
            max_terms = self.max_expansions
        
        try:
            # 1. Извлечь ключевые слова
            keywords = self._extract_keywords(query)
            
            if not keywords:
                logger.debug("No keywords found for expansion")
                return query
            
            logger.debug(f"🔍 Keywords extracted: {keywords}")
            
            # 2. Найти related tags для каждого keyword
            expanded_terms: Set[str] = set()
            
            for keyword in keywords[:2]:  # Limit to first 2 keywords (avoid over-expansion)
                try:
                    # Запросить related tags из Neo4j
                    related = await neo4j_client.get_tag_relationships(
                        tag_name=keyword,
                        limit=max_terms
                    )
                    
                    if related:
                        # Добавить названия related tags
                        related_names = [r.get('tag') for r in related if r.get('tag')]
                        expanded_terms.update(related_names[:max_terms])
                        logger.debug(f"   '{keyword}' → {related_names[:max_terms]}")
                        
                except Exception as e:
                    logger.warning(f"⚠️ Failed to get related tags for '{keyword}': {e}")
            
            # 3. Собрать expanded query
            if expanded_terms:
                # Фильтруем термины которые уже есть в запросе
                query_lower = query.lower()
                new_terms = [
                    term for term in expanded_terms
                    if term.lower() not in query_lower
                ]
                
                if new_terms:
                    # Limit to max_terms
                    new_terms = new_terms[:max_terms]
                    expanded_query = f"{query} {' '.join(new_terms)}"
                    
                    logger.info(f"✨ Query expanded: '{query}' → '{expanded_query}'")
                    return expanded_query
            
            # Нет расширений
            logger.debug(f"No expansion for query: '{query}'")
            return query
            
        except Exception as e:
            logger.error(f"❌ Query expansion failed: {e}")
            return query  # Fallback to original
    
    def _extract_keywords(self, query: str) -> List[str]:
        """
        Извлечь ключевые слова из запроса
        
        Args:
            query: Текст запроса
        
        Returns:
            Список ключевых слов (отфильтрованы стоп-слова, min length=3)
        
        Best practice: Simple regex-based extraction
        """
        # Очистить от пунктуации
        query_clean = query.lower()
        query_clean = re.sub(r'[^\w\s]', ' ', query_clean)
        
        # Разбить на слова
        words = query_clean.split()
        
        # Фильтровать:
        # - Стоп-слова
        # - Короткие слова (< 3 символа)
        # - Дубликаты
        keywords = []
        seen = set()
        
        for word in words:
            if (
                len(word) >= 3 and
                word not in self.stop_words and
                word not in seen
            ):
                keywords.append(word)
                seen.add(word)
        
        return keywords
    
    def add_stop_word(self, word: str):
        """
        Добавить стоп-слово (для кастомизации)
        
        Args:
            word: Слово для добавления в stop list
        """
        self.stop_words.add(word.lower())
        logger.debug(f"Added stop word: {word}")
    
    def remove_stop_word(self, word: str):
        """
        Удалить стоп-слово
        
        Args:
            word: Слово для удаления из stop list
        """
        self.stop_words.discard(word.lower())
        logger.debug(f"Removed stop word: {word}")


# Singleton instance
query_expander = QueryExpander()

