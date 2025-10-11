# RAG System - Быстрый старт

## Что это?

RAG (Retrieval-Augmented Generation) - система для интеллектуального поиска и анализа постов из Telegram каналов.

**Возможности:**
- 🔍 Семантический поиск по постам (векторный + keyword)
- 🤖 Ответы на вопросы на основе постов (RAG)
- 📰 AI-дайджесты с персонализацией
- 💡 Рекомендации на основе интересов пользователя
- 🌐 Гибридный поиск (посты + веб через Searxng)
- 📄 Обогащение постов контентом ссылок (Crawl4AI)

**Интеграции:**
- **Qdrant** - векторная БД для хранения embeddings
- **Redis** - кеширование embeddings (TTL 24h) и RAG-ответов (TTL 1h)
- **GigaChat** - генерация embeddings (EmbeddingsGigaR)
- **OpenRouter/GigaChat** - LLM для ответов
- **Searxng** - метапоисковик для расширения контекста
- **Crawl4AI** - извлечение контента веб-страниц
- **Ollama** - локальные LLM для приватных данных
- **n8n/Flowise** - автоматизация через webhooks

## Telegram бот - Новые команды

Используйте бота для быстрого доступа к RAG:

```
/ask <вопрос>          - Поиск ответа в постах
/digest                - Настройка AI-дайджестов
/recommend             - Персональные рекомендации
/search <запрос>       - Гибридный поиск (посты + web)
```

**Примеры:**
```
/ask Что писали про нейросети на этой неделе?
/ask Какие новости про Tesla?
/search блокчейн технологии
```

## Быстрый старт

### 1. Убедитесь что система запущена

```bash
# Проверка всех сервисов
docker ps | grep -E "telethon|rag-service|gpt2giga|qdrant"

# Должны быть запущены:
# - telethon
# - rag-service
# - gpt2giga-proxy
# - qdrant (если есть)
```

### 2. Проверка RAG-сервиса

```bash
# Health check
curl http://localhost:8020/health

# API документация
open http://localhost:8020/docs
```

### 3. Индексация постов

**Автоматически:** Новые посты индексируются автоматически после парсинга.

**Вручную:**
```bash
# Индексировать все посты пользователя (замените 1 на ваш user_id)
curl -X POST "http://localhost:8020/rag/index/user/1"

# Проверить статус индексации
curl "http://localhost:8020/rag/stats/1"
```

### 4. Поиск

```bash
# Простой поиск
curl "http://localhost:8020/rag/search?query=искусственный+интеллект&user_id=1&limit=5"

# С фильтрами
curl "http://localhost:8020/rag/search?query=AI&user_id=1&tags=технологии&limit=10"
```

### 5. Задать вопрос (RAG)

```bash
curl -X POST http://localhost:8020/rag/ask \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Что писали про искусственный интеллект на этой неделе?",
    "user_id": 1,
    "context_limit": 10
  }'
```

### 6. Дайджест

```bash
# Дайджест за последние 7 дней
curl -X POST http://localhost:8020/rag/digest/generate \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "date_from": "2025-01-05T00:00:00Z",
    "date_to": "2025-01-11T23:59:59Z",
    "format": "markdown",
    "max_posts": 20
  }'
```

## Интеграция с n8n

### Webhook для новых постов

Добавьте в n8n webhook для получения новых проиндексированных постов:

```
URL: http://rag-service:8020/rag/index/batch
Method: POST
Body: {"post_ids": [1, 2, 3]}
```

### Workflow: Ежедневный дайджест

1. **Trigger:** Schedule (каждый день в 9:00)
2. **HTTP Request:** POST к `/rag/digest/generate`
3. **Send to Telegram:** Отправить дайджест в канал/чат

## AI-дайджесты с персонализацией

### Настройка через бот

```
/digest    # Откроет меню настроек
```

**Выбор опций:**
- 📅 Частота: ежедневно / еженедельно
- 🕐 Время отправки: 09:00 (по умолчанию)
- 🤖 AI-суммаризация: вкл/выкл
- 📊 Стиль: краткий / детальный / executive
- 🏷️ Темы: список предпочитаемых тем

### Как работает персонализация

RAG анализирует **историю ваших запросов** за последние 30 дней:

```python
# 1. Извлекаем темы из запросов
/ask что нового в криптовалютах?
/ask новости про Tesla
→ Темы: [криптовалюты, Tesla, автомобили, технологии]

# 2. Ищем релевантные посты по темам
→ 10 постов про криптовалюты
→ 10 постов про Tesla
→ ...

# 3. AI суммаризация
→ Краткий дайджест с основными новостями по вашим интересам
```

### API для дайджестов

```bash
# Настройка AI-дайджеста
curl -X POST http://localhost:8020/rag/digest/settings/1 \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "ai_summarize": true,
    "frequency": "daily",
    "time": "09:00",
    "preferred_topics": ["AI", "блокчейн", "стартапы"],
    "summary_style": "concise",
    "max_posts": 50
  }'

# Генерация дайджеста
curl -X POST http://localhost:8020/rag/digest/generate/1
```

## Работа с внешними сервисами

### Redis кеширование

**Автоматическое:**
- Embeddings кешируются на 24 часа
- RAG-ответы кешируются на 1 час

**Ручное управление:**
```bash
# Очистка кеша embeddings
docker exec redis redis-cli -a LOCALONLYREDIS KEYS "embedding:*" | xargs docker exec redis redis-cli -a LOCALONLYREDIS DEL

# Очистка RAG-ответов
docker exec redis redis-cli -a LOCALONLYREDIS KEYS "rag:*" | xargs docker exec redis redis-cli -a LOCALONLYREDIS DEL

# Проверка статистики
docker exec redis redis-cli -a LOCALONLYREDIS INFO stats
```

