"""
Тесты для RAG команд бота
/ask, /search, /recommend, /digest
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from bot import TelegramBot
from tests.utils.factories import UserFactory, ChannelFactory, PostFactory
from tests.utils.mocks import create_mock_telegram_update, create_mock_telegram_context


# SessionLocal патчится глобально в conftest.py через patch_all_session_locals


@pytest.mark.unit
@pytest.mark.rag
class TestAskCommand:
    """Тесты для команды /ask"""
    
    @pytest.fixture
    def bot(self):
        with patch('bot.Application.builder'):
            return TelegramBot()
    
    @pytest.mark.asyncio
    async def test_ask_command_without_args(self, bot, db):
        """Тест /ask без аргументов показывает usage"""
        user = UserFactory.create(db, telegram_id=10000001, is_authenticated=True)
        
        update = create_mock_telegram_update(user_id=user.telegram_id)
        context = create_mock_telegram_context(args=[])
        
        await bot.ask_command(update, context)
        
        # Проверяем usage message
        call_args = update.message.reply_text.call_args[0]
        assert "Использование" in call_args[0]
        assert "/ask" in call_args[0] and "ваш вопрос" in call_args[0]
    
    @pytest.mark.asyncio
    async def test_ask_command_requires_authentication(self, bot, db):
        """Тест что /ask требует аутентификации"""
        user = UserFactory.create(
            db,
            telegram_id=10100001,
            is_authenticated=False
        )
        
        update = create_mock_telegram_update(user_id=user.telegram_id)
        context = create_mock_telegram_context(args=["Что нового?"])
        
        await bot.ask_command(update, context)
        
        # Проверяем сообщение об ошибке
        call_args = update.message.reply_text.call_args[0]
        assert "аутентификацию" in call_args[0]
    
    @pytest.mark.asyncio
    async def test_ask_command_no_posts(self, bot, db):
        """Тест /ask когда нет постов в БД"""
        user = UserFactory.create(db, telegram_id=10200001, is_authenticated=True)
        
        update = create_mock_telegram_update(user_id=user.telegram_id)
        context = create_mock_telegram_context(args=["Тест запрос"])
        
        await bot.ask_command(update, context)
        
        # Проверяем сообщение о пустой БД
        call_args = update.message.reply_text.call_args[0]
        assert "нет постов" in call_args[0]
        assert "/add_channel" in call_args[0]
    
    @pytest.mark.asyncio
    async def test_ask_command_success(self, bot, db):
        """Тест успешного RAG запроса"""
        user = UserFactory.create(db, telegram_id=10300001, is_authenticated=True)
        channel = ChannelFactory.create(db)
        
        # Создаем посты
        PostFactory.create(db, user_id=user.id, channel_id=channel.id)
        
        update = create_mock_telegram_update(user_id=user.telegram_id)
        context = create_mock_telegram_context(args=["Что нового в AI?"])
        
        # Mock RAG service response
        mock_rag_response = {
            "answer": "Согласно постам, в AI произошли революционные изменения",
            "sources": [
                {
                    "channel": "tech_news",
                    "url": "https://t.me/tech_news/123",
                    "score": 0.95
                }
            ]
        }
        
        with patch.object(bot, '_call_rag_service', return_value=mock_rag_response):
            await bot.ask_command(update, context)
            
            # Проверяем typing indicator
            update.message.chat.send_action.assert_called_once_with(action="typing")
            
            # Проверяем ответ
            call_args = update.message.reply_text.call_args[0]
            response = call_args[0]
            
            assert "Согласно постам" in response
            assert "революционные изменения" in response
            assert "Источники:" in response


@pytest.mark.unit
@pytest.mark.rag
class TestSearchCommand:
    """Тесты для команды /search"""
    
    @pytest.fixture
    def bot(self):
        with patch('bot.Application.builder'):
            return TelegramBot()
    
    @pytest.mark.asyncio
    async def test_search_command_without_args(self, bot, db):
        """Тест /search без аргументов"""
        user = UserFactory.create(db, telegram_id=10400001, is_authenticated=True)
        
        update = create_mock_telegram_update(user_id=user.telegram_id)
        context = create_mock_telegram_context(args=[])
        
        await bot.search_command(update, context)
        
        call_args = update.message.reply_text.call_args[0]
        assert "Использование" in call_args[0]
        assert "/search" in call_args[0] and "запрос" in call_args[0]
    
    @pytest.mark.asyncio
    async def test_search_command_hybrid_results(self, bot, db):
        """Тест гибридного поиска (посты + веб)"""
        user = UserFactory.create(db, telegram_id=10500001, is_authenticated=True)
        
        update = create_mock_telegram_update(user_id=user.telegram_id)
        context = create_mock_telegram_context(args=["квантовые", "компьютеры"])
        
        # Mock hybrid search response
        mock_response = {
            "posts": [
                {
                    "channel": "tech_news",
                    "snippet": "Квантовые компьютеры достигли нового прорыва",
                    "url": "https://t.me/tech_news/123",
                    "score": 0.92
                }
            ],
            "web": [
                {
                    "title": "IBM Quantum Computing",
                    "url": "https://ibm.com/quantum",
                    "snippet": "Latest quantum advances"
                }
            ]
        }
        
        with patch.object(bot, '_call_rag_service', return_value=mock_response):
            await bot.search_command(update, context)
            
            call_args = update.message.reply_text.call_args
            response = call_args[0][0]
            reply_markup = call_args[1].get('reply_markup')
            
            # Проверяем оба типа результатов
            assert "Ваши посты" in response
            assert "Интернет" in response
            
            # Проверяем кнопки фильтрации
            assert reply_markup is not None


@pytest.mark.unit
@pytest.mark.rag
class TestRecommendCommand:
    """Тесты для команды /recommend"""
    
    @pytest.fixture
    def bot(self):
        with patch('bot.Application.builder'):
            return TelegramBot()
    
    @pytest.mark.asyncio
    async def test_recommend_command_no_history(self, bot, db):
        """Тест /recommend без истории запросов"""
        user = UserFactory.create(db, telegram_id=10600001, is_authenticated=True)
        
        update = create_mock_telegram_update(user_id=user.telegram_id)
        context = create_mock_telegram_context()
        
        # Mock пустой ответ от RAG service
        with patch.object(bot, '_call_rag_service', return_value={"recommendations": []}):
            await bot.recommend_command(update, context)
            
            call_args = update.message.reply_text.call_args[0]
            response = call_args[0]
            
            assert "Недостаточно данных" in response
            assert "/ask" in response
    
    @pytest.mark.asyncio
    async def test_recommend_command_with_recommendations(self, bot, db):
        """Тест /recommend с рекомендациями"""
        user = UserFactory.create(db, telegram_id=10700001, is_authenticated=True)
        
        update = create_mock_telegram_update(user_id=user.telegram_id)
        context = create_mock_telegram_context()
        
        # Mock рекомендации
        mock_response = {
            "recommendations": [
                {
                    "channel": "ai_digest",
                    "title": "Новые достижения в AI",
                    "url": "https://t.me/ai_digest/456",
                    "score": 0.88
                }
            ]
        }
        
        with patch.object(bot, '_call_rag_service', return_value=mock_response):
            await bot.recommend_command(update, context)
            
            call_args = update.message.reply_text.call_args[0]
            response = call_args[0]
            
            assert "Рекомендации для вас" in response
            assert "88%" in response
            assert "ai_digest" in response


@pytest.mark.unit
@pytest.mark.rag
class TestDigestCommand:
    """Тесты для команды /digest"""
    
    @pytest.fixture
    def bot(self):
        with patch('bot.Application.builder'):
            return TelegramBot()
    
    @pytest.mark.asyncio
    async def test_digest_command_shows_menu(self, bot, db):
        """Тест что /digest показывает меню настроек"""
        user = UserFactory.create(db, telegram_id=10800001, is_authenticated=True)
        
        update = create_mock_telegram_update(user_id=user.telegram_id)
        context = create_mock_telegram_context()
        
        # Mock настройки дайджеста
        mock_settings = {
            "enabled": False,
            "frequency": "daily",
            "time": "09:00",
            "ai_summarize": False,
            "summary_style": "concise",
            "preferred_topics": []
        }
        
        with patch.object(bot, '_call_rag_service', return_value=mock_settings):
            await bot.digest_command(update, context)
            
            call_args = update.message.reply_text.call_args
            response = call_args[0][0]
            reply_markup = call_args[1].get('reply_markup')
            
            # Проверяем меню
            assert "Настройки дайджестов" in response
            assert "Отключен" in response
            assert reply_markup is not None
    
    @pytest.mark.asyncio
    async def test_digest_callback_frequency_change(self, bot, db):
        """Тест изменения частоты через callback"""
        user = UserFactory.create(db, telegram_id=10900001, is_authenticated=True)
        
        # Mock callback query
        from tests.utils.mocks import create_mock_callback_query
        query = create_mock_callback_query(
            user_id=user.telegram_id,
            data="digest_freq_weekly"
        )
        
        # Mock текущие настройки
        mock_settings = {
            "enabled": True,
            "frequency": "daily",
            "time": "09:00",
            "ai_summarize": False,
            "summary_style": "concise"
        }
        
        with patch.object(bot, '_call_rag_service') as mock_rag:
            # GET settings
            mock_rag.return_value = mock_settings
            
            # Создаем фейковый Update с callback_query
            update = MagicMock()
            update.callback_query = query
            
            await bot.handle_digest_callback(query, MagicMock())
            
            # Проверяем что был вызов для обновления
            # (второй вызов - PUT с новой частотой)
            assert mock_rag.call_count >= 2

