# Cursor Rules Update - RAG System

## Дополнение к n8n-telegram-bot.mdc

Добавить в секцию **"🐍 Основные компоненты"** после `run_system.py`:

---

### RAG System (новое!)

**rag_service/** - микросервис для векторного поиска и генерации ответов:
- `main.py` - FastAPI сервер (порт 8020)
- `vector_db.py` - Qdrant клиент для векторного поиска
- `embeddings.py` - генерация embeddings (GigaChat + fallback)
- `indexer.py` - индексирование постов в Qdrant
- `search.py` - гибридный поиск по постам
- `generator.py` - RAG-генерация ответов
- `digest_generator.py` - генерация дайджестов
- `scheduler.py` - планировщик автоматических дайджестов
- `schemas.py` - Pydantic модели API
- `config.py` - конфигурация RAG
- `Dockerfile.rag` - Docker образ
- `requirements.txt` - зависимости (minimal)

---

## Добавить новую секцию: "🤖 RAG System"

### 9. RAG System (`rag_service/`)

**Архитектура:**
- Отдельный микросервис на FastAPI
- Порт: 8020
- Интеграция через HTTP API
- Автоматическая индексация через webhook

**Технологии:**
```python
# Векторная БД
- Qdrant (https://qdrant.produman.studio)
- Коллекции: telegram_posts_{user_id}
- Изоляция по пользователям

# Embeddings
- Основной: EmbeddingsGigaR (через gpt2giga-proxy)
- Контекст: до 4096 токенов
- Chunking: 1536 токенов, overlap 256
- Fallback: sentence-transformers (опционально)

# LLM для RAG
- OpenRouter (google/gemini-2.0-flash-exp:free)
- Fallback: GigaChat через gpt2giga-proxy
```

**Компоненты:**

1. **Индексирование (`indexer.py`)**
   ```python
   async def index_post(post_id: int):
       # Генерация embedding через GigaChat
       # Chunking для длинных постов
       # Сохранение в Qdrant с метаданными
       # Статус в таблице indexing_status
       pass
   ```

2. **Поиск (`search.py`)**
   ```python
   async def search(query: str, user_id: int, filters: dict):
       # Векторный поиск в Qdrant
       # Фильтры: channel_id, tags, date range
       # Min score threshold для релевантности
       # Обогащение данными из БД
       pass
   ```

3. **RAG-генерация (`generator.py`)**
   ```python
   async def generate_answer(query: str, user_id: int):
       # Retrieval: поиск релевантных постов
       # Формирование промпта с контекстом
       # Generation: ответ через OpenRouter/GigaChat
       # Цитирование источников [@канал, дата]
       pass
   ```

4. **Дайджесты (`digest_generator.py`)**
   ```python
   async def generate_digest(user_id: int, date_range: tuple):
       # Группировка постов по каналам
       # Форматирование: Markdown/HTML/Plain
       # Планирование через scheduler
       pass
   ```

**API Endpoints:**
```
# Индексирование
POST /rag/index/post/{post_id}
POST /rag/index/user/{user_id}
POST /rag/index/batch
POST /rag/reindex/user/{user_id}
DELETE /rag/index/user/{user_id}

# Поиск
GET /rag/search
GET /rag/search/similar/{post_id}
GET /rag/tags/popular/{user_id}
GET /rag/channels/stats/{user_id}

# RAG
POST /rag/ask

# Дайджесты
POST /rag/digest/generate
GET /rag/digest/settings/{user_id}
PUT /rag/digest/settings/{user_id}

# Управление
GET /rag/stats/{user_id}
GET /health
```

**Интеграция с парсером:**
```python
# В parser_service.py автоматически вызывается:
async def _notify_rag_service(post_ids: List[int]):
    """Уведомление RAG-сервиса о новых постах"""
    await http_client.post(
        "http://rag-service:8020/rag/index/batch",
        json={"post_ids": post_ids}
    )
```

**Новые модели БД:**
```python
class DigestSettings(Base):
    """Настройки автоматических дайджестов"""
    __tablename__ = "digest_settings"
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    enabled = Column(Boolean, default=False)
    frequency = Column(String, default="daily")
    time = Column(String, default="09:00")
    # ... настройки расписания и контента

class IndexingStatus(Base):
    """Статус индексации постов в Qdrant"""
    __tablename__ = "indexing_status"
    user_id = Column(Integer, ForeignKey("users.id"))
    post_id = Column(Integer, ForeignKey("posts.id"))
    status = Column(String)  # success, failed, pending
    vector_id = Column(String)  # ID в Qdrant
```

---

## Обновить секцию: "📁 Структура проекта"

```
telethon/
├── docs/                      # Вся документация
│   ├── quickstart/           # Быстрые старты
│   │   ├── QUICK_START.md
│   │   ├── RAG_QUICKSTART.md         # ← НОВОЕ
│   │   └── RAG_SYSTEM_READY.md       # ← НОВОЕ
│   ├── features/             # Документация функций
│   │   ├── rag/                      # ← НОВОЕ
│   │   │   ├── README.md
│   │   │   ├── RAG_IMPLEMENTATION_SUMMARY.md
│   │   │   ├── RAG_DEPLOYMENT_SUMMARY.md
│   │   │   ├── RAG_CHECKLIST.md
│   │   │   └── DOCKER_DEPLOYMENT_ORDER.md
│   │   ├── TAGGING_RETRY_SYSTEM.md
│   │   └── ...
│   ├── migrations/           # Руководства по миграциям
│   ├── troubleshooting/      # Решение проблем
│   │   └── TIMEZONE_FIX.md          # ← перемещено
│   └── archive/              # Архив старых документов ← НОВОЕ
│       ├── README.md
│       ├── ARCHITECTURE_COMPARISON.md
│       ├── LIBRARY_DOCS_REVIEW.md
│       └── REORGANIZATION_SUMMARY.md
├── scripts/                   # Скрипты
│   ├── setup/                # Настройка системы
│   ├── migrations/           # Миграции БД
│   │   └── add_rag_tables.py        # ← НОВОЕ
│   └── utils/                # Утилиты
├── rag_service/              # RAG микросервис ← НОВОЕ
│   ├── main.py
│   ├── vector_db.py
│   ├── embeddings.py
│   ├── indexer.py
│   ├── search.py
│   ├── generator.py
│   ├── digest_generator.py
│   ├── scheduler.py
│   ├── schemas.py
│   ├── config.py
│   ├── requirements.txt
│   ├── Dockerfile.rag
│   └── README.md
├── tests/                     # Тесты
├── examples/                  # Примеры (n8n workflows)
├── sessions/                  # Сессии Telegram (gitignored)
├── data/                      # База данных SQLite
├── logs/                      # Логи приложения
├── README.md                  # Главный README
└── [основные .py файлы]      # Код приложения
```

---

## Обновить секцию: "🐳 Docker интеграция"

### Дополнительные сервисы в docker-compose.override.yml

**telethon** (порты 8010, 8001):
- API сервер + Parser + Bot
- Переменные из корневого .env

**telethon-bot** (standalone bot):
- Отдельный контейнер для Telegram бота

**gpt2giga-proxy** (порт 8090):
- OpenAI-совместимый прокси для GigaChat (Sber)
- Переменная: `GIGACHAT_CREDENTIALS` (единый API ключ)
- Получить credentials: https://developers.sber.ru/gigachat

**rag-service** (порт 8020): ← НОВОЕ
- RAG микросервис для поиска и генерации ответов
- Зависимости: telethon, gpt2giga-proxy
- Сети: default + localai_default (для доступа к Qdrant)
- Volumes: общие с telethon (data, logs, models.py, database.py)

### Используется корневой docker-compose
```yaml
# docker-compose.override.yml в корне проекта
services:
  telethon:
    build: ./telethon
    ports:
      - "8010:8010"  # API
      - "8001:8001"  # Auth web
    volumes:
      - ./telethon/sessions:/app/sessions
      - ./telethon/data:/app/data
      - ./telethon/logs:/app/logs
  
  rag-service:                 # ← НОВОЕ
    build: ./telethon/rag_service
    ports:
      - "8020:8020"  # RAG API
    volumes:
      - ./telethon/rag_service:/app
      - ./telethon/data:/app/data
      - ./telethon/logs:/app/logs
      - ./telethon/database.py:/app/database.py
      - ./telethon/models.py:/app/models.py
    depends_on:
      - telethon
      - gpt2giga-proxy
    networks:
      - default
      - localai_default
```

---

## Обновить секцию: "🌍 Переменные окружения"

### telethon/.env (опционально)
```env
# Специфичные для сервиса:
BOT_TOKEN=...
PARSER_INTERVAL_MINUTES=30
MAX_POSTS_PER_CHANNEL=50
HOST=0.0.0.0
PORT=8010
AUTH_BASE_URL=https://telegram-auth.produman.studio
OPENROUTER_API_KEY=...
OPENROUTER_MODEL=google/gemini-2.0-flash-exp:free
TAGGING_BATCH_SIZE=10

# RAG Service Configuration ← НОВОЕ
QDRANT_API_KEY=your_qdrant_api_key
RAG_SERVICE_ENABLED=true
RAG_SERVICE_URL=http://rag-service:8020
GIGACHAT_ENABLED=true
EMBEDDING_MAX_TOKENS_GIGACHAT=1536
EMBEDDING_OVERLAP_TOKENS_GIGACHAT=256
RAG_TOP_K=10
RAG_MIN_SCORE=0.7
RAG_CONTEXT_WINDOW=4000
RAG_TEMPERATURE=0.3
DIGEST_DEFAULT_TIME=09:00
DIGEST_MAX_POSTS=20
```

---

## Добавить новую секцию: "🔍 RAG System Workflow"

### Автоматическая индексация

```python
# 1. Parser парсит новые посты
await parser_service.parse_channel(channel_id, user_id)

# 2. Автоматическое тегирование
await tagging_service.process_posts_batch(new_post_ids)

# 3. Автоматическая индексация в Qdrant ← НОВОЕ
await _notify_rag_service(new_post_ids)

# 4. RAG-сервис индексирует посты
# - Генерация embeddings через GigaChat
# - Chunking длинных текстов (>1536 токенов)
# - Сохранение в Qdrant с метаданными
# - Обновление статуса в indexing_status
```

### Использование RAG

**Поиск:**
```bash
GET /rag/search?query=AI&user_id=1&limit=5
# Возвращает топ-5 релевантных постов
```

**RAG-ответ:**
```bash
POST /rag/ask
{
  "query": "Что писали про AI?",
  "user_id": 1,
  "context_limit": 10
}
# Возвращает развернутый ответ с источниками
```

**Дайджест:**
```bash
POST /rag/digest/generate
{
  "user_id": 1,
  "date_from": "2025-01-10T00:00:00Z",
  "date_to": "2025-01-11T23:59:59Z",
  "format": "markdown"
}
# Возвращает дайджест в Markdown
```

### Миграция для RAG

**Скрипт:** `scripts/migrations/add_rag_tables.py`

Добавляет таблицы:
- `digest_settings` - настройки автоматических дайджестов
- `indexing_status` - статус индексации постов в Qdrant

**Запуск:**
```bash
cd /home/ilyasni/n8n-server/n8n-installer/telethon
python3 scripts/migrations/add_rag_tables.py
```

---

## Обновить секцию: "📁 Структура проекта"

Заменить блок структуры на обновленный (см. выше).

---

## Обновить секцию: "🔄 Workflow разработки"

### Разработка RAG-сервиса

```bash
# Docker разработка
cd /home/ilyasni/n8n-server/n8n-installer

# Пересборка RAG-сервиса
docker compose build rag-service --no-cache
docker compose up -d rag-service

# Просмотр логов
docker logs -f rag-service

# Перезапуск после изменений
docker restart rag-service

# Вход в контейнер
docker exec -it rag-service bash

# API документация
open http://localhost:8020/docs
```

### Локальная разработка RAG

```bash
cd /home/ilyasni/n8n-server/n8n-installer/telethon/rag_service

# Установка зависимостей
pip install -r requirements.txt

# Запуск локально
python main.py

# API будет на http://localhost:8020
```

---

## Обновить секцию: "🚨 Частые ошибки"

### RAG-специфичные ошибки:

**❌ НЕ делайте так:**
```python
# Импорт models.py вместо schemas.py
from models import SearchRequest  # ❌ Конфликт с SQLAlchemy models

# Именование клиента как библиотеки
from qdrant_client import qdrant_client  # ❌ Circular import
```

**✅ Делайте так:**
```python
# Используйте schemas для Pydantic моделей
from schemas import SearchRequest  # ✅

# Используйте vector_db для Qdrant
from vector_db import qdrant_client  # ✅
```

### Troubleshooting RAG

**RAG-сервис не запускается:**
```bash
# Проверить логи
docker logs rag-service --tail 50

# Проверить сети (должны быть обе!)
docker inspect rag-service | grep -A 5 "Networks"
# Должно быть: default + localai_default

# Пересобрать
docker compose build rag-service --no-cache
docker compose up -d rag-service
```

**Qdrant не подключается:**
```bash
# Проверить что Qdrant запущен
docker ps | grep qdrant

# Проверить сеть Qdrant
docker inspect qdrant | grep -A 5 "Networks"
# Должно быть: default + localai_default

# Проверить API ключ
docker logs rag-service | grep "QDRANT"

# Health check
curl http://localhost:8020/health
# qdrant_connected должен быть true
```

**Embeddings не генерируются:**
```bash
# Проверить gpt2giga-proxy
docker logs gpt2giga-proxy

curl http://localhost:8090/health

# Проверить в RAG логах
docker logs rag-service | grep "embedding"
```

---

## Обновить секцию: "🔗 Интеграция с n8n"

### API endpoints для n8n workflows

**Основной Parser API:**
```
GET  /posts                    # Получить посты
GET  /posts/{post_id}          # Получить конкретный пост
GET  /channels                 # Список каналов пользователя
POST /tags/generate            # Сгенерировать теги
GET  /users/{user_id}/settings # Настройки пользователя
```

**RAG API (новое):** ← ДОБАВИТЬ
```
# Поиск
GET  http://rag-service:8020/rag/search

# RAG-ответ
POST http://rag-service:8020/rag/ask

# Дайджест
POST http://rag-service:8020/rag/digest/generate

# Статистика
GET  http://rag-service:8020/rag/stats/{user_id}
```

**Примеры workflows:** ← ОБНОВИТЬ
- `examples/n8n_parser.json` - базовый парсинг
- `examples/n8n_rag_search.json` - поиск через RAG ← НОВОЕ
- `examples/n8n_ask_question.json` - RAG-ответы ← НОВОЕ
- `examples/n8n_daily_digest.json` - автодайджесты ← НОВОЕ

---

## Добавить в секцию: "📊 Мониторинг и логи"

### RAG Service логи ← НОВОЕ

```bash
# Просмотр логов RAG
docker logs -f rag-service

# Типичные логи при успешной работе:
✅ RAG Service запускается...
✅ Qdrant клиент инициализирован: http://qdrant:6333
✅ Embeddings сервис инициализирован
   GigaChat proxy: http://gpt2giga-proxy:8090/v1/embeddings
✅ RAG Service готов к работе

# При индексации:
🔄 Начало batch индексации 5 постов
📄 Пост 123: разбит на 2 chunks
✅ Пост 123 chunk 1/2 проиндексирован (gigachat)
✅ Batch индексация завершена: успешно=5, ошибок=0

# При поиске:
🔍 Поиск для user 1: 'AI' (embedding: gigachat)
✅ Найдено 5 результатов для user 1

# При RAG-ответе:
🤖 Генерация ответа для user 1: 'Что писали про AI?'
✅ Ответ сгенерирован для user 1 (использовано 10 источников)
```

### Health Check ← НОВОЕ

```bash
# Проверка всех компонентов RAG
curl http://localhost:8020/health

# Ожидаемый результат:
{
  "status": "healthy",
  "qdrant_connected": true,      # Qdrant доступен
  "gigachat_available": true,    # GigaChat для embeddings
  "openrouter_available": true,  # OpenRouter для RAG
  "version": "0.1.0"
}
```

---

## Обновить секцию: "🎯 Performance"

### Limits

```python
# Parser
MAX_POSTS_PER_CHANNEL = 50      # За один парсинг
PARSER_INTERVAL_MINUTES = 30    # Минимальный интервал
TAGGING_BATCH_SIZE = 10         # Постов за раз для AI
MAX_CHANNELS_PER_USER = 100     # Ограничение каналов

# RAG Service ← НОВОЕ
RAG_TOP_K = 10                  # Документов для контекста
RAG_MIN_SCORE = 0.7             # Минимальный score релевантности
RAG_CONTEXT_WINDOW = 4000       # Макс. контекст (tokens)
EMBEDDING_MAX_TOKENS = 1536     # Макс. токенов на chunk (GigaChat: до 4096)
DIGEST_MAX_POSTS = 20           # Макс. постов в дайджесте
```

### Производительность RAG ← НОВОЕ

- **Индексация:** ~0.5-2 сек/пост
- **Поиск:** <500ms
- **RAG-ответ:** 5-12 сек (зависит от LLM)
- **Дайджест:** 5-10 сек для 20 постов

---

## Добавить в секцию: "🔧 Скрипты"

### Миграции БД

**add_rag_tables.py:** ← НОВОЕ
```python
# Добавление таблиц для RAG-системы
# - digest_settings: настройки дайджестов
# - indexing_status: статус индексации в Qdrant

python scripts/migrations/add_rag_tables.py
```

---

## Добавить новую секцию: "🌐 Сетевая архитектура"

### Docker Networks

**default (n8n-installer_default):**
- n8n, postgres, redis
- qdrant ← Должен быть в обеих сетях!
- caddy

**localai_default (external):**
- telethon, telethon-bot
- gpt2giga-proxy
- rag-service ← Должен быть в обеих сетях!
- qdrant ← Должен быть в обеих сетях!

**Критично для RAG:**
```yaml
rag-service:
  networks:
    - default           # Для доступа к Qdrant, Caddy
    - localai_default   # Для telethon, gpt2giga

qdrant:
  networks:
    - default           # Для n8n, flowise, caddy
    - localai_default   # Для RAG-service
```

### Порядок запуска

**Правильная последовательность:**
```bash
# 1. БД и инфраструктура
postgres, redis, clickhouse

# 2. Supabase (если включен)
supabase-db, supabase-kong, ...

# 3. AI infrastructure
qdrant              # ← Должен быть до RAG!

# 4. Telegram Parser Stack
gpt2giga-proxy      # ← Должен быть до telethon и RAG!
telethon
telethon-bot

# 5. RAG Service
rag-service         # ← После telethon и gpt2giga!

# 6. n8n
n8n, n8n-worker

# 7. Reverse Proxy
caddy
```

---

## Обновить: "✨ Best Practices"

Добавить пункт 9:

9. **RAG:** Используйте GigaChat для embeddings, chunking для длинных текстов, кэшируйте результаты

---

## Добавить секцию: "🆕 Обновления версии 2.2"

### RAG System (11 октября 2025)
- ✅ Реализован RAG микросервис для векторного поиска и генерации ответов
- ✅ Интеграция Qdrant векторной БД
- ✅ Embeddings через EmbeddingsGigaR (gpt2giga-proxy)
- ✅ Автоматическая индексация новых постов
- ✅ API endpoints для поиска, RAG-ответов и дайджестов
- ✅ Миграция БД: добавлены таблицы digest_settings и indexing_status
- ✅ Docker конфигурация с правильными сетями
- ✅ Caddy reverse proxy для внешнего доступа
- ✅ Полная документация в docs/features/rag/

### Структура документации
- ✅ Реорганизованы MD файлы:
  - RAG документация перемещена в docs/features/rag/
  - Старые отчеты в docs/archive/
  - Только README.md остался в корне telethon/
- ✅ Создан README.md в docs/features/rag/
- ✅ Создан README.md в docs/archive/

### Исправления
- ✅ Исправлена сетевая изоляция: Qdrant и RAG в обеих сетях
- ✅ Исправлены конфликты имен: models.py → schemas.py, qdrant_client.py → vector_db.py
- ✅ Упрощены зависимости: minimal requirements.txt без torch
- ✅ Добавлена интеграция с Caddy для внешнего доступа

---

## Инструкции по обновлению Cursor Rules

1. Откройте настройки Cursor
2. Найдите правило "n8n-telegram-bot"
3. Добавьте секции выше в соответствующие места
4. Обновите версию на **2.2**
5. Обновите дату на **11 октября 2025**
6. Сохраните изменения

---

**Версия правил:** 2.2  
**Дата обновления:** 11 октября 2025  
**Изменения:** Добавлена RAG System, реорганизована документация

