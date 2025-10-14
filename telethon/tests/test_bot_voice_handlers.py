"""
Тесты для голосовых команд бота
Premium/Enterprise feature с SaluteSpeech + n8n AI classifier
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from bot import TelegramBot
from tests.utils.factories import UserFactory
from tests.utils.mocks import create_mock_telegram_update, create_mock_telegram_context, create_mock_voice_message


# SessionLocal патчится глобально в conftest.py через patch_all_session_locals


@pytest.mark.unit
@pytest.mark.voice
class TestVoiceHandlers:
    """Тесты для handle_voice_command"""
    
    @pytest.fixture
    def bot(self):
        with patch('bot.Application.builder'):
            return TelegramBot()
    
    @pytest.mark.asyncio
    async def test_voice_requires_premium(self, bot, db):
        """Тест что голосовые команды доступны только Premium/Enterprise"""
        # Free user
        free_user = UserFactory.create(
            db,
            telegram_id=21000001,
            subscription_type="free",
            is_authenticated=True
        )
        
        update = create_mock_telegram_update(user_id=free_user.telegram_id)
        update.message.voice = create_mock_voice_message(duration=5)
        context = create_mock_telegram_context()
        
        await bot.handle_voice_command(update, context)
        
        # Проверяем отказ
        call_args = update.message.reply_text.call_args[0]
        assert "Premium/Enterprise" in call_args[0]
    
    @pytest.mark.asyncio
    async def test_voice_duration_limit_60_seconds(self, bot, db):
        """Тест лимита длительности голосового (60 секунд)"""
        premium_user = UserFactory.create(
            db,
            telegram_id=21100001,
            subscription_type="premium",
            is_authenticated=True
        )
        
        update = create_mock_telegram_update(user_id=premium_user.telegram_id)
        # Голосовое 120 секунд (превышает лимит)
        update.message.voice = create_mock_voice_message(duration=120)
        context = create_mock_telegram_context()
        
        await bot.handle_voice_command(update, context)
        
        # Проверяем сообщение об ошибке
        call_args = update.message.reply_text.call_args[0]
        assert "слишком длинное" in call_args[0]
        assert "60" in call_args[0]
    
    @pytest.mark.asyncio
    async def test_voice_daily_limit(self, bot, db):
        """Тест дневного лимита голосовых запросов"""
        premium_user = UserFactory.create(
            db,
            telegram_id=21200001,
            subscription_type="premium",
            is_authenticated=True,
            voice_queries_today=50,  # Достигнут лимит для Premium (50/day)
            voice_queries_reset_at=datetime.now(timezone.utc) + timedelta(days=1)
        )
        
        update = create_mock_telegram_update(user_id=premium_user.telegram_id)
        update.message.voice = create_mock_voice_message(duration=5)
        context = create_mock_telegram_context()
        
        await bot.handle_voice_command(update, context)
        
        # Проверяем сообщение о лимите
        call_args = update.message.reply_text.call_args[0]
        assert "лимит" in call_args[0]
    
    @pytest.mark.asyncio
    async def test_voice_transcription_success(self, bot, db):
        """Тест успешной транскрибации голосового"""
        premium_user = UserFactory.create(
            db,
            telegram_id=21300001,
            subscription_type="premium",
            is_authenticated=True,
            voice_queries_today=0
        )
        
        update = create_mock_telegram_update(user_id=premium_user.telegram_id)
        update.message.voice = create_mock_voice_message(duration=5)
        context = create_mock_telegram_context()
        
        # Mock voice transcription service
        with patch('bot.voice_transcription_service') as mock_voice_service:
            mock_voice_service.is_enabled = MagicMock(return_value=True)
            mock_voice_service.transcribe_voice_message = AsyncMock(
                return_value="что нового в искусственном интеллекте"
            )
            
            # Mock n8n AI classifier
            with patch.object(
                bot,
                '_classify_voice_command',
                return_value={
                    "command": "ask",
                    "confidence": 0.85,
                    "reasoning": "Question detected"
                }
            ):
                # Mock RAG service
                with patch.object(
                    bot,
                    '_call_rag_service',
                    return_value={"answer": "AI ответ", "sources": []}
                ):
                    await bot.handle_voice_command(update, context)
                    
                    # Проверяем что транскрипция выполнена
                    mock_voice_service.transcribe_voice_message.assert_called_once()
                    
                    # Проверяем увеличение счетчика
                    db.refresh(premium_user)
                    assert premium_user.voice_queries_today == 1
    
    @pytest.mark.asyncio
    async def test_voice_ai_classification(self, bot, db):
        """Тест AI классификации голосовой команды через n8n"""
        user = UserFactory.create(
            db,
            telegram_id=21400001,
            subscription_type="enterprise",
            is_authenticated=True
        )
        
        transcription = "найди информацию о блокчейне"
        
        # Mock n8n classifier response
        mock_n8n_response = MagicMock()
        mock_n8n_response.status_code = 200
        mock_n8n_response.json = MagicMock(return_value={
            "command": "search",
            "confidence": 0.90,
            "reasoning": "Search intent detected"
        })
        
        with patch('httpx.AsyncClient') as mock_httpx:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_n8n_response)
            mock_httpx.return_value = mock_client
            
            result = await bot._classify_voice_command(transcription, user.id)
            
            assert result is not None
            assert result['command'] == 'search'
            assert result['confidence'] == 0.90

