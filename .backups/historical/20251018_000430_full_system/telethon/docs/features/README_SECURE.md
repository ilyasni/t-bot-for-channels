# 🔐 Безопасная система Telegram парсера

## 🚨 КРИТИЧЕСКОЕ ОБНОВЛЕНИЕ БЕЗОПАСНОСТИ

Система была полностью переработана для устранения серьезных уязвимостей безопасности.

## ⚠️ Что было исправлено

- ❌ **Ввод кодов в Telegram чат** → ✅ **HTTPS веб-форма**
- ❌ **Открытое хранение API данных** → ✅ **Шифрование Fernet**
- ❌ **Отсутствие защиты от брутфорса** → ✅ **Rate limiting + блокировки**
- ❌ **Небезопасные сессии** → ✅ **Временные сессии с TTL**

## 🚀 Быстрый старт

### 1. Генерация ключа шифрования
```bash
# Вне контейнера (на хосте)
python generate_encryption_key.py
```
Скопируйте сгенерированный ключ в `.env` файл:
```bash
ENCRYPTION_KEY=your_generated_key_here
```

> **💡 Примечание:** `pip install -r requirements.txt` запускать НЕ НУЖНО - зависимости устанавливаются автоматически при сборке Docker образа!

### 2. Настройка .env файла
```bash
# Обязательные параметры
BOT_TOKEN=your_bot_token_from_botfather
ENCRYPTION_KEY=your_generated_key_here
AUTH_BASE_URL=https://telegram-auth.produman.studio

# Для продакшена (SSL)
SSL_CERT_PATH=/path/to/certificate.crt
SSL_KEY_PATH=/path/to/private.key

# База данных (уже настроена в docker-compose)
DATABASE_URL=postgresql://postgres:your_password@postgres:5432/postgres?sslmode=require
```

### 3. Миграция базы данных (ВАЖНО!)
```bash
# ВАЖНО: Перед первым запуском обновленной системы выполните миграцию БД
docker compose -p localai -f docker-compose.override.yml exec telethon python migrate_database.py
```

### 4. Запуск через Docker Compose
```bash
# Запуск всей системы n8n-installer (включая telethon)
docker compose -p localai -f docker-compose.override.yml up --build -d

# Проверка статуса контейнеров
docker compose -p localai -f docker-compose.override.yml ps

# Просмотр логов telethon
docker compose -p localai -f docker-compose.override.yml logs telethon

# Просмотр логов веб-сервера аутентификации
docker compose -p localai -f docker-compose.override.yml logs telethon-auth
```

### 5. Доступ к сервисам
```bash
# Telegram бот - работает автоматически в контейнере
# Веб-сервер аутентификации - доступен по адресу:
# https://telegram-auth.produman.studio

# Проверка состояния веб-сервера
curl https://telegram-auth.produman.studio/health
```

### 6. Управление контейнерами
```bash
# Остановка всех сервисов
docker compose -p localai -f docker-compose.override.yml down

# Перезапуск только telethon
docker compose -p localai -f docker-compose.override.yml restart telethon

# Перезапуск с пересборкой
docker compose -p localai -f docker-compose.override.yml up --build -d

# Просмотр логов в реальном времени
docker compose -p localai -f docker-compose.override.yml logs -f telethon
```

## 🔐 Процесс аутентификации

### Новый безопасный процесс:
1. **В боте:** `/auth` - получить ссылку на веб-форму
2. **В браузере:** Открыть HTTPS ссылку, ввести API данные
3. **В Telegram:** Получить код, ввести в веб-форме
4. **Готово:** Аутентификация завершена

### Старый небезопасный процесс (УДАЛЕН):
❌ ~~Ввод API данных в чат~~  
❌ ~~Ввод кодов в чат~~  
❌ ~~Хранение данных в открытом виде~~

## 🛡️ Безопасность

### Шифрование данных:
- 🔐 **API Hash** зашифрован в БД
- 🔐 **Номера телефонов** зашифрованы в БД
- 🔐 **Ключ шифрования** в ENV переменных

### Защита от атак:
- 🚫 **Rate limiting:** 3 попытки в 5 минут
- 🚫 **Блокировка:** 1 час при превышении лимита
- 🚫 **Временные сессии:** TTL 10 минут
- 🚫 **Автоматическая очистка** истекших сессий

### HTTPS защита:
- 🔒 **SSL сертификаты** для продакшена
- 🔒 **HTTPS шифрование** всех данных
- 🔒 **Защищенная передача** кодов

