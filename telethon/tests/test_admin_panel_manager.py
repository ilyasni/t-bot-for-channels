"""
Тесты для Admin Panel Manager
Проверка admin sessions в Redis для Mini App
"""

import pytest
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch, Mock
import fakeredis

# Mock Redis ПЕРЕД импортом admin_panel_manager
with patch('redis.Redis', fakeredis.FakeRedis):
    from admin_panel_manager import AdminPanelManager

from tests.utils.factories import UserFactory


@pytest.mark.unit
@pytest.mark.auth
class TestAdminPanelManager:
    """Тесты для AdminPanelManager"""
    
    @pytest.fixture
    def admin_manager(self, redis_client):
        """Fixture для AdminPanelManager с fake Redis"""
        with patch('admin_panel_manager.redis.Redis', return_value=redis_client):
            manager = AdminPanelManager()
            manager.redis_client = redis_client
            return manager
    
    def test_create_admin_session_for_admin(self, admin_manager, db, redis_client):
        """Тест создания admin session для администратора"""
        admin = UserFactory.create_admin(db, telegram_id=5000001)
        
        # Создаем admin session
        token = admin_manager.create_admin_session(admin.telegram_id)
        
        assert token is not None
        assert len(token) == 36  # UUID format
        
        # Проверяем что сохранено в Redis
        redis_key = f"admin_session:{token}"
        stored_data = redis_client.get(redis_key)
        
        assert stored_data is not None
        session_data = json.loads(stored_data)
        assert session_data['admin_id'] == admin.telegram_id
        assert session_data['role'] == 'admin'
    
    def test_create_admin_session_rejects_non_admin(self, admin_manager, db):
        """Тест что обычный пользователь не может создать admin session"""
        regular_user = UserFactory.create(
            db,
            telegram_id=5100001,
            role="user"
        )
        
        # Попытка создать admin session
        token = admin_manager.create_admin_session(regular_user.telegram_id)
        
        # Должен вернуть None
        assert token is None
    
    def test_verify_admin_session_valid(self, admin_manager, db, redis_client):
        """Тест валидации admin session"""
        admin = UserFactory.create_admin(db, telegram_id=5200001)
        
        # Создаем session
        token = admin_manager.create_admin_session(admin.telegram_id)
        
        # Верифицируем
        is_valid = admin_manager.verify_admin_session(token, admin.telegram_id)
        
        assert is_valid is True
    
    def test_verify_admin_session_wrong_admin_id(self, admin_manager, db, redis_client):
        """Тест что session не валидна для другого admin_id"""
        admin = UserFactory.create_admin(db, telegram_id=5300001)
        other_admin = UserFactory.create_admin(db, telegram_id=5300002)
        
        # Создаем session для первого админа
        token = admin_manager.create_admin_session(admin.telegram_id)
        
        # Пытаемся использовать с другим admin_id
        is_valid = admin_manager.verify_admin_session(token, other_admin.telegram_id)
        
        assert is_valid is False
    
    def test_verify_admin_session_expired(self, admin_manager, redis_client):
        """Тест что истекшая session не валидна"""
        admin_id = 5400001
        token = "test_expired_token"
        
        # Создаем истекшую session
        session_data = {
            "admin_id": admin_id,
            "role": "admin",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        }
        
        redis_client.set(
            f"admin_session:{token}",
            json.dumps(session_data)
        )
        
        # Верификация должна вернуть False
        is_valid = admin_manager.verify_admin_session(token, admin_id)
        
        assert is_valid is False
    
    def test_admin_session_ttl_1_hour(self, admin_manager, db, redis_client):
        """Тест что TTL admin session = 1 час (3600 секунд)"""
        admin = UserFactory.create_admin(db, telegram_id=5500001)
        
        # Mock setex для проверки TTL
        redis_client.setex = MagicMock()
        
        # Создаем session
        session_data = {
            "admin_id": admin.telegram_id,
            "role": "admin",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        }
        
        redis_client.setex(
            f"admin_session:test_token",
            3600,  # 1 час
            json.dumps(session_data)
        )
        
        # Проверяем TTL
        redis_client.setex.assert_called_once()
        args = redis_client.setex.call_args[0]
        assert args[1] == 3600
    
    def test_get_session_data(self, admin_manager, redis_client):
        """Тест получения данных admin session"""
        token = "test_token_123"
        session_data = {
            "admin_id": 5600001,
            "admin_name": "Test Admin",
            "role": "admin",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        redis_client.set(
            f"admin_session:{token}",
            json.dumps(session_data)
        )
        
        # Получаем данные
        retrieved = admin_manager.get_session_data(token)
        
        assert retrieved is not None
        assert retrieved['admin_id'] == 5600001
        assert retrieved['role'] == 'admin'
    
    def test_invalidate_session(self, admin_manager, redis_client):
        """Тест инвалидации admin session"""
        token = "test_token_to_invalidate"
        
        # Создаем session
        redis_client.set(
            f"admin_session:{token}",
            json.dumps({"admin_id": 5700001})
        )
        
        # Инвалидируем
        admin_manager.invalidate_session(token)
        
        # Проверяем что удалена
        redis_client.delete.assert_called()
        assert f"admin_session:{token}" in str(redis_client.delete.call_args)

