"""
Глобальные fixtures для тестов
Настройка БД, Redis, моков внешних сервисов
"""

import asyncio
import os
import pytest
import fakeredis
from datetime import datetime, timezone, timedelta
from typing import Generator, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Устанавливаем тестовые переменные окружения ПЕРЕД импортом моделей
os.environ['TELEGRAM_DATABASE_URL'] = 'postgresql://postgres:postgres@localhost:5432/test_telegram'
os.environ['BOT_TOKEN'] = 'test_bot_token'
os.environ['MASTER_API_ID'] = '12345678'
os.environ['MASTER_API_HASH'] = 'test_api_hash'
os.environ['ENCRYPTION_KEY'] = 'WX7wmC8298QkVh1acJr0h8roQ16M4am8qh1h4q35BqQ='
os.environ['REDIS_HOST'] = 'localhost'
os.environ['REDIS_PORT'] = '6379'

from models import Base, User, Channel, Post, Group, InviteCode, SubscriptionHistory
from database import get_db


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def db_engine():
    """
    Session-scoped database engine для тестов
    Использует in-memory SQLite для скорости (только для unit тестов)
    """
    # Для unit тестов используем SQLite in-memory (быстро)
    # ВАЖНО: Используем специальные настройки для SQLite чтобы эмулировать PostgreSQL
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Включаем foreign keys для SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    
    # Создаем все таблицы
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # Cleanup
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator[Session, None, None]:
    """
    Function-scoped database session
    Автоматически rollback после каждого теста
    """
    connection = db_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()
    
    yield session
    
    # Rollback транзакции после теста
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def db(db_session):
    """Alias для db_session (короче писать в тестах)"""
    return db_session


@pytest.fixture(scope="function", autouse=True)
def patch_all_session_locals(db):
    """
    Глобальный патч SessionLocal для всех модулей проекта.
    Автоматически заменяет все вызовы SessionLocal() на тестовую БД.
    """
    modules_to_patch = [
        'database.SessionLocal',
        'bot.SessionLocal',
        'bot_login_handlers_qr.SessionLocal',
        'bot_admin_handlers.SessionLocal',
        'parser_service.SessionLocal',
        'tagging_service.SessionLocal',
        'cleanup_service.SessionLocal',
        'group_monitor_service.SessionLocal',
        'shared_auth_manager.SessionLocal',
        'qr_auth_manager.SessionLocal',
    ]
    
    patches = []
    for module_path in modules_to_patch:
        try:
            p = patch(module_path, return_value=db)
            p.start()
            patches.append(p)
        except:
            pass  # Модуль может не использовать SessionLocal
    
    yield
    
    # Останавливаем все патчи
    for p in patches:
        p.stop()


# ============================================================================
# Redis Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def redis_client():
    """
    FakeRedis клиент для unit тестов
    Эмулирует Redis без реального сервера
    """
    fake_redis = fakeredis.FakeRedis(decode_responses=True)
    yield fake_redis
    # Очистка после теста
    fake_redis.flushall()


@pytest.fixture(scope="function")
def mock_redis(mocker, redis_client):
    """
    Мок Redis клиента в модулях проекта
    Автоматически патчит redis.Redis на FakeRedis
    """
    mocker.patch('redis.Redis', return_value=redis_client)
    return redis_client


@pytest.fixture(scope="session", autouse=True)
def mock_redis_for_imports():
    """
    Session-wide мок Redis для импортов модулей (admin_panel_manager и др.)
    Автоматически применяется ко всем тестам
    """
    import fakeredis
    fake = fakeredis.FakeRedis(decode_responses=True)
    
    with patch('redis.Redis', return_value=fake):
        yield fake


# ============================================================================
# Telegram Bot Mocks
# ============================================================================

@pytest.fixture
def mock_telegram_user():
    """Mock объект Telegram User"""
    user = MagicMock()
    user.id = 123456789
    user.first_name = "Test"
    user.last_name = "User"
    user.username = "testuser"
    user.is_bot = False
    return user


@pytest.fixture
def mock_telegram_message(mock_telegram_user):
    """Mock объект Telegram Message"""
    message = MagicMock()
    message.from_user = mock_telegram_user
    message.chat.id = 123456789
    message.message_id = 1
    message.text = "Test message"
    message.date = datetime.now(timezone.utc)
    
    # Mock reply methods
    message.reply_text = AsyncMock()
    message.chat.send_action = AsyncMock()
    
    return message


