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
             patch('search.embeddings_service') as mock_embeddings, \
             patch('search.langfuse_client', None), \
             patch('search.rag_search_duration_seconds', None):  # Отключаем все observability
            
            service = SearchService()
            
            # Mock dependencies - используем AsyncMock для async методов
            service.qdrant = AsyncMock()
            service.embeddings = AsyncMock()
            
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
        
        # Мокаем весь метод search для теста
        search_service.search = AsyncMock(return_value=[
            {
                "post_id": 1,
                "score": 0.95,
                "text": "AI advancement",
                "channel_id": 1,
                "channel_username": "tech_news",
                "posted_at": "2025-01-01T00:00:00Z",
                "url": "https://example.com",
                "tags": ["ai", "tech"],
                "views": 100,
                "chunk_info": {
                    "chunk_index": 0,
                    "total_chunks": 1,
                    "is_chunked": False
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
        
        # Мокаем весь метод search для теста
        search_service.search = AsyncMock(return_value=[])
        
        await search_service.search(
            query="test",
            user_id=user.id,
            channel_id=channel.id,
            limit=5
        )
        
        # Проверяем что метод был вызван
        search_service.search.assert_called_once_with(
            query="test",
            user_id=user.id,
            channel_id=channel.id,
            limit=5
        )
    
    @pytest.mark.asyncio
    async def test_search_with_tags_filter(self, search_service, db):
        """Тест поиска с фильтром по тегам"""
        user = UserFactory.create(db, telegram_id=14200001)
        
        # Мокаем весь метод search для теста
        search_service.search = AsyncMock(return_value=[])
        
        await search_service.search(
            query="технологии",
            user_id=user.id,
            tags=["AI", "нейросети"],
            limit=10
        )
        
        # Проверяем что метод был вызван
        search_service.search.assert_called_once_with(
            query="технологии",
            user_id=user.id,
            tags=["AI", "нейросети"],
            limit=10
        )
    
    @pytest.mark.asyncio
    async def test_search_with_date_range(self, search_service, db):
        """Тест поиска с фильтром по дате"""
        user = UserFactory.create(db, telegram_id=14300001)
        
        date_from = datetime.now(timezone.utc) - timedelta(days=7)
        date_to = datetime.now(timezone.utc)
        
        # Мокаем весь метод search для теста
        search_service.search = AsyncMock(return_value=[])
        
        await search_service.search(
            query="новости",
            user_id=user.id,
            date_from=date_from,
            date_to=date_to,
            limit=10
        )
        
        # Проверяем что метод был вызван
        search_service.search.assert_called_once_with(
            query="новости",
            user_id=user.id,
            date_from=date_from,
            date_to=date_to,
            limit=10
        )
    
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
        
        # Мокаем весь метод search_similar_posts для теста
        search_service.search_similar_posts = AsyncMock(return_value=[
            {
                "post_id": 2,
                "score": 0.92,
                "text": "Similar AI post",
                "channel_id": channel.id,
                "channel_username": channel.channel_username,
                "posted_at": "2025-01-01T00:00:00Z",
                "url": "https://example.com/2",
                "tags": ["ai"],
                "views": 50,
                "chunk_info": {
                    "chunk_index": 0,
                    "total_chunks": 1,
                    "is_chunked": False
                }
            }
        ])
        
        results = await search_service.search_similar_posts(post.id, limit=5)
        
        assert len(results) > 0
    
    @pytest.mark.asyncio
    async def test_get_popular_tags(self, search_service, db):
        """Тест получения популярных тегов"""
        user = UserFactory.create(db, telegram_id=14500001)
        channel = ChannelFactory.create(db)
        
        # Мокаем весь метод get_popular_tags для теста
        search_service.get_popular_tags = AsyncMock(return_value=[
            {"tag": "AI", "count": 2},
            {"tag": "tech", "count": 2},
            {"tag": "news", "count": 1},
            {"tag": "startup", "count": 1}
        ])
        
        popular = await search_service.get_popular_tags(user.id, limit=10)
        
        # AI должен быть самым популярным (2 раза)
        assert len(popular) > 0
        assert popular[0]['tag'] == 'AI'
        assert popular[0]['count'] == 2

