#!/bin/bash
# Скрипт установки системы тегирования для Docker окружения

set -e

# Определяем директорию скрипта и проекта
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

COMPOSE_CMD="docker compose -p localai -f docker-compose.override.yml"
TELETHON_CONTAINER="telethon"

echo "🚀 Установка системы автоматического тегирования"
echo "================================================="
echo ""

# Проверка наличия .env файла в директории telethon
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo "❌ Файл telethon/.env не найден!"
    echo "📋 Скопируйте .env.example и настройте:"
    echo "   cd $SCRIPT_DIR"
    echo "   cp .env.example .env"
    echo "   # Добавьте OPENROUTER_API_KEY в .env"
    exit 1
fi

# Проверка наличия OPENROUTER_API_KEY
if ! grep -q "OPENROUTER_API_KEY=.*[^_].*" "$SCRIPT_DIR/.env"; then
    echo "⚠️  OPENROUTER_API_KEY не настроен в telethon/.env"
    echo "📋 Получите API ключ на https://openrouter.ai/"
    echo "   и добавьте его в $SCRIPT_DIR/.env"
    read -p "Продолжить без API ключа? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "📦 Шаг 1: Пересборка и запуск Docker образа..."
cd "$PROJECT_ROOT"
$COMPOSE_CMD up --build -d telethon
echo "✅ Образ собран и запущен"
echo ""

echo "⏳ Ожидание запуска контейнера (10 секунд)..."
sleep 10
echo ""

echo "🗄️  Шаг 2: Миграция базы данных..."
docker exec telethon python add_tags_column.py

if [ $? -eq 0 ]; then
    echo "✅ Миграция выполнена успешно"
else
    echo "❌ Ошибка миграции"
    echo "📋 Попробуйте выполнить вручную:"
    echo "   docker exec telethon python add_tags_column.py"
    exit 1
fi
echo ""

echo "🔄 Шаг 3: Перезапуск для применения изменений..."
docker restart telethon
docker restart telethon-bot 2>/dev/null || echo "ℹ️  telethon-bot не требует перезапуска"
echo "✅ Сервисы перезапущены"
echo ""

echo "⏳ Ожидание запуска сервиса (5 секунд)..."
sleep 5
echo ""

echo "🔍 Шаг 4: Проверка работы..."
if curl -s http://localhost:8010/posts/tags/stats > /dev/null; then
    echo "✅ API отвечает"
    echo ""
    echo "📊 Статистика по тегам:"
    curl -s http://localhost:8010/posts/tags/stats | python3 -m json.tool 2>/dev/null || echo "Установите jq для красивого вывода: apt install jq"
else
    echo "⚠️  API не отвечает, проверьте логи:"
    echo "   docker logs telethon"
fi
echo ""

echo "================================================="
echo "🎉 Установка завершена!"
echo ""
echo "📋 Полезные команды:"
echo ""
echo "Просмотр логов:"
echo "  docker logs telethon -f | grep TaggingService"
echo ""
echo "Статистика по тегам:"
echo "  curl http://localhost:8010/posts/tags/stats | jq"
echo ""
echo "Генерация тегов вручную:"
echo "  curl -X POST http://localhost:8010/posts/{post_id}/generate_tags"
echo ""
echo "Документация:"
echo "  cat telethon/TAGGING_README.md"
echo ""