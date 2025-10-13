# Telegram Bot Cursor Rules

**Version:** 3.2.0  
**Last Updated:** 13 октября 2025  
**Changelog:** См. [CHANGELOG.mdc](./CHANGELOG.mdc)

## 📋 О системе правил

Модульная система Cursor Rules для проекта **Telegram Channel Parser Bot** с поддержкой:
- QR-авторизации (без SMS)
- Admin Panel через Mini App
- RAG-системы для поиска
- Микросервисной архитектуры

## 🗂️ Структура модулей

Правила разделены на **9 логических модулей** по рекомендациям Cursor (< 600 строк каждый):

### Core Modules

| Модуль | Описание | Строк | Priority | Scope |
|--------|----------|-------|----------|-------|
| **01-core.mdc** | Основные правила, критичные паттерны | ~310 | 🔴 Critical | `telethon/**/*.py` |
| **02-architecture.mdc** | Микросервисы, Docker, networking | ~333 | 🟡 Medium | `telethon/**/*.py` |
| **03-database.mdc** | PostgreSQL, Redis, модели, timezone | ~434 | 🔴 Critical | `telethon/models.py`, `telethon/database.py` |
| **04-development.mdc** | Workflow, testing, dev.sh helper | ~488 | 🟢 Low | `telethon/scripts/**` |

### Feature Modules

| Модуль | Описание | Строк | Priority | Scope |
|--------|----------|-------|----------|-------|
| **05-security.mdc** | QR Login, auth, encryption, sessions | ~512 | 🔴 Critical | `telethon/*auth*.py`, `telethon/crypto*.py` |
| **06-admin.mdc** | Admin Panel, roles, subscriptions | ~546 | 🟡 Medium | `telethon/admin*.py` |
| **07-rag.mdc** | RAG, vector search, embeddings, AI | ~591 | 🟡 Medium | `telethon/rag_service/**` |
| **08-api.mdc** | FastAPI endpoints, rate limiting | ~599 | 🟡 Medium | `telethon/main.py`, `telethon/api_*.py` |
| **09-external.mdc** | External services (Qdrant, Crawl4AI) | ~535 | 🟢 Low | `telethon/integrations/**` |

**Special Files:**

| Файл | Назначение | Priority |
|------|------------|----------|
| **CHANGELOG.mdc** | История версий и изменений | 🟢 Low |
| **README.md** | Навигация и документация системы | 🟢 Low |

**Entry Point (в корне проекта):**

| Файл | Назначение | Priority |
|------|------------|----------|
| **`.cursorrules`** | Entry point, critical rules, verification checklist | 🔴 Critical |

## 🎯 Как использовать

### Основной workflow

1. **Entry point:** `.cursorrules` в корне проекта — загружается автоматически
2. **Cursor автоматически загрузит модули** по `scope` (file patterns)
3. **Для конкретных задач** используйте соответствующий модуль из `.cursor/rules/telegram-bot/`

### Cursor Settings

**Рекомендуемые настройки для `.cursor/settings.json`:**

```json
{
  "cursor.rules.autoAttach": true,
  "cursor.rules.scope": "workspace",
  "cursor.rules.maxFiles": 3,
  "cursor.rules.priority": "user"
}
```

### Auto-Attach по Scope

Модули автоматически применяются при редактировании соответствующих файлов:

```yaml
# 01-core.mdc
scope:
  - "telethon/**/*.py"
  - "!telethon/tests/**"

# 03-database.mdc
scope:
  - "telethon/models.py"
  - "telethon/database.py"
  - "telethon/migrations/**"

# 05-security.mdc
scope:
  - "telethon/*auth*.py"
  - "telethon/crypto*.py"
  - "telethon/sessions/**"
```

## 📚 Quick Links

### По задачам

**🆕 Создание нового компонента:**
1. `telegram-bot.cursorrules` → critical rules
2. `01-core.mdc` → структура проекта
3. `02-architecture.mdc` → где разместить код
4. `03-database.mdc` → модели БД (если нужны)
5. `08-api.mdc` → API endpoints (если нужны)

**🐛 Debugging:**
1. `telegram-bot.cursorrules` → verification checklist
2. `04-development.mdc` → логи, отладка
3. Соответствующий feature module

