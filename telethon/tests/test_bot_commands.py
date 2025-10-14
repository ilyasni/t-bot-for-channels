"""
Тесты для основных команд Telegram бота
/start, /add_channel, /my_channels, /help, /subscription
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from bot import TelegramBot
from tests.utils.factories import UserFactory, ChannelFactory
from tests.utils.mocks import (
    create_mock_telegram_update,
    create_mock_telegram_context,
    create_mock_callback_query
)


# SessionLocal патчится глобально в conftest.py через patch_all_session_locals


@pytest.mark.unit
class TestBotStartCommand:
    """Тесты для команды /start"""
    
    @pytest.fixture
    def bot(self):
        """Fixture для TelegramBot"""
        with patch('bot.Application.builder'):
            bot_instance = TelegramBot()
            return bot_instance
    
    @pytest.mark.asyncio
    async def test_start_command_new_user(self, bot, db):
        """Тест /start для нового пользователя"""
        update = create_mock_telegram_update(user_id=6000001)
        context = create_mock_telegram_context()
        
        # Выполняем команду
        await bot.start_command(update, context)
        
        # Проверяем что пользователь создан
        from models import User
        user = db.query(User).filter(User.telegram_id == 6000001).first()
        
        assert user is not None
        assert user.telegram_id == 6000001
        
        # Проверяем что отправлено welcome сообщение
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0]
        assert "Добро пожаловать" in call_args[0]
        assert "/login" in call_args[0]
    
    @pytest.mark.asyncio
    async def test_start_command_existing_authenticated_user(self, bot, db):
        """Тест /start для авторизованного пользователя"""
        user = UserFactory.create(
            db,
            telegram_id=6100001,
            first_name="Existing",
            is_authenticated=True
        )
        
        update = create_mock_telegram_update(user_id=user.telegram_id)
        context = create_mock_telegram_context()
        
        await bot.start_command(update, context)
        
        # Проверяем welcome back сообщение
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0]
        assert "С возвращением" in call_args[0]
        assert "Existing" in call_args[0]
    
    @pytest.mark.asyncio
    async def test_start_command_admin_sees_admin_commands(self, bot, db):
        """Тест что админ видит админские команды"""
        admin = UserFactory.create_admin(
            db,
            telegram_id=6200001,
            first_name="Admin"
        )
        
        update = create_mock_telegram_update(user_id=admin.telegram_id)
        context = create_mock_telegram_context()
        
        await bot.start_command(update, context)
        
        # Проверяем наличие админских команд
        call_args = update.message.reply_text.call_args[0]
        assert "/admin" in call_args[0]
        assert "Администратор" in call_args[0]


@pytest.mark.unit
class TestBotChannelCommands:
    """Тесты для команд управления каналами"""
    
    @pytest.fixture
    def bot(self):
        with patch('bot.Application.builder'):
            return TelegramBot()
    
    @pytest.mark.asyncio
    async def test_add_channel_command_success(self, bot, db):
        """Тест успешного добавления канала"""
        user = UserFactory.create(
            db,
            telegram_id=6300001,
            is_authenticated=True,
            max_channels=5
        )
        
        update = create_mock_telegram_update(user_id=user.telegram_id)
        context = create_mock_telegram_context(args=["@tech_news"])
        
        await bot.add_channel_command(update, context)
        
        # Проверяем что канал добавлен
        db.refresh(user)
        assert len(user.channels) == 1
        assert user.channels[0].channel_username == "tech_news"
        
        # Проверяем успешное сообщение
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0]
        assert "успешно добавлен" in call_args[0]
    
    @pytest.mark.asyncio
    async def test_add_channel_command_requires_auth(self, bot, db):
        """Тест что /add_channel требует аутентификации"""
        user = UserFactory.create(
            db,
            telegram_id=6400001,
            is_authenticated=False
        )
        
        update = create_mock_telegram_update(user_id=user.telegram_id)
        context = create_mock_telegram_context(args=["@test_channel"])
        
        await bot.add_channel_command(update, context)
        
        # Проверяем сообщение об ошибке
        call_args = update.message.reply_text.call_args[0]
        assert "аутентификацию" in call_args[0]
    
    @pytest.mark.asyncio
    async def test_add_channel_command_limit_reached(self, bot, db):
        """Тест достижения лимита каналов"""
        user = UserFactory.create(
            db,
            telegram_id=6500001,
            is_authenticated=True,
            max_channels=2
        )
        
        # Добавляем 2 канала (лимит достигнут)
        channel1 = ChannelFactory.create(db, channel_username="channel1")
        channel2 = ChannelFactory.create(db, channel_username="channel2")
        channel1.add_user(db, user)
        channel2.add_user(db, user)
        
        update = create_mock_telegram_update(user_id=user.telegram_id)
        context = create_mock_telegram_context(args=["@channel3"])
        
        await bot.add_channel_command(update, context)
        
        # Проверяем сообщение об ошибке
        call_args = update.message.reply_text.call_args[0]
        assert "лимит каналов" in call_args[0]
    
    @pytest.mark.asyncio
    async def test_my_channels_command(self, bot, db):
        """Тест команды /my_channels"""
        user = UserFactory.create(
            db,
            telegram_id=6600001,
            is_authenticated=True
        )
        
        # Добавляем несколько каналов
        channel1 = ChannelFactory.create(db, channel_username="channel1")
        channel2 = ChannelFactory.create(db, channel_username="channel2")
        channel1.add_user(db, user, is_active=True)
        channel2.add_user(db, user, is_active=False)
        
        update = create_mock_telegram_update(user_id=user.telegram_id)
        context = create_mock_telegram_context()
        
        await bot.my_channels_command(update, context)
        
        # Проверяем ответ
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        response_text = call_args[0][0]
        
        assert "channel1" in response_text
        assert "channel2" in response_text
        assert "Активен" in response_text
        assert "Неактивен" in response_text
    
    @pytest.mark.asyncio
    async def test_my_channels_command_empty(self, bot, db):
        """Тест /my_channels когда каналов нет"""
        user = UserFactory.create(
            db,
            telegram_id=6700001,
            is_authenticated=True
        )
        
        update = create_mock_telegram_update(user_id=user.telegram_id)
        context = create_mock_telegram_context()
        
        await bot.my_channels_command(update, context)
        
        # Проверяем сообщение о пустом списке
        call_args = update.message.reply_text.call_args[0]
        assert "нет добавленных каналов" in call_args[0]


@pytest.mark.unit
class TestBotHelpCommand:
    """Тесты для команды /help"""
    
    @pytest.fixture
    def bot(self):
        with patch('bot.Application.builder'):
            return TelegramBot()
    
    @pytest.mark.asyncio
    async def test_help_command_for_regular_user(self, bot, db):
        """Тест справки для обычного пользователя"""
        user = UserFactory.create(
            db,
            telegram_id=6800001,
            role="user"
        )
        
        update = create_mock_telegram_update(user_id=user.telegram_id)
        context = create_mock_telegram_context()
        
        await bot.help_command(update, context)
        
        call_args = update.message.reply_text.call_args[0]
        help_text = call_args[0]
        
        # Проверяем основные секции
        assert "/add_channel" in help_text
        assert "/ask" in help_text
        assert "/search" in help_text
        
        # Не должно быть админских команд
        assert "/admin_invite" not in help_text
    
    @pytest.mark.asyncio
    async def test_help_command_for_admin(self, bot, db):
        """Тест справки для администратора"""
        admin = UserFactory.create_admin(db, telegram_id=6900001)
        
        update = create_mock_telegram_update(user_id=admin.telegram_id)
        context = create_mock_telegram_context()
        
        await bot.help_command(update, context)
        
        call_args = update.message.reply_text.call_args[0]
        help_text = call_args[0]
        
        # Должны быть админские команды
        assert "/admin" in help_text
        assert "/admin_invite" in help_text
        assert "АДМИНИСТРАТОРА" in help_text


@pytest.mark.unit
class TestBotSubscriptionCommand:
    """Тесты для команды /subscription"""
    
    @pytest.mark.asyncio
    async def test_subscription_command_active(self, db):
        """Тест /subscription для активной подписки"""
        from bot_login_handlers_qr import subscription_command
        
        user = UserFactory.create_premium(
            db,
            telegram_id=7000001
        )
        
        update = create_mock_telegram_update(user_id=user.telegram_id)
        context = create_mock_telegram_context()
        
        await subscription_command(update, context)
        
        # Проверяем ответ
        call_args = update.message.reply_text.call_args[0]
        response = call_args[0]
        
        assert "Активна" in response
        assert "Premium" in response
        assert "дней" in response  # Количество дней до истечения
    
    @pytest.mark.asyncio
    async def test_subscription_command_expired(self, db):
        """Тест /subscription для истекшей подписки"""
        from bot_login_handlers_qr import subscription_command
        
        user = UserFactory.create(
            db,
            telegram_id=7100001,
            subscription_type="premium",
            subscription_expires=datetime.now(timezone.utc) - timedelta(days=1)
        )
        
        update = create_mock_telegram_update(user_id=user.telegram_id)
        context = create_mock_telegram_context()
        
        await subscription_command(update, context)
        
        # Проверяем предупреждение
        call_args = update.message.reply_text.call_args[0]
        assert "истекла" in call_args[0].lower()


@pytest.mark.unit
class TestBotCallbacks:
    """Тесты для callback обработчиков (inline кнопки)"""
    
    @pytest.fixture
    def bot(self):
        with patch('bot.Application.builder'):
            return TelegramBot()
    
    @pytest.mark.asyncio
    async def test_remove_channel_callback(self, bot, db):
        """Тест удаления канала через callback кнопку"""
        user = UserFactory.create(
            db,
            telegram_id=7200001,
            is_authenticated=True
        )
        channel = ChannelFactory.create(db, channel_username="to_remove")
        channel.add_user(db, user)
        
        # Mock callback query
        query = create_mock_callback_query(
            user_id=user.telegram_id,
            data=f"remove_{channel.id}"
        )
        
        await bot.remove_channel_by_id(query, channel.id)
        
        # Проверяем что канал удален
        db.refresh(user)
        assert channel not in user.channels
        
        # Проверяем сообщение
        query.edit_message_text.assert_called_once()

