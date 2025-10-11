# Changelog: Система автоматического тегирования

## Дата: 2025-10-10

### ✨ Новые возможности

#### 1. Автоматическое тегирование постов
- Посты автоматически анализируются с помощью LLM (OpenRouter API)
- Генерируется 3-7 релевантных тегов на русском языке
- Теги сохраняются в формате JSON массива
- Фоновая обработка не блокирует парсинг

#### 2. API Endpoints
- `POST /posts/{post_id}/generate_tags` - генерация тегов для одного поста
- `POST /users/{telegram_id}/posts/generate_tags` - генерация тегов для всех постов пользователя
- `GET /posts/tags/stats` - статистика по тегам
- `GET /users/{telegram_id}/posts` - теперь включает теги в ответе

#### 3. Интеграция с парсером
- После парсинга автоматически запускается тегирование новых постов
- Асинхронная обработка для оптимальной производительности

### 📝 Измененные файлы

#### models.py
- Добавлено поле `tags` (JSON) в модель `Post`
- Поддержка хранения массива тегов

#### parser_service.py
- Добавлено отслеживание ID новых постов
- Запуск фонового тегирования после парсинга
- Метод `_tag_new_posts_background()` для асинхронной обработки

#### main.py
- Добавлены новые endpoints для управления тегами
- Обновлен endpoint получения постов (включает теги)
- Добавлен endpoint статистики по тегам

#### requirements.txt
- Добавлена зависимость `httpx==0.25.2` для HTTP запросов

#### .env.example
- Добавлены настройки OpenRouter:
  - `OPENROUTER_API_KEY`
  - `OPENROUTER_MODEL`
  - `TAGGING_BATCH_SIZE`

### 🆕 Новые файлы

#### tagging_service.py
Основной сервис тегирования с функциями:
- `generate_tags_for_text()` - генерация тегов через LLM
- `update_post_tags()` - обновление тегов поста
- `process_posts_batch()` - пакетная обработка постов
- `tag_posts_without_tags()` - тегирование постов без тегов

#### add_tags_column.py
Скрипт миграции базы данных:
- Добавление колонки `tags` в таблицу `posts`
- Поддержка SQLite и PostgreSQL
- Автоматическая проверка и валидация

#### TAGGING_README.md
Полная документация по системе тегирования:
- Установка и настройка
- Использование API
- Интеграция с n8n
- Решение проблем

#### n8n_tagging_workflow_example.json
Пример n8n workflow:
- Получение постов
- Генерация тегов для постов без них
- Анализ и статистика по тегам

### 🔧 Миграция базы данных

Для применения изменений выполните:

```bash
python add_tags_column.py
```

### 📋 Установка (Docker)

```bash
# 1. Настройте переменные окружения
# Добавьте в telethon/.env:
# OPENROUTER_API_KEY=your_key_here
# OPENROUTER_MODEL=openai/gpt-oss-20b:free
# TAGGING_BATCH_SIZE=10

# 2. Пересоберите Docker образ
cd /home/ilyasni/n8n-server/n8n-installer
docker-compose -f docker-compose.yml -f docker-compose.override.yml build telethon

# 3. Выполните миграцию
docker-compose -f docker-compose.yml -f docker-compose.override.yml run --rm telethon python add_tags_column.py

# 4. Перезапустите систему
docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d telethon telethon-bot
```

### 🎯 Примеры использования

#### Автоматическое тегирование
Теги генерируются автоматически при парсинге каналов.

#### Ручная генерация тегов
```bash
# Для одного поста
curl -X POST "http://localhost:8010/posts/123/generate_tags"

# Для всех постов пользователя
curl -X POST "http://localhost:8010/users/123456789/posts/generate_tags"
```

#### Получение постов с тегами
```bash
curl "http://localhost:8010/users/123456789/posts"
```

#### Статистика по тегам
```bash
curl "http://localhost:8010/posts/tags/stats"
```

### 🔐 Безопасность

- API ключ хранится в зашифрованном виде в `.env`
- Не передается в репозиторий (добавлен в `.gitignore`)
- Используется HTTPS для связи с OpenRouter API

### ⚙️ Настройки по умолчанию

- Модель: `google/gemini-2.0-flash-exp:free` (бесплатная, январь 2025)
- Размер батча: 10 постов
- Задержка между запросами: 1 секунда
- Количество тегов: 3-7 на пост

**Важно:** Для работы бесплатных моделей настройте политику данных на https://openrouter.ai/settings/privacy

### 📊 Производительность

- Фоновая обработка не блокирует основной парсинг
- Пакетная обработка для оптимизации
- Rate limiting для соблюдения лимитов API

### 🐛 Известные ограничения

- Требуется API ключ OpenRouter
- Бесплатная модель может иметь ограничения по скорости
- Теги генерируются только для постов с текстом

### 📚 Дополнительные ресурсы

- [TAGGING_README.md](TAGGING_README.md) - Полная документация
- [OpenRouter Documentation](https://openrouter.ai/docs)
- [n8n Workflow Example](n8n_tagging_workflow_example.json)

### 🤝 Вклад

Разработано для проекта n8n-server/n8n-installer

