#!/bin/bash
# Ручное удаление пользователя из БД для тестирования
# Использование: ./delete_user_manual.sh USER_ID или TELEGRAM_ID

set -e

USER_ID=$1

if [ -z "$USER_ID" ]; then
    echo "❌ Использование: $0 USER_ID"
    echo "Пример: $0 17"
    echo "или: $0 139883458"
    exit 1
fi

echo "🔍 Ищем пользователя $USER_ID..."

# Находим telegram_id
TELEGRAM_ID=$(docker exec supabase-db psql -U postgres -d postgres -t -c \
    "SELECT telegram_id FROM users WHERE id = $USER_ID OR telegram_id = $USER_ID LIMIT 1;" | tr -d ' ')

if [ -z "$TELEGRAM_ID" ]; then
    echo "❌ Пользователь $USER_ID не найден в БД"
    exit 1
fi

echo "✅ Найден: telegram_id = $TELEGRAM_ID"

# Удаляем session файлы
echo "🗑️ Удаление session файлов..."
rm -f "/home/ilyasni/n8n-server/n8n-installer/telethon/sessions/user_${TELEGRAM_ID}.session"
rm -f "/home/ilyasni/n8n-server/n8n-installer/telethon/sessions/user_${TELEGRAM_ID}.session-journal"

echo "✅ Session файлы удалены"

# Удаляем пользователя из БД
echo "🗑️ Удаление из БД..."
docker exec supabase-db psql -U postgres -d postgres -c \
    "DELETE FROM users WHERE telegram_id = $TELEGRAM_ID;"

echo "✅ Пользователь $TELEGRAM_ID удален из БД"

# Очищаем Redis (если есть)
echo "🗑️ Очистка Redis..."
docker exec redis redis-cli KEYS "qr_session:*" | while read key; do
    if [ ! -z "$key" ]; then
        SESSION_DATA=$(docker exec redis redis-cli GET "$key" 2>/dev/null || echo "")
        if echo "$SESSION_DATA" | grep -q "\"telegram_id\": $TELEGRAM_ID"; then
            docker exec redis redis-cli DEL "$key" >/dev/null
            echo "  • Удалена QR сессия: $key"
        fi
    fi
done

echo ""
echo "🎉 Удаление завершено!"
echo ""
echo "Пользователь $TELEGRAM_ID может теперь:"
echo "  • Попробовать /login INVITE_CODE заново"
echo "  • Будет создан как новый пользователь"
echo ""

