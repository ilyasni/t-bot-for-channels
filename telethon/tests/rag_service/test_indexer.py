"""
Тесты для Indexer Service
Индексация постов в Qdrant
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../rag_service'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from indexer import IndexerService
from tests.utils.factories import UserFactory, ChannelFactory, PostFactory


@pytest.mark.unit
@pytest.mark.rag
class TestIndexerService:
    """Тесты для IndexerService"""
    
    @pytest.fixture
    def indexer_service(self):
        """Fixture для IndexerService"""
        with patch('indexer.qdrant_client') as mock_qdrant, \
             patch('indexer.embeddings_service') as mock_embeddings:
            service = IndexerService()
            
            # Mock dependencies
            service.vector_db = MagicMock()
            service.vector_db.ensure_collection = AsyncMock()
            service.vector_db.upsert_point = AsyncMock(return_value="point_id")
            
            service.embeddings = MagicMock()
            service.embeddings.generate_embedding = AsyncMock(
                return_value=([0.1] * 1024, "gigachat")
            )
            service.embeddings.count_tokens = MagicMock(return_value=100)
            service.embeddings.chunk_text = MagicMock(return_value=[
                ("Chunk text", 0, 100)
            ])
            
            return service
    
    @pytest.mark.asyncio
    async def test_index_post(self, indexer_service, db):
        """Тест индексации одного поста"""
        user = UserFactory.create(db, telegram_id=13000001)
        channel = ChannelFactory.create(db)
        
        post = PostFactory.create(
            db,
            user_id=user.id,
            channel_id=channel.id,
            text="Test post for indexing with AI content"
        )
        
        # Индексируем
        success, error = await indexer_service.index_post(post.id, db)
        
        assert success is True
        assert error is None
        
        # Проверяем что был вызов к vector_db
        indexer_service.vector_db.upsert_point.assert_called()
    
    @pytest.mark.asyncio
    async def test_index_post_chunking_large_text(self, indexer_service, db):
        """Тест разбиения большого поста на chunks"""
        user = UserFactory.create(db, telegram_id=13100001)
        channel = ChannelFactory.create(db)
        
        # Создаем большой пост
        large_text = " ".join(["Word"] * 2000)  # Очень длинный текст
        post = PostFactory.create(
            db,
            user_id=user.id,
            channel_id=channel.id,
            text=large_text
        )
        
        # Mock chunking (3 chunks)
        indexer_service.embeddings.chunk_text = MagicMock(return_value=[
            ("Chunk 1", 0, 500),
            ("Chunk 2", 450, 950),  # Overlap
            ("Chunk 3", 900, 1400)
        ])
        
        success, error = await indexer_service.index_post(post.id, db)
        
        assert success is True
        
        # Проверяем что upsert_point вызван 3 раза (по одному на chunk)
        assert indexer_service.vector_db.upsert_point.call_count == 3
    
    @pytest.mark.asyncio
    async def test_index_posts_batch(self, indexer_service, db):
        """Тест batch индексации нескольких постов"""
        user = UserFactory.create(db, telegram_id=13200001)
        channel = ChannelFactory.create(db)
        
        # Создаем несколько постов
        posts = PostFactory.create_batch(
            db,
            user_id=user.id,
            channel_id=channel.id,
            count=5
        )
        
        post_ids = [p.id for p in posts]
        
        # Индексируем batch
        result = await indexer_service.index_posts_batch(post_ids)
        
        assert result['total'] == 5
        assert result['indexed'] > 0
    
    @pytest.mark.asyncio
    async def test_index_user_posts(self, indexer_service, db):
        """Тест индексации всех постов пользователя"""
        user = UserFactory.create(db, telegram_id=13300001)
        channel = ChannelFactory.create(db)
        
        # Создаем посты
        PostFactory.create_batch(
            db,
            user_id=user.id,
            channel_id=channel.id,
            count=10
        )
        
        # Индексируем все посты пользователя
        result = await indexer_service.index_user_posts(user.id, limit=20)
        
        assert result['total'] == 10
    
    @pytest.mark.asyncio
    async def test_index_post_saves_status(self, indexer_service, db):
        """Тест сохранения статуса индексации в БД"""
        user = UserFactory.create(db, telegram_id=13400001)
        channel = ChannelFactory.create(db)
        
        post = PostFactory.create(
            db,
            user_id=user.id,
            channel_id=channel.id,
            text="Post for status tracking"
        )
        
        # Mock _save_indexing_status
        with patch.object(indexer_service, '_save_indexing_status'):
            await indexer_service.index_post(post.id, db)
            
            # Проверяем что статус сохранен
            indexer_service._save_indexing_status.assert_called()

