# Langfuse Setup - AI Tracing для Telegram Bot

Langfuse используется для трейсинга AI операций (OpenRouter, GigaChat, RAG search).

## 📋 Что трейсится

**Критичные AI операции:**
- ✅ **OpenRouter API calls** - команда `/ask` (через bot.py)
- ✅ **GigaChat embeddings** - генерация векторов (через rag_service/embeddings.py)
- ✅ **Qdrant vector search** - поиск в векторной БД (через rag_service/search.py)

**Метаданные trace:**
- User ID
- Query length
- Response length
- Provider (gigachat, openai, etc.)
- Results count
- Embedding dimensions

## 🚀 Quick Start

### 1. Получить Langfuse credentials

```bash
# Если используете self-hosted Langfuse (уже в docker-compose.yml)
# Зайдите в https://langfuse.produman.studio
# Создайте проект
# Скопируйте Public Key и Secret Key
```

### 2. Настроить environment variables

```bash
# В .env файле:
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-xxx
LANGFUSE_SECRET_KEY=sk-lf-xxx
LANGFUSE_HOST=https://langfuse.produman.studio
```

### 3. Rebuild контейнеры

```bash
docker compose up -d --build telethon rag-service
```

### 4. Проверить трейсинг

```bash
# 1. Выполнить /ask команду в боте
# 2. Зайти в Langfuse UI
# 3. Найти trace "bot_ask_command"
# 4. Увидеть метаданные (user_id, query_length, sources_count)
```

## 🔧 Как это работает

### Bot.py (команда /ask)

```python
with langfuse_client.trace_context(
    "bot_ask_command",
    metadata={
        "user_id": db_user.id,
        "query_length": len(query_text),
        "posts_count": posts_count
    }
) as trace:
    result = await self._call_rag_service("/rag/ask", ...)
    
    if trace and result:
        trace.update(metadata={
            "sources_count": len(result.get("sources", [])),
            "answer_length": len(result.get("answer", ""))
        })
```

### Embeddings.py (GigaChat)

```python
with langfuse_client.trace_context(
    "embedding_generation",
    metadata={"provider": "gigachat", "text_length": len(text)}
) as trace:
    response = await client.post(gigachat_url, json={...})
    embedding = result["data"][0]["embedding"]
    
    if trace:
        trace.update(metadata={"embedding_dim": len(embedding)})
```

### Search.py (RAG)

```python
with langfuse_client.trace_context(
    "rag_vector_search",
    metadata={
        "user_id": user_id,
        "query_length": len(query),
        "limit": limit,
        "provider": provider
    }
) as trace:
    search_results = await qdrant_client.search(...)
    
    if trace:
        trace.update(metadata={"results_count": len(search_results)})
```

## 📊 Что анализировать в Langfuse UI

### Performance
- **Latency** - сколько времени занимает каждая операция
- **Bottlenecks** - какая часть AI pipeline самая медленная
- **Provider comparison** - GigaChat vs fallback embeddings

### Quality
- **Scores** - можно добавить оценки качества ответов
- **User feedback** - track thumbs up/down
- **Error tracking** - какие запросы фейлятся

### Cost (если используете платные API)
- **Token usage** - сколько токенов потрачено
- **Cost per user** - кто больше всего тратит
- **API quotas** - контроль лимитов

## 🔒 Security Best Practices

```bash
# ❌ НЕ коммитьте credentials в git
echo "LANGFUSE_PUBLIC_KEY=..." >> .env
echo "LANGFUSE_SECRET_KEY=..." >> .env

# ✅ Используйте .env.example как template
cp .env.example .env
# Затем заполните реальные значения
```

## 🐛 Troubleshooting

### Langfuse не инициализируется

```bash
# Проверить что Langfuse контейнер запущен
docker ps | grep langfuse

# Проверить логи
docker logs langfuse-web

# Проверить что credentials корректны
curl -H "Authorization: Bearer $LANGFUSE_SECRET_KEY" \
  https://langfuse.produman.studio/api/health
```

### Traces не появляются

```bash
# 1. Проверить что LANGFUSE_ENABLED=true
docker exec telethon env | grep LANGFUSE

# 2. Проверить логи бота
docker logs telethon | grep Langfuse

# 3. Должна быть строка: "✅ Langfuse client initialized"
```

### Graceful degradation

```python
# Код работает БЕЗ Langfuse!
# Если langfuse не установлен - используется mock client
# Если LANGFUSE_ENABLED=false - трейсинг отключен
# Если ошибка при trace - логируется и игнорируется
```

## 📚 Best Practices

### 1. Selective Tracing
Трейсим только **критичные** операции:
- ✅ OpenRouter /ask (дорого, важно отслеживать)
- ✅ GigaChat embeddings (может быть медленным)
- ✅ RAG search (ключевая feature)
- ❌ Parsing (слишком часто, не AI)
- ❌ Database queries (используйте APM для этого)

### 2. Meaningful Metadata
```python
# ✅ Good
trace.update(metadata={
    "user_id": 123,
    "query_length": 45,
    "results_count": 5,
    "provider": "gigachat"
})

# ❌ Bad
trace.update(metadata={"data": "some data"})
```

### 3. Error Handling
```python
with langfuse_client.trace_context("operation") as trace:
    try:
        result = await some_ai_operation()
    except Exception as e:
        # Langfuse автоматически логирует ошибки
        raise
```

## 🔗 Полезные ссылки

- [Langfuse Documentation](https://langfuse.com/docs)
- [Langfuse Python SDK](https://github.com/langfuse/langfuse-python)
- [Best Practices](https://langfuse.com/docs/tracing/best-practices)
- [Context7 Langfuse Guide](/langfuse/langfuse-python)

## 🎯 Next Steps

1. ✅ **Setup Langfuse** (done)
2. ⏭️ **Add custom scores** - оценка качества ответов
3. ⏭️ **Add user feedback** - thumbs up/down в боте
4. ⏭️ **Cost tracking** - если используете платные API
5. ⏭️ **A/B testing** - сравнение разных промптов

