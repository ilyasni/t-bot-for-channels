# 🔧 Быстрое решение: Ошибки тегирования постов

## 🎯 Проблема

Периодически возникают ошибки при тегировании постов через OpenRouter API:

```
ERROR:tagging_service:❌ TaggingService: API вернул пустой ответ
ERROR:tagging_service:Полный ответ API: {"error": {"message": "Upstream error from OpenInference: Error from model endpoint", "code": 502, ...}}
```

**Причина:** Временная недоступность upstream модели на стороне OpenRouter (ошибка 502).

## ✅ Решение (3 шага)

### Шаг 1: Миграция БД

Добавляет поля для отслеживания статуса тегирования:

```bash
cd /home/ilyasni/n8n-server/n8n-installer/telethon
python scripts/migrations/add_tagging_status_fields.py
```

**Результат:**
- ✅ Новые поля: `tagging_status`, `tagging_attempts`, `last_tagging_attempt`, `tagging_error`
- ✅ Автоматическое обновление существующих постов
- ✅ Совместимо с SQLite и PostgreSQL

### Шаг 2: Обновление конфигурации

Добавьте в `.env` (если еще нет):

```env
# Retry настройки для тегирования
TAGGING_MAX_RETRIES=3          # Количество retry при 5xx ошибках
TAGGING_RETRY_DELAY=2.0        # Начальная задержка (экспоненциально растет: 2s, 4s, 8s)
TAGGING_MAX_ATTEMPTS=5         # Максимум попыток для одного поста

# Используйте стабильную модель (рекомендуется)
OPENROUTER_MODEL=google/gemini-2.0-flash-exp:free
```

### Шаг 3: Перезапуск контейнеров

```bash
# Пересборка и перезапуск
cd /home/ilyasni/n8n-server/n8n-installer/telethon
./scripts/utils/dev.sh rebuild

# Или через docker-compose (из корня проекта)
cd /home/ilyasni/n8n-server/n8n-installer
docker compose -p localai restart telethon telethon-bot
```

## 🔄 Использование

### Автоматический retry

После обновления система автоматически:
- ✅ Повторяет генерацию при ошибках 502/503/504
- ✅ Использует экспоненциальную задержку (2s, 4s, 8s...)
- ✅ Переключается на fallback модели при неудаче основной
- ✅ Отслеживает статус каждого поста

### Ручная перегенерация тегов

#### 1. Проверить статистику

```bash
curl http://localhost:8010/users/{user_id}/posts/tagging_stats
```

**Пример ответа:**
```json
{
  "total_posts": 150,
  "posts_with_tags": 140,
  "posts_need_retry": 5,
  "stats_by_status": {
    "success": 140,
    "failed": 2,
    "retrying": 5,
    "pending": 3
  }
}
```

#### 2. Запустить retry для failed постов

```bash
# Обычный режим (только для постов не превысивших лимит)
curl -X POST "http://localhost:8010/users/{user_id}/posts/retry_tagging?limit=50"

# Принудительный режим (даже для превысивших лимит)
curl -X POST "http://localhost:8010/users/{user_id}/posts/retry_tagging?force=true&limit=50"
```

#### 3. Перегенерация конкретного поста

```bash
curl -X POST http://localhost:8010/posts/{post_id}/regenerate_tags
```

## 📊 Новые возможности

### 1. Retry с экспоненциальной задержкой

```
Попытка 1: Ошибка 502 → ждем 2s
Попытка 2: Ошибка 502 → ждем 4s
Попытка 3: Ошибка 502 → ждем 8s
Попытка 4: Пробуем fallback модель
```

### 2. Fallback модели

```python
Основная:  google/gemini-2.0-flash-exp:free
Fallback1: meta-llama/llama-3.2-3b-instruct:free
Fallback2: qwen/qwen-2-7b-instruct:free
Fallback3: google/gemma-2-9b-it:free
```

### 3. Отслеживание статуса

Каждый пост теперь имеет:
- **status**: `pending`, `success`, `failed`, `retrying`, `skipped`
- **attempts**: количество попыток
- **last_attempt**: время последней попытки
- **error**: текст ошибки (если есть)

### 4. API endpoints

| Endpoint | Описание |
|----------|----------|
| `GET /users/{user_id}/posts/tagging_stats` | Статистика тегирования |
| `POST /users/{user_id}/posts/retry_tagging` | Retry для failed постов |
| `POST /posts/{post_id}/regenerate_tags` | Перегенерация конкретного поста |

## 🔍 Мониторинг

### Логи успешного retry

```
INFO:tagging_service:🏷️ TaggingService: Начинаем обработку 2 постов
ERROR:tagging_service:❌ TaggingService: API вернул пустой ответ
INFO:tagging_service:⏳ TaggingService: Retry через 2.0с...
INFO:tagging_service:🔄 TaggingService: Попытка 2, используем fallback модель: meta-llama/llama-3.2-3b-instruct:free
INFO:tagging_service:✅ TaggingService: Сгенерировано 4 тегов
INFO:tagging_service:✅ TaggingService: Обработка завершена. Успешно: 2, Ошибок: 0
```

### Просмотр логов

```bash
# Live логи
docker logs -f telethon | grep "TaggingService"

# Поиск ошибок
docker logs telethon 2>&1 | grep "TaggingService.*ERROR"

# Retry события
docker logs telethon 2>&1 | grep -E "(Retry через|fallback модель)"
```

## 🐛 Troubleshooting

### Проблема: Все посты с статусом "failed"

**Решение:**
```bash
# 1. Проверьте API ключ
echo $OPENROUTER_API_KEY

# 2. Смените на стабильную модель в .env
OPENROUTER_MODEL=google/gemini-2.0-flash-exp:free

# 3. Перезапустите
docker compose -p localai restart telethon

# 4. Принудительный retry
curl -X POST "http://localhost:8010/users/{user_id}/posts/retry_tagging?force=true"
```

### Проблема: Retry не работает

**Проверьте:**
1. Логи: `docker logs telethon 2>&1 | grep "Retry"`
2. Переменные: `docker exec telethon env | grep TAGGING`
3. Статус: `curl http://localhost:8010/users/{user_id}/posts/tagging_stats`

### Проблема: Fallback модели не используются

**Причина:** Превышен `TAGGING_MAX_RETRIES` до fallback.

**Решение:** Увеличьте в `.env`:
```env
TAGGING_MAX_RETRIES=5  # Было: 3
```

## 📚 Документация

Подробная документация: [TAGGING_RETRY_SYSTEM.md](docs/features/TAGGING_RETRY_SYSTEM.md)

Включает:
- Детальное описание архитектуры
- Workflow диаграммы
- Примеры использования
- Best practices
- Расширенное troubleshooting

## 🎉 Результат

После внедрения системы:
- ✅ Временные ошибки API обрабатываются автоматически
- ✅ Fallback на альтернативные модели при недоступности основной
- ✅ Полная прозрачность статуса тегирования
- ✅ Возможность ручной перегенерации через API
- ✅ Отслеживание всех попыток в БД

---

**Дата создания:** 11 октября 2025  
**Версия:** 1.0

