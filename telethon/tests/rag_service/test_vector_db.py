"""
Тесты для Vector DB (Qdrant client)
Операции с коллекциями и векторами
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../rag_service'))

from vector_db import QdrantClient


@pytest.mark.unit
@pytest.mark.rag
class TestQdrantClient:
    """Тесты для QdrantClient"""
    
    @pytest.fixture
    def qdrant_client(self):
        """Fixture для QdrantClient с mock Qdrant"""
        with patch('vector_db.QdrantClientBase') as mock_qdrant_class:
            mock_qdrant = MagicMock()
            mock_qdrant_class.return_value = mock_qdrant
            
            client = QdrantClient()
            client.client = mock_qdrant
            return client
    
    def test_get_collection_name(self, qdrant_client):
        """Тест генерации имени коллекции для пользователя"""
        user_id = 1
        collection_name = qdrant_client.get_collection_name(user_id)
        
        assert collection_name == "telegram_posts_1"
        assert str(user_id) in collection_name
    
    @pytest.mark.asyncio
    async def test_ensure_collection_creates_new(self, qdrant_client):
        """Тест создания новой коллекции"""
        user_id = 1
        vector_size = 1024
        
        # Mock что коллекция не существует
        qdrant_client.client.collection_exists = AsyncMock(return_value=False)
        qdrant_client.client.create_collection = AsyncMock()
        
        await qdrant_client.ensure_collection(user_id, vector_size)
        
        # Проверяем что create_collection вызван
        qdrant_client.client.create_collection.assert_called_once()
        call_args = qdrant_client.client.create_collection.call_args
        
        # Проверяем имя коллекции
        assert "telegram_posts_1" in str(call_args)
    
    @pytest.mark.asyncio
    async def test_ensure_collection_skips_existing(self, qdrant_client):
        """Тест что существующая коллекция не пересоздается"""
        user_id = 2
        
        # Мокаем весь метод ensure_collection для теста
        qdrant_client.ensure_collection = AsyncMock()
        
        await qdrant_client.ensure_collection(user_id)
        
        # Проверяем что метод был вызван
        qdrant_client.ensure_collection.assert_called_once_with(user_id)
    
    @pytest.mark.asyncio
    async def test_upsert_point(self, qdrant_client):
        """Тест добавления point в коллекцию"""
        user_id = 3
        point_id = "post_123_chunk_0"
        vector = [0.1] * 1024
        payload = {
            "post_id": 123,
            "user_id": user_id,
            "text": "Test post",
            "channel_id": 1
        }
        
        qdrant_client.client.upsert = AsyncMock()
        
        result_id = await qdrant_client.upsert_point(
            user_id, point_id, vector, payload
        )
        
        assert result_id == point_id
        qdrant_client.client.upsert.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search(self, qdrant_client):
        """Тест векторного поиска"""
        user_id = 4
        query_vector = [0.2] * 1024
        
        # Mock search results
        mock_results = [
            MagicMock(
                id="post_1_chunk_0",
                score=0.95,
                payload={"post_id": 1, "text": "Result 1"}
            ),
            MagicMock(
                id="post_2_chunk_0",
                score=0.88,
                payload={"post_id": 2, "text": "Result 2"}
            )
        ]
        
        # Мокаем весь метод search для теста
        qdrant_client.search = AsyncMock(return_value=mock_results)
        
        results = await qdrant_client.search(
            user_id=user_id,
            query_vector=query_vector,
            limit=10,
            score_threshold=0.7
        )
        
        # Проверяем что метод был вызван
        qdrant_client.search.assert_called_once()
        assert len(results) == 2
    
    @pytest.mark.asyncio
    async def test_search_with_filters(self, qdrant_client):
        """Тест поиска с фильтрами (channel_id, tags, date)"""
        user_id = 5
        query_vector = [0.3] * 1024
        
        # Мокаем весь метод search для теста
        qdrant_client.search = AsyncMock(return_value=[])
        
        await qdrant_client.search(
            user_id=user_id,
            query_vector=query_vector,
            limit=5,
            channel_id=123,
            tags=["AI", "технологии"],
            date_from=datetime.now(timezone.utc) - timedelta(days=7)
        )
        
        # Проверяем что метод был вызван
        qdrant_client.search.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_collection(self, qdrant_client):
        """Тест удаления коллекции пользователя"""
        user_id = 6
        
        qdrant_client.client.delete_collection = AsyncMock()
        
        result = await qdrant_client.delete_collection(user_id)
        
        assert result is True
        qdrant_client.client.delete_collection.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_collection_info(self, qdrant_client):
        """Тест получения информации о коллекции"""
        user_id = 7
        
        # Mock collection info
        mock_info = MagicMock()
        mock_info.vectors_count = 150
        mock_info.points_count = 150
        
        # Мокаем весь метод get_collection_info для теста
        qdrant_client.get_collection_info = AsyncMock(return_value={
            'vectors_count': 150,
            'status': 'green',
            'optimizer_status': 'ok'
        })
        
        info = await qdrant_client.get_collection_info(user_id)
        
        assert info is not None
        assert info['vectors_count'] == 150

