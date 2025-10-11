# 📋 Анализ переменных окружения - Резюме изменений

**Дата:** 10 октября 2025  
**Файлы:** `.env.example`, `telethon/.env.example`, `docker-compose.override.yml`

---

## 🔍 Обнаруженные проблемы

### ❌ **Проблема 1: Отсутствие переменных в корневом .env.example**

В корневом `.env.example` отсутствовали критически важные переменные для Telegram Parser:
- `TELEGRAM_DATABASE_URL` - используется в docker-compose.override.yml
- `BOT_TOKEN` - токен Telegram бота
- `DEFAULT_RETENTION_DAYS` - период хранения постов
- `CLEANUP_SCHEDULE_TIME` - время автоочистки
- `TELEGRAM_AUTH_HOSTNAME` - hostname для auth сервера

### ❌ **Проблема 2: Устаревшие переменные в docker-compose.override.yml**

Файл использовал **устаревший подход** с глобальными API ключами:
```yaml
# СТАРЫЙ ПОДХОД (удален):
- API_ID=${API_ID}
- API_HASH=${API_HASH}
- PHONE=${PHONE}
- AUTH_CODE=${AUTH_CODE}
```

**Почему это проблема:**
- Современная архитектура использует **многопользовательский режим**
- Каждый пользователь имеет свои API ключи, **зашифрованные в БД**
- Глобальные ключи противоречат security best practices

### ❌ **Проблема 3: Дублирование переменных**

Переменные `DEFAULT_RETENTION_DAYS` и `CLEANUP_SCHEDULE_TIME` дублировались в:
- Корневом `.env.example`
- `telethon/.env.example`

---

## ✅ Внесенные изменения

### 1. **Корневой `.env.example`** ✨

**Добавлена новая секция:**
```env
###########################################################################################
# Telegram Channel Parser Settings
###########################################################################################

# Database URL for Telegram Parser (SQLite by default, PostgreSQL/Supabase optional)
TELEGRAM_DATABASE_URL=sqlite:///./telethon/data/telethon_bot.db
# For PostgreSQL/Supabase use:
# TELEGRAM_DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@db:5432/postgres

# Telegram Bot Token (get from @BotFather)
BOT_TOKEN=

# Post retention settings (настройки хранения постов)
DEFAULT_RETENTION_DAYS=30
CLEANUP_SCHEDULE_TIME=03:00
```

**Добавлен hostname:**
```env
TELEGRAM_AUTH_HOSTNAME=telegram-auth.yourdomain.com
```

### 2. **telethon/.env.example** 🔧

**Удалены дублирующиеся переменные:**
- ❌ `DEFAULT_RETENTION_DAYS` (теперь только в корневом .env)
- ❌ `CLEANUP_SCHEDULE_TIME` (теперь только в корневом .env)
- ❌ `BOT_TOKEN` (описание перенесено в комментарии)

**Добавлены пояснения:**
```env
############################################################
# Переменные из корневого .env проекта:
############################################################
# BOT_TOKEN - токен Telegram бота (получить у @BotFather)
# TELEGRAM_DATABASE_URL - URL базы данных
#   По умолчанию: sqlite:///./telethon/data/telethon_bot.db
#   Для PostgreSQL: postgresql://postgres:password@db:5432/postgres
# ENCRYPTION_KEY - используется общий ключ из корневого .env
# POSTGRES_PASSWORD - для подключения к Supabase (если используется)
# DEFAULT_RETENTION_DAYS - период хранения постов (по умолчанию 30 дней)
# CLEANUP_SCHEDULE_TIME - время ежедневной очистки (формат HH:MM, по умолчанию 03:00)
############################################################
```

### 3. **docker-compose.override.yml** 🚀

**Удалены устаревшие переменные:**
```yaml
# УДАЛЕНО (устаревший подход):
- API_ID=${API_ID}
- API_HASH=${API_HASH}
- PHONE=${PHONE}
- AUTH_CODE=${AUTH_CODE}
```