@pytest.fixture
def mock_telegram_update(mock_telegram_message, mock_telegram_user):
    """Mock объект Telegram Update"""
    update = MagicMock()
    update.effective_user = mock_telegram_user
    update.message = mock_telegram_message
    update.callback_query = None
    return update


@pytest.fixture
def mock_telegram_context():
    """Mock объект CallbackContext"""
    context = MagicMock()
    context.args = []
    context.user_data = {}
    context.chat_data = {}
    context.bot_data = {}
    context.bot = MagicMock()
    return context


@pytest.fixture
def mock_callback_query(mock_telegram_user):
    """Mock объект CallbackQuery для inline кнопок"""
    query = MagicMock()
    query.from_user = mock_telegram_user
    query.data = "test_callback"
    query.message = MagicMock()
    query.message.chat_id = 123456789
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    return query


# ============================================================================
# Telethon Client Mocks
# ============================================================================

@pytest.fixture
def mock_telethon_client():
    """Mock Telethon TelegramClient"""
    client = AsyncMock()
    client.is_connected = MagicMock(return_value=True)
    client.is_user_authorized = AsyncMock(return_value=True)
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client.send_code_request = AsyncMock()
    client.sign_in = AsyncMock()
    client.get_entity = AsyncMock()
    client.iter_messages = AsyncMock()
    client.iter_dialogs = AsyncMock()
    return client


# ============================================================================
# HTTP Mocks для внешних API
# ============================================================================

@pytest.fixture
def mock_httpx_client(mocker):
    """
    Mock для httpx.AsyncClient
    Используется для моков всех HTTP запросов к внешним API
    """
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock()
    
    mocker.patch('httpx.AsyncClient', return_value=mock_client)
    
    return mock_client


@pytest.fixture
def mock_gigachat_api(httpx_mock):
    """Mock GigaChat API через gpt2giga-proxy"""
    # Embeddings endpoint
    httpx_mock.add_response(
        url="http://gpt2giga-proxy:8090/v1/embeddings",
        method="POST",
        json={
            "data": [{
                "embedding": [0.1] * 1024,  # GigaChat embeddings dimension
                "index": 0
            }],
            "model": "EmbeddingsGigaR",
            "usage": {"prompt_tokens": 10, "total_tokens": 10}
        }
    )
    
    # Chat completion endpoint
    httpx_mock.add_response(
        url="http://gpt2giga-proxy:8090/v1/chat/completions",
        method="POST",
        json={
            "choices": [{
                "message": {
                    "content": "Test AI response",
                    "role": "assistant"
                },
                "finish_reason": "stop",
                "index": 0
            }],
            "model": "GigaChat-Lite",
            "usage": {"prompt_tokens": 50, "completion_tokens": 20}
        }
    )


@pytest.fixture
def mock_openrouter_api(httpx_mock):
    """Mock OpenRouter API"""
    httpx_mock.add_response(
        url="https://openrouter.ai/api/v1/chat/completions",
        method="POST",
        json={
            "choices": [{
                "message": {
                    "content": "OpenRouter test response",
                    "role": "assistant"
                }
            }]
        }
    )