### Searxng (веб-поиск)

**Включение:**
```bash
# В .env
SEARXNG_ENABLED=true
SEARXNG_URL=https://searxng.produman.studio
SEARXNG_USER=hello@ilyasni.com
SEARXNG_PASSWORD=your_password
```

**Использование через бот:**
```
/search квантовые компьютеры
→ Ищет в ваших постах + в интернете через Searxng
```

**API:**
```bash
curl -X POST http://localhost:8020/rag/hybrid_search \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "query": "квантовые компьютеры",
    "include_web": true
  }'
```

### Crawl4AI (извлечение контента)

**Автоматическое обогащение:**
Когда пост содержит ссылку, Crawl4AI автоматически извлекает контент:

```python
# Пост с ссылкой
"Отличная статья про AI: https://example.com/ai-article"

# Автоматически извлекается контент ссылки
→ Статья индексируется вместе с постом
→ Доступна для поиска и RAG
```

**Настройка:**
```bash
# В .env
CRAWL4AI_ENABLED=true
CRAWL4AI_URL=http://crawl4ai:11235
CRAWL4AI_TIMEOUT=30
CRAWL4AI_WORD_THRESHOLD=100    # Минимум слов для индексации
```

### Ollama (локальные LLM)

**Use case:** Приватная обработка чувствительных данных

```bash
# В .env
OLLAMA_ENABLED=true
OLLAMA_URL=http://ollama:11434
OLLAMA_DEFAULT_MODEL=llama3.2
```

**API:**
```bash
# Анонимизация данных локально (без отправки в облако)
curl -X POST http://localhost:8020/rag/anonymize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Мой номер телефона +79001234567",
    "user_id": 1
  }'
```

## Troubleshooting

### RAG-сервис не запускается

```bash
# Проверка логов
docker logs rag-service

# Пересоздание контейнера
docker compose up rag-service --build -d
```

### Qdrant недоступен

```bash
# Проверка Qdrant
curl http://localhost:6333/collections

# Проверка API ключа в .env
grep QDRANT_API_KEY telethon/.env
```

### Embeddings не генерируются

```bash
# Проверка gpt2giga-proxy
docker logs gpt2giga-proxy

# Проверка в RAG логах
docker logs rag-service | grep "embedding"
```

### RAG не отвечает на вопросы

```bash
# Проверка OPENROUTER_API_KEY
docker logs rag-service | grep "OPENROUTER"

# Проверка на https://openrouter.ai/
```

### Посты не индексируются

```bash
# Ручная индексация
curl -X POST "http://localhost:8020/rag/index/user/YOUR_USER_ID"

# Проверка статуса
curl "http://localhost:8020/rag/stats/YOUR_USER_ID"
```

## Конфигурация

### Основные переменные (.env)

```bash
# Qdrant
QDRANT_API_KEY=your_qdrant_api_key

# OpenRouter (для RAG)
OPENROUTER_API_KEY=your_openrouter_api_key

# GigaChat (для embeddings)
GIGACHAT_CREDENTIALS=your_gigachat_credentials

# RAG настройки
RAG_TOP_K=10                    # Кол-во документов для контекста
RAG_MIN_SCORE=0.7               # Минимальный score релевантности
RAG_CONTEXT_WINDOW=4000         # Макс. размер контекста (tokens)
```

### Chunking (для длинных постов)

```bash
# GigaChat embeddings
EMBEDDING_MAX_TOKENS_GIGACHAT=1536      # Макс. токенов на chunk
EMBEDDING_OVERLAP_TOKENS_GIGACHAT=256   # Overlap между chunks

# Sentence-transformers (fallback)
EMBEDDING_MAX_TOKENS_FALLBACK=384
EMBEDDING_OVERLAP_TOKENS_FALLBACK=64
```

## Примеры использования

### Python

```python
import httpx

async def search_posts(query: str, user_id: int):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8020/rag/search",
            params={"query": query, "user_id": user_id, "limit": 5}
        )
        return response.json()

async def ask_question(query: str, user_id: int):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8020/rag/ask",
            json={"query": query, "user_id": user_id}
        )
        return response.json()
```

### JavaScript (n8n)

```javascript
// n8n HTTP Request node
const options = {
  method: 'POST',
  url: 'http://rag-service:8020/rag/ask',
  body: {
    query: $json.question,
    user_id: $json.user_id,
    context_limit: 10
  }
};

return $http(options);
```

## Полезные ссылки

- **API Docs:** http://localhost:8020/docs
- **Qdrant UI:** https://qdrant.produman.studio
- **OpenRouter:** https://openrouter.ai/
- **Документация:** `/home/ilyasni/n8n-server/n8n-installer/telethon/docs/`

## Следующие шаги

1. ✅ Проверьте индексацию ваших постов
2. ✅ Попробуйте поиск
3. ✅ Задайте вопрос через RAG
4. ✅ Сгенерируйте дайджест
5. 📱 Интегрируйте с Telegram ботом (опционально)
6. 🔧 Настройте n8n workflows
7. 📊 Мониторинг через логи

## Поддержка

Вопросы? Смотрите:
- `telethon/rag_service/README.md` - подробная документация
- `telethon/RAG_IMPLEMENTATION_SUMMARY.md` - отчет о реализации
- Логи: `docker logs rag-service`

