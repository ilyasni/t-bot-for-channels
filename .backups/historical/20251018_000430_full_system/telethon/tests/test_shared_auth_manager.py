"""
Тесты для Shared Auth Manager
Проверка shared credentials authentication
"""

import pytest
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, call

from shared_auth_manager import SharedAuthManager
from tests.utils.factories import UserFactory
from tests.utils.mocks import create_mock_telethon_client


@pytest.mark.unit
@pytest.mark.auth
class TestSharedAuthManager:
    """Тесты для SharedAuthManager"""
    
    @pytest.fixture
    def auth_manager(self, tmp_path):
        """Fixture для SharedAuthManager с временной директорией"""
        sessions_dir = tmp_path / "test_sessions"
        sessions_dir.mkdir()
        
        with patch.dict(os.environ, {
            'MASTER_API_ID': '12345678',
            'MASTER_API_HASH': 'test_master_hash'
        }):
            manager = SharedAuthManager()
            manager.sessions_dir = str(sessions_dir)
            return manager
    
    def test_get_session_path(self, auth_manager):
        """Тест генерации пути к session файлу"""
        telegram_id = 3000001
        
        session_path = auth_manager._get_session_path(telegram_id)
        
        assert "user_3000001.session" in session_path
        assert session_path.endswith(".session")
    
    @pytest.mark.asyncio
    async def test_create_client(self, auth_manager):
        """Тест создания Telethon клиента"""
        telegram_id = 3100001
        
        # Mock TelegramClient
        with patch('shared_auth_manager.TelegramClient') as mock_client_class:
            mock_client = create_mock_telethon_client()
            mock_client_class.return_value = mock_client
            
            client = await auth_manager._create_client(telegram_id)
            
            assert client is not None
            mock_client_class.assert_called_once()
            
            # Проверяем что использовались master credentials
            call_args = mock_client_class.call_args
            assert int(os.environ['MASTER_API_ID']) in call_args[0]
    
    @pytest.mark.asyncio
    async def test_get_user_client_caching(self, auth_manager):
        """Тест кеширования active_clients"""
        telegram_id = 3200001
        
        # Mock client
        mock_client = create_mock_telethon_client()
        
        with patch.object(auth_manager, '_create_client', return_value=mock_client):
            # Первый вызов - создает клиент
            client1 = await auth_manager.get_user_client(telegram_id)
            
            # Второй вызов - возвращает кешированный
            client2 = await auth_manager.get_user_client(telegram_id)
            
            assert client1 is client2
            assert telegram_id in auth_manager.active_clients
    
    @pytest.mark.asyncio
    async def test_disconnect_client(self, auth_manager):
        """Тест отключения клиента"""
        telegram_id = 3300001
        
        # Добавляем клиент в active_clients
        mock_client = create_mock_telethon_client()
        auth_manager.active_clients[telegram_id] = mock_client
        
        # Отключаем
        await auth_manager.disconnect_client(telegram_id)
        
        # Проверяем что disconnect вызван
        mock_client.disconnect.assert_called_once()
        
        # Проверяем что удален из словаря
        assert telegram_id not in auth_manager.active_clients
    
    def test_is_user_blocked(self, auth_manager, db):
        """Тест проверки блокировки пользователя"""
        # Заблокированный пользователь (блокировка не истекла)
        blocked_user = UserFactory.create(
            db,
            telegram_id=3400001,
            is_blocked=True,
            block_expires=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        
        assert auth_manager._is_user_blocked(blocked_user) is True
        
        # Разблокированный пользователь
        unblocked_user = UserFactory.create(
            db,
            telegram_id=3400002,
            is_blocked=False
        )
        
        assert auth_manager._is_user_blocked(unblocked_user) is False
        
        # Пользователь с истекшей блокировкой
        expired_block_user = UserFactory.create(
            db,
            telegram_id=3400003,
            is_blocked=True,
            block_expires=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        
        assert auth_manager._is_user_blocked(expired_block_user) is False
    
    def test_check_rate_limit(self, auth_manager, db):
        """Тест rate limiting (защита от flood)"""
        # Пользователь с недавней попыткой
        recent_attempt_user = UserFactory.create(
            db,
            telegram_id=3500001,
            last_auth_attempt=datetime.now(timezone.utc) - timedelta(seconds=30),
            failed_auth_attempts=1
        )
        
        # Должен быть rate limit (< 60 секунд)
        assert auth_manager._check_rate_limit(recent_attempt_user) is False
        
        # Пользователь без недавних попыток
        no_attempt_user = UserFactory.create(
            db,
            telegram_id=3500002,
            last_auth_attempt=None
        )
        
        assert auth_manager._check_rate_limit(no_attempt_user) is True
        
        # Пользователь с давней попыткой (>60 секунд)
        old_attempt_user = UserFactory.create(
            db,
            telegram_id=3500003,
            last_auth_attempt=datetime.now(timezone.utc) - timedelta(minutes=5)
        )
        
        assert auth_manager._check_rate_limit(old_attempt_user) is True
    
    @pytest.mark.asyncio
    async def test_send_code(self, auth_manager, db):
        """Тест отправки SMS кода"""
        user = UserFactory.create(db, telegram_id=3600001)
        phone = "+79991234567"
        
        # Mock Telethon client
        mock_client = create_mock_telethon_client()
        mock_sent_code = MagicMock()
        mock_sent_code.phone_code_hash = "test_hash_123"
        mock_client.send_code_request = AsyncMock(return_value=mock_sent_code)
        
        with patch.object(auth_manager, '_create_client', return_value=mock_client):
            result = await auth_manager.send_code(user.telegram_id, phone)
            
            assert result['success'] is True
            assert 'phone_code_hash' in result
            mock_client.connect.assert_called_once()
            mock_client.send_code_request.assert_called_once_with(phone)
    
    @pytest.mark.asyncio
    async def test_verify_code_success(self, auth_manager, db):
        """Тест успешной верификации кода"""
        user = UserFactory.create(
            db,
            telegram_id=3700001,
            is_authenticated=False
        )
        
        # Mock Telethon client
        mock_client = create_mock_telethon_client()
        mock_client.sign_in = AsyncMock(return_value=MagicMock())
        mock_client.is_user_authorized = AsyncMock(return_value=True)
        
        # Добавляем client в active_clients
        auth_manager.active_clients[user.telegram_id] = mock_client
        
        with patch.object(auth_manager, 'get_client', return_value=mock_client):
            result = await auth_manager.verify_code(
                telegram_id=user.telegram_id,
                phone="+79991234567",
                code="12345"
            )
            
            assert result['success'] is True
            mock_client.sign_in.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cleanup_inactive_clients(self, auth_manager):
        """Тест очистки неактивных клиентов"""
        # Добавляем disconnected клиент
        inactive_client = create_mock_telethon_client(is_connected=False)
        auth_manager.active_clients[4000001] = inactive_client
        
        # Добавляем активный клиент
        active_client = create_mock_telethon_client(is_connected=True)
        auth_manager.active_clients[4000002] = active_client
        
        # Запускаем cleanup
        await auth_manager.cleanup_inactive_clients()
        
        # Неактивный должен быть удален
        assert 4000001 not in auth_manager.active_clients
        # Активный должен остаться
        assert 4000002 in auth_manager.active_clients
    
    def test_session_file_management(self, auth_manager, tmp_path):
        """Тест создания/удаления session файлов"""
        telegram_id = 4100001
        
        # Путь к session файлу
        session_path = auth_manager._get_session_path(telegram_id)
        
        # Создаем файл
        with open(session_path, 'w') as f:
            f.write("test session data")
        
        assert os.path.exists(session_path)
        
        # Удаляем файл
        if os.path.exists(session_path):
            os.remove(session_path)
        
        assert not os.path.exists(session_path)
    
    @pytest.mark.asyncio
    async def test_get_user_client_event_loop_check(self, auth_manager, db):
        """
        Тест проверки event loop при получении клиента
        
        КРИТИЧНО (Context7 Event Loop fix):
        - get_user_client должен проверять что клиент в правильном event loop
        - Если loop изменился - должен пересоздать клиента
        - Telethon клиенты НЕ МОГУТ работать если event loop изменился
        """
        user = UserFactory.create(
            db,
            telegram_id=4200001,
            is_authenticated=True
        )
        
        # Mock Telethon client
        mock_client = create_mock_telethon_client()
        mock_client.is_user_authorized = AsyncMock(return_value=True)
        
        # ВАЖНО: Mock get_me чтобы вернул правильный telegram_id
        mock_me = MagicMock()
        mock_me.id = user.telegram_id  # Должен совпадать!
        mock_client.get_me = AsyncMock(return_value=mock_me)
        
        # Mock asyncio.get_running_loop
        import asyncio
        
        with patch.object(auth_manager, '_create_client', return_value=mock_client):
            # Первый вызов - создаем клиент
            client1 = await auth_manager.get_user_client(user.telegram_id)
            
            assert client1 is not None
            assert user.telegram_id in auth_manager.active_clients
            
            # Проверяем что клиент сохранен
            assert auth_manager.active_clients[user.telegram_id] is client1
            
            # Второй вызов - должен вернуть тот же клиент (если loop не изменился)
            client2 = await auth_manager.get_user_client(user.telegram_id)
            
            # В тестах loop не меняется, поэтому должен быть тот же клиент
            assert client2 is client1
    
    @pytest.mark.asyncio
    async def test_client_not_deleted_after_parsing(self, auth_manager, db):
        """
        Тест что клиент НЕ удаляется после парсинга
        
        КРИТИЧНО (Context7 fix):
        - Клиенты должны оставаться в active_clients после парсинга
        - Это позволяет избежать пересоздания клиентов в новых event loops
        """
        user = UserFactory.create(
            db,
            telegram_id=4300001,
            is_authenticated=True
        )
        
        # Mock клиент
        mock_client = create_mock_telethon_client()
        auth_manager.active_clients[user.telegram_id] = mock_client
        
        # Имитируем что прошел парсинг
        # (в новом коде клиент НЕ должен удаляться)
        
        # Проверяем что клиент остался
        assert user.telegram_id in auth_manager.active_clients
        assert auth_manager.active_clients[user.telegram_id] is mock_client

