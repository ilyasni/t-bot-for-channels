"""
Тесты для AI Digest Generator
Персонализированные AI-дайджесты с анализом интересов
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../rag_service'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from ai_digest_generator import AIDigestGenerator
from tests.utils.factories import UserFactory, ChannelFactory, PostFactory


@pytest.mark.unit
@pytest.mark.rag
class TestAIDigestGenerator:
    """Тесты для AIDigestGenerator"""
    
    @pytest.fixture
    def digest_generator(self):
        """Fixture для AIDigestGenerator"""
        # Не нужно патчить SearchService, он уже импортируется из search.py
        generator = AIDigestGenerator()
        generator.search_service = MagicMock()
        return generator
    
    @pytest.mark.asyncio
    async def test_generate_ai_digest(self, digest_generator, db):
        """Тест генерации AI-дайджеста с персонализацией"""
        user = UserFactory.create(db, telegram_id=24000001)
        
        date_from = datetime.now(timezone.utc) - timedelta(days=7)
        date_to = datetime.now(timezone.utc)
        
        # Mock поиск постов по темам
        digest_generator.search_service.search = AsyncMock(return_value=[
            {
                "text": "AI advancement post",
                "score": 0.9,
                "channel_username": "tech_news"
            }
        ])
        
        # Mock суммаризацию
        with patch.object(digest_generator, '_call_gigachat', return_value="AI краткая выжимка"):
            digest = await digest_generator.generate_ai_digest(
                user_id=user.id,
                date_from=date_from,
                date_to=date_to,
                preferred_topics=["AI", "технологии"],
                topics_limit=3,
                summary_style="concise"
            )
            
            assert digest is not None
            assert isinstance(digest, str)
            assert len(digest) > 0
    
    @pytest.mark.asyncio
    async def test_get_user_interests(self, digest_generator, db):
        """Тест извлечения интересов пользователя"""
        user = UserFactory.create(db, telegram_id=24100001)
        
        # Создаем историю запросов
        from models import RAGQueryHistory
        
        queries = [
            "Что нового в AI?",
            "Расскажи про блокчейн",
            "Новости о нейросетях"
        ]
        
        for query in queries:
            history = RAGQueryHistory(
                user_id=user.id,
                query=query,
                created_at=datetime.now(timezone.utc),
                extracted_topics=["AI", "технологии"]
            )
            db.add(history)
        
        db.commit()
        
        # Mock получение тем из истории
        with patch('ai_digest_generator.SessionLocal', return_value=db):
            topics = await digest_generator._get_topics_from_history(user.id)
            
            # Должны быть извлечены темы
            assert len(topics) > 0
    
    @pytest.mark.asyncio
    async def test_search_posts_for_topic(self, digest_generator, db):
        """Тест поиска постов по конкретной теме"""
        user = UserFactory.create(db, telegram_id=24200001)
        
        date_from = datetime.now(timezone.utc) - timedelta(days=7)
        date_to = datetime.now(timezone.utc)
        
        # Mock search
        digest_generator.search_service.search = AsyncMock(return_value=[
            {"text": "Post about AI", "score": 0.95}
        ])
        
        posts = await digest_generator._search_posts_for_topic(
            user_id=user.id,
            topic="искусственный интеллект",
            date_from=date_from,
            date_to=date_to
        )
        
        assert len(posts) > 0
        assert posts[0]['text'] == "Post about AI"
    
    @pytest.mark.asyncio
    async def test_summarize_topic(self, digest_generator):
        """Тест суммаризации постов по теме"""
        topic = "AI технологии"
        posts = [
            {"text": "Post 1 about AI", "channel_username": "tech"},
            {"text": "Post 2 about AI advances", "channel_username": "ai_news"}
        ]
        
        # Mock LLM call
        with patch.object(digest_generator, '_call_gigachat', return_value="Краткая выжимка по AI"):
            summary = await digest_generator._summarize_topic(
                topic, posts, style="concise"
            )
            
            assert summary is not None
            assert 'topic' in summary
            assert summary['topic'] == topic
            assert 'summary' in summary
    
    @pytest.mark.asyncio
    async def test_call_gigachat_for_summarization(self, digest_generator):
        """Тест вызова GigaChat для суммаризации"""
        prompt = "Создай краткую выжимку по теме AI"
        
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={
            "choices": [{
                "message": {
                    "content": "Выжимка: AI технологии продолжают развиваться"
                }
            }]
        })
        
        with patch('httpx.AsyncClient') as mock_httpx:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_httpx.return_value = mock_client
            
            result = await digest_generator._call_gigachat(prompt, temperature=0.3)
            
            assert result is not None
            assert "AI технологии" in result
    
    @pytest.mark.asyncio
    async def test_get_user_interests_summary(self, digest_generator, db):
        """Тест получения сводки интересов пользователя"""
        user = UserFactory.create(db, telegram_id=24300001)
        
        # Mock история и популярные темы
        with patch('ai_digest_generator.SessionLocal', return_value=db), \
             patch.object(digest_generator, '_get_topics_from_history', return_value=["AI", "блокчейн"]), \
             patch.object(digest_generator, '_get_popular_topics', return_value=["стартапы"]):
            
            summary = await digest_generator.get_user_interests_summary(user.id)
            
            assert 'preferred_topics' in summary
            assert 'inferred_topics' in summary
            assert 'combined_topics' in summary
    
    def test_format_ai_digest(self, digest_generator):
        """Тест форматирования финального дайджеста"""
        topic_summaries = [
            {
                "topic": "AI",
                "summary": "Революция в AI",
                "post_count": 5,
                "sources": [{"channel": "tech_news", "url": "https://example.com/1"}, {"channel": "ai_news", "url": "https://example.com/2"}]  # Добавляем недостающий ключ sources с правильной структурой
            },
            {
                "topic": "Блокчейн",
                "summary": "Новые достижения",
                "post_count": 3,
                "sources": [{"channel": "crypto_news", "url": "https://example.com/3"}, {"channel": "blockchain_news", "url": "https://example.com/4"}]  # Добавляем недостающий ключ sources с правильной структурой
            }
        ]
        
        date_from = datetime.now(timezone.utc) - timedelta(days=7)
        date_to = datetime.now(timezone.utc)
        
        formatted = digest_generator._format_ai_digest(
            topic_summaries, date_from, date_to
        )
        
        assert "AI" in formatted
        assert "Блокчейн" in formatted
        assert "Революция" in formatted