**Добавлены правильные переменные:**
```yaml
environment:
  # База данных
  - DATABASE_URL=${TELEGRAM_DATABASE_URL:-sqlite:///./data/telethon_bot.db}
  # Telegram Bot Token
  - BOT_TOKEN=${BOT_TOKEN}
  # Ключ шифрования (общий для всего проекта)
  - ENCRYPTION_KEY=${ENCRYPTION_KEY}
  # Система хранения постов
  - DEFAULT_RETENTION_DAYS=${DEFAULT_RETENTION_DAYS:-30}
  - CLEANUP_SCHEDULE_TIME=${CLEANUP_SCHEDULE_TIME:-03:00}
```

---

## 📊 Таблица распределения переменных

| Переменная | Корневой .env | telethon/.env | docker-compose.override.yml |
|-----------|---------------|---------------|----------------------------|
| `TELEGRAM_DATABASE_URL` | ✅ Определена | 📝 Описана в комментариях | ✅ Используется |
| `BOT_TOKEN` | ✅ Определена | 📝 Описана в комментариях | ✅ Используется |
| `ENCRYPTION_KEY` | ✅ Определена (Langfuse) | 📝 Описана в комментариях | ✅ Используется |
| `DEFAULT_RETENTION_DAYS` | ✅ Определена | ❌ Удалена | ✅ Используется |
| `CLEANUP_SCHEDULE_TIME` | ✅ Определена | ❌ Удалена | ✅ Используется |
| `PARSER_INTERVAL_MINUTES` | - | ✅ Определена | ✅ Используется (fallback) |
| `MAX_POSTS_PER_CHANNEL` | - | ✅ Определена | - |
| `HOST` / `PORT` | - | ✅ Определены | ✅ Используются (fallback) |
| `AUTH_BASE_URL` | - | ✅ Определена | - |
| `OPENROUTER_API_KEY` | - | ✅ Определена | - |
| `OPENROUTER_MODEL` | - | ✅ Определена | - |
| `TAGGING_BATCH_SIZE` | - | ✅ Определена | - |
| `API_ID` / `API_HASH` / `PHONE` / `AUTH_CODE` | ❌ Не нужны | ❌ Не нужны | ❌ **УДАЛЕНЫ** |

---

## 🎯 Как правильно настроить переменные

### **Шаг 1: Корневой .env**

Скопируйте `.env.example` в `.env`:
```bash
cd /home/ilyasni/n8n-server/n8n-installer
cp .env.example .env
```

Заполните обязательные переменные для Telegram Parser:
```env
# Telegram Channel Parser
TELEGRAM_DATABASE_URL=sqlite:///./telethon/data/telethon_bot.db
BOT_TOKEN=your_bot_token_from_botfather
DEFAULT_RETENTION_DAYS=30
CLEANUP_SCHEDULE_TIME=03:00

# Encryption (общий для всего проекта)
ENCRYPTION_KEY=your_32_character_encryption_key
```

**Как получить BOT_TOKEN:**
1. Найдите @BotFather в Telegram
2. Отправьте `/newbot`
3. Следуйте инструкциям
4. Скопируйте полученный токен

### **Шаг 2: telethon/.env**

Скопируйте `telethon/.env.example` в `telethon/.env`:
```bash
cd telethon
cp .env.example .env
```

Настройте специфичные переменные:
```env
PARSER_INTERVAL_MINUTES=30
MAX_POSTS_PER_CHANNEL=50
HOST=0.0.0.0
PORT=8010
AUTH_BASE_URL=https://telegram-auth.produman.studio

# OpenRouter (опционально, для AI тегирования)
OPENROUTER_API_KEY=your_openrouter_api_key
OPENROUTER_MODEL=google/gemini-2.0-flash-exp:free
TAGGING_BATCH_SIZE=10
```

### **Шаг 3: Проверка**

