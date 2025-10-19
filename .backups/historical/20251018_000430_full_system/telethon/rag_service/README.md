# RAG Service для Telegram Channel Parser

## Описание

RAG (Retrieval-Augmented Generation) Service - микросервис для интеллектуального поиска и анализа постов из Telegram каналов.

## Возможности

- 🔍 **Векторный поиск** - семантический поиск по постам с фильтрацией
- 🤖 **RAG-ответы** - генерация ответов на вопросы на основе найденных постов
- 📰 **Дайджесты** - автоматическая генерация сводок постов
- 🏷️ **Автоиндексация** - автоматическое индексирование новых постов
- 📊 **Аналитика** - статистика по каналам и тегам

## Архитектура

```
rag_service/
├── main.py                    # FastAPI приложение
├── indexer.py                 # Индексирование в Qdrant
├── search.py                  # Гибридный поиск
├── generator.py               # RAG-генерация ответов
├── digest_generator.py        # Генерация дайджестов
├── qdrant_client.py          # Клиент Qdrant
├── embeddings.py             # Генерация embeddings
├── scheduler.py              # Планировщик задач
├── models.py                 # Pydantic модели
└── config.py                 # Конфигурация
```

## Технологии

- **Векторная БД:** Qdrant (https://qdrant.produman.studio)
- **Embeddings:** EmbeddingsGigaR (через gpt2giga-proxy) + fallback на sentence-transformers
- **LLM:** OpenRouter (google/gemini-2.0-flash-exp:free)
- **API:** FastAPI
- **Scheduler:** APScheduler

## API Endpoints

### Индексирование

```bash
# Индексировать один пост
POST /rag/index/post/{post_id}

# Индексировать все посты пользователя
POST /rag/index/user/{user_id}?limit=100

# Batch индексирование
POST /rag/index/batch
{
  "post_ids": [1, 2, 3, ...]
}

# Переиндексировать пользователя
POST /rag/reindex/user/{user_id}

# Удалить индекс пользователя
DELETE /rag/index/user/{user_id}
```

### Поиск

```bash
# Гибридный поиск
GET /rag/search?query=искусственный+интеллект&user_id=1&limit=10

# Поиск с фильтрами
GET /rag/search?query=...&user_id=1&channel_id=5&tags=технологии,ai&date_from=2025-01-01

# Похожие посты
GET /rag/search/similar/{post_id}?limit=5

# Популярные теги
GET /rag/tags/popular/{user_id}?limit=20

# Статистика каналов
GET /rag/channels/stats/{user_id}
```

### RAG-ответы

```bash
# Задать вопрос
POST /rag/ask
{
  "query": "Что писали про AI на этой неделе?",
  "user_id": 1,
  "context_limit": 10,
  "channels": [1, 2],
  "tags": ["ai", "технологии"]
}
```

### Дайджесты

```bash
# Сгенерировать дайджест
POST /rag/digest/generate
{
  "user_id": 1,
  "date_from": "2025-01-10T00:00:00Z",
  "date_to": "2025-01-11T23:59:59Z",
  "format": "markdown",
  "max_posts": 20
}

# Настройки дайджеста
GET /rag/digest/settings/{user_id}
PUT /rag/digest/settings/{user_id}
{
  "enabled": true,
  "frequency": "daily",
  "time": "09:00",
  "format": "markdown"
}
```

### Статистика

```bash
# Статистика индексации
GET /rag/stats/{user_id}

# Здоровье сервиса
GET /health
```

## Конфигурация

Переменные окружения в `.env`:

```bash
# Qdrant
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=your_api_key
QDRANT_EXTERNAL_URL=https://qdrant.produman.studio

# Embeddings
GIGACHAT_PROXY_URL=http://gpt2giga-proxy:8090
GIGACHAT_ENABLED=true
EMBEDDING_MAX_TOKENS_GIGACHAT=1536
EMBEDDING_OVERLAP_TOKENS_GIGACHAT=256

# RAG
OPENROUTER_API_KEY=your_api_key
OPENROUTER_MODEL=google/gemini-2.0-flash-exp:free
RAG_TOP_K=10
RAG_MIN_SCORE=0.7
RAG_CONTEXT_WINDOW=4000
RAG_TEMPERATURE=0.3

# Database
DATABASE_URL=sqlite:///./data/telethon_bot.db
```

## Запуск

### Docker (рекомендуется)

```bash
# Из корня проекта
docker compose up rag-service -d

# Просмотр логов
docker logs -f rag-service
```

### Локально

```bash
cd rag_service
pip install -r requirements.txt
python main.py
```

API будет доступен на: http://localhost:8020

Документация API: http://localhost:8020/docs

## Использование

### 1. Индексация постов

После того как парсер добавил новые посты, они автоматически индексируются через webhook.

Для ручной индексации:

```bash
curl -X POST http://localhost:8020/rag/index/user/1
```

### 2. Поиск

```bash
curl "http://localhost:8020/rag/search?query=искусственный+интеллект&user_id=1&limit=5"
```

### 3. RAG-ответ

```bash
curl -X POST http://localhost:8020/rag/ask \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Что писали про AI на этой неделе?",
    "user_id": 1,
    "context_limit": 10
  }'
```

### 4. Дайджест

```bash
curl -X POST http://localhost:8020/rag/digest/generate \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "date_from": "2025-01-10T00:00:00Z",
    "date_to": "2025-01-11T23:59:59Z",
    "format": "markdown"
  }'
```

## Интеграция

### С parser_service

Parser автоматически уведомляет RAG-сервис о новых постах:

```python
# В parser_service.py
await self._notify_rag_service(post_ids)
```

### С n8n

Используйте proxy endpoints в основном API telethon:

```
GET  /users/{user_id}/search
POST /users/{user_id}/ask
POST /users/{user_id}/digest
```

## Chunking Strategy

### EmbeddingsGigaR (основной)
- Макс токенов: 1536
- Overlap: 256 токенов
- Контекст: до 4096 токенов

### Sentence-transformers (fallback)
- Макс токенов: 384
- Overlap: 64 токенов

## Troubleshooting

### Qdrant недоступен

```bash
# Проверка подключения
curl http://localhost:6333/collections

# Проверка API ключа
docker logs qdrant
```

### Embeddings не генерируются

```bash
# Проверка gpt2giga-proxy
curl http://localhost:8090/health

# Fallback на sentence-transformers
# Автоматически используется если gpt2giga недоступен
```

### RAG не генерирует ответы

```bash
# Проверка OPENROUTER_API_KEY
docker logs rag-service | grep "OPENROUTER"

# Проверка лимитов OpenRouter
# https://openrouter.ai/settings
```

## Производительность

- **Индексация:** ~2-5 постов/сек
- **Поиск:** <500ms
- **RAG-ответ:** 3-10 сек (зависит от LLM)
- **Дайджест:** 5-15 сек

## Лицензия

MIT

## Поддержка

Документация: `/home/ilyasni/n8n-server/n8n-installer/telethon/docs/`

