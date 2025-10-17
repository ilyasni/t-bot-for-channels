"""
Тесты для FastAPI endpoints (main.py)
REST API для интеграции с n8n и другими сервисами
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

import sys
import os
# Добавляем путь к telethon модулю (не rag_service)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Импортируем из корневого main.py, а не rag_service/main.py
import main as main_module
app = main_module.app

from tests.utils.factories import UserFactory, ChannelFactory, PostFactory


@pytest.mark.unit
class TestAPIUserEndpoints:
    """Тесты для user endpoints"""
    
    @pytest.fixture
    def client(self):
        """TestClient для FastAPI"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_db(self, db):
        """Mock database dependency"""
        def override_get_db():
            yield db
        
        app.dependency_overrides[main_module.get_db] = override_get_db
        yield db
        app.dependency_overrides.clear()
    
    def test_get_users_endpoint(self, client, mock_db):
        """Тест GET /users"""
        # Создаем пользователей
        UserFactory.create(mock_db, telegram_id=15000001)
        UserFactory.create(mock_db, telegram_id=15000002)
        
        response = client.get("/users")
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'users' in data
        assert len(data['users']) >= 2
    
    def test_get_users_filter_authenticated(self, client, mock_db):
        """Тест фильтра authenticated_only"""
        UserFactory.create(mock_db, telegram_id=15100001, is_authenticated=True)
        UserFactory.create(mock_db, telegram_id=15100002, is_authenticated=False)
        
        response = client.get("/users?authenticated_only=true")
        
        assert response.status_code == 200
        data = response.json()
        
        # Должен быть только 1 авторизованный
        assert len(data['users']) >= 1
        assert all(u['is_authenticated'] for u in data['users'])
    
    def test_get_user_channels(self, client, mock_db):
        """Тест GET /users/{telegram_id}/channels"""
        user = UserFactory.create(mock_db, telegram_id=15200001)
        channel = ChannelFactory.create(mock_db, channel_username="test_api")
        channel.add_user(mock_db, user, is_active=True)
        
        response = client.get(f"/users/{user.telegram_id}/channels")
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'channels' in data
        assert len(data['channels']) == 1
        assert data['channels'][0]['channel_username'] == 'test_api'
    
    def test_get_user_posts_with_filters(self, client, mock_db):
        """Тест GET /users/{telegram_id}/posts с фильтрами"""
        user = UserFactory.create(mock_db, telegram_id=15300001)
        channel = ChannelFactory.create(mock_db)
        
        # Создаем посты с разными датами
        PostFactory.create(
            mock_db,
            user_id=user.id,
            channel_id=channel.id,
            posted_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        PostFactory.create(
            mock_db,
            user_id=user.id,
            channel_id=channel.id,
            posted_at=datetime.now(timezone.utc) - timedelta(hours=48)
        )
        
        # Запрос за последние 24 часа
        response = client.get(
            f"/users/{user.telegram_id}/posts?hours_back=24&limit=10"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'posts' in data
        # Должен быть только 1 пост (за последние 24 часа)
        assert len(data['posts']) == 1


@pytest.mark.unit
class TestAPIRetentionEndpoints:
    """Тесты для retention settings endpoints"""
    
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
    
    def test_get_retention_settings(self, client, mock_db):
        """Тест GET /users/{user_id}/retention_settings"""
        user = UserFactory.create(
            mock_db,
            telegram_id=15400001,
            retention_days=30
        )
        
        response = client.get(f"/users/{user.id}/retention_settings")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['retention_days'] == 30
        assert data['user_id'] == user.id
        assert 'posts_stats' in data
    
    def test_update_retention_settings(self, client, mock_db):
        """Тест PUT /users/{user_id}/retention_settings"""
        user = UserFactory.create(
            mock_db,
            telegram_id=15500001,
            retention_days=30
        )
        
        # Обновляем на 60 дней
        response = client.put(
            f"/users/{user.id}/retention_settings",
            json={
                "retention_days": 60,
                "run_cleanup_immediately": False
            }
        )
        
        assert response.status_code == 200
        
        # Проверяем обновление в БД
        mock_db.refresh(user)
        assert user.retention_days == 60
    
    def test_cleanup_run_endpoint(self, client, mock_db):
        """Тест POST /cleanup/run"""
        # Мокаем cleanup_service согласно best practices
        with patch('cleanup_service.cleanup_service') as mock_cleanup_service:
            mock_cleanup_service.cleanup_old_posts = AsyncMock(return_value={
                "status": "success",
                "users_processed": 5,
                "total_posts_deleted": 100
            })
            
            response = client.post("/cleanup/run")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data['status'] == 'success'
            assert data['total_posts_deleted'] == 100

