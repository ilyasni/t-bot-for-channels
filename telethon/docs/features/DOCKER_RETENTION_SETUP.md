# Быстрая установка системы хранения постов в Docker

## Для n8n-installer проекта

Этот гайд предназначен для пользователей, использующих Docker-окружение n8n-installer.

## 📋 Предварительные требования

- Docker и Docker Compose установлены
- Запущен проект n8n-installer
- Контейнер telethon работает

## 🚀 Установка (3 шага)

### Шаг 1: Применение миграции

Запустите скрипт миграции в Docker-контейнере:

```bash
cd /home/ilyasni/n8n-server/n8n-installer/telethon
./docker-migrate-retention.sh
```

**Альтернативный способ (вручную):**
```bash
docker exec telethon python add_retention_days.py
```

### Шаг 2: Настройка переменных окружения

Отредактируйте `.env` файл в директории `telethon/`:

```bash
nano /home/ilyasni/n8n-server/n8n-installer/telethon/.env
```

Добавьте или убедитесь, что есть строки:

```env
# Система хранения постов
DEFAULT_RETENTION_DAYS=30
CLEANUP_SCHEDULE_TIME=03:00
```

### Шаг 3: Перезапуск контейнера

Перезапустите контейнер telethon для применения изменений:

```bash
cd /home/ilyasni/n8n-server/n8n-installer
docker-compose restart telethon
```

## ✅ Проверка работы

### Проверка миграции

```bash
# Проверяем, что поле retention_days добавлено
docker exec telethon python -c "
from database import SessionLocal
from models import User
db = SessionLocal()
user = db.query(User).first()
if user:
    print(f'✅ Миграция успешна! retention_days = {user.retention_days}')
else:
    print('ℹ️  Нет пользователей в БД')
db.close()
"
```

### Проверка API

```bash
# Получить настройки пользователя (замените 1 на ID вашего пользователя)
curl http://localhost:8010/users/1/retention_settings
```

### Проверка логов

```bash
# Проверяем логи сервиса
docker-compose logs telethon | grep -i "retention\|cleanup"
```

## 🔧 Использование

### Получение настроек пользователя

```bash
curl http://localhost:8010/users/USER_ID/retention_settings
```

### Изменение периода хранения

```bash
curl -X PUT http://localhost:8010/users/USER_ID/retention_settings \
  -H "Content-Type: application/json" \
  -d '{
    "retention_days": 60,
    "run_cleanup_immediately": false
  }'
```

### Запуск очистки вручную

```bash
curl -X POST http://localhost:8010/cleanup/run
```

### Просмотр логов очистки

```bash
docker-compose logs -f telethon | grep "CleanupService\|cleanup"
```

## 🎯 Интеграция с n8n

### Пример workflow для изменения тарифа

1. Создайте webhook в n8n
2. Добавьте HTTP Request ноду:

```json
{
  "method": "PUT",
  "url": "http://telethon:8010/users/{{ $json.user_id }}/retention_settings",
  "body": {
    "retention_days": "{{ $json.plan === 'premium' ? 90 : 30 }}",
    "run_cleanup_immediately": false
  }
}
```

### Пример мониторинга в n8n

Создайте Schedule Trigger (раз в день) с HTTP Request:

```json
{
  "method": "POST",
  "url": "http://telethon:8010/cleanup/run"
}
```

## 📊 Мониторинг

### Просмотр состояния контейнера

```bash
docker-compose ps telethon
```

### Просмотр использования ресурсов

```bash
docker stats telethon
```

### Просмотр логов в реальном времени

```bash
docker-compose logs -f telethon
```

## 🔄 Обновление конфигурации

### Изменение времени очистки

1. Отредактируйте `.env`:
```bash
nano /home/ilyasni/n8n-server/n8n-installer/telethon/.env
```

2. Измените `CLEANUP_SCHEDULE_TIME`:
```env
CLEANUP_SCHEDULE_TIME=04:00  # Теперь очистка в 4:00 утра
```

3. Перезапустите контейнер:
```bash
docker-compose restart telethon
```

### Изменение периода по умолчанию для новых пользователей

1. Отредактируйте `.env`:
```env
DEFAULT_RETENTION_DAYS=60  # Теперь по умолчанию 60 дней
```

2. Перезапустите контейнер:
```bash
docker-compose restart telethon
```

## 🐛 Решение проблем

### Миграция не применилась

```bash
# Проверьте логи миграции
docker exec telethon cat /var/log/migration.log

# Попробуйте запустить миграцию вручную с выводом
docker exec -it telethon python add_retention_days.py
```

### API недоступен

```bash
# Проверьте, что контейнер запущен
docker ps | grep telethon

# Проверьте логи
docker-compose logs telethon

# Перезапустите контейнер
docker-compose restart telethon
```

### Очистка не работает

```bash
# Проверьте логи планировщика
docker exec telethon python -c "
import os
print('CLEANUP_SCHEDULE_TIME:', os.getenv('CLEANUP_SCHEDULE_TIME', '03:00'))
print('DEFAULT_RETENTION_DAYS:', os.getenv('DEFAULT_RETENTION_DAYS', '30'))
"

# Запустите очистку вручную для тестирования
docker exec telethon python cleanup_service.py
```

### База данных заблокирована (SQLite)

```bash
# Если используете SQLite, убедитесь что не запущено несколько процессов
docker exec telethon ps aux | grep python

# Перезапустите контейнер
docker-compose restart telethon
```

## 📦 Резервное копирование

### Создание резервной копии базы данных

```bash
# Для SQLite
docker exec telethon cp /app/data/telethon_bot.db /app/data/telethon_bot.db.backup

# Копирование на хост
docker cp telethon:/app/data/telethon_bot.db ./telethon_bot.db.backup
```

### Восстановление из резервной копии

```bash
# Остановите контейнер
docker-compose stop telethon

# Восстановите базу
docker cp ./telethon_bot.db.backup telethon:/app/data/telethon_bot.db

# Запустите контейнер
docker-compose start telethon
```

## 🔐 Безопасность

### Ограничение доступа к API

Убедитесь, что порт 8010 не открыт извне:

```bash
# Проверьте настройки портов в docker-compose.override.yml
# Используйте reverse proxy (Caddy) для защищенного доступа
```

### Логирование

Все операции очистки логируются:

```bash
# Просмотр логов очистки за последний час
docker-compose logs --since 1h telethon | grep cleanup
```

## 📚 Дополнительные ресурсы

- **Полная документация**: `telethon/RETENTION_README.md`
- **Быстрый старт**: `telethon/QUICK_START_RETENTION.md`
- **Changelog**: `telethon/CHANGELOG_RETENTION.md`
- **Тестирование**: `telethon/test_retention_system.py`

## 🆘 Поддержка

При возникновении проблем:

1. Проверьте логи: `docker-compose logs telethon`
2. Проверьте .env файл
3. Убедитесь, что миграция применена
4. Проверьте доступность API

---

**Версия**: 1.0.0  
**Дата**: 2025-10-10  
**Статус**: ✅ Готово к использованию в Docker

