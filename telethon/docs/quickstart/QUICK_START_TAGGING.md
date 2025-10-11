# 🏷️ Быстрый старт: Система тегирования

## За 3 шага

### 1️⃣ Настройте API ключ

Добавьте в `telethon/.env`:
```env
OPENROUTER_API_KEY=sk-or-v1-ваш_ключ_здесь
OPENROUTER_MODEL=google/gemini-2.0-flash-exp:free
```

**Важно!** 
1. Получить ключ: https://openrouter.ai/
2. Настройте политику: https://openrouter.ai/settings/privacy
3. Включите "Allow free models"

### 2️⃣ Запустите установку

```bash
cd /home/ilyasni/n8n-server/n8n-installer/telethon
./setup_tagging.sh
```

### 3️⃣ Готово! 🎉

Теги автоматически генерируются при парсинге.

---

## Проверка работы

```bash
# Статистика
curl http://localhost:8010/posts/tags/stats | jq

# Логи
docker logs telethon -f | grep TaggingService
```

---

## Ручная генерация тегов

```bash
# Для одного поста
curl -X POST "http://localhost:8010/posts/1/generate_tags"

# Для всех постов пользователя
curl -X POST "http://localhost:8010/users/123456789/posts/generate_tags"
```

---

## Использование в n8n

Импортируйте готовый workflow:
```
telethon/n8n_tagging_workflow_example.json
```

Или получите посты с тегами через HTTP Request:
```
GET http://telethon:8010/users/{telegram_id}/posts
```

Ответ включает теги:
```json
{
  "posts": [
    {
      "id": 1,
      "text": "...",
      "tags": ["технологии", "AI", "новости"]
    }
  ]
}
```

---

## Решение проблем

### Теги не генерируются

1. Проверьте API ключ:
   ```bash
   docker exec telethon env | grep OPENROUTER_API_KEY
   ```

2. Проверьте логи:
   ```bash
   docker logs telethon -f | grep "TaggingService"
   ```

3. Проверьте баланс на https://openrouter.ai/

### Rate limit

Уменьшите batch size в `.env`:
```env
TAGGING_BATCH_SIZE=5
```

Перезапустите:
```bash
docker-compose -f ../docker-compose.yml -f ../docker-compose.override.yml restart telethon
```

---

## Подробная документация

📖 [TAGGING_README.md](TAGGING_README.md) - Полное руководство
📋 [CHANGELOG_TAGGING.md](CHANGELOG_TAGGING.md) - История изменений

---

## Команды Docker

```bash
# Базовая директория
cd /home/ilyasni/n8n-server/n8n-installer

# Пересборка
docker-compose -f docker-compose.yml -f docker-compose.override.yml build telethon

# Миграция
docker-compose -f docker-compose.yml -f docker-compose.override.yml run --rm telethon python add_tags_column.py

# Перезапуск
docker-compose -f docker-compose.yml -f docker-compose.override.yml restart telethon

# Логи
docker logs telethon -f
```

