#!/bin/bash

echo "🐳 Запуск Telegram Channel Parser Bot в Docker"
echo "================================================"

# Проверка наличия .env файла
if [ ! -f .env ]; then
    echo "❌ Файл .env не найден!"
    echo "📝 Создайте .env файл на основе .env.example:"
    echo "   cp .env.example .env"
    echo "   nano .env"
    exit 1
fi

# Создание необходимых директорий
echo "📁 Создание директорий..."
mkdir -p sessions data logs

# Проверка переменных окружения
echo "🔍 Проверка конфигурации..."
source .env

required_vars=("API_ID" "API_HASH" "PHONE" "BOT_TOKEN")
missing_vars=()

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    echo "❌ Отсутствуют обязательные переменные: ${missing_vars[*]}"
    echo "📝 Заполните их в файле .env"
    exit 1
fi

echo "✅ Конфигурация корректна"

# Сборка и запуск контейнера
echo "🔨 Сборка Docker образа..."
docker-compose build

if [ $? -ne 0 ]; then
    echo "❌ Ошибка сборки образа"
    exit 1
fi

echo "🚀 Запуск контейнера..."
docker-compose up -d

if [ $? -ne 0 ]; then
    echo "❌ Ошибка запуска контейнера"
    exit 1
fi

echo "✅ Контейнер запущен!"
echo ""
echo "📋 Информация:"
echo "  🌐 API доступен по адресу: http://localhost:8010"
echo "  📊 Документация API: http://localhost:8010/docs"
echo "  📝 Логи: docker-compose logs -f"
echo "  🛑 Остановка: docker-compose down"
echo ""
echo "🤖 Найдите вашего бота в Telegram и отправьте /start"
echo ""
echo "📊 Для мониторинга используйте:"
echo "  docker-compose logs -f telethon-bot" 