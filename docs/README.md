# 📚 Документация Telegram Bot

Добро пожаловать в документацию проекта Telegram Channel Parser Bot с функционалом Groups!

---

## 🗂️ Структура документации

### 📁 [groups/](groups/)
Документация по функционалу групп Telegram

- **[quickstart/](groups/quickstart/)** - Быстрые старты и первые шаги
- **[deployment/](groups/deployment/)** - Гайды по развертыванию
- **[implementation/](groups/implementation/)** - Технические детали реализации
- **[troubleshooting/](groups/troubleshooting/)** - Решение проблем и ошибок

### 📁 [workflows/](workflows/)
Документация по n8n workflows (находится в `n8n/workflows/`)

### 📁 [archive/](archive/)
Архив старой документации и отчетов

---

## 🚀 Быстрый старт

**Для новых пользователей:**
1. [БЫСТРЫЙ_СТАРТ.md](groups/quickstart/БЫСТРЫЙ_СТАРТ.md) - Импорт Sub-workflows (на русском)
2. [QUICK_START_SUB_WORKFLOWS.md](groups/quickstart/QUICK_START_SUB_WORKFLOWS.md) - Quick start (на английском)

**Для развертывания:**
- [GROUPS_DEPLOYMENT_GUIDE.md](groups/deployment/GROUPS_DEPLOYMENT_GUIDE.md) - Полное руководство по развертыванию

**При проблемах:**
- [ПРОВЕРКА_N8N_WORKFLOWS.md](groups/troubleshooting/ПРОВЕРКА_N8N_WORKFLOWS.md) - Диагностика n8n
- [ИТОГОВОЕ_ИСПРАВЛЕНИЕ.md](groups/troubleshooting/ИТОГОВОЕ_ИСПРАВЛЕНИЕ.md) - Частые ошибки

---

## 📖 Основная документация

**В корне проекта:**
- `README.md` - Главная документация проекта
- `QUICKSTART.md` - Быстрый старт всего проекта
- `CHANGELOG.md` - История изменений
- `CONTRIBUTING.md` - Правила контрибуции

**В telethon/docs/:**
- Детальная документация по компонентам бота

**В n8n/workflows/:**
- `НАСТРОЙКА_SUB_WORKFLOWS.md` - Детальная настройка workflows
- `SUB_WORKFLOWS_GUIDE.md` - Sub-workflows guide (English)
- `README_GROUP_WORKFLOWS.md` - Group workflows README

---

## 🎯 Навигация по темам

### Генерация дайджестов групп
1. [Быстрый старт](groups/quickstart/БЫСТРЫЙ_СТАРТ.md)
2. [Настройка n8n workflows](../n8n/workflows/НАСТРОЙКА_SUB_WORKFLOWS.md)
3. [Решение проблем](groups/troubleshooting/ИТОГОВОЕ_ИСПРАВЛЕНИЕ.md)

### Уведомления о @mention
1. [Group Mention Analyzer](../n8n/workflows/README_GROUP_WORKFLOWS.md)
2. [Настройка подписок](groups/deployment/GROUPS_DEPLOYMENT_GUIDE.md)

### Технические детали
1. [Sub-workflows архитектура](groups/implementation/SUB_WORKFLOWS_IMPLEMENTATION.md)
2. [Отчет о реализации](groups/implementation/GROUPS_FINAL_REPORT.md)
3. [Финальный статус](groups/implementation/FINAL_STATUS.md)

---

## 🆘 Помощь

**Частые проблемы:**

| Проблема | Решение |
|----------|---------|
| "Referenced node doesn't exist" | [ИСПРАВЛЕНИЕ_ОШИБКИ_REFERENCED_NODE.md](groups/troubleshooting/ИСПРАВЛЕНИЕ_ОШИБКИ_REFERENCED_NODE.md) |
| "Can't parse entities" | [MARKDOWN_ESCAPING_FIX.md](groups/troubleshooting/MARKDOWN_ESCAPING_FIX.md) |
| n8n возвращает 500 | [ПРОВЕРКА_N8N_WORKFLOWS.md](groups/troubleshooting/ПРОВЕРКА_N8N_WORKFLOWS.md) |
| message_count = 0 | [DIGEST_FIX_FINAL.md](groups/troubleshooting/DIGEST_FIX_FINAL.md) |
| Execute Workflow Trigger | [ИСПРАВЛЕНИЕ_ИНСТРУКЦИЙ.md](groups/troubleshooting/ИСПРАВЛЕНИЕ_ИНСТРУКЦИЙ.md) |

---

## 📝 История проекта

- [CHANGELOG.md](../CHANGELOG.md) - Полная история изменений
- [Архив отчетов](archive/) - Старые отчеты и статусы

---

**Версия:** 1.0 (Sub-workflows architecture)  
**Дата обновления:** 13 октября 2025

