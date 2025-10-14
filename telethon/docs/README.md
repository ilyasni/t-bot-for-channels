# 📚 Telegram Bot Documentation

Централизованная документация проекта Telegram Channel Parser Bot.

## 🚀 Быстрый старт

| Я хочу... | Перейти к документу |
|-----------|---------------------|
| 🆕 Начать с нуля | [guides/START_HERE.md](guides/START_HERE.md) |
| 🎨 Использовать HTML форматирование | [formatting/HTML_FORMAT_EXAMPLES.md](formatting/HTML_FORMAT_EXAMPLES.md) ⭐ |
| 🚀 Задеплоить изменения | [formatting/DEPLOYMENT_GUIDE.md](formatting/DEPLOYMENT_GUIDE.md) |
| 🧪 Запустить тесты | [testing/TESTING_GUIDE.md](testing/TESTING_GUIDE.md) |
| ⚡ Быстрая настройка | [quickstart/QUICK_START.md](quickstart/QUICK_START.md) |
| 🔍 Настроить RAG | [quickstart/RAG_QUICKSTART.md](quickstart/RAG_QUICKSTART.md) |
| 🔐 Настроить QR Login | [quickstart/QR_LOGIN_GUIDE.md](quickstart/QR_LOGIN_GUIDE.md) |

## 📂 Структура документации

### 🎨 [formatting/](formatting/) - HTML Форматирование (NEW!)
- **HTML_FORMATTING_COMPLETE.md** ⭐ - Полная документация (12KB)
- **HTML_FORMAT_EXAMPLES.md** ⭐ - 10 примеров использования (13KB)
- **DEPLOYMENT_GUIDE.md** ⭐ - Deployment инструкции (10KB)

**Новое в v3.3.0:**
- Blockquote и expandable blockquote
- Spoilers `<tg-spoiler>`
- Code blocks с подсветкой языка
- RAG ответы с expandable источниками
- Умные дайджесты с auto-expandable

### ✨ [features/](features/) - Функциональность
- **GROUPS_FEATURE_README.md** - Groups мониторинг и дайджесты
- **TAGGING_INDEXING_VERIFICATION.md** - Автоматическое тегирование
- **SUBSCRIPTIONS.md** - Система подписок (Trial/Premium/Enterprise)
- **[rag/](features/rag/)** - RAG система и векторный поиск
- **[voice/](features/voice/)** - Голосовые команды (SaluteSpeech)
- **[groups/](features/groups/)** - Groups дайджесты через n8n

### 📖 [guides/](guides/) - Руководства
- **START_HERE.md** - Полное руководство для новичков
- **QUICK_REFERENCE.md** - Быстрый справочник по командам
- **COMMANDS_CHEATSHEET.md** - Шпаргалка по всем командам бота
- **DOCKER_TESTING.md** - Тестирование в Docker окружении

### 🧪 [testing/](testing/) - Тестирование
- **TESTING_GUIDE.md** - Полное руководство по тестированию
- **TEST_SUITE_SUMMARY.md** - Сводка по test suite
- **TESTING.md** - Базовые инструкции
- **README_TESTS.md** - Документация тестов

**Статус:** ✅ 42/42 тестов проходят

### ⚡ [quickstart/](quickstart/) - Быстрые старты
- **QUICK_START.md** - Быстрый старт проекта
- **RAG_QUICKSTART.md** - Настройка RAG за 5 минут
- **QR_LOGIN_GUIDE.md** - Настройка QR аутентификации
- **ADMIN_PANEL_QUICKSTART.md** - Админ панель через Mini App

### 🔧 [troubleshooting/](troubleshooting/) - Решение проблем
- **CONNECTION_TROUBLESHOOTING.md** - Проблемы подключения
- **RATE_LIMIT_429.md** - Rate limit ошибки
- **GIGACHAT_MODEL_CHECK.md** - Проблемы с GigaChat
- **QR_LOGIN_2FA_ISSUE.md** - Проблемы с 2FA
- **TIMEZONE_FIX.md** - Проблемы с timezone

### 🗄️ [migrations/](migrations/) - Миграции БД
- **README_MIGRATION.md** - Руководство по миграциям
- **MIGRATION_MANY_TO_MANY.md** - Many-to-many relationships
- **MIGRATION_SUPABASE.md** - Интеграция с Supabase

### 📦 [archive/](archive/) - Архив
Исторические документы, старые отчёты и миграции.  
**Не для повседневного использования.**

## 📝 Актуальная документация (v3.3.0)

