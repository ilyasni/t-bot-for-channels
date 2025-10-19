"""
Enhanced Search Service
Hybrid search: Qdrant (vector) + Neo4j (graph)

Best practices from neo4j-graphrag HybridRetriever:
- Parallel execution (asyncio.gather)
- Graph-aware ranking
- Context expansion
- Graceful degradation
"""
import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

# Импорты зависимостей
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from graph.neo4j_client import neo4j_client
from rag_service.search import search_service
from rag_service.metrics import (
    hybrid_search_duration_seconds,
    hybrid_search_results_total,
    graph_expansion_added_docs,
    combined_score_distribution,
    record_hybrid_search
)
import time

# Query expansion (опционально)
try:
    from rag_service.query_expander import query_expander
    from rag_service.feature_flags import feature_flags as ff
    QUERY_EXPANSION_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ Query expansion not available")
    QUERY_EXPANSION_AVAILABLE = False
    query_expander = None
    ff = None

logger = logging.getLogger(__name__)


class EnhancedSearchService:
    """
    Hybrid search combining Qdrant vector search and Neo4j graph context
    
    Architecture:
        1. Parallel: Qdrant search + Neo4j personalization signals
        2. Expand: Add graph-related posts
        3. Rank: Combined score (vector + graph)
    
    Usage:
        ```python
        enhanced_search = EnhancedSearchService()
        
        results = await enhanced_search.search_with_graph_context(
            query="AI новости",
            user_id=123,
            limit=10
        )
        ```
    """
    
    def __init__(self):
        """Инициализация enhanced search service"""
        self.search_service = search_service
        self.neo4j_enabled = neo4j_client.enabled
        logger.info(f"✅ EnhancedSearchService initialized (Neo4j: {self.neo4j_enabled})")
    
    async def search_with_graph_context(
        self,
        query: str,
        user_id: int,
        limit: int = 10,
        expand_graph: bool = True,
        graph_weight: float = 0.3,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search с graph context
        
        Args:
            query: Поисковый запрос
            user_id: ID пользователя
            limit: Финальное количество результатов
            expand_graph: Расширять ли контекст через граф
            graph_weight: Вес graph score (0.0-1.0)
            **kwargs: Дополнительные параметры для vector search
        
        Returns:
            Ranked список постов с combined scores
        
        Flow:
            1. Parallel: Qdrant search (limit*2) + Neo4j signals
            2. Expand: добавить related posts через граф
            3. Rank: (1-w)*vector_score + w*graph_score
            4. Return: top K results
        """
        # Start timer
        start_time = time.time()
        
        try:
            # Если Neo4j недоступен - fallback на обычный search
            if not self.neo4j_enabled or not expand_graph:
                logger.info("🔍 Fallback to vector-only search (Neo4j disabled)")
                results = await self.search_service.search(
                    query=query,
                    user_id=user_id,
                    limit=limit,
                    **kwargs
                )
                
                # Record metrics
                duration = time.time() - start_time
                record_hybrid_search(
                    duration=duration,
                    results_count=len(results),
                    mode="fallback_vector_only"
                )
                
                return results
            
            logger.info(f"🔍 Hybrid search for user {user_id}: '{query}' (graph_weight={graph_weight})")
            
            # Query expansion (если включен feature flag)
            expanded_query = query
            if QUERY_EXPANSION_AVAILABLE and query_expander and ff:
                if ff.is_enabled('query_expansion', user_id=user_id):
                    try:
                        expanded_query = await query_expander.expand_query(
                            query=query,
                            user_id=user_id
                        )
                        if expanded_query != query:
                            logger.info(f"✨ Query expanded: '{query}' → '{expanded_query}'")
                    except Exception as e:
                        logger.warning(f"⚠️ Query expansion failed: {e}")
            
            # 1. Parallel execution: Vector search + Graph signals
            vector_results, graph_signals = await asyncio.gather(
                self._vector_search(expanded_query, user_id, limit * 2, **kwargs),  # Use expanded query
                self._get_graph_signals(user_id),
                return_exceptions=True
            )
            
            # Handle exceptions
            if isinstance(vector_results, Exception):
                logger.error(f"❌ Vector search failed: {vector_results}")
                return []
            
            if isinstance(graph_signals, Exception):
                logger.warning(f"⚠️ Graph signals failed: {graph_signals}, continuing without")
                graph_signals = {"user_interests": [], "trending_tags": []}
            
            if not vector_results:
                return []
            
            # 2. Expand with graph context
            graph_context = []
            if expand_graph and len(vector_results) > 0:
                post_ids = [r.get('post_id') for r in vector_results if r.get('post_id')]
                if post_ids:
                    graph_context = await neo4j_client.expand_with_graph(
                        post_ids=post_ids,
                        limit_per_post=2  # 2 related posts per result
                    )
            
            # 3. Merge and rank
            combined_results = self._rank_with_graph(
                vector_results=vector_results,
                graph_context=graph_context,
                graph_signals=graph_signals,
                graph_weight=graph_weight
            )
            
            # 4. Return top K
            top_results = combined_results[:limit]
            
            # Record metrics
            duration = time.time() - start_time
            avg_score = sum(r.get('combined_score', 0) for r in top_results) / len(top_results) if top_results else 0
            
            record_hybrid_search(
                duration=duration,
                results_count=len(top_results),
                mode="hybrid",
                avg_combined_score=avg_score
            )
            
            # Record graph expansion
            if graph_expansion_added_docs:
                total_graph_docs = sum(len(g.get('related_posts', [])) for g in graph_context)
                graph_expansion_added_docs.observe(total_graph_docs)
            
            logger.info(f"✅ Hybrid search returned {len(top_results)} results "
                       f"(from {len(vector_results)} vector + {len(graph_context)} graph) "
                       f"in {duration:.3f}s")
            
            return top_results
            
        except Exception as e:
            logger.error(f"❌ Enhanced search failed: {e}", exc_info=True)
            # Fallback to vector search
            try:
                return await self.search_service.search(
                    query=query,
                    user_id=user_id,
                    limit=limit,
                    **kwargs
                )
            except:
                return []
    
    async def _vector_search(
        self,
        query: str,
        user_id: int,
        limit: int,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Векторный поиск через Qdrant
        
        Используется existing search_service
        """
        try:
            results = await self.search_service.search(
                query=query,
                user_id=user_id,
                limit=limit,
                **kwargs
            )
            
            # Ensure results have required fields
            for r in results:
                if 'score' not in r:
                    r['score'] = 0.0
                if 'post_id' not in r:
                    r['post_id'] = r.get('id')
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Vector search error: {e}")
            return []
    
    async def _get_graph_signals(self, user_id: int) -> Dict[str, Any]:
        """
        Получить graph signals для персонализации
        
        Returns:
            {
                "user_interests": [{"tag": "AI", "posts_count": 42}, ...],
                "trending_tags": [{"name": "AI", "posts_count": 125}, ...]
            }
        """
        try:
            # Нужен telegram_id для Neo4j
            # TODO: получить telegram_id из user_id (DB query)
            # Временно: просто вызываем с user_id как telegram_id
            
            user_interests, trending_tags = await asyncio.gather(
                neo4j_client.get_user_interests(
                    telegram_id=user_id,  # FIXME: нужен маппинг
                    limit=20
                ),
                neo4j_client.get_trending_tags(days=3, limit=10),
                return_exceptions=True
            )
            
            if isinstance(user_interests, Exception):
                user_interests = []
            if isinstance(trending_tags, Exception):
                trending_tags = []
            
            return {
                "user_interests": user_interests,
                "trending_tags": trending_tags
            }
            
        except Exception as e:
            logger.error(f"❌ Graph signals error: {e}")
            return {"user_interests": [], "trending_tags": []}
    
    def _rank_with_graph(
        self,
        vector_results: List[Dict],
        graph_context: List[Dict],
        graph_signals: Dict,
        graph_weight: float
    ) -> List[Dict[str, Any]]:
        """
        Graph-aware ranking algorithm
        
        Combined score = (1 - graph_weight) * vector_score + graph_weight * graph_score
        
        Graph score components:
            - Tag overlap with user interests (+0.2)
            - Presence in graph context (+0.3)
            - Recency boost (+0.1)
        
        Args:
            vector_results: Результаты от Qdrant
            graph_context: Расширенный контекст от Neo4j
            graph_signals: User interests + trending tags
            graph_weight: Вес graph score (0.0-1.0)
        
        Returns:
            Отсортированный список с combined_score
        """
        # Извлечь user interest tags
        user_tags = {
            interest.get("tag", "").lower()
            for interest in graph_signals.get("user_interests", [])
        }
        
        # Trending tags
        trending_tags = {
            tag.get("name", "").lower()
            for tag in graph_signals.get("trending_tags", [])
        }
        
        # Создать lookup для graph context
        graph_lookup = {}
        for item in graph_context:
            source_id = item.get("source_post_id")
            if source_id:
                graph_lookup[source_id] = item.get("related_posts", [])
        
        # Ранжировать каждый результат
        ranked = []
        for result in vector_results:
            vector_score = result.get('score', 0.0)
            post_id = result.get('post_id')
            tags = result.get('tags', [])
            posted_at = result.get('posted_at')
            
            # Compute graph score
            graph_score = 0.0
            
            # Component 1: Tag overlap with user interests (0-0.3)
            if tags and user_tags:
                overlap = sum(1 for tag in tags if tag.lower() in user_tags)
                graph_score += min(0.3, overlap * 0.1)
            
            # Component 2: Trending tags bonus (0-0.2)
            if tags and trending_tags:
                trending_overlap = sum(1 for tag in tags if tag.lower() in trending_tags)
                graph_score += min(0.2, trending_overlap * 0.1)
            
            # Component 3: In graph context (0-0.3)
            if post_id in graph_lookup and graph_lookup[post_id]:
                graph_score += 0.3
            
            # Component 4: Recency boost (0-0.2)
            if posted_at:
                try:
                    if isinstance(posted_at, str):
                        post_date = datetime.fromisoformat(posted_at.replace('Z', '+00:00'))
                    else:
                        post_date = posted_at
                    
                    age_days = (datetime.now(timezone.utc) - post_date).days
                    recency_score = max(0, 0.2 * (1 - age_days / 30))  # Decay over 30 days
                    graph_score += recency_score
                except:
                    pass
            
            # Combined score
            combined_score = (1 - graph_weight) * vector_score + graph_weight * graph_score
            
            # Add to result
            result['vector_score'] = vector_score
            result['graph_score'] = graph_score
            result['combined_score'] = combined_score
            
            ranked.append(result)
        
        # Sort by combined score
        ranked.sort(key=lambda x: x['combined_score'], reverse=True)
        
        return ranked


# Singleton instance
enhanced_search_service = EnhancedSearchService()

