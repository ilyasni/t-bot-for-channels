# 🕐 Исправление отображения времени в API (Timezone Fix)

**Дата:** 11 октября 2025  
**Проблема:** Даты в API ответах отставали на 3 часа от реального времени по таймзоне MSK

## 🐛 Проблема

### До исправления:
```json
{
  "posted_at": "2025-10-11T08:56:12",      // UTC (без timezone)
  "created_at": "2025-10-06T11:17:35.740589"  // UTC (отстает на 3 часа)
}
```

**Причина:**
- Даты хранятся в БД корректно (в UTC)
- Но при возврате через API не конвертировались в локальную таймзону (MSK, UTC+3)
- Пользователь видел UTC время вместо MSK

## ✅ Решение

### После исправления:
```json
{
  "posted_at": "2025-10-11T11:56:12+03:00",      // MSK (UTC+3) ✅
  "created_at": "2025-10-06T14:17:35.740589+03:00"  // MSK (UTC+3) ✅
}
```

### Реализация

**1. Добавлена функция конвертации в `main.py`:**

```python
# Локальная таймзона из переменной окружения
LOCAL_TZ_NAME = os.getenv('TZ', 'Europe/Moscow')
LOCAL_TZ = zoneinfo.ZoneInfo(LOCAL_TZ_NAME)

def to_local_time(dt: datetime) -> str:
    """
    Конвертирует datetime из UTC в локальную таймзону
    
    Args:
        dt: datetime объект (может быть с timezone или без)
        
    Returns:
        ISO строка в локальной таймзоне
    """
    if dt is None:
        return None
    
    # Если datetime без timezone, считаем что это UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    # Конвертируем в локальную таймзону
    local_dt = dt.astimezone(LOCAL_TZ)
    return local_dt.isoformat()
```

**2. Обновлены все API endpoints:**

Заменено:
```python
"posted_at": post.posted_at.isoformat()  # Было
```

На:
```python
"posted_at": to_local_time(post.posted_at)  # Стало
```

**Затронутые endpoints:**
- `GET /users` - created_at, last_auth_check
- `GET /users/{user_id}/auth_status` - last_auth_check
- `GET /users/{telegram_id}/channels` - created_at, subscription_created_at, last_parsed_at
- `GET /users/{telegram_id}/posts` - posted_at, parsed_at
- `GET /users/{user_id}/retention_settings` - oldest_post_date, newest_post_date
- `PUT /users/{user_id}/retention_settings` - updated_at

## 🎯 Настройка таймзоны

### Через переменную окружения:

```bash
# В .env или docker-compose.yml
TZ=Europe/Moscow
```

**Поддерживаемые таймзоны:**
- `Europe/Moscow` - MSK (UTC+3)
- `Europe/London` - GMT/BST
- `America/New_York` - EST/EDT
- `Asia/Tokyo` - JST (UTC+9)
- И любые другие из IANA timezone database

**По умолчанию:** `Europe/Moscow` (MSK)

### Fallback:

Если `zoneinfo` недоступен (старый Python), используется простой offset:
```python
LOCAL_TZ = timezone(timedelta(hours=3))  # UTC+3 для MSK
```

## 📊 Пример работы

### API запрос:
```bash
curl http://localhost:8010/users/8124731874/posts?limit=1
```

### Ответ:
```json
{
  "posts": [
    {
      "id": 399,
      "posted_at": "2025-10-11T12:19:02+03:00",  // ← MSK, правильное время!
      "parsed_at": "2025-10-11T12:38:59.422996+03:00",  // ← MSK
      "text": "..."
    }
  ]
}
```

**Объяснение:**
- Telegram отправил пост в 12:19 MSK (09:19 UTC)
- Сохранился в БД как 09:19 UTC (naive datetime)
- API конвертирует и возвращает: `12:19:02+03:00` (MSK) ✅

## 🔍 Внутренний workflow

```
1. Telegram message.date
   └─> 2025-10-11 09:19:02 UTC (от Telegram API)

2. Parser сохраняет в БД
   └─> posted_at = 2025-10-11 09:19:02 (naive datetime в БД)

3. API читает из БД
   └─> post.posted_at = 2025-10-11 09:19:02 (без tzinfo)

4. to_local_time() конвертирует
   └─> Добавляет tzinfo=UTC: 2025-10-11 09:19:02+00:00
   └─> Конвертирует в MSK: 2025-10-11 12:19:02+03:00
   └─> Возвращает ISO строку: "2025-10-11T12:19:02+03:00"

5. FastAPI возвращает JSON
   └─> "posted_at": "2025-10-11T12:19:02+03:00" ✅
```

## 🗄️ Хранение в БД

**Важно:** Даты хранятся в БД как naive datetime (без timezone), что нормально для:
- SQLite (не поддерживает timezone aware datetime)
- PostgreSQL с типом TIMESTAMP (без TIME ZONE)

**Best practice:**
- ✅ Хранить в UTC (как naive datetime)
- ✅ Конвертировать в локальную таймзону при отдаче через API
- ✅ Использовать `timezone.utc` при записи в БД

**Если нужна timezone aware storage** (для multi-timezone приложений):
```python
# В models.py
from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import TIMESTAMP

# Вместо:
posted_at = Column(DateTime, nullable=False)

# Использовать:
posted_at = Column(DateTime(timezone=True), nullable=False)
# Или для PostgreSQL явно:
posted_at = Column(TIMESTAMP(timezone=True), nullable=False)
```

Но для вашего случая (один пользователь, одна таймзона) **текущее решение идеально**.

## 🧪 Тестирование

### Проверка конвертации:

```bash
# 1. Получить посты
curl http://localhost:8010/users/{telegram_id}/posts?limit=5

# 2. Проверить формат дат
# Должно быть: "posted_at": "2025-10-11T12:19:02+03:00"
# А не: "posted_at": "2025-10-11T09:19:02"

# 3. Проверить разницу с UTC
# MSK = UTC + 3 часа
# posted_at в MSK должен быть на 3 часа больше чем в UTC
```

### Тест таймзоны внутри контейнера:

```bash
docker exec telethon date
# Должно показать: Sat Oct 11 HH:MM:SS MSK 2025

docker exec telethon python -c "
from datetime import datetime, timezone, timedelta
import zoneinfo
LOCAL_TZ = zoneinfo.ZoneInfo('Europe/Moscow')
utc_now = datetime.now(timezone.utc)
msk_now = utc_now.astimezone(LOCAL_TZ)
print(f'UTC: {utc_now.isoformat()}')
print(f'MSK: {msk_now.isoformat()}')
"
# Должно показать разницу +3 часа
```

## 📝 Смена таймзоны

Если вам нужна другая таймзона:

**1. Обновите переменную окружения:**
```bash
# В .env или docker-compose.yml
TZ=Europe/London  # Пример: GMT/BST
```

**2. Перезапустите контейнер:**
```bash
docker compose -p localai restart telethon
```

**3. Проверьте:**
```bash
curl http://localhost:8010/users | python3 -m json.tool | grep created_at
# Должны увидеть время в новой таймзоне
```

## 🎉 Итог

✅ **Проблема решена:** Даты теперь отображаются в правильной таймзоне  
✅ **Best practice:** UTC в БД, локальная таймзона в API  
✅ **Гибкость:** Поддержка любой IANA timezone через переменную `TZ`  
✅ **Обратная совместимость:** Не требует миграции БД  

---

**Дата:** 11 октября 2025  
**Автор:** Telegram Channel Parser Team

