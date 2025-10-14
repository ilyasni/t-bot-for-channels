# Telegram Channel Parser Bot

Telegram бот для мониторинга каналов, RAG-поиска, дайджестов и анализа групп.

## 🚀 Быстрый старт

```bash
# 1. Клонировать репозиторий
cd /home/ilyasni/n8n-server/n8n-installer/telethon

# 2. Установить зависимости
pip install -r requirements.txt

# 3. Настроить .env
cp .env.example .env
# Отредактировать .env с вашими токенами

# 4. Запустить
python bot.py
```

## 📚 Документация

Вся документация находится в **[docs/](docs/)** папке:

- 🎨 **[docs/formatting/](docs/formatting/)** - HTML форматирование сообщений
- 🧪 **[docs/testing/](docs/testing/)** - Руководства по тестированию
- ✨ **[docs/features/](docs/features/)** - Описание функций
- 📖 **[docs/guides/](docs/guides/)** - Руководства пользователя

### Начните здесь

1. **Новый разработчик?** → [docs/guides/START_HERE.md](docs/guides/START_HERE.md)
2. **HTML форматирование?** → [docs/formatting/HTML_FORMAT_EXAMPLES.md](docs/formatting/HTML_FORMAT_EXAMPLES.md)
3. **Тестирование?** → [docs/testing/TESTING_GUIDE.md](docs/testing/TESTING_GUIDE.md)
4. **Деплой?** → [docs/formatting/DEPLOYMENT_GUIDE.md](docs/formatting/DEPLOYMENT_GUIDE.md)

## ✨ Основные возможности

### 1. QR Login
Аутентификация через QR код без ввода номера телефона.

### 2. RAG (Retrieval-Augmented Generation)
- Векторный поиск по постам из каналов
- AI-ответы с источниками
- Гибридный поиск (посты + веб)

### 3. Дайджесты
- Автоматические дайджесты по расписанию
- AI-дайджесты с саммари по темам
- HTML форматирование с expandable блоками

### 4. Groups мониторинг
- Отслеживание упоминаний
- Дайджесты групповых диалогов
- Интеграция с n8n multi-agent workflows

### 5. Голосовые команды
- Транскрипция через SaluteSpeech API
- /ask и /search голосом
- Лимиты по subscription tiers

## 🏗️ Архитектура

```
telethon/
├── bot.py                      # Основной бот
├── telegram_formatter.py       # HTML форматирование ⭐
├── qr_auth_manager.py         # QR аутентификация
├── voice_transcription_service.py  # Голос → текст
├── group_monitor_service.py   # Мониторинг групп
├── rag_service/               # RAG система
│   ├── main.py               # FastAPI endpoints
│   ├── generator.py          # RAG генератор
│   ├── searcher.py           # Векторный поиск
│   ├── digest_generator.py   # Дайджесты
│   └── scheduler.py          # Планировщик
├── models.py                  # SQLAlchemy модели
├── database.py               # PostgreSQL
└── tests/                    # Тесты (42 passing ✅)
```

## 🎨 HTML Форматирование (NEW!)

Бот поддерживает расширенный HTML с уникальными возможностями Telegram:

```html
<!-- Expandable blockquote для скрытия длинного контента -->
<blockquote expandable>📚 Источники:
1. @python_news (15.01.2024)
2. @dev_channel (10.01.2024)
</blockquote>

<!-- Spoilers -->
<tg-spoiler>Секретный текст</tg-spoiler>

<!-- Code blocks с языком -->
<pre><code class="language-python">
def hello():
    print("world")
</code></pre>
```

**Подробнее:** [docs/formatting/HTML_FORMAT_EXAMPLES.md](docs/formatting/HTML_FORMAT_EXAMPLES.md)

## 🧪 Тестирование

```bash
# Запустить все тесты
pytest tests/ -v

# Только форматирование
pytest tests/test_telegram_formatter.py -v

# С покрытием
pytest tests/ --cov=. --cov-report=html
```

**Статус:** ✅ 42/42 тестов проходят

## 🔧 Технологии

- **Python 3.11+**
- **python-telegram-bot** - Telegram Bot API
- **Telethon** - Telegram Client API
- **FastAPI** - RAG сервис
- **PostgreSQL** - База данных
- **Redis (Valkey)** - Кеш и сессии
- **Qdrant** - Векторная БД
- **GigaChat/OpenRouter** - LLM
- **n8n** - Workflows и автоматизация

## 📊 Subscription Tiers

| Feature | Trial | Premium | Enterprise |
|---------|-------|---------|------------|
| Channels | 3 | 20 | 100 |
| RAG queries | 10/day | 100/day | 999/day |
| Voice queries | 20/day | 50/day | 999/day |
| AI Digests | ❌ | ✅ | ✅ |
| Groups Monitor | ❌ | 5 groups | 50 groups |

## 🚀 Deployment

**Docker (рекомендуется):**
```bash
cd /home/ilyasni/n8n-server/n8n-installer
docker-compose up -d telethon
docker logs telethon -f
```

**Manual:**
```bash
cd telethon
python bot.py
```

**Подробнее:** [docs/formatting/DEPLOYMENT_GUIDE.md](docs/formatting/DEPLOYMENT_GUIDE.md)

## 📝 Environment Variables

Ключевые переменные в `.env`:

```bash
# Telegram
BOT_TOKEN=your_bot_token
MASTER_API_ID=your_api_id
MASTER_API_HASH=your_api_hash

# Database
DATABASE_URL=postgresql://user:pass@db:5432/telethon

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# RAG
QDRANT_HOST=http://qdrant:6333
GIGACHAT_ENABLED=true
OPENROUTER_API_KEY=your_key

# Voice
SALUTESPEECH_CLIENT_ID=your_id
SALUTESPEECH_CLIENT_SECRET=your_secret
```

## 🤝 Contributing

1. Создать ветку для фичи
2. Написать тесты
3. Убедиться что все тесты проходят
4. Создать pull request

**Code Style:**
- Следовать PEP 8
- Type hints обязательны
- Docstrings для публичных функций
- Использовать async/await

## 📄 License

MIT License - см. [LICENSE](LICENSE)

## 📞 Support

- **Issues:** GitHub Issues
- **Docs:** [docs/](docs/)
- **Examples:** [docs/formatting/HTML_FORMAT_EXAMPLES.md](docs/formatting/HTML_FORMAT_EXAMPLES.md)

---

**Версия:** 3.3.0 (HTML Formatting Update)  
**Последнее обновление:** 14 октября 2025  
**Статус:** ✅ Production Ready
