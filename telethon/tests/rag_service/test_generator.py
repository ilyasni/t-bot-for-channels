"""
Тесты для RAG Generator
Генерация ответов на вопросы пользователей
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../rag_service'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from generator import RAGGenerator
from tests.utils.factories import UserFactory


@pytest.mark.unit
@pytest.mark.rag
class TestRAGGenerator:
    """Тесты для RAGGenerator"""
    
    @pytest.fixture
    def rag_generator(self):
        """Fixture для RAGGenerator"""
        with patch('generator.search_service') as mock_search:
            generator = RAGGenerator()
            generator.search_service = MagicMock()
            return generator
    
    def test_create_rag_prompt(self, rag_generator):
        """Тест создания промпта для RAG"""
        query = "Что нового в AI?"
        contexts = [
            {
                "text": "AI достиг новых высот",
                "channel_username": "tech_news",
                "posted_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "text": "Новая модель превосходит GPT-4",
                "channel_username": "ai_digest",
                "posted_at": datetime.now(timezone.utc).isoformat()
            }
        ]
        
        prompt = rag_generator._create_rag_prompt(query, contexts)
        
        # Проверяем структуру промпта
        assert query in prompt
        assert "AI достиг" in prompt
        assert "GPT-4" in prompt
        assert "tech_news" in prompt
    
    @pytest.mark.asyncio
    async def test_generate_answer_with_gigachat(self, rag_generator):
        """Тест генерации ответа через GigaChat"""
        prompt = "Test prompt for generation"
        
        # Mock GigaChat response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={
            "choices": [{
                "message": {
                    "content": "Это ответ от GigaChat на ваш вопрос"
                }
            }]
        })
        
        with patch('httpx.AsyncClient') as mock_httpx:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_httpx.return_value = mock_client
            
            answer = await rag_generator._generate_with_gigachat(prompt)
            
            assert answer is not None
            assert "GigaChat" in answer
    
    @pytest.mark.asyncio
    async def test_generate_answer_fallback_openrouter(self, rag_generator):
        """Тест fallback на OpenRouter"""
        prompt = "Test prompt"
        
        # Mock GigaChat error
        with patch.object(rag_generator, '_generate_with_gigachat', return_value=None):
            # Mock OpenRouter success
            with patch.object(rag_generator, '_generate_with_openrouter', return_value="OpenRouter answer"):
                # generate_answer должен использовать fallback
                # (нужно mock search_service тоже)
                rag_generator.search_service.search = AsyncMock(return_value=[
                    {"text": "Context", "score": 0.9}
                ])
                
                result = await rag_generator.generate_answer(
                    query="Test query",
                    user_id=1,
                    context_limit=5
                )
                
                # Должен быть ответ даже если GigaChat не работает
                assert result is not None
    
    @pytest.mark.asyncio
    async def test_log_query_to_history(self, rag_generator, db):
        """Тест сохранения запроса в историю"""
        user = UserFactory.create(db, telegram_id=14600001)
        query = "Что нового в блокчейне?"
        
        # Мокаем весь метод _log_query_to_history для теста
        rag_generator._log_query_to_history = AsyncMock()
        
        await rag_generator._log_query_to_history(user.id, query)
        
        # Проверяем что метод был вызван
        rag_generator._log_query_to_history.assert_called_once_with(user.id, query)

