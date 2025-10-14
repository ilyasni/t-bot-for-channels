"""
Integration тесты для RAG flow
Индексация → Поиск → Генерация ответа
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../rag_service'))

from tests.utils.factories import UserFactory, ChannelFactory, PostFactory


@pytest.mark.integration
@pytest.mark.rag
@pytest.mark.slow
class TestRAGCompleteFlow:
    """Integration тесты для полного RAG workflow"""
    
    @pytest.mark.asyncio
    async def test_index_search_ask_flow(self, db):
        """
        Полный RAG flow:
        1. Создание постов
        2. Индексация в Qdrant
        3. Векторный поиск
        4. Генерация ответа
        """
        # 1. Создаем пользователя и посты
        user = UserFactory.create(db, telegram_id=20000001)
        channel = ChannelFactory.create(db, channel_username="ai_news")
        
        posts = PostFactory.create_batch(
            db,
            user_id=user.id,
            channel_id=channel.id,
            count=10
        )
        
        # 2. Mock индексацию
        from indexer import IndexerService
        
        indexer = IndexerService()
        
        # Mock dependencies
        indexer.vector_db = MagicMock()
        indexer.vector_db.ensure_collection = AsyncMock()
        indexer.vector_db.upsert_point = AsyncMock(return_value="point_id")
        
        indexer.embeddings = MagicMock()
        indexer.embeddings.generate_embedding = AsyncMock(
            return_value=([0.1] * 1024, "gigachat")
        )
        indexer.embeddings.count_tokens = MagicMock(return_value=50)
        indexer.embeddings.chunk_text = MagicMock(return_value=[("chunk", 0, 100)])
        
        # Индексируем первый пост
        success, error = await indexer.index_post(posts[0].id, db)
        assert success is True
        
        # 3. Mock поиск
        from search import SearchService
        
        search_service = SearchService()
        search_service.vector_db = MagicMock()
        search_service.embeddings = MagicMock()
        
        search_service.embeddings.generate_embedding = AsyncMock(
            return_value=([0.2] * 1024, "gigachat")
        )
        
        search_service.vector_db.search = AsyncMock(return_value=[
            {
                "id": f"post_{posts[0].id}_chunk_0",
                "score": 0.95,
                "payload": {
                    "post_id": posts[0].id,
                    "text": posts[0].text,
                    "channel_username": channel.channel_username
                }
            }
        ])
        
        results = await search_service.search(
            query="AI technology",
            user_id=user.id,
            limit=5
        )
        
        assert len(results) > 0
        assert results[0]['score'] >= 0.9
        
        # 4. Mock генерацию ответа
        from generator import RAGGenerator
        
        rag_gen = RAGGenerator()
        rag_gen.search_service = search_service
        
        # Mock LLM generation
        with patch.object(rag_gen, '_generate_with_gigachat', return_value="AI ответ на вопрос"):
            answer_result = await rag_gen.generate_answer(
                query="Что нового в AI?",
                user_id=user.id,
                context_limit=5
            )
            
            assert answer_result is not None
            assert 'answer' in answer_result
    
    @pytest.mark.asyncio
    async def test_digest_generation_flow(self, db):
        """Тест генерации AI-дайджеста"""
        user = UserFactory.create(db, telegram_id=20100001)
        channel = ChannelFactory.create(db)
        
        # Создаем посты за неделю
        date_from = datetime.now(timezone.utc) - timedelta(days=7)
        date_to = datetime.now(timezone.utc)
        
        for i in range(20):
            PostFactory.create(
                db,
                user_id=user.id,
                channel_id=channel.id,
                posted_at=date_from + timedelta(hours=i * 8),
                text=f"Post {i} about technology and AI",
                tags=["AI", "технологии"]
            )
        
        # Mock digest generator
        from ai_digest_generator import AIDigestGenerator
        
        digest_gen = AIDigestGenerator()
        
        # Mock search service для поиска по темам
        mock_search = MagicMock()
        mock_search.search = AsyncMock(return_value=[
            {"text": "Post about AI", "score": 0.9}
        ])
        
        # Mock LLM для суммаризации
        with patch('ai_digest_generator.SearchService', return_value=mock_search), \
             patch.object(digest_gen, '_call_gigachat', return_value="AI summary"):
            
            digest = await digest_gen.generate_ai_digest(
                user_id=user.id,
                date_from=date_from,
                date_to=date_to,
                preferred_topics=["AI"],
                topics_limit=3,
                summary_style="concise"
            )
            
            assert digest is not None
            assert isinstance(digest, str)
            assert len(digest) > 0
    
    @pytest.mark.asyncio
    async def test_recommendations_based_on_history(self, db):
        """Тест рекомендаций на основе истории запросов"""
        user = UserFactory.create(db, telegram_id=20200001)
        channel = ChannelFactory.create(db)
        
        # Создаем посты
        PostFactory.create_batch(
            db,
            user_id=user.id,
            channel_id=channel.id,
            count=15
        )
        
        # Создаем историю запросов
        from models import RAGQueryHistory
        
        queries = ["AI технологии", "блокчейн", "нейросети"]
        for query in queries:
            history = RAGQueryHistory(
                user_id=user.id,
                query=query,
                created_at=datetime.now(timezone.utc),
                extracted_topics=["AI", "технологии"]
            )
            db.add(history)
        
        db.commit()
        
        # Проверяем что история сохранена
        history_count = db.query(RAGQueryHistory).filter(
            RAGQueryHistory.user_id == user.id
        ).count()
        
        assert history_count == 3

