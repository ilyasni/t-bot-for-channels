# 🔄 Система Retry для Тегирования

**Дата создания:** 11 октября 2025  
**Версия:** 1.0  
**Статус:** ✅ Активно

## 📋 Описание

Система автоматического повтора генерации тегов для постов с ошибками. Включает:
- **Retry механизм** с экспоненциальной задержкой
- **Fallback модели** OpenRouter
- **Отслеживание статуса** тегирования
- **API endpoints** для ручной перегенерации
- **Автоматическая очистка** неудачных попыток

## 🎯 Проблема

OpenRouter API может возвращать временные ошибки (502, 503, 504) из-за:
- Перегрузки upstream модели
- Сетевых проблем
- Недоступности конкретной модели
- Rate limiting

Без retry системы такие посты остаются без тегов навсегда.

## ✨ Решение

### 1. Отслеживание статуса в БД

Добавлены поля в модель `Post`:

```python
tagging_status = "pending"        # pending, success, failed, retrying, skipped
tagging_attempts = 0              # Количество попыток
last_tagging_attempt = None       # Время последней попытки
tagging_error = None              # Текст последней ошибки
```

**Статусы:**
- `pending` - ожидает тегирования (первая попытка)
- `success` - теги успешно сгенерированы
- `failed` - превышен лимит попыток
- `retrying` - временная ошибка, будет retry
- `skipped` - пост без текста, тегирование не требуется

### 2. Retry механизм с экспоненциальной задержкой

```python
# При ошибке API:
if retry_count < max_retries:
    delay = retry_delay * (2 ** retry_count)  # 2s, 4s, 8s...
    await asyncio.sleep(delay)
    return await generate_tags_for_text(text, retry_count + 1)
```

**Настройки:**
```env
TAGGING_MAX_RETRIES=3         # Retry при 5xx ошибках
TAGGING_RETRY_DELAY=2.0       # Начальная задержка
TAGGING_MAX_ATTEMPTS=5        # Общий лимит попыток для поста
```

### 3. Fallback модели

При исчерпании retry основной модели, система пробует fallback модели:

```python
fallback_models = [
    "google/gemini-2.0-flash-exp:free",      # Основная (рекомендуется)
    "meta-llama/llama-3.2-3b-instruct:free", # Fallback #1
    "qwen/qwen-2-7b-instruct:free",          # Fallback #2
    "google/gemma-2-9b-it:free"              # Fallback #3
]
```

**Логика:**
1. Попытка 1-3: Основная модель (`OPENROUTER_MODEL`)
2. Попытка 4: Fallback модель #1
3. Попытка 5: Fallback модель #2
4. После 5 попыток: статус `failed`

### 4. API Endpoints

#### GET `/users/{user_id}/posts/tagging_stats`

Получить статистику тегирования:

```bash
curl http://localhost:8010/users/1/posts/tagging_stats
```

**Ответ:**
```json
{
  "user_id": 1,
  "total_posts": 150,
  "posts_with_tags": 140,
  "posts_without_tags": 10,
  "posts_need_retry": 5,
  "stats_by_status": {
    "pending": 3,
    "success": 140,
    "failed": 2,
    "retrying": 5,
    "skipped": 0
  },
  "tagging_enabled": true,
  "max_retry_attempts": 5
}
```

#### POST `/users/{user_id}/posts/retry_tagging`

Повторная генерация тегов для постов с ошибками:

```bash
# Обычный режим (только посты не превысившие лимит)
curl -X POST "http://localhost:8010/users/1/posts/retry_tagging?limit=50"

# Принудительный режим (даже для превысивших лимит)
curl -X POST "http://localhost:8010/users/1/posts/retry_tagging?force=true&limit=50"
```

**Параметры:**
- `force` (bool, default=false) - принудительный retry даже для `failed` постов
- `limit` (int, default=50) - максимум постов для обработки

**Ответ:**
```json
{
  "user_id": 1,
  "status": "completed",
  "force_mode": false,
  "processed_limit": 50,
  "stats_after_retry": {
    "pending": 0,
    "success": 145,
    "failed": 2,
    "retrying": 3
  },
  "message": "Повторная генерация тегов завершена"
}
```

#### POST `/posts/{post_id}/regenerate_tags`

Перегенерация тегов для конкретного поста:

```bash
curl -X POST http://localhost:8010/posts/391/regenerate_tags
```

**Ответ:**
```json
{
  "post_id": 391,
  "success": true,
  "tags": ["золото", "инфляция", "экономика"],
  "tagging_status": "success",
  "tagging_attempts": 2,
  "last_tagging_attempt": "2025-10-11T10:30:00Z",
  "tagging_error": null
}
```

### ⚡ Background Processing

**Все retry endpoints работают асинхронно через FastAPI BackgroundTasks:**

