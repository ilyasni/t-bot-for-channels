#!/bin/bash
# Скрипт для тестирования исправления Event Loop
# Автоматическая проверка что парсер работает корректно

set -e

echo "🧪 Тестирование исправления Event Loop..."
echo "================================================"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Счетчики
PASSED=0
FAILED=0

# Функция для проверки
check() {
    local test_name="$1"
    local command="$2"
    local expected="$3"
    
    echo -n "⏳ $test_name... "
    
    if eval "$command" | grep -q "$expected"; then
        echo -e "${GREEN}✅ PASSED${NC}"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}❌ FAILED${NC}"
        echo "   Ожидалось: $expected"
        echo "   Команда: $command"
        ((FAILED++))
        return 1
    fi
}

# Проверка 1: Контейнер запущен
echo ""
echo "1️⃣ Проверка контейнера..."
if docker ps | grep -q "telethon"; then
    echo -e "${GREEN}✅ Контейнер telethon запущен${NC}"
    ((PASSED++))
else
    echo -e "${RED}❌ Контейнер telethon НЕ запущен${NC}"
    echo "   Запустите: docker-compose up -d telethon"
    ((FAILED++))
    exit 1
fi

# Проверка 2: Нет ошибок event loop в последних логах
echo ""
echo "2️⃣ Проверка ошибок event loop..."
if docker logs telethon --tail 100 2>&1 | grep -q "event loop must not change"; then
    echo -e "${RED}❌ Найдены ошибки event loop в логах${NC}"
    ((FAILED++))
else
    echo -e "${GREEN}✅ Нет ошибок event loop${NC}"
    ((PASSED++))
fi

# Проверка 3: ParserService инициализирован
echo ""
echo "3️⃣ Проверка инициализации ParserService..."
check "ParserService инициализирован" \
    "docker logs telethon --tail 200" \
    "ParserService инициализирован"

# Проверка 4: Проверка исправлений в коде
echo ""
echo "4️⃣ Проверка применения исправлений..."

# Проверяем что в parser_service.py есть новый код
check "Исправление run_parsing()" \
    "docker exec telethon cat parser_service.py" \
    "КРИТИЧНО: НЕ используем asyncio.run()"

check "Исправление run_system.py" \
    "docker exec telethon cat run_system.py" \
    "asyncio.run() вызывается ТОЛЬКО ОДИН РАЗ"

# Проверка 5: API доступно
echo ""
echo "5️⃣ Проверка API..."
if curl -s http://localhost:8010/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ API доступно${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠️  API недоступно (возможно, еще не запустилось)${NC}"
fi

# Проверка 6: Есть аутентифицированные пользователи
echo ""
echo "6️⃣ Проверка пользователей..."
USER_COUNT=$(docker exec telethon python3 -c "
from database import SessionLocal
from models import User
db = SessionLocal()
print(db.query(User).filter(User.is_authenticated==True).count())
" 2>/dev/null || echo "0")

if [ "$USER_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✅ Найдено $USER_COUNT аутентифицированных пользователей${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠️  Нет аутентифицированных пользователей${NC}"
    echo "   Пользователям нужно авторизоваться через бота: /login"
fi

# Проверка 7: Есть активные каналы
echo ""
echo "7️⃣ Проверка каналов..."
CHANNEL_COUNT=$(docker exec telethon python3 -c "
from database import SessionLocal
from models import Channel
db = SessionLocal()
print(db.query(Channel).filter(Channel.is_active==True).count())
" 2>/dev/null || echo "0")

if [ "$CHANNEL_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✅ Найдено $CHANNEL_COUNT активных каналов${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠️  Нет активных каналов${NC}"
    echo "   Добавьте каналы через бота: /add_channel"
fi

# Итоги
echo ""
echo "================================================"
echo "📊 Результаты тестирования:"
echo "   ✅ Пройдено: $PASSED"
echo "   ❌ Провалено: $FAILED"
echo "================================================"

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 Все проверки пройдены!${NC}"
    echo ""
    echo "📝 Следующие шаги:"
    echo "   1. Дождитесь автоматического парсинга (30 минут)"
    echo "   2. Или запустите вручную: curl -X POST http://localhost:8010/parse/user/{USER_ID}"
    echo "   3. Проверьте логи: docker logs telethon -f | grep 'добавлено'"
    echo ""
    echo "📚 Документация:"
    echo "   - TESTING_EVENT_LOOP_FIX.md - полное руководство"
    echo "   - docs/EVENT_LOOP_FIX.md - детальное объяснение"
    exit 0
else
    echo -e "${RED}⚠️  Некоторые проверки провалены${NC}"
    echo ""
    echo "🔧 Рекомендации:"
    echo "   1. Проверьте логи: docker logs telethon --tail 100"
    echo "   2. Пересоберите образ: docker-compose build telethon"
    echo "   3. Перезапустите: docker-compose restart telethon"
    echo ""
    echo "📚 Документация:"
    echo "   - TESTING_EVENT_LOOP_FIX.md - руководство по устранению проблем"
    exit 1
fi

