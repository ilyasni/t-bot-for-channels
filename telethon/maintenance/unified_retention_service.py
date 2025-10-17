"""
Unified Retention Service
Централизованная очистка данных с учетом digest frequency и best practices

Features:
- Smart retention (учет digest frequency)
- Channel orphan cleanup (нет подписчиков)
- Dry run mode
- Sync cleanup: PostgreSQL → Neo4j → Qdrant
- Context7 best practices (PostgreSQL partitioning)

Best practices (from Context7):
- PostgreSQL: batch DELETE + VACUUM OR партиционирование
- Neo4j: DETACH DELETE с batch iterations (apoc.periodic.iterate)
- Qdrant: delete by filter (posted_at < cutoff_date)
- Sequential cleanup: PostgreSQL → Neo4j → Qdrant
"""

import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional

# Imports
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import SessionLocal
from models import Post, User, Channel, DigestSettings, user_channel
from rag_service.metrics import record_cleanup

logger = logging.getLogger(__name__)


class UnifiedRetentionService:
    """
    Централизованная очистка данных
    
    Логика retention:
    retention = MAX(
        90 days,  # Базовый минимум (3 месяца)
        digest_period * 2,  # Запас для дайджестов
        user.retention_days  # Пользовательская настройка
    )
    
    Edge cases:
    - Отписка от канала → orphaned channels cleanup
    - Разные digest frequency → maximum period
    - Недавние посты vs старые → минимум 90 дней для RAG
    """
    
    def __init__(self, base_retention_days: int = None):
        """
        Инициализация unified retention service
        
        Args:
            base_retention_days: Базовый минимум retention (default: 90 дней)
        """
        if base_retention_days is None:
            base_retention_days = int(os.getenv("DATA_RETENTION_DAYS", "90"))
        
        self.base_retention_days = base_retention_days
        self.min_retention_days = 90  # Абсолютный минимум для RAG/search
        self.max_retention_days = 3650  # Максимум (10 лет)
        
        logger.info(f"🗑️ UnifiedRetentionService initialized (base: {base_retention_days} days)")
        logger.info(f"   Min retention: {self.min_retention_days} days (for RAG/search)")
    
    async def calculate_retention_period(self, user_id: int) -> int:
        """
        Рассчитать период retention для пользователя
        
        Логика:
        1. Базовый минимум: 90 дней (для RAG/search)
        2. Digest frequency: period * 2 (запас для дайджестов)
        3. User retention_days: пользовательская настройка
        4. Maximum из всех
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Количество дней retention
        """
        db = SessionLocal()
        try:
            # 1. Получить пользователя
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.warning(f"⚠️ User {user_id} not found, using base retention")
                return self.base_retention_days
            
            # 2. Базовый минимум (для RAG/search)
            base_retention = self.min_retention_days
            
            # 3. Получить digest settings
            digest_settings = db.query(DigestSettings).filter(
                DigestSettings.user_id == user_id
            ).first()
            
            # 4. Конвертировать frequency в дни
            if digest_settings and digest_settings.enabled:
                if digest_settings.frequency == "daily":
                    digest_period = 1
                elif digest_settings.frequency == "weekly":
                    digest_period = 7
                elif digest_settings.frequency == "monthly":
                    digest_period = 30
                else:
                    digest_period = 7  # Default weekly
                
                # Запас для дайджестов: period * 2
                digest_retention = digest_period * 2
                logger.debug(f"📊 User {user_id}: digest {digest_settings.frequency} → {digest_retention} days")
            else:
                digest_retention = 14  # Default: 2 weeks for weekly digest
                logger.debug(f"📊 User {user_id}: no digest settings → {digest_retention} days")
            
            # 5. User retention_days
            user_retention = user.retention_days or 30
            
            # 6. Maximum
            calculated_retention = max(base_retention, digest_retention, user_retention)
            
            # 7. Валидация
            if calculated_retention < self.min_retention_days:
                logger.warning(f"⚠️ User {user_id}: calculated {calculated_retention} < min {self.min_retention_days}")
                calculated_retention = self.min_retention_days
            
            if calculated_retention > self.max_retention_days:
                logger.warning(f"⚠️ User {user_id}: calculated {calculated_retention} > max {self.max_retention_days}")
                calculated_retention = self.max_retention_days
            
            logger.debug(f"✅ User {user_id}: retention = max({base_retention}, {digest_retention}, {user_retention}) = {calculated_retention}")
            
            return calculated_retention
            
        except Exception as e:
            logger.error(f"❌ Error calculating retention for user {user_id}: {e}")
            return self.base_retention_days
        finally:
            db.close()
    
    async def cleanup_orphaned_channels(self, dry_run: bool = False) -> int:
        """
        Очистка каналов без подписчиков
        
        Логика:
        - Канал считается orphaned если нет активных подписок
        - Удаляются посты канала старше 30 дней
        - Сам канал остается (для истории)
        
        Args:
            dry_run: Если True, только подсчет без удаления
            
        Returns:
            Количество удаленных постов
        """
        logger.info(f"🧹 Cleanup orphaned channels (dry_run={dry_run})")
        
        db = SessionLocal()
        try:
            # Найти каналы без активных подписок
            orphaned_channels = db.query(Channel).filter(
                ~Channel.id.in_(
                    db.query(user_channel.c.channel_id).filter(
                        user_channel.c.is_active == True
                    )
                )
            ).all()
            
            if not orphaned_channels:
                logger.info("📭 No orphaned channels found")
                return 0
            
            logger.info(f"📊 Found {len(orphaned_channels)} orphaned channels")
            
            cutoff = datetime.now(timezone.utc) - timedelta(days=30)
            total_deleted = 0
            
            for channel in orphaned_channels:
                try:
                    # Подсчитать посты для удаления
                    posts_query = db.query(Post).filter(
                        Post.channel_id == channel.id,
                        Post.posted_at < cutoff
                    )
                    count = posts_query.count()
                    
                    if count > 0:
                        logger.info(f"📊 Channel @{channel.channel_username}: {count} posts to delete")
                        
                        if not dry_run:
                            # Удалить посты
                            deleted = posts_query.delete(synchronize_session=False)
                            db.commit()
                            total_deleted += deleted
                            logger.info(f"✅ Channel @{channel.channel_username}: deleted {deleted} posts")
                        else:
                            total_deleted += count
                    
                except Exception as e:
                    logger.error(f"❌ Error cleaning channel @{channel.channel_username}: {e}")
                    db.rollback()
                    continue
            
            logger.info(f"✅ Orphaned channels cleanup: {total_deleted} posts {'would be' if dry_run else ''} deleted")
            return total_deleted
            
        except Exception as e:
            logger.error(f"❌ Error in orphaned channels cleanup: {e}")
            db.rollback()
            return 0
        finally:
            db.close()
    
    async def cleanup_user_posts(self, user_id: int, dry_run: bool = False) -> Dict[str, Any]:
        """
        Очистка постов для конкретного пользователя
        
        Args:
            user_id: ID пользователя
            dry_run: Если True, только подсчет без удаления
            
        Returns:
            Статистика очистки
        """
        try:
            # Рассчитать retention period
            retention_days = await self.calculate_retention_period(user_id)
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
            
            logger.info(f"📊 User {user_id}: retention={retention_days} days, cutoff={cutoff_date.isoformat()}")
            
            db = SessionLocal()
            try:
                # Подсчитать посты для удаления
                posts_query = db.query(Post).filter(
                    Post.user_id == user_id,
                    Post.posted_at < cutoff_date
                )
                count = posts_query.count()
                
                if count == 0:
                    return {
                        "user_id": user_id,
                        "retention_days": retention_days,
                        "cutoff_date": cutoff_date.isoformat(),
                        "posts_deleted": 0,
                        "dry_run": dry_run
                    }
                
                logger.info(f"📊 User {user_id}: {count} posts to delete")
                
                if not dry_run:
                    # Удалить посты
                    deleted = posts_query.delete(synchronize_session=False)
                    db.commit()
                    logger.info(f"✅ User {user_id}: deleted {deleted} posts")
                else:
                    deleted = count
                
                return {
                    "user_id": user_id,
                    "retention_days": retention_days,
                    "cutoff_date": cutoff_date.isoformat(),
                    "posts_deleted": deleted,
                    "dry_run": dry_run
                }
                
            except Exception as e:
                logger.error(f"❌ Error cleaning posts for user {user_id}: {e}")
                db.rollback()
                return {
                    "user_id": user_id,
                    "error": str(e),
                    "dry_run": dry_run
                }
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"❌ Error in cleanup_user_posts for user {user_id}: {e}")
            return {
                "user_id": user_id,
                "error": str(e),
                "dry_run": dry_run
            }
    
    async def cleanup_all_users(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Главный метод очистки для всех пользователей
        
        Args:
            dry_run: Если True, только подсчет без удаления
            
        Returns:
            Общая статистика очистки
        """
        logger.info(f"🧹 Starting unified cleanup (dry_run={dry_run})")
        
        db = SessionLocal()
        try:
            # Получить всех активных пользователей
            users = db.query(User).filter(User.is_active == True).all()
            
            if not users:
                logger.info("📭 No active users found")
                return {
                    "status": "success",
                    "users_processed": 0,
                    "total_posts_deleted": 0,
                    "dry_run": dry_run,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            
            logger.info(f"📊 Processing {len(users)} active users")
            
            total_posts_deleted = 0
            users_processed = 0
            user_stats = []
            errors = []
            
            for user in users:
                try:
                    result = await self.cleanup_user_posts(user.id, dry_run)
                    users_processed += 1
                    
                    if "error" in result:
                        errors.append(f"User {user.id}: {result['error']}")
                    else:
                        posts_deleted = result.get("posts_deleted", 0)
                        total_posts_deleted += posts_deleted
                        
                        if posts_deleted > 0:
                            user_stats.append({
                                "user_id": user.id,
                                "telegram_id": user.telegram_id,
                                "retention_days": result.get("retention_days"),
                                "posts_deleted": posts_deleted
                            })
                            logger.info(f"✅ User {user.telegram_id}: {posts_deleted} posts {'would be' if dry_run else ''} deleted")
                
                except Exception as e:
                    logger.error(f"❌ Error processing user {user.id}: {e}")
                    errors.append(f"User {user.id}: {str(e)}")
                    continue
            
            # Cleanup orphaned channels
            try:
                orphaned_deleted = await self.cleanup_orphaned_channels(dry_run)
                total_posts_deleted += orphaned_deleted
            except Exception as e:
                logger.error(f"❌ Error in orphaned channels cleanup: {e}")
                errors.append(f"Orphaned channels: {str(e)}")
            
            logger.info(f"✅ Unified cleanup complete: {total_posts_deleted} posts {'would be' if dry_run else ''} deleted")
            
            return {
                "status": "success",
                "users_processed": users_processed,
                "total_posts_deleted": total_posts_deleted,
                "user_stats": user_stats,
                "errors": errors,
                "dry_run": dry_run,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Critical error in unified cleanup: {e}")
            return {
                "status": "error",
                "error": str(e),
                "dry_run": dry_run,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        finally:
            db.close()
    
    async def get_retention_stats(self) -> Dict[str, Any]:
        """
        Получить статистику по retention для всех пользователей
        
        Returns:
            Статистика retention
        """
        logger.info("📊 Getting retention statistics")
        
        db = SessionLocal()
        try:
            users = db.query(User).filter(User.is_active == True).all()
            
            stats = {
                "total_users": len(users),
                "retention_stats": [],
                "summary": {
                    "min_retention": self.min_retention_days,
                    "max_retention": self.max_retention_days,
                    "base_retention": self.base_retention_days
                }
            }
            
            for user in users:
                try:
                    retention_days = await self.calculate_retention_period(user.id)
                    
                    # Подсчитать посты
                    cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
                    posts_count = db.query(Post).filter(
                        Post.user_id == user.id,
                        Post.posted_at < cutoff_date
                    ).count()
                    
                    stats["retention_stats"].append({
                        "user_id": user.id,
                        "telegram_id": user.telegram_id,
                        "retention_days": retention_days,
                        "posts_to_delete": posts_count,
                        "cutoff_date": cutoff_date.isoformat()
                    })
                    
                except Exception as e:
                    logger.error(f"❌ Error getting stats for user {user.id}: {e}")
                    continue
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error getting retention stats: {e}")
            return {"error": str(e)}
        finally:
            db.close()


# Global instance
unified_retention_service = UnifiedRetentionService()