- POST `/users/{user_id}/posts/retry_tagging` - немедленный ответ, обработка в фоне
- POST `/posts/{post_id}/regenerate_tags` - немедленный ответ, обработка в фоне

**Преимущества:**
- ✅ API endpoint отвечает мгновенно (< 100ms)
- ✅ Retry выполняется в фоне после отправки ответа
- ✅ Не блокирует другие запросы
- ✅ Не требует дополнительных зависимостей (Celery, Redis)

**Пример ответа:**
```json
{
  "status": "queued",
  "message": "Повторная генерация тегов запущена в фоне"
}
```

**Мониторинг статуса:**
```bash
# Проверить статус после запуска retry
curl http://localhost:8010/users/{user_id}/posts/tagging_stats
```

**Результат обработки** можно увидеть в:
- Логах: `docker logs -f telethon | grep TaggingService`
- Статистике: `GET /users/{user_id}/posts/tagging_stats`
- Конкретном посте: `GET /posts/{post_id}`

## 🔄 Workflow

### Автоматический процесс

```
Новый пост парсится
    ↓
tagging_status = "pending"
tagging_attempts = 0
    ↓
Попытка генерации тегов
    ↓
┌─────────────────┬────────────────────┐
│   Успех ✅      │   Ошибка ❌        │
│                 │                    │
│ status=success  │ attempts++         │
│ tags=[...]      │ status=retrying    │
│                 │                    │
│                 │ ┌─────────────┐   │
│                 │ │ Retry через │   │
│                 │ │ 2s, 4s, 8s  │   │
│                 │ └─────────────┘   │
│                 │                    │
│                 │ ┌─────────────┐   │
│                 │ │ Fallback    │   │
│                 │ │ модели      │   │
│                 │ └─────────────┘   │
│                 │                    │
│                 │ Если attempts≥5:  │
│                 │ status=failed     │
└─────────────────┴────────────────────┘
```

### Ручная перегенерация

```bash
# 1. Проверить статистику
curl http://localhost:8010/users/1/posts/tagging_stats

# 2. Запустить retry для failed постов
curl -X POST "http://localhost:8010/users/1/posts/retry_tagging?limit=50"

# 3. Принудительный retry (если нужно)
curl -X POST "http://localhost:8010/users/1/posts/retry_tagging?force=true&limit=10"

# 4. Перегенерировать конкретный пост
curl -X POST http://localhost:8010/posts/391/regenerate_tags
```

## 📊 Логи

### Успешная генерация
```
INFO:tagging_service:🏷️ TaggingService: Начинаем обработку 2 постов
INFO:httpx:HTTP Request: POST https://openrouter.ai/api/v1/chat/completions "HTTP/1.1 200 OK"
INFO:tagging_service:✅ TaggingService: Сгенерировано 5 тегов
INFO:tagging_service:✅ TaggingService: Пост 390 обновлен с тегами: ['золото', 'инфляция', 'экономика', 'благосостояние', 'спрос']
```

### Ошибка с retry
```
INFO:httpx:HTTP Request: POST https://openrouter.ai/api/v1/chat/completions "HTTP/1.1 200 OK"
ERROR:tagging_service:❌ TaggingService: API вернул пустой ответ
ERROR:tagging_service:Полный ответ API: {"error": {"message": "Upstream error from OpenInference: Error from model endpoint", "code": 502, "metadata": {"provider_name": "OpenInference"}}, "user_id": "..."}
INFO:tagging_service:⏳ TaggingService: Retry через 2.0с...
INFO:tagging_service:🔄 TaggingService: Попытка 2, используем fallback модель: meta-llama/llama-3.2-3b-instruct:free
INFO:tagging_service:✅ TaggingService: Сгенерировано 4 тегов
```

### Превышен лимит попыток
```
WARNING:tagging_service:⚠️ TaggingService: Не удалось сгенерировать теги для поста 391 (попытка 5)
WARNING:tagging_service:⚠️ TaggingService: Обработка завершена. Успешно: 1, Ошибок: 1
```

## 🛠️ Настройка

### 1. Переменные окружения

Отредактируйте `.env`:

```env
# Основная модель (рекомендуется самая стабильная)
OPENROUTER_MODEL=google/gemini-2.0-flash-exp:free

# Retry настройки
TAGGING_MAX_RETRIES=3          # 3 retry при 5xx ошибках
TAGGING_RETRY_DELAY=2.0        # Начальная задержка 2с
TAGGING_MAX_ATTEMPTS=5         # Максимум 5 попыток на пост

# Batch size
TAGGING_BATCH_SIZE=10          # Постов в батче
```

### 2. Fallback модели

Отредактируйте `tagging_service.py`:

```python
self.fallback_models = [
    "google/gemini-2.0-flash-exp:free",      # Основная
    "meta-llama/llama-3.2-3b-instruct:free", # Backup #1
    "qwen/qwen-2-7b-instruct:free",          # Backup #2
    "google/gemma-2-9b-it:free"              # Backup #3
]
```