@pytest.fixture
def mock_salutespeech_api(httpx_mock):
    """Mock SaluteSpeech API для voice transcription"""
    # OAuth2 token endpoint
    httpx_mock.add_response(
        url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
        method="POST",
        json={
            "access_token": "test_access_token",
            "expires_at": int((datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp())
        }
    )
    
    # Upload endpoint
    httpx_mock.add_response(
        url="https://smartspeech.sber.ru/rest/v1/data:upload",
        method="POST",
        json={"result": "test_file_id_12345"}
    )
    
    # Recognize endpoint
    httpx_mock.add_response(
        url="https://smartspeech.sber.ru/rest/v1/speech:async_recognize",
        method="POST",
        json={"result": "test_task_id_67890"}
    )
    
    # Status endpoint (completed)
    httpx_mock.add_response(
        url="https://smartspeech.sber.ru/rest/v1/task:get",
        method="POST",
        json={
            "result": {
                "id": "test_task_id_67890",
                "status": "DONE",
                "response_file_id": "test_response_file_id"
            }
        }
    )
    
    # Download result endpoint
    httpx_mock.add_response(
        url="https://smartspeech.sber.ru/rest/v1/data:download",
        method="POST",
        json={
            "result": [{
                "normalized_text": "тестовая транскрипция голосового сообщения",
                "confidence": 0.95
            }]
        }
    )


@pytest.fixture
def mock_n8n_webhooks(httpx_mock):
    """Mock n8n webhooks для groups и voice"""
    # Group digest workflow
    httpx_mock.add_response(
        url="http://n8n:5678/webhook/group-digest",
        method="POST",
        json={
            "summary": "Test group digest summary",
            "topics": ["Topic 1", "Topic 2"],
            "key_speakers": ["Alice", "Bob"],
            "message_count": 10
        }
    )
    
    # Mention analyzer workflow
    httpx_mock.add_response(
        url="http://n8n:5678/webhook/mention-analyzer",
        method="POST",
        json={
            "reason": "Test mention reason",
            "context": "Test context",
            "urgency": "medium"
        }
    )
    
    # Voice classifier workflow
    httpx_mock.add_response(
        url="http://n8n:5678/webhook/voice-classify",
        method="POST",
        json={
            "command": "ask",
            "confidence": 0.85,
            "reasoning": "Question detected in transcription"
        }
    )


@pytest.fixture
def mock_qdrant_client(mocker):
    """Mock Qdrant client"""
    mock_qdrant = MagicMock()
    
    # Collection operations
    mock_qdrant.create_collection = AsyncMock()
    mock_qdrant.get_collection = AsyncMock(return_value={"vectors_count": 0})
    mock_qdrant.delete_collection = AsyncMock()
    
    # Point operations
    mock_qdrant.upsert = AsyncMock()
    mock_qdrant.search = AsyncMock(return_value=[])
    mock_qdrant.delete = AsyncMock()
    
    mocker.patch('qdrant_client.QdrantClient', return_value=mock_qdrant)
    
    return mock_qdrant


@pytest.fixture
def mock_crawl4ai_api(httpx_mock):
    """Mock Crawl4AI web scraping API"""
    httpx_mock.add_response(
        url="http://crawl4ai:11235/crawl",
        method="POST",
        json={
            "success": True,
            "cleaned_html": "<p>Test content from scraped page</p>",
            "markdown": "Test content from scraped page",
            "links": ["https://example.com/link1"],
            "word_count": 50
        }
    )


# ============================================================================
# Factory Fixtures
# ============================================================================

@pytest.fixture
def create_test_user(db_session):
    """Factory для создания тестовых пользователей"""
    def _create_user(
        telegram_id: int = None,
        username: str = "testuser",
        first_name: str = "Test",
        role: str = "user",
        subscription_type: str = "free",
        is_authenticated: bool = False,
        **kwargs
    ) -> User:
        if telegram_id is None:
            # Генерируем уникальный ID
            import random
            telegram_id = random.randint(100000000, 999999999)
        
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            role=role,
            subscription_type=subscription_type,
            is_authenticated=is_authenticated,
            max_channels=kwargs.get('max_channels', 3),
            **kwargs
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user
    
    return _create_user


@pytest.fixture
def create_test_channel(db_session):
    """Factory для создания тестовых каналов"""
    def _create_channel(
        channel_username: str = None,
        channel_id: int = None,
        channel_title: str = "Test Channel",
        **kwargs
    ) -> Channel:
        if channel_username is None:
            import random
            channel_username = f"test_channel_{random.randint(1000, 9999)}"
        
        if channel_id is None:
            import random
            channel_id = random.randint(1000000000, 9999999999)
        
        channel = Channel(
            channel_username=channel_username,
            channel_id=channel_id,
            channel_title=channel_title,
            **kwargs
        )
        db_session.add(channel)
        db_session.commit()
        db_session.refresh(channel)
        return channel
    
    return _create_channel


@pytest.fixture
def create_test_post(db_session):
    """Factory для создания тестовых постов"""
    def _create_post(
        user_id: int,
        channel_id: int,
        text: str = "Test post content",
        posted_at: datetime = None,
        **kwargs
    ) -> Post:
        if posted_at is None:
            posted_at = datetime.now(timezone.utc)
        
        post = Post(
            user_id=user_id,
            channel_id=channel_id,
            text=text,
            posted_at=posted_at,
            telegram_message_id=kwargs.get('telegram_message_id', 1),
            url=kwargs.get('url', f"https://t.me/channel/{kwargs.get('telegram_message_id', 1)}"),
            **kwargs
        )
        db_session.add(post)
        db_session.commit()
        db_session.refresh(post)
        return post
    
    return _create_post


@pytest.fixture
def create_test_group(db_session):
    """Factory для создания тестовых групп"""
    def _create_group(
        group_id: int = None,
        group_title: str = "Test Group",
        group_username: str = None,
        **kwargs
    ) -> Group:
        if group_id is None:
            import random
            group_id = -random.randint(1000000000, 9999999999)
        
        group = Group(
            group_id=group_id,
            group_title=group_title,
            group_username=group_username,
            **kwargs
        )
        db_session.add(group)
        db_session.commit()
        db_session.refresh(group)
        return group
    
    return _create_group


@pytest.fixture
def create_test_invite(db_session, create_test_user):
    """Factory для создания тестовых invite codes"""
    def _create_invite(
        code: str = None,
        created_by: int = None,
        subscription_type: str = "trial",
        expires_days: int = 7,
        **kwargs
    ) -> InviteCode:
        if code is None:
            code = InviteCode.generate_code()
        
        if created_by is None:
            # Создаем админа
            admin = create_test_user(role="admin")
            created_by = admin.id
        
        invite = InviteCode(
            code=code,
            created_by=created_by,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=expires_days),
            default_subscription=subscription_type,
            max_uses=kwargs.get('max_uses', 1),
            uses_count=kwargs.get('uses_count', 0),
            **kwargs
        )
        db_session.add(invite)
        db_session.commit()
        db_session.refresh(invite)
        return invite
    
    return _create_invite


