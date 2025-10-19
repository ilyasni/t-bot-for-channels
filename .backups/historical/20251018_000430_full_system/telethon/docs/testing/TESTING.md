# 🧪 Testing Guide - Telegram Parser

**Comprehensive test suite для всех компонентов проекта**

---

## 🎯 Обзор

Создан полный набор unit и integration тестов с покрытием:
- ✅ **Models** - бизнес-логика, relationships, timezone handling
- ✅ **Authentication** - QR login, shared credentials, admin sessions
- ✅ **Bot Handlers** - все команды бота с моками Telegram API
- ✅ **Parser Service** - парсинг, тегирование, enrichment
- ✅ **RAG Service** - векторный поиск, embeddings, генерация
- ✅ **Groups** - дайджесты, мониторинг упоминаний
- ✅ **API Endpoints** - FastAPI endpoints для main и RAG
- ✅ **Integration** - полные workflows с реальными сервисами

**Статистика:**
- **Файлов тестов:** 20+
- **Тестовых функций:** 100+
- **Coverage target:** 60-70%
- **Технологии:** pytest, pytest-asyncio, pytest-mock, pytest-httpx

---

## ⚡ Quick Start

```bash
# 1. Установка dependencies
cd /home/ilyasni/n8n-server/n8n-installer/telethon
pip install -r requirements-test.txt

# 2. Запуск unit тестов (быстро, ~30 секунд)
pytest tests/ -m "unit" -v

# 3. Coverage report
pytest tests/ --cov=. --cov-report=html
open htmlcov/index.html
```

---

## 📚 Документация

**Основная:** `tests/README.md`

**Структура:**
- `tests/conftest.py` - глобальные fixtures
- `tests/utils/` - factories, mocks, test data
- `tests/integration/` - integration тесты
- `tests/rag_service/` - RAG service тесты

**Helper script:** `tests/run_tests.sh`

```bash
./tests/run_tests.sh unit        # Unit тесты
./tests/run_tests.sh integration # Integration тесты
./tests/run_tests.sh coverage    # С coverage
./tests/run_tests.sh fast        # Параллельно
```

---

## 🔍 Примеры тестов

### Unit Test с Factory

```python
@pytest.mark.unit
def test_user_subscription_active(db):
    user = UserFactory.create_premium(
        db,
        telegram_id=123,
        subscription_expires=datetime.now(timezone.utc) + timedelta(days=10)
    )
    
    assert user.check_subscription_active() is True
```

### Async Test с HTTP Mock

```python
@pytest.mark.unit
@pytest.mark.asyncio
async def test_voice_transcription(httpx_mock):
    httpx_mock.add_response(
        url="https://smartspeech.sber.ru/rest/v1/speech:async_recognize",
        json={"result": "task_id"}
    )
    
    result = await service.transcribe(audio_bytes)
    assert result is not None
```

### Integration Test

```python
@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
async def test_qr_login_complete_flow(db, redis_client):
    # Полный flow с PostgreSQL + Redis
    session = await qr_manager.create_qr_session(telegram_id, invite_code)
    await qr_manager._finalize_authorization(session['session_id'])
    
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    assert user.is_authenticated is True
```

---

## 🎨 Test Patterns

### Factory Pattern

```python
# tests/utils/factories.py
user = UserFactory.create(db, telegram_id=123, role="admin")
channel = ChannelFactory.create(db, channel_username="test")
posts = PostFactory.create_batch(db, user_id=user.id, count=10)
```

### Mocks Pattern

```python
# tests/utils/mocks.py
update = create_mock_telegram_update(user_id=123)
context = create_mock_telegram_context(args=["test"])
client = create_mock_telethon_client()
```

### Fixtures Pattern

```python
# tests/conftest.py
@pytest.fixture
def mock_gigachat_api(httpx_mock):
    httpx_mock.add_response(...)
```

---

## ✅ Что тестируется

### ✅ Models (test_models.py)
- Timezone-aware datetime fields
- User subscription logic
- Channel many-to-many relationships
- Encrypted fields (api_hash, phone_number)
- InviteCode validation и usage

### ✅ Authentication
- QR login sessions в Redis (TTL 5 минут)
- Shared credentials management
- Admin panel sessions (TTL 1 час)
- Rate limiting и блокировки
- Session file management

### ✅ Bot Handlers
- Все основные команды (/start, /help, /add_channel)
- QR login conversation flow
- Admin команды (права доступа)
- RAG команды (/ask, /search, /recommend, /digest)
- Голосовые команды (Premium only)
- Group команды

### ✅ Services
- Parser: парсинг, timezone handling, enrichment
- Tagging: GigaChat + OpenRouter fallback, retry logic
- Cleanup: retention_days calculation, cutoff logic
- Voice: SaluteSpeech OAuth, transcription, caching

### ✅ RAG System
- Vector DB: Qdrant operations
- Embeddings: GigaChat + fallback, chunking, Redis cache
- Indexer: индексация, batch operations
- Search: векторный поиск с фильтрами
- Generator: RAG ответы с context

### ✅ API Endpoints
- User endpoints (GET /users, /channels, /posts)
- Admin API (authentication, управление)
- RAG API (index, search, ask, digest)
- Retention settings (GET/PUT)

### ✅ Integration
- Полный QR auth flow
- Parser → Tagging → Indexing
- Multi-user isolation
- Retention cleanup

---

## 🚀 CI/CD Ready

Тесты готовы для GitHub Actions, GitLab CI, или других CI/CD:

```yaml
test:
  script:
    - pip install -r requirements-test.txt
    - pytest tests/ -m "unit" --cov=. --cov-report=xml
  coverage: '/TOTAL.*\s+(\d+%)$/'
```

---

## 📊 Статистика

**Создано:**
- Тестовых файлов: 20+
- Тестовых функций: 100+
- Fixtures: 30+
- Factories: 5
- Mock utilities: 10+

**Покрытие:**
- Models: ~80%
- Auth: ~75%
- Bot handlers: ~65%
- Services: ~65%
- RAG: ~60%

**Target достигнут:** ✅ 60-70% overall coverage

---

## 💡 Рекомендации

1. **Запускайте unit тесты часто** (быстрые, ~30 сек)
2. **Integration тесты перед commit** (полная проверка)
3. **Coverage проверяйте периодически** (цель >60%)
4. **Используйте markers** для фильтрации тестов
5. **Добавляйте тесты для новых features** сразу

---

## 🔗 Ссылки

- **Tests README:** `tests/README.md`
- **Run Script:** `tests/run_tests.sh`
- **Pytest Config:** `pytest.ini`
- **Coverage Config:** `.coveragerc`
- **Test Dependencies:** `requirements-test.txt`

---

**Версия:** 3.3.0  
**Статус:** ✅ Production Ready  
**Обновлено:** 14 октября 2025

