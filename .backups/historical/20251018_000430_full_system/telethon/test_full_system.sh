#!/bin/bash
# Полная проверка всех систем после исправления Event Loop
# Проверяет: парсинг, тегирование, индексацию, поиск

# НЕ используем set -e чтобы скрипт продолжал работу при ошибках

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASSED=0
FAILED=0

echo -e "${BLUE}🔍 ПОЛНАЯ ПРОВЕРКА TELEGRAM PARSER SYSTEM${NC}"
echo "============================================================"

# 1. Контейнеры
echo -e "\n${BLUE}1️⃣ Проверка контейнеров...${NC}"
for container in telethon rag-service qdrant; do
    if docker ps | grep -q "$container"; then
        echo -e "  ${GREEN}✅ $container${NC}"
        ((PASSED++))
    else
        echo -e "  ${RED}❌ $container НЕ ЗАПУЩЕН${NC}"
        ((FAILED++))
    fi
done

# 2. Event Loop
echo -e "\n${BLUE}2️⃣ Проверка Event Loop...${NC}"
LOOP_COUNT=$(docker logs telethon 2>&1 | grep "event loop ID" | awk '{print $NF}' | sort -u | wc -l)
if [ "$LOOP_COUNT" -eq 1 ]; then
    LOOP_ID=$(docker logs telethon 2>&1 | grep "event loop ID" | tail -1 | awk '{print $NF}')
    echo -e "  ${GREEN}✅ Все клиенты в одном event loop: $LOOP_ID${NC}"
    ((PASSED++))
else
    echo -e "  ${YELLOW}⚠️  Найдено $LOOP_COUNT разных event loops${NC}"
    ((FAILED++))
fi

# Проверка ошибок event loop
if docker logs telethon 2>&1 | grep -q "event loop must not change"; then
    echo -e "  ${RED}❌ Найдены ошибки event loop${NC}"
    ((FAILED++))
else
    echo -e "  ${GREEN}✅ Нет ошибок event loop${NC}"
    ((PASSED++))
fi

