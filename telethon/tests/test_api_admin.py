"""
Тесты для Admin API endpoints
Управление пользователями, инвайтами, статистика
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import sys
import os
# Добавляем путь к telethon модулю (не rag_service)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Импортируем из корневого main.py, а не rag_service/main.py
import main as main_module
app = main_module.app

from tests.utils.factories import UserFactory, InviteCodeFactory


@pytest.mark.unit
class TestAdminAPIAccess:
    """Тесты контроля доступа к admin API"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def mock_db(self, db):
        def override_get_db():
            yield db
        from main import get_db
        app.dependency_overrides[get_db] = override_get_db
        yield db
        app.dependency_overrides.clear()
    
    def test_admin_endpoints_require_admin_session(self, client, mock_db):
        """Тест что admin endpoints требуют валидную admin session"""
        admin = UserFactory.create_admin(mock_db, telegram_id=16000001)
        
        # Mock admin session validation
        with patch.object(main_module, 'admin_panel_manager') as mock_manager:
            mock_manager.verify_admin_session = MagicMock(return_value=False)
            
            # Попытка доступа без валидной session
            response = client.get(
                "/api/admin/users",
                params={"admin_id": admin.telegram_id, "token": "invalid_token"}
            )
            
            # Должен вернуть 403
            assert response.status_code == 403
    
    def test_admin_endpoints_reject_non_admin(self, client, mock_db):
        """Тест что обычный пользователь не может вызвать admin API"""
        regular_user = UserFactory.create(
            mock_db,
            telegram_id=16100001,
            role="user"
        )
        
        with patch.object(main_module, 'admin_panel_manager') as mock_manager:
            # Даже с валидной session, но role != admin
            mock_manager.verify_admin_session = MagicMock(return_value=True)
            
            response = client.get(
                "/api/admin/users",
                params={"admin_id": regular_user.telegram_id, "token": "valid_token"}
            )
            
            # Должен проверить роль и отклонить
            assert response.status_code == 403


@pytest.mark.unit
class TestAdminUsersAPI:
    """Тесты для /api/admin/users endpoints"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def mock_db(self, db):
        def override_get_db():
            yield db
        from main import get_db
        app.dependency_overrides[get_db] = override_get_db
        yield db
        app.dependency_overrides.clear()
    
    @pytest.fixture
    def mock_admin_auth(self):
        """Mock admin authentication"""
        with patch.object(main_module, 'admin_panel_manager') as mock_manager:
            mock_manager.verify_admin_session = MagicMock(return_value=True)
            yield mock_manager
    
    def test_get_users_api_pagination(self, client, mock_db, mock_admin_auth):
        """Тест пагинации списка пользователей"""
        admin = UserFactory.create_admin(mock_db, telegram_id=16200001)
        
        # Создаем 25 пользователей
        for i in range(25):
            UserFactory.create(mock_db, telegram_id=16200100 + i)
        
        # Первая страница (20 пользователей)
        response = client.get(
            "/api/admin/users",
            params={
                "admin_id": admin.telegram_id,
                "token": "test_token",
                "page": 1,
                "limit": 20
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data['users']) == 20
        assert data['total'] >= 25
        assert data['page'] == 1
    
    def test_update_user_role_api(self, client, mock_db, mock_admin_auth):
        """Тест изменения роли пользователя"""
        admin = UserFactory.create_admin(mock_db, telegram_id=16300001)
        user = UserFactory.create(mock_db, telegram_id=16300002, role="user")
        
        response = client.post(
            f"/api/admin/user/{user.id}/role",
            params={"admin_id": admin.telegram_id, "token": "test_token"},
            json={"role": "admin"}
        )
        
        assert response.status_code == 200
        
        # Проверяем обновление
        mock_db.refresh(user)
        assert user.role == "admin"
    
    def test_update_user_subscription_api(self, client, mock_db, mock_admin_auth):
        """Тест изменения подписки через API"""
        admin = UserFactory.create_admin(mock_db, telegram_id=16400001)
        user = UserFactory.create(mock_db, telegram_id=16400002, subscription_type="free")
        
        response = client.post(
            f"/api/admin/user/{user.id}/subscription",
            params={"admin_id": admin.telegram_id, "token": "test_token"},
            json={
                "subscription_type": "premium",
                "days": 30
            }
        )
        
        assert response.status_code == 200
        
        # Проверяем обновление
        mock_db.refresh(user)
        assert user.subscription_type == "premium"
        assert user.subscription_expires is not None


@pytest.mark.unit
class TestAdminInvitesAPI:
    """Тесты для /api/admin/invites endpoints"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def mock_db(self, db):
        def override_get_db():
            yield db
        from main import get_db
        app.dependency_overrides[get_db] = override_get_db
        yield db
        app.dependency_overrides.clear()
    
    @pytest.fixture
    def mock_admin_auth(self):
        with patch.object(main_module, 'admin_panel_manager') as mock_manager:
            mock_manager.verify_admin_session = MagicMock(return_value=True)
            yield mock_manager
    
    def test_create_invite_api(self, client, mock_db, mock_admin_auth):
        """Тест создания инвайт кода через API"""
        admin = UserFactory.create_admin(mock_db, telegram_id=16500001)
        
        response = client.post(
            "/api/admin/invite/create",
            params={"admin_id": admin.telegram_id, "token": "test_token"},
            json={
                "subscription_type": "premium",
                "expires_days": 7,
                "max_uses": 1
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'code' in data
        assert len(data['code']) == 12
    
    def test_get_invites_api_with_filters(self, client, mock_db, mock_admin_auth):
        """Тест получения списка инвайтов с фильтрами"""
        admin = UserFactory.create_admin(mock_db, telegram_id=16600001)
        
        # Создаем разные инвайты
        InviteCodeFactory.create(mock_db, created_by=admin.id, subscription_type="premium")
        InviteCodeFactory.create_expired(mock_db, created_by=admin.id)
        
        # Запрашиваем активные
        response = client.get(
            "/api/admin/invites",
            params={
                "admin_id": admin.telegram_id,
                "token": "test_token",
                "status": "active"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'invites' in data


@pytest.mark.unit
class TestAdminStatsAPI:
    """Тесты для статистики"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def mock_db(self, db):
        def override_get_db():
            yield db
        from main import get_db
        app.dependency_overrides[get_db] = override_get_db
        yield db
        app.dependency_overrides.clear()
    
    @pytest.fixture
    def mock_admin_auth(self):
        with patch.object(main_module, 'admin_panel_manager') as mock_manager:
            mock_manager.verify_admin_session = MagicMock(return_value=True)
            yield mock_manager
    
    def test_get_stats_summary_api(self, client, mock_db, mock_admin_auth):
        """Тест GET /api/admin/stats/summary"""
        admin = UserFactory.create_admin(mock_db, telegram_id=16700001)
        
        # Создаем данные для статистики
        UserFactory.create(mock_db, telegram_id=16700002, subscription_type="free")
        UserFactory.create(mock_db, telegram_id=16700003, subscription_type="premium")
        
        response = client.get(
            "/api/admin/stats/summary",
            params={"admin_id": admin.telegram_id, "token": "test_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'total_users' in data
        assert 'subscription_distribution' in data
        assert data['total_users'] >= 2

