# 🚀 Быстрый запуск Telegram Channel Parser Bot

## 📋 Что нужно сделать за 5 минут

### 1. Получить Telegram API credentials (2 мин)
1. Перейдите на https://my.telegram.org/
2. Войдите в аккаунт
3. Создайте приложение → получите `API_ID` и `API_HASH`

### 2. Создать бота (1 мин)
1. Найдите @BotFather в Telegram
2. Отправьте `/newbot`
3. Следуйте инструкциям → получите `BOT_TOKEN`

### 3. Настроить окружение (1 мин)
```bash
# Скопируйте конфигурацию
cp .env.example .env

# Отредактируйте .env
nano .env
```

Заполните:
```env
API_ID=ваш_api_id
API_HASH=ваш_api_hash
PHONE=+79001234567
BOT_TOKEN=ваш_bot_token
```

### 4. Установить и запустить (1 мин)
```bash
# Установка зависимостей
pip install -r requirements.txt

# Первоначальная аутентификация
python auth.py

# Запуск системы
python run_system.py
```

### 5. Начать использовать
1. Найдите вашего бота в Telegram
2. Отправьте `/start`
3. Добавьте канал: `/add_channel @example_channel`

## 🎯 Готово!

Теперь у вас есть:
- ✅ Telegram бот для управления каналами
- ✅ Автоматический парсер постов
- ✅ REST API для интеграции с n8n
- ✅ База данных с постами

## 🔗 API Endpoints

- `GET /users` - список пользователей
- `GET /users/{id}/channels` - каналы пользователя
- `GET /users/{id}/posts` - посты пользователя
- `POST /parse_all_channels` - запуск парсинга

## 📊 Интеграция с n8n

Импортируйте `n8n_workflow_example.json` в n8n для автоматического анализа постов с помощью AI.

---

**Нужна помощь?** Смотрите полную документацию в `README.md` 