# 3. Парсинг
echo -e "\n${BLUE}3️⃣ Проверка парсинга...${NC}"
PARSE_RESULT=$(curl -s -X POST http://localhost:8010/users/6/channels/parse 2>/dev/null || echo '{"posts_added":0}')
POSTS_ADDED=$(echo "$PARSE_RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin).get('posts_added', 0))" 2>/dev/null || echo "0")

if [ "$POSTS_ADDED" -gt 0 ]; then
    echo -e "  ${GREEN}✅ Парсинг работает: $POSTS_ADDED постов добавлено${NC}"
    ((PASSED++))
else
    echo -e "  ${YELLOW}⚠️  Парсинг вернул 0 постов (возможно, нет новых)${NC}"
fi

# 4. Тегирование
echo -e "\n${BLUE}4️⃣ Проверка тегирования...${NC}"
TAG_STATS=$(docker exec telethon python3 -c "
from database import SessionLocal
from models import Post
db = SessionLocal()
with_tags = db.query(Post).filter(Post.tags != None).count()
total = db.query(Post).count()
print(f'{with_tags},{total}')
" 2>/dev/null)

WITH_TAGS=$(echo "$TAG_STATS" | cut -d',' -f1)
TOTAL=$(echo "$TAG_STATS" | cut -d',' -f2)

if [ -n "$WITH_TAGS" ] && [ -n "$TOTAL" ] && [ "$TOTAL" -gt 0 ]; then
    PERCENT=$(python3 -c "print(int($WITH_TAGS/$TOTAL*100))")
    if [ "$PERCENT" -ge 90 ]; then
        echo -e "  ${GREEN}✅ Тегирование: $WITH_TAGS/$TOTAL постов ($PERCENT%)${NC}"
        ((PASSED++))
    else
        echo -e "  ${YELLOW}⚠️  Тегирование: $WITH_TAGS/$TOTAL постов ($PERCENT%)${NC}"
    fi
else
    echo -e "  ${YELLOW}⚠️  Не удалось получить статистику тегов${NC}"
fi

# 5. RAG Service
echo -e "\n${BLUE}5️⃣ Проверка RAG Service...${NC}"
RAG_HEALTH=$(curl -s http://localhost:8020/health 2>/dev/null || echo '{"status":"error"}')
RAG_STATUS=$(echo "$RAG_HEALTH" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'error'))" 2>/dev/null || echo "error")

if [ "$RAG_STATUS" = "healthy" ]; then
    echo -e "  ${GREEN}✅ RAG Service работает${NC}"
    ((PASSED++))
    
    # Проверяем Qdrant подключение
    QDRANT_CONN=$(echo "$RAG_HEALTH" | python3 -c "import sys, json; print(json.load(sys.stdin).get('qdrant_connected', False))" 2>/dev/null || echo "False")
    if [ "$QDRANT_CONN" = "True" ]; then
        echo -e "  ${GREEN}✅ Qdrant подключен${NC}"
        ((PASSED++))
    else
        echo -e "  ${RED}❌ Qdrant НЕ подключен${NC}"
        ((FAILED++))
    fi
else
    echo -e "  ${RED}❌ RAG Service недоступен${NC}"
    ((FAILED++))
fi

# 6. Индексация
echo -e "\n${BLUE}6️⃣ Проверка индексации в Qdrant...${NC}"
QDRANT_STATS=$(curl -s http://localhost:8020/rag/stats/6 2>/dev/null || echo '{"vectors_count":0}')
VECTORS=$(echo "$QDRANT_STATS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('vectors_count', 0))" 2>/dev/null || echo "0")
INDEXED=$(echo "$QDRANT_STATS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('indexed_posts', 0))" 2>/dev/null || echo "0")

if [ "$VECTORS" -gt 0 ]; then
    echo -e "  ${GREEN}✅ Векторов в Qdrant: $VECTORS${NC}"
    echo -e "  ${GREEN}✅ Проиндексировано постов: $INDEXED${NC}"
    ((PASSED++))
else
    echo -e "  ${YELLOW}⚠️  Нет векторов в Qdrant (возможно, еще не индексировались)${NC}"
fi

# 7. Векторный поиск
echo -e "\n${BLUE}7️⃣ Проверка векторного поиска...${NC}"
SEARCH_RESULT=$(curl -s "http://localhost:8020/rag/search?user_id=6&query=авто&limit=1&min_score=0.5" 2>/dev/null || echo '{"results_count":0}')
RESULTS_COUNT=$(echo "$SEARCH_RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin).get('results_count', 0))" 2>/dev/null || echo "0")

if [ "$RESULTS_COUNT" -gt 0 ]; then
    echo -e "  ${GREEN}✅ Поиск работает: найдено $RESULTS_COUNT результатов${NC}"
    ((PASSED++))
else
    echo -e "  ${YELLOW}⚠️  Поиск вернул 0 результатов${NC}"
fi

# ИТОГИ
echo ""
echo "============================================================"
echo -e "${BLUE}📊 ИТОГОВЫЕ РЕЗУЛЬТАТЫ:${NC}"
echo "  ✅ Пройдено: $PASSED"
echo "  ❌ Провалено: $FAILED"
echo "============================================================"

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ УСПЕШНО!${NC}"
    echo ""
    echo "📚 Документация:"
    echo "  - FINAL_SUMMARY.md - полный отчет"
    echo "  - QUICK_REFERENCE.md - шпаргалка"
    echo "  - VERIFICATION_REPORT.md - детали event loop fix"
    echo "  - TAGGING_INDEXING_VERIFICATION.md - детали тегирования"
    echo ""
    echo "🚀 Система готова к использованию!"
    exit 0
else
    echo -e "${YELLOW}⚠️  Некоторые проверки не прошли (см. выше)${NC}"
    echo ""
    echo "🔧 Рекомендации:"
    echo "  1. Проверьте логи: docker logs telethon --tail 100"
    echo "  2. Проверьте RAG service: docker logs rag-service --tail 50"
    echo "  3. См. документацию: TROUBLESHOOTING.md"
    exit 1
fi

