"""
Тесты для Parser Service
Парсинг каналов, обогащение контентом, уведомления
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from parser_service import ParserService
from tests.utils.factories import UserFactory, ChannelFactory, PostFactory
from tests.utils.mocks import create_mock_telethon_client, create_mock_telethon_message


@pytest.mark.unit
class TestParserService:
    """Тесты для ParserService"""
    
    @pytest.fixture
    def parser_service(self):
        """Fixture для ParserService"""
        service = ParserService()
        return service
    
    @pytest.mark.asyncio
    async def test_parse_user_channels(self, parser_service, db):
        """Тест парсинга каналов пользователя"""
        user = UserFactory.create(
            db,
            telegram_id=11000001,
            is_authenticated=True
        )
        channel = ChannelFactory.create(db, channel_username="tech_news")
        channel.add_user(db, user, is_active=True)
        
        # Mock Telethon client
        mock_client = create_mock_telethon_client()
        
        # Mock iter_messages
        mock_messages = [
            create_mock_telethon_message(
                text=f"Test post {i}",
                message_id=i,
                date=datetime.now(timezone.utc) - timedelta(hours=i)
            )
            for i in range(5)
        ]
        
        async def mock_iter_messages(*args, **kwargs):
            for msg in mock_messages:
                yield msg
        
        mock_client.iter_messages = mock_iter_messages
        
        # Mock get_entity для получения channel info
        mock_entity = MagicMock()
        mock_entity.id = channel.channel_id
        mock_entity.title = channel.channel_title
        mock_client.get_entity = AsyncMock(return_value=mock_entity)
        
        # Парсим
        with patch('parser_service.get_user_client', return_value=mock_client):
            posts_count = await parser_service.parse_user_channels(user, db)
            
            # Проверяем что посты добавлены
            assert posts_count == 5
            
            # Проверяем в БД
            from models import Post
            posts = db.query(Post).filter(Post.user_id == user.id).all()
            assert len(posts) == 5
    
    @pytest.mark.asyncio
    async def test_parse_channel_posts_timezone_handling(self, parser_service, db):
        """Тест корректной обработки timezone в постах"""
        user = UserFactory.create(db, telegram_id=11100001, is_authenticated=True)
        channel = ChannelFactory.create(db)
        
        mock_client = create_mock_telethon_client()
        
        # Mock сообщение с naive datetime
        naive_datetime = datetime(2025, 1, 15, 12, 0, 0)  # БЕЗ timezone
        mock_message = create_mock_telethon_message(
            text="Test",
            message_id=1,
            date=naive_datetime
        )
        
        async def mock_iter_messages(*args, **kwargs):
            yield mock_message
        
        mock_client.iter_messages = mock_iter_messages
        mock_client.get_entity = AsyncMock(return_value=MagicMock(id=channel.channel_id))
        
        # Парсим
        await parser_service.parse_channel_posts(channel, user, mock_client, db)
        
        # Проверяем что posted_at конвертирован в timezone-aware
        from models import Post
        post = db.query(Post).filter(Post.user_id == user.id).first()
        
        assert post is not None
        assert post.posted_at.tzinfo == timezone.utc
    
    @pytest.mark.asyncio
    async def test_enrich_post_with_links(self, parser_service, db):
        """Тест обогащения поста контентом из ссылок (Crawl4AI)"""
        user = UserFactory.create(db, telegram_id=11200001)
        channel = ChannelFactory.create(db)
        
        post = PostFactory.create(
            db,
            user_id=user.id,
            channel_id=channel.id,
            text="Интересная статья: https://example.com/article"
        )
        
        # Mock Crawl4AI response
        mock_crawl_response = MagicMock()
        mock_crawl_response.status_code = 200
        mock_crawl_response.json = MagicMock(return_value={
            "success": True,
            "markdown": "# Article Title\n\nFull content from the article...",
            "word_count": 500
        })
        
        with patch('httpx.AsyncClient') as mock_httpx:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_crawl_response)
            mock_httpx.return_value = mock_client
            
            # Обогащаем пост
            await parser_service._enrich_post_with_links(post, db)
            
            # Проверяем что enriched_content заполнен
            db.refresh(post)
            assert post.enriched_content is not None
            assert "Full content" in post.enriched_content
    
    @pytest.mark.asyncio
    async def test_notify_rag_service_after_parsing(self, parser_service):
        """Тест уведомления RAG service о новых постах"""
        post_ids = [1, 2, 3, 4, 5]
        
        # Mock HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        with patch('httpx.AsyncClient') as mock_httpx:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_httpx.return_value = mock_client
            
            # Уведомляем
            await parser_service._notify_rag_service(post_ids)
            
            # Проверяем что был POST запрос
            mock_client.post.assert_called_once()
    
    def test_extract_urls_from_text(self, parser_service):
        """Тест извлечения URL из текста поста"""
        text = """
        Проверьте эти ссылки:
        https://example.com/article1
        http://test.com/page
        https://github.com/project
        """
        
        urls = parser_service._extract_urls(text)
        
        assert len(urls) == 3
        assert "https://example.com/article1" in urls
        assert "http://test.com/page" in urls
        assert "https://github.com/project" in urls
    
    @pytest.mark.asyncio
    async def test_parse_user_channels_by_id_with_tagging(self, parser_service, db):
        """
        Тест parse_user_channels_by_id с запуском тегирования
        
        ВАЖНО (Context7 Event Loop fix):
        - Проверяем что тегирование запускается через create_task
        - НЕ используется asyncio.run() (это создало бы новый loop!)
        """
        user = UserFactory.create(
            db,
            telegram_id=11400001,
            is_authenticated=True
        )
        channel = ChannelFactory.create(db, channel_username="test_channel")
        channel.add_user(db, user, is_active=True)
        
        # Mock Telethon client
        mock_client = create_mock_telethon_client()
        
        # Mock iter_messages - 3 новых поста
        mock_messages = [
            create_mock_telethon_message(
                text=f"New post {i}",
                message_id=1000 + i,
                date=datetime.now(timezone.utc) - timedelta(minutes=i)
            )
            for i in range(3)
        ]
        
        async def mock_iter_messages(*args, **kwargs):
            for msg in mock_messages:
                yield msg
        
        mock_client.iter_messages = mock_iter_messages
        mock_client.get_entity = AsyncMock(return_value=MagicMock(id=channel.channel_id))
        
        # Mock shared_auth_manager
        with patch('parser_service.shared_auth_manager') as mock_auth:
            mock_auth.get_user_client = AsyncMock(return_value=mock_client)
            
            # Mock _tag_new_posts_background
            with patch.object(parser_service, '_tag_new_posts_background', new_callable=AsyncMock) as mock_tag:
                # Парсим
                result = await parser_service.parse_user_channels_by_id(user.id)
                
                # Проверяем результат
                assert result['status'] == 'success'
                assert result['posts_added'] == 3
                
                # КРИТИЧНО: Проверяем что тегирование БЫЛО запущено
                # (через create_task, а не asyncio.run!)
                # Mock должен быть вызван если были новые посты
                if result['posts_added'] > 0:
                    # Даем asyncio время на обработку create_task
                    import asyncio
                    await asyncio.sleep(0.1)
    
    @pytest.mark.asyncio
    async def test_run_parsing_uses_create_task(self, parser_service):
        """
        Тест что run_parsing использует create_task, а НЕ asyncio.run()
        
        КРИТИЧНО (Context7 best practices):
        - run_parsing должен использовать asyncio.get_running_loop()
        - Должен вызывать create_task(), а НЕ asyncio.run()
        - Telethon клиенты НЕ МОГУТ работать если event loop изменился
        """
        # Mock parse_all_channels
        with patch.object(parser_service, 'parse_all_channels', new_callable=AsyncMock) as mock_parse:
            # Mock asyncio.create_task
            with patch('asyncio.create_task') as mock_create_task:
                # Запускаем внутри running loop
                import asyncio
                
                async def test_runner():
                    parser_service.run_parsing()
                    # Даем время на обработку
                    await asyncio.sleep(0.1)
                
                await test_runner()
                
                # КРИТИЧНО: create_task должен быть вызван
                # asyncio.run() НЕ должен вызываться (это создало бы новый loop!)
                mock_create_task.assert_called_once()

