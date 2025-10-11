# Обновление: Система ограничения хранения постов для Telethon

## 📋 Обзор обновления

Добавлена новая функциональность для управления периодом хранения постов в Telegram Channel Parser:

- ✅ Настраиваемый период хранения для каждого пользователя (1-365 дней)
- ✅ Автоматическая очистка устаревших постов по расписанию
- ✅ Расчет периода от последнего поста каждого канала
- ✅ API endpoints для управления настройками
- ✅ Готовность для монетизации (платные тарифы)

## 🚀 Быстрая установка

### Для пользователей Docker (рекомендуется)

```bash
# 1. Перейдите в директорию telethon
cd /home/ilyasni/n8n-server/n8n-installer/telethon

# 2. Примените миграцию
./docker-migrate-retention.sh

# 3. Перезапустите контейнеры
cd ..
docker-compose restart telethon telethon-bot
```

### Для локального запуска (без Docker)

```bash
# 1. Перейдите в директорию telethon
cd /home/ilyasni/n8n-server/n8n-installer/telethon

# 2. Примените миграцию
python add_retention_days.py

# 3. Настройте .env (если не настроено)
echo "DEFAULT_RETENTION_DAYS=30" >> .env
echo "CLEANUP_SCHEDULE_TIME=03:00" >> .env

# 4. Перезапустите сервис
# (зависит от вашего способа запуска)
```

## 📝 Что изменилось

### Новые файлы

```
telethon/
├── add_retention_days.py          # Скрипт миграции БД
├── cleanup_service.py             # Сервис очистки постов
├── test_retention_system.py       # Тестирование системы
├── docker-migrate-retention.sh    # Миграция в Docker
├── RETENTION_README.md            # Полная документация
├── QUICK_START_RETENTION.md       # Быстрый старт
├── CHANGELOG_RETENTION.md         # Детальный changelog
├── IMPLEMENTATION_SUMMARY.md      # Резюме реализации
└── DOCKER_RETENTION_SETUP.md      # Docker-специфичная инструкция
```

### Измененные файлы

1. **telethon/models.py**
   - Добавлено поле `retention_days` в модель User
   - Исправлены таймзоны (datetime.utcnow → datetime.now(timezone.utc))

2. **telethon/parser_service.py**
   - Добавлено расписание ежедневной очистки
   - Интеграция с cleanup_service

3. **telethon/main.py**
   - Новые API endpoints:
     - `GET /users/{user_id}/retention_settings`
     - `PUT /users/{user_id}/retention_settings`
     - `POST /cleanup/run`

4. **telethon/.env.example**
   - Добавлены параметры:
     - `DEFAULT_RETENTION_DAYS=30`
     - `CLEANUP_SCHEDULE_TIME=03:00`

5. **docker-compose.override.yml**
   - Добавлены переменные окружения для retention системы

6. **telethon/docker-run.sh**
   - Добавлена информация о системе хранения при запуске

## 🔧 Конфигурация

### Переменные окружения (.env)

```env
# Период хранения постов по умолчанию для новых пользователей
DEFAULT_RETENTION_DAYS=30

# Время ежедневной автоматической очистки (формат HH:MM)
CLEANUP_SCHEDULE_TIME=03:00
```

### Docker Compose

Переменные автоматически подхватываются из `.env` файла через:
- `env_file: - ./telethon/.env`
- Прямой монтаж `.env` файла в контейнер

## 📊 API Endpoints

### Получение настроек пользователя

```bash
GET http://localhost:8010/users/{user_id}/retention_settings
```

**Ответ:**
```json
{
  "user_id": 1,
  "telegram_id": 123456789,
  "retention_days": 30,
  "posts_stats": {
    "total_posts": 1542,
    "oldest_post_date": "2024-09-10T12:00:00+00:00",
    "newest_post_date": "2025-10-10T18:30:00+00:00",
    "channels_count": 5,
    "active_channels_count": 4
  }
}
```

### Изменение настроек

```bash
PUT http://localhost:8010/users/{user_id}/retention_settings
Content-Type: application/json

{
  "retention_days": 60,
  "run_cleanup_immediately": false
}
```

