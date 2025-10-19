"""
Переиспользуемые моки для Telegram Bot API и Telethon
"""

import random
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock
from typing import Optional


def create_mock_telegram_user(
    user_id: int = 123456789,
    username: str = "testuser",
    first_name: str = "Test",
    last_name: str = "User",
    is_bot: bool = False
):
    """Создать mock объект Telegram User"""
    user = MagicMock()
    user.id = user_id
    user.username = username
    user.first_name = first_name
    user.last_name = last_name
    user.is_bot = is_bot
    return user


def create_mock_telegram_message(
    text: str = "Test message",
    user_id: int = 123456789,
    chat_id: int = 123456789,
    message_id: int = 1,
    username: str = "testuser"
):
    """Создать mock объект Telegram Message"""
    message = MagicMock()
    message.text = text
    message.chat.id = chat_id
    message.message_id = message_id
    message.date = datetime.now(timezone.utc)
    
    # User
    message.from_user = create_mock_telegram_user(
        user_id=user_id,
        username=username
    )
    
    # Async методы
    message.reply_text = AsyncMock()
    message.chat.send_action = AsyncMock()
    
    return message


def create_mock_telegram_update(
    message_text: str = "Test message",
    user_id: int = 123456789,
    callback_data: Optional[str] = None
):
    """Создать mock объект Telegram Update"""
    update = MagicMock()
    
    # User
    update.effective_user = create_mock_telegram_user(user_id=user_id)
    
    # Message
    if callback_data is None:
        update.message = create_mock_telegram_message(
            text=message_text,
            user_id=user_id
        )
        update.callback_query = None
    else:
        # Callback query
        update.message = None
        update.callback_query = create_mock_callback_query(
            user_id=user_id,
            data=callback_data
        )
    
    return update


def create_mock_telegram_context(args: list = None, user_data: dict = None):
    """Создать mock объект CallbackContext"""
    context = MagicMock()
    context.args = args or []
    context.user_data = user_data or {}
    context.chat_data = {}
    context.bot_data = {}
    context.bot = MagicMock()
    return context


def create_mock_callback_query(
    user_id: int = 123456789,
    data: str = "test_callback",
    message_id: int = 1
):
    """Создать mock объект CallbackQuery"""
    query = MagicMock()
    query.from_user = create_mock_telegram_user(user_id=user_id)
    query.data = data
    query.id = "test_callback_query_id"
    
    # Message
    query.message = MagicMock()
    query.message.message_id = message_id
    query.message.chat_id = user_id
    query.message.reply_text = AsyncMock()
    
    # Async методы
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    
    return query


def create_mock_voice_message(
    duration: int = 5,
    file_id: str = "test_voice_file_id",
    file_size: int = 10000
):
    """Создать mock объект Voice для голосовых сообщений"""
    voice = MagicMock()
    voice.duration = duration
    voice.file_id = file_id
    voice.file_size = file_size
    voice.mime_type = "audio/ogg"
    
    # Mock file download
    voice_file = MagicMock()
    voice_file.download_as_bytearray = AsyncMock(return_value=bytearray(b"fake_audio_data"))
    voice.get_file = AsyncMock(return_value=voice_file)
    
    return voice


def create_mock_telethon_client(
    is_connected: bool = True,
    is_authorized: bool = True
):
    """Создать mock Telethon TelegramClient"""
    client = AsyncMock()
    
    # Connection state
    client.is_connected = MagicMock(return_value=is_connected)
    client.is_user_authorized = AsyncMock(return_value=is_authorized)
    
    # Basic operations
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    
    # Auth operations
    client.send_code_request = AsyncMock()
    client.sign_in = AsyncMock()
    client.qr_login = AsyncMock()
    
    # Data operations
    client.get_entity = AsyncMock()
    client.iter_messages = AsyncMock()
    client.iter_dialogs = AsyncMock()
    
    return client


def create_mock_telethon_message(
    text: str = "Test message",
    message_id: int = 1,
    date: Optional[datetime] = None,
    sender_username: str = "testuser"
):
    """Создать mock Telethon Message для iter_messages"""
    message = MagicMock()
    message.id = message_id
    message.text = text
    message.date = date or datetime.now(timezone.utc)
    message.views = random.randint(100, 10000)
    
    # Sender
    message.sender = MagicMock()
    message.sender.username = sender_username
    message.sender.first_name = "Test"
    
    # Chat
    message.chat = MagicMock()
    message.chat.username = "test_channel"
    
    return message


def create_mock_redis_client():
    """Создать mock Redis client"""
    redis_mock = MagicMock()
    
    # Базовые операции
    redis_mock.get = MagicMock(return_value=None)
    redis_mock.set = MagicMock(return_value=True)
    redis_mock.setex = MagicMock(return_value=True)
    redis_mock.delete = MagicMock(return_value=1)
    redis_mock.keys = MagicMock(return_value=[])
    redis_mock.ping = MagicMock(return_value=True)
    redis_mock.flushall = MagicMock(return_value=True)
    
    return redis_mock


def create_mock_qdrant_client():
    """Создать mock Qdrant client"""
    qdrant_mock = MagicMock()
    
    # Collection operations
    qdrant_mock.create_collection = AsyncMock()
    qdrant_mock.get_collection = AsyncMock(return_value={"vectors_count": 0, "points_count": 0})
    qdrant_mock.delete_collection = AsyncMock()
    qdrant_mock.collection_exists = AsyncMock(return_value=False)
    
    # Point operations
    qdrant_mock.upsert = AsyncMock()
    qdrant_mock.search = AsyncMock(return_value=[])
    qdrant_mock.delete = AsyncMock()
    qdrant_mock.scroll = AsyncMock(return_value=([], None))
    
    return qdrant_mock


def create_mock_httpx_response(
    status_code: int = 200,
    json_data: dict = None,
    text: str = ""
):
    """Создать mock httpx Response"""
    response = MagicMock()
    response.status_code = status_code
    response.text = text
    response.json = MagicMock(return_value=json_data or {})
    response.raise_for_status = MagicMock()
    
    return response

