"""
Тесты для RAG API endpoints (rag_service/main.py)
Векторный поиск, индексация, генерация ответов
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../rag_service'))

# Import напрямую из rag_service (PYTHONPATH уже включает rag_service/)
from main import app as rag_app
from tests.utils.factories import UserFactory, ChannelFactory, PostFactory


@pytest.mark.unit
@pytest.mark.rag
class TestRAGIndexEndpoints:
    """Тесты для endpoints индексации"""
    
    @pytest.fixture
    def client(self):
        """TestClient для RAG service"""
        return TestClient(rag_app)
    
    @pytest.fixture
    def mock_db(self, db):
        """Mock database для RAG service"""
        def override_get_db():
            yield db
        
        # RAG service использует свой get_db
        with patch('rag_service.main.SessionLocal', return_value=db):
            yield db
    
    def test_index_post_endpoint(self, client, mock_db):
        """Тест POST /rag/index/post/{post_id}"""
        user = UserFactory.create(mock_db, telegram_id=19000001)
        channel = ChannelFactory.create(mock_db)
        post = PostFactory.create(
            mock_db,
            user_id=user.id,
            channel_id=channel.id,
            text="Post for indexing"
        )
        
        # Mock indexer service
        with patch('rag_service.main.indexer_service') as mock_indexer:
            mock_indexer.index_post = AsyncMock(return_value=(True, None))
            
            response = client.post(f"/rag/index/post/{post.id}")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data['status'] == 'queued' or data['status'] == 'success'
    
    def test_index_batch_endpoint(self, client, mock_db):
        """Тест POST /rag/index/batch"""
        user = UserFactory.create(mock_db, telegram_id=19100001)
        channel = ChannelFactory.create(mock_db)
        
        posts = PostFactory.create_batch(
            mock_db,
            user_id=user.id,
            channel_id=channel.id,
            count=5
        )
        
        post_ids = [p.id for p in posts]
        
        with patch('rag_service.main.indexer_service') as mock_indexer:
            mock_indexer.index_posts_batch = AsyncMock(return_value={
                "total": 5,
                "indexed": 5,
                "failed": 0
            })
            
            response = client.post(
                "/rag/index/batch",
                json={"post_ids": post_ids}
            )
            
            assert response.status_code == 200


@pytest.mark.unit
@pytest.mark.rag
class TestRAGSearchEndpoints:
    """Тесты для search endpoints"""
    
    @pytest.fixture
    def client(self):
        return TestClient(rag_app)
    
    def test_rag_search_endpoint(self, client):
        """Тест GET /rag/search"""
        # Mock search service
        with patch('rag_service.main.search_service') as mock_search:
            mock_search.search = AsyncMock(return_value=[
                {
                    "post_id": 1,
                    "score": 0.95,
                    "text": "Search result",
                    "channel_username": "tech_news"
                }
            ])
            
            response = client.get(
                "/rag/search",
                params={
                    "query": "искусственный интеллект",
                    "user_id": 1,
                    "limit": 10
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data['query'] == "искусственный интеллект"
            assert len(data['results']) > 0
    
    def test_rag_ask_endpoint(self, client):
        """Тест POST /rag/ask"""
        # Mock RAG generator
        with patch('rag_service.main.rag_generator') as mock_generator:
            mock_generator.generate_answer = AsyncMock(return_value={
                "answer": "Ответ на ваш вопрос о технологиях",
                "sources": [
                    {
                        "post_id": 1,
                        "channel_username": "tech",
                        "excerpt": "Excerpt"
                    }
                ],
                "context_used": 5
            })
            
            response = client.post(
                "/rag/ask",
                json={
                    "query": "Что нового в AI?",
                    "user_id": 1,
                    "context_limit": 10
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert 'answer' in data
            assert 'sources' in data
    
    def test_hybrid_search_endpoint(self, client):
        """Тест POST /rag/hybrid_search"""
        # Mock hybrid search
        with patch('rag_service.main.search_service') as mock_search, \
             patch('rag_service.main.search_web_searxng') as mock_web:
            
            mock_search.search = AsyncMock(return_value=[
                {"post_id": 1, "text": "Post result"}
            ])
            
            mock_web.return_value = [
                {"title": "Web result", "url": "https://example.com"}
            ]
            
            response = client.post(
                "/rag/hybrid_search",
                json={
                    "user_id": 1,
                    "query": "test query",
                    "include_posts": True,
                    "include_web": True,
                    "limit": 5
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert 'posts' in data
            assert 'web' in data


@pytest.mark.unit
@pytest.mark.rag
class TestRAGDigestEndpoints:
    """Тесты для digest endpoints"""
    
    @pytest.fixture
    def client(self):
        return TestClient(rag_app)
    
    def test_get_digest_settings(self, client, db):
        """Тест GET /rag/digest/settings/{user_id}"""
        user = UserFactory.create(db, telegram_id=19300001)
        
        # Mock database
        with patch('rag_service.main.SessionLocal', return_value=db):
            response = client.get(f"/rag/digest/settings/{user.id}")
            
            assert response.status_code == 200
            data = response.json()
            
            # Должны быть настройки по умолчанию
            assert 'enabled' in data
            assert 'frequency' in data
            assert 'time' in data
    
    def test_update_digest_settings(self, client, db):
        """Тест PUT /rag/digest/settings/{user_id}"""
        user = UserFactory.create(db, telegram_id=19400001)
        
        with patch('rag_service.main.SessionLocal', return_value=db):
            response = client.put(
                f"/rag/digest/settings/{user.id}",
                json={
                    "enabled": True,
                    "frequency": "weekly",
                    "time": "12:00",
                    "ai_summarize": True
                }
            )
            
            assert response.status_code == 200
    
    def test_get_recommendations(self, client):
        """Тест GET /rag/recommend/{user_id}"""
        # Mock recommendations
        with patch('rag_service.main.search_service') as mock_search, \
             patch('rag_service.main.SessionLocal'):
            
            mock_search.search = AsyncMock(return_value=[
                {
                    "post_id": 1,
                    "score": 0.92,
                    "text": "Recommended post",
                    "channel_username": "ai_news"
                }
            ])
            
            response = client.get(
                "/rag/recommend/1",
                params={"limit": 5}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert 'recommendations' in data