**🔐 Работа с authentication:**
1. `05-security.mdc` → QR Login, sessions
2. `03-database.mdc` → User model, Redis
3. `telegram-bot.cursorrules` → critical patterns

**👑 Admin функции:**
1. `06-admin.mdc` → Admin Panel, roles
2. `03-database.mdc` → SubscriptionHistory
3. `08-api.mdc` → Admin API endpoints

**🤖 RAG/AI функции:**
1. `07-rag.mdc` → RAG pipeline, embeddings
2. `09-external.mdc` → Qdrant, GigaChat
3. `03-database.mdc` → IndexingStatus

## ⚠️ Критичные правила (must-read)

### Из `telegram-bot.cursorrules` и `01-core.mdc`

✅ **#0: ВСЕГДА используйте Context7 перед разработкой**

```bash
# ✅ ПРАВИЛЬНЫЙ WORKFLOW:
# 1. Используйте Context7 для поиска решений
Context7: "Telegram Bot API best practices"
Context7: "FastAPI async patterns"
Context7: "SQLAlchemy relationships PostgreSQL"

# 2. Изучите официальную документацию через Context7
#    - Найдите примеры использования
#    - Проверьте актуальные версии API
#    - Узнайте best practices

# 3. ТОЛЬКО ПОТОМ пишите код
```

**Auto-integration hint для AI:**
```python
# If uncertain about library usage, automatically query:
# Context7("library-name best practices")
# Context7("library-name current API version")
```

**Примеры:**
```bash
# Перед добавлением Telegram Mini App
→ Context7: "Telegram Mini Apps WebAppInfo best practices"

# Перед работой с FastAPI
→ Context7: "FastAPI background tasks async"

# Перед изменением SQLAlchemy моделей
→ Context7: "SQLAlchemy relationships many-to-many"

# Перед интеграцией внешнего API
→ Context7: "Qdrant Python client async"
```

---

✅ **#1: ТОЛЬКО PostgreSQL** (БЕЗ SQLite fallback)

```python
# ✅ Правильно
database_url = os.getenv("TELEGRAM_DATABASE_URL")
if "sqlite" in database_url.lower():
    raise ValueError("SQLite НЕ поддерживается!")

# ❌ НИКОГДА
db_url = os.getenv("DATABASE_URL", "sqlite:///fallback.db")  # НЕТ!
```

---

✅ **#2: Timezone-aware datetime ВСЕГДА**

```python
from datetime import datetime, timezone

# ✅ Правильно
user.created_at = datetime.now(timezone.utc)

# ❌ Naive datetime - НЕТ!
user.created_at = datetime.now()
```

---

✅ **#3: Фильтрация по user_id ОБЯЗАТЕЛЬНА**

```python
# ✅ Правильно
posts = db.query(Post).filter(Post.user_id == user_id).all()

# ❌ Утечка данных
posts = db.query(Post).all()
```

---

✅ **#4: Redis БЕЗ пароля + prefixes**

```python
# ✅ Правильно (Valkey default)
redis_client = redis.Redis(host='redis', port=6379)

# ✅ Всегда используйте prefixes
redis.setex(f"qr_session:{session_id}", 300, data)

# ❌ НЕТ пароля!
redis_client = redis.Redis(host='redis', password='...')  # НЕТ!

# ❌ НЕТ prefix - конфликты!
redis.setex(session_id, 300, data)
```

### Из `03-database.mdc`

✅ **Timezone handling в PostgreSQL:**

```python
# ✅ Всегда UTC в БД, Europe/Moscow для display
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# Сохраняем
user.created_at = datetime.now(timezone.utc)

# Показываем пользователю
LOCAL_TZ = ZoneInfo('Europe/Moscow')
display_time = user.created_at.astimezone(LOCAL_TZ)

# Сравнение
if expires.tzinfo is None:
    expires = expires.replace(tzinfo=timezone.utc)
```

### Из `04-development.mdc`

✅ **Context7 Workflow в development cycle:**

```bash
# 0. ОБЯЗАТЕЛЬНО: Изучить документацию через Context7
# → Context7: "Feature name best practices"
# → Context7: "Library name API documentation"

# 1. Внести изменения
vim telethon/qr_auth_manager.py

# 2. Пересобрать
telethon-rebuild

# 3. Смотреть логи
telethon-logs

# 4. Тестировать
curl http://localhost:8010/docs
```

