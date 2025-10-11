# Telegram Channel Parser Bot

🤖 Система для парсинга Telegram каналов с возможностью управления через бота и интеграции с n8n.

## 🚀 Возможности

- **Telegram Bot** - управление каналами пользователей
- **Автоматический парсер** - регулярный сбор постов из каналов
- **REST API** - интеграция с n8n для анализа постов
- **База данных** - хранение пользователей, каналов и постов (SQLite/PostgreSQL/Supabase)
- **Многопользовательская система** - каждый пользователь видит только свои каналы
- **AI тегирование** - автоматическая категоризация постов
- **Retention система** - автоматическая очистка старых постов

## 📁 Структура проекта

```
telethon/
├── docs/                      # 📚 Вся документация
│   ├── quickstart/           # Быстрый старт
│   ├── features/             # Документация функций
│   ├── migrations/           # Руководства по миграциям
│   └── troubleshooting/      # Решение проблем
├── scripts/                   # 🔧 Скрипты
│   ├── setup/                # Настройка системы
│   ├── migrations/           # Миграции БД
│   └── utils/                # Утилиты
├── tests/                     # 🧪 Тесты
├── examples/                  # 📝 Примеры (n8n workflows)
├── sessions/                  # 🔐 Сессии Telegram
├── data/                      # 💾 База данных
├── logs/                      # 📋 Логи
└── [основные .py файлы]      # 🐍 Код приложения
```

## 📋 Компоненты системы

1. **Telegram Bot** (`bot.py`) - бот для управления каналами
2. **Parser Service** (`parser_service.py`) - автоматический парсинг
3. **API Server** (`main.py`) - REST API для интеграции
4. **Database** (`models.py`, `database.py`) - хранение данных
5. **Auth** (`auth.py`, `secure_auth_manager.py`) - аутентификация
6. **Tagging Service** (`tagging_service.py`) - AI тегирование постов
7. **Cleanup Service** (`cleanup_service.py`) - автоочистка старых постов

## 🛠️ Установка и настройка

> ⚠️ **Важно:** Этот сервис интегрирован в основной проект n8n-server.  
> Для запуска используйте корневой `start_services.py` из папки `/home/ilyasni/n8n-server/n8n-installer/`

### Быстрый старт

```bash
# Перейдите в корень проекта
cd /home/ilyasni/n8n-server/n8n-installer/

# Настройте .env (если еще не настроен)
cp .env.example .env
nano .env

# Добавьте переменные для Telegram сервиса:
# BOT_TOKEN - получите у @BotFather
# OPENROUTER_API_KEY - для AI тегирования (опционально)
# DEFAULT_RETENTION_DAYS - период хранения постов (по умолчанию 30)

# Запустите все сервисы
python start_services.py
```

Сервис будет доступен:
- 🌐 API: `http://localhost:8010`
- 📚 Документация API: `http://localhost:8010/docs`
- 🤖 Telegram Bot: найдите вашего бота и отправьте `/start`

### Дополнительная настройка

Для специфичных настроек Telegram сервиса создайте `telethon/.env`:

```bash
cd telethon
cp .env.example .env
nano .env
```

См. `telethon/.env.example` для доступных опций.

### 📚 Документация

- **Быстрый старт**: [`docs/quickstart/`](docs/quickstart/)
- **Функции системы**: [`docs/features/`](docs/features/)
- **Миграции**: [`docs/migrations/`](docs/migrations/)
- **Решение проблем**: [`docs/troubleshooting/`](docs/troubleshooting/)

## 🚀 Использование

### Запуск в составе основного проекта (рекомендуется)

```bash
# Из корня проекта n8n-installer
python start_services.py
```

### Локальный запуск (для разработки)

```bash
# Запуск всей системы
python run_system.py

# Или отдельные компоненты
python bot.py              # Только Telegram бот
python main.py             # Только API сервер
```

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