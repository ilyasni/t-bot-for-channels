# Telegram Channel Parser Bot

🤖 Система для парсинга Telegram каналов с возможностью управления через бота и интеграции с n8n.

## 🚀 Возможности

- **Telegram Bot** - управление каналами пользователей
- **Автоматический парсер** - регулярный сбор постов из каналов
- **REST API** - интеграция с n8n для анализа постов
- **База данных** - хранение пользователей, каналов и постов
- **Многопользовательская система** - каждый пользователь видит только свои каналы

## 📋 Компоненты системы

1. **Telegram Bot** (`bot.py`) - бот для управления каналами
2. **Parser Service** (`parser_service.py`) - автоматический парсинг
3. **API Server** (`main.py`) - REST API для интеграции
4. **Database** (`models.py`, `database.py`) - хранение данных
5. **Auth** (`auth.py`) - аутентификация в Telegram

## 🛠️ Установка и настройка

### 1. Получение Telegram API credentials

1. Перейдите на https://my.telegram.org/
2. Войдите в свой аккаунт
3. Создайте новое приложение
4. Скопируйте `API_ID` и `API_HASH`

### 2. Создание Telegram бота

1. Найдите @BotFather в Telegram
2. Отправьте команду `/newbot`
3. Следуйте инструкциям для создания бота
4. Скопируйте полученный токен

### 3. Настройка окружения

```bash
# Скопируйте файл конфигурации
cp .env.example .env

# Отредактируйте .env файл
nano .env
```

Заполните следующие переменные:
```env
# Telegram API credentials
API_ID=your_api_id_here
API_HASH=your_api_hash_here
PHONE=your_phone_number_here
AUTH_CODE=your_auth_code_here

# Bot Token (получите у @BotFather)
BOT_TOKEN=your_bot_token_here

# Database configuration
DATABASE_URL=sqlite:///./telethon_bot.db

# Parser settings
PARSER_INTERVAL_MINUTES=30
MAX_POSTS_PER_CHANNEL=50

# Server settings
HOST=0.0.0.0
PORT=8010
```

### 4. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 5. Первоначальная аутентификация

```bash
python auth.py
```

Следуйте инструкциям для ввода кода подтверждения.

## 🚀 Запуск системы

### 🐳 Запуск в Docker (рекомендуется)

```bash
# Быстрый запуск
chmod +x docker-run.sh
./docker-run.sh

# Или ручной запуск
docker-compose up -d
```

Подробная инструкция: [DOCKER_README.md](DOCKER_README.md)

### 💻 Запуск локально

#### Запуск всей системы
```bash
python run_system.py
```

Это запустит:
- Telegram бота
- API сервер
- Автоматический парсер

#### Запуск отдельных компонентов

##### Только бот
```bash
python bot.py
```

##### Только API сервер
```bash
python main.py
```

##### Только парсер
```bash
python parser_service.py
```

## 📱 Использование бота

### Команды бота

- `/start` - Начало работы с ботом
- `/add_channel @channel_name` - Добавить канал для отслеживания
- `/my_channels` - Показать ваши каналы
- `/remove_channel` - Удалить канал
- `/help` - Показать справку

### Пример использования

1. Найдите вашего бота в Telegram
2. Отправьте `/start`
3. Добавьте канал: `/add_channel @example_channel`
4. Просмотрите ваши каналы: `/my_channels`

## 🌐 REST API

### Endpoints

#### Получить всех пользователей
```
GET /users
```

#### Получить каналы пользователя
```
GET /users/{telegram_id}/channels
```

#### Получить посты пользователя
```
GET /users/{telegram_id}/posts?hours_back=24&limit=100
```

#### Парсить все каналы
```
POST /parse_all_channels
```

#### Получить посты из канала (старый endpoint)
```
GET /get_recent_posts?channel=@channel_name&hours_back=24&limit=100
```

### Примеры использования API

#### Получить посты пользователя
```bash
curl "http://localhost:8010/users/123456789/posts?hours_back=24&limit=50"
```

#### Запустить парсинг всех каналов
```bash
curl -X POST "http://localhost:8010/parse_all_channels"
```