**Рекомендации:**
- Используйте стабильные модели (Gemini, Llama)
- Избегайте нестабильных моделей (DeepSeek, GPT-OSS)
- Тестируйте fallback модели перед добавлением

### 3. Миграция БД

Запустите миграцию для добавления полей:

```bash
cd /home/ilyasni/n8n-server/n8n-installer/telethon
python scripts/migrations/add_tagging_status_fields.py
```

Миграция:
- ✅ Добавляет новые поля в таблицу `posts`
- ✅ Обновляет статус существующих постов
- ✅ Совместима с SQLite и PostgreSQL

## 📈 Мониторинг

### Проверка статуса тегирования

```bash
# Статистика пользователя
curl http://localhost:8010/users/1/posts/tagging_stats

# Посты с ошибками
curl http://localhost:8010/users/1/posts | jq '.posts[] | select(.tagging_status == "failed")'
```

### Анализ логов

```bash
# Ошибки тегирования
docker logs telethon 2>&1 | grep "TaggingService.*ERROR"

# Retry события
docker logs telethon 2>&1 | grep "Retry через"

# Успешные генерации
docker logs telethon 2>&1 | grep "Сгенерировано.*тегов"
```

## 🧪 Тестирование

### Тест retry механизма

1. Временно установите нестабильную модель:
   ```env
   OPENROUTER_MODEL=deepseek/deepseek-r1-distill-qwen-32b:free
   ```

2. Запустите парсинг:
   ```bash
   curl -X POST http://localhost:8010/users/1/channels/parse
   ```

3. Проверьте логи:
   ```bash
   docker logs -f telethon | grep -E "(Retry|fallback)"
   ```

4. Проверьте статистику:
   ```bash
   curl http://localhost:8010/users/1/posts/tagging_stats
   ```

### Тест ручной перегенерации

```bash
# 1. Найти посты с ошибками
curl http://localhost:8010/users/1/posts/tagging_stats

# 2. Запустить retry
curl -X POST "http://localhost:8010/users/1/posts/retry_tagging?limit=10"

# 3. Проверить результат
curl http://localhost:8010/users/1/posts/tagging_stats
```

## 🔧 Troubleshooting

### Все посты с статусом "failed"

**Причина:** Модель недоступна или API ключ невалиден.

**Решение:**
1. Проверьте API ключ: `echo $OPENROUTER_API_KEY`
2. Смените модель на стабильную: `OPENROUTER_MODEL=google/gemini-2.0-flash-exp:free`
3. Принудительный retry: `curl -X POST "http://localhost:8010/users/1/posts/retry_tagging?force=true"`

### Retry не работает

**Причина:** Ошибка не 5xx (например, 401, 429).

**Решение:**
- Для 401: проверьте API ключ
- Для 429 (rate limit): увеличьте `TAGGING_BATCH_SIZE` задержку между запросами
- Для других ошибок: проверьте логи для деталей

### Fallback модели не используются

**Причина:** Превышен `TAGGING_MAX_RETRIES` до fallback.

**Решение:**
- Увеличьте `TAGGING_MAX_RETRIES=5`
- Или уменьшите delay: `TAGGING_RETRY_DELAY=1.0`

### Посты не обновляются после retry

**Причина:** Достигнут `TAGGING_MAX_ATTEMPTS`.

**Решение:**
```bash
# Принудительный retry (игнорирует лимит)
curl -X POST "http://localhost:8010/users/1/posts/retry_tagging?force=true"
```

## 📝 Best Practices

1. **Выбор модели:**
   - Используйте `google/gemini-2.0-flash-exp:free` (наиболее стабильная)
   - Избегайте `deepseek` и `openai/gpt-oss` моделей

2. **Настройки retry:**
   - `TAGGING_MAX_RETRIES=3` - достаточно для временных ошибок
   - `TAGGING_MAX_ATTEMPTS=5` - даёт возможность попробовать fallback модели

3. **Мониторинг:**
   - Проверяйте статистику еженедельно
   - Настройте алерты на высокий процент `failed` постов

4. **Периодический retry:**
   - Запускайте ручной retry раз в неделю для `failed` постов
   - Используйте `force=true` только при необходимости

## 🔗 Связанные документы

- [AI Тегирование](AI_TAGGING.md)
- [API Documentation](../API.md)
- [Миграции БД](../migrations/README.md)
- [Troubleshooting](../troubleshooting/README.md)

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи: `docker logs telethon 2>&1 | grep "TaggingService"`
2. Получите статистику: `GET /users/{user_id}/posts/tagging_stats`
3. Проверьте переменные окружения: `.env`
4. Создайте issue в репозитории с подробным описанием

---

**Автор:** Telegram Channel Parser Team  
**Последнее обновление:** 11 октября 2025

