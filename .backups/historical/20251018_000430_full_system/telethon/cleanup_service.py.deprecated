"""
Сервис очистки устаревших постов

Этот сервис удаляет посты, которые выходят за пределы периода хранения (retention_days)
для каждого пользователя. Период рассчитывается от даты последнего опубликованного поста
в каждом канале.

Логика:
- Для каждого канала находим последний опубликованный пост
- Удаляем посты старше (last_post_date - retention_days)
- Пример: если последний пост от 2025-10-10 и retention_days=30,
  удаляем посты опубликованные до 2025-09-10
"""

import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import func
from sqlalchemy.orm import Session
from database import SessionLocal
from models import User, Channel, Post

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CleanupService:
    """Сервис для очистки устаревших постов"""
    
    def __init__(self):
        self.min_retention_days = 1  # Минимальный период хранения для защиты
        self.max_retention_days = 3650  # Максимальный период (10 лет)
    
    async def cleanup_old_posts(self) -> dict:
        """
        Удаление устаревших постов для всех пользователей
        
        Returns:
            dict: Статистика очистки
        """
        db = SessionLocal()
        
        try:
            logger.info("🧹 Запуск очистки устаревших постов...")
            
            # Получаем всех активных пользователей
            users = db.query(User).filter(User.is_active == True).all()
            
            if not users:
                logger.info("📭 Нет активных пользователей для очистки")
                return {
                    "status": "success",
                    "users_processed": 0,
                    "total_posts_deleted": 0,
                    "message": "Нет активных пользователей"
                }
            
            total_users_processed = 0
            total_posts_deleted = 0
            user_stats = []
            
            for user in users:
                try:
                    user_result = await self.cleanup_user_posts(user, db)
                    total_users_processed += 1
                    total_posts_deleted += user_result["posts_deleted"]
                    
                    if user_result["posts_deleted"] > 0:
                        user_stats.append({
                            "user_id": user.id,
                            "telegram_id": user.telegram_id,
                            "retention_days": user.retention_days,
                            "posts_deleted": user_result["posts_deleted"],
                            "channels_processed": user_result["channels_processed"]
                        })
                        logger.info(
                            f"✅ Пользователь {user.telegram_id}: удалено {user_result['posts_deleted']} постов "
                            f"из {user_result['channels_processed']} каналов"
                        )
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка очистки для пользователя {user.telegram_id}: {str(e)}")
                    continue
            
            logger.info(
                f"✅ Очистка завершена. Обработано пользователей: {total_users_processed}, "
                f"удалено постов: {total_posts_deleted}"
            )
            
            return {
                "status": "success",
                "users_processed": total_users_processed,
                "total_posts_deleted": total_posts_deleted,
                "user_stats": user_stats,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Критическая ошибка очистки: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        finally:
            db.close()
    
    async def cleanup_user_posts(self, user: User, db: Session) -> dict:
        """
        Удаление устаревших постов для конкретного пользователя
        
        Args:
            user: Объект пользователя
            db: Сессия базы данных
            
        Returns:
            dict: Статистика очистки для пользователя
        """
        try:
            # Проверяем retention_days
            retention_days = user.retention_days or 30
            
            # Валидация периода хранения
            if retention_days < self.min_retention_days:
                logger.warning(
                    f"⚠️  Пользователь {user.telegram_id}: retention_days={retention_days} меньше минимума. "
                    f"Используем {self.min_retention_days}"
                )
                retention_days = self.min_retention_days
            
            if retention_days > self.max_retention_days:
                logger.warning(
                    f"⚠️  Пользователь {user.telegram_id}: retention_days={retention_days} больше максимума. "
                    f"Используем {self.max_retention_days}"
                )
                retention_days = self.max_retention_days
            
            # Получаем все каналы пользователя (включая неактивные)
            channels_with_info = user.get_all_channels(db)
            
            if not channels_with_info:
                return {
                    "posts_deleted": 0,
                    "channels_processed": 0
                }
            
            total_posts_deleted = 0
            channels_processed = 0
            
            for channel, sub_info in channels_with_info:
                try:
                    posts_deleted = await self.cleanup_channel_posts(
                        channel, user, retention_days, db
                    )
                    total_posts_deleted += posts_deleted
                    channels_processed += 1
                    
                    if posts_deleted > 0:
                        logger.debug(
                            f"  📊 Канал @{channel.channel_username}: удалено {posts_deleted} постов"
                        )
                    
                except Exception as e:
                    logger.error(
                        f"❌ Ошибка очистки канала @{channel.channel_username}: {str(e)}"
                    )
                    continue
            
            return {
                "posts_deleted": total_posts_deleted,
                "channels_processed": channels_processed
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка очистки постов пользователя {user.telegram_id}: {str(e)}")
            raise
    
    async def cleanup_channel_posts(
        self, channel: Channel, user, retention_days: int, db: Session
    ) -> int:
        """
        Удаление устаревших постов для конкретного канала и пользователя
        
        Args:
            channel: Объект канала
            user: Объект пользователя
            retention_days: Период хранения в днях
            db: Сессия базы данных
            
        Returns:
            int: Количество удаленных постов
        """
        try:
            # Находим дату последнего опубликованного поста в канале для этого пользователя
            last_post = db.query(func.max(Post.posted_at)).filter(
                Post.channel_id == channel.id,
                Post.user_id == user.id
            ).scalar()
            
            if not last_post:
                # Нет постов в канале для этого пользователя
                return 0
            
            # Убеждаемся, что last_post имеет timezone
            if last_post.tzinfo is None:
                last_post = last_post.replace(tzinfo=timezone.utc)
            
            # Рассчитываем дату отсечения: last_post_date - retention_days
            cutoff_date = last_post - timedelta(days=retention_days)
            
            # Получаем посты старше cutoff_date для этого пользователя
            old_posts = db.query(Post).filter(
                Post.channel_id == channel.id,
                Post.user_id == user.id,
                Post.posted_at < cutoff_date
            ).all()
            
            posts_count = len(old_posts)
            
            if posts_count > 0:
                logger.debug(
                    f"  🗑️  Канал @{channel.channel_username}: "
                    f"последний пост {last_post.isoformat()}, "
                    f"удаляем посты до {cutoff_date.isoformat()}, "
                    f"найдено постов: {posts_count}"
                )
                
                # Удаляем посты
                for post in old_posts:
                    db.delete(post)
                
                db.commit()
            
            return posts_count
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Ошибка удаления постов канала {channel.id}: {str(e)}")
            raise
    
    async def cleanup_user_posts_immediately(self, user_id: int) -> dict:
        """
        Немедленная очистка постов для конкретного пользователя
        Используется при изменении retention_days
        
        Args:
            user_id: ID пользователя
            
        Returns:
            dict: Статистика очистки
        """
        db = SessionLocal()
        
        try:
            user = db.query(User).filter(User.id == user_id).first()
            
            if not user:
                return {
                    "status": "error",
                    "error": "Пользователь не найден"
                }
            
            result = await self.cleanup_user_posts(user, db)
            
            return {
                "status": "success",
                "user_id": user.id,
                "telegram_id": user.telegram_id,
                "retention_days": user.retention_days,
                "posts_deleted": result["posts_deleted"],
                "channels_processed": result["channels_processed"],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка немедленной очистки для пользователя {user_id}: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        finally:
            db.close()


# Глобальный экземпляр сервиса
cleanup_service = CleanupService()


# Функция для запуска очистки (для использования в других модулях)
async def run_cleanup():
    """Запуск очистки устаревших постов"""
    return await cleanup_service.cleanup_old_posts()


if __name__ == "__main__":
    import asyncio
    
    # Тестовый запуск очистки
    async def test_cleanup():
        result = await cleanup_service.cleanup_old_posts()
        print("\n" + "=" * 60)
        print("Результат очистки:")
        print("=" * 60)
        for key, value in result.items():
            print(f"{key}: {value}")
        print("=" * 60)
    
    asyncio.run(test_cleanup())

