"""
Тесты для моделей базы данных
Проверка бизнес-логики, relationships, timezone handling
"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.exc import IntegrityError

from models import User, Channel, Post, Group, InviteCode, SubscriptionHistory
from models import user_channel, user_group
from tests.utils.factories import UserFactory, ChannelFactory, PostFactory, GroupFactory, InviteCodeFactory


# ============================================================================
# User Model Tests
# ============================================================================

@pytest.mark.unit
class TestUserModel:
    """Тесты для модели User"""
    
    def test_user_creation_with_timezone(self, db):
        """Проверка что created_at имеет timezone UTC"""
        user = UserFactory.create(db, telegram_id=111111)
        
        assert user.created_at is not None
        assert user.created_at.tzinfo is not None
        assert user.created_at.tzinfo == timezone.utc
    
    def test_user_subscription_active(self, db):
        """Проверка логики check_subscription_active()"""
        # Активная подписка
        user_active = UserFactory.create(
            db,
            telegram_id=222222,
            subscription_type="premium",
            subscription_expires=datetime.now(timezone.utc) + timedelta(days=10)
        )
        assert user_active.check_subscription_active() is True
        
        # Истекшая подписка
        user_expired = UserFactory.create(
            db,
            telegram_id=333333,
            subscription_type="premium",
            subscription_expires=datetime.now(timezone.utc) - timedelta(days=1)
        )
        assert user_expired.check_subscription_active() is False
        
        # Подписка без срока (free, enterprise)
        user_unlimited = UserFactory.create(
            db,
            telegram_id=444444,
            subscription_type="free",
            subscription_expires=None
        )
        assert user_unlimited.check_subscription_active() is True
    
    def test_user_can_add_channel(self, db):
        """Проверка лимитов каналов по подписке"""
        user = UserFactory.create(
            db,
            telegram_id=555555,
            max_channels=3
        )
        
        # Создаем 3 канала
        for i in range(3):
            channel = ChannelFactory.create(db, channel_username=f"channel_{i}")
            channel.add_user(db, user, is_active=True)
        
        # Достигнут лимит
        assert user.can_add_channel() is False
        
        # Увеличиваем лимит
        user.max_channels = 5
        db.commit()
        
        assert user.can_add_channel() is True
    
    def test_user_can_add_group(self, db):
        """Проверка лимитов групп по подписке"""
        from subscription_config import SUBSCRIPTION_TIERS
        
        user = UserFactory.create(
            db,
            telegram_id=666666,
            subscription_type="premium"
        )
        
        max_groups = SUBSCRIPTION_TIERS["premium"]["max_groups"]
        
        # Создаем группы до лимита
        for i in range(max_groups):
            group = GroupFactory.create(db, group_id=-(i + 1000000))
            group.add_user(db, user)
        
        # Достигнут лимит
        assert user.can_add_group() is False
    
    def test_user_encrypted_fields(self, db):
        """Проверка шифрования api_hash и phone_number"""
        user = UserFactory.create(db, telegram_id=777777)
        
        # Устанавливаем зашифрованные данные
        test_api_hash = "test_api_hash_secret_123"
        test_phone = "+79991234567"
        
        user.set_encrypted_api_hash(test_api_hash)
        user.set_encrypted_phone_number(test_phone)
        db.commit()
        
        # Проверяем что в БД хранятся зашифрованные данные (не plaintext)
        assert user.api_hash != test_api_hash
        assert user.phone_number != test_phone
        
        # Проверяем расшифровку
        assert user.get_decrypted_api_hash() == test_api_hash
        assert user.get_decrypted_phone_number() == test_phone
        
        # Проверяем маскированный вывод
        masked_phone = user.get_masked_phone_number()
        assert masked_phone.startswith("+7")
        assert "***" in masked_phone
    
    def test_user_voice_queries_reset(self, db):
        """Проверка счетчика голосовых запросов"""
        user = UserFactory.create(
            db,
            telegram_id=888888,
            subscription_type="premium"
        )
        
        # Устанавливаем счетчик и reset time
        user.voice_queries_today = 10
        user.voice_queries_reset_at = datetime.now(timezone.utc) + timedelta(days=1)
        db.commit()
        
        assert user.voice_queries_today == 10
        assert user.voice_queries_reset_at.tzinfo == timezone.utc
    
    def test_user_is_admin(self, db):
        """Проверка метода is_admin()"""
        admin = UserFactory.create_admin(db, telegram_id=999999)
        regular_user = UserFactory.create(db, telegram_id=111000)
        
        assert admin.is_admin() is True
        assert regular_user.is_admin() is False
    
    def test_user_unique_telegram_id(self, db):
        """Проверка уникальности telegram_id"""
        UserFactory.create(db, telegram_id=123000)
        
        # Попытка создать пользователя с тем же telegram_id
        with pytest.raises(IntegrityError):
            UserFactory.create(db, telegram_id=123000)
            db.commit()


# ============================================================================
# Channel Model Tests
# ============================================================================

@pytest.mark.unit
class TestChannelModel:
    """Тесты для модели Channel"""
    
    def test_channel_get_or_create_new(self, db):
        """Проверка создания нового канала"""
        channel = Channel.get_or_create(
            db,
            channel_username="new_channel",
            channel_id=123456,
            channel_title="New Channel"
        )
        
        assert channel.channel_username == "new_channel"
        assert channel.channel_id == 123456
        assert channel.channel_title == "New Channel"
    
    def test_channel_get_or_create_existing(self, db):
        """Проверка получения существующего канала"""
        # Создаем канал
        existing = ChannelFactory.create(
            db,
            channel_username="existing_channel",
            channel_id=999999
        )
        
        # Пытаемся создать снова
        channel = Channel.get_or_create(
            db,
            channel_username="existing_channel",
            channel_id=999999
        )
        
        # Должен вернуть существующий
        assert channel.id == existing.id
    
    def test_channel_many_to_many_relationship(self, db):
        """Проверка many-to-many связи с пользователями"""
        channel = ChannelFactory.create(db, channel_username="shared_channel")
        user1 = UserFactory.create(db, telegram_id=100001)
        user2 = UserFactory.create(db, telegram_id=100002)
        
        # Добавляем пользователей к каналу
        channel.add_user(db, user1, is_active=True)
        channel.add_user(db, user2, is_active=True)
        
        # Проверяем что оба пользователя подписаны
        assert len(channel.users) == 2
        assert user1 in channel.users
        assert user2 in channel.users
    
    def test_channel_add_remove_user(self, db):
        """Проверка подписки/отписки пользователя"""
        channel = ChannelFactory.create(db, channel_username="test_sub")
        user = UserFactory.create(db, telegram_id=200001)
        
        # Подписка
        channel.add_user(db, user, is_active=True)
        assert user in channel.users
        
        # Проверяем информацию о подписке
        sub_info = channel.get_user_subscription(db, user)
        assert sub_info is not None
        assert sub_info['is_active'] is True
        
        # Отписка
        channel.remove_user(db, user)
        assert user not in channel.users
    
    def test_channel_unique_username(self, db):
        """Проверка уникальности channel_username"""
        ChannelFactory.create(db, channel_username="unique_channel")
        
        # Попытка создать канал с тем же username
        with pytest.raises(IntegrityError):
            ChannelFactory.create(db, channel_username="unique_channel")
            db.commit()
    
    def test_channel_update_user_subscription(self, db):
        """Проверка обновления параметров подписки"""
        channel = ChannelFactory.create(db, channel_username="update_test")
        user = UserFactory.create(db, telegram_id=300001)
        
        # Добавляем пользователя
        channel.add_user(db, user, is_active=True)
        
        # Обновляем подписку
        now = datetime.now(timezone.utc)
        channel.update_user_subscription(
            db,
            user,
            is_active=False,
            last_parsed_at=now
        )
        
        # Проверяем обновление
        sub_info = channel.get_user_subscription(db, user)
        assert sub_info['is_active'] is False
        assert sub_info['last_parsed_at'] == now


# ============================================================================
# Post Model Tests
# ============================================================================

@pytest.mark.unit
class TestPostModel:
    """Тесты для модели Post"""
    
    def test_post_user_filtering(self, db):
        """Проверка изоляции постов по user_id (критично!)"""
        user1 = UserFactory.create(db, telegram_id=400001)
        user2 = UserFactory.create(db, telegram_id=400002)
        channel = ChannelFactory.create(db, channel_username="shared")
        
        # Создаем посты для обоих пользователей
        post1 = PostFactory.create(db, user_id=user1.id, channel_id=channel.id)
        post2 = PostFactory.create(db, user_id=user2.id, channel_id=channel.id)
        
        # Проверяем изоляцию
        user1_posts = db.query(Post).filter(Post.user_id == user1.id).all()
        user2_posts = db.query(Post).filter(Post.user_id == user2.id).all()
        
        assert len(user1_posts) == 1
        assert len(user2_posts) == 1
        assert post1 in user1_posts
        assert post2 in user2_posts
        assert post1 not in user2_posts
        assert post2 not in user1_posts
    
    def test_post_tagging_status(self, db):
        """Проверка статусов тегирования"""
        user = UserFactory.create(db, telegram_id=500001)
        channel = ChannelFactory.create(db)
        
        # Pending
        post_pending = PostFactory.create(
            db,
            user_id=user.id,
            channel_id=channel.id,
            tagging_status="pending",
            tagging_attempts=0
        )
        assert post_pending.tagging_status == "pending"
        
        # Success
        post_success = PostFactory.create(
            db,
            user_id=user.id,
            channel_id=channel.id,
            tagging_status="success",
            tags=["AI", "технологии"]
        )
        assert post_success.tagging_status == "success"
        assert len(post_success.tags) == 2
        
        # Failed
        post_failed = PostFactory.create(
            db,
            user_id=user.id,
            channel_id=channel.id,
            tagging_status="failed",
            tagging_attempts=3,
            tagging_error="Rate limit exceeded"
        )
        assert post_failed.tagging_status == "failed"
        assert post_failed.tagging_attempts == 3
    
    def test_post_timezone_aware_dates(self, db):
        """Проверка timezone-aware datetime полей"""
        user = UserFactory.create(db, telegram_id=600001)
        channel = ChannelFactory.create(db)
        
        posted_time = datetime.now(timezone.utc) - timedelta(hours=5)
        post = PostFactory.create(
            db,
            user_id=user.id,
            channel_id=channel.id,
            posted_at=posted_time
        )
        
        # Проверяем posted_at
        assert post.posted_at.tzinfo == timezone.utc
        
        # Проверяем parsed_at
        assert post.parsed_at.tzinfo == timezone.utc
    
    def test_post_enriched_content(self, db):
        """Проверка enriched_content поля для Crawl4AI"""
        user = UserFactory.create(db, telegram_id=700001)
        channel = ChannelFactory.create(db)
        
        post = PostFactory.create(
            db,
            user_id=user.id,
            channel_id=channel.id,
            text="Original text https://example.com",
            enriched_content="Original text. Scraped content from example.com"
        )
        
        assert post.enriched_content is not None
        assert "Scraped content" in post.enriched_content


# ============================================================================
# Group Model Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.groups
class TestGroupModel:
    """Тесты для модели Group"""
    
    def test_group_get_or_create(self, db):
        """Проверка get_or_create для групп"""
        group = Group.get_or_create(
            db,
            group_id=-1001234567890,
            group_title="Test Group",
            group_username="test_group"
        )
        
        assert group.group_id == -1001234567890
        assert group.group_title == "Test Group"
        
        # Повторный вызов должен вернуть тот же объект
        group2 = Group.get_or_create(
            db,
            group_id=-1001234567890,
            group_title="Updated Title"  # Не должен обновиться
        )
        
        assert group2.id == group.id
        assert group2.group_title == "Test Group"  # Оригинальное название
    
    def test_group_add_user(self, db):
        """Проверка добавления пользователя к группе"""
        group = GroupFactory.create(db)
        user = UserFactory.create(db, telegram_id=800001)
        
        # Добавляем пользователя
        group.add_user(db, user, is_active=True, mentions_enabled=True)
        
        assert user in group.users
        
        # Проверяем параметры подписки через user_group таблицу
        subscription = db.execute(
            user_group.select().where(
                (user_group.c.user_id == user.id) &
                (user_group.c.group_id == group.id)
            )
        ).fetchone()
        
        assert subscription is not None
        assert subscription.is_active is True
        assert subscription.mentions_enabled is True
    
    def test_group_remove_user(self, db):
        """Проверка удаления пользователя из группы"""
        group = GroupFactory.create(db)
        user = UserFactory.create(db, telegram_id=900001)
        
        group.add_user(db, user)
        assert user in group.users
        
        group.remove_user(db, user)
        assert user not in group.users


# ============================================================================
# InviteCode Model Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.auth
class TestInviteCodeModel:
    """Тесты для модели InviteCode"""
    
    def test_invite_code_generation(self, db):
        """Проверка генерации уникальных кодов"""
        codes = set()
        for _ in range(10):
            code = InviteCode.generate_code()
            codes.add(code)
        
        # Все коды уникальны
        assert len(codes) == 10
        
        # Формат: 12 символов, uppercase
        for code in codes:
            assert len(code) == 12
            assert code.isupper()
            assert code.isalnum()
    
    def test_invite_code_validation_valid(self, db):
        """Проверка валидного инвайт кода"""
        invite = InviteCodeFactory.create(
            db,
            subscription_type="premium",
            expires_days=7
        )
        
        assert invite.is_valid() is True
    
    def test_invite_code_validation_expired(self, db):
        """Проверка истекшего инвайт кода"""
        invite = InviteCodeFactory.create_expired(db)
        
        assert invite.is_valid() is False
    
    def test_invite_code_validation_used(self, db):
        """Проверка использованного инвайт кода"""
        user = UserFactory.create(db, telegram_id=1000001)
        invite = InviteCodeFactory.create_used(
            db,
            used_by=user.id
        )
        
        assert invite.is_valid() is False
        assert invite.uses_count == 1
        assert invite.used_by == user.id
    
    def test_invite_code_usage(self, db):
        """Проверка использования инвайт кода"""
        user = UserFactory.create(db, telegram_id=1100001)
        invite = InviteCodeFactory.create(db)
        
        # Используем код
        result = invite.use(user.id)
        db.commit()
        
        assert result is True
        assert invite.uses_count == 1
        assert invite.used_by == user.id
        assert invite.used_at is not None
        
        # Повторное использование должно вернуть False
        result2 = invite.use(user.id)
        assert result2 is False
    
    def test_invite_code_max_uses(self, db):
        """Проверка max_uses ограничения"""
        invite = InviteCodeFactory.create(
            db,
            max_uses=3
        )
        
        # Используем 3 раза разными пользователями
        for i in range(3):
            user = UserFactory.create(db, telegram_id=1200000 + i)
            result = invite.use(user.id)
            db.commit()
            db.refresh(invite)
            
            if i < 2:
                assert result is True
        
        # 4-я попытка должна вернуть False
        user4 = UserFactory.create(db, telegram_id=1200099)
        result4 = invite.use(user4.id)
        assert result4 is False


# ============================================================================
# User-Channel Relationship Tests
# ============================================================================

@pytest.mark.unit
class TestUserChannelRelationship:
    """Тесты для many-to-many связи User-Channel"""
    
    def test_user_get_active_channels(self, db):
        """Проверка получения только активных каналов"""
        user = UserFactory.create(db, telegram_id=1300001)
        
        # Создаем 3 канала
        active_channel = ChannelFactory.create(db, channel_username="active")
        inactive_channel = ChannelFactory.create(db, channel_username="inactive")
        
        # Добавляем каналы
        active_channel.add_user(db, user, is_active=True)
        inactive_channel.add_user(db, user, is_active=False)
        
        # Получаем только активные
        active_channels = user.get_active_channels(db)
        
        assert len(active_channels) == 1
        assert active_channels[0].channel_username == "active"
    
    def test_user_get_all_channels(self, db):
        """Проверка получения всех каналов с информацией о подписке"""
        user = UserFactory.create(db, telegram_id=1400001)
        
        channel1 = ChannelFactory.create(db, channel_username="channel1")
        channel2 = ChannelFactory.create(db, channel_username="channel2")
        
        channel1.add_user(db, user, is_active=True)
        channel2.add_user(db, user, is_active=False)
        
        # Получаем все каналы
        all_channels = user.get_all_channels(db)
        
        assert len(all_channels) == 2
        
        # Проверяем структуру (channel, subscription_info)
        for channel, sub_info in all_channels:
            assert 'is_active' in sub_info
            assert 'subscription_created_at' in sub_info
    
    def test_cascade_delete_user_removes_subscriptions(self, db):
        """Проверка каскадного удаления при удалении пользователя"""
        user = UserFactory.create(db, telegram_id=1500001)
        channel = ChannelFactory.create(db, channel_username="cascade_test")
        
        channel.add_user(db, user)
        
        # Проверяем что подписка существует
        sub_count_before = db.query(user_channel).filter(
            user_channel.c.user_id == user.id
        ).count()
        assert sub_count_before == 1
        
        # Удаляем пользователя
        db.delete(user)
        db.commit()
        
        # Подписка должна быть удалена (CASCADE)
        sub_count_after = db.query(user_channel).filter(
            user_channel.c.user_id == user.id
        ).count()
        assert sub_count_after == 0


# ============================================================================
# SubscriptionHistory Tests
# ============================================================================

@pytest.mark.unit
class TestSubscriptionHistory:
    """Тесты для модели SubscriptionHistory"""
    
    def test_subscription_history_creation(self, db):
        """Проверка создания записи истории"""
        user = UserFactory.create(db, telegram_id=1600001)
        admin = UserFactory.create_admin(db, telegram_id=1600002)
        
        history = SubscriptionHistory(
            user_id=user.id,
            action="upgraded",
            old_type="free",
            new_type="premium",
            changed_by=admin.id,
            changed_at=datetime.now(timezone.utc),
            notes="Manual upgrade by admin"
        )
        
        db.add(history)
        db.commit()
        db.refresh(history)
        
        assert history.user_id == user.id
        assert history.action == "upgraded"
        assert history.changed_by == admin.id
        assert history.changed_at.tzinfo == timezone.utc
    
    def test_subscription_history_timeline(self, db):
        """Проверка хронологии изменений подписки"""
        user = UserFactory.create(db, telegram_id=1700001)
        
        # Создаем несколько записей
        changes = [
            ("created", None, "free"),
            ("upgraded", "free", "trial"),
            ("upgraded", "trial", "premium"),
        ]
        
        for action, old_type, new_type in changes:
            history = SubscriptionHistory(
                user_id=user.id,
                action=action,
                old_type=old_type,
                new_type=new_type,
                changed_at=datetime.now(timezone.utc)
            )
            db.add(history)
        
        db.commit()
        
        # Получаем историю в хронологическом порядке
        timeline = db.query(SubscriptionHistory).filter(
            SubscriptionHistory.user_id == user.id
        ).order_by(SubscriptionHistory.changed_at.asc()).all()
        
        assert len(timeline) == 3
        assert timeline[0].new_type == "free"
        assert timeline[-1].new_type == "premium"

