"""
Background cleanup для накопленных постов

Best practice: Context7 FastAPI background tasks + batch processing
Обрабатывает посты в статусе pending/failed и посты без индексации
"""
import logging
import sys
import os
import asyncio
from datetime import datetime, timedelta, timezone
from typing import List

# Добавляем родительскую директорию в path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import SessionLocal
from models import Post, IndexingStatus
from indexer import indexer_service

logger = logging.getLogger(__name__)


class CleanupService:
    """Сервис для обработки накопленных постов"""
    
    async def process_untagged_posts(self, limit: int = 50):
        """
        Обработать посты без тегов
        
        Args:
            limit: Максимальное количество постов для обработки
        """
        db = SessionLocal()
        try:
            # Посты старше 1 часа в статусе pending/failed
            cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
            
            posts = db.query(Post).filter(
                Post.tagging_status.in_(['pending', 'failed']),
                Post.parsed_at < cutoff,
                Post.text.isnot(None)
            ).limit(limit).all()
            
            if not posts:
                logger.info("✅ Нет постов для тегирования")
                return
            
            logger.info(f"🏷️ Запуск тегирования {len(posts)} накопленных постов")
            
            # Вызываем тегирование через HTTP API (архитектурно правильнее)
            # Избегаем проблем с cross-service импортами
            import httpx
            post_ids = [p.id for p in posts]
            
            telethon_api_url = os.getenv("TELETHON_API_URL", "http://telethon:8010")
            
            # Sequential обработка с rate limiting
            async with httpx.AsyncClient(timeout=300.0) as client:
                for post_id in post_ids:
                    try:
                        response = await client.post(
                            f"{telethon_api_url}/posts/{post_id}/generate_tags"
                        )
                        
                        if response.status_code == 200:
                            logger.debug(f"✅ Post {post_id} тегирован")
                        else:
                            logger.warning(f"⚠️ Post {post_id}: {response.status_code}")
                        
                        # Задержка с учетом rate limit
                        await asyncio.sleep(1.5)
                        
                    except Exception as e:
                        logger.error(f"❌ Ошибка тегирования post {post_id}: {e}")
            
            logger.info(f"✅ Тегирование {len(post_ids)} постов завершено")
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки не тегированных постов: {e}")
        finally:
            db.close()
    
    async def process_unindexed_posts(self, limit: int = 50):
        """
        Обработать посты без индексации в Qdrant
        
        Args:
            limit: Максимальное количество постов для обработки
        """
        db = SessionLocal()
        try:
            # Посты с тегами но без индексации
            # Используем LEFT JOIN для поиска постов без записи в indexing_status
            unindexed = db.query(Post).filter(
                Post.tags.isnot(None),
                ~Post.id.in_(
                    db.query(IndexingStatus.post_id)
                )
            ).limit(limit).all()
            
            if not unindexed:
                logger.info("✅ Нет постов для индексации")
                return
            
            logger.info(f"📊 Запуск индексации {len(unindexed)} накопленных постов")
            
            post_ids = [p.id for p in unindexed]
            
            # Batch индексация
            await indexer_service.index_posts_batch(post_ids)
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки не проиндексированных постов: {e}")
        finally:
            db.close()
    
    async def get_backlog_stats(self) -> dict:
        """
        Получить статистику накопленных постов
        
        Returns:
            Словарь со статистикой
        """
        db = SessionLocal()
        try:
            # Посты без тегов
            untagged_count = db.query(Post).filter(
                Post.tagging_status.in_(['pending', 'failed']),
                Post.text.isnot(None)
            ).count()
            
            # Посты без индексации
            unindexed_count = db.query(Post).filter(
                Post.tags.isnot(None),
                ~Post.id.in_(
                    db.query(IndexingStatus.post_id)
                )
            ).count()
            
            # Посты с ошибками тегирования
            failed_tagging = db.query(Post).filter(
                Post.tagging_status == 'failed'
            ).count()
            
            # Посты с ошибками индексации
            failed_indexing = db.query(IndexingStatus).filter(
                IndexingStatus.status == 'failed'
            ).count()
            
            return {
                "untagged_posts": untagged_count,
                "unindexed_posts": unindexed_count,
                "failed_tagging": failed_tagging,
                "failed_indexing": failed_indexing,
                "total_backlog": untagged_count + unindexed_count
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики: {e}")
            return {}
        finally:
            db.close()


# Глобальный экземпляр сервиса
cleanup_service = CleanupService()

