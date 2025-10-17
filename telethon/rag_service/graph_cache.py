"""
Redis Cache Layer для Neo4j Graph Queries

Best practices:
- TTL для всех ключей (избежать memory bloat)
- JSON serialization для complex objects
- Graceful degradation (работает без Redis)
- Prefix-based keys для организации
"""
import logging
import json
import os
from typing import List, Dict, Any, Optional
import redis.asyncio as redis

from graph.neo4j_client import neo4j_client
from rag_service.metrics import record_cache_hit

logger = logging.getLogger(__name__)


class GraphCache:
    """
    Redis cache для Neo4j graph queries
    
    Снижает latency для часто запрашиваемых graph traversals
    
    Cache keys:
        - graph:interests:{user_id} - user interests (TTL: 1h)
        - graph:trending:tags - trending tags (TTL: 6h)
        - graph:post_context:{post_id} - post context (TTL: 24h)
    
    Usage:
        ```python
        cache = GraphCache()
        
        # Cached call
        interests = await cache.get_user_interests(user_id=123)
        ```
    """
    
    def __init__(self):
        """Инициализация Redis client"""
        self.enabled = False
        self.redis_client: Optional[redis.Redis] = None
        
        try:
            redis_host = os.getenv("REDIS_HOST", "redis")
            redis_port = int(os.getenv("REDIS_PORT", "6379"))
            
            # Best practice: Redis без пароля (Valkey default)
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                decode_responses=True,  # Автоматически decode в str
                socket_timeout=5,
                socket_connect_timeout=5
            )
            
            self.enabled = True
            logger.info(f"✅ GraphCache initialized (Redis: {redis_host}:{redis_port})")
            
        except Exception as e:
            logger.warning(f"⚠️ GraphCache disabled (Redis unavailable): {e}")
            self.enabled = False
    
    async def get_user_interests(
        self,
        user_id: int,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Получить user interests с кешированием
        
        Args:
            user_id: Telegram ID пользователя
            limit: Количество топ тегов
        
        Returns:
            User interests (cached или fresh)
        
        TTL: 1 hour
        """
        cache_key = f"graph:interests:{user_id}"
        
        # Try cache first
        if self.enabled and self.redis_client:
            try:
                cached = await self.redis_client.get(cache_key)
                if cached:
                    logger.debug(f"✅ Cache HIT: {cache_key}")
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"⚠️ Cache read error: {e}")
        
        # Fetch from Neo4j
        interests = await neo4j_client.get_user_interests(
            telegram_id=user_id,
            limit=limit
        )
        
        # Store in cache
        if self.enabled and self.redis_client and interests:
            try:
                await self.redis_client.setex(
                    cache_key,
                    3600,  # 1 hour
                    json.dumps(interests)
                )
                logger.debug(f"✅ Cache SET: {cache_key}")
            except Exception as e:
                logger.warning(f"⚠️ Cache write error: {e}")
        
        return interests
    
    async def get_trending_tags(
        self,
        days: int = 7,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Получить trending tags с кешированием
        
        Args:
            days: Период в днях
            limit: Количество топ тегов
        
        Returns:
            Trending tags (cached или fresh)
        
        TTL: 6 hours (обновляется реже)
        """
        cache_key = f"graph:trending:tags:d{days}"
        
        # Try cache first
        if self.enabled and self.redis_client:
            try:
                cached = await self.redis_client.get(cache_key)
                if cached:
                    logger.debug(f"✅ Cache HIT: {cache_key}")
                    record_cache_hit('trending', hit=True)
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"⚠️ Cache read error: {e}")
        
        # Cache miss
        record_cache_hit('trending', hit=False)
        
        # Fetch from Neo4j
        trending = await neo4j_client.get_trending_tags(days=days, limit=limit)
        
        # Store in cache
        if self.enabled and self.redis_client and trending:
            try:
                await self.redis_client.setex(
                    cache_key,
                    21600,  # 6 hours
                    json.dumps(trending)
                )
                logger.debug(f"✅ Cache SET: {cache_key}")
            except Exception as e:
                logger.warning(f"⚠️ Cache write error: {e}")
        
        return trending
    
    async def get_post_context(
        self,
        post_id: int
    ) -> Dict[str, Any]:
        """
        Получить post context с кешированием
        
        Args:
            post_id: ID поста
        
        Returns:
            Post context (cached или fresh)
        
        TTL: 24 hours (граф редко меняется для старых постов)
        """
        cache_key = f"graph:post_context:{post_id}"
        
        # Try cache first
        if self.enabled and self.redis_client:
            try:
                cached = await self.redis_client.get(cache_key)
                if cached:
                    logger.debug(f"✅ Cache HIT: {cache_key}")
                    record_cache_hit('post_context', hit=True)
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"⚠️ Cache read error: {e}")
        
        # Cache miss
        record_cache_hit('post_context', hit=False)
        
        # Fetch from Neo4j
        context = await neo4j_client.get_post_context(post_id=post_id)
        
        # Store in cache
        if self.enabled and self.redis_client and context:
            try:
                await self.redis_client.setex(
                    cache_key,
                    86400,  # 24 hours
                    json.dumps(context)
                )
                logger.debug(f"✅ Cache SET: {cache_key}")
            except Exception as e:
                logger.warning(f"⚠️ Cache write error: {e}")
        
        return context
    
    async def invalidate_user_interests(self, user_id: int):
        """
        Инвалидировать cache для user interests
        
        Вызывать при:
        - Новом посте пользователя
        - Удалении постов
        """
        if self.enabled and self.redis_client:
            try:
                cache_key = f"graph:interests:{user_id}"
                await self.redis_client.delete(cache_key)
                logger.debug(f"✅ Cache INVALIDATED: {cache_key}")
            except Exception as e:
                logger.warning(f"⚠️ Cache invalidation error: {e}")
    
    async def invalidate_trending(self):
        """
        Инвалидировать cache для trending tags
        
        Вызывать при:
        - Batch обновлении постов
        - Cleanup старых данных
        """
        if self.enabled and self.redis_client:
            try:
                # Удалить все trending cache keys
                pattern = "graph:trending:*"
                async for key in self.redis_client.scan_iter(match=pattern):
                    await self.redis_client.delete(key)
                logger.debug(f"✅ Cache INVALIDATED: trending tags")
            except Exception as e:
                logger.warning(f"⚠️ Cache invalidation error: {e}")
    
    async def close(self):
        """Закрыть Redis connection"""
        if self.redis_client:
            try:
                await self.redis_client.close()
                logger.info("✅ GraphCache closed")
            except Exception as e:
                logger.error(f"❌ GraphCache close error: {e}")


# Singleton instance
graph_cache = GraphCache()

