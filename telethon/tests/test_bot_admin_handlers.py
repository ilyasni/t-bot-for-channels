"""
Тесты для админских команд бота
/admin, /admin_invite, /admin_users, /admin_grant, /admin_stats
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from bot_admin_handlers import (
    admin_invite_command, admin_users_command, admin_user_command,
    admin_grant_command, admin_stats_command, admin_panel_command,
    is_admin
)
from tests.utils.factories import UserFactory, InviteCodeFactory
from tests.utils.mocks import create_mock_telegram_update, create_mock_telegram_context, create_mock_callback_query


# SessionLocal патчится глобально в conftest.py через patch_all_session_locals


@pytest.mark.unit
class TestAdminAccessControl:
    """Тесты контроля доступа к админ командам"""
    
    def test_is_admin_function(self, db):
        """Тест helper функции is_admin()"""
        admin = UserFactory.create_admin(db, telegram_id=9000001)
        regular_user = UserFactory.create(db, telegram_id=9000002, role="user")
        
        assert is_admin(admin.telegram_id) is True
        assert is_admin(regular_user.telegram_id) is False
        assert is_admin(999999999) is False  # Несуществующий user
    
    @pytest.mark.asyncio
    async def test_admin_command_requires_admin_role(self, db):
        """Тест что админ команды доступны только админам"""
        regular_user = UserFactory.create(db, telegram_id=9100001, role="user")
        
        update = create_mock_telegram_update(user_id=regular_user.telegram_id)
        context = create_mock_telegram_context()
        
        # Пытаемся вызвать админ команду
        await admin_stats_command(update, context)
        
        # Проверяем отказ
        call_args = update.message.reply_text.call_args[0]
        assert "администраторам" in call_args[0]


@pytest.mark.unit
class TestAdminInviteCommand:
    """Тесты для /admin_invite"""
    
    @pytest.mark.asyncio
    async def test_admin_invite_shows_menu(self, db):
        """Тест что /admin_invite показывает меню выбора подписки"""
        admin = UserFactory.create_admin(db, telegram_id=9200001)
        
        update = create_mock_telegram_update(user_id=admin.telegram_id)
        context = create_mock_telegram_context()
        
        await admin_invite_command(update, context)
        
        # Проверяем что показано меню
        call_args = update.message.reply_text.call_args
        response_text = call_args[0][0]
        reply_markup = call_args[1].get('reply_markup')
        
        assert "Создание инвайт кода" in response_text
        assert reply_markup is not None
        
        # Проверяем наличие кнопок для всех типов подписок
        buttons = reply_markup.inline_keyboard
        assert len(buttons) == 5  # trial, basic, premium, enterprise, free


@pytest.mark.unit
class TestAdminUsersCommand:
    """Тесты для /admin_users"""
    
    @pytest.mark.asyncio
    async def test_admin_users_all(self, db):
        """Тест /admin_users без фильтра (все пользователи)"""
        admin = UserFactory.create_admin(db, telegram_id=9300001)
        
        # Создаем несколько пользователей
        UserFactory.create(db, telegram_id=9300002, subscription_type="free")
        UserFactory.create(db, telegram_id=9300003, subscription_type="premium")
        UserFactory.create(db, telegram_id=9300004, subscription_type="basic")
        
        update = create_mock_telegram_update(user_id=admin.telegram_id)
        context = create_mock_telegram_context(args=[])
        
        await admin_users_command(update, context)
        
        # Проверяем список пользователей
        call_args = update.message.reply_text.call_args[0]
        response = call_args[0]
        
        assert "Пользователи" in response
        # Должны быть показаны все типы подписок
        assert "free" in response.lower()
        assert "premium" in response.lower()
    
    @pytest.mark.asyncio
    async def test_admin_users_filter_active(self, db):
        """Тест фильтра /admin_users active"""
        admin = UserFactory.create_admin(db, telegram_id=9400001)
        
        # Создаем авторизованных и неавторизованных пользователей
        UserFactory.create(db, telegram_id=9400002, is_authenticated=True)
        UserFactory.create(db, telegram_id=9400003, is_authenticated=False)
        
        update = create_mock_telegram_update(user_id=admin.telegram_id)
        context = create_mock_telegram_context(args=["active"])
        
        await admin_users_command(update, context)
        
        call_args = update.message.reply_text.call_args[0]
        response = call_args[0]
        
        assert "active" in response.lower()
    
    @pytest.mark.asyncio
    async def test_admin_users_filter_premium(self, db):
        """Тест фильтра по типу подписки"""
        admin = UserFactory.create_admin(db, telegram_id=9500001)
        
        # Создаем пользователей с разными подписками
        UserFactory.create(db, telegram_id=9500002, subscription_type="premium")
        UserFactory.create(db, telegram_id=9500003, subscription_type="free")
        
        update = create_mock_telegram_update(user_id=admin.telegram_id)
        context = create_mock_telegram_context(args=["premium"])
        
        await admin_users_command(update, context)
        
        call_args = update.message.reply_text.call_args[0]
        response = call_args[0]
        
        assert "premium" in response.lower()


@pytest.mark.unit
class TestAdminGrantCommand:
    """Тесты для /admin_grant"""
    
    @pytest.mark.asyncio
    async def test_admin_grant_subscription(self, db):
        """Тест выдачи подписки пользователю"""
        admin = UserFactory.create_admin(db, telegram_id=9600001)
        user = UserFactory.create(
            db,
            telegram_id=9600002,
            subscription_type="free"
        )
        
        update = create_mock_telegram_update(user_id=admin.telegram_id)
        context = create_mock_telegram_context(args=["9600002", "premium", "30"])
        
        await admin_grant_command(update, context)
        
        # Проверяем обновление подписки
        db.refresh(user)
        assert user.subscription_type == "premium"
        assert user.subscription_expires is not None
        
        # Проверяем что создана запись в истории
        from models import SubscriptionHistory
        history = db.query(SubscriptionHistory).filter(
            SubscriptionHistory.user_id == user.id
        ).first()
        
        assert history is not None
        assert history.action == "upgraded"
        assert history.new_type == "premium"
        assert history.changed_by == admin.id


@pytest.mark.unit
class TestAdminStatsCommand:
    """Тесты для /admin_stats"""
    
    @pytest.mark.asyncio
    async def test_admin_stats_shows_counts(self, db):
        """Тест что /admin_stats показывает статистику"""
        admin = UserFactory.create_admin(db, telegram_id=9700001)
        
        # Создаем пользователей с разными подписками
        UserFactory.create(db, telegram_id=9700002, subscription_type="free")
        UserFactory.create(db, telegram_id=9700003, subscription_type="premium")
        UserFactory.create(db, telegram_id=9700004, subscription_type="premium")
        
        # Создаем инвайты
        InviteCodeFactory.create(db, created_by=admin.id)
        InviteCodeFactory.create_used(db, created_by=admin.id, used_by=9700002)
        
        update = create_mock_telegram_update(user_id=admin.telegram_id)
        context = create_mock_telegram_context()
        
        await admin_stats_command(update, context)
        
        call_args = update.message.reply_text.call_args[0]
        response = call_args[0]
        
        # Проверяем наличие статистики
        assert "Статистика" in response
        assert "Пользователи" in response
        assert "Подписки" in response
        assert "Инвайт коды" in response


@pytest.mark.unit
class TestAdminPanelCommand:
    """Тесты для /admin (Mini App панель)"""
    
    @pytest.mark.asyncio
    async def test_admin_panel_creates_session(self, db):
        """Тест создания admin session для Mini App"""
        admin = UserFactory.create_admin(db, telegram_id=9800001)
        
        update = create_mock_telegram_update(user_id=admin.telegram_id)
        context = create_mock_telegram_context()
        
        # Mock AdminPanelManager
        with patch('bot_admin_handlers.admin_panel_manager') as mock_manager:
            mock_manager.create_admin_session = MagicMock(return_value="test_token_123")
            
            await admin_panel_command(update, context)
            
            # Проверяем что session создана
            mock_manager.create_admin_session.assert_called_once_with(admin.telegram_id)
            
            # Проверяем что отправлена кнопка WebApp
            call_args = update.message.reply_text.call_args
            reply_markup = call_args[1].get('reply_markup')
            
            assert reply_markup is not None
            assert "Админ Панель" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_admin_panel_rejects_non_admin(self, db):
        """Тест что обычный пользователь не может открыть админ панель"""
        user = UserFactory.create(db, telegram_id=9900001, role="user")
        
        update = create_mock_telegram_update(user_id=user.telegram_id)
        context = create_mock_telegram_context()
        
        await admin_panel_command(update, context)
        
        # Проверяем отказ
        call_args = update.message.reply_text.call_args[0]
        assert "Доступ запрещен" in call_args[0]

