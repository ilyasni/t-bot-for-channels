# ✅ Дайджест настроен для пользователя 6 (Automaniac)

**Дата настройки:** 11 октября 2025  
**Статус:** ✅ Активен

---

## Пользователь

- **ID:** 6
- **Telegram ID:** 8124731874
- **Имя:** Automaniac
- **Каналов:** 1 (@banksta)
- **Постов:** 12+ (растет)

---

## Настройки дайджеста

```json
{
  "enabled": true,              ✅ Включен
  "frequency": "daily",          Ежедневно
  "time": "09:00",              9:00 утра
  "timezone": "Europe/Moscow",   МСК (UTC+3)
  "format": "markdown",          Markdown
  "max_posts": 200,             ← До 200 постов в дайджесте
  "delivery_method": "telegram",
  "channels": null,             Все каналы пользователя
  "tags": null                  Все теги
}
```

### Что это значит?

- **Каждый день в 9:00 МСК** система автоматически сгенерирует дайджест
- Включит **до 200 постов** за последние 24 часа (отсортированных по дате)
- Сгруппирует по каналам
- Отформатирует в **Markdown**

---

## Формат дайджеста

### Markdown (текущий)

```markdown
# 📰 Дайджест постов
**Период:** 10.10.2025 - 11.10.2025

## 📢 @banksta
*Постов: 12*

### 11.10.2025 12:19
Цены на бриллианты продолжают падать...
[Читать полностью →](https://t.me/banksta/79979)

### 11.10.2025 11:51
Крупнейшим торговым партнером...
```

### Альтернативные форматы

**HTML:**
```bash
curl -X PUT "http://localhost:8020/rag/digest/settings/6" \
  -H "Content-Type: application/json" \
  -d '{"format": "html"}'
```

**Plain Text:**
```bash
curl -X PUT "http://localhost:8020/rag/digest/settings/6" \
  -H "Content-Type: application/json" \
  -d '{"format": "plain"}'
```

---

## Управление дайджестом

### Изменить время отправки

```bash
# На 8:00 утра
curl -X PUT "http://localhost:8020/rag/digest/settings/6" \
  -H "Content-Type: application/json" \
  -d '{"time": "08:00"}'

# На 20:00 вечера
curl -X PUT "http://localhost:8020/rag/digest/settings/6" \
  -H "Content-Type: application/json" \
  -d '{"time": "20:00"}'
```

### Изменить частоту

```bash
# Еженедельно (по понедельникам)
curl -X PUT "http://localhost:8020/rag/digest/settings/6" \
  -H "Content-Type: application/json" \
  -d '{"frequency": "weekly", "days_of_week": [1]}'

# Вернуть ежедневно
curl -X PUT "http://localhost:8020/rag/digest/settings/6" \
  -H "Content-Type: application/json" \
  -d '{"frequency": "daily", "days_of_week": null}'
```

### Ограничить количество постов

```bash
# Только 50 самых свежих постов
curl -X PUT "http://localhost:8020/rag/digest/settings/6" \
  -H "Content-Type: application/json" \
  -d '{"max_posts": 50}'

# Все до 200 постов (текущее)
curl -X PUT "http://localhost:8020/rag/digest/settings/6" \
  -H "Content-Type: application/json" \
  -d '{"max_posts": 200}'

# Максимум 500 (лимит API)
curl -X PUT "http://localhost:8020/rag/digest/settings/6" \
  -H "Content-Type: application/json" \
  -d '{"max_posts": 500}'
```

### Выключить дайджест

```bash
curl -X PUT "http://localhost:8020/rag/digest/settings/6" \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

---

## Ручная генерация дайджеста

### За сегодня

```bash
curl -X POST "http://localhost:8020/rag/digest/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 6,
    "date_from": "2025-10-11T00:00:00Z",
    "date_to": "2025-10-11T23:59:59Z",
    "format": "markdown",
    "max_posts": 200
  }'
```

### За неделю

```bash
curl -X POST "http://localhost:8020/rag/digest/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 6,
    "date_from": "2025-10-05T00:00:00Z",
    "date_to": "2025-10-11T23:59:59Z",
    "format": "markdown",
    "max_posts": 500
  }'
```

### С фильтром по тегам

```bash
curl -X POST "http://localhost:8020/rag/digest/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 6,
    "date_from": "2025-10-10T00:00:00Z",
    "date_to": "2025-10-11T23:59:59Z",
    "tags": ["финансы", "экономика"],
    "max_posts": 200
  }'
```

---

## 📊 Статус индексации

```
✅ Проиндексировано: 12 постов
✅ Ошибок: 0
✅ GigaChat embeddings: работает
✅ Qdrant: подключен
```

### Векторный поиск доступен!

```bash
# Поиск постов о бриллиантах
curl "http://localhost:8020/rag/search?query=бриллианты&user_id=6&limit=5"

# Поиск постов о торговле
curl "http://localhost:8020/rag/search?query=торговля&user_id=6&limit=5"
```

### RAG-ответы

```bash
# Задать вопрос по постам
curl -X POST "http://localhost:8020/rag/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Что писали про бриллианты?",
    "user_id": 6,
    "context_limit": 10
  }'
```

---

## 🔔 Доставка дайджестов

### Текущий метод: Telegram

**TODO:** Интеграция с Telegram Bot для автоматической отправки

**Временное решение:** Используйте n8n workflow:

1. **Cron Trigger:** каждый день в 9:00
2. **HTTP Request:** 
   ```
   POST http://rag-service:8020/rag/digest/generate
   {
     "user_id": 6,
     "date_from": "{{$today.minus({days: 1}).startOf('day').toISO()}}",
     "date_to": "{{$today.startOf('day').toISO()}}",
     "format": "markdown",
     "max_posts": 200
   }
   ```
3. **Telegram Node:** Отправить `{{$json.digest}}` пользователю 8124731874

### Будущее: Email delivery

```bash
curl -X PUT "http://localhost:8020/rag/digest/settings/6" \
  -H "Content-Type: application/json" \
  -d '{
    "delivery_method": "email",
    "email": "user@example.com"
  }'
```

---

## 💡 Рекомендации

### Для 200+ постов в день

1. **Используйте фильтры по тегам:**
   ```bash
   # Только важные темы
   curl -X PUT "http://localhost:8020/rag/digest/settings/6" \
     -d '{"tags": ["важное", "срочное"]}'
   ```

2. **Несколько дайджестов:**
   - Утренний (9:00): важные новости (max_posts: 50)
   - Вечерний (20:00): полный дайджест (max_posts: 200)

3. **Разделение по каналам:**
   ```bash
   # Только определенные каналы
   curl -X PUT "http://localhost:8020/rag/digest/settings/6" \
     -d '{"channels": [1, 2, 3]}'
   ```

4. **AI-суммаризация (TODO):**
   - Вместо полных текстов - краткие саммари
   - Кластеризация по темам
   - Выделение ключевых фактов

---

## ✅ Готово!

Дайджест для пользователя **Automaniac** (ID: 6) полностью настроен:

- ✅ Включен
- ✅ Ежедневно в 09:00 МСК
- ✅ До 200 постов
- ✅ Формат Markdown
- ✅ Автоматическая индексация работает
- ✅ Векторный поиск доступен

**Следующий шаг:** Настройте n8n workflow для автоматической отправки или дождитесь интеграции с Telegram Bot.

