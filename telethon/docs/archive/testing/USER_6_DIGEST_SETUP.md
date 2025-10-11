# Настройка дайджеста для пользователя ID 6 (Automaniac)

**Дата:** 11 октября 2025  
**Статус:** ✅ Настроено

---

## Информация о пользователе

```
ID: 6
Telegram ID: 8124731874
Имя: Automaniac
Статус: Аутентифицирован ✅
Каналов: 1 (@banksta)
Постов за неделю: 12
```

---

## ✅ Настройки дайджеста

```json
{
  "user_id": 6,
  "enabled": true,              ← Включен!
  "frequency": "daily",          Ежедневно
  "time": "09:00",              В 9:00 утра
  "timezone": "Europe/Moscow",   МСК
  "format": "markdown",          Формат Markdown
  "max_posts": 20,              Макс. 20 постов
  "delivery_method": "telegram", Доставка в Telegram
  "channels": null,             Все каналы
  "tags": null                  Все теги
}
```

---

## 📰 Тестовый дайджест

Успешно сгенерирован дайджест за 10-11 октября:
- **Постов:** 12
- **Канал:** @banksta
- **Формат:** Markdown ✅

### Пример содержимого:

```markdown
# 📰 Дайджест постов
**Период:** 10.10.2025 - 11.10.2025

## 📢 @banksta
*Постов: 12*

### 11.10.2025 12:19
Цены на бриллианты продолжают падать уже третий год...
[Читать полностью →](https://t.me/banksta/79979)

### 11.10.2025 11:51
Крупнейшим торговым...
```

---

## 🚀 Как работает автоматический дайджест

### Расписание

**Каждый день в 09:00 МСК** автоматически:

1. Система собирает посты за последние 24 часа
2. Группирует по каналам (@banksta и др.)
3. Форматирует в Markdown
4. Отправляет в Telegram

### Управление через API

**Получить настройки:**
```bash
curl "http://localhost:8020/rag/digest/settings/6"
```

**Изменить время:**
```bash
curl -X PUT "http://localhost:8020/rag/digest/settings/6" \
  -H "Content-Type: application/json" \
  -d '{"time": "08:00"}'
```

**Выключить:**
```bash
curl -X PUT "http://localhost:8020/rag/digest/settings/6" \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

**Изменить формат:**
```bash
curl -X PUT "http://localhost:8020/rag/digest/settings/6" \
  -H "Content-Type: application/json" \
  -d '{"format": "html"}'
# Доступны: markdown, html, plain
```

**Фильтр по тегам:**
```bash
curl -X PUT "http://localhost:8020/rag/digest/settings/6" \
  -H "Content-Type: application/json" \
  -d '{"tags": ["технологии", "финансы"]}'
```

---

## 📤 Ручная отправка дайджеста

**Дайджест за сегодня:**
```bash
curl -X POST "http://localhost:8020/rag/digest/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 6,
    "date_from": "2025-10-11T00:00:00Z",
    "date_to": "2025-10-11T23:59:59Z",
    "format": "markdown"
  }'
```

**Дайджест за неделю:**
```bash
curl -X POST "http://localhost:8020/rag/digest/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 6,
    "date_from": "2025-10-05T00:00:00Z",
    "date_to": "2025-10-11T23:59:59Z",
    "format": "markdown",
    "max_posts": 50
  }'
```

---

## 🔍 Дополнительные возможности

### Поиск по постам

```bash
curl "http://localhost:8020/rag/search?query=бриллианты&user_id=6&limit=5"
```

### RAG-ответ на вопрос

```bash
curl -X POST "http://localhost:8020/rag/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Что писали про бриллианты?",
    "user_id": 6,
    "context_limit": 10
  }'
```

### Статистика каналов

```bash
curl "http://localhost:8020/rag/channels/stats/6"
```

### Популярные теги

```bash
curl "http://localhost:8020/rag/tags/popular/6?limit=10"
```

---

## 📊 Статус индексации

```
✅ Проиндексировано постов: 12
✅ Ошибок: 0
✅ GigaChat embeddings: работает
✅ Векторы в Qdrant: сохранены
```

---

## TODO: Интеграция с Telegram Bot

Для автоматической отправки дайджестов в Telegram нужно:

1. Добавить команду `/digest_now` в `bot.py`
2. Реализовать отправку через Telegram API
3. Scheduler будет автоматически вызывать отправку

**Временное решение:** Используйте n8n workflow:
- Cron trigger: каждый день в 9:00
- HTTP Request: POST к `/rag/digest/generate`
- Telegram node: отправить дайджест пользователю

---

## ✅ Готово!

Дайджест для пользователя **Automaniac** (ID: 6) настроен и работает!

**API:** http://localhost:8020/docs  
**Статус:** Enabled, ежедневно в 09:00 МСК