## 📋 Команды бота

### ✅ Безопасные команды:
- `/auth` - Безопасная аутентификация через веб-форму
- `/auth_status` - Проверка статуса аутентификации
- `/logout` - Выход из системы
- `/clear_auth` - Очистка данных аутентификации
- `/add_channel` - Добавить канал для отслеживания
- `/my_channels` - Показать ваши каналы
- `/help` - Справка

### ❌ Отключенные команды:
- `/auth_code` - **ОТКЛЮЧЕНА** по соображениям безопасности

## 🔧 Настройка SSL

### Для разработки:
В Docker контейнере веб-сервер автоматически запускается в режиме разработки (без SSL).

### Для продакшена:
1. Получите SSL сертификат
2. Скопируйте сертификаты в папку с проектом
3. Укажите пути в .env (относительно корня проекта):
```bash
SSL_CERT_PATH=./certs/certificate.crt
SSL_KEY_PATH=./certs/private.key
```
4. Перезапустите контейнеры:
```bash
docker compose -p localai -f docker-compose.override.yml up --build -d
```

### Структура для SSL сертификатов:
```
n8n-installer/
├── certs/
│   ├── certificate.crt
│   └── private.key
├── docker-compose.override.yml
└── telethon/
    └── .env
```

## 📊 Мониторинг

### Проверка состояния:
```bash
# Проверка веб-сервера аутентификации
curl https://telegram-auth.produman.studio/health

# Проверка статуса контейнеров
docker compose -p localai -f docker-compose.override.yml ps

# Проверка логов telethon
docker compose -p localai -f docker-compose.override.yml logs telethon --tail=50

# Мониторинг логов в реальном времени
docker compose -p localai -f docker-compose.override.yml logs -f telethon
```

### Логи безопасности:
- Все попытки аутентификации логируются в контейнере
- Блокировки и rate limiting отслеживаются
- Ошибки шифрования записываются в stdout контейнера

### Мониторинг ресурсов:
```bash
# Использование ресурсов контейнером telethon
docker stats $(docker compose -p localai -f docker-compose.override.yml ps -q telethon)

# Проверка использования диска
docker compose -p localai -f docker-compose.override.yml exec telethon df -h
```

## 🗃️ Структура файлов

```
telethon/
├── 🔐 Безопасные компоненты:
│   ├── secure_auth_manager.py      # Безопасный менеджер аутентификации
│   ├── crypto_utils.py             # Шифрование данных
│   ├── auth_web_server.py          # HTTPS веб-сервер
│   └── start_auth_server.py        # Запуск веб-сервера
├── 🤖 Обновленный бот:
│   ├── bot.py                      # Обновленный бот (безопасный)
│   ├── bot_standalone.py           # Запуск бота
│   └── auth.py                     # Обновленный модуль аутентификации
├── 🗄️ Модели данных:
│   ├── models.py                   # Обновленные модели с шифрованием
│   └── database.py                 # База данных
├── 🚀 Запуск системы:
│   ├── start_secure_system.py      # Запуск всей системы
│   └── generate_encryption_key.py  # Генерация ключа шифрования
├── 📚 Документация:
│   ├── SECURITY_UPDATE.md          # Подробное описание обновлений
│   └── README_SECURE.md            # Этот файл
└── ⚙️ Конфигурация:
    ├── requirements.txt            # Обновленные зависимости
    └── .env.example               # Пример конфигурации
```

## 🔄 Миграция данных

### ⚠️ ВАЖНО: Миграция базы данных
Перед первым запуском обновленной системы **ОБЯЗАТЕЛЬНО** выполните миграцию:

```bash
# Запуск миграции в Docker контейнере
docker compose -p localai -f docker-compose.override.yml exec telethon python migrate_database.py
```

### Что делает миграция:
1. ✅ Добавляет новые колонки в таблицу `users`
2. ✅ Шифрует существующие API hash и номера телефонов
3. ✅ Проверяет успешность миграции
4. ✅ Сохраняет все существующие данные

### Проверка миграции:
```python
from database import SessionLocal
from models import User
from crypto_utils import crypto_manager

db = SessionLocal()
users = db.query(User).filter(User.api_hash.isnot(None)).all()

for user in users:
    if user.api_hash:
        print(f"User {user.telegram_id}: API hash encrypted: {isinstance(user.api_hash, bytes)}")
        print(f"Masked phone: {user.get_masked_phone_number()}")
        print(f"Masked API hash: {user.get_masked_api_hash()}")

db.close()
```