| Документ | Версия | Статус | Описание |
|----------|--------|--------|----------|
| **HTML_FORMATTING_COMPLETE.md** | 1.0 | ✅ Актуально | Полная документация HTML форматирования |
| **HTML_FORMAT_EXAMPLES.md** | 1.0 | ✅ Актуально | 10 практических примеров |
| **DEPLOYMENT_GUIDE.md** | 1.0 | ✅ Актуально | Production deployment guide |
| TESTING_GUIDE.md | 3.3 | ✅ Актуально | Руководство по тестированию |
| GROUPS_FEATURE_README.md | 1.0 | ✅ Актуально | Groups мониторинг |
| RAG_QUICKSTART.md | 1.2 | ✅ Актуально | RAG setup guide |

## 🔍 Навигация по темам

### Разработка
- [START_HERE.md](guides/START_HERE.md) - Начало работы
- [QUICK_REFERENCE.md](guides/QUICK_REFERENCE.md) - Справочник
- [TESTING_GUIDE.md](testing/TESTING_GUIDE.md) - Тестирование

### Форматирование
- [HTML_FORMAT_EXAMPLES.md](formatting/HTML_FORMAT_EXAMPLES.md) - Примеры HTML
- [HTML_FORMATTING_COMPLETE.md](formatting/HTML_FORMATTING_COMPLETE.md) - Полная документация
- [DEPLOYMENT_GUIDE.md](formatting/DEPLOYMENT_GUIDE.md) - Деплой

### Функции
- [GROUPS_FEATURE_README.md](features/GROUPS_FEATURE_README.md) - Groups
- [features/rag/README.md](features/rag/README.md) - RAG система
- [features/voice/README.md](features/voice/README.md) - Голосовые команды

### Troubleshooting
- [CONNECTION_TROUBLESHOOTING.md](troubleshooting/CONNECTION_TROUBLESHOOTING.md) - Подключение
- [RATE_LIMIT_429.md](troubleshooting/RATE_LIMIT_429.md) - Rate limits
- [GIGACHAT_MODEL_CHECK.md](troubleshooting/GIGACHAT_MODEL_CHECK.md) - GigaChat

## 🎯 Рекомендуемый путь изучения

**Для новичков:**
1. [guides/START_HERE.md](guides/START_HERE.md)
2. [quickstart/QUICK_START.md](quickstart/QUICK_START.md)
3. [guides/COMMANDS_CHEATSHEET.md](guides/COMMANDS_CHEATSHEET.md)
4. [testing/TESTING_GUIDE.md](testing/TESTING_GUIDE.md)

**Для HTML форматирования:**
1. [formatting/HTML_FORMAT_EXAMPLES.md](formatting/HTML_FORMAT_EXAMPLES.md) ⭐
2. [formatting/HTML_FORMATTING_COMPLETE.md](formatting/HTML_FORMATTING_COMPLETE.md)
3. [formatting/DEPLOYMENT_GUIDE.md](formatting/DEPLOYMENT_GUIDE.md)

**Для настройки фич:**
1. [quickstart/RAG_QUICKSTART.md](quickstart/RAG_QUICKSTART.md)
2. [quickstart/QR_LOGIN_GUIDE.md](quickstart/QR_LOGIN_GUIDE.md)
3. [features/GROUPS_FEATURE_README.md](features/GROUPS_FEATURE_README.md)

## 🆕 Последние обновления

### 14.10.2025 - HTML Formatting v1.0
- ✅ Полная поддержка Telegram HTML тегов
- ✅ Expandable blockquote для длинного контента
- ✅ Spoilers и code blocks с языками
- ✅ RAG ответы с expandable источниками
- ✅ 42/42 тестов проходят
- ✅ Production ready

### Архивировано
- Markdown миграция документы → [archive/](archive/)
- Старые отчёты по тестам → [archive/testing/](archive/testing/)
- Исторические summaries → [archive/](archive/)

## 💡 Полезные команды

```bash
# Найти документ по ключевому слову
cd /home/ilyasni/n8n-server/n8n-installer/telethon/docs
grep -r "blockquote" .

# Список всех md файлов
find . -name "*.md" | sort

# Поиск по содержимому
grep -r "example" . --include="*.md"
```

## 📊 Статистика документации

- **Всего документов:** ~150
- **Актуальных:** ~25
- **Архивных:** ~125
- **Категорий:** 8
- **Языков:** Русский/English
- **Формат:** Markdown (.md)

## 🤝 Контрибьюторы

При добавлении новой документации:

1. **Выбрать правильную категорию** (formatting/features/guides/etc)
2. **Использовать template:**
   ```markdown
   # Название
   
   ## Контекст
   ## План
   ## Примеры
   ## Проверка
   ```
3. **Обновить этот README.md** с ссылкой на новый документ
4. **Добавить в соответствующую папку**

---

**Последнее обновление:** 14 октября 2025  
**Версия документации:** 3.3.0  
**Статус:** ✅ Актуально
