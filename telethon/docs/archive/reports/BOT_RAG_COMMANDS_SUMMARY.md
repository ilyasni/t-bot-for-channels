# Реализация RAG команд для Telegram бота

**Дата:** 11 октября 2025  
**Версия:** 2.2.1  
**Статус:** ✅ Реализовано, ожидает тестирования

---

## ✅ Что реализовано

### 1. Новые команды бота (bot.py)

#### `/ask <вопрос>` - RAG-поиск ответа
- ✅ Отправка запроса к RAG service
- ✅ Форматирование ответа с источниками
- ✅ Обработка всех edge cases
- ✅ Индикатор "печатает..."
- ✅ Проверка аутентификации и наличия постов

#### `/recommend` - Персональные рекомендации
- ✅ Получение рекомендаций от RAG service
- ✅ Форматирование с процентами релевантности
- ✅ Обработка случаев отсутствия истории
- ✅ Ссылки на посты

#### `/search <запрос>` - Гибридный поиск
- ✅ Поиск в постах (Qdrant)
- ✅ Поиск в интернете (Searxng)
- ✅ Разделение результатов на "Ваши" и "Интернет"
- ✅ Inline кнопки для фильтрации
- ✅ Обработка отсутствия результатов

#### `/digest` - Настройка AI-дайджестов
- ✅ Получение текущих настроек от RAG service
- ✅ Inline меню с 6 настройками
- ✅ 12 callback handlers для кнопок
- ✅ State management для ввода тем
- ✅ Включение/отключение дайджеста
- ✅ Выбор частоты (daily/weekly)
- ✅ Выбор времени (09:00, 12:00, 18:00, 21:00)
- ✅ Toggle AI-суммаризации
- ✅ Выбор стиля (concise/detailed/executive)

### 2. Вспомогательные методы

#### `_call_rag_service()` - Универсальный HTTP клиент
- ✅ Поддержка GET и POST запросов
- ✅ Timeout handling (30s)
- ✅ Connect error handling
- ✅ Graceful fallback

#### `_show_digest_menu()` - Отображение меню дайджестов
- ✅ Динамическое получение настроек
- ✅ Форматирование текущих значений
- ✅ Генерация inline кнопок
- ✅ Поддержка edit и reply режимов

#### `handle_digest_callback()` - Обработка digest кнопок
- ✅ 12 различных callback actions
- ✅ Обновление настроек через API
- ✅ Навигация между меню
- ✅ State management для ввода

#### `handle_search_callback()` - Обработка search кнопок
- ✅ Фильтрация по типу (posts/web/both)
- ✅ Переформатирование результатов
- ✅ Динамические кнопки

### 3. Обновленные методы

#### `handle_text()` - Обработка текстовых сообщений
- ✅ Добавлена обработка ввода тем для digest
- ✅ Парсинг тем через запятую
- ✅ Сохранение через RAG API
- ✅ Очистка state после ввода
- ✅ Обновлено сообщение с подсказками (добавлены /ask, /search)

#### `help_command()` - Справка
- ✅ Добавлена секция "RAG & AI"
- ✅ Примеры использования новых команд
- ✅ Обновлен workflow (добавлены RAG шаги)

#### `start_command()` - Приветствие
- ✅ Упоминание RAG команд для новых пользователей
- ✅ Обновлен список команд для аутентифицированных

### 4. Обогащение постов (parser_service.py)

#### `_extract_urls()` - Извлечение URL
- ✅ Regex для поиска https:// и http:// ссылок
- ✅ Обработка отсутствия текста
- ✅ Возврат списка URL

#### `_enrich_post_with_links()` - Обогащение контентом
- ✅ Проверка `CRAWL4AI_ENABLED`
- ✅ Вызов Crawl4AI API
- ✅ Timeout handling (30s default)
- ✅ Сохранение в `post.enriched_content`
- ✅ Ограничение размера (2000 символов)
- ✅ Логирование успеха/ошибок
- ✅ Graceful degradation (ошибки не ломают парсинг)

