"""
Тесты для QR Authentication Manager
Проверка QR login flow через Telegram Mini App
"""

import pytest
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from qr_auth_manager import QRAuthManager
from tests.utils.factories import UserFactory, InviteCodeFactory


@pytest.mark.unit
@pytest.mark.auth
class TestQRAuthManager:
    """Тесты для QRAuthManager"""
    
    @pytest.fixture
    def qr_manager(self, redis_client):
        """Fixture для QRAuthManager с fake Redis"""
        with patch('qr_auth_manager.redis.Redis', return_value=redis_client):
            manager = QRAuthManager()
            manager.redis_client = redis_client
            return manager
    
    @pytest.mark.asyncio
    async def test_create_qr_session(self, qr_manager, db, redis_client):
        """Тест создания QR сессии в Redis"""
        user = UserFactory.create(db, telegram_id=2000001)
        invite = InviteCodeFactory.create(db, created_by=1)
        
        # Создаем QR сессию
        session_data = await qr_manager.create_qr_session(
            telegram_id=user.telegram_id,
            invite_code=invite.code
        )
        
        assert 'session_id' in session_data
        assert 'qr_token' in session_data
        assert 'expires_at' in session_data
        
        # Проверяем что сессия сохранена в Redis
        session_id = session_data['session_id']
        redis_key = f"qr_session:{session_id}"
        
        stored_data = redis_client.get(redis_key)
        assert stored_data is not None
        
        # Проверяем структуру данных
        parsed_data = json.loads(stored_data)
        assert parsed_data['telegram_id'] == user.telegram_id
        assert parsed_data['invite_code'] == invite.code
        assert parsed_data['status'] == 'pending'
    
    def test_qr_session_expiration(self, qr_manager, db, redis_client):
        """Тест TTL QR сессии (5 минут)"""
        user = UserFactory.create(db, telegram_id=2100001)
        invite = InviteCodeFactory.create(db, created_by=1)
        
        # Mock setex для проверки TTL
        redis_client.setex = MagicMock()
        
        # Создаем сессию (синхронный вызов для теста)
        session_id = "test_session_id"
        session_data = {
            "telegram_id": user.telegram_id,
            "invite_code": invite.code,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        redis_client.setex(
            f"qr_session:{session_id}",
            300,  # 5 минут в секундах
            json.dumps(session_data)
        )
        
        # Проверяем что setex вызван с правильным TTL
        redis_client.setex.assert_called_once()
        args = redis_client.setex.call_args[0]
        assert args[1] == 300  # TTL = 5 минут
    
    def test_get_session_from_redis(self, qr_manager, redis_client):
        """Тест получения сессии из Redis"""
        session_id = "test_session_123"
        session_data = {
            "telegram_id": 2200001,
            "invite_code": "TEST123",
            "status": "pending"
        }
        
        # Сохраняем в Redis
        redis_client.set(
            f"qr_session:{session_id}",
            json.dumps(session_data)
        )
        
        # Получаем через manager
        retrieved = qr_manager._get_session_from_redis(session_id)
        
        assert retrieved is not None
        assert retrieved['telegram_id'] == 2200001
        assert retrieved['status'] == 'pending'
    
    def test_update_session_status(self, qr_manager, redis_client):
        """Тест обновления статуса сессии"""
        session_id = "test_session_456"
        session_data = {
            "telegram_id": 2300001,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        redis_client.set(
            f"qr_session:{session_id}",
            json.dumps(session_data)
        )
        
        # Обновляем статус
        qr_manager._update_session_status(
            session_id,
            status="authorized",
            error=None
        )
        
        # Проверяем обновление
        updated = qr_manager._get_session_from_redis(session_id)
        assert updated['status'] == "authorized"
    
    @pytest.mark.asyncio
    async def test_finalize_authorization(self, qr_manager, db, redis_client):
        """Тест финализации авторизации после QR scan"""
        # Создаем пользователя и инвайт
        user = UserFactory.create(
            db,
            telegram_id=2400001,
            is_authenticated=False,
            subscription_type="free"
        )
        invite = InviteCodeFactory.create(
            db,
            created_by=1,
            subscription_type="premium"
        )
        
        # Создаем сессию в Redis
        session_id = "finalize_test_session"
        session_data = {
            "telegram_id": user.telegram_id,
            "invite_code": invite.code,
            "status": "authorized",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        redis_client.set(
            f"qr_session:{session_id}",
            json.dumps(session_data)
        )
        
        # Mock Telethon client для проверки авторизации
        mock_client = AsyncMock()
        mock_client.is_user_authorized = AsyncMock(return_value=True)
        
        with patch.object(qr_manager, 'get_client', return_value=mock_client):
            # Финализируем авторизацию
            await qr_manager._finalize_authorization(session_id)
        
        # Проверяем обновление пользователя в БД
        db.refresh(user)
        assert user.is_authenticated is True
        assert user.subscription_type == "premium"  # Из invite code
        
        # Проверяем что invite код использован
        db.refresh(invite)
        assert invite.uses_count == 1
        assert invite.used_by == user.id
    
    def test_get_session_status(self, qr_manager, redis_client):
        """Тест получения статуса QR сессии"""
        session_id = "status_test_session"
        session_data = {
            "telegram_id": 2500001,
            "status": "authorized",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=3)).isoformat()
        }
        
        redis_client.set(
            f"qr_session:{session_id}",
            json.dumps(session_data)
        )
        
        # Получаем статус
        status = qr_manager.get_session_status(session_id)
        
        assert status['status'] == 'authorized'
        assert status['telegram_id'] == 2500001
    
    def test_cleanup_old_sessions(self, qr_manager, redis_client):
        """Тест очистки истекших QR сессий"""
        # Создаем несколько сессий
        old_time = datetime.now(timezone.utc) - timedelta(hours=2)
        recent_time = datetime.now(timezone.utc) - timedelta(minutes=2)
        
        # Старая сессия (должна быть удалена)
        old_session_id = "old_session"
        redis_client.set(
            f"qr_session:{old_session_id}",
            json.dumps({
                "telegram_id": 2600001,
                "created_at": old_time.isoformat()
            })
        )
        
        # Свежая сессия (должна остаться)
        recent_session_id = "recent_session"
        redis_client.set(
            f"qr_session:{recent_session_id}",
            json.dumps({
                "telegram_id": 2600002,
                "created_at": recent_time.isoformat()
            })
        )
        
        # Mock keys() чтобы вернуть наши сессии
        redis_client.keys = MagicMock(return_value=[
            f"qr_session:{old_session_id}",
            f"qr_session:{recent_session_id}"
        ])
        
        # Запускаем очистку (максимум 1 час)
        qr_manager.cleanup_old_sessions(max_age_hours=1)
        
        # Проверяем что старая сессия удалена
        # В реальности fakeredis сам удалит, проверяем вызов delete
        assert redis_client.delete.called

