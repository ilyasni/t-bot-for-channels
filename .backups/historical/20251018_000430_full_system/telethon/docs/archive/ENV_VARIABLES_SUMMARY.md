# 🎯 Переменные окружения - Краткое резюме

## ✅ Что исправлено

### 1. **Корневой .env.example**
**Добавлено:**
- `TELEGRAM_DATABASE_URL` - путь к БД Telegram Parser
- `BOT_TOKEN` - токен бота от @BotFather
- `DEFAULT_RETENTION_DAYS` - период хранения постов (30 дней)
- `CLEANUP_SCHEDULE_TIME` - время автоочистки (03:00)
- `TELEGRAM_AUTH_HOSTNAME` - hostname для auth сервера

### 2. **telethon/.env.example**
**Удалено:**
- Дублирующиеся переменные (теперь только в корневом .env)
- Устаревшие комментарии

**Добавлено:**
- Четкие пояснения какие переменные должны быть в корневом .env

### 3. **docker-compose.override.yml**
**Удалено (устаревший подход):**
```yaml
- API_ID=${API_ID}         # ❌ Удалено
- API_HASH=${API_HASH}     # ❌ Удалено
- PHONE=${PHONE}           # ❌ Удалено
- AUTH_CODE=${AUTH_CODE}   # ❌ Удалено
```

**Добавлено (современный подход):**
```yaml
- DATABASE_URL=${TELEGRAM_DATABASE_URL}
- BOT_TOKEN=${BOT_TOKEN}
- ENCRYPTION_KEY=${ENCRYPTION_KEY}
```

---

## 📍 Где какие переменные

### Корневой `.env` (основные настройки проекта)
```env
# Telegram Parser
TELEGRAM_DATABASE_URL=sqlite:///./telethon/data/telethon_bot.db
BOT_TOKEN=your_bot_token
DEFAULT_RETENTION_DAYS=30
CLEANUP_SCHEDULE_TIME=03:00

# Общие для проекта
ENCRYPTION_KEY=your_32_char_key
POSTGRES_PASSWORD=your_password
```

### `telethon/.env` (специфичные для Telegram Parser)
```env
# Парсер
PARSER_INTERVAL_MINUTES=30
MAX_POSTS_PER_CHANNEL=50

# Сервер
HOST=0.0.0.0
PORT=8010

# Auth
AUTH_BASE_URL=https://telegram-auth.produman.studio

# AI тегирование (опционально)
OPENROUTER_API_KEY=your_key
OPENROUTER_MODEL=google/gemini-2.0-flash-exp:free
TAGGING_BATCH_SIZE=10
```

---

## 🚀 Быстрая настройка

```bash
# 1. Корневой .env
cd /home/ilyasni/n8n-server/n8n-installer
cp .env.example .env
nano .env  # Заполните BOT_TOKEN и ENCRYPTION_KEY

# 2. Telethon .env
cd telethon
cp .env.example .env
nano .env  # Настройте OPENROUTER_API_KEY (опционально)

# 3. Запуск
cd ..
python start_services.py
```

---

## 🔐 Важно

**Многопользовательский режим:**
- Каждый пользователь регистрируется через Web Auth (порт 8001)
- API credentials **зашифрованы в БД**, не в .env
- Глобальные API_ID/API_HASH **больше не используются**

**Encryption Key:**
- Генерация: `openssl rand -hex 32`
- **НЕ МЕНЯЙТЕ** после начала использования

---

**Полная документация:** `ENV_VARIABLES_ANALYSIS.md`

