# n8n Server with Telegram Channel Parser & RAG System

**Форк проекта [n8n-installer](https://github.com/kossakovsky/n8n-installer) от Cole Medin с расширенной функциональностью.**

Этот проект представляет собой комплексную self-hosted платформу для AI автоматизации, включающую:

- 🤖 **n8n** - low-code платформа автоматизации с 400+ интеграциями
- 📱 **Telegram Channel Parser** - многопользовательский парсер Telegram каналов с AI тегированием и RAG системой
- 🧠 **RAG System** - векторный поиск и AI-ответы на основе спарсенных постов
- 🔍 **Full AI Stack** - Flowise, Open WebUI, Supabase, Qdrant, Langfuse, SearXNG и другие

---

## 🆕 Дополнительные возможности этого форка

### Telegram Channel Parser (telethon)

Расположение: `/telethon/`

**Ключевые функции:**
- ✅ **Многопользовательский режим** - каждый пользователь с собственными Telegram API ключами
- ✅ **QR Login** - авторизация через QR код (без SMS кодов!)
- ✅ **REST API** - интеграция с n8n workflows
- ✅ **AI Тегирование** - автоматическое тегирование постов (OpenRouter/GigaChat)
- ✅ **RAG System** - векторный поиск по постам с генерацией ответов
- ✅ **AI Дайджесты** - персонализированные ежедневные/еженедельные дайджесты
- ✅ **Обогащение данных** - автоматическое извлечение контента из ссылок (Crawl4AI)
- ✅ **Система подписок** - роли и лимиты (free, trial, basic, premium, enterprise)
- ✅ **Admin Panel** - управление пользователями через Telegram Mini App
- ✅ **Retention System** - автоматическая очистка старых постов

**Технологии:**
- Telethon (Telegram API)
- FastAPI (REST API)
- PostgreSQL/Supabase (база данных)
- Qdrant (векторное хранилище)
- Redis/Valkey (кеширование)
- GigaChat/OpenRouter (AI модели)
- Crawl4AI (web scraping)
- Docker (контейнеризация)

**Документация:**
- [Быстрый старт](/telethon/docs/quickstart/QUICK_START.md)
- [QR Login гайд](/telethon/docs/quickstart/QR_LOGIN_GUIDE.md)
- [Admin Panel](/telethon/docs/quickstart/ADMIN_PANEL_QUICKSTART.md)
- [RAG система](/telethon/docs/quickstart/RAG_QUICKSTART.md)
- [Полная документация](/telethon/docs/README.md)

### GPT2Giga Proxy

Расположение: `/gpt2giga/`

OpenAI-совместимый прокси для GigaChat (Sber AI):
- ✅ Embeddings генерация (EmbeddingsGigaR)
- ✅ Chat completions (GigaChat-Lite, GigaChat, GigaChatMAX)
- ✅ Streaming support
- ✅ OpenAI SDK совместимость

---

## 📋 Что включено (оригинальный стек)

### Обязательные компоненты

✅ [**Self-hosted n8n**](https://n8n.io/) - платформа автоматизации с 400+ интеграциями и AI компонентами  
✅ **Caddy** - reverse proxy с автоматическим HTTPS  
✅ **PostgreSQL** - основная база данных  
✅ **Redis/Valkey** - кеширование и очереди задач  

### Опциональные сервисы (выбираются при установке)

✅ [**Supabase**](https://supabase.com/) - open-source альтернатива Firebase (БД, auth, vector store)  
✅ [**Open WebUI**](https://openwebui.com/) - ChatGPT-like интерфейс для AI моделей  
✅ [**Flowise**](https://flowiseai.com/) - no-code AI agent builder  
✅ [**Qdrant**](https://qdrant.tech/) - высокопроизводительная векторная БД  
✅ [**SearXNG**](https://searxng.org/) - приватный метапоисковик  
✅ [**Langfuse**](https://langfuse.com/) - мониторинг AI агентов  
✅ [**Crawl4AI**](https://github.com/Alfresco/crawl4ai) - web crawler для AI  
✅ [**Letta**](https://docs.letta.com/) - AI agent server с долгосрочной памятью  
✅ [**Weaviate**](https://weaviate.io/) - AI-native векторная БД  
✅ [**Neo4j**](https://neo4j.com/) - графовая база данных  
✅ [**Ollama**](https://ollama.com/) - локальные LLM (Llama, Mistral, Gemma)  
✅ [**Prometheus**](https://prometheus.io/) - система мониторинга  
✅ [**Grafana**](https://grafana.com/) - визуализация метрик  

### Community Workflows

В проект включено **300+ готовых n8n workflows**, покрывающих:
- 🤖 AI Agents & Chatbots (RAG, LangChain, OpenAI, Claude)
- 📧 Gmail & Outlook автоматизация
- 📊 Notion, Airtable, Google Sheets интеграции
- 📄 PDF, Image, Audio, Video обработка
- 💬 Telegram, WhatsApp, Discord боты
- 🌐 WordPress, WooCommerce AI-контент
- 📱 Социальные сети (LinkedIn, Instagram, Twitter, YouTube)

---

## 🚀 Быстрая установка

### Предварительные требования

1. **Домен** - зарегистрированный домен (например, `yourdomain.com`)
2. **DNS** - настроенная wildcard A-запись: `*.yourdomain.com` → `YOUR_SERVER_IP`
3. **Сервер** - Ubuntu 24.04 LTS, 64-bit:
   - **Минимальная конфигурация** (n8n + Flowise): 4GB RAM / 2 CPU / 30GB Disk
   - **Полная конфигурация** (все сервисы): 8GB RAM / 4 CPU / 60GB Disk
   - **С Telegram Parser + RAG**: 12GB RAM / 6 CPU / 80GB Disk (рекомендуется)

### Установка

Подключитесь к серверу через SSH и выполните:

    ```bash
git clone https://github.com/yourusername/n8n-server && cd n8n-server/n8n-installer
sudo bash ./scripts/install.sh
```

Скрипт установки автоматически:
- 📦 Подготовит систему (обновления, firewall, базовая защита)
- 🐳 Установит Docker и Docker Compose
- 🔐 Сгенерирует `.env` с секретными ключами
- 🎯 Запустит Service Selection Wizard
- 🚀 Развернет выбранные сервисы

**Вас спросят:**
1. Основной домен (например, `yourdomain.com`)
2. Email адрес (для SSL сертификатов и входа в сервисы)
3. OpenAI API ключ (опционально)
4. Импортировать ли 300 готовых n8n workflows (опционально, 20-30 минут)
5. Количество n8n workers (для параллельной обработки)
6. Какие сервисы развернуть (интерактивный wizard)

После установки скрипт выведет **summary report** со всеми URL и credentials. **Сохраните его!**

---

## 🔧 Доступ к сервисам

После установки сервисы доступны по адресам (замените `yourdomain.com` на ваш домен):

### Основные сервисы
- **n8n:** `n8n.yourdomain.com`
- **Telegram Parser API:** `telegram-api.yourdomain.com` (если настроен)
- **Telegram Auth:** `telegram-auth.yourdomain.com` (QR login)

### AI Stack
    - **Open WebUI:** `webui.yourdomain.com`
- **Flowise:** `flowise.yourdomain.com`
    - **Langfuse:** `langfuse.yourdomain.com`

### Базы данных
- **Supabase Dashboard:** `supabase.yourdomain.com`
- **Qdrant:** `qdrant.yourdomain.com`
    - **Neo4j:** `neo4j.yourdomain.com`

### Мониторинг
    - **Grafana:** `grafana.yourdomain.com`
- **Prometheus:** `prometheus.yourdomain.com`

### Утилиты
    - **SearXNG:** `searxng.yourdomain.com`

**Credentials** для всех сервисов указаны в summary report после установки.

---

## 📱 Telegram Channel Parser - Быстрый старт

### 1. Получение Telegram API ключей

1. Перейдите на https://my.telegram.org
2. Войдите с вашим номером телефона
3. Выберите "API development tools"
4. Создайте приложение и получите `api_id` и `api_hash`

### 2. Получение invite code

Попросите администратора создать invite code через Admin Panel (`/admin` команда бота).

### 3. Авторизация через QR код

```
1. Отправьте боту: /login YOUR_INVITE_CODE
2. Нажмите кнопку "🔐 QR Авторизация"
3. Отсканируйте QR код камерой или используйте ссылку
4. Подтвердите вход в официальном Telegram
5. Готово! ✅
```

### 4. Добавление каналов

```
/add_channel @channelname
/my_channels
```

### 5. RAG команды

```
/ask Расскажи о последних новостях AI
/search Ищу информацию про GPT-4
/recommend - Персональные рекомендации
/digest - Настроить AI-дайджесты
```

**Подробнее:** [Telegram Parser документация](/telethon/docs/README.md)

---

## 🔄 Обновление системы

Для обновления всех компонентов до последних версий:

```bash
cd /path/to/n8n-installer
sudo bash ./scripts/update.sh
```

Скрипт обновления:
1. Получит последние изменения из Git репозитория
2. Остановит сервисы
3. Скачает новые Docker образы
4. Предложит обновить n8n workflows
5. Перезапустит сервисы

---

## 🛠️ Управление сервисами

### Запуск/остановка

```bash
# Запустить все сервисы
python3 start_services.py

# Остановить все
docker compose -p localai down

# Перезапустить конкретный сервис
docker compose -p localai restart telethon
docker compose -p localai restart n8n
```

### Логи

```bash
# Логи всех сервисов
docker compose -p localai logs -f

# Логи конкретного сервиса
docker logs -f telethon
docker logs -f n8n
docker logs -f rag-service
```

### Telegram Parser - разработка

```bash
cd telethon

# Docker разработка
./scripts/utils/dev.sh rebuild  # Пересборка + restart
./scripts/utils/dev.sh logs     # Просмотр логов
./scripts/utils/dev.sh shell    # Bash в контейнере

# Локальная разработка (без Docker)
./scripts/utils/dev.sh setup    # Настройка venv
./scripts/utils/dev.sh local    # Запуск локально
./scripts/utils/dev.sh test     # Тесты
```

---

## 💡 Советы и трюки

### Shared folder для n8n

Папка `shared/` в корне проекта доступна из n8n workflows по пути `/data/shared`.

**Полезные n8n ноды:**
- [Read/Write Files from Disk](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.filesreadwrite/)
- [Local File Trigger](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.localfiletrigger/)
- [Execute Command](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.executecommand/)

### Pre-installed libraries в n8n

Доступны в Code ноде:
- `cheerio` - парсинг HTML/XML
- `axios` - HTTP requests
- `moment` - работа с датами
- `lodash` - утилиты для массивов/объектов

### Telegram Parser - Интеграция с n8n

1. Создайте webhook в n8n
2. Добавьте URL в переменную окружения:
   ```bash
   WEBHOOK_NEW_POST=https://n8n.yourdomain.com/webhook/new-post
   ```
3. Telegram Parser будет отправлять события:
   - `new_post` - новый пост добавлен
   - `post_tagged` - пост получил AI-теги
   - `post_indexed` - пост индексирован в RAG
   - `digest_sent` - дайджест отправлен

---

## 📁 Структура проекта

```
n8n-installer/
├── telethon/              # Telegram Channel Parser (многопользовательский бот)
├── gpt2giga/             # OpenAI-совместимый прокси для GigaChat
├── n8n/                  # n8n конфигурация и workflows
├── flowise/              # Flowise конфигурация
├── supabase/             # Supabase setup
├── scripts/              # Утилиты и инструменты установки
│   ├── install.sh        # Основной скрипт установки
│   ├── update.sh         # Скрипт обновления
│   └── n8n_pipe.py       # Open WebUI интеграция с n8n
├── docs/                 # Документация
│   ├── reports/          # Отчёты о статусах и изменениях
│   ├── features/         # Документация по функциям
│   ├── observability/    # Мониторинг и метрики
│   └── voice/            # Voice AI команды
├── shared/               # Shared folder для n8n workflows
├── start_services.py     # Скрипт запуска всех сервисов
├── docker-compose.yml    # Основная Docker конфигурация
└── .env                  # Переменные окружения (генерируется при установке)
```

### Документация по отчётам

Все отчёты о выполненных работах и изменениях находятся в `docs/reports/`:
- Интеграции (SearXNG, Crawl4AI, мониторинг)
- Voice AI статусы
- Telegram Groups функции
- Обновления и откаты
- Восстановление данных

См. [docs/reports/README.md](docs/reports/README.md) для деталей.

---

## 🐛 Troubleshooting

### Общие проблемы

**"Dangerous Site" warning в браузере:**
- Подождите несколько часов, пока Caddy получит Let's Encrypt сертификаты
- Проверьте DNS настройки (wildcard A-запись)

**VPN конфликты:**
- Отключите VPN при загрузке Docker образов

**Supabase проблемы:**
- Избегайте спецсимволов (@, %) в `POSTGRES_PASSWORD`
- Проверьте логи: `docker logs supabase-db`

### Telegram Parser

**QR Login не работает:**
```bash
# Проверить Redis
docker logs redis

# Проверить session в Redis
docker exec redis redis-cli KEYS "qr_session:*"

# Проверить логи
docker logs telethon | grep "QRAuthManager"
```

**RAG не индексирует посты:**
```bash
# Проверить Qdrant
curl http://qdrant:6333/collections

# Проверить RAG сервис
docker logs rag-service

# Проверить статус индексации
curl http://telegram-api.yourdomain.com/api/rag/index/status/USER_ID
```

**Подробнее:** [Telegram Parser Troubleshooting](/telethon/docs/troubleshooting/)

---

## 📚 Полезные ресурсы

### n8n Обучение
- [AI agents: from theory to practice](https://blog.n8n.io/ai-agents/)
- [Build an AI workflow tutorial](https://docs.n8n.io/advanced-ai/intro-tutorial/)
- [Langchain in n8n](https://docs.n8n.io/advanced-ai/langchain/langchain-n8n/)
- [Vector databases explained](https://docs.n8n.io/advanced-ai/examples/understand-vector-databases/)

### Telegram Parser
- [Telegram API Documentation](https://core.telegram.org/api)
- [Telethon Documentation](https://docs.telethon.dev/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

### Видео
- [Cole's Guide to the AI Starter Kit](https://youtu.be/pOsO40HSbOo)

### Шаблоны n8n
- [Official n8n AI templates](https://n8n.io/workflows/?categories=AI)

---

## 🔗 Важные ссылки

- **Оригинальный проект:** [n8n-installer by Cole Medin](https://github.com/kossakovsky/n8n-installer)
- **Upstream:** [n8n Self-Hosted AI Starter Kit](https://github.com/n8n-io/self-hosted-ai-starter-kit)
- **Community форум:** [oTTomator Think Tank](https://thinktank.ottomator.ai/c/local-ai/18)
- **GitHub Kanban:** [Project Board](https://github.com/users/coleam00/projects/2/views/1)

---

## 🤝 Contributors

**Оригинальный проект:**
- [Contributors to n8n-installer](https://github.com/kossakovsky/n8n-installer/graphs/contributors)

**Этот форк:**
- Telegram Channel Parser + RAG System: [ваше имя/контакты]
- GPT2Giga Proxy integration
- Admin Panel UI/UX improvements
- QR Login implementation

---

## 📜 License

Этот проект (основанный на n8n-installer от Cole Medin и contributors) распространяется под лицензией Apache License 2.0. 

См. [LICENSE](LICENSE) для деталей.

**Дополнительные компоненты (Telegram Parser):**
- Разработаны как расширение оригинального проекта
- Также распространяются под Apache License 2.0
- Copyright для новых компонентов: 2025 [ваше имя]

---

## 🙏 Благодарности

- **Cole Medin** и команда за оригинальный n8n-installer
- **n8n.io** за платформу автоматизации
- **Supabase**, **Qdrant**, **Flowise** и другие open-source проекты
- **Telegram** за API и возможности ботов
- **Sber AI** за GigaChat API

---

**Версия:** 3.1  
**Дата:** Октябрь 2025
