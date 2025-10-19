# 🎉 Система автоматического тегирования готова!

## ✅ Что было сделано

### 📦 Код
- ✅ Обновлена модель `Post` - добавлено поле `tags` (JSON)
- ✅ Создан сервис `tagging_service.py` для работы с OpenRouter API
- ✅ Интегрировано с парсером - автоматическое тегирование новых постов
- ✅ Добавлены API endpoints для управления тегами
- ✅ Обновлены зависимости - добавлен `httpx`

### 📄 Документация
- ✅ `TAGGING_README.md` - полное руководство
- ✅ `QUICK_START_TAGGING.md` - быстрый старт
- ✅ `CHANGELOG_TAGGING.md` - список изменений
- ✅ `n8n_tagging_workflow_example.json` - готовый workflow

### 🛠️ Инструменты
- ✅ `add_tags_column.py` - скрипт миграции БД
- ✅ `setup_tagging.sh` - автоматическая установка

---

## 🚀 Следующие шаги для запуска

### Вариант 1: Автоматическая установка (рекомендуется)

```bash
# 1. Настройте API ключ
nano /home/ilyasni/n8n-server/n8n-installer/telethon/.env
# Добавьте: OPENROUTER_API_KEY=sk-or-v1-ваш_ключ

# 2. Запустите автоматическую установку
cd /home/ilyasni/n8n-server/n8n-installer/telethon
./setup_tagging.sh
```

### Вариант 2: Ручная установка

```bash
# 1. Настройте переменные окружения
cd /home/ilyasni/n8n-server/n8n-installer
nano telethon/.env

# Добавьте:
# OPENROUTER_API_KEY=sk-or-v1-ваш_ключ_здесь
# OPENROUTER_MODEL=openai/gpt-oss-20b:free
# TAGGING_BATCH_SIZE=10

# 2. Пересоберите Docker образ
docker-compose -f docker-compose.yml -f docker-compose.override.yml build telethon

# 3. Выполните миграцию БД
docker-compose -f docker-compose.yml -f docker-compose.override.yml stop telethon
docker-compose -f docker-compose.yml -f docker-compose.override.yml run --rm telethon python add_tags_column.py

# 4. Запустите сервисы
docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d telethon telethon-bot
```

---

## 🔑 Получение API ключа OpenRouter

1. Зарегистрируйтесь на https://openrouter.ai/
2. Перейдите в раздел **API Keys**
3. Нажмите **Create Key**
4. **Важно!** Настройте политику данных:
   - Откройте https://openrouter.ai/settings/privacy
   - Включите "Allow free models"
   - Сохраните изменения
5. Скопируйте ключ (начинается с `sk-or-v1-`)
6. Добавьте в `telethon/.env`:
   ```env
   OPENROUTER_API_KEY=sk-or-v1-ваш_ключ_здесь
   OPENROUTER_MODEL=google/gemini-2.0-flash-exp:free
   ```

**Рекомендуемые бесплатные модели (январь 2025):**
- `google/gemini-2.0-flash-exp:free` (рекомендуется)
- `meta-llama/llama-3.2-3b-instruct:free`
- `qwen/qwen-2-7b-instruct:free`

Актуальный список: https://openrouter.ai/models?max_price=0

---

## 📊 Проверка работы

### 1. Проверьте статус сервиса
```bash
docker logs telethon -f
```

### 2. Получите статистику по тегам
```bash
curl http://localhost:8010/posts/tags/stats | jq
```

Пример ответа:
```json
{
  "total_posts": 150,
  "posts_with_tags": 120,
  "posts_without_tags": 30,
  "unique_tags_count": 45,
  "top_tags": [
    {"tag": "технологии", "count": 35},
    {"tag": "новости", "count": 28}
  ]
}
```

### 3. Проверьте логи тегирования
```bash
docker logs telethon | grep "TaggingService"
```

---

## 🎯 Как это работает

### Автоматически
После парсинга каналов система автоматически:
1. Собирает ID новых постов
2. Запускает фоновое тегирование
3. Анализирует каждый пост через LLM
4. Сохраняет 3-7 тегов в JSON формате

### Вручную через API

#### Генерация тегов для одного поста
```bash
curl -X POST "http://localhost:8010/posts/1/generate_tags"
```

#### Генерация тегов для всех постов пользователя
```bash
curl -X POST "http://localhost:8010/users/123456789/posts/generate_tags"
```

