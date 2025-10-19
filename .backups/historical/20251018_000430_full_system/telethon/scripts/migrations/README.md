# 🔄 Миграции базы данных

Список всех миграций для Telegram Channel Parser.

## 📋 Доступные миграции

### 1. `add_tagging_status_fields.py`

**Дата:** 11 октября 2025  
**Статус:** ✅ Готов к применению

**Описание:**  
Добавляет поля для отслеживания статуса тегирования постов.

**Новые поля:**
- `tagging_status` (VARCHAR) - статус тегирования: pending, success, failed, retrying, skipped
- `tagging_attempts` (INTEGER) - количество попыток тегирования
- `last_tagging_attempt` (DATETIME/TIMESTAMP) - время последней попытки
- `tagging_error` (TEXT) - текст последней ошибки

**Применение:**
```bash
cd /home/ilyasni/n8n-server/n8n-installer/telethon
python scripts/migrations/add_tagging_status_fields.py
```

**Совместимость:**
- ✅ SQLite
- ✅ PostgreSQL / Supabase

**Что делает:**
1. Проверяет существование полей (безопасная повторная миграция)
2. Добавляет недостающие поля
3. Обновляет статус существующих постов:
   - Посты с тегами → `success`
   - Посты без тегов с текстом → `pending`
   - Посты без текста → `skipped`

**Rollback:**  
Не требуется - поля nullable, не влияют на существующий функционал.

**Связанные документы:**
- [TAGGING_RETRY_SYSTEM.md](../../docs/features/TAGGING_RETRY_SYSTEM.md)
- [TAGGING_RETRY_QUICK_FIX.md](../../TAGGING_RETRY_QUICK_FIX.md)

---

## 🚀 Применение миграций

### Подготовка

1. **Бэкап БД** (рекомендуется):
   ```bash
   # SQLite
   cp data/telethon_bot.db data/telethon_bot.db.backup
   
   # PostgreSQL
   docker exec supabase-db pg_dump -U postgres postgres > backup_$(date +%Y%m%d).sql
   ```

2. **Проверка подключения:**
   ```bash
   python -c "from database import engine; print(engine.url)"
   ```

### Запуск миграции

```bash
cd /home/ilyasni/n8n-server/n8n-installer/telethon
python scripts/migrations/<migration_name>.py
```

### Проверка результата

```bash
# SQLite
sqlite3 data/telethon_bot.db ".schema posts"

# PostgreSQL (через Docker)
docker exec supabase-db psql -U postgres -d postgres -c "\d posts"

# Или через Python
python -c "from sqlalchemy import inspect; from database import engine; print(inspect(engine).get_columns('posts'))"
```

## 🔍 Информация о миграциях

### История миграций

| Дата | Файл | Описание | Статус |
|------|------|----------|--------|
| 2025-10-11 | `add_tagging_status_fields.py` | Поля для retry тегирования | ✅ Готов |

### Best Practices

1. **Всегда делайте бэкап** перед миграцией
2. **Тестируйте на локальной БД** перед продакшном
3. **Читайте логи** миграции внимательно
4. **Проверяйте результат** после миграции

### Безопасность

- ✅ Все миграции проверяют существование полей
- ✅ Безопасный повторный запуск (idempotent)
- ✅ Не удаляют данные
- ✅ Nullable поля по умолчанию

## 🐛 Troubleshooting

### Ошибка: "column already exists"

**Причина:** Миграция уже была применена.

**Решение:** Это нормально, миграция пропустит существующие поля.

### Ошибка: "database is locked" (SQLite)

**Причина:** БД используется другим процессом.

**Решение:**
```bash
# Остановите контейнеры
docker compose -p localai stop telethon telethon-bot

# Запустите миграцию
python scripts/migrations/<migration_name>.py

# Перезапустите контейнеры
docker compose -p localai start telethon telethon-bot
```

### Ошибка: "permission denied" (PostgreSQL)

**Причина:** Недостаточно прав пользователя БД.

**Решение:** Используйте `postgres` пользователя или service role.

## 📚 Создание миграций

### Шаблон миграции

```python
#!/usr/bin/env python3
"""
Миграция: <Название>

Дата: YYYY-MM-DD
Описание: <Подробное описание>

Совместимость: SQLite, PostgreSQL
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text
from database import engine

def migrate():
    with engine.connect() as conn:
        # Ваша миграция
        conn.execute(text("ALTER TABLE ..."))
        conn.commit()

if __name__ == "__main__":
    migrate()
```

### Checklist для новой миграции

- [ ] Описание в docstring
- [ ] Проверка существования полей/таблиц
- [ ] Обработка ошибок
- [ ] Логирование всех действий
- [ ] Тестирование на SQLite
- [ ] Тестирование на PostgreSQL
- [ ] Документация в этом README
- [ ] Обновление моделей в `models.py`

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи миграции
2. Убедитесь в корректности `DATABASE_URL`
3. Проверьте права доступа к БД
4. Создайте issue с подробным описанием

---

**Последнее обновление:** 11 октября 2025

