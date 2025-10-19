"""
Тесты для QR Login handlers
ConversationHandler для /login команды
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone, timedelta

from bot_login_handlers_qr import login_start, WAITING_QR_SCAN
from tests.utils.factories import UserFactory, InviteCodeFactory
from tests.utils.mocks import create_mock_telegram_update, create_mock_telegram_context


# SessionLocal патчится глобально в conftest.py через patch_all_session_locals


@pytest.mark.unit
@pytest.mark.auth
class TestLoginHandlers:
    """Тесты для QR login handlers"""
    
    @pytest.mark.asyncio
    async def test_login_start_without_args(self, db):
        """Тест /login без аргументов"""
        update = create_mock_telegram_update(user_id=8000001)
        context = create_mock_telegram_context(args=[])
        
        from telegram.ext import ConversationHandler
        result = await login_start(update, context)
        
        # Должен вернуть END без начала conversation
        assert result == ConversationHandler.END
        
        # Проверяем usage сообщение
        call_args = update.message.reply_text.call_args[0]
        assert "Использование" in call_args[0]
        assert "INVITE_CODE" in call_args[0]
    
    @pytest.mark.asyncio
    async def test_login_start_invalid_invite(self, db):
        """Тест /login с невалидным инвайт кодом"""
        update = create_mock_telegram_update(user_id=8100001)
        context = create_mock_telegram_context(args=["INVALID_CODE"])
        
        from telegram.ext import ConversationHandler
        result = await login_start(update, context)
        
        assert result == ConversationHandler.END
        
        # Проверяем ошибку
        call_args = update.message.reply_text.call_args[0]
        assert "не найден" in call_args[0]
    
    @pytest.mark.asyncio
    async def test_login_start_expired_invite(self, db):
        """Тест /login с истекшим инвайт кодом"""
        admin = UserFactory.create_admin(db, telegram_id=8199999)
        invite = InviteCodeFactory.create_expired(db, created_by=admin.id)
        
        update = create_mock_telegram_update(user_id=8200001)
        context = create_mock_telegram_context(args=[invite.code])
        
        from telegram.ext import ConversationHandler
        result = await login_start(update, context)
        
        assert result == ConversationHandler.END
        
        call_args = update.message.reply_text.call_args[0]
        assert "истек" in call_args[0]
    
    @pytest.mark.asyncio
    async def test_login_start_valid_invite_new_user(self, db):
        """Тест /login с валидным кодом для нового пользователя"""
        admin = UserFactory.create_admin(db, telegram_id=1)
        invite = InviteCodeFactory.create(
            db,
            created_by=admin.id,
            subscription_type="premium"
        )
        
        update = create_mock_telegram_update(user_id=8300001)
        context = create_mock_telegram_context(args=[invite.code])
        
        # Mock QR auth manager
        with patch('bot_login_handlers_qr.qr_auth_manager') as mock_qr_manager:
            mock_qr_manager.create_qr_session = AsyncMock(return_value={
                'session_id': 'test_session_123',
                'qr_token': 'test_qr_token',
                'expires_at': datetime.now(timezone.utc) + timedelta(minutes=5)
            })
            
            result = await login_start(update, context)
            
            # Должен начать conversation
            assert result == WAITING_QR_SCAN
            
            # Проверяем что пользователь создан в БД
            from models import User
            user = db.query(User).filter(User.telegram_id == 8300001).first()
            assert user is not None
            assert user.subscription_type == "premium"
            
            # Проверяем что отправлена кнопка Mini App
            update.message.reply_text.assert_called()
            call_args = update.message.reply_text.call_args
            assert 'reply_markup' in call_args[1]
    
    @pytest.mark.asyncio
    async def test_login_start_existing_user_upgrades_subscription(self, db):
        """Тест что существующий пользователь получает подписку из invite"""
        # Создаем пользователя с free подпиской
        user = UserFactory.create(
            db,
            telegram_id=8400001,
            subscription_type="free"
        )
        
        # Создаем premium инвайт
        admin = UserFactory.create_admin(db, telegram_id=1)
        invite = InviteCodeFactory.create(
            db,
            created_by=admin.id,
            subscription_type="premium"
        )
        
        update = create_mock_telegram_update(user_id=user.telegram_id)
        context = create_mock_telegram_context(args=[invite.code])
        
        with patch('bot_login_handlers_qr.qr_auth_manager') as mock_qr_manager:
            mock_qr_manager.create_qr_session = AsyncMock(return_value={
                'session_id': 'test_session_456',
                'qr_token': 'test_token',
                'expires_at': datetime.now(timezone.utc) + timedelta(minutes=5)
            })
            
            result = await login_start(update, context)
            
            assert result == WAITING_QR_SCAN
            
            # Данные для апгрейда сохранены в context
            assert context.user_data['subscription_type'] == 'premium'

