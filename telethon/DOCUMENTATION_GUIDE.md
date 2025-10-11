# 📚 Навигация по документации - Краткая справка

**Версия:** 2.2.1  
**Последнее обновление:** 11 октября 2025

---

## 🎯 Быстрый доступ

### Я только начинаю
→ **[README.md](README.md)** - Начните отсюда!

### Мне нужна шпаргалка
→ **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Команды бота

### Хочу протестировать
→ **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - 14 сценариев

---

## 📁 Структура docs/

```
docs/
├── README.md                 📍 Главная навигация
│
├── quickstart/               🚀 Быстрые старты (6)
│   ├── QUICK_START.md       - Основы системы
│   └── RAG_QUICKSTART.md    - RAG & AI
│
├── features/                 🔧 Функции (12)
│   ├── TAGGING_README.md    - AI-тегирование
│   ├── RETENTION_README.md  - Автоочистка
│   └── rag/                 🤖 RAG система (10)
│       ├── BOT_RAG_COMMANDS.md - Команды бота
│       └── AI_DIGEST_GUIDE.md - AI-дайджесты
│
├── migrations/               🔄 Миграции БД (4)
│   └── README_MIGRATION.md
│
├── troubleshooting/          🐛 Проблемы (6)
│   ├── RATE_LIMIT_429.md
│   └── GIGACHAT_MODEL_CHECK.md
│
└── archive/                  📦 Архив (22)
    ├── reports/              - Отчеты о разработке (9)
    ├── testing/              - Тестовые отчеты (4)
    └── [changelogs, updates] - Технические (10)
```

---

## 🔍 Поиск по задачам

| Задача | Файл |
|--------|------|
| **Начать работу** | [docs/quickstart/QUICK_START.md](docs/quickstart/QUICK_START.md) |
| **Настроить RAG** | [docs/quickstart/RAG_QUICKSTART.md](docs/quickstart/RAG_QUICKSTART.md) |
| **Команды бота** | [QUICK_REFERENCE.md](QUICK_REFERENCE.md) |
| **Тестирование** | [TESTING_GUIDE.md](TESTING_GUIDE.md) |
| **AI-тегирование** | [docs/features/TAGGING_README.md](docs/features/TAGGING_README.md) |
| **Миграция БД** | [docs/migrations/README_MIGRATION.md](docs/migrations/README_MIGRATION.md) |
| **Ошибка 429** | [docs/troubleshooting/RATE_LIMIT_429.md](docs/troubleshooting/RATE_LIMIT_429.md) |
| **RAG команды** | [docs/features/rag/BOT_RAG_COMMANDS.md](docs/features/rag/BOT_RAG_COMMANDS.md) |
| **История проекта** | [docs/archive/README.md](docs/archive/README.md) |

---

## 🌐 API Документация

**Онлайн:**
- Parser API: http://localhost:8010/docs
- RAG Service: http://localhost:8020/docs

**Health Checks:**
- Parser: http://localhost:8010/users
- RAG: http://localhost:8020/health

---

## 📊 Категории документации

### quickstart/ - Быстрый старт
Если вы новичок или хотите быстро что-то запустить.

### features/ - Детальное описание
Углубленная документация каждой функции системы.

### features/rag/ - RAG система
Все о векторном поиске, AI-ответах и дайджестах.

### migrations/ - Миграции
Обновление структуры базы данных.

### troubleshooting/ - Проблемы
Решения типичных ошибок и проблем.

### archive/ - Архив
Исторические документы, отчеты, старые changelog.

---

## 🔗 Внешние ресурсы

**Cursor Rules:**
- [.cursor/rules/n8n-telegram-bot.mdc](../.cursor/rules/n8n-telegram-bot.mdc)

**Основной проект:**
- [n8n-installer README](../../README.md)

**RAG Service:**
- [rag_service/README.md](rag_service/README.md)

---

## ✨ Правила документирования

### Где создавать новые документы:

| Тип документа | Директория |
|---------------|------------|
| Быстрый старт функции | `docs/quickstart/` |
| Описание функции | `docs/features/` |
| RAG функция | `docs/features/rag/` |
| Миграция БД | `docs/migrations/` |
| Решение проблемы | `docs/troubleshooting/` |
| Временный отчет | `docs/archive/reports/` |
| Тестовый отчет | `docs/archive/testing/` |

### ❌ НЕ создавайте в корне telethon/!

Исключения:
- README.md (главная)
- TESTING_GUIDE.md (важное руководство)
- QUICK_REFERENCE.md (шпаргалка)

---

**Версия справки:** 2.2.1  
**Организация:** Чистая и масштабируемая  
**Статус:** 🟢 Готово к использованию