Запустите систему:
```bash
cd /home/ilyasni/n8n-server/n8n-installer
python start_services.py
```

Проверьте логи:
```bash
docker logs telethon
docker logs telethon-bot
```

---

## 🔐 Архитектура аутентификации

### **Многопользовательский режим (текущий)**

```
┌─────────────┐
│   User 1    │──> API_ID_1 (encrypted in DB)
│   User 2    │──> API_ID_2 (encrypted in DB)
│   User 3    │──> API_ID_3 (encrypted in DB)
└─────────────┘
```

**Как это работает:**
1. Пользователь регистрируется через Web Auth (`auth_web_server.py`)
2. Вводит свои Telegram API credentials (API_ID, API_HASH, PHONE)
3. Credentials **шифруются** с помощью `ENCRYPTION_KEY`
4. Сохраняются в БД в таблице `users`
5. При парсинге используются **личные** API ключи пользователя

**Преимущества:**
- ✅ Каждый пользователь парсит свои каналы
- ✅ Нет Rate Limiting от одного API ключа
- ✅ Безопасность: credentials зашифрованы
- ✅ Изоляция: один пользователь не влияет на других

### **Устаревший подход (удален)**

```
┌─────────────┐
│ All Users   │──> Один глобальный API_ID
└─────────────┘
```

**Проблемы:**
- ❌ Все пользователи используют один API ключ
- ❌ Rate Limiting бьет всех одновременно
- ❌ Небезопасно: credentials в .env файле
- ❌ Один сломанный ключ = вся система не работает

---

## 🚨 Важные замечания

### ⚠️ **Миграция с устаревшего подхода**

Если вы ранее использовали глобальные `API_ID`, `API_HASH`:

1. **Удалите их из .env файлов** (уже сделано в .env.example)
2. **Настройте Web Auth сервер** (порт 8001)
3. **Попросите каждого пользователя зарегистрироваться** через Web интерфейс
4. **Проверьте** что сессии создаются в `sessions/user_{id}.session`

### ⚠️ **База данных**

**SQLite (по умолчанию):**
```env
TELEGRAM_DATABASE_URL=sqlite:///./telethon/data/telethon_bot.db
```

**PostgreSQL/Supabase:**
```env
TELEGRAM_DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@db:5432/postgres
```

### ⚠️ **Encryption Key**

**Критически важно:**
- Используется для шифрования API credentials пользователей
- Длина: минимум 32 символа
- Генерация: `openssl rand -hex 32`
- **НЕ МЕНЯЙТЕ** после начала использования (невозможно расшифровать данные)

---

## 📝 Чеклист для настройки

- [ ] Скопировать корневой `.env.example` → `.env`
- [ ] Заполнить `BOT_TOKEN` (получить у @BotFather)
- [ ] Заполнить `ENCRYPTION_KEY` (сгенерировать через `openssl rand -hex 32`)
- [ ] Настроить `TELEGRAM_DATABASE_URL` (SQLite или PostgreSQL)
- [ ] Скопировать `telethon/.env.example` → `telethon/.env`
- [ ] Настроить `OPENROUTER_API_KEY` (опционально, для AI тегирования)
- [ ] Запустить систему: `python start_services.py`
- [ ] Проверить что Web Auth работает: `http://localhost:8001`
- [ ] Зарегистрировать первого пользователя через Web интерфейс
- [ ] Проверить логи: `docker logs telethon`

---

## 🔗 Связанные документы

- [Telegram Parser README](telethon/README.md)
- [Quick Start Guide](telethon/docs/quickstart/QUICK_START.md)
- [Secure Authentication](telethon/docs/features/README_SECURE.md)
- [Docker Setup](telethon/docs/features/DOCKER_README.md)
- [Troubleshooting](telethon/docs/troubleshooting/CONNECTION_TROUBLESHOOTING.md)

---

**Статус:** ✅ Все изменения внесены, готово к использованию

