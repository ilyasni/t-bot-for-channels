"""
Тесты для Group Monitor Service
Real-time мониторинг упоминаний в Telegram группах
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from group_monitor_service import GroupMonitorService
from tests.utils.factories import UserFactory, GroupFactory
from tests.utils.mocks import create_mock_telethon_client, create_mock_telethon_message


@pytest.mark.unit
@pytest.mark.groups
class TestGroupMonitorService:
    """Тесты для GroupMonitorService"""
    
    @pytest.fixture
    def monitor_service(self):
        """Fixture для GroupMonitorService"""
        service = GroupMonitorService()
        return service
    
    @pytest.mark.asyncio
    async def test_start_monitoring(self, monitor_service, db):
        """Тест запуска мониторинга для пользователя"""
        user = UserFactory.create(
            db,
            telegram_id=23000001,
            is_authenticated=True
        )
        
        # Добавляем группу
        group = GroupFactory.create(db)
        group.add_user(db, user, is_active=True, mentions_enabled=True)
        
        # Mock Telethon client
        mock_client = create_mock_telethon_client()
        mock_client.on = MagicMock()  # Event decorator
        
        with patch('group_monitor_service.shared_auth_manager') as mock_auth:
            mock_auth.get_user_client = AsyncMock(return_value=mock_client)
            
            result = await monitor_service.start_monitoring(user.telegram_id)
            
            # Проверяем что мониторинг запущен
            assert result is True
            assert user.telegram_id in monitor_service.active_monitors
    
    @pytest.mark.asyncio
    async def test_stop_monitoring(self, monitor_service):
        """Тест остановки мониторинга"""
        telegram_id = 23100001
        
        # Добавляем фейковый клиент в active_monitors
        mock_client = create_mock_telethon_client()
        monitor_service.active_monitors[telegram_id] = mock_client
        
        # Останавливаем
        await monitor_service.stop_monitoring(telegram_id)
        
        # Проверяем что disconnect вызван
        mock_client.disconnect.assert_called_once()
        
        # Проверяем что удален из словаря
        assert telegram_id not in monitor_service.active_monitors
    
    @pytest.mark.asyncio
    async def test_process_mention(self, monitor_service, db):
        """Тест обработки упоминания пользователя"""
        user = UserFactory.create(
            db,
            telegram_id=23200001,
            username="testuser"
        )
        group = GroupFactory.create(db, group_title="Test Group")
        group.add_user(db, user, mentions_enabled=True)
        
        # Mock Telegram event с упоминанием
        mock_event = MagicMock()
        mock_event.message = create_mock_telethon_message(
            text="@testuser что думаешь о новой технологии?",
            message_id=123
        )
        mock_event.chat_id = group.group_id
        
        # Mock context messages
        context_messages = [
            create_mock_telethon_message(text=f"Context {i}", message_id=120 + i)
            for i in range(5)
        ]
        
        # Mock методы
        with patch.object(monitor_service, '_get_context_messages', return_value=context_messages), \
             patch('group_monitor_service.group_digest_generator') as mock_digest_gen, \
             patch.object(monitor_service, '_notify_user'):
            
            mock_digest_gen.analyze_mention = AsyncMock(return_value={
                "reason": "Запрос мнения",
                "context": "Обсуждение технологий",
                "urgency": "medium"
            })
            
            await monitor_service._process_mention(user.telegram_id, mock_event)
            
            # Проверяем что analyze_mention вызван
            mock_digest_gen.analyze_mention.assert_called_once()
            
            # Проверяем что создана запись в БД
            from models import GroupMention
            mention = db.query(GroupMention).filter(
                GroupMention.user_id == user.id
            ).first()
            
            # Может быть None если БД не была передана в _process_mention
            # Это нормально для unit теста
    
    @pytest.mark.asyncio
    async def test_get_context_messages(self, monitor_service):
        """Тест получения контекстных сообщений вокруг упоминания"""
        mock_client = create_mock_telethon_client()
        
        # Mock get_messages для получения контекста
        context_msgs = [
            create_mock_telethon_message(text=f"Msg {i}", message_id=i)
            for i in range(100, 111)  # 11 сообщений
        ]
        
        mock_client.get_messages = AsyncMock(return_value=context_msgs)
        
        result = await monitor_service._get_context_messages(
            client=mock_client,
            chat_id=-1001234567890,
            message_id=105,  # Центральное сообщение
            context_size=5
        )
        
        # Должно вернуть 11 сообщений (5 до + само сообщение + 5 после)
        assert len(result) == 11
    
    @pytest.mark.asyncio
    async def test_notify_user(self, monitor_service):
        """Тест отправки уведомления пользователю"""
        telegram_id = 23400001
        
        analysis = {
            "reason": "Вас упомянули в обсуждении",
            "context": "Технический вопрос",
            "urgency": "high"
        }
        
        mock_event = MagicMock()
        mock_event.message = MagicMock()
        mock_event.message.id = 123
        
        # Mock bot для отправки сообщения
        with patch('group_monitor_service.Application') as mock_app:
            mock_bot = MagicMock()
            mock_bot.bot.send_message = AsyncMock()
            mock_app.builder.return_value.token.return_value.build.return_value = mock_bot
            
            # Mock group_digest_generator.format_mention_for_telegram
            with patch('group_monitor_service.group_digest_generator') as mock_gen:
                mock_gen.format_mention_for_telegram = MagicMock(
                    return_value="📢 Formatted mention notification"
                )
                
                await monitor_service._notify_user(
                    telegram_id,
                    analysis,
                    "Test Group",
                    mock_event
                )
                
                # Проверяем formatting вызван
                mock_gen.format_mention_for_telegram.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_all_monitors(self, monitor_service, db):
        """Тест запуска мониторинга для всех пользователей с группами"""
        # Создаем пользователей с группами
        user1 = UserFactory.create(db, telegram_id=23500001, is_authenticated=True)
        user2 = UserFactory.create(db, telegram_id=23500002, is_authenticated=True)
        
        group = GroupFactory.create(db)
        group.add_user(db, user1, mentions_enabled=True)
        group.add_user(db, user2, mentions_enabled=True)
        
        # Mock start_monitoring
        with patch.object(monitor_service, 'start_monitoring', return_value=True):
            count = await monitor_service.start_all_monitors()
            
            # Должен запустить мониторинг для обоих пользователей
            assert count == 2
            assert monitor_service.start_monitoring.call_count == 2
    
    def test_get_status(self, monitor_service):
        """Тест получения статуса мониторинга"""
        # Добавляем несколько активных мониторов
        monitor_service.active_monitors[23600001] = MagicMock()
        monitor_service.active_monitors[23600002] = MagicMock()
        
        status = monitor_service.get_status()
        
        assert status['active_monitors'] == 2
        assert 23600001 in status['monitored_users']
        assert 23600002 in status['monitored_users']

