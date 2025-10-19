# 🧪 Тесты Telegram Channel Parser

**Версия:** 3.3.0  
**Coverage Target:** 60-70%  
**Обновлено:** 14 октября 2025

---

## 📋 Структура тестов

```
tests/
├── conftest.py                    # Глобальные fixtures
├── utils/                         # Test utilities
│   ├── factories.py              # Factory pattern для моделей
│   ├── mocks.py                  # Переиспользуемые моки
│   └── fixtures_data.py          # Тестовые данные
│
├── test_models.py                # Models (User, Channel, Post, Group)
├── test_qr_auth_manager.py       # QR авторизация
├── test_shared_auth_manager.py   # Shared credentials auth
├── test_admin_panel_manager.py   # Admin sessions
│
├── test_bot_commands.py          # Основные команды бота
├── test_bot_login_handlers.py    # QR login handlers
├── test_bot_admin_handlers.py    # Админские команды
├── test_bot_rag_commands.py      # RAG команды (/ask, /search)
├── test_bot_voice_handlers.py    # Голосовые команды
├── test_bot_group_commands.py    # Group команды
│
├── test_parser_service.py        # Парсинг каналов
├── test_tagging_service.py       # AI тегирование
├── test_cleanup_service.py       # Retention cleanup
├── test_voice_transcription.py   # SaluteSpeech API
├── test_group_digest_generator.py # n8n workflows для групп
│
├── test_api_main.py              # FastAPI endpoints (main.py)
├── test_api_admin.py             # Admin API endpoints
├── test_api_rag.py               # RAG API endpoints
│
├── rag_service/                  # RAG service tests
│   ├── test_vector_db.py        # Qdrant operations
│   ├── test_embeddings.py       # GigaChat embeddings
│   ├── test_indexer.py          # Индексация постов
│   ├── test_search.py           # Векторный поиск
│   └── test_generator.py        # RAG генерация ответов
│
├── integration/                  # Integration tests
│   ├── test_auth_flow.py        # Полный QR auth flow
│   ├── test_parser_flow.py      # Парсинг → Тегирование
│   └── test_rag_flow.py         # Индексация → Поиск → RAG
│
├── test_many_to_many.py         # Legacy: many-to-many migration
├── test_retention_system.py     # Legacy: retention system
└── run_tests.sh                 # Helper скрипт для запуска
```

---

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
cd /home/ilyasni/n8n-server/n8n-installer/telethon

# Установить test dependencies
pip install -r requirements-test.txt
```

### 2. Запуск тестов

```bash
# Все тесты
pytest tests/ -v

# Только unit тесты (быстро, с моками)
pytest tests/ -m "unit" -v

# Только integration тесты (медленно, требуют сервисы)
pytest tests/ -m "integration" -v

# С coverage отчетом
pytest tests/ --cov=. --cov-report=html

# Используя helper скрипт
chmod +x tests/run_tests.sh
./tests/run_tests.sh unit       # Unit тесты
./tests/run_tests.sh coverage   # С coverage
./tests/run_tests.sh fast       # Параллельно
```

---

## 🏷️ Pytest Markers

Тесты категоризированы с помощью markers:

```python
@pytest.mark.unit          # Unit тесты (изолированные, моки)
@pytest.mark.integration   # Integration тесты (реальные сервисы)
@pytest.mark.slow          # Медленные тесты (>1 сек)
@pytest.mark.auth          # Authentication тесты
@pytest.mark.rag           # RAG system тесты
@pytest.mark.groups        # Groups functionality
@pytest.mark.voice         # Voice transcription
@pytest.mark.external_api  # Требуют внешние API
```

**Примеры фильтрации:**

```bash
# Только auth тесты
pytest tests/ -m "auth" -v

# Unit тесты без slow
pytest tests/ -m "unit and not slow" -v

# RAG тесты
pytest tests/ -m "rag" -v
```

---

## 📊 Coverage

**Target:** 60-70% code coverage

**Запуск с coverage:**

```bash
pytest tests/ --cov=. --cov-report=html --cov-report=term-missing

# Открыть HTML отчет
open htmlcov/index.html
```

**Конфигурация:** `.coveragerc`

**Исключения:**
- `tests/` - сами тесты
- `scripts/migrations/` - миграции
- `scripts/setup/` - setup скрипты
- Deprecated файлы

---

## 🔧 Конфигурация

### `pytest.ini`

Основные настройки:
- `asyncio_mode = auto` - автоматический async support
- `--cov-fail-under=60` - минимум 60% coverage
- Timeout 30 секунд для тестов

### `.coveragerc`

Coverage конфигурация с исключениями для migrations и tests.

---

## 🧪 Test Fixtures

### Database Fixtures

```python
@pytest.fixture
def db_session(db_engine):
    """Function-scoped DB session с auto-rollback"""
    # Используется в большинстве тестов
```

### Factory Fixtures

```python
@pytest.fixture
def create_test_user(db_session):
    """Factory для User объектов"""
    
@pytest.fixture
def create_test_channel(db_session):
    """Factory для Channel объектов"""