#### Интеграция в `parse_channel_posts()`
- ✅ Вызов после создания нового поста
- ✅ Обработка асинхронно
- ✅ Не блокирует парсинг

### 5. Обновление модели данных (models.py)

#### Таблица `posts`
- ✅ Добавлено поле `enriched_content` (Text, nullable)
- ✅ Комментарий о назначении поля

### 6. Миграция БД

#### `scripts/migrations/add_enriched_content.py`
- ✅ Проверка существования столбца
- ✅ Создание backup (SQLite)
- ✅ Добавление столбца ALTER TABLE
- ✅ Поддержка SQLite и PostgreSQL
- ✅ Инструкции по откату
- ✅ Валидация перед выполнением

### 7. Документация

#### `docs/features/rag/BOT_RAG_COMMANDS.md`
- ✅ Полное описание всех команд
- ✅ Примеры использования
- ✅ Технические детали
- ✅ Сценарии тестирования
- ✅ Troubleshooting guide

---

## 📊 Статистика изменений

| Файл | Добавлено строк | Функций/Методов |
|------|-----------------|-----------------|
| bot.py | ~800 | 6 новых |
| parser_service.py | ~70 | 2 новых |
| models.py | 3 | - |
| add_enriched_content.py | 140 | - |
| BOT_RAG_COMMANDS.md | 400+ | - |
| **ИТОГО** | **~1413** | **8** |

---

## 🔄 Следующие шаги (для тестирования)

### 1. Запустить миграцию БД

```bash
cd /home/ilyasni/n8n-server/n8n-installer/telethon
python scripts/migrations/add_enriched_content.py
```

**Ожидаемый результат:**
```
============================================================
Миграция: Добавление поля enriched_content
============================================================
📊 База данных: sqlite
✅ Backup создан: data/telethon_bot.db.backup_20251011_HHMMSS

⚠️ Продолжить миграцию? (yes/no): yes

🚀 Начало миграции...
✅ Столбец enriched_content успешно добавлен

============================================================
✅ Миграция завершена успешно!
============================================================
```

### 2. Пересобрать контейнеры

```bash
cd /home/ilyasni/n8n-server/n8n-installer

# Пересобрать telethon и telethon-bot
docker compose up telethon telethon-bot --build -d

# Или через alias (если настроен)
telethon-rebuild
```

### 3. Проверить логи

```bash
# Логи бота
docker logs -f telethon-bot

# Ожидаемые логи:
# ✅ База данных инициализирована
# ✅ Telegram Bot запущен
# 🤖 Запуск Telegram бота...
```

### 4. Проверить RAG service

```bash
# Health check
curl http://localhost:8020/health

# Ожидаемый результат:
# {
#   "status": "healthy",
#   "qdrant_connected": true,
#   "gigachat_available": true,
#   "openrouter_available": true
# }
```

### 5. Тестирование в Telegram

#### Базовый workflow:
```
1. /start                          # ✅ Видим упоминание RAG команд
2. /help                           # ✅ Видим секцию "RAG & AI"
3. /auth                           # Аутентификация
4. /add_channel @tech_channel      # Добавляем канал
5. [Ждем 5-10 минут парсинга]
6. /ask Что нового?                # ✅ Получаем ответ
7. /search технологии              # ✅ Гибридный поиск
8. /recommend                      # ✅ Рекомендации
9. /digest                         # ✅ Настройки дайджестов
```

#### Детальное тестирование каждой команды:

**`/ask`:**
- ✅ С аргументами → ответ с источниками
- ✅ Без аргументов → usage
- ✅ Не auth → предлагает /auth
- ✅ Нет постов → предлагает /add_channel

**`/recommend`:**
- ✅ С историей запросов → 5 рекомендаций
- ✅ Без истории → предлагает /ask

**`/search`:**
- ✅ С аргументами → посты + web
- ✅ Без аргументов → usage
- ✅ Кнопки фильтрации работают

