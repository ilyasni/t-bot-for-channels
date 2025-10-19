"""
Тесты для Group Digest Generator
Генерация дайджестов диалогов через n8n workflows
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from group_digest_generator import GroupDigestGenerator
from tests.utils.mocks import create_mock_telethon_message


@pytest.mark.unit
@pytest.mark.groups
class TestGroupDigestGenerator:
    """Тесты для GroupDigestGenerator"""
    
    @pytest.fixture
    def digest_generator(self):
        """Fixture для GroupDigestGenerator"""
        generator = GroupDigestGenerator()
        return generator
    
    @pytest.mark.asyncio
    async def test_generate_digest(self, digest_generator):
        """Тест генерации дайджеста через n8n"""
        user_id = 1
        group_id = 1
        hours = 24
        
        # Mock сообщения из группы
        messages = [
            create_mock_telethon_message(
                text=f"Message {i} about technology",
                message_id=i,
                sender_username=f"user_{i % 3}"
            )
            for i in range(10)
        ]
        
        # Mock n8n response
        mock_n8n_response = {
            "summary": "Обсуждались новые технологии",
            "topics": ["AI", "блокчейн"],
            "key_speakers": ["alice", "bob"],
            "message_count": 10
        }
        
        # Mock httpx
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value=mock_n8n_response)
        
        with patch('httpx.AsyncClient') as mock_httpx:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_httpx.return_value = mock_client
            
            digest = await digest_generator.generate_digest(
                user_id, group_id, messages, hours
            )
            
            assert digest is not None
            assert 'summary' in digest
            assert 'topics' in digest
            assert digest['message_count'] == 10
    
    @pytest.mark.asyncio
    async def test_generate_digest_timeout_handling(self, digest_generator):
        """Тест обработки timeout от n8n"""
        messages = [create_mock_telethon_message(text="Test")]
        
        # Mock timeout exception
        with patch('httpx.AsyncClient') as mock_httpx:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.post = AsyncMock(side_effect=TimeoutError())
            mock_httpx.return_value = mock_client
            
            # Должен обработать timeout gracefully
            with pytest.raises(Exception):
                await digest_generator.generate_digest(1, 1, messages, 24)
    
    @pytest.mark.asyncio
    async def test_analyze_mention(self, digest_generator):
        """Тест анализа упоминания через n8n"""
        mentioned_user = "testuser"
        context_messages = [
            create_mock_telethon_message(
                text=f"Context message {i}",
                message_id=i
            )
            for i in range(5)
        ]
        
        # Mock n8n mention analyzer response
        mock_response_data = {
            "reason": "Запросили мнение",
            "context": "Обсуждение AI технологий",
            "urgency": "medium"
        }
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value=mock_response_data)
        
        with patch('httpx.AsyncClient') as mock_httpx:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_httpx.return_value = mock_client
            
            analysis = await digest_generator.analyze_mention(
                mentioned_user, context_messages
            )
            
            assert analysis is not None
            assert analysis['reason'] == "Запросили мнение"
            assert analysis['urgency'] == "medium"
    
    def test_format_digest_for_telegram(self, digest_generator):
        """Тест форматирования дайджеста для Telegram"""
        digest = {
            "summary": "Тестовое резюме диалога",
            "topics": ["Topic 1", "Topic 2"],
            "key_speakers": ["Alice", "Bob"],
            "message_count": 25
        }
        
        formatted = digest_generator.format_digest_for_telegram(
            digest, "Test Group"
        )
        
        # Проверяем Markdown formatting
        assert "Test Group" in formatted
        assert "Тестовое резюме" in formatted
        assert "Topic 1" in formatted
        assert "Alice" in formatted
        assert "25" in formatted
    
    def test_format_mention_for_telegram(self, digest_generator):
        """Тест форматирования анализа упоминания"""
        analysis = {
            "reason": "Пользователь задал вопрос",
            "context": "Обсуждение технологий",
            "urgency": "high"
        }
        
        formatted = digest_generator.format_mention_for_telegram(
            analysis,
            "Tech Chat",
            "https://t.me/c/123456/789"
        )
        
        # Проверяем formatting
        assert "Tech Chat" in formatted
        assert "Пользователь задал вопрос" in formatted
        assert "🔴" in formatted  # High urgency indicator

