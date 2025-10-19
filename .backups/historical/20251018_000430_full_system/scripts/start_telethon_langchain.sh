#!/bin/bash

# Скрипт для запуска Telegram Bot с LangChain Direct Integration

echo "🚀 Запуск Telegram Bot с LangChain Direct Integration"

# Проверка наличия .env файла
if [ ! -f .env ]; then
    echo "❌ Файл .env не найден!"
    echo "   Скопируйте .env.example в .env и настройте переменные:"
    echo "   cp .env.example .env"
    echo "   nano .env"
    exit 1
fi

# Проверка обязательных переменных
source .env

if [ -z "$BOT_TOKEN" ]; then
    echo "❌ BOT_TOKEN не установлен в .env файле"
    exit 1
fi

if [ -z "$MASTER_API_ID" ]; then
    echo "❌ MASTER_API_ID не установлен в .env файле"
    exit 1
fi

if [ -z "$MASTER_API_HASH" ]; then
    echo "❌ MASTER_API_HASH не установлен в .env файле"
    exit 1
fi

if [ -z "$ENCRYPTION_KEY" ]; then
    echo "❌ ENCRYPTION_KEY не установлен в .env файле"
    exit 1
fi

# Установка USE_LANGCHAIN_DIRECT=true
echo "🔧 Включение LangChain Direct Integration"
export USE_LANGCHAIN_DIRECT=true

# Обновление .env файла
if grep -q "USE_LANGCHAIN_DIRECT=" .env; then
    sed -i 's/USE_LANGCHAIN_DIRECT=.*/USE_LANGCHAIN_DIRECT=true/' .env
else
    echo "USE_LANGCHAIN_DIRECT=true" >> .env
fi

echo "✅ LangChain Direct Integration включен"

# Проверка доступности зависимых сервисов
echo "🔍 Проверка зависимых сервисов..."

# Проверка PostgreSQL
if ! docker compose ps postgres | grep -q "Up"; then
    echo "⚠️  PostgreSQL не запущен, запускаем..."
    docker compose up -d postgres
    sleep 10
fi

# Проверка Redis
if ! docker compose ps redis | grep -q "Up"; then
    echo "⚠️  Redis не запущен, запускаем..."
    docker compose up -d redis
    sleep 5
fi

# Проверка gpt2giga-proxy
if ! docker compose ps gpt2giga-proxy | grep -q "Up"; then
    echo "⚠️  gpt2giga-proxy не запущен, запускаем..."
    docker compose up -d gpt2giga-proxy
    sleep 10
fi

# Проверка n8n (для fallback)
if ! docker compose ps n8n | grep -q "Up"; then
    echo "⚠️  n8n не запущен, запускаем для fallback..."
    docker compose up -d n8n
    sleep 15
fi

echo "✅ Все зависимые сервисы запущены"

# Сборка и запуск telethon с LangChain
echo "🔨 Сборка и запуск Telegram Bot с LangChain..."
docker compose up -d --build telethon

# Ожидание запуска
echo "⏳ Ожидание запуска бота..."
sleep 10

# Проверка статуса
if docker compose ps telethon | grep -q "Up"; then
    echo "✅ Telegram Bot успешно запущен с LangChain Direct Integration!"
    echo ""
    echo "📊 Мониторинг:"
    echo "   Логи: docker compose logs -f telethon"
    echo "   Статус: docker compose ps telethon"
    echo ""
    echo "🔧 Управление:"
    echo "   Остановить: docker compose stop telethon"
    echo "   Перезапустить: docker compose restart telethon"
    echo "   Переключить на n8n: sed -i 's/USE_LANGCHAIN_DIRECT=true/USE_LANGCHAIN_DIRECT=false/' .env && docker compose restart telethon"
    echo ""
    echo "📈 Observability:"
    echo "   Langfuse: https://langfuse.produman.studio"
    echo "   Prometheus: http://localhost:9090"
    echo "   Grafana: http://localhost:3000"
else
    echo "❌ Ошибка запуска Telegram Bot"
    echo "   Проверьте логи: docker compose logs telethon"
    exit 1
fi
