# 📚 Навигация по документации

**Telegram Channel Parser Bot + Groups Functionality**

---

## 🚀 Быстрый старт

### Новый пользователь?

**Выберите язык:**
- 🇷🇺 **Русский:** [docs/groups/quickstart/БЫСТРЫЙ_СТАРТ.md](docs/groups/quickstart/БЫСТРЫЙ_СТАРТ.md)
- 🇬🇧 **English:** [docs/groups/quickstart/QUICK_START_SUB_WORKFLOWS.md](docs/groups/quickstart/QUICK_START_SUB_WORKFLOWS.md)

**Или начните с:**
- [QUICKSTART.md](QUICKSTART.md) - Быстрый старт всего проекта
- [README.md](README.md) - Главная документация

---

## 📁 Структура документации

```
project/
├── README.md                           # Главная документация проекта
├── QUICKSTART.md                       # Быстрый старт проекта
├── DOCUMENTATION.md                    # Этот файл (навигация)
│
├── docs/                               # Вся документация здесь
│   ├── README.md                       # Индекс документации
│   ├── groups/                         # Функционал групп
│   │   ├── quickstart/                 # Быстрые старты
│   │   ├── deployment/                 # Развертывание
│   │   ├── implementation/             # Технические детали
│   │   └── troubleshooting/            # Решение проблем
│   └── archive/                        # Архив
│
├── n8n/workflows/                      # n8n workflows + документация
│   ├── НАСТРОЙКА_SUB_WORKFLOWS.md     # Детальная настройка
│   ├── SUB_WORKFLOWS_GUIDE.md         # Guide (English)
│   └── README_GROUP_WORKFLOWS.md      # Group workflows
│
└── telethon/docs/                      # Документация компонентов бота
    └── features/groups/                # Документация по groups
```

---

## 🎯 Навигация по задачам

### Я хочу настроить Groups функционал

**Шаг 1:** [Быстрый старт](docs/groups/quickstart/БЫСТРЫЙ_СТАРТ.md) (20 минут)  
**Шаг 2:** [Настройка n8n](n8n/workflows/НАСТРОЙКА_SUB_WORKFLOWS.md) (детали)  
**Шаг 3:** [Тестирование](docs/groups/quickstart/QUICK_TEST_GROUPS.md)

### У меня проблема

**Смотрите:** [docs/groups/troubleshooting/](docs/groups/troubleshooting/)

**Частые проблемы:**
- [n8n возвращает 500](docs/groups/troubleshooting/ПРОВЕРКА_N8N_WORKFLOWS.md)
- [Can't parse entities](docs/groups/troubleshooting/MARKDOWN_ESCAPING_FIX.md)
- [Referenced node doesn't exist](docs/groups/troubleshooting/ИСПРАВЛЕНИЕ_ОШИБКИ_REFERENCED_NODE.md)
- [message_count = 0](docs/groups/troubleshooting/DIGEST_FIX_FINAL.md)

### Я разработчик

**Архитектура:**
- [Sub-workflows Implementation](docs/groups/implementation/SUB_WORKFLOWS_IMPLEMENTATION.md)
- [Groups Final Report](docs/groups/implementation/GROUPS_FINAL_REPORT.md)

**Код:**
- `telethon/` - Python бот
- `n8n/workflows/` - n8n workflows (JSON)
- `.cursor/rules/` - Cursor AI rules

---

## 📖 Детальная документация

### По компонентам

**Telegram Bot (Python):**
- [telethon/docs/](telethon/docs/) - Документация по компонентам
- [telethon/docs/features/groups/](telethon/docs/features/groups/) - Groups функционал

**n8n Workflows:**
- [n8n/workflows/НАСТРОЙКА_SUB_WORKFLOWS.md](n8n/workflows/НАСТРОЙКА_SUB_WORKFLOWS.md) - Детальная настройка (RU)
- [n8n/workflows/SUB_WORKFLOWS_GUIDE.md](n8n/workflows/SUB_WORKFLOWS_GUIDE.md) - Guide (EN)
- [n8n/workflows/README_GROUP_WORKFLOWS.md](n8n/workflows/README_GROUP_WORKFLOWS.md) - Импорт workflows

**База данных:**
- `telethon/models.py` - SQLAlchemy модели
- `telethon/scripts/migrations/` - Миграции БД

---

## 🆘 Помощь и поддержка

### Частые вопросы (FAQ)

**Q: Как импортировать n8n workflows?**  
A: [БЫСТРЫЙ_СТАРТ.md](docs/groups/quickstart/БЫСТРЫЙ_СТАРТ.md) - пошаговая инструкция

**Q: Агенты не активируются, это нормально?**  
A: Да! [ИСПРАВЛЕНИЕ_ИНСТРУКЦИЙ.md](docs/groups/troubleshooting/ИСПРАВЛЕНИЕ_ИНСТРУКЦИЙ.md) - Execute Workflow Trigger не требует активации

**Q: Где посмотреть логи?**
```bash
# Логи бота
docker logs telethon

# Логи n8n
docker logs n8n

# Логи gpt2giga-proxy
docker logs gpt2giga-proxy
```

**Q: Как обновить код в контейнере?**
```bash
docker cp telethon/file.py telethon:/app/
docker restart telethon
```

---

## 📝 История изменений

- [CHANGELOG.md](CHANGELOG.md) - Полная история проекта
- [docs/archive/](docs/archive/) - Старые отчеты

---

## 🔗 Полезные ссылки

**Основные файлы:**
- [README.md](README.md) - Главная страница проекта
- [CONTRIBUTING.md](CONTRIBUTING.md) - Правила контрибуции
- [.env.example](.env.example) - Пример конфигурации

**Внешняя документация:**
- [n8n Documentation](https://docs.n8n.io/)
- [Telethon Documentation](https://docs.telethon.dev/)
- [GigaChat API](https://developers.sber.ru/docs/ru/gigachat/api/overview)

---

**Версия:** 1.0 (Sub-workflows architecture)  
**Последнее обновление:** 13 октября 2025

**Вернуться к:** [Главной документации](docs/README.md)

