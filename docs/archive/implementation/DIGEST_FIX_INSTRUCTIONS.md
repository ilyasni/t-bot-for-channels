# Инструкция по исправлению проблем с дайджестами

**Дата:** 15 октября 2025  
**Проблема:** AI-дайджесты пустые из-за GigaChat Rate Limit (429 Too Many Requests)

---

## ✅ Что было исправлено

### 1. Добавлена защита от Rate Limit

**Файл:** `telethon/rag_service/ai_digest_generator.py`

**Изменения:**
- ✅ Задержка 500ms между обработкой тем
- ✅ Retry с exponential backoff (1s → 2s → 3s) для 429 ошибок
- ✅ Максимум 3 попытки для каждой темы
- ✅ Fallback на обычный дайджест если AI-дайджест пустой

**Эффект:**
- Уменьшение количества одновременных запросов к GigaChat
- Автоматический retry при Rate Limit
- Пользователь всегда получает дайджест (AI или обычный)

---

### 2. Добавлен Fallback дайджест

**Метод:** `_generate_fallback_digest()`

**Логика:**
1. Если AI-дайджест пустой (все темы вернули 0 результатов)
2. Генерируется обычный дайджест из БД
3. Топ-20 постов по просмотрам за период
4. Группировка по каналам
5. Уведомление пользователя: "AI-дайджест недоступен, показаны топ-посты"

**Эффект:**
- Пользователь ВСЕГДА получает дайджест
- Даже при полном отказе GigaChat API
- Даже при проблемах с Qdrant индексацией

---

## 🚀 Применение исправлений

### Шаг 1: Проверка текущего состояния

```bash
# Диагностика дайджестов
docker exec telethon python /app/scripts/debug_digest.py

# Проверка индексации
docker exec telethon python /app/scripts/check_qdrant.py
```

### Шаг 2: Применение патчей

**Файлы уже изменены локально. Нужно перестроить контейнер:**

```bash
cd /home/ilyasni/n8n-server/n8n-installer

# Остановить RAG Service
docker stop rag-service

# Перестроить с новым кодом
docker-compose up -d --build rag-service

# Проверить логи
docker logs -f rag-service
```

### Шаг 3: Тестирование

**Ручное тестирование дайджеста:**

```bash
# Для user 6
curl -X POST http://localhost:8020/rag/digest/generate \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 6,
    "date_from": "2025-10-14T00:00:00Z",
    "date_to": "2025-10-15T23:59:59Z",
    "format": "markdown",
    "max_posts": 20
  }'

# Для user 19
curl -X POST http://localhost:8020/rag/digest/generate \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 19,
    "date_from": "2025-10-14T00:00:00Z",
    "date_to": "2025-10-15T23:59:59Z",
    "format": "markdown",
    "max_posts": 20
  }'
```

**Ожидаемый результат:**
- ✅ Дайджест генерируется за 5-15 секунд
- ✅ Логи показывают: "Обработка темы 1/5", "Обработка темы 2/5", ...
- ✅ При Rate Limit: "⚠️ Rate limit для темы 'AI', повтор через 1.0s..."
- ✅ Если все темы пустые: "⚠️ AI-дайджест пустой, генерируем fallback"
- ✅ Дайджест содержит посты (AI или fallback)

### Шаг 4: Проверка завтрашнего дайджеста

**Дайджесты запланированы на 09:00 MSK:**
```bash
# Проверить расписание
docker exec rag-service python -c "
from rag_service.scheduler import digest_scheduler
jobs = digest_scheduler.scheduler.get_jobs()
for job in jobs:
    print(f'{job.id}: next run at {job.next_run_time}')
"

# Завтра в 09:00 проверить логи
docker logs rag-service --tail 100 | grep -E "(дайджест|Rate limit|fallback)"
```

---

## 🔧 Дополнительные рекомендации

### Краткосрочные улучшения (1-2 дня)

#### 1. Установить sentence-transformers для полного fallback

```bash
# Добавить в requirements.txt
echo "sentence-transformers>=2.2.0" >> telethon/rag_service/requirements.txt
echo "torch>=2.0.0" >> telethon/rag_service/requirements.txt

# Перестроить
docker-compose up -d --build rag-service
```