## 🔀 Conflict Resolution

### Priority System

При конфликте правил из разных модулей:

1. **01-core.mdc** (HIGHEST PRIORITY)
   - Critical patterns always apply
   - PostgreSQL, timezone, user filtering

2. **03-database.mdc & 05-security.mdc** (HIGH)
   - Database rules for data persistence
   - Security rules for auth logic

3. **07-rag.mdc & 08-api.mdc** (MEDIUM)
   - Feature-specific implementations
   - API endpoint patterns

4. **02-architecture.mdc & 04-development.mdc** (LOW)
   - Architectural guidance
   - Development workflow

### Resolution Strategy

```yaml
# If core rule conflicts with feature rule:
→ follow 01-core.mdc

# If security conflicts with database:
→ follow 05-security.mdc for auth logic
→ follow 03-database.mdc for persistence

# If both database and RAG apply:
→ follow 03-database.mdc for models
→ follow 07-rag.mdc for embeddings/search

# If in doubt:
→ follow higher priority module
→ check telegram-bot.cursorrules
```

## ✅ Verification Checklist

См. полный checklist в `telegram-bot.cursorrules` секция "Verification Checklist Summary".

**Краткая версия:**

- [ ] Context7 использован для изучения API
- [ ] PostgreSQL only (`grep -r "sqlite"` → 0 результатов)
- [ ] Timezone-aware datetime везде
- [ ] User ID filtering во всех queries
- [ ] Type hints на всех функциях
- [ ] Async patterns для HTTP/DB
- [ ] Redis prefixes для изоляции
- [ ] Error handling с try-except

## 🚨 Troubleshooting

**Cursor не применяет правила:**
1. Проверьте `.cursor/rules` в корне workspace
2. Откройте Command Palette → "Cursor Rules: Reload"
3. Проверьте что файл соответствует `scope` pattern
4. Проверьте `autoAttach: true` в YAML frontmatter

**Правила конфликтуют:**
1. Смотрите секцию "Conflict Resolution" выше
2. `01-core.mdc` имеет highest priority
3. При конфликте — следуйте `telegram-bot.cursorrules`

**Нужно добавить новое правило:**
1. Определите категорию (core/database/security/etc.)
2. Добавьте в соответствующий модуль
3. Если модуль > 600 строк → разделите на подмодули
4. Обновите YAML frontmatter (`scope`, `tags`, `priority`)
5. Добавьте quick examples в конце модуля
6. Обновите CHANGELOG.mdc
7. Обновите этот README

**AI не использует Context7:**
1. Проверьте что правило #0 в `telegram-bot.cursorrules`
2. Добавьте auto-integration hint в модуль
3. Явно напомните AI использовать Context7

## 📊 Статистика

**Файловая структура:**
- Total modules: 9
- Total lines: ~4,350
- Average per module: ~483 lines
- Files with YAML frontmatter: 100%

**Покрытие scope:**
- Core files: `telethon/**/*.py`
- Database: `telethon/models.py`, `telethon/database.py`
- Security: `telethon/*auth*.py`, `telethon/crypto*.py`
- RAG: `telethon/rag_service/**`
- API: `telethon/main.py`, `telethon/api_*.py`

## 🔄 Updates

См. [CHANGELOG.mdc](./CHANGELOG.mdc) для детальной истории изменений.

**Latest (v3.2.0 - 2025-10-13):**
- ✅ YAML frontmatter во всех модулях
- ✅ Context7 auto-integration hints
- ✅ Quick Examples (✅/❌) в конце модулей
- ✅ Conflict Resolution блоки
- ✅ Verification Checklist Summary
- ✅ Отдельный CHANGELOG.mdc
- ✅ Переезд в `.cursor/rules/`

## 📞 Support

- **GitHub Issues:** [telethon/issues](https://github.com/your-repo/telethon/issues)
- **Documentation:** `/home/ilyasni/n8n-server/n8n-installer/telethon/docs/`
- **Cursor Rules Docs:** [docs.cursor.com/context/rules](https://docs.cursor.com/context/rules)
- **Trigger.dev Guide:** [trigger.dev/blog/cursor-rules](https://trigger.dev/blog/cursor-rules)

---

**Maintained by:** Telegram Bot Team  
**License:** CC0-1.0  
**Version:** 3.2.0

