# 🔄 Миграция Many-to-Many для Supabase (PostgreSQL)

## ✅ Обновлено для Supabase!

Скрипты миграции теперь **автоматически определяют тип БД** и используют правильный SQL синтаксис для PostgreSQL/Supabase.

---

## 🚀 Быстрый старт

```bash
cd /home/ilyasni/n8n-server/n8n-installer/telethon

# Просмотр плана миграции
python3 migrate_services.py --dry-run

# Выполнение миграции
python3 migrate_services.py
```

---

## 🔍 Что делает скрипт

Скрипт автоматически:
1. ✅ Определяет тип БД из `.env` (PostgreSQL/Supabase)
2. ✅ Использует правильный SQL синтаксис для PostgreSQL
3. ✅ Создает таблицу `user_channel`
4. ✅ Переносит данные без дубликатов
5. ✅ Обновляет связи в таблице `posts`

---

## 💾 Резервное копирование (Supabase)

### Вариант 1: Через Supabase Dashboard (рекомендуется)
1. Откройте ваш проект в Supabase Dashboard
2. Перейдите в **Settings** → **Database**
3. Нажмите **Create backup**
4. Дождитесь завершения

### Вариант 2: Через pg_dump (если есть доступ)
```bash
# Получите connection string из Supabase Dashboard
# Settings → Database → Connection string

pg_dump "postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT].supabase.co:5432/postgres" > backup.sql
```

---

## ⚙️ Определение типа БД

Скрипт автоматически определяет тип БД из `.env`:

```bash
# PostgreSQL (Supabase)
DATABASE_URL=postgresql://postgres:password@db.project.supabase.co:5432/postgres?sslmode=require
```

Вывод скрипта покажет:
```
✅ [SUCCESS] Тип БД: PostgreSQL (Supabase)
```

---

## 📊 Проверка после миграции

### Через Supabase Dashboard
1. Откройте **Table Editor**
2. Проверьте таблицу `channels` - должны быть уникальные каналы
3. Проверьте таблицу `user_channel` - связи пользователей с каналами
4. Убедитесь что нет дубликатов в `channels`

### Через SQL Editor в Supabase
```sql
-- Количество уникальных каналов
SELECT COUNT(*) FROM channels;

-- Количество подписок
SELECT COUNT(*) FROM user_channel;

-- Проверка отсутствия дубликатов
SELECT channel_username, COUNT(*) as cnt 
FROM channels 
GROUP BY channel_username 
HAVING COUNT(*) > 1;
-- Должно быть пусто!

-- Посмотреть каналы с количеством подписчиков
SELECT c.channel_username, c.channel_title, COUNT(uc.user_id) as subscribers
FROM channels c
LEFT JOIN user_channel uc ON c.id = uc.channel_id
GROUP BY c.id, c.channel_username, c.channel_title
ORDER BY subscribers DESC;
```

---

## 🔄 Откат миграции

### Через Supabase Dashboard
1. **Settings** → **Database** → **Backups**
2. Выберите backup созданный до миграции
3. Нажмите **Restore**

### Через pg_restore (если есть dump)
```bash
# ВНИМАНИЕ: Это удалит текущую БД!
psql "postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT].supabase.co:5432/postgres" < backup.sql
```

---

## ⚠️ Важные отличия от SQLite

| Параметр | SQLite | PostgreSQL (Supabase) |
|----------|--------|----------------------|
| Файл БД | Да (telegram.db) | Нет (облако) |
| Резервная копия | Автоматически (файл) | Вручную (Supabase Dashboard) |
| Проверка | sqlite3 команды | SQL Editor / Dashboard |
| ID генерация | AUTOINCREMENT | SERIAL |
| ON CONFLICT | Поддерживается | Поддерживается |

---

## 🧪 Тестирование

```bash
# Запустить все тесты
python3 test_many_to_many.py

# Тесты работают с обоими типами БД
```

---

## 📈 Типичные результаты

### До миграции:
```sql
SELECT COUNT(*) FROM channels;
-- Пример: 150 (с дубликатами)
```

### После миграции:
```sql
-- Уникальные каналы
SELECT COUNT(*) FROM channels;
-- Пример: 80

-- Подписки (связи)
SELECT COUNT(*) FROM user_channel;
-- Пример: 150

-- Сэкономлено: 70 записей (47%)
```

---

## 🔧 Устранение проблем

### Ошибка: "relation channels already exists"
Миграция уже выполнена. Проверьте структуру:
```sql
\d channels;  -- Должен быть без user_id
\d user_channel;  -- Должна существовать
```

### Ошибка: "permission denied"
Проверьте права доступа к БД в Supabase.

### Ошибка подключения
Проверьте:
1. CONNECTION POOLER URL в .env (для Supabase)
2. Правильность пароля
3. Доступность интернета

---

## 📚 Дополнительная документация

- **README_MIGRATION.md** - главная точка входа
- **QUICK_MIGRATION.md** - быстрая инструкция
- **MIGRATION_MANY_TO_MANY.md** - полная документация
- **CHANGELOG_MANY_TO_MANY.md** - все изменения

---

## ✨ Преимущества для Supabase

1. **Масштабируемость**: PostgreSQL лучше справляется с большими объемами
2. **Целостность данных**: Строгие FOREIGN KEY constraints
3. **Производительность**: Индексы PostgreSQL эффективнее
4. **Аналитика**: Мощные возможности для запросов
5. **Backup**: Встроенные механизмы резервного копирования

---

## 🎉 Готово!

Теперь ваша система использует эффективную структуру Many-to-Many с поддержкой PostgreSQL/Supabase!

```bash
# Запустите миграцию
python3 migrate_services.py
```

**Версия:** 2.0.0  
**Поддержка:** PostgreSQL 12+, Supabase  
**Дата:** 10 октября 2024