```

### Mock Fixtures

```python
@pytest.fixture
def mock_telegram_update():
    """Mock Telegram Update"""

@pytest.fixture
def mock_telethon_client():
    """Mock Telethon TelegramClient"""

@pytest.fixture
def redis_client():
    """FakeRedis для unit тестов"""
```

### External API Mocks

```python
@pytest.fixture
def mock_gigachat_api(httpx_mock):
    """Mock GigaChat API responses"""

@pytest.fixture
def mock_salutespeech_api(httpx_mock):
    """Mock SaluteSpeech voice API"""

@pytest.fixture
def mock_n8n_webhooks(httpx_mock):
    """Mock n8n workflow webhooks"""
```

---

## 📝 Примеры использования

### Простой unit тест

```python
@pytest.mark.unit
def test_user_creation(db):
    from tests.utils.factories import UserFactory
    
    user = UserFactory.create(db, telegram_id=123)
    
    assert user.telegram_id == 123
    assert user.created_at.tzinfo == timezone.utc
```

### Async тест с моками

```python
@pytest.mark.unit
@pytest.mark.asyncio
async def test_ask_command(bot, db, mock_httpx):
    user = UserFactory.create(db, is_authenticated=True)
    
    # Mock RAG service
    mock_httpx.post.return_value = {"answer": "Test"}
    
    await bot.ask_command(update, context)
    
    assert update.message.reply_text.called
```

### Integration тест

```python
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
async def test_full_auth_flow(db, redis_client):
    # Полный flow с реальными Redis + PostgreSQL
    ...
```

---

## 🐛 Troubleshooting

### Проблема: ImportError при запуске тестов

**Решение:**
```bash
# Запускать из корня telethon/
cd /home/ilyasni/n8n-server/n8n-installer/telethon
export PYTHONPATH=$PWD:$PWD/rag_service
pytest tests/
```

### Проблема: Database connection errors

**Решение:**
- Unit тесты используют SQLite in-memory (не требуют PostgreSQL)
- Integration тесты требуют PostgreSQL:
  ```bash
  export TELEGRAM_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/test_db"
  ```

### Проблема: Redis connection errors

**Решение:**
- Unit тесты используют `fakeredis` (не требуют Redis)
- Integration тесты требуют Redis:
  ```bash
  docker run -d -p 6379:6379 redis:alpine
  ```

### Проблема: Async warnings

**Решение:**
- Убедитесь что используется `@pytest.mark.asyncio` для async тестов
- Проверьте `pytest.ini`: `asyncio_mode = auto`

---

## 📈 CI/CD Integration

Тесты готовы для интеграции в CI/CD pipeline:

```yaml
# GitHub Actions example
- name: Run tests
  run: |
    pip install -r requirements-test.txt
    pytest tests/ -m "unit" --cov=. --cov-report=xml
    
- name: Upload coverage
  uses: codecov/codecov-action@v3
```

---

## 📚 Best Practices

✅ **Следуем из Cursor Rules:**
1. Все datetime с `timezone.utc` ✅
2. PostgreSQL only (SQLite только in-memory для unit) ✅
3. User ID filtering во всех multi-user тестах ✅
4. Async/await everywhere ✅
5. Моки внешних API через pytest-httpx ✅
6. Factory pattern для тестовых данных ✅

✅ **Дополнительно:**
- Изоляция тестов (auto-rollback DB)
- Clear naming (test_<what>_<scenario>)
- AAA pattern (Arrange, Act, Assert)
- Fixtures для переиспользования
- Marks для категоризации

---

## 🎯 Coverage Goals

| Компонент | Target | Приоритет |
|-----------|--------|-----------|
| Models | 80%+ | 🔴 Critical |
| Auth (QR + Shared) | 75%+ | 🔴 Critical |
| Bot handlers | 65%+ | 🟠 High |
| Parser service | 70%+ | 🟠 High |
| RAG service | 60%+ | 🟡 Medium |
| Groups | 50%+ | 🟢 Low |
| Voice | 50%+ | 🟢 Low |

**Общий target:** 60-70%

---

## 🔗 Полезные команды

```bash
# Запуск конкретного файла
pytest tests/test_models.py -v

# Запуск конкретного теста
pytest tests/test_models.py::TestUserModel::test_user_creation_with_timezone -v

# Запуск с выводом print statements
pytest tests/ -v -s

# Остановка на первой ошибке
pytest tests/ -x

# Повторный запуск только failed тестов
pytest tests/ --lf

# Показать 10 slowest тестов
pytest tests/ --durations=10

# Параллельный запуск (требует pytest-xdist)
pytest tests/ -n auto
```

---

## 📞 Поддержка

**Проблемы с тестами?**
1. Проверьте `.env` файл
2. Убедитесь что все зависимости установлены
3. Запустите отдельно unit и integration тесты
4. Проверьте логи: `pytest tests/ -v -s`

---

**Автор:** AI Assistant  
**Дата создания:** 14 октября 2025  
**Статус:** ✅ Готово к использованию
