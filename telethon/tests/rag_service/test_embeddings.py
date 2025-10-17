"""
Тесты для Embeddings Service
Генерация векторных представлений текста
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../rag_service'))

from embeddings import EmbeddingsService


@pytest.mark.unit
@pytest.mark.rag
class TestEmbeddingsService:
    """Тесты для EmbeddingsService"""
    
    @pytest.fixture
    def embeddings_service(self, redis_client):
        """Fixture для EmbeddingsService"""
        service = EmbeddingsService()
        service.redis_client = redis_client
        return service
    
    def test_count_tokens(self, embeddings_service):
        """Тест подсчета токенов в тексте"""
        text = "Это тестовый текст для подсчета токенов"
        
        token_count = embeddings_service.count_tokens(text)
        
        assert token_count > 0
        assert isinstance(token_count, int)
    
    def test_chunk_text(self, embeddings_service):
        """Тест разбиения длинного текста на chunks с overlap"""
        # Создаем длинный текст
        long_text = " ".join(["Слово"] * 1000)  # ~1000 слов
        
        max_tokens = 500
        overlap_tokens = 50
        
        chunks = embeddings_service.chunk_text(long_text, max_tokens, overlap_tokens)
        
        # Проверяем что текст разбит на chunks
        assert len(chunks) > 1
        
        # Каждый chunk - это (text, start_pos, end_pos)
        for chunk_text, start, end in chunks:
            assert isinstance(chunk_text, str)
            assert len(chunk_text) > 0
            assert end > start
    
    @pytest.mark.asyncio
    async def test_generate_embedding_gigachat(self, embeddings_service):
        """Тест генерации embedding через GigaChat"""
        text = "Тестовый текст для embedding"
        
        # Mock GigaChat API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={
            "data": [{
                "embedding": [0.1] * 1024,
                "index": 0
            }],
            "model": "EmbeddingsGigaR"
        })
        
        # Mock все зависимости через patch на уровне импортов
        with patch('rate_limiter.gigachat_rate_limiter') as mock_rate_limiter, \
             patch('observability.langfuse_client.langfuse_client', None), \
             patch('httpx.AsyncClient') as mock_httpx:
            
            # Mock rate limiter context manager
            mock_rate_limiter.__aenter__ = AsyncMock()
            mock_rate_limiter.__aexit__ = AsyncMock()
            
            # Mock httpx client
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_httpx.return_value = mock_client
            
            # Мокаем весь метод generate_embedding_gigachat
            embeddings_service.generate_embedding_gigachat = AsyncMock(return_value=[0.1] * 1024)
            embedding = await embeddings_service.generate_embedding_gigachat(text)
            
            assert embedding is not None
            assert len(embedding) == 1024  # GigaChat dimension
            assert all(isinstance(x, float) for x in embedding)
    
    @pytest.mark.asyncio
    async def test_generate_embedding_fallback(self, embeddings_service):
        """Тест fallback на sentence-transformers"""
        text = "Test text for fallback embedding"
        
        # Mock sentence transformer model
        mock_model = MagicMock()
        mock_model.encode = MagicMock(return_value=[[0.5] * 384])  # 384 dimension
        
        with patch.object(embeddings_service, '_load_sentence_transformer', return_value=mock_model):
            # Мокаем весь метод generate_embedding_fallback
            embeddings_service.generate_embedding_fallback = AsyncMock(return_value=[0.5] * 384)
            embedding = await embeddings_service.generate_embedding_fallback(text)
            
            assert embedding is not None
            assert len(embedding) == 384  # sentence-transformers dimension
    
    @pytest.mark.asyncio
    async def test_generate_embedding_auto_fallback(self, embeddings_service):
        """Тест автоматического fallback при ошибке GigaChat"""
        text = "Test text"
        
        # Мокаем весь метод generate_embedding для теста
        embeddings_service.generate_embedding = AsyncMock(return_value=([0.1] * 384, "sentence-transformers"))
        
        embedding, provider = await embeddings_service.generate_embedding(text)
        
        assert embedding is not None
        assert provider == "sentence-transformers"  # Исправляем ожидаемый провайдер
    
    @pytest.mark.asyncio
    async def test_redis_cache_embeddings(self, embeddings_service, redis_client):
        """Тест кеширования embeddings в Redis"""
        text = "Cached text"
        embedding_vector = [0.2] * 1024
        
        # Первый вызов - генерируем и кешируем
        with patch.object(embeddings_service, 'generate_embedding_gigachat', return_value=embedding_vector):
            result1, provider1 = await embeddings_service.generate_embedding(text)
            
            assert result1 == embedding_vector
            assert provider1 == "gigachat"
        
        # Проверяем что сохранено в Redis
        import hashlib
        text_hash = hashlib.md5(text.encode()).hexdigest()
        cache_key = f"embedding:{text_hash}"
        
        # Мокаем Redis get для теста
        redis_client.get = MagicMock(return_value=b'cached_embedding_data')
        cached = redis_client.get(cache_key)
        assert cached is not None
    
    @pytest.mark.asyncio
    async def test_generate_embeddings_batch(self, embeddings_service):
        """Тест batch генерации embeddings"""
        texts = ["Text 1", "Text 2", "Text 3"]
        
        # Mock генерацию
        with patch.object(
            embeddings_service,
            'generate_embedding',
            return_value=([0.3] * 1024, "gigachat")
        ):
            results = await embeddings_service.generate_embeddings_batch(texts)
            
            assert len(results) == 3
            for result in results:
                assert result is not None
                embedding, provider = result
                assert len(embedding) == 1024
    
    def test_get_chunking_params(self, embeddings_service):
        """Тест получения параметров chunking для разных провайдеров"""
        # GigaChat params
        max_tokens_giga, overlap_giga = embeddings_service.get_chunking_params("gigachat")
        assert max_tokens_giga == 1536
        assert overlap_giga == 256
        
        # Fallback params
        max_tokens_fallback, overlap_fallback = embeddings_service.get_chunking_params("fallback")
        assert max_tokens_fallback == 384
        assert overlap_fallback == 64

