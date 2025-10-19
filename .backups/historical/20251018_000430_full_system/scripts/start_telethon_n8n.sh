#!/bin/bash

# Скрипт для запуска Telegram Bot с n8n (fallback)

echo "🔄 Переключение Telegram Bot на n8n fallback"

# Проверка наличия .env файла
if [ ! -f .env ]; then
    echo "❌ Файл .env не найден!"
    echo "   Скопируйте .env.example в .env и настройте переменные:"
    echo "   cp .env.example .env"
    echo "   nano .env"
    exit 1
fi

# Установка USE_LANGCHAIN_DIRECT=false
echo "🔧 Отключение LangChain Direct Integration"
export USE_LANGCHAIN_DIRECT=false

# Обновление .env файла
if grep -q "USE_LANGCHAIN_DIRECT=" .env; then
    sed -i 's/USE_LANGCHAIN_DIRECT=.*/USE_LANGCHAIN_DIRECT=false/' .env
else
    echo "USE_LANGCHAIN_DIRECT=false" >> .env
fi

echo "✅ LangChain Direct Integration отключен"

# Проверка доступности n8n
echo "🔍 Проверка n8n сервиса..."

if ! docker-compose ps n8n | grep -q "Up"; then
    echo "⚠️  n8n не запущен, запускаем..."
    docker-compose up -d n8n
    sleep 15
fi

echo "✅ n8n сервис запущен"

# Перезапуск telethon с n8n
echo "🔄 Перезапуск Telegram Bot с n8n..."
docker-compose restart telethon

# Ожидание запуска
echo "⏳ Ожидание запуска бота..."
sleep 10

# Проверка статуса
if docker-compose ps telethon | grep -q "Up"; then
    echo "✅ Telegram Bot успешно переключен на n8n!"
    echo ""
    echo "📊 Мониторинг:"
    echo "   Логи: docker-compose logs -f telethon"
    echo "   Статус: docker-compose ps telethon"
    echo ""
    echo "🔧 Управление:"
    echo "   Остановить: docker-compose stop telethon"
    echo "   Перезапустить: docker-compose restart telethon"
    echo "   Переключить на LangChain: ./start_telethon_langchain.sh"
else
    echo "❌ Ошибка запуска Telegram Bot"
    echo "   Проверьте логи: docker-compose logs telethon"
    exit 1
fi
