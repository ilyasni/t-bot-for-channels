# 🔍 Аудит сервисов удаления постов

**Дата:** 15 октября 2025  
**Критичность:** 🔴 ВЫСОКАЯ  
**Проблема:** Автоматическое удаление постов пользователей

---

## ⚠️ НАЙДЕНО: Автоматическое удаление ВКЛЮЧЕНО!

```bash
CLEANUP_ENABLED=true  # ← ВКЛЮЧЕН!
```

---

## 🔴 Сервисы, которые удаляют посты

### 1. CleanupService (`telethon/cleanup_service.py`)

**Что удаляет:**
- Посты старше `(last_post_date - retention_days)` для каждого канала
- По умолчанию: `retention_days = 30` дней

**Когда запускается:**
- **Автоматически:** Каждый день в 03:00 (если `CLEANUP_ENABLED=true`)
- **Вручную:** Через API endpoints

**Логика:**
```python
# Для каждого канала:
last_post_date = max(Post.posted_at)  # Например, 2025-10-14
cutoff_date = last_post_date - timedelta(days=retention_days)  # 2025-09-14
# Удаляет: Post.posted_at < 2025-09-14
```

**Файлы:**
- `telethon/cleanup_service.py` - Основная логика
- `telethon/maintenance/cleanup_scheduler.py` - Scheduler (3:00 AM)

---

### 2. DataRetentionService (`telethon/maintenance/data_retention.py`)

**Что удаляет:**
- Посты старше `retention_days` (глобально, по умолчанию 120 дней)
- Также удаляет из Neo4j и Qdrant

**Когда запускается:**
- **Автоматически:** Если `CLEANUP_ENABLED=true` (через cleanup_scheduler)
- **Вручную:** Через maintenance скрипты

**Логика:**
```python
cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
# Удаляет: Post.posted_at < cutoff_date
```

**Sync cleanup:**
1. PostgreSQL → удаляет посты
2. Neo4j → удаляет Post nodes
3. Qdrant → удаляет vectors

---

## 🔎 Текущее состояние

### User 6:
- **retention_days:** 30 дней
- **Посты 720-728:** posted 2025-10-14 (1 день назад)
- **Статус:** НЕ ДОЛЖНЫ удаляться (свежие)
- **Состояние в БД:** ✅ Существуют, status=pending

### Cleanup Schedule:
- **Включен:** ✅ CLEANUP_ENABLED=true
- **Расписание:** 03:00 каждый день
- **Последний запуск:** Проверить логи

---

## ❌ Проблема с 404 ошибками

### Причина 404:

**Cleanup вызывал неправильный порт:**
```python
# БЫЛО:
telethon_api_url = "http://telethon:8001"  # ← Auth web server (QR login)

# СТАЛО:
telethon_api_url = "http://telethon:8010"  # ← Main FastAPI app
```

**Структура portов telethon:**
- `8001` - auth_web_server (QR логин)
- `8010` - main.app (FastAPI с endpoints для тегирования)

**Исправлено:** `telethon/rag_service/cleanup_service.py` строка 56

---

## 🛡️ Защита от случайного удаления

### Текущие safeguards:

1. **Минимальный retention:**
   ```python
   self.min_retention_days = 1  # Нельзя удалить посты свежее 1 дня
   ```

2. **Валидация retention_days:**
   ```python
   if retention_days < self.min_retention_days:
       retention_days = self.min_retention_days
   ```

3. **Per-channel cleanup:**
   - Удаление только для конкретных каналов
   - Рассчитывается от `last_post_date` канала

4. **User_id filtering:**
   - Удаляются только посты конкретного пользователя
   - Нет cross-user deletion

---

## 🚨 РЕКОМЕНДАЦИИ

### КРИТИЧНО: Отключить автоматическое удаление

**Если не нужно удалять посты пользователей:**

```bash
# В .env файле:
CLEANUP_ENABLED=false

# Перезапустить telethon
docker restart telethon
```

**Проверка:**
```bash
docker exec telethon python -c "import os; print(f'CLEANUP_ENABLED={os.getenv(\"CLEANUP_ENABLED\")}')"
# Должно быть: CLEANUP_ENABLED=false
```

---

### ВАЖНО: Увеличить retention_days

**Если нужно хранить посты дольше:**

```sql
-- Для всех пользователей:
UPDATE users SET retention_days = 365 WHERE id > 0;

-- Для конкретного пользователя:
UPDATE users SET retention_days = 365 WHERE id = 6;
```

**Рекомендуемые значения:**
- 365 дней (1 год) - для долгосрочного хранения
- 180 дней (6 месяцев) - баланс между хранением и размером БД
- 90 дней (3 месяца) - минимум для аналитики

---

## 📊 Мониторинг удалений

### Проверить что было удалено:

```bash
# Логи cleanup
docker logs telethon | grep -E "(удалено.*постов|posts deleted)" -i

# Последний cleanup
docker logs telethon | grep "🧹 Запуск очистки" -A10
```

### Статистика по пользователю:

```sql
-- Посты за последние 30 дней
SELECT COUNT(*) FROM posts 
WHERE user_id = 6 
AND posted_at > NOW() - INTERVAL '30 days';

-- Самый старый пост
SELECT MIN(posted_at) FROM posts WHERE user_id = 6;

-- Самый новый пост
SELECT MAX(posted_at) FROM posts WHERE user_id = 6;
```

---

## ✅ Итоговые действия

### Для предотвращения удаления постов:

1. **Отключить cleanup (если не нужен):**
   ```bash
   # В .env:
   CLEANUP_ENABLED=false
   docker restart telethon
   ```

2. **Или увеличить retention:**
   ```sql
   UPDATE users SET retention_days = 365;  # 1 год
   ```

3. **Мониторинг:**
   ```bash
   # Проверять логи каждый день после 03:00:
   docker logs telethon | grep "🧹 Очистка завершена"
   ```

---

## 🔐 Безопасность

### Кто может удалять посты:

1. **CleanupScheduler** - автоматически (03:00 AM, если enabled)
2. **Админы** - через API `/api/admin/user/{user_id}/cleanup`
3. **Пользователи** - НЕ МОГУТ удалять свои посты (защищено)

### Cascade delete:

```python
# models.py
# При удалении канала → посты НЕ удаляются автоматически
# При удалении пользователя → посты удаляются (CASCADE)
```

---

## ⚠️ ВНИМАНИЕ

**404 ошибки в cleanup НЕ означают удаление постов!**

Это была проблема неправильного порта API:
- ❌ telethon:8001 (auth server) - 404
- ✅ telethon:8010 (main API) - 200

**Посты 720-728:**
- ✅ Существуют в БД
- ✅ НЕ удалены
- ✅ Будут протегированы после исправления порта

---

**Автор:** AI Assistant  
**Дата:** 15 октября 2025

