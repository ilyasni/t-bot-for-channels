"""
Unit tests для Digest Orchestrator
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from langchain_agents.orchestrator import DigestOrchestrator


class TestDigestOrchestrator:
    """Тесты для Digest Orchestrator"""
    
    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.orchestrator = DigestOrchestrator()
    
    def test_orchestrator_initialization(self):
        """Тест инициализации оркестратора"""
        assert self.orchestrator.assessor is not None
        assert self.orchestrator.topic_extractor is not None
        assert self.orchestrator.emotion_analyzer is not None
        assert self.orchestrator.speaker_analyzer is not None
        assert self.orchestrator.summarizer is not None
        assert self.orchestrator.key_moments is not None
        assert self.orchestrator.timeline is not None
        assert self.orchestrator.context_links is not None
        assert self.orchestrator.supervisor is not None
    
    @pytest.mark.asyncio
    async def test_format_messages_for_analysis(self):
        """Тест форматирования сообщений для анализа"""
        # Создаем mock сообщения
        messages = []
        for i in range(3):
            msg = Mock()
            msg.message = f"Test message {i}"
            msg.username = f"user{i}"
            msg.date = datetime.now(timezone.utc)
            messages.append(msg)
        
        formatted = self.orchestrator._format_messages_for_analysis(messages)
        
        assert "[1] user0:" in formatted
        assert "[2] user1:" in formatted
        assert "[3] user2:" in formatted
        assert "Test message 0" in formatted
        assert "Test message 1" in formatted
        assert "Test message 2" in formatted
    
    @pytest.mark.asyncio
    async def test_format_messages_without_username(self):
        """Тест форматирования сообщений без username"""
        messages = []
        msg = Mock()
        msg.message = "Test message"
        msg.username = None
        msg.sender_id = 12345
        msg.date = datetime.now(timezone.utc)
        messages.append(msg)
        
        formatted = self.orchestrator._format_messages_for_analysis(messages)
        
        assert "[1] user_12345:" in formatted
        assert "Test message" in formatted
    
    @pytest.mark.asyncio
    async def test_format_messages_with_timestamp(self):
        """Тест форматирования сообщений с временными метками"""
        messages = []
        msg = Mock()
        msg.message = "Test message"
        msg.username = "testuser"
        msg.date = datetime(2024, 1, 1, 12, 30, 0, tzinfo=timezone.utc)
        messages.append(msg)
        
        formatted = self.orchestrator._format_messages_for_analysis(messages)
        
        assert "[1] testuser (12:30):" in formatted
        assert "Test message" in formatted
    
    @pytest.mark.asyncio
    async def test_execute_conditional_agents_micro_level(self):
        """Тест выполнения условных агентов для micro уровня"""
        assessment = {
            "detail_level": "micro",
            "has_links": False
        }
        
        input_data = {
            "messages_text": "Test messages",
            "assessment": assessment,
            "user_id": 123
        }
        
        # Mock всех условных агентов
        with patch.object(self.orchestrator.key_moments, 'ainvoke', new_callable=AsyncMock) as mock_key_moments, \
             patch.object(self.orchestrator.timeline, 'ainvoke', new_callable=AsyncMock) as mock_timeline, \
             patch.object(self.orchestrator.context_links, 'ainvoke', new_callable=AsyncMock) as mock_context_links:
            
            results = await self.orchestrator._execute_conditional_agents(input_data, assessment)
            
            # Все условные агенты должны быть пропущены
            assert results["key_moments"]["skipped"] == True
            assert results["timeline"]["skipped"] == True
            assert results["context_links"]["skipped"] == True
            
            # Агенты не должны вызываться
            mock_key_moments.assert_not_called()
            mock_timeline.assert_not_called()
            mock_context_links.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_execute_conditional_agents_standard_level(self):
        """Тест выполнения условных агентов для standard уровня"""
        assessment = {
            "detail_level": "standard",
            "has_links": False
        }
        
        input_data = {
            "messages_text": "Test messages",
            "assessment": assessment,
            "user_id": 123
        }
        
        # Mock результатов агентов
        key_moments_result = {"key_decisions": [], "critical_questions": []}
        
        with patch.object(self.orchestrator.key_moments, 'ainvoke', new_callable=AsyncMock) as mock_key_moments, \
             patch.object(self.orchestrator.timeline, 'ainvoke', new_callable=AsyncMock) as mock_timeline, \
             patch.object(self.orchestrator.context_links, 'ainvoke', new_callable=AsyncMock) as mock_context_links:
            
            mock_key_moments.return_value = key_moments_result
            
            results = await self.orchestrator._execute_conditional_agents(input_data, assessment)
            
            # Key Moments должен выполниться
            assert results["key_moments"] == key_moments_result
            assert results["timeline"]["skipped"] == True
            assert results["context_links"]["skipped"] == True
            
            # Проверяем вызовы
            mock_key_moments.assert_called_once()
            mock_timeline.assert_not_called()
            mock_context_links.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_execute_conditional_agents_detailed_level(self):
        """Тест выполнения условных агентов для detailed уровня"""
        assessment = {
            "detail_level": "detailed",
            "has_links": False
        }
        
        input_data = {
            "messages_text": "Test messages",
            "assessment": assessment,
            "user_id": 123
        }
        
        # Mock результатов агентов
        key_moments_result = {"key_decisions": [], "critical_questions": []}
        timeline_result = {"timeline_events": [], "discussion_phases": []}
        
        with patch.object(self.orchestrator.key_moments, 'ainvoke', new_callable=AsyncMock) as mock_key_moments, \
             patch.object(self.orchestrator.timeline, 'ainvoke', new_callable=AsyncMock) as mock_timeline, \
             patch.object(self.orchestrator.context_links, 'ainvoke', new_callable=AsyncMock) as mock_context_links:
            
            mock_key_moments.return_value = key_moments_result
            mock_timeline.return_value = timeline_result
            
            results = await self.orchestrator._execute_conditional_agents(input_data, assessment)
            
            # Key Moments и Timeline должны выполниться
            assert results["key_moments"] == key_moments_result
            assert results["timeline"] == timeline_result
            assert results["context_links"]["skipped"] == True
            
            # Проверяем вызовы
            mock_key_moments.assert_called_once()
            mock_timeline.assert_called_once()
            mock_context_links.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_execute_conditional_agents_comprehensive_level(self):
        """Тест выполнения условных агентов для comprehensive уровня"""
        assessment = {
            "detail_level": "comprehensive",
            "has_links": False
        }
        
        input_data = {
            "messages_text": "Test messages",
            "assessment": assessment,
            "user_id": 123
        }
        
        # Mock результатов агентов
        key_moments_result = {"key_decisions": [], "critical_questions": []}
        timeline_result = {"timeline_events": [], "discussion_phases": []}
        context_links_result = {"external_links": [], "telegram_links": []}
        
        with patch.object(self.orchestrator.key_moments, 'ainvoke', new_callable=AsyncMock) as mock_key_moments, \
             patch.object(self.orchestrator.timeline, 'ainvoke', new_callable=AsyncMock) as mock_timeline, \
             patch.object(self.orchestrator.context_links, 'ainvoke', new_callable=AsyncMock) as mock_context_links:
            
            mock_key_moments.return_value = key_moments_result
            mock_timeline.return_value = timeline_result
            mock_context_links.return_value = context_links_result
            
            results = await self.orchestrator._execute_conditional_agents(input_data, assessment)
            
            # Все условные агенты должны выполниться
            assert results["key_moments"] == key_moments_result
            assert results["timeline"] == timeline_result
            assert results["context_links"] == context_links_result
            
            # Проверяем вызовы
            mock_key_moments.assert_called_once()
            mock_timeline.assert_called_once()
            mock_context_links.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_conditional_agents_with_links(self):
        """Тест выполнения условных агентов при наличии ссылок"""
        assessment = {
            "detail_level": "standard",
            "has_links": True
        }
        
        input_data = {
            "messages_text": "Test messages with https://example.com",
            "assessment": assessment,
            "user_id": 123
        }
        
        # Mock результатов агентов
        key_moments_result = {"key_decisions": [], "critical_questions": []}
        context_links_result = {"external_links": [], "telegram_links": []}
        
        with patch.object(self.orchestrator.key_moments, 'ainvoke', new_callable=AsyncMock) as mock_key_moments, \
             patch.object(self.orchestrator.timeline, 'ainvoke', new_callable=AsyncMock) as mock_timeline, \
             patch.object(self.orchestrator.context_links, 'ainvoke', new_callable=AsyncMock) as mock_context_links:
            
            mock_key_moments.return_value = key_moments_result
            mock_context_links.return_value = context_links_result
            
            results = await self.orchestrator._execute_conditional_agents(input_data, assessment)
            
            # Key Moments и Context Links должны выполниться
            assert results["key_moments"] == key_moments_result
            assert results["timeline"]["skipped"] == True
            assert results["context_links"] == context_links_result
            
            # Проверяем вызовы
            mock_key_moments.assert_called_once()
            mock_timeline.assert_not_called()
            mock_context_links.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_conditional_agents_error_handling(self):
        """Тест обработки ошибок в условных агентах"""
        assessment = {
            "detail_level": "standard",
            "has_links": False
        }
        
        input_data = {
            "messages_text": "Test messages",
            "assessment": assessment,
            "user_id": 123
        }
        
        # Mock ошибки в Key Moments агенте
        with patch.object(self.orchestrator.key_moments, 'ainvoke', new_callable=AsyncMock) as mock_key_moments:
            mock_key_moments.side_effect = Exception("Test error")
            
            results = await self.orchestrator._execute_conditional_agents(input_data, assessment)
            
            # Ошибка должна быть обработана
            assert "error" in results["key_moments"]
            assert results["key_moments"]["error"] == "Test error"
    
    def test_count_executed_agents(self):
        """Тест подсчета выполненных агентов"""
        input_data = {
            "key_moments": {"skipped": False},
            "timeline": {"skipped": True},
            "context_links": {"skipped": False}
        }
        
        count = self.orchestrator._count_executed_agents(input_data)
        
        # Базовые 5 агентов + Key Moments + Context Links + Supervisor = 8
        assert count == 8
    
    def test_count_executed_agents_all_skipped(self):
        """Тест подсчета выполненных агентов когда все условные пропущены"""
        input_data = {
            "key_moments": {"skipped": True},
            "timeline": {"skipped": True},
            "context_links": {"skipped": True}
        }
        
        count = self.orchestrator._count_executed_agents(input_data)
        
        # Базовые 5 агентов + Supervisor = 6
        assert count == 6
    
    @pytest.mark.asyncio
    async def test_prepare_final_result(self):
        """Тест подготовки финального результата"""
        start_time = datetime.now(timezone.utc)
        
        final_digest = {
            "html_digest": "<b>Test digest</b>",
            "metadata": {
                "detail_level": "standard",
                "dialogue_type": "discussion"
            },
            "sections": {
                "summary": "Test summary",
                "topics": "Test topics"
            }
        }
        
        input_data = {
            "messages": [Mock(), Mock(), Mock()],
            "hours": 24,
            "user_id": 123,
            "group_id": 456,
            "assessment": {
                "detail_level": "standard",
                "participants": 3
            }
        }
        
        result = self.orchestrator._prepare_final_result(final_digest, input_data, start_time)
        
        # Проверяем основную структуру
        assert "html_digest" in result
        assert "metadata" in result
        assert "sections" in result
        assert "generation_metadata" in result
        assert "agent_results" in result
        assert "agent_statistics" in result
        
        # Проверяем метаданные генерации
        assert result["generation_metadata"]["user_id"] == 123
        assert result["generation_metadata"]["group_id"] == 456
        assert result["generation_metadata"]["message_count"] == 3
        assert result["generation_metadata"]["hours_analyzed"] == 24
        
        # Проверяем статистику агентов
        assert result["agent_statistics"]["participants"] == 3
        assert result["agent_statistics"]["detail_level"] == "standard"
    
    @pytest.mark.asyncio
    async def test_handle_generation_error(self):
        """Тест обработки ошибок генерации"""
        start_time = datetime.now(timezone.utc)
        error = Exception("Test generation error")
        
        input_data = {
            "messages": [Mock(), Mock()],
            "hours": 24,
            "user_id": 123,
            "group_id": 456,
            "assessment": {
                "detail_level": "standard",
                "participants": 2
            }
        }
        
        result = await self.orchestrator._handle_generation_error(error, input_data, start_time)
        
        # Проверяем структуру fallback результата
        assert "html_digest" in result
        assert "metadata" in result
        assert "sections" in result
        assert "generation_metadata" in result
        assert "agent_statistics" in result
        
        # Проверяем наличие ошибки в метаданных
        assert result["generation_metadata"]["error"] == "Test generation error"
        assert result["agent_statistics"]["error"] == True
        
        # Проверяем fallback HTML
        assert "Ошибка генерации" in result["html_digest"]
        assert "Test generation error" in result["html_digest"]
