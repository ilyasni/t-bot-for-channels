# Telegram Timeout & Database Locked - Troubleshooting

**Дата:** 13 октября 2025  
**Проблема:** `Timed out` при добавлении канала, но канал успешно добавлен в БД  
**Причина:** Конфликт session файлов между telethon и telethon-bot контейнерами

---

## 🐛 Симптомы

**Пользователь видит:**
```
❌ Ошибка при добавлении канала: Timed out
```

**В БД:**
```sql
✅ Канал добавлен
✅ Пользователь подключен к каналу
✅ Все данные сохранены
```

**В логах:**
```
INFO:models:📢 Создан новый канал: @techno_yandex
INFO:models:✅ Пользователь подключен к каналу
ERROR:telegram.ext.Application: telegram.error.TimedOut
sqlite3.OperationalError: database is locked
```

---

## 🔍 Корневая причина

### Архитектура с двумя контейнерами

```
Docker Volumes:
./telethon/sessions → /app/sessions

Используется ОБОИМИ контейнерами:
    ↓                          ↓
telethon (FastAPI)    telethon-bot (Bot)
    ↓                          ↓
user_139883458.session (SQLite)
```

**Проблема:**
- Telethon использует SQLite для session файлов
- SQLite **НЕ поддерживает** одновременный write access из разных процессов
- Когда `telethon-bot` пытается создать клиент → **database is locked**
- Задержка → timeout при отправке Telegram сообщения

---

## ✅ Решения

### Вариант 1: Игнорировать (текущее состояние)

**Плюсы:**
- Канал все равно добавляется успешно
- Пользователь может проверить через `/my_channels`
- Не требует изменений кода

**Минусы:**
- Плохой UX (ошибка при успехе)
- Пользователь не знает что канал добавлен

**Рекомендация для пользователя:**
```
Если видите "Timed out" - проверьте командой:
/my_channels

Скорее всего канал уже добавлен!
```

### Вариант 2: Увеличить timeout (простое решение)

**Файл:** `bot_standalone.py`

```python
from telegram.ext import Application
from telegram.request import HTTPXRequest

# Увеличиваем timeout
request = HTTPXRequest(
    connect_timeout=30.0,
    read_timeout=30.0,
    write_timeout=30.0
)

application = Application.builder().token(BOT_TOKEN).request(request).build()
```

**Плюсы:**
- Простое исправление
- Даем больше времени для ответа

**Минусы:**
- Не решает корневую проблему (database locked)

### Вариант 3: Переключиться на StringSession (рекомендуется)

**Проблема:** SQLite session файлы не thread-safe

**Решение:** Использовать StringSession (хранится в PostgreSQL)

**Файл:** `shared_auth_manager.py`

```python
from telethon.sessions import StringSession

class SharedAuthManager:
    async def _create_client(self, telegram_id: int) -> TelegramClient:
        # Получаем session string из БД
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            session_string = user.telethon_session_string  # Новое поле в БД
        finally:
            db.close()
        
        # Создаем клиент с StringSession
        client = TelegramClient(
            StringSession(session_string),  # Вместо file path
            self.master_api_id,
            self.master_api_hash
        )
        
        return client
```

**Изменения в models.py:**
```python
class User(Base):
    __tablename__ = "users"
    # ... existing fields ...
    telethon_session_string = Column(Text, nullable=True)  # НОВОЕ ПОЛЕ
```

**Плюсы:**
- ✅ Нет конфликтов между контейнерами
- ✅ Session в PostgreSQL (надежнее)
- ✅ Backup сессий вместе с БД
- ✅ Нет файлов session на диске

**Минусы:**
- Требует миграцию БД
- Требует рефакторинг shared_auth_manager и qr_auth_manager

### Вариант 4: Использовать один контейнер (архитектурное решение)

**Проблема:** Зачем два контейнера если они используют одни и те же session файлы?

**Решение:** Запускать бота в основном контейнере `telethon`

**Файл:** `run_system.py` (уже так делает!)

```python
# Запускаем бота в том же процессе что и FastAPI
async def main():
    # 1. Запуск FastAPI
    # 2. Запуск Bot (python-telegram-bot)
    # 3. Запуск Parser Service
    # Все в одном контейнере
```

**Docker Compose:** Удалить отдельный `telethon-bot` контейнер

**Плюсы:**
- ✅ Нет конфликтов session файлов
- ✅ Меньше контейнеров
- ✅ Единая память для active_clients

**Минусы:**
- Если FastAPI падает → бот тоже падает

---

## 🎯 Рекомендации

### Немедленно (для пользователя):

1. **Канал уже добавлен!** Проверьте:
   ```
   /my_channels
   ```

2. **Если нужно добавить еще каналы:**
   - Просто повторите команду
   - Если видите "Timed out" - подождите 10 секунд и проверьте `/my_channels`
   - Скорее всего канал будет в списке

### Краткосрочно (следующие 1-2 дня):

**Увеличить timeout в bot_standalone.py:**

```python
request = HTTPXRequest(
    connect_timeout=30.0,  # Было: 10.0
    read_timeout=30.0,     # Было: 10.0
    write_timeout=30.0     # Было: 10.0
)
```

### Среднесрочно (неделя):

**Переключиться на StringSession:**
1. Добавить поле `telethon_session_string` в таблицу `users`
2. Миграция: конвертировать существующие session файлы → StringSession
3. Обновить `shared_auth_manager` и `qr_auth_manager`
4. Удалить session файлы

### Долгосрочно (месяц):

**Объединить контейнеры:**
- Использовать только один контейнер `telethon`
- Запускать бота через `run_system.py`
- Удалить отдельный `telethon-bot` контейнер

---

## 📊 Сравнение решений

| Решение | Сложность | Эффективность | Время |
|---------|-----------|---------------|-------|
| **Игнорировать** | ⭐ | ⭐ | 0 минут |
| **Увеличить timeout** | ⭐⭐ | ⭐⭐ | 5 минут |
| **StringSession** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 2-3 часа |
| **Один контейнер** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 1 час |

---

## 🔗 Похожие проблемы

- SQLite session locks при параллельных запросах
- Telegram API rate limiting
- Network timeouts

---

**Статус:** ⚠️ Не критично (функциональность работает)  
**Workaround:** Проверяйте `/my_channels` если видите "Timed out"  
**Версия:** 3.2.0  
**Дата:** 13 октября 2025