**`/digest`:**
- ✅ Показывает настройки
- ✅ Все кнопки работают
- ✅ Ввод тем сохраняется
- ✅ Включение/отключение работает

### 6. Тестирование обогащения постов

```bash
# 1. Включить Crawl4AI в .env
echo "CRAWL4AI_ENABLED=true" >> telethon/.env

# 2. Перезапустить telethon
docker compose restart telethon

# 3. Добавить канал с постами содержащими ссылки
# В Telegram:
/add_channel @channel_with_links

# 4. Проверить логи парсера
docker logs telethon | grep "обогащен"

# Ожидаемый лог:
# ✅ ParserService: Пост 123 обогащен контентом ссылки https://example.com
```

---

## ⚠️ Известные ограничения

1. **Crawl4AI timeout:** При медленных сайтах может происходить timeout
   - **Решение:** Увеличить `CRAWL4AI_TIMEOUT` до 60 секунд

2. **Searxng rate limits:** При интенсивном использовании возможны ограничения
   - **Решение:** Кеширование результатов в Redis (будет добавлено)

3. **Длинные ответы `/ask`:** Telegram ограничивает длину сообщений (4096 символов)
   - **Решение:** Текст обрезается автоматически (можно добавить пагинацию)

4. **Callback data limits:** Telegram ограничивает размер callback_data (64 байта)
   - **Решение:** Для `/search` callback обрезаем query до 30 символов

---

## 🎯 Критерии приемки

- [x] Все импорты добавлены
- [x] Команды зарегистрированы в setup_handlers()
- [x] Реализовано 4 новые команды
- [x] Реализовано 2 callback handlers
- [x] Добавлен универсальный _call_rag_service()
- [x] Обновлена команда /help
- [x] Обновлены welcome сообщения /start
- [x] Добавлено поле enriched_content в модель
- [x] Созданы методы обогащения постов
- [x] Создана миграция БД
- [x] Написана полная документация
- [ ] Запущена миграция БД
- [ ] Пересобраны контейнеры
- [ ] Протестированы все команды
- [ ] Проверено обогащение постов

---

## 🚀 Быстрый запуск для тестирования

```bash
# 1. Перейти в директорию проекта
cd /home/ilyasni/n8n-server/n8n-installer/telethon

# 2. Запустить миграцию
python scripts/migrations/add_enriched_content.py
# Ответить: yes

# 3. Пересобрать контейнеры
cd /home/ilyasni/n8n-server/n8n-installer
docker compose up telethon telethon-bot --build -d

# 4. Проверить логи
docker logs -f telethon-bot

# 5. В Telegram боте:
/start
/help
/auth
/add_channel @some_channel
# [Подождать 5-10 минут]
/ask Что нового?
/search технологии
/recommend
/digest
```

---

## 📁 Измененные файлы

1. **telethon/bot.py** (+800 строк)
   - Импорты: httpx, asyncio, typing
   - Новые команды: ask_command, recommend_command, search_command, digest_command
   - Callback handlers: handle_digest_callback, handle_search_callback
   - Утилиты: _call_rag_service, _show_digest_menu
   - Обновления: help_command, start_command, handle_text

2. **telethon/parser_service.py** (+70 строк)
   - Методы: _extract_urls, _enrich_post_with_links
   - Интеграция: вызов обогащения после создания поста

3. **telethon/models.py** (+3 строки)
   - Поле: enriched_content (Text, nullable)

4. **telethon/scripts/migrations/add_enriched_content.py** (новый файл, 140 строк)
   - Миграция для добавления enriched_content
   - Backup и rollback support

5. **telethon/docs/features/rag/BOT_RAG_COMMANDS.md** (новый файл, 400+ строк)
   - Полная документация новых команд
   - Примеры использования
   - Сценарии тестирования

6. **telethon/BOT_RAG_COMMANDS_SUMMARY.md** (этот файл)
   - Отчет о реализации
   - Инструкции по запуску

---

## 🔧 Конфигурация

### Обязательные переменные (уже настроены):