## 🔄 Интеграция с n8n

### Webhook для получения постов

Создайте webhook в n8n:

1. **HTTP Request Node**:
   - Method: GET
   - URL: `http://your-server:8010/users/{telegram_id}/posts`
   - Parameters:
     - `hours_back`: 24
     - `limit`: 100

2. **AI Analysis Node**:
   - Используйте полученные посты для анализа
   - Пример: анализ тональности, извлечение ключевых слов

### Автоматический парсинг

Настройте cron job в n8n:

1. **Cron Node**:
   - Schedule: `0 */30 * * * *` (каждые 30 минут)

2. **HTTP Request Node**:
   - Method: POST
   - URL: `http://your-server:8010/parse_all_channels`

3. **AI Processing Node**:
   - Обработка новых постов

## 📊 Структура базы данных

### Таблица Users
- `id` - ID пользователя
- `telegram_id` - Telegram ID пользователя
- `username` - Username в Telegram
- `first_name` - Имя
- `last_name` - Фамилия
- `created_at` - Дата регистрации
- `is_active` - Активен ли пользователь

### Таблица Channels
- `id` - ID канала
- `user_id` - ID пользователя (внешний ключ)
- `channel_username` - Username канала
- `channel_id` - Telegram ID канала
- `channel_title` - Название канала
- `is_active` - Активен ли канал
- `created_at` - Дата добавления
- `last_parsed_at` - Время последнего парсинга

### Таблица Posts
- `id` - ID поста
- `user_id` - ID пользователя (внешний ключ)
- `channel_id` - ID канала (внешний ключ)
- `telegram_message_id` - ID сообщения в Telegram
- `text` - Текст поста
- `views` - Количество просмотров
- `url` - Ссылка на пост
- `posted_at` - Время публикации
- `parsed_at` - Время парсинга

## 🔧 Настройка производительности

### Интервал парсинга
Измените `PARSER_INTERVAL_MINUTES` в `.env`:
```env
PARSER_INTERVAL_MINUTES=15  # Парсинг каждые 15 минут
```

### Лимит постов
Измените `MAX_POSTS_PER_CHANNEL` в `.env`:
```env
MAX_POSTS_PER_CHANNEL=100  # Максимум 100 постов за раз
```

### База данных
Для продакшена рекомендуется использовать PostgreSQL:
```env
DATABASE_URL=postgresql://user:password@localhost/telethon_bot
```

## 🐛 Устранение неполадок

### Ошибка подключения к Telegram
1. Проверьте правильность `API_ID` и `API_HASH`
2. Убедитесь, что номер телефона указан в международном формате
3. Проверьте файл сессии в папке `sessions/`

### Ошибка бота
1. Проверьте правильность `BOT_TOKEN`
2. Убедитесь, что бот не заблокирован
3. Проверьте логи в консоли

### Ошибка базы данных
1. Проверьте права доступа к файлу базы данных
2. Для PostgreSQL проверьте подключение
3. Убедитесь, что таблицы созданы

## 📝 Логирование

Система ведет подробные логи:
- `INFO` - Информационные сообщения
- `WARNING` - Предупреждения
- `ERROR` - Ошибки

Логи выводятся в консоль и содержат эмодзи для удобства чтения.

## 🔒 Безопасность

- Каждый пользователь видит только свои каналы и посты
- API не требует аутентификации (для внутреннего использования)
- Рекомендуется настроить firewall для API сервера
- Используйте HTTPS в продакшене

## 📈 Мониторинг

### Метрики для отслеживания:
- Количество активных пользователей
- Количество каналов на пользователя
- Количество новых постов в день
- Время выполнения парсинга
- Ошибки парсинга

### Пример запроса метрик:
```bash
# Количество пользователей
curl "http://localhost:8010/users" | jq '.users | length'

# Количество каналов
curl "http://localhost:8010/users/123456789/channels" | jq '.channels | length'
```

## 🤝 Поддержка

При возникновении проблем:
1. Проверьте логи в консоли
2. Убедитесь в правильности конфигурации
3. Проверьте подключение к интернету
4. Убедитесь, что Telegram API доступен

## 📄 Лицензия

MIT License 