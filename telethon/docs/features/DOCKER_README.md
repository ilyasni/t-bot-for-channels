# 🐳 Запуск в Docker

## 📋 Быстрый запуск

### 1. Подготовка
```bash
# Клонируйте репозиторий
git clone <your-repo>
cd telethon

# Создайте .env файл
cp .env.example .env
nano .env
```

### 2. Настройка .env
Заполните обязательные переменные:
```env
API_ID=ваш_api_id
API_HASH=ваш_api_hash
PHONE=+79001234567
BOT_TOKEN=ваш_bot_token
```

### 3. Запуск
```bash
# Сделайте скрипт исполняемым
chmod +x docker-run.sh

# Запустите систему
./docker-run.sh
```

## 🔧 Ручной запуск

### Сборка и запуск
```bash
# Создание директорий
mkdir -p sessions data logs

# Сборка образа
docker-compose build

# Запуск
docker-compose up -d
```

### Просмотр логов
```bash
# Все логи
docker-compose logs -f

# Только логи бота
docker-compose logs -f telethon-bot
```

### Остановка
```bash
docker-compose down
```

## 📁 Структура директорий

```
telethon/
├── sessions/          # Сессии Telegram (монтируется в контейнер)
├── data/             # База данных (монтируется в контейнер)
├── logs/             # Логи (монтируется в контейнер)
├── .env              # Конфигурация (монтируется в контейнер)
├── docker-compose.yml
├── Dockerfile.telethon
└── docker-run.sh
```

## 🌐 Доступ к API

После запуска API будет доступен по адресу:
- **API**: http://localhost:8010
- **Документация**: http://localhost:8010/docs
- **Альтернативная документация**: http://localhost:8010/redoc

## 🔍 Отладка

### Проверка статуса контейнера
```bash
docker-compose ps
```

### Вход в контейнер
```bash
docker-compose exec telethon-bot bash
```

### Проверка логов
```bash
# Последние 100 строк
docker-compose logs --tail=100 telethon-bot

# Логи в реальном времени
docker-compose logs -f telethon-bot
```

### Проверка файлов
```bash
# Проверка сессий
ls -la sessions/

# Проверка базы данных
ls -la data/

# Проверка логов
ls -la logs/
```

## 🐛 Устранение проблем

### Ошибка сборки
```bash
# Очистка кэша Docker
docker system prune -a

# Пересборка
docker-compose build --no-cache
```

### Ошибка подключения к Telegram
1. Проверьте правильность `API_ID` и `API_HASH`
2. Убедитесь, что номер телефона в международном формате
3. Проверьте файл сессии в `sessions/`

### Ошибка бота
1. Проверьте правильность `BOT_TOKEN`
2. Убедитесь, что бот не заблокирован
3. Проверьте логи: `docker-compose logs telethon-bot`

### Проблемы с правами доступа
```bash
# Исправление прав на директории
sudo chown -R $USER:$USER sessions/ data/ logs/
chmod -R 755 sessions/ data/ logs/
```

## 🔄 Обновление

### Обновление кода
```bash
# Остановка
docker-compose down

# Получение обновлений
git pull

# Пересборка и запуск
docker-compose build --no-cache
docker-compose up -d
```

### Обновление зависимостей
```bash
# Остановка
docker-compose down

# Пересборка с новыми зависимостями
docker-compose build --no-cache

# Запуск
docker-compose up -d
```

## 📊 Мониторинг

### Проверка здоровья системы
```bash
# Статус контейнеров
docker-compose ps

# Использование ресурсов
docker stats

# Проверка API
curl http://localhost:8010/users
```

### Резервное копирование
```bash
# Создание бэкапа
tar -czf backup-$(date +%Y%m%d).tar.gz sessions/ data/ logs/

# Восстановление
tar -xzf backup-20240101.tar.gz
```

## 🔒 Безопасность

### Переменные окружения
- Никогда не коммитьте `.env` файл в Git
- Используйте секреты в продакшене
- Регулярно обновляйте токены

### Сеть
- API доступен только на localhost по умолчанию
- Для продакшена настройте reverse proxy
- Используйте HTTPS в продакшене

## 🚀 Продакшен

### С PostgreSQL
Раскомментируйте PostgreSQL в `docker-compose.yml`:
```yaml
postgres:
  image: postgres:15
  environment:
    POSTGRES_DB: telethon_bot
    POSTGRES_USER: telethon_user
    POSTGRES_PASSWORD: telethon_password
```

И обновите `DATABASE_URL` в `.env`:
```env
DATABASE_URL=postgresql://telethon_user:telethon_password@postgres:5432/telethon_bot
```

### С reverse proxy
Добавьте nginx или traefik для HTTPS и балансировки нагрузки.

### Мониторинг
Используйте Prometheus + Grafana для мониторинга метрик.

---

**Нужна помощь?** Смотрите основную документацию в `README.md` 