```bash
# В корневом .env или telethon/.env
RAG_SERVICE_URL=http://rag-service:8020
RAG_SERVICE_ENABLED=true
```

### Опциональные переменные:

```bash
# Для обогащения постов ссылками (по желанию)
CRAWL4AI_ENABLED=false          # Изменить на true для включения
CRAWL4AI_URL=http://crawl4ai:11235
CRAWL4AI_TIMEOUT=30
CRAWL4AI_WORD_THRESHOLD=100

# Для веб-поиска в /search (рекомендуется)
SEARXNG_ENABLED=true
SEARXNG_URL=https://searxng.produman.studio
SEARXNG_USER=hello@ilyasni.com
SEARXNG_PASSWORD=B5Hp8jfp7sjDnb4XwRRzPo54RYETVOhX
```

---

## 🐛 Возможные проблемы и решения

### Проблема 1: RAG service недоступен

**Симптомы:**
```
/ask не работает
/recommend возвращает ошибку
/digest не показывает настройки
```

**Решение:**
```bash
# Проверить статус
docker ps | grep rag-service

# Если не запущен
docker compose up rag-service -d

# Проверить логи
docker logs rag-service

# Проверить health
curl http://localhost:8020/health
```

### Проблема 2: Команды не зарегистрированы

**Симптомы:**
```
Бот не реагирует на /ask, /search, etc.
```

**Решение:**
```bash
# Пересобрать контейнер бота
docker compose up telethon-bot --build -d

# Проверить логи на ошибки
docker logs telethon-bot
```

### Проблема 3: Миграция не прошла

**Симптомы:**
```
Ошибка при обогащении постов
Поле enriched_content не существует
```

**Решение:**
```bash
# Повторить миграцию
python scripts/migrations/add_enriched_content.py

# Или вручную в БД
docker exec telethon python -c "
from database import SessionLocal, engine
from sqlalchemy import text
engine.execute(text('ALTER TABLE posts ADD COLUMN enriched_content TEXT'))
"
```

### Проблема 4: Ответы Telegram слишком длинные

**Симптомы:**
```
Ошибка: Message is too long
```

**Решение:**
- RAG service уже ограничивает ответы до 500 tokens
- Если проблема сохраняется, можно обрезать в боте:
```python
if len(answer) > 3000:
    answer = answer[:2997] + "..."
```

---

## 📈 Метрики использования

После внедрения можно отслеживать:

```bash
# Через логи
docker logs telethon-bot | grep "Команда /ask"
docker logs telethon-bot | grep "Команда /search"

# Через RAG API
curl http://localhost:8020/rag/stats/USER_ID

# Статистика запросов
curl http://localhost:8020/rag/query_history/USER_ID
```

---

## ✨ Будущие улучшения

Возможные доработки (не в текущем scope):

1. **Пагинация для длинных ответов**
   - Кнопки "Следующая страница" для `/search`

2. **Кеширование в Redis**
   - Кеш ответов `/ask` на 1 час
   - Кеш результатов `/search` на 30 минут

3. **Inline mode**
   - `@bot что нового в AI?` → инлайн результаты

4. **Голосовые запросы**
   - Speech-to-Text для голосовых `/ask`

5. **Экспорт дайджестов**
   - Отправка в PDF/HTML формате

6. **Расширенные фильтры**
   - Фильтрация по датам, каналам, тегам

7. **Статистика использования**
   - Команда `/stats` для просмотра своей активности

---

## 📚 Связанная документация

- [RAG System Quickstart](docs/quickstart/RAG_QUICKSTART.md)
- [RAG Implementation Summary](docs/features/rag/RAG_IMPLEMENTATION_SUMMARY.md)
- [Cursor Rules v2.2](.cursor/rules/n8n-telegram-bot.mdc)
- [API Documentation](http://localhost:8020/docs)

---

**Автор:** AI Assistant (Claude Sonnet 4.5)  
**Проект:** n8n-server / Telegram Channel Parser + RAG System

