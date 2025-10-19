# Система автоматического тегирования постов

## 📋 Описание

Система автоматического тегирования использует OpenRouter API для генерации релевантных тегов для постов из телеграм каналов. Теги помогают классифицировать контент и упрощают дальнейший анализ в n8n.

## 🚀 Установка и настройка (Docker)

### 1. Настройка переменных окружения

Добавьте в файл `telethon/.env`:

```env
# OpenRouter AI settings (для автоматического тегирования постов)
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_MODEL=google/gemini-2.0-flash-exp:free
TAGGING_BATCH_SIZE=10
```

**Получение API ключа и настройка:**

1. Зарегистрируйтесь на https://openrouter.ai/
2. Перейдите в раздел API Keys
3. Создайте новый ключ
4. **Важно!** Настройте политику данных:
   - Перейдите на https://openrouter.ai/settings/privacy
   - Выберите "Allow free models" или подходящую политику
5. Скопируйте ключ в `telethon/.env`

**Доступные бесплатные модели (январь 2025):**
- `google/gemini-2.0-flash-exp:free` (рекомендуется)
- `meta-llama/llama-3.2-3b-instruct:free`
- `qwen/qwen-2-7b-instruct:free`

Проверить актуальный список: https://openrouter.ai/models?order=newest&supported_parameters=tools&max_price=0

### 2. Пересборка Docker образа

Зависимости уже включены в `requirements.txt`, пересоберите образ:

```bash
cd /home/ilyasni/n8n-server/n8n-installer
docker-compose -f docker-compose.yml -f docker-compose.override.yml build telethon
```

### 3. Миграция базы данных

Выполните миграцию внутри контейнера:

```bash
# Остановите контейнер для безопасной миграции
docker-compose -f docker-compose.yml -f docker-compose.override.yml stop telethon

# Запустите миграцию
docker-compose -f docker-compose.yml -f docker-compose.override.yml run --rm telethon python add_tags_column.py

# Или если контейнер запущен
docker exec telethon python add_tags_column.py
```

Скрипт автоматически:
- Добавит колонку `tags` в таблицу `posts`
- Проверит совместимость с существующими данными
- Покажет статистику по постам

### 4. Перезапуск системы

После миграции перезапустите сервисы:

```bash
cd /home/ilyasni/n8n-server/n8n-installer
docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d telethon telethon-bot
```

### 5. Проверка работы

Проверьте логи контейнера:

```bash
# Просмотр логов
docker logs telethon -f

# Проверка что сервис запущен
curl http://localhost:8010/posts/tags/stats
```

## 🎯 Как это работает

### Автоматическое тегирование

1. **При парсинге**: После завершения парсинга каналов автоматически запускается фоновая задача тегирования
2. **Обработка**: Каждый новый пост анализируется через LLM
3. **Генерация тегов**: Модель генерирует 3-7 релевантных тегов на русском языке
4. **Сохранение**: Теги сохраняются в поле `tags` как JSON массив

### Формат тегов

Теги хранятся в формате JSON массива:
```json
["технологии", "искусственный интеллект", "новости"]
```

## 📡 API Endpoints

### 1. Генерация тегов для одного поста

```http
POST /posts/{post_id}/generate_tags
```

**Пример:**
```bash
curl -X POST "http://localhost:8010/posts/123/generate_tags"
```

**Ответ:**
```json
{
  "status": "success",
  "post_id": 123,
  "tags": ["технологии", "новости", "AI"],
  "message": "Теги успешно сгенерированы"
}
```

### 2. Генерация тегов для всех постов пользователя

```http
POST /users/{telegram_id}/posts/generate_tags?limit=100
```

**Пример:**
```bash
curl -X POST "http://localhost:8010/users/123456789/posts/generate_tags?limit=50"
```

**Ответ:**
```json
{
  "status": "success",
  "user_id": 1,
  "telegram_id": 123456789,
  "posts_to_process": 25,
  "message": "Запущено тегирование 25 постов"
}
```

### 3. Получение постов с тегами

```http
GET /users/{telegram_id}/posts
```

Теперь включает поле `tags` в каждом посте:

```json
{
  "posts": [
    {
      "id": 1,
      "text": "Текст поста...",
      "tags": ["технологии", "новости"],
      "posted_at": "2024-01-15T10:30:00"
    }
  ]
}
```

### 4. Статистика по тегам

```http
GET /posts/tags/stats
```

**Ответ:**
```json
{
  "total_posts": 1000,
  "posts_with_tags": 750,
  "posts_without_tags": 250,
  "unique_tags_count": 150,
  "top_tags": [
    {"tag": "технологии", "count": 120},
    {"tag": "новости", "count": 95}
  ]
}
```

## 🔧 Использование в n8n

### Пример workflow для тегирования

```json
{
  "nodes": [
    {
      "name": "Получить новые посты",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "url": "http://telethon:8010/users/{{ $json.telegram_id }}/posts?hours_back=1",
        "method": "GET"
      }
    },
    {
      "name": "Фильтр постов без тегов",
      "type": "n8n-nodes-base.filter",
      "parameters": {
        "conditions": {
          "string": [
            {
              "value1": "={{ $json.tags }}",
              "operation": "isEmpty"
            }
          ]
        }
      }
    },
    {
      "name": "Генерация тегов",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "url": "http://telethon:8010/posts/{{ $json.id }}/generate_tags",
        "method": "POST"
      }
    }
  ]
}
```

