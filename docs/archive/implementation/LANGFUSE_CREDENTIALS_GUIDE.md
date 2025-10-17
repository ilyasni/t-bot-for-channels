# 🔑 Как получить Langfuse Credentials

Langfuse теперь работает! Вот как получить API ключи:

## 📝 Шаги:

### 1. Открыть Langfuse UI
```
https://langfuse.produman.studio
```

### 2. Создать аккаунт
- Email: `your@email.com`
- Password: `your_secure_password`
- Name: `Your Name`

### 3. Создать Organization
- Organization name: `My Organization` (любое имя)

### 4. Создать Project
- Project name: `Telegram Bot` (рекомендуется)

### 5. Получить API Keys
1. Зайти в **Settings** (⚙️)
2. Выбрать **API Keys**
3. Нажать **Create new API key**
4. Скопировать:
   - **Public Key**: `pk-lf-xxxxxxxxxxxxxxxx`
   - **Secret Key**: `sk-lf-xxxxxxxxxxxxxxxx`

### 6. Добавить в .env

```bash
cd /home/ilyasni/n8n-server/n8n-installer

# Добавить в .env:
nano .env

# Вставить:
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-xxxxxxxxxxxxxxxx
LANGFUSE_SECRET_KEY=sk-lf-xxxxxxxxxxxxxxxx
LANGFUSE_HOST=https://langfuse.produman.studio
```

### 7. Rebuild контейнеры

```bash
docker compose up -d --build telethon rag-service
```

### 8. Проверить интеграцию

```bash
# Проверить логи
docker logs telethon | grep Langfuse
# Должно быть: "✅ Langfuse client initialized"

# Выполнить /ask команду в боте
# Затем зайти в Langfuse UI → Traces
# Должен появиться trace "bot_ask_command"
```

## 🎉 Готово!

Теперь все AI операции трейсятся:
- ✅ OpenRouter /ask calls
- ✅ GigaChat embeddings
- ✅ RAG vector search

**Next:** Откройте Grafana для метрик → https://grafana.produman.studio

