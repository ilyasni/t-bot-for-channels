"""
Integration тесты для полного auth flow
QR login от начала до конца с PostgreSQL + Redis
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from tests.utils.factories import UserFactory, InviteCodeFactory


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.slow
class TestQRLoginCompleteFlow:
    """Integration тесты для QR login flow"""
    
    @pytest.mark.asyncio
    async def test_qr_login_complete_flow(self, db, redis_client):
        """
        Полный flow QR авторизации:
        1. Создание QR сессии
        2. Polling авторизации
        3. Финализация и обновление БД
        4. Использование invite code
        """
        # 1. Подготовка: создаем admin и invite code
        admin = UserFactory.create_admin(db, telegram_id=1)
        invite = InviteCodeFactory.create(
            db,
            created_by=admin.id,
            subscription_type="premium"
        )
        
        # 2. Импортируем QRAuthManager с реальным Redis
        from qr_auth_manager import QRAuthManager
        
        with patch('qr_auth_manager.redis.Redis', return_value=redis_client):
            qr_manager = QRAuthManager()
            qr_manager.redis_client = redis_client
            
            # 3. Создаем QR сессию
            telegram_id = 17000001
            session_data = await qr_manager.create_qr_session(
                telegram_id, invite.code
            )
            
            assert 'session_id' in session_data
            assert 'qr_token' in session_data
            
            session_id = session_data['session_id']
            
            # 4. Симулируем успешную авторизацию в Telegram
            # Mock Telethon client
            mock_client = AsyncMock()
            mock_client.is_user_authorized = AsyncMock(return_value=True)
            mock_client.get_me = AsyncMock(return_value=MagicMock(
                id=telegram_id,
                first_name="Test User"
            ))
            
            with patch.object(qr_manager, 'get_client', return_value=mock_client):
                # Обновляем статус сессии на authorized
                qr_manager._update_session_status(session_id, "authorized", None)
                
                # 5. Финализируем авторизацию
                await qr_manager._finalize_authorization(session_id)
            
            # 6. Проверяем результаты в БД
            from models import User
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            
            assert user is not None
            assert user.is_authenticated is True
            assert user.subscription_type == "premium"  # Из invite
            
            # 7. Проверяем что invite использован
            db.refresh(invite)
            assert invite.uses_count == 1
            assert invite.used_by == user.id
    
    @pytest.mark.asyncio
    async def test_invite_code_subscription_assignment(self, db):
        """Тест назначения подписки из invite code"""
        admin = UserFactory.create_admin(db, telegram_id=1)
        
        # Создаем invite с trial подпиской
        invite = InviteCodeFactory.create(
            db,
            created_by=admin.id,
            subscription_type="trial",
            default_trial_days=7
        )
        
        # Создаем нового пользователя
        user = UserFactory.create(
            db,
            telegram_id=17100001,
            subscription_type="free"
        )
        
        # Используем invite
        invite.use(user.id)
        
        # Обновляем подписку пользователя (как делает QR auth)
        user.subscription_type = invite.default_subscription
        user.subscription_started_at = datetime.now(timezone.utc)
        user.subscription_expires = datetime.now(timezone.utc) + timedelta(days=invite.default_trial_days)
        
        db.commit()
        db.refresh(user)
        
        # Проверяем назначение подписки
        assert user.subscription_type == "trial"
        assert user.subscription_expires is not None
        assert user.check_subscription_active() is True

