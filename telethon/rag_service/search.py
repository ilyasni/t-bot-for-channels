"""
Сервис гибридного поиска по постам

Поддерживает:
- Векторный поиск по embeddings
- Фильтры: channel_id, tags, date range
- Re-ranking результатов
"""
import logging
import sys
import os
from typing import List, Optional, Dict, Any
from datetime import datetime

# Добавляем родительскую директорию в path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import SessionLocal
from models import Post, Channel
from vector_db import qdrant_client
from embeddings import embeddings_service
import config

# Observability
try:
    from observability.langfuse_client import langfuse_client
    from observability.metrics import rag_search_duration_seconds, rag_query_errors_total
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("⚠️ Observability modules not available")
    langfuse_client = None
    rag_search_duration_seconds = None
    rag_query_errors_total = None

logger = logging.getLogger(__name__)


class SearchService:
    """Сервис для гибридного поиска по постам"""
    
    def __init__(self):
        """Инициализация сервиса поиска"""
        self.qdrant = qdrant_client
        self.embeddings = embeddings_service
        logger.info("✅ Search Service инициализирован")
    
    async def search(
        self,
        query: str,
        user_id: int,
        limit: int = 10,
        channel_id: Optional[int] = None,
        tags: Optional[List[str]] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        min_score: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Гибридный поиск по постам
        
        Args:
            query: Поисковый запрос
            user_id: ID пользователя
            limit: Количество результатов
            channel_id: Фильтр по каналу
            tags: Фильтр по тегам
            date_from: Фильтр по дате (от)
            date_to: Фильтр по дате (до)
            min_score: Минимальный score релевантности
            
        Returns:
            Список найденных постов с метаданными
        """
        try:
            # Генерируем embedding для запроса
            result = await self.embeddings.generate_embedding(query)
            if not result:
                logger.error("❌ Не удалось сгенерировать embedding для запроса")
                if rag_query_errors_total:
                    rag_query_errors_total.labels(error_type='embedding_failed').inc()
                return []
            
            query_vector, provider = result
            logger.info(f"🔍 Поиск для user {user_id}: '{query}' (embedding: {provider})")
            
            # Применяем min_score по умолчанию из конфига, если не указан
            if min_score is None:
                min_score = config.RAG_MIN_SCORE
            
            # Prometheus metrics: measure Qdrant search latency
            if rag_search_duration_seconds:
                timer = rag_search_duration_seconds.time()
                timer.__enter__()
            else:
                timer = None
            
            # Langfuse tracing
            trace_ctx = langfuse_client.trace_context(
                "rag_vector_search",
                metadata={
                    "user_id": user_id,
                    "query_length": len(query),
                    "limit": limit,
                    "provider": provider
                }
            ) if langfuse_client else None
            
            trace = None
            if trace_ctx:
                trace = trace_ctx.__enter__()
            
            try:
                # Выполняем векторный поиск в Qdrant
                search_results = await self.qdrant.search(
                    user_id=user_id,
                    query_vector=query_vector,
                    limit=limit,
                    score_threshold=min_score,
                    channel_id=channel_id,
                    tags=tags,
                    date_from=date_from,
                    date_to=date_to
                )
                
                # Update trace with results
                if trace:
                    trace.update(metadata={"results_count": len(search_results) if search_results else 0})
                
            finally:
                if timer:
                    timer.__exit__(None, None, None)
                if trace_ctx:
                    trace_ctx.__exit__(None, None, None)
            
            if not search_results:
                logger.info(f"📭 Поиск не нашел результатов для user {user_id}")
                return []
            
            # Обогащаем результаты данными из БД
            enriched_results = await self._enrich_search_results(search_results)
            
            # Применяем date фильтр после обогащения (т.к. Qdrant хранит posted_at как keyword)
            if date_from or date_to:
                from datetime import timezone as dt_timezone
                
                filtered_results = []
                for r in enriched_results:
                    posted_at = r['posted_at']
                    
                    # Делаем обе даты timezone-aware
                    if posted_at and posted_at.tzinfo is None:
                        posted_at = posted_at.replace(tzinfo=dt_timezone.utc)
                    
                    df = date_from.replace(tzinfo=dt_timezone.utc) if date_from and date_from.tzinfo is None else date_from
                    dt = date_to.replace(tzinfo=dt_timezone.utc) if date_to and date_to.tzinfo is None else date_to
                    
                    # Проверяем диапазон
                    if (not df or posted_at >= df) and (not dt or posted_at <= dt):
                        filtered_results.append(r)
                
                enriched_results = filtered_results
            
            logger.info(f"✅ Найдено {len(enriched_results)} результатов для user {user_id}")
            return enriched_results
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска: {e}")
            raise
    
    async def _enrich_search_results(
        self,
        search_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Обогатить результаты поиска данными из БД
        
        Args:
            search_results: Результаты из Qdrant
            
        Returns:
            Обогащенные результаты
        """
        db = SessionLocal()
        try:
            enriched = []
            
            for result in search_results:
                payload = result["payload"]
                
                # Извлекаем post_id из payload
                post_id = payload.get("post_id")
                if not post_id:
                    continue
                
                # Получаем пост из БД для актуальных данных
                post = db.query(Post).filter(Post.id == post_id).first()
                if not post:
                    continue
                
                # Формируем обогащенный результат
                enriched_result = {
                    "post_id": post.id,
                    "score": result["score"],
                    "text": payload.get("text", post.text),
                    "channel_id": post.channel_id,
                    "channel_username": post.channel.channel_username,
                    "posted_at": post.posted_at,
                    "url": post.url,
                    "tags": post.tags,
                    "views": post.views,
                    "chunk_info": {
                        "chunk_index": payload.get("chunk_index", 0),
                        "total_chunks": payload.get("total_chunks", 1),
                        "is_chunked": payload.get("total_chunks", 1) > 1
                    }
                }
                
                enriched.append(enriched_result)
            
            return enriched
            
        except Exception as e:
            logger.error(f"❌ Ошибка обогащения результатов: {e}")
            return []
        finally:
            db.close()
    
    async def search_similar_posts(
        self,
        post_id: int,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Найти похожие посты
        
        Args:
            post_id: ID поста для поиска похожих
            limit: Количество результатов
            
        Returns:
            Список похожих постов
        """
        db = SessionLocal()
        try:
            # Получаем пост
            post = db.query(Post).filter(Post.id == post_id).first()
            if not post or not post.text:
                logger.warning(f"⚠️ Пост {post_id} не найден или не содержит текста")
                return []
            
            # Используем текст поста как запрос
            return await self.search(
                query=post.text,
                user_id=post.user_id,
                limit=limit + 1  # +1 чтобы исключить сам пост
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска похожих постов: {e}")
            return []
        finally:
            db.close()
    
    async def get_popular_tags(
        self,
        user_id: int,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Получить популярные теги пользователя
        
        Args:
            user_id: ID пользователя
            limit: Количество тегов
            
        Returns:
            Список тегов с количеством постов
        """
        db = SessionLocal()
        try:
            # Получаем все посты пользователя с тегами
            posts = db.query(Post).filter(
                Post.user_id == user_id,
                Post.tags != None
            ).all()
            
            # Подсчитываем теги
            tag_counts = {}
            for post in posts:
                if post.tags:
                    for tag in post.tags:
                        tag = tag.lower().strip()
                        if tag:
                            tag_counts[tag] = tag_counts.get(tag, 0) + 1
            
            # Сортируем по популярности
            sorted_tags = sorted(
                tag_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:limit]
            
            return [
                {"tag": tag, "count": count}
                for tag, count in sorted_tags
            ]
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения популярных тегов: {e}")
            return []
        finally:
            db.close()
    
    async def get_channel_stats(
        self,
        user_id: int
    ) -> List[Dict[str, Any]]:
        """
        Получить статистику по каналам пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Статистика по каналам
        """
        db = SessionLocal()
        try:
            from sqlalchemy import func
            
            # Группируем посты по каналам
            stats = db.query(
                Post.channel_id,
                Channel.channel_username,
                Channel.channel_title,
                func.count(Post.id).label('posts_count'),
                func.max(Post.posted_at).label('last_post_at')
            ).join(
                Channel, Post.channel_id == Channel.id
            ).filter(
                Post.user_id == user_id
            ).group_by(
                Post.channel_id,
                Channel.channel_username,
                Channel.channel_title
            ).order_by(
                func.count(Post.id).desc()
            ).all()
            
            return [
                {
                    "channel_id": stat.channel_id,
                    "channel_username": stat.channel_username,
                    "channel_title": stat.channel_title,
                    "posts_count": stat.posts_count,
                    "last_post_at": stat.last_post_at
                }
                for stat in stats
            ]
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики каналов: {e}")
            return []
        finally:
            db.close()


# Глобальный экземпляр сервиса
search_service = SearchService()

