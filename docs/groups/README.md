# 📁 Groups - Функционал Telegram групп

Документация по функционалу дайджестов и уведомлений в Telegram группах.

---

## 🗂️ Содержание

### 🚀 [quickstart/](quickstart/)
**Быстрые старты для новых пользователей**

- `БЫСТРЫЙ_СТАРТ.md` - Импорт Sub-workflows (на русском, 20 минут)
- `QUICK_START_SUB_WORKFLOWS.md` - Quick reference (English)
- `QUICK_TEST_GROUPS.md` - Тестирование функционала

**Начните здесь если:**
- Впервые настраиваете Sub-workflows
- Нужна краткая инструкция
- Хотите быстро протестировать

---

### 🚢 [deployment/](deployment/)
**Гайды по развертыванию и настройке**

- `GROUPS_DEPLOYMENT_GUIDE.md` - Полное руководство по развертыванию
- `PRIVATE_GROUPS_GUIDE.md` - Работа с приватными группами

**Используйте когда:**
- Настраиваете проект впервые
- Добавляете новые группы
- Настраиваете приватные группы

---

### 🔧 [troubleshooting/](troubleshooting/)
**Решение проблем и исправление ошибок**

- `ИТОГОВОЕ_ИСПРАВЛЕНИЕ.md` - Сводка всех исправлений
- `ПРОВЕРКА_N8N_WORKFLOWS.md` - Диагностика n8n workflows
- `ИСПРАВЛЕНИЕ_ОШИБКИ_REFERENCED_NODE.md` - "Referenced node doesn't exist"
- `MARKDOWN_ESCAPING_FIX.md` - "Can't parse entities"
- `DIGEST_FIX_FINAL.md` - Пустой дайджест, неправильный count
- `ИСПРАВЛЕНИЕ_ИНСТРУКЦИЙ.md` - Execute Workflow Trigger
- `WORKFLOW_V3_UPDATE.md` - Обновление на v3

**Откройте когда:**
- Получаете ошибку в боте
- n8n возвращает 500
- Неправильные данные в дайджесте
- Проблемы с Markdown форматированием

---

### 📊 [implementation/](implementation/)
**Технические детали и отчеты о реализации**

- `SUB_WORKFLOWS_IMPLEMENTATION.md` - Архитектура Sub-workflows
- `GROUPS_FINAL_REPORT.md` - Финальный отчет реализации
- `GROUPS_IMPLEMENTATION_COMPLETE.md` - Завершение реализации
- `GROUPS_STATUS_REPORT.md` - Статус реализации
- `FINAL_STATUS.md` - Итоговый статус

**Для понимания:**
- Как устроена архитектура
- Какие компоненты добавлены
- История разработки
- Технические решения

---

## 🎯 Быстрая навигация

### Я хочу:

**Начать с нуля:**
→ [БЫСТРЫЙ_СТАРТ.md](quickstart/БЫСТРЫЙ_СТАРТ.md)

**Решить проблему:**
→ [troubleshooting/](troubleshooting/)

**Понять как работает:**
→ [SUB_WORKFLOWS_IMPLEMENTATION.md](implementation/SUB_WORKFLOWS_IMPLEMENTATION.md)

**Развернуть на production:**
→ [GROUPS_DEPLOYMENT_GUIDE.md](deployment/GROUPS_DEPLOYMENT_GUIDE.md)

---

## ⚡ Частые вопросы

**Q: Как импортировать workflows?**  
A: [БЫСТРЫЙ_СТАРТ.md](quickstart/БЫСТРЫЙ_СТАРТ.md) - пошаговая инструкция

**Q: Почему n8n возвращает 500?**  
A: [ПРОВЕРКА_N8N_WORKFLOWS.md](troubleshooting/ПРОВЕРКА_N8N_WORKFLOWS.md)

**Q: Агенты не активируются?**  
A: [ИСПРАВЛЕНИЕ_ИНСТРУКЦИЙ.md](troubleshooting/ИСПРАВЛЕНИЕ_ИНСТРУКЦИЙ.md) - это нормально!

**Q: Как работают Sub-workflows?**  
A: [SUB_WORKFLOWS_IMPLEMENTATION.md](implementation/SUB_WORKFLOWS_IMPLEMENTATION.md)

**Q: Как добавить приватную группу?**  
A: [PRIVATE_GROUPS_GUIDE.md](deployment/PRIVATE_GROUPS_GUIDE.md)

---

## 📋 Чеклист настройки

- [ ] Прочитал [БЫСТРЫЙ_СТАРТ.md](quickstart/БЫСТРЫЙ_СТАРТ.md)
- [ ] Импортировал 3 агента в n8n
- [ ] Импортировал orchestrator
- [ ] Настроил Execute Workflow узлы
- [ ] Протестировал `/group_digest`
- [ ] Работает без ошибок

**Если что-то не работает:** → [troubleshooting/](troubleshooting/)

---

**Вернуться:** [📚 Главная документация](../README.md)

