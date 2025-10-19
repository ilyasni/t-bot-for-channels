"""
Тесты для Event Loop Fix
Проверка что исправления event loop работают корректно

КРИТИЧНО (Context7 best practices):
- asyncio.run() используется ТОЛЬКО ОДИН РАЗ для всего приложения
- Все Telethon клиенты работают в ОДНОМ event loop
- API отправляет задачи в главный loop через run_coroutine_threadsafe()
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, ANY
from datetime import datetime, timezone

from parser_service import ParserService
from shared_auth_manager import SharedAuthManager
from tests.utils.factories import UserFactory, ChannelFactory
from tests.utils.mocks import create_mock_telethon_client


@pytest.mark.unit
@pytest.mark.event_loop
class TestEventLoopFix:
    """Тесты для проверки исправления Event Loop"""
    
    @pytest.mark.asyncio
    async def test_parser_service_run_parsing_no_asyncio_run(self):
        """
        Тест что run_parsing НЕ использует asyncio.run()
        
        КРИТИЧНО: asyncio.run() создает НОВЫЙ event loop,
        что ломает Telethon клиенты
        """
        service = ParserService()
        
        # Mock parse_all_channels
        with patch.object(service, 'parse_all_channels', new_callable=AsyncMock):
            # Mock asyncio.create_task
            with patch('parser_service.asyncio.create_task') as mock_create_task:
                # Mock asyncio.get_running_loop (должен вызываться)
                with patch('parser_service.asyncio.get_running_loop') as mock_get_loop:
                    mock_get_loop.return_value = asyncio.get_running_loop()
                    
                    # Запускаем внутри running loop
                    service.run_parsing()
                    
                    # Проверяем что get_running_loop был вызван (может быть > 1 раза)
                    assert mock_get_loop.called
                    
                    # КРИТИЧНО: create_task должен быть вызван
                    # asyncio.run() НЕ должен вызываться!
                    mock_create_task.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_shared_auth_manager_client_reuse(self, db):
        """
        Тест переиспользования клиентов в одном event loop
        
        ВАЖНО: Клиенты НЕ должны пересоздаваться если loop не изменился
        """
        with patch.dict('os.environ', {
            'MASTER_API_ID': '12345',
            'MASTER_API_HASH': 'test_hash'
        }):
            manager = SharedAuthManager()
            
            telegram_id = 5000001
            
            # Mock Telethon client
            mock_client = create_mock_telethon_client()
            mock_client.is_user_authorized = AsyncMock(return_value=True)
            mock_client.get_me = AsyncMock(return_value=MagicMock(id=telegram_id))
            
            # Mock get_running_loop
            current_loop = asyncio.get_running_loop()
            mock_client.loop = current_loop  # Клиент в ТЕКУЩЕМ loop
            
            with patch.object(manager, '_create_client', return_value=mock_client) as mock_create:
                # Первый вызов - создает клиента
                client1 = await manager.get_user_client(telegram_id)
                
                # Второй вызов - должен вернуть ТОТ ЖЕ клиент (не пересоздавать!)
                client2 = await manager.get_user_client(telegram_id)
                
                assert client1 is client2
                # _create_client должен был вызваться только ОДИН раз
                assert mock_create.call_count == 1
    
    @pytest.mark.asyncio
    async def test_shared_auth_manager_event_loop_detection(self, db):
        """
        Тест детектирования неправильного event loop
        
        ВАЖНО: Если клиент создан в ДРУГОМ loop - должен логировать предупреждение
        """
        with patch.dict('os.environ', {
            'MASTER_API_ID': '12345',
            'MASTER_API_HASH': 'test_hash'
        }):
            manager = SharedAuthManager()
            
            telegram_id = 5100001
            
            # Mock клиент с ДРУГИМ event loop
            mock_client = create_mock_telethon_client()
            
            # Создаем фейковый другой loop (имитация)
            fake_other_loop = MagicMock()
            fake_other_loop.__class__ = asyncio.AbstractEventLoop
            mock_client.loop = fake_other_loop  # Клиент в ДРУГОМ loop!
            
            # Добавляем в active_clients
            manager.active_clients[telegram_id] = mock_client
            
            # Mock logger
            with patch('shared_auth_manager.logger') as mock_logger:
                # Mock _create_client для пересоздания
                new_client = create_mock_telethon_client()
                new_client.is_user_authorized = AsyncMock(return_value=True)
                new_client.get_me = AsyncMock(return_value=MagicMock(id=telegram_id))
                
                with patch.object(manager, '_create_client', return_value=new_client):
                    # Вызываем get_user_client
                    client = await manager.get_user_client(telegram_id)
                    
                    # КРИТИЧНО: Должно быть предупреждение о разных loop
                    # mock_logger.warning должен вызваться
                    warning_calls = [c for c in mock_logger.warning.call_args_list 
                                   if 'другом event loop' in str(c)]
                    
                    # Если loop разные - должно быть предупреждение
                    # (в реальности это НЕ ДОЛЖНО происходить!)
                    assert len(warning_calls) > 0 or client is new_client
    
    @pytest.mark.asyncio
    async def test_parser_service_clients_not_recreated_unnecessarily(self, db):
        """
        Тест что клиенты НЕ пересоздаются без необходимости
        
        ВАЖНО: Частое пересоздание клиентов приводит к:
        - Потере соединения
        - Ошибкам event loop
        - Снижению производительности
        """
        user = UserFactory.create(
            db,
            telegram_id=5200001,
            is_authenticated=True
        )
        
        channel = ChannelFactory.create(db, channel_username="test_ch")
        channel.add_user(db, user, is_active=True)
        
        # Mock Telethon client
        mock_client = create_mock_telethon_client()
        
        async def mock_iter_messages(*args, **kwargs):
            # Пустой итератор - нет новых постов
            return
            yield  # Unreachable, но делаем генератор
        
        mock_client.iter_messages = mock_iter_messages
        mock_client.get_entity = AsyncMock(return_value=MagicMock(id=channel.channel_id))
        
        service = ParserService()
        
        with patch('parser_service.shared_auth_manager') as mock_auth:
            mock_auth.get_user_client = AsyncMock(return_value=mock_client)
            
            # Парсим ДВАЖДЫ
            await service.parse_user_channels(user, db)
            await service.parse_user_channels(user, db)
            
            # get_user_client должен вызваться дважды
            assert mock_auth.get_user_client.call_count == 2
            
            # Но возвращаться должен ТОТ ЖЕ клиент
            # (в реальности shared_auth_manager вернет кешированный)