### Ручной запуск очистки

```bash
POST http://localhost:8010/cleanup/run
```

## 💼 Использование для платных тарифов

Система готова для монетизации:

```python
# Пример тарифных планов
PLANS = {
    "free": 7,       # Бесплатный - 7 дней
    "basic": 30,     # Базовый - 30 дней
    "premium": 90,   # Премиум - 90 дней
    "vip": 365       # VIP - год
}
```

### Интеграция с n8n

**Workflow для управления подпиской:**

1. **Webhook триггер** - получает данные о смене тарифа
2. **HTTP Request** - обновляет retention_days:

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

## 🔍 Проверка работы

### 1. Проверка миграции

```bash
# Docker
docker exec telethon python -c "from database import SessionLocal; from models import User; db = SessionLocal(); u = db.query(User).first(); print(f'retention_days: {u.retention_days if u else \"No users\"}'); db.close()"

# Локально
python -c "from database import SessionLocal; from models import User; db = SessionLocal(); u = db.query(User).first(); print(f'retention_days: {u.retention_days if u else \"No users\"}'); db.close()"
```

### 2. Тестирование системы

```bash
cd telethon
python test_retention_system.py
```

### 3. Проверка API

```bash
# Получить список пользователей
curl http://localhost:8010/users

# Получить настройки первого пользователя
curl http://localhost:8010/users/1/retention_settings
```

## 🐛 Известные проблемы и решения

### Проблема: Таймзона отстает на 3 часа

**Решение:** Уже исправлено в этом обновлении. Все `datetime.utcnow` заменены на `datetime.now(timezone.utc)`.

### Проблема: Миграция не применилась

**Решение:**
```bash
# Проверьте, что БД доступна
docker exec telethon ls -la /app/data/

# Запустите миграцию с выводом
docker exec -it telethon python add_retention_days.py
```

### Проблема: Очистка не запускается

**Решение:**
```bash
# Проверьте переменные окружения
docker exec telethon env | grep -E "RETENTION|CLEANUP"

# Запустите очистку вручную
docker exec telethon python cleanup_service.py
```

## 🔄 Откат изменений

Если нужно откатить изменения:

### PostgreSQL

```bash
docker exec telethon python add_retention_days.py --rollback
```

### SQLite

Используйте резервную копию:
```bash
docker cp telethon_bot.db.backup telethon:/app/data/telethon_bot.db
docker-compose restart telethon
```

## 📚 Документация

Полная документация доступна в следующих файлах:

- **`telethon/RETENTION_README.md`** - Полная документация
- **`telethon/QUICK_START_RETENTION.md`** - Быстрый старт
- **`telethon/DOCKER_RETENTION_SETUP.md`** - Docker-специфичная инструкция
- **`telethon/CHANGELOG_RETENTION.md`** - Детальный список изменений
- **`telethon/IMPLEMENTATION_SUMMARY.md`** - Резюме реализации

## 🎯 Следующие шаги

1. ✅ Примените миграцию
2. ✅ Проверьте работу через API
3. ✅ Настройте .env под ваши нужды
4. ✅ Интегрируйте с n8n workflows (опционально)
5. ✅ Настройте мониторинг (опционально)

## ⚙️ Интеграция с существующими скриптами

### start_services.py

Скрипт автоматически учитывает новые переменные окружения из `.env`.

### scripts/

Скрипты установки не требуют изменений, так как изменения касаются только telethon-модуля.

## 🔐 Безопасность

- Все операции удаления транзакционные
- Защита от случайного удаления (минимум 1 день)
- Детальное логирование всех операций
- Валидация входных данных (1-365 дней)

## 📞 Поддержка

При возникновении проблем:

1. Проверьте логи: `docker-compose logs telethon`
2. Прочитайте документацию в `telethon/RETENTION_README.md`
3. Запустите тесты: `python telethon/test_retention_system.py`
4. Проверьте конфигурацию `.env`

---

**Версия обновления**: 1.0.0  
**Дата**: 2025-10-10  
**Совместимость**: Обратная совместимость сохранена  
**Статус**: ✅ Готово к использованию

