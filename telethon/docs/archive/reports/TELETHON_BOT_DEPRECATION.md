# 🔧 DEPRECATION: telethon-bot контейнер удален

**Дата:** 13 октября 2025  
**Версия:** 3.1.1  
**Статус:** ✅ РЕАЛИЗОВАНО

---

## 📋 Контекст

После объединения контейнеров в версии 3.0.0, standalone контейнер `telethon-bot` больше не нужен, так как бот теперь работает внутри unified контейнера `telethon`.

---

## 🚨 Что изменилось

### До v3.1.1 (УСТАРЕЛО):

```yaml
# docker-compose.override.yml
services:
  telethon:
    # run_system.py - API + Parser + Bot
    
  telethon-bot:
    # bot_standalone.py - standalone Bot
    command: ["python", "bot_standalone.py"]
```

**Проблема:** Два бота с одним `BOT_TOKEN` → **конфликт getUpdates**

### После v3.1.1 (АКТУАЛЬНО):

```yaml
# docker-compose.override.yml
services:
  telethon:
    # run_system.py - API + Parser + Bot + Auth
    # Unified architecture
  
  # telethon-bot: УДАЛЕН
```

**Решение:** Один unified контейнер → **нет конфликтов**

---

## 🔄 Миграция

### Если у вас есть telethon-bot контейнер:

```bash
# 1. Остановить и удалить
docker stop telethon-bot
docker rm telethon-bot

# 2. Обновить docker-compose.override.yml
# (telethon-bot сервис уже закомментирован)

# 3. Перезапустить telethon
docker compose up -d telethon
```

### Проверка:

```bash
# Должен быть только telethon
docker ps | grep telethon
# ✅ telethon (run_system.py)
# ❌ telethon-bot не должен быть

# Логи без ошибок Conflict
docker logs telethon --tail 20
# ✅ Нет "terminated by other getUpdates request"
```

---

## 📝 Обновленная документация

### scripts/utils/dev.sh

**Было:**
```bash
docker compose build telethon telethon-bot
docker compose restart telethon telethon-bot
docker compose stop telethon telethon-bot
```

**Стало:**
```bash
# telethon-bot удален в v3.1.1
docker compose build telethon
docker compose restart telethon
docker compose stop telethon
```

### TESTING_GUIDE.md

**Было:**
```bash
docker compose up telethon-bot --build -d
```

**Стало:**
```bash
docker compose up telethon --build -d  # telethon-bot удален
```

### QUICK_REFERENCE.md

**Было:**
```bash
docker compose restart telethon-bot
```

**Стало:**
```bash
docker compose restart telethon  # telethon-bot удален
```

---

## 🔧 bot_standalone.py

**Статус:** ✅ СОХРАНЕН для локальной отладки

**Использование:**

```bash
# ТОЛЬКО для локальной отладки (БЕЗ Docker):
cd /home/ilyasni/n8n-server/n8n-installer/telethon
source venv/bin/activate
python bot_standalone.py
```

**В Docker:**
```bash
# ❌ НЕ используется
# ✅ Используется run_system.py
```

**Dev script:**
```bash
# Показывает предупреждение
./scripts/utils/dev.sh bot
# ВНИМАНИЕ: bot_standalone.py - DEPRECATED в Docker!
# Используйте для локальной отладки. В Docker используется run_system.py
```

---

## 📊 Влияние на функционал

### ✅ Работает как раньше:

- Telegram Bot (команды /start, /add_channel, /ask, и т.д.)
- FastAPI Server (порт 8010)
- Auth Web Server (порт 8001)
- Parser Service (автоматический парсинг)
- Admin Panel (QR Login, subscription management)
- RAG Service (векторный поиск, дайджесты)

### 🔄 Изменилось:

- **Один контейнер** вместо двух
- **run_system.py** запускает все компоненты
- **bot_standalone.py** только для локальной отладки

### ❌ Не работает:

- Standalone контейнер `telethon-bot` (УДАЛЕН)

---

## 🎯 Best Practices

### Telegram Bot API:

✅ **Один экземпляр бота** на токен  
❌ Несколько экземпляров → Conflict  

### Docker:

✅ **Unified architecture** - все в одном контейнере  
❌ Микросервисы без необходимости → сложность  

### python-telegram-bot:

✅ **Application.run_async()** для интеграции с FastAPI  
❌ **Application.run()** блокирует event loop  

---

## 📚 См. также

- `docs/archive/reports/CONTAINER_CONFLICT_FIX.md` - решение конфликта getUpdates
- `docs/archive/reports/UNIFIED_CONTAINER_ARCHITECTURE.md` - архитектура v3.0.0
- `docs/archive/reports/CODE_REFACTORING_2025_10_13.md` - рефакторинг v3.1.1

---

## ✅ Проверка после миграции

```bash
# 1. Контейнеры
docker ps | grep telethon
# ✅ Только telethon

# 2. Логи чистые
docker logs telethon --tail 20 2>&1 | grep -i error
# ✅ Нет ошибок Conflict

# 3. API работает
curl http://localhost:8010/users
# ✅ {"total":N,"users":[...]}

# 4. Bot отвечает в Telegram
# /start
# ✅ Получен ответ
```

---

**Версия:** 3.1.1  
**Дата:** 13 октября 2025  
**Статус:** ✅ РЕАЛИЗОВАНО И РАБОТАЕТ

