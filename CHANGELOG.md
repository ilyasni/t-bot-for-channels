# Changelog

Все значимые изменения в проекте документируются в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
версионирование следует [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [3.1.0] - 2025-10-12

### Добавлено - Telegram Parser

#### QR Login система
- ✅ Авторизация через QR код (без SMS!)
- ✅ `QRAuthManager` для управления QR сессиями
- ✅ Telegram Mini App UI для QR логина
- ✅ Deep links поддержка (`tg://login?token=...`)
- ✅ Shared state через Redis между контейнерами
- ✅ Документация: `/telethon/docs/quickstart/QR_LOGIN_GUIDE.md`

#### Admin Panel (Telegram Mini App)
- ✅ Полнофункциональная SPA (2700+ строк)
- ✅ Tabs навигация: Dashboard, Users, Invites, Stats
- ✅ Управление пользователями (роли, подписки, лимиты)
- ✅ Генерация invite codes
- ✅ Статистика и графики (Chart.js)
- ✅ Темная тема support
- ✅ Skeleton loading и плавные анимации
- ✅ Документация: `/telethon/docs/quickstart/ADMIN_PANEL_QUICKSTART.md`

#### Система ролей и подписок
- ✅ Роли: `admin`, `user`
- ✅ Subscription tiers: free, trial, basic, premium, enterprise
- ✅ Invite codes с настраиваемыми параметрами
- ✅ `SubscriptionHistory` для аудита изменений
- ✅ Лимиты каналов по подписке
- ✅ Документация: `/telethon/docs/features/SUBSCRIPTIONS.md`

#### Shared Credentials система
- ✅ Master Telegram API credentials для всех пользователей
- ✅ `SharedAuthManager` для управления Telethon клиентами
- ✅ Упрощенная авторизация (не нужны личные API ключи)
- ✅ Документация: `/telethon/docs/features/SHARED_CREDENTIALS.md`

### Изменено - Telegram Parser

#### База данных
- ⚠️ **BREAKING:** Только PostgreSQL (удален SQLite fallback)
- ✅ Timezone-aware datetime везде (UTC в БД, Europe/Moscow для display)
- ✅ Миграция: `scripts/migrations/add_roles_and_subscriptions.py`
- ✅ Новые таблицы: `invite_codes`, `subscription_history`

#### Бот команды
- ✅ `/start` - обновлен для QR login workflow
- ✅ `/login INVITE_CODE` - QR авторизация
- ✅ `/admin` - открыть Admin Panel Mini App
- ✅ Deprecated: `/admin_invite`, `/admin_users` (используйте `/admin`)

#### UI/UX
- ✅ Tailwind CSS через CDN
- ✅ Темная тема (auto-detect через Telegram WebApp API)
- ✅ Градиенты для карточек (БЕЗ постоянной анимации)
- ✅ Ripple эффект для кнопок
- ✅ Toast notifications
- ✅ Modal dialogs с glassmorphism

#### Инфраструктура
- ✅ Redis обязателен (shared state для QR sessions и admin sessions)
- ✅ `admin_session:` prefix для изоляции от `qr_session:`
- ✅ TTL: QR sessions - 10 минут, Admin sessions - 1 час

### Исправлено - Telegram Parser

- 🐛 User parsing теперь работает для всех пользователей (не только user_id=6)
- 🐛 2FA handle в QR login (автоматически)
- 🐛 Timezone issues в Admin Panel (все datetime timezone-aware)
- 🐛 Desktop browser error в Mini App (добавлена поддержка)

### Документация

#### Добавлено
- ✅ `/telethon/docs/quickstart/QR_LOGIN_GUIDE.md`
- ✅ `/telethon/docs/quickstart/ADMIN_PANEL_QUICKSTART.md`
- ✅ `/telethon/docs/features/SUBSCRIPTIONS.md`
- ✅ `/telethon/docs/features/SHARED_CREDENTIALS.md`

#### Обновлено
- ✅ Cursor Rules v3.1 (QR Login, Admin Panel, PostgreSQL only)
- ✅ `/telethon/README.md` - актуализирован для v3.1
- ✅ `/telethon/docs/README.md` - навигация обновлена

#### Архивировано
- 📦 `/telethon/docs/archive/reports/QR_LOGIN_FINAL_SUMMARY.md`
- 📦 `/telethon/docs/archive/reports/ADMIN_PANEL_UI_ENHANCEMENTS.md`
- 📦 `/telethon/docs/archive/reports/VERSION_3.1_SUMMARY.md`

---

## [2.2.1] - 2025-10-11

### Добавлено - Telegram Parser

#### RAG System - Telegram Bot команды
- ✅ `/ask <вопрос>` - RAG-поиск ответа в постах
- ✅ `/search <запрос>` - Гибридный поиск (посты + веб через Searxng)
- ✅ `/recommend` - Персональные рекомендации
- ✅ `/digest` - Интерактивное меню настройки AI-дайджестов
- ✅ Документация: `/telethon/docs/features/rag/BOT_RAG_COMMANDS.md`

#### Обогащение данных
- ✅ Автоматическое извлечение контента из ссылок (Crawl4AI)
- ✅ Поле `enriched_content` в таблице posts
- ✅ Миграция: `scripts/migrations/add_enriched_content.py`

### Изменено - Telegram Parser

#### Реорганизация документации
- 📚 72 → 50 актуальных файлов (22 файла архивировано)
- 📚 Корень `telethon/` очищен (11 → 3 MD файла)
- 📚 Создан `docs/archive/` с подкатегориями (reports, testing)
- 📚 Актуализирована навигация в `docs/README.md`

---

## [2.2.0] - 2025-10-10

### Добавлено - Telegram Parser

#### RAG System (векторный поиск и AI-ответы)
- ✅ Микросервис `rag_service/` (FastAPI, 20+ endpoints)
- ✅ Qdrant интеграция (векторное хранилище)
- ✅ Redis кеширование embeddings (24h TTL)
- ✅ Гибридный поиск (vector + keyword)
- ✅ AI-дайджесты с персонализацией
- ✅ Автоматическая индексация новых постов
- ✅ Документация: `/telethon/docs/quickstart/RAG_QUICKSTART.md`

#### Интеграция внешних сервисов
- ✅ Qdrant (векторная БД)
- ✅ Redis/Valkey (кеширование)
- ✅ Searxng (метапоисковик)
- ✅ Crawl4AI (web scraping)
- ✅ Ollama (локальные LLM)

#### База данных
- ✅ Новые таблицы: `digest_settings`, `indexing_status`, `rag_query_history`
- ✅ Миграция: `scripts/migrations/add_rag_tables.py`
- ✅ Supabase RLS для изоляции данных

### Изменено - Telegram Parser

#### Архитектура
- ✅ Микросервисная архитектура (telethon + rag-service)
- ✅ Event-Driven Architecture (новые события: post_indexed, digest_sent)
- ✅ Graceful degradation с fallback chains
- ✅ Circuit breaker для внешних сервисов

#### Performance
- ✅ Connection pooling через Supavisor
- ✅ Async everywhere (httpx, aiofiles)
- ✅ Background tasks для тяжелых операций
- ✅ Batch indexing в Qdrant (до 100 постов)
- ✅ Rate limiting через Redis

---

## [2.1.0] - 2025-10-09

### Добавлено

#### GPT2Giga Proxy
- ✅ OpenAI-совместимый прокси для GigaChat (Sber AI)
- ✅ Embeddings генерация (EmbeddingsGigaR)
- ✅ Chat completions (GigaChat-Lite, GigaChat, GigaChatMAX)
- ✅ Streaming support
- ✅ Порт 8090
- ✅ Документация: `/gpt2giga/README.md`

#### Telegram Parser - инфраструктура разработки
- ✅ `telethon/scripts/utils/dev.sh` - helper скрипт
- ✅ Docker разработка (rebuild, restart, logs, shell)
- ✅ Локальная разработка (setup, local, api, bot, test)
- ✅ Алиасы для быстрого доступа из любой директории
- ✅ Документация: `/telethon/scripts/README.md`

### Изменено

#### start_services.py
- ✅ Автоматическая подготовка директорий для telethon
- ✅ Копирование `.env.example` → `.env` для telethon и gpt2giga
- ✅ Интеграция в единую сеть `localai_default`
- ✅ Переменные окружения из корневого `.env`

#### Безопасность
- ✅ Двойной уровень `.gitignore` (корневой + локальный)
- ✅ Защита `.session` файлов, БД, логов
- ✅ Явные паттерны для SQLite и Telegram сессий

#### Скрипты установки
- ✅ `scripts/03_generate_secrets.sh` - запрос BOT_TOKEN, OPENROUTER_API_KEY, GIGACHAT_CREDENTIALS
- ✅ `scripts/04_wizard.sh` - информация о telethon и gpt2giga
- ✅ `scripts/06_final_report.sh` - отображение telethon и gpt2giga
- ✅ Упрощена конфигурация GigaChat (одна переменная `GIGACHAT_CREDENTIALS`)

---

## [2.0.0] - 2025-10-05

### Добавлено - Telegram Parser

#### Основная функциональность
- ✅ Многопользовательский режим (каждый юзер свои API ключи)
- ✅ REST API (FastAPI) для интеграции с n8n
- ✅ Автоматический парсер каналов
- ✅ AI тегирование постов (OpenRouter)
- ✅ Retention система (автоочистка старых постов)
- ✅ Безопасная аутентификация (шифрование credentials)
- ✅ Web-сервер для OAuth (порт 8001)
- ✅ Telegram бот для управления

#### База данных
- ✅ SQLite по умолчанию
- ✅ PostgreSQL/Supabase support
- ✅ Many-to-Many связи (users ↔ channels)
- ✅ Миграции: `/telethon/scripts/migrations/`

#### Docker интеграция
- ✅ Сервис `telethon` (порты 8010, 8001)
- ✅ Сервис `telethon-bot` (standalone)
- ✅ Volumes: sessions, data, logs
- ✅ Единая сеть с основным стеком

#### Документация
- ✅ `/telethon/README.md` - главная документация
- ✅ `/telethon/docs/quickstart/QUICK_START.md`
- ✅ `/telethon/docs/features/` - детальное описание функций
- ✅ `/telethon/TESTING_GUIDE.md`

---

## [1.0.0] - 2025-09-01

### Добавлено - Базовый стек (upstream)

#### Основные компоненты
- ✅ n8n с queue mode (Redis + PostgreSQL)
- ✅ Caddy reverse proxy с auto-HTTPS
- ✅ PostgreSQL 15
- ✅ Redis для очередей

#### Опциональные сервисы
- ✅ Supabase (БД, auth, storage)
- ✅ Open WebUI
- ✅ Flowise
- ✅ Qdrant
- ✅ SearXNG
- ✅ Langfuse
- ✅ Crawl4AI
- ✅ Letta
- ✅ Weaviate
- ✅ Neo4j
- ✅ Ollama
- ✅ Prometheus + Grafana

#### Скрипты установки
- ✅ `scripts/install.sh` - основной установщик
- ✅ `scripts/update.sh` - обновление
- ✅ Service Selection Wizard
- ✅ Импорт 300+ n8n workflows

---

## Типы изменений

- `Added` - новая функциональность
- `Changed` - изменения в существующей функциональности
- `Deprecated` - функции, которые скоро будут удалены
- `Removed` - удаленная функциональность
- `Fixed` - исправления багов
- `Security` - исправления уязвимостей

---

## Ссылки

- [Оригинальный n8n-installer](https://github.com/kossakovsky/n8n-installer)
- [n8n Self-Hosted AI Starter Kit](https://github.com/n8n-io/self-hosted-ai-starter-kit)