### Анализ по тегам

```javascript
// Code node в n8n для группировки по тегам
const posts = $input.all();
const tagStats = {};

for (const post of posts) {
  if (post.json.tags) {
    for (const tag of post.json.tags) {
      tagStats[tag] = (tagStats[tag] || 0) + 1;
    }
  }
}

return Object.entries(tagStats).map(([tag, count]) => ({
  json: { tag, count }
}));
```

## 🎛️ Настройки

### Модель LLM

Вы можете изменить модель в `.env`:

```env
# Бесплатные модели (январь 2025)
OPENROUTER_MODEL=google/gemini-2.0-flash-exp:free
OPENROUTER_MODEL=meta-llama/llama-3.2-3b-instruct:free
OPENROUTER_MODEL=qwen/qwen-2-7b-instruct:free

# Платные модели (лучшее качество)
OPENROUTER_MODEL=openai/gpt-4o-mini
OPENROUTER_MODEL=anthropic/claude-3-5-haiku
OPENROUTER_MODEL=google/gemini-pro-1.5
```

**Важно:** Для бесплатных моделей настройте политику данных на https://openrouter.ai/settings/privacy

### Размер батча

Количество постов обрабатываемых одновременно:

```env
TAGGING_BATCH_SIZE=10  # По умолчанию
```

Уменьшите значение если получаете rate limit ошибки.

### Задержка между запросами

В `tagging_service.py` параметр `delay_between_requests`:

```python
await tagging_service.process_posts_batch(
    post_ids,
    delay_between_requests=1.0  # Секунды между запросами
)
```

## 🐛 Решение проблем

### Ошибка 404 "No endpoints found matching your data policy"

Это самая частая ошибка! Решение:

1. **Настройте политику данных:**
   - Откройте https://openrouter.ai/settings/privacy
   - Включите "Allow free models" или выберите подходящую политику
   - Сохраните изменения

2. **Используйте актуальную модель:**
   ```bash
   # В telethon/.env измените на:
   OPENROUTER_MODEL=google/gemini-2.0-flash-exp:free
   ```

3. **Перезапустите контейнер:**
   ```bash
   docker restart telethon
   ```

### Теги не генерируются

1. **Проверьте API ключ в контейнере:**
   ```bash
   docker exec telethon env | grep OPENROUTER_API_KEY
   ```

2. **Проверьте логи контейнера:**
   ```bash
   # Реальное время
   docker logs telethon -f | grep "TaggingService"
   
   # Или в файлах логов
   docker exec telethon cat logs/parser.log | grep "TaggingService"
   ```

3. **Проверьте баланс на OpenRouter:**
   - Зайдите на https://openrouter.ai/
   - Проверьте Credits

### Ошибка "Rate limit exceeded"

Обновите переменную окружения в `telethon/.env`:

```env
TAGGING_BATCH_SIZE=5  # Уменьшите с 10 до 5
```

Затем перезапустите контейнер:

```bash
docker-compose -f docker-compose.yml -f docker-compose.override.yml restart telethon
```

### Некорректные теги

Измените промпт в `telethon/tagging_service.py` и пересоберите образ:

```python
prompt = f"""Проанализируй следующий текст и определи 3-7 релевантных тегов...

Требования:
- Более специфичные требования
- Примеры тегов для вашей тематики
"""
```

Затем:
```bash
docker-compose -f docker-compose.yml -f docker-compose.override.yml build telethon
docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d telethon
```

## 📊 Мониторинг

### Просмотр статистики

```bash
curl http://localhost:8010/posts/tags/stats | jq
```

### Проверка постов без тегов

```bash
# SQL запрос (SQLite) внутри контейнера
docker exec telethon sqlite3 /app/data/telethon_bot.db "SELECT COUNT(*) FROM posts WHERE tags IS NULL"

# Или для подробной информации
docker exec telethon sqlite3 /app/data/telethon_bot.db "SELECT id, channel_id, LEFT(text, 50) as text_preview FROM posts WHERE tags IS NULL LIMIT 10"
```

### Логи тегирования

```bash
# Реальное время
docker logs telethon -f | grep "TaggingService"

# Последние 100 строк
docker logs telethon --tail 100 | grep "TaggingService"
```

## 🔐 Безопасность

- API ключ хранится в `.env` и не передается в репозиторий
- Используйте `.gitignore` для защиты `.env`
- Для продакшена используйте переменные окружения системы

## 📚 Дополнительная информация

- [OpenRouter Documentation](https://openrouter.ai/docs)
- [n8n Workflow Examples](https://n8n.io/workflows)
- [Основной README](README.md)

## 🤝 Поддержка

При возникновении проблем:
1. Проверьте логи
2. Убедитесь что миграция выполнена
3. Проверьте настройки в `.env`
4. Создайте issue с описанием проблемы

