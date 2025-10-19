#!/bin/bash

echo "🔄 Применение миграции: Система хранения постов"
echo "================================================"

# Проверка, запущен ли контейнер telethon
if ! docker ps | grep -q telethon; then
    echo "❌ Контейнер telethon не запущен!"
    echo "📝 Сначала запустите контейнер:"
    echo "   cd /home/ilyasni/n8n-server/n8n-installer"
    echo "   docker-compose up -d telethon"
    exit 1
fi

echo "✅ Контейнер telethon найден"
echo ""
echo "📝 Запуск миграции в контейнере..."

# Запускаем миграцию внутри контейнера
docker exec telethon python add_retention_days.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Миграция успешно применена!"
    echo ""
    echo "📋 Следующие шаги:"
    echo "  1. Проверьте настройки в .env файле:"
    echo "     DEFAULT_RETENTION_DAYS=30"
    echo "     CLEANUP_SCHEDULE_TIME=03:00"
    echo ""
    echo "  2. Перезапустите контейнер для применения изменений:"
    echo "     docker-compose restart telethon"
    echo ""
    echo "  3. Проверьте API endpoints:"
    echo "     curl http://localhost:8010/users/1/retention_settings"
    echo ""
    echo "📖 Полная документация: telethon/RETENTION_README.md"
else
    echo ""
    echo "❌ Ошибка применения миграции"
    echo "📝 Проверьте логи:"
    echo "   docker-compose logs telethon"
    exit 1
fi