# ============================================================================
# Async Event Loop
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """
    Session-scoped event loop для async тестов
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Environment Mocks
# ============================================================================

@pytest.fixture
def clean_env(monkeypatch):
    """Очищает переменные окружения для изолированных тестов"""
    # Сохраняем критичные переменные
    critical_vars = ['TELEGRAM_DATABASE_URL', 'BOT_TOKEN', 'MASTER_API_ID', 'MASTER_API_HASH']
    saved_env = {k: os.environ.get(k) for k in critical_vars}
    
    yield monkeypatch
    
    # Восстанавливаем после теста
    for k, v in saved_env.items():
        if v is not None:
            os.environ[k] = v


# ============================================================================
# Sample Data Fixtures
# ============================================================================

@pytest.fixture
def sample_post_text():
    """Пример текста поста для тестов"""
    return """
    🚀 Новая технология в области искусственного интеллекта!
    
    Исследователи разработали революционный подход к обработке естественного языка.
    Это может изменить индустрию навсегда.
    
    #AI #технологии #инновации
    https://example.com/article
    """


@pytest.fixture
def sample_messages_for_digest():
    """Примеры сообщений из группы для тестирования дайджестов"""
    messages = []
    base_time = datetime.now(timezone.utc) - timedelta(hours=12)
    
    for i in range(10):
        msg = MagicMock()
        msg.id = i + 1
        msg.text = f"Test message {i + 1} from group discussion"
        msg.date = base_time + timedelta(minutes=i * 10)
        msg.sender = MagicMock()
        msg.sender.username = f"user_{i % 3}"  # 3 разных пользователя
        msg.sender.first_name = f"User {i % 3}"
        messages.append(msg)
    
    return messages


# ============================================================================
# Cleanup Helpers
# ============================================================================

@pytest.fixture(autouse=True)
def reset_singletons():
    """
    Сбрасывает глобальные singleton объекты после каждого теста
    Предотвращает state pollution между тестами
    """
    yield
    
    # Очищаем активные клиенты в shared_auth_manager
    try:
        from shared_auth_manager import shared_auth_manager
        shared_auth_manager.active_clients.clear()
    except:
        pass
    
    # Очищаем QR сессии
    try:
        from qr_auth_manager import qr_auth_manager
        if hasattr(qr_auth_manager, 'active_sessions'):
            qr_auth_manager.active_sessions.clear()
    except:
        pass


# ============================================================================
# Markers для фильтрации тестов
# ============================================================================

def pytest_configure(config):
    """Регистрация custom markers"""
    config.addinivalue_line("markers", "unit: Unit tests with mocks")
    config.addinivalue_line("markers", "integration: Integration tests with real services")
    config.addinivalue_line("markers", "slow: Tests that take >1 second")
    config.addinivalue_line("markers", "external_api: Tests requiring external API")
    config.addinivalue_line("markers", "auth: Authentication tests")
    config.addinivalue_line("markers", "rag: RAG system tests")
    config.addinivalue_line("markers", "groups: Groups functionality tests")
    config.addinivalue_line("markers", "voice: Voice transcription tests")