**Эффект:**
- При 429 от GigaChat → автоматический переход на локальные embeddings
- Дайджест всегда будет генерироваться (даже без GigaChat)

#### 2. Увеличить задержки между темами

**Если 500ms недостаточно:**
```python
# В ai_digest_generator.py строка 79
await asyncio.sleep(1.0)  # Увеличить до 1 секунды
```

#### 3. Уменьшить количество тем

**Для пользователей с большим количеством тем:**
```python
# В models.py изменить default
topics_limit = Column(Integer, default=3)  # Было 5, стало 3
```

**Или через API:**
```bash
curl -X PUT http://localhost:8020/rag/digest/settings/6 \
  -H "Content-Type: application/json" \
  -d '{"topics_limit": 3}'
```

### Среднесрочные улучшения (1-2 недели)

#### 4. Смещение времени дайджестов

**Избежать одновременной генерации для всех пользователей:**

```sql
-- User 6: 09:00
UPDATE digest_settings SET time = '09:00' WHERE user_id = 6;

-- User 19: 09:05 (сдвиг на 5 минут)
UPDATE digest_settings SET time = '09:05' WHERE user_id = 19;
```

#### 5. Кэширование embeddings для популярных тем

**Создать таблицу topic_embeddings:**
```sql
CREATE TABLE topic_embeddings (
    topic VARCHAR PRIMARY KEY,
    embedding VECTOR(768),
    created_at TIMESTAMP,
    expires_at TIMESTAMP
);
```

**Эффект:**
- Темы "AI", "авто", "технологии" → embeddings кэшируются на 7 дней
- Уменьшение запросов к GigaChat на 70-80%

---

## 📊 Мониторинг

### Метрики для отслеживания

```bash
# Количество 429 ошибок за день
docker logs rag-service --since 24h | grep -c "429"

# Количество успешных дайджестов
docker logs rag-service --since 24h | grep -c "✅ Дайджест успешно отправлен"

# Количество fallback дайджестов
docker logs rag-service --since 24h | grep -c "Fallback: обычный дайджест"
```

### Алерты

**Настроить оповещения (опционально):**
- 🔴 Критично: > 50% дайджестов используют fallback
- 🟡 Внимание: > 10 ошибок 429 за час
- 🟢 Норма: < 5% fallback дайджестов

---

## ❓ FAQ

### Q: Что если дайджест всё равно пустой?

**A:** Проверьте:
1. Есть ли посты в БД за период: `SELECT COUNT(*) FROM posts WHERE user_id=6 AND posted_at >= NOW() - INTERVAL '1 day'`
2. Работает ли индексация: `docker exec telethon python /app/scripts/check_qdrant.py`
3. Есть ли ошибки в логах: `docker logs rag-service --tail 100`

### Q: Как отключить AI-дайджест и использовать только обычный?

**A:** Через API:
```bash
curl -X PUT http://localhost:8020/rag/digest/settings/6 \
  -H "Content-Type: application/json" \
  -d '{"ai_summarize": false}'
```

### Q: Как увеличить количество постов в дайджесте?

**A:** Через API:
```bash
curl -X PUT http://localhost:8020/rag/digest/settings/6 \
  -H "Content-Type: application/json" \
  -d '{"max_posts": 50}'
```

### Q: Почему User 18 не получает дайджесты?

**A:** У него нет настроек дайджеста. Создать через API:
```bash
curl -X PUT http://localhost:8020/rag/digest/settings/18 \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "frequency": "daily",
    "time": "09:00",
    "max_posts": 20
  }'
```

Но у него также нет подписок на каналы и постов в БД.

---

## ✅ Чеклист после применения

- [ ] RAG Service перестроен с новым кодом
- [ ] Тестовый дайджест сгенерирован успешно
- [ ] Логи показывают задержки между темами
- [ ] Логи показывают retry при 429 ошибках
- [ ] Fallback дайджест работает (тест с отключенным GigaChat)
- [ ] Диагностические скрипты работают
- [ ] Завтрашние дайджесты запланированы корректно

---

**Автор:** AI Assistant  
**Контакты:** См. DIGEST_ISSUE_REPORT.md для полного анализа проблемы  
**Дата:** 15 октября 2025

