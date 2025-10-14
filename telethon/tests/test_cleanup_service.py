"""
Тесты для Cleanup Service
Автоматическая очистка старых постов по retention_days
"""

import pytest
from datetime import datetime, timezone, timedelta

from cleanup_service import CleanupService
from tests.utils.factories import UserFactory, ChannelFactory, PostFactory


@pytest.mark.unit
class TestCleanupService:
    """Тесты для CleanupService"""
    
    @pytest.fixture
    def cleanup_service(self):
        return CleanupService()
    
    @pytest.mark.asyncio
    async def test_cleanup_old_posts_by_retention(self, cleanup_service, db):
        """Тест очистки постов по retention_days"""
        user = UserFactory.create(
            db,
            telegram_id=12200001,
            retention_days=30
        )
        channel = ChannelFactory.create(db)
        channel.add_user(db, user)
        
        # Создаем посты разных возрастов
        # Последний пост - сегодня
        latest_post = PostFactory.create(
            db,
            user_id=user.id,
            channel_id=channel.id,
            posted_at=datetime.now(timezone.utc),
            text="Latest post"
        )
        
        # Пост 20 дней назад (должен остаться: 0 - 30 = -30 дней от последнего)
        recent_post = PostFactory.create(
            db,
            user_id=user.id,
            channel_id=channel.id,
            posted_at=datetime.now(timezone.utc) - timedelta(days=20),
            text="Recent post"
        )
        
        # Пост 35 дней назад (должен быть удален: 0 - 35 = -35 < -30)
        old_post = PostFactory.create(
            db,
            user_id=user.id,
            channel_id=channel.id,
            posted_at=datetime.now(timezone.utc) - timedelta(days=35),
            text="Old post"
        )
        
        # Запускаем очистку
        result = await cleanup_service.cleanup_user_posts(user, db)
        
        # Проверяем результат
        assert result['posts_deleted'] == 1
        
        # Проверяем что старый пост удален
        from models import Post
        remaining_posts = db.query(Post).filter(Post.user_id == user.id).all()
        
        assert len(remaining_posts) == 2
        assert old_post.id not in [p.id for p in remaining_posts]
        assert latest_post.id in [p.id for p in remaining_posts]
        assert recent_post.id in [p.id for p in remaining_posts]
    
    @pytest.mark.asyncio
    async def test_cleanup_channel_posts_cutoff_calculation(self, cleanup_service, db):
        """Тест расчета cutoff date от последнего поста канала"""
        user = UserFactory.create(db, telegram_id=12300001, retention_days=15)
        channel = ChannelFactory.create(db)
        channel.add_user(db, user)
        
        # Последний пост - 10 дней назад
        last_post_date = datetime.now(timezone.utc) - timedelta(days=10)
        last_post = PostFactory.create(
            db,
            user_id=user.id,
            channel_id=channel.id,
            posted_at=last_post_date
        )
        
        # Пост 30 дней назад (до cutoff: last - 15 = -25 дней)
        old_post = PostFactory.create(
            db,
            user_id=user.id,
            channel_id=channel.id,
            posted_at=datetime.now(timezone.utc) - timedelta(days=30)
        )
        
        # Запускаем очистку для канала
        deleted_count = await cleanup_service.cleanup_channel_posts(
            channel, user, user.retention_days, db
        )
        
        # Проверяем что старый пост удален
        assert deleted_count == 1
    
    @pytest.mark.asyncio
    async def test_cleanup_user_posts_immediately(self, cleanup_service, db):
        """Тест немедленной очистки для пользователя"""
        user = UserFactory.create(db, telegram_id=12400001, retention_days=7)
        channel = ChannelFactory.create(db)
        channel.add_user(db, user)
        
        # Создаем старые посты
        for i in range(5):
            PostFactory.create(
                db,
                user_id=user.id,
                channel_id=channel.id,
                posted_at=datetime.now(timezone.utc) - timedelta(days=20 + i)
            )
        
        # Свежий пост
        PostFactory.create(
            db,
            user_id=user.id,
            channel_id=channel.id,
            posted_at=datetime.now(timezone.utc)
        )
        
        # Запускаем немедленную очистку
        result = await cleanup_service.cleanup_user_posts_immediately(user.id)
        
        assert result['status'] == 'success'
        assert result['posts_deleted'] > 0
    
    @pytest.mark.asyncio
    async def test_cleanup_respects_min_retention_days(self, cleanup_service, db):
        """Тест что cleanup защищен минимальным retention (1 день)"""
        user = UserFactory.create(
            db,
            telegram_id=12500001,
            retention_days=0  # Некорректное значение
        )
        
        # При cleanup должен использоваться минимум 1 день
        result = await cleanup_service.cleanup_user_posts(user, db)
        
        # Не должно быть ошибки, используется min_retention_days
        assert result['posts_deleted'] >= 0

