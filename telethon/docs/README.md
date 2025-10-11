# 📚 Документация Telegram Channel Parser + RAG System

**Версия:** 2.2.1  
**Последнее обновление:** 11 октября 2025

---

## 🚀 Быстрый старт

**Навигация по всей документации:**
- [DOCUMENTATION_GUIDE.md](DOCUMENTATION_GUIDE.md) - Полная справка
- [NAVIGATION_CHEATSHEET.md](NAVIGATION_CHEATSHEET.md) - Quick links ← Начните здесь!

### Новые пользователи
1. [QUICK_START.md](quickstart/QUICK_START.md) - Основной Parser
2. [RAG_QUICKSTART.md](quickstart/RAG_QUICKSTART.md) - RAG система и AI-дайджесты

### Для тестирования
1. [telethon/TESTING_GUIDE.md](../TESTING_GUIDE.md) - Полное руководство (14 сценариев)
2. [telethon/QUICK_REFERENCE.md](../QUICK_REFERENCE.md) - Шпаргалка по командам

---

## 📁 Структура документации

### 📘 `/quickstart/` - Быстрые старты
```
QUICK_START.md              - Основной Parser (аутентификация, каналы, API)
RAG_QUICKSTART.md           - RAG система (поиск, дайджесты, AI)
RAG_SYSTEM_READY.md         - Статус готовности RAG
QUICK_MIGRATION.md          - Миграция данных
QUICK_START_RETENTION.md    - Система хранения постов
QUICK_START_TAGGING.md      - AI тегирование
```

### 🔧 `/features/` - Функции системы

**Основные функции:**
```
RETENTION_README.md         - Автоочистка старых постов
TAGGING_README.md           - AI-тегирование (OpenRouter/GigaChat)
TAGGING_RETRY_SYSTEM.md     - Retry механизм для тегирования
TAGGING_AND_INDEXING_WORKFLOW.md - Workflow тегирования и индексации
README_SECURE.md            - Безопасная аутентификация
IMPLEMENTATION_SUMMARY.md   - Общая сводка
MANY_TO_MANY_SUMMARY.md     - Many-to-Many архитектура
```

**Docker:**
```
DOCKER_README.md            - Запуск в Docker
DOCKER_RETENTION_SETUP.md   - Настройка retention в Docker
```

**Интеграции:**
```
OPENWEBUI_INTEGRATION.md    - Интеграция с Open WebUI (опционально)
```

### 🤖 `/features/rag/` - RAG System

**RAG документация:**
```
README.md                   - Навигация по RAG docs
BOT_RAG_COMMANDS.md         - Описание команд бота (/ask, /search, /recommend, /digest)
RAG_IMPLEMENTATION_SUMMARY.md - Технические детали реализации
RAG_DEPLOYMENT_SUMMARY.md   - Развертывание RAG
RAG_CHECKLIST.md            - Чеклист проверки
DOCKER_DEPLOYMENT_ORDER.md  - Порядок запуска сервисов
```

**AI Digests:**
```
AI_DIGEST_GUIDE.md          - Руководство по AI-дайджестам
AI_DIGEST_IMPLEMENTATION_SUMMARY.md - Технические детали
AI_DIGEST_FINAL_REPORT.md   - Финальный отчет
DIGEST_EXPLANATION.md       - Объяснение работы дайджестов
```

### 🔄 `/migrations/` - Миграции БД
```
README_MIGRATION.md         - Общее руководство
MIGRATION_MANY_TO_MANY.md   - Переход на Many-to-Many
MIGRATION_SUPABASE.md       - Миграция на Supabase
MIGRATION_FILES_LIST.md     - Список скриптов миграций
```

### 🐛 `/troubleshooting/` - Решение проблем
```
CONNECTION_TROUBLESHOOTING.md - Проблемы подключения
SUPABASE_INTEGRATION.md      - Интеграция с Supabase
TIMEZONE_FIX.md              - Исправление таймзон
GIGACHAT_MODEL_CHECK.md      - Проверка моделей GigaChat
GIGACHAT_PRO_FIX.md          - Исправления GigaChat
RATE_LIMIT_429.md            - Обработка rate limits
```

### 📦 `/archive/` - Архивные материалы

**Отчеты о разработке:**
- `/archive/reports/` - Временные отчеты о реализации (11 файлов)
- `/archive/testing/` - Тестовые отчеты (4 файла)
- `/archive/` - Старые технические документы (10 файлов)

---

## 🎯 Навигация по задачам

### Я хочу начать работу с системой
→ [quickstart/QUICK_START.md](quickstart/QUICK_START.md)

### Я хочу использовать RAG и AI-дайджесты
→ [quickstart/RAG_QUICKSTART.md](quickstart/RAG_QUICKSTART.md)

### Я хочу протестировать новые команды
→ [../TESTING_GUIDE.md](../TESTING_GUIDE.md)

### Мне нужна шпаргалка по командам
→ [../QUICK_REFERENCE.md](../QUICK_REFERENCE.md)

### Я хочу настроить AI-тегирование
→ [features/TAGGING_README.md](features/TAGGING_README.md)

### Мне нужно выполнить миграцию БД
→ [migrations/README_MIGRATION.md](migrations/README_MIGRATION.md)

### У меня проблемы с подключением/сервисами
→ [troubleshooting/](troubleshooting/)

### Я разработчик, нужны технические детали RAG
→ [features/rag/README.md](features/rag/README.md)

---

## 📊 Статистика документации

**Всего:** ~64 MD файла (42 актуальных + 25 архивных)
- Быстрые старты: 6
- Функции: 19 (RAG: 10, основные: 8, Docker: 2, интеграции: 1)
- Миграции: 4
- Troubleshooting: 6
- Документация (guides): 2
- Архив: 25 (reports: 11, testing: 4, technical: 10)

---

## 🔗 Внешние ссылки

**API документация:**
- Parser API: http://localhost:8010/docs
- RAG Service: http://localhost:8020/docs

**Cursor Rules:**
- [.cursor/rules/n8n-telegram-bot.mdc](../../../.cursor/rules/n8n-telegram-bot.mdc)

---

**Версия:** 2.2.1  
**Организация:** Структурированная по категориям


