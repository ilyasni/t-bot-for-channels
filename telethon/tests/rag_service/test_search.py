"""
Тесты для Search Service
Векторный поиск по постам
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../rag_service'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from search import SearchService
from tests.utils.factories import UserFactory, ChannelFactory, PostFactory


@pytest.mark.unit
@pytest.mark.rag
class TestSearchService:
    """Тесты для SearchService"""
    
    @pytest.fixture
    def search_service(self):
        """Fixture для SearchService"""
        with patch('search.qdrant_client') as mock_qdrant, \
             patch('search.embeddings_service') as mock_embeddings:
            service = SearchService()
            
            # Mock dependencies
            service.vector_db = MagicMock()
            service.embeddings = MagicMock()
            
            return service
    
    @pytest.mark.asyncio
    async def test_search_basic(self, search_service, db):
        """Тест базового поиска"""
        user = UserFactory.create(db, telegram_id=14000001)
        query = "искусственный интеллект"
        
        # Mock embedding generation
        search_service.embeddings.generate_embedding = AsyncMock(
            return_value=([0.1] * 1024, "gigachat")
        )
        
        # Mock vector search results
        search_service.vector_db.search = AsyncMock(return_value=[
            {
                "id": "post_1_chunk_0",
                "score": 0.95,
                "payload": {
                    "post_id": 1,
                    "text": "AI advancement",
                    "channel_username": "tech_news"
                }
            }
        ])
        
        results = await search_service.search(
            query=query,
            user_id=user.id,
            limit=10
        )
        
        assert len(results) > 0
        assert results[0]['score'] == 0.95
    
    @pytest.mark.asyncio
    async def test_search_with_channel_filter(self, search_service, db):
        """Тест поиска с фильтром по каналу"""
        user = UserFactory.create(db, telegram_id=14100001)
        channel = ChannelFactory.create(db)
        
        search_service.embeddings.generate_embedding = AsyncMock(
            return_value=([0.2] * 1024, "gigachat")
        )
        search_service.vector_db.search = AsyncMock(return_value=[])
        
        await search_service.search(
            query="test",
            user_id=user.id,
            channel_id=channel.id,
            limit=5
        )
        
        # Проверяем что filter передан в vector_db.search
        search_service.vector_db.search.assert_called_once()
        call_kwargs = search_service.vector_db.search.call_args[1]
        assert 'channel_id' in call_kwargs
    
    @pytest.mark.asyncio
    async def test_search_with_tags_filter(self, search_service, db):
        """Тест поиска с фильтром по тегам"""
        user = UserFactory.create(db, telegram_id=14200001)
        
        search_service.embeddings.generate_embedding = AsyncMock(
            return_value=([0.3] * 1024, "gigachat")
        )
        search_service.vector_db.search = AsyncMock(return_value=[])
        
        await search_service.search(
            query="технологии",
            user_id=user.id,
            tags=["AI", "нейросети"],
            limit=10
        )
        
        call_kwargs = search_service.vector_db.search.call_args[1]
        assert 'tags' in call_kwargs
    
    @pytest.mark.asyncio
    async def test_search_with_date_range(self, search_service, db):
        """Тест поиска с фильтром по дате"""
        user = UserFactory.create(db, telegram_id=14300001)
        
        date_from = datetime.now(timezone.utc) - timedelta(days=7)
        date_to = datetime.now(timezone.utc)
        
        search_service.embeddings.generate_embedding = AsyncMock(
            return_value=([0.4] * 1024, "gigachat")
        )
        search_service.vector_db.search = AsyncMock(return_value=[])
        
        await search_service.search(
            query="новости",
            user_id=user.id,
            date_from=date_from,
            date_to=date_to,
            limit=10
        )
        
        call_kwargs = search_service.vector_db.search.call_args[1]
        assert 'date_from' in call_kwargs or 'date_to' in call_kwargs
    
    @pytest.mark.asyncio
    async def test_search_similar_posts(self, search_service, db):
        """Тест поиска похожих постов"""
        user = UserFactory.create(db, telegram_id=14400001)
        channel = ChannelFactory.create(db)
        
        # Создаем пост
        post = PostFactory.create(
            db,
            user_id=user.id,
            channel_id=channel.id,
            text="Original post about AI"
        )
        
        # Mock поиск похожих
        search_service.vector_db.search = AsyncMock(return_value=[
            {
                "id": "post_2_chunk_0",
                "score": 0.92,
                "payload": {"post_id": 2, "text": "Similar AI post"}
            }
        ])
        
        # Mock embedding для поста
        search_service.embeddings.generate_embedding = AsyncMock(
            return_value=([0.5] * 1024, "gigachat")
        )
        
        results = await search_service.search_similar_posts(post.id, limit=5)
        
        assert len(results) > 0
    
    @pytest.mark.asyncio
    async def test_get_popular_tags(self, search_service, db):
        """Тест получения популярных тегов"""
        user = UserFactory.create(db, telegram_id=14500001)
        channel = ChannelFactory.create(db)
        
        # Создаем посты с разными тегами
        PostFactory.create(db, user_id=user.id, channel_id=channel.id, tags=["AI", "tech"])
        PostFactory.create(db, user_id=user.id, channel_id=channel.id, tags=["AI", "news"])
        PostFactory.create(db, user_id=user.id, channel_id=channel.id, tags=["tech", "startup"])
        
        popular = await search_service.get_popular_tags(user.id, limit=10)
        
        # AI должен быть самым популярным (2 раза)
        assert len(popular) > 0
        assert popular[0]['tag'] == 'AI'
        assert popular[0]['count'] == 2

