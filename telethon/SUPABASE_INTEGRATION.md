# Интеграция с Supabase PostgreSQL

Это руководство поможет вам настроить telethon для работы с Supabase PostgreSQL вместо SQLite.

## 🔧 Настройка подключения к Supabase

### Вариант 1: Локальная Supabase (через docker-compose)

Если у вас уже запущена локальная Supabase через docker-compose:

1. **Добавьте переменную в корневой `.env` файл:**
```env
# Подключение к локальной Supabase PostgreSQL через основной контейнер
TELEGRAM_DATABASE_URL=postgresql://postgres:xiNmSysbbcqTOWT4eb1KkQtM2fb8X7Ms@supabase-db:5432/postgres?sslmode=disable

# Альтернативно через pooler (если основной не работает)
# TELEGRAM_DATABASE_URL=postgresql://postgres:xiNmSysbbcqTOWT4eb1KkQtM2fb8X7Ms@supabase-pooler:5432/postgres?sslmode=disable

# Временно используем SQLite для тестирования
# TELEGRAM_DATABASE_URL=sqlite:///./data/telethon_bot.db
```

**Примечание:** Используем `supabase-db:5432` для подключения к основному PostgreSQL контейнеру.

2. **Убедитесь, что контейнеры telethon и postgres находятся в одной сети:**
```yaml
# В docker-compose.override.yml добавьте networks для telethon сервисов
networks:
  - default
```

### Вариант 2: Supabase Cloud

Для подключения к Supabase Cloud:

1. **Получите строку подключения из Supabase Dashboard:**
   - Перейдите в Settings > Database
   - Скопируйте Connection string

2. **Добавьте в корневой `.env` файл:**
```env
# Подключение к Supabase Cloud
TELEGRAM_DATABASE_URL=postgresql://postgres:your_password@db.your-project.supabase.co:5432/postgres?sslmode=require
```

### Вариант 3: Настройка в .env файле telethon

Альтернативно, можно настроить прямо в `telethon/.env`:

```env
# В telethon/.env
DATABASE_URL=postgresql://postgres:your_password@postgres:5432/postgres?sslmode=disable
```

## 🚀 Запуск с PostgreSQL

1. **Остановите текущие контейнеры:**
```bash
docker compose -p localai -f docker-compose.override.yml down
```

2. **Обновите .env файл** с правильной строкой подключения к PostgreSQL

3. **Перезапустите контейнеры:**
```bash
docker compose -p localai -f docker-compose.override.yml up --build -d
```

## 📊 Проверка подключения

После запуска проверьте логи:
```bash
# Логи API сервера
docker compose -p localai -f docker-compose.override.yml logs telethon

# Логи бота
docker compose -p localai -f docker-compose.override.yml logs telethon-bot
```

Вы должны увидеть:
- ✅ Успешное подключение к базе данных
- ✅ Создание таблиц (если их еще нет)

## 🔍 Проверка данных в Supabase

1. **Откройте Supabase Dashboard**
2. **Перейдите в Table Editor**
3. **Найдите таблицы:**
   - `users` - пользователи бота
   - `channels` - каналы для парсинга
   - `posts` - посты из каналов

## 🛠️ Миграция данных

Если у вас уже есть данные в SQLite и вы хотите их перенести:

1. **Экспортируйте данные из SQLite:**
```bash
# Создайте SQL дамп
sqlite3 telethon/data/telethon_bot.db .dump > telethon_data.sql
```

2. **Адаптируйте SQL для PostgreSQL** (уберите SQLite-специфичные команды)

3. **Импортируйте в Supabase:**
   - Используйте SQL Editor в Supabase Dashboard
   - Или подключитесь через psql

## 🔧 Устранение проблем

### Ошибка подключения
```
psycopg2.OperationalError: could not connect to server
```

**Решение:**
- Проверьте, что Supabase PostgreSQL запущен
- Убедитесь в правильности строки подключения
- Проверьте сетевые настройки Docker

### Ошибка SSL
```
psycopg2.OperationalError: SSL connection is required
```

**Решение:**
- Для локальной Supabase: `?sslmode=disable`
- Для Supabase Cloud: `?sslmode=require`

### Ошибка прав доступа
```
psycopg2.OperationalError: permission denied for schema public
```

**Решение:**
- Убедитесь, что пользователь `postgres` имеет права на создание таблиц
- Проверьте настройки RLS (Row Level Security) в Supabase

## 📋 Преимущества PostgreSQL

- ✅ **Лучшая производительность** для больших объемов данных
- ✅ **Масштабируемость** - поддержка множественных подключений
- ✅ **Интеграция с Supabase** - доступ к дополнительным функциям
- ✅ **Backup и восстановление** - встроенные инструменты
- ✅ **Мониторинг** - детальная аналитика в Supabase Dashboard

## 🔄 Возврат к SQLite

Если нужно вернуться к SQLite:

1. **Удалите переменную из .env:**
```bash
# Удалите или закомментируйте
# TELEGRAM_DATABASE_URL=...
```

2. **Перезапустите контейнеры:**
```bash
docker compose -p localai -f docker-compose.override.yml up --build -d
```
