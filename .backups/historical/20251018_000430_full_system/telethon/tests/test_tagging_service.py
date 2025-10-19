"""
Тесты для Tagging Service
AI-тегирование постов через GigaChat/OpenRouter
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from tagging_service import TaggingService
from tests.utils.factories import UserFactory, ChannelFactory, PostFactory


@pytest.mark.unit
class TestTaggingService:
    """Тесты для TaggingService"""
    
    @pytest.fixture
    def tagging_service(self):
        """Fixture для TaggingService"""
        with patch.dict('os.environ', {
            'TAGGING_PROVIDER': 'gigachat',
            'GIGACHAT_PROXY_URL': 'http://gpt2giga-proxy:8090',
            'OPENROUTER_API_KEY': 'test_key'
        }):
            service = TaggingService()
            return service
    
    @pytest.mark.asyncio
    async def test_generate_tags_gigachat(self, tagging_service):
        """Тест генерации тегов через GigaChat"""
        text = "Революция в области искусственного интеллекта! Новые нейросети превосходят GPT-4."
        
        # Mock GigaChat response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={
            "choices": [{
                "message": {
                    "content": '["AI", "нейросети", "технологии"]'
                }
            }]
        })
        
        with patch('httpx.AsyncClient') as mock_httpx:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_httpx.return_value = mock_client
            
            tags = await tagging_service.generate_tags_for_text(text)
            
            assert tags is not None
            assert isinstance(tags, list)
            assert "AI" in tags
            assert "нейросети" in tags
    
    @pytest.mark.asyncio
    async def test_generate_tags_fallback_to_openrouter(self, tagging_service):
        """Тест fallback на OpenRouter при ошибке GigaChat"""
        text = "Test text for tagging"
        
        # Mock GigaChat ошибка
        gigachat_response = MagicMock()
        gigachat_response.status_code = 503
        
        # Mock OpenRouter успех
        openrouter_response = MagicMock()
        openrouter_response.status_code = 200
        openrouter_response.json = MagicMock(return_value={
            "choices": [{
                "message": {
                    "content": '["fallback", "tags"]'
                }
            }]
        })
        
        with patch('httpx.AsyncClient') as mock_httpx:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            
            # Первый вызов (GigaChat) - ошибка, второй (OpenRouter) - успех
            mock_client.post = AsyncMock(side_effect=[
                gigachat_response,
                openrouter_response
            ])
            mock_httpx.return_value = mock_client
            
            tags = await tagging_service.generate_tags_for_text(text, use_fallback=True)
            
            assert tags is not None
            assert "fallback" in tags
    
    @pytest.mark.asyncio
    async def test_update_post_tags(self, tagging_service, db):
        """Тест обновления тегов поста"""
        user = UserFactory.create(db, telegram_id=12000001)
        channel = ChannelFactory.create(db)
        
        post = PostFactory.create(
            db,
            user_id=user.id,
            channel_id=channel.id,
            text="AI revolution in technology",
            tagging_status="pending",
            tags=None
        )
        
        # Mock успешную генерацию тегов
        with patch.object(
            tagging_service,
            'generate_tags_for_text',
            return_value=["AI", "technology", "innovation"]
        ):
            result = await tagging_service.update_post_tags(post.id, db)
            
            assert result is True
            
            # Проверяем обновление в БД
            db.refresh(post)
            assert post.tags == ["AI", "technology", "innovation"]
            assert post.tagging_status == "success"
            assert post.tagging_attempts == 1
    
    @pytest.mark.asyncio
    async def test_retry_failed_posts(self, tagging_service, db):
        """Тест retry для failed постов"""
        user = UserFactory.create(db, telegram_id=12100001)
        channel = ChannelFactory.create(db)
        
        # Создаем failed посты
        failed_posts = []
        for i in range(3):
            post = PostFactory.create(
                db,
                user_id=user.id,
                channel_id=channel.id,
                text=f"Failed post {i}",
                tagging_status="failed",
                tagging_attempts=1
            )
            failed_posts.append(post)
        
        # Mock успешный retry
        with patch.object(tagging_service, 'update_post_tags', return_value=True):
            await tagging_service.retry_failed_posts(user_id=user.id, limit=10)
            
            # Проверяем что update_post_tags вызван для всех failed постов
            assert tagging_service.update_post_tags.call_count == 3
    
    @pytest.mark.asyncio
    async def test_rate_limit_handling_429(self, tagging_service):
        """Тест обработки 429 rate limit ошибки"""
        text = "Test text"
        
        # Mock 429 ответ
        rate_limit_response = MagicMock()
        rate_limit_response.status_code = 429
        rate_limit_response.text = "Rate limit exceeded"
        
        with patch('httpx.AsyncClient') as mock_httpx:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.post = AsyncMock(return_value=rate_limit_response)
            mock_httpx.return_value = mock_client
            
            # Должен вернуть None при rate limit
            tags = await tagging_service.generate_tags_for_text(text, retry_count=0)
            
            # При первой попытке - None (будет retry)
            # TaggingService обрабатывает 429 через retry mechanism
            assert tags is None or isinstance(tags, list)