#### Получение постов с тегами
```bash
curl "http://localhost:8010/users/123456789/posts?hours_back=24" | jq
```

---

## 🔗 Интеграция с n8n

### Готовый Workflow
Импортируйте файл:
```
telethon/n8n_tagging_workflow_example.json
```

### Использование в HTTP Request
```javascript
// n8n HTTP Request Node
GET http://telethon:8010/users/{{ $json.telegram_id }}/posts

// Ответ включает теги
{
  "posts": [
    {
      "id": 1,
      "text": "Новость о технологиях...",
      "tags": ["технологии", "AI", "новости"],
      "url": "https://t.me/channel/123",
      "posted_at": "2024-01-15T10:30:00"
    }
  ]
}
```

### Фильтрация по тегам в n8n
```javascript
// Code Node - фильтр постов с тегом "технологии"
const items = $input.all();
return items.filter(item => 
  item.json.tags && item.json.tags.includes("технологии")
);
```

---

## 🐛 Решение проблем

### ❌ Ошибка 404 "No endpoints found matching your data policy"

**Самая частая проблема!** Решается за минуту:

1. Откройте https://openrouter.ai/settings/privacy
2. Включите "Allow free models"
3. Сохраните изменения
4. Перезапустите контейнер:
   ```bash
   docker restart telethon
   ```

### Теги не генерируются

**Проверка 1:** API ключ установлен?
```bash
docker exec telethon env | grep OPENROUTER_API_KEY
```

**Проверка 2:** Правильная модель?
```bash
docker exec telethon env | grep OPENROUTER_MODEL
# Должно быть: google/gemini-2.0-flash-exp:free
```

**Проверка 3:** Есть ли ошибки в логах?
```bash
docker logs telethon -f | grep -i error
```

**Проверка 4:** Баланс на OpenRouter
- Зайдите на https://openrouter.ai/credits
- Проверьте Credits

### Rate Limit Exceeded

Уменьшите нагрузку в `telethon/.env`:
```env
TAGGING_BATCH_SIZE=5  # было 10
```

Перезапустите:
```bash
docker-compose -f docker-compose.yml -f docker-compose.override.yml restart telethon
```

### Качество тегов низкое

Попробуйте другую модель в `.env`:
```env
# Платные модели (лучше качество)
OPENROUTER_MODEL=openai/gpt-3.5-turbo
# или
OPENROUTER_MODEL=anthropic/claude-3-haiku
```

---

## 📚 Документация

| Документ | Описание |
|----------|----------|
| `QUICK_START_TAGGING.md` | Быстрый старт за 3 шага |
| `TAGGING_README.md` | Полное руководство |
| `CHANGELOG_TAGGING.md` | История изменений |
| `n8n_tagging_workflow_example.json` | Готовый n8n workflow |

---

## 📋 API Endpoints

| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | `/users/{telegram_id}/posts` | Получить посты (с тегами) |
| POST | `/posts/{post_id}/generate_tags` | Генерация тегов для поста |
| POST | `/users/{telegram_id}/posts/generate_tags` | Генерация для всех постов |
| GET | `/posts/tags/stats` | Статистика по тегам |

---

## 🔧 Полезные команды

```bash
# Логи в реальном времени
docker logs telethon -f | grep "TaggingService"

# Статистика по тегам
curl http://localhost:8010/posts/tags/stats | jq

# Количество постов без тегов
docker exec telethon sqlite3 /app/data/telethon_bot.db \
  "SELECT COUNT(*) FROM posts WHERE tags IS NULL"

# Пересборка после изменений
docker-compose -f docker-compose.yml -f docker-compose.override.yml build telethon
docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d telethon
```

---

## ⚙️ Настройки по умолчанию

```env
OPENROUTER_MODEL=openai/gpt-oss-20b:free  # Бесплатная модель
TAGGING_BATCH_SIZE=10                      # Постов за раз
```

**Рекомендации:**
- Для бесплатной модели: `TAGGING_BATCH_SIZE=5-10`
- Для платных моделей: `TAGGING_BATCH_SIZE=20-50`
- Задержка между запросами: 1 секунда (в коде)

---

## 🎊 Готово!

Система автоматического тегирования настроена и готова к использованию.

При парсинге каналов теги будут генерироваться автоматически.

**Наслаждайтесь организованными данными! 🚀**