## ❓ FAQ

### Q: Почему отключена команда /auth_code?
**A:** Ввод кодов в Telegram чат небезопасен. Коды могут быть перехвачены или сохранены в логах.

### Q: Как работает новая система?
**A:** Бот создает временную HTTPS ссылку на защищенную форму, где пользователь безопасно вводит данные.

### Q: Что делать со старыми данными?
**A:** Система автоматически зашифрует существующие данные при первом запуске.

### Q: Можно ли использовать HTTP?
**A:** Только для разработки. В продакшене обязательно HTTPS.

### Q: Как получить SSL сертификат?
**A:** Используйте Let's Encrypt, Cloudflare, или другой провайдер SSL.

### Q: Что если потеряю ключ шифрования?
**A:** Данные будут недоступны. Обязательно сохраните ключ в безопасном месте.

### Q: Как обновить код в Docker контейнере?
**A:** Используйте команду:
```bash
docker compose -p localai -f docker-compose.override.yml up --build -d
```

### Q: Как войти в контейнер telethon для отладки?
**A:** 
```bash
docker compose -p localai -f docker-compose.override.yml exec telethon bash
```

### Q: Как проверить переменные окружения в контейнере?
**A:**
```bash
docker compose -p localai -f docker-compose.override.yml exec telethon env | grep -E "(BOT_TOKEN|ENCRYPTION_KEY|DATABASE_URL)"
```

### Q: Как перезапустить только telethon без других сервисов?
**A:**
```bash
docker compose -p localai -f docker-compose.override.yml restart telethon
```

### Q: Нужно ли запускать pip install в контейнере?
**A:** НЕТ! В Docker зависимости устанавливаются автоматически при сборке образа. Просто используйте:
```bash
docker compose -p localai -f docker-compose.override.yml up --build -d
```

### Q: Как обновить зависимости в контейнере?
**A:** Обновите requirements.txt и пересоберите образ:
```bash
docker compose -p localai -f docker-compose.override.yml up --build -d
```

### Q: Получаю ошибку "column users.auth_session_id does not exist"
**A:** Выполните миграцию базы данных:
```bash
docker compose -p localai -f docker-compose.override.yml exec telethon python migrate_database.py
```

### Q: Что делать если миграция не удалась?
**A:** 
1. Проверьте логи миграции
2. Убедитесь что контейнер telethon запущен
3. Проверьте подключение к базе данных
4. Запустите миграцию повторно

## 🆘 Поддержка

### При возникновении проблем:
1. **Проверьте логи** на наличие ошибок
2. **Убедитесь** в правильности настроек .env
3. **Проверьте SSL** сертификаты (для продакшена)
4. **Обратитесь** к администратору

### Полезные команды:
```bash
# Генерация ключа шифрования (вне контейнера)
python generate_encryption_key.py

# Проверка состояния веб-сервера
curl https://telegram-auth.produman.studio/health

# Управление Docker контейнерами
docker compose -p localai -f docker-compose.override.yml ps
docker compose -p localai -f docker-compose.override.yml logs -f telethon
docker compose -p localai -f docker-compose.override.yml restart telethon

# Вход в контейнер telethon для отладки
docker compose -p localai -f docker-compose.override.yml exec telethon bash

# Просмотр переменных окружения в контейнере
docker compose -p localai -f docker-compose.override.yml exec telethon env | grep -E "(BOT_TOKEN|ENCRYPTION_KEY|DATABASE_URL)"

# Перезапуск с пересборкой
docker compose -p localai -f docker-compose.override.yml up --build -d
```

## 🎯 Преимущества новой системы

### ✅ Безопасность:
- Шифрование всех чувствительных данных
- HTTPS защищенная передача
- Rate limiting и защита от брутфорса
- Временные сессии с автоматической очисткой

### ✅ Удобство:
- Красивый веб-интерфейс
- Автоматическая миграция данных
- Мониторинг и логирование
- Graceful shutdown

### ✅ Надежность:
- Автоматический перезапуск процессов
- Проверка состояния системы
- Обработка ошибок
- Backup и восстановление

---

**⚠️ ВАЖНО:** Эта система устраняет критические уязвимости безопасности. Обязательно обновитесь до новой версии!

**🔐 Безопасность превыше всего!**
