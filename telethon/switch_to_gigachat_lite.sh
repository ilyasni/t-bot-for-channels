#!/bin/bash
# Быстрое переключение на GigaChat Lite для решения 429 Rate Limit

set -e

echo "⚡ Переключение на GigaChat Lite для тегирования"
echo ""

# Определяем путь к корневому .env
ROOT_ENV="/home/ilyasni/n8n-server/n8n-installer/.env"
TELETHON_ENV="/home/ilyasni/n8n-server/n8n-installer/telethon/.env"

# Проверяем наличие GIGACHAT_CREDENTIALS
if ! grep -q "GIGACHAT_CREDENTIALS" "$ROOT_ENV" 2>/dev/null; then
    echo "❌ Ошибка: GIGACHAT_CREDENTIALS не найден в .env"
    echo ""
    echo "Получите credentials на https://developers.sber.ru/gigachat"
    echo "Затем добавьте в $ROOT_ENV:"
    echo "GIGACHAT_CREDENTIALS=your_credentials_here"
    exit 1
fi

# Проверяем что credentials не пустой
GIGACHAT_CREDS=$(grep "GIGACHAT_CREDENTIALS" "$ROOT_ENV" | cut -d '=' -f2)
if [ -z "$GIGACHAT_CREDS" ] || [ "$GIGACHAT_CREDS" = "your_credentials_here" ]; then
    echo "❌ Ошибка: GIGACHAT_CREDENTIALS не установлен"
    echo ""
    echo "Получите credentials на https://developers.sber.ru/gigachat"
    echo "Затем установите в $ROOT_ENV"
    exit 1
fi

echo "✅ GIGACHAT_CREDENTIALS найден"

# Обновляем или добавляем переменные в telethon/.env
if [ ! -f "$TELETHON_ENV" ]; then
    echo "📝 Создаем $TELETHON_ENV"
    touch "$TELETHON_ENV"
fi

# Обновляем TAGGING_PROVIDER
if grep -q "^TAGGING_PROVIDER=" "$TELETHON_ENV"; then
    sed -i 's/^TAGGING_PROVIDER=.*/TAGGING_PROVIDER=gigachat/' "$TELETHON_ENV"
    echo "✅ Обновлен TAGGING_PROVIDER=gigachat"
else
    echo "TAGGING_PROVIDER=gigachat" >> "$TELETHON_ENV"
    echo "✅ Добавлен TAGGING_PROVIDER=gigachat"
fi

# Обновляем GIGACHAT_MODEL
if grep -q "^GIGACHAT_MODEL=" "$TELETHON_ENV"; then
    sed -i 's/^GIGACHAT_MODEL=.*/GIGACHAT_MODEL=GigaChat-Lite/' "$TELETHON_ENV"
    echo "✅ Обновлен GIGACHAT_MODEL=GigaChat-Lite"
else
    echo "GIGACHAT_MODEL=GigaChat-Lite" >> "$TELETHON_ENV"
    echo "✅ Добавлен GIGACHAT_MODEL=GigaChat-Lite"
fi

echo ""
echo "🔄 Перезапускаем сервисы..."
cd /home/ilyasni/n8n-server/n8n-installer
docker compose -p localai restart telethon gpt2giga-proxy

echo ""
echo "⏳ Ждем запуска сервисов (5 секунд)..."
sleep 5

echo ""
echo "📊 Проверяем логи..."
docker logs telethon 2>&1 | grep "TaggingService" | tail -5

echo ""
echo "✅ Готово! Проверьте логи выше."
echo ""
echo "Ожидаемый вывод:"
echo "  ✅ TaggingService: Инициализирован с GigaChat"
echo "  💡 TaggingService: Используется модель GigaChat-Lite"
echo "  ⚡ GigaChat-Lite: быстрая модель с высокими лимитами"
echo ""
echo "📝 Для обработки постов с ошибками:"
echo "  curl -X POST 'http://localhost:8010/users/YOUR_USER_ID/posts/retry_tagging?limit=100'"

