# Скрипты Telegram Channel Parser

Все скрипты проекта организованы по категориям:

## 📁 Структура скриптов

### `/setup/` - Скрипты настройки
- `setup.py` - Основной скрипт настройки проекта
- `setup_tagging.sh` - Настройка системы тегирования

**Использование:**
```bash
# Первоначальная настройка
cd /home/ilyasni/n8n-server/n8n-installer/telethon
python scripts/setup/setup.py

# Настройка тегирования
bash scripts/setup/setup_tagging.sh
```

### `/migrations/` - Скрипты миграций
Python скрипты:
- `migrate_services.py` - Миграция сервисов
- `migrate_to_many_to_many.py` - Миграция на многопользовательскую систему
- `migrate_to_many_to_many_old.py` - Старая версия миграции
- `migrate_to_many_to_many_universal.py` - Универсальная миграция
- `migrate_database.py` - Миграция базы данных
- `add_retention_days.py` - Добавление поля retention_days
- `add_tags_column.py` - Добавление колонки tags

Bash скрипты:
- `utils_migration.sh` - Утилиты для миграций
- `migrate_many_to_many.sh` - Автоматическая миграция
- `apply_many_to_many.sh` - Применение миграции
- `docker-migrate-retention.sh` - Миграция retention в Docker

**Использование:**
```bash
# Python миграция
python scripts/migrations/migrate_to_many_to_many.py

# Bash миграция
bash scripts/migrations/migrate_many_to_many.sh
```

### `/utils/` - Утилиты
- `generate_encryption_key.py` - Генерация ключа шифрования
- `clear_sessions.py` - Очистка сессий Telegram
- `init_database.py` - Инициализация базы данных
- `dev.sh` - **Helper скрипт для разработки** 🛠️

#### Использование dev.sh

**Быстрые команды для разработки:**

```bash
cd /home/ilyasni/n8n-server/n8n-installer/telethon

# Локальная разработка (рекомендуется)
./scripts/utils/dev.sh setup    # Первоначальная настройка
./scripts/utils/dev.sh local    # Запуск локально (без Docker)
./scripts/utils/dev.sh api      # Только FastAPI сервер
./scripts/utils/dev.sh bot      # Только Telegram бот
./scripts/utils/dev.sh test     # Запуск тестов

# Docker разработка
./scripts/utils/dev.sh rebuild  # Пересборка контейнеров
./scripts/utils/dev.sh restart  # Рестарт без пересборки
./scripts/utils/dev.sh stop     # Остановка контейнеров
./scripts/utils/dev.sh logs     # Просмотр логов (live)
./scripts/utils/dev.sh shell    # Bash внутри контейнера

# Справка
./scripts/utils/dev.sh help     # Показать все команды
```

**Использование:**
```bash
# Генерация ключа шифрования
python scripts/utils/generate_encryption_key.py

# Очистка сессий
python scripts/utils/clear_sessions.py

# Инициализация БД
python scripts/utils/init_database.py
```

## ⚠️ Важно

Все скрипты должны запускаться из корневой папки проекта telethon для правильной работы путей и импортов.

