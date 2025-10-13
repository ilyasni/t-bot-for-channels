# 🚀 Quick Start Guide

Быстрый старт для развертывания n8n Server + Telegram Channel Parser.

---

## 📋 Перед установкой

### 1. Подготовка сервера

- **ОС:** Ubuntu 24.04 LTS, 64-bit
- **Ресурсы:**
  - Минимум (n8n + Flowise): 4GB RAM / 2 CPU / 30GB Disk
  - Рекомендуется (с Telegram Parser + RAG): 12GB RAM / 6 CPU / 80GB Disk
- **Доступ:** SSH root или sudo

### 2. Домен и DNS

1. Зарегистрируйте домен (например, `yourdomain.com`)
2. Создайте wildcard A-запись:
   ```
   *.yourdomain.com → YOUR_SERVER_IP
   ```
3. Дождитесь распространения DNS (проверка: `dig n8n.yourdomain.com`)

### 3. Telegram Bot (если нужен Parser)

1. Создайте бота: https://t.me/BotFather → `/newbot`
2. Сохраните `BOT_TOKEN`

---

## 🛠️ Установка (5-15 минут)

### Вариант 1: Полная установка (рекомендуется)

```bash
# 1. Клонируйте репозиторий
git clone https://github.com/yourusername/n8n-server
cd n8n-server/n8n-installer

# 2. Запустите установщик
sudo bash ./scripts/install.sh

# 3. Следуйте интерактивному wizard:
# - Укажите домен: yourdomain.com
# - Email для SSL сертификатов
# - OpenAI API key (опционально)
# - Импорт workflows (y/n)
# - Количество n8n workers (1-4)
# - Выберите сервисы для установки

# 4. Дождитесь завершения (10-15 минут)
```

### Вариант 2: Быстрая установка (минимальный стек)

```bash
git clone https://github.com/yourusername/n8n-server
cd n8n-server/n8n-installer
sudo bash ./scripts/install.sh

# В wizard:
# - Домен: yourdomain.com
# - Email: your@email.com
# - OpenAI: [Enter] (skip)
# - Workflows: n (skip)
# - Workers: 1
# - Сервисы: выберите только n8n, Flowise, Telegram Parser
```

---

## 🔑 После установки

### 1. Сохраните credentials

Скрипт выведет **Summary Report** с:
- URL всех сервисов
- Логины и пароли
- API ключи

**Сохраните эту информацию в безопасном месте!**

### 2. Первый вход

#### n8n
```
URL: https://n8n.yourdomain.com
Email: [ваш email из установки]
Password: [из Summary Report]
```

#### Flowise
```
URL: https://flowise.yourdomain.com
Username: [из Summary Report]
Password: [из Summary Report]
```

#### Supabase (если установлен)
```
URL: https://supabase.yourdomain.com
Username: [из Summary Report]
Password: [из Summary Report]
```

---

## 📱 Telegram Parser - Быстрый старт

### 1. Настройка (через бота)

```
1. Найдите вашего бота в Telegram
2. Отправьте: /start
3. Получите invite code у администратора
4. Отправьте: /login YOUR_INVITE_CODE
5. Нажмите кнопку "🔐 QR Авторизация"
6. Отсканируйте QR или используйте ссылку
7. Подтвердите в официальном Telegram
```

### 2. Добавьте каналы

```
/add_channel @channelname
/my_channels
```

### 3. Используйте RAG

```
/ask Расскажи о последних новостях AI
/search Ищу информацию про GPT-4
/recommend
/digest
```

---

## 🧪 Проверка работоспособности

### Все сервисы запущены?

```bash
docker ps --filter "name=localai" --format "table {{.Names}}\t{{.Status}}"
```

Должно быть несколько контейнеров в состоянии `Up`.

### Проверка логов

```bash
# Все логи
docker compose -p localai logs -f

# Конкретный сервис
docker logs -f n8n
docker logs -f telethon
docker logs -f rag-service
```

### Healthchecks

```bash
# n8n
curl -I https://n8n.yourdomain.com

# Telegram Parser API
curl https://telegram-api.yourdomain.com/health

# RAG Service
curl http://localhost:8020/rag/health
```

---

## 🔧 Управление

### Остановить все

```bash
cd /path/to/n8n-installer
docker compose -p localai down
```

### Запустить все

```bash
cd /path/to/n8n-installer
python3 start_services.py
```

### Перезапустить сервис

```bash
docker compose -p localai restart n8n
docker compose -p localai restart telethon
```

---

## 📚 Что дальше?

### Изучите n8n
1. Импортируйте workflows из `n8n/backup/workflows/`
2. Изучите [n8n documentation](https://docs.n8n.io/)
3. Попробуйте [AI templates](https://n8n.io/workflows/?categories=AI)

### Настройте Telegram Parser
1. Прочитайте [Telegram Parser QuickStart](/telethon/docs/quickstart/QUICK_START.md)
2. Настройте [RAG систему](/telethon/docs/quickstart/RAG_QUICKSTART.md)
3. Изучите [Admin Panel](/telethon/docs/quickstart/ADMIN_PANEL_QUICKSTART.md)

### Интеграция
1. Создайте n8n workflow для Telegram постов
2. Настройте webhooks (в `.env`)
3. Используйте RAG API в workflows

---

## 🐛 Проблемы?

### Временное предупреждение "Dangerous Site"

Подождите несколько часов, пока Caddy получит Let's Encrypt сертификаты.

### Сервис не запускается

```bash
# Проверьте логи
docker logs [service-name]

# Пересоздайте контейнер
docker compose -p localai down
docker compose -p localai up -d
```

### QR Login не работает

```bash
# Проверьте Redis
docker logs redis

# Проверьте telethon
docker logs telethon | grep "QRAuthManager"
```

**Подробнее:** [Troubleshooting Guide](/telethon/docs/troubleshooting/)

---

## 📞 Поддержка

- **Документация:** [README.md](README.md)
- **Telegram Parser:** [/telethon/docs/README.md](/telethon/docs/README.md)
- **Upstream:** [n8n-installer issues](https://github.com/kossakovsky/n8n-installer/issues)
- **Issues:** Создайте issue в этом репозитории

---

**Версия:** 3.1  
**Дата обновления:** Октябрь 2025

