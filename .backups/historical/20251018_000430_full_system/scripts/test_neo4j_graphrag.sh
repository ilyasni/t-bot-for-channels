#!/bin/bash
# 🧪 Neo4j + RAG Hybrid Integration - Test Script
# Автоматическая проверка всех компонентов

set -e  # Exit on error

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  🧪 Neo4j + RAG Hybrid Integration Test Suite       ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════╝${NC}\n"

# Проверить что admin API key установлен
if [ -f .env ]; then
    export $(grep -v '^#' .env | grep ADMIN_API_KEY | xargs)
fi

if [ -z "$ADMIN_API_KEY" ]; then
    echo -e "${RED}❌ ADMIN_API_KEY not set in .env${NC}"
    echo -e "${YELLOW}   Generate: openssl rand -hex 32${NC}"
    exit 1
fi

# ========================================
# Test 1: Neo4j Integration
# ========================================
echo -e "${YELLOW}1️⃣  Testing Neo4j Integration...${NC}"

HEALTH=$(curl -s http://localhost:8010/graph/health 2>/dev/null || echo '{"neo4j_enabled":false}')
NEO4J_ENABLED=$(echo "$HEALTH" | grep -oP '"neo4j_enabled":\s*\K(true|false)' || echo "false")
NEO4J_CONNECTED=$(echo "$HEALTH" | grep -oP '"neo4j_connected":\s*\K(true|false)' || echo "false")

echo "   $HEALTH"

if [ "$NEO4J_ENABLED" = "true" ] && [ "$NEO4J_CONNECTED" = "true" ]; then
    echo -e "${GREEN}   ✅ Neo4j integration OK${NC}"
else
    echo -e "${RED}   ❌ Neo4j not connected${NC}"
    echo -e "${YELLOW}   → Check: NEO4J_ENABLED, NEO4J_PASSWORD in .env${NC}"
fi

# ========================================
# Test 2: Cleanup Scheduler
# ========================================
echo -e "\n${YELLOW}2️⃣  Testing Cleanup Scheduler...${NC}"

STATUS=$(curl -s -X GET http://localhost:8010/admin/cleanup/status \
    -H "api-key: $ADMIN_API_KEY" 2>/dev/null || echo '{"scheduler_running":false}')

echo "   $STATUS"

SCHEDULER_RUNNING=$(echo "$STATUS" | grep -oP '"scheduler_running":\s*\K(true|false)' || echo "false")

if [ "$SCHEDULER_RUNNING" = "true" ]; then
    echo -e "${GREEN}   ✅ Cleanup scheduler running${NC}"
else
    echo -e "${YELLOW}   ⚠️  Cleanup scheduler not running${NC}"
    echo -e "${YELLOW}   → Check: CLEANUP_ENABLED in .env${NC}"
fi

# ========================================
# Test 3: Dry Run Cleanup
# ========================================
echo -e "\n${YELLOW}3️⃣  Testing Dry Run Cleanup...${NC}"

CLEANUP=$(curl -s -X POST "http://localhost:8010/admin/cleanup?dry_run=true" \
    -H "api-key: $ADMIN_API_KEY" 2>/dev/null || echo '{"status":"error"}')

echo "   $CLEANUP" | head -10

CLEANUP_STATUS=$(echo "$CLEANUP" | grep -oP '"status":\s*"\K[^"]+' || echo "error")

if [ "$CLEANUP_STATUS" = "success" ]; then
    echo -e "${GREEN}   ✅ Dry run cleanup successful${NC}"
    
    # Extract counts
    POSTGRES=$(echo "$CLEANUP" | grep -oP '"postgres":\s*\K\d+' || echo "0")
    NEO4J=$(echo "$CLEANUP" | grep -oP '"neo4j":\s*\K\d+' || echo "0")
    QDRANT=$(echo "$CLEANUP" | grep -oP '"qdrant":\s*\K\d+' || echo "0")
    
    echo -e "${BLUE}   Будет удалено:${NC}"
    echo -e "   - PostgreSQL: ${POSTGRES} posts"
    echo -e "   - Neo4j: ${NEO4J} nodes"
    echo -e "   - Qdrant: ${QDRANT} vectors"
else
    echo -e "${RED}   ❌ Cleanup failed${NC}"
fi

# ========================================
# Test 4: Prometheus Metrics
# ========================================
echo -e "\n${YELLOW}4️⃣  Testing Prometheus Metrics...${NC}"

METRICS=$(curl -s http://localhost:8010/metrics 2>/dev/null | grep -c "^graph_" || echo "0")

if [ "$METRICS" -gt 0 ]; then
    echo -e "${GREEN}   ✅ Prometheus metrics available (${METRICS} graph metrics)${NC}"
    
    # Show sample metrics
    echo -e "${BLUE}   Sample metrics:${NC}"
    curl -s http://localhost:8010/metrics | grep "^graph_" | head -5 | sed 's/^/   /'
else
    echo -e "${YELLOW}   ⚠️  No graph metrics found yet${NC}"
    echo -e "${YELLOW}   → Metrics appear after first requests${NC}"
fi

# ========================================
# Test 5: Redis Cache
# ========================================
echo -e "\n${YELLOW}5️⃣  Testing Redis Cache...${NC}"

# Check Redis container
if docker ps | grep -q redis; then
    echo -e "${GREEN}   ✅ Redis container running${NC}"
    
    # Check cache keys
    CACHE_KEYS=$(docker exec redis redis-cli KEYS "graph:*" 2>/dev/null | wc -l || echo "0")
    
    if [ "$CACHE_KEYS" -gt 0 ]; then
        echo -e "${GREEN}   ✅ Cache keys found: ${CACHE_KEYS}${NC}"
        docker exec redis redis-cli KEYS "graph:*" | head -5 | sed 's/^/      /'
    else
        echo -e "${YELLOW}   ⚠️  No cache keys yet (normal after fresh deploy)${NC}"
    fi
else
    echo -e "${RED}   ❌ Redis container not running${NC}"
fi

# ========================================
# Test 6: Service Logs
# ========================================
echo -e "\n${YELLOW}6️⃣  Checking Service Logs...${NC}"

echo -e "${BLUE}   Recent initialization logs:${NC}"
docker logs telethon --tail 100 2>&1 | \
    grep -E "(EnhancedSearch|GraphCache|DataRetention|CleanupScheduler)" | \
    tail -10 | sed 's/^/   /'

# ========================================
# Summary
# ========================================
echo -e "\n${BLUE}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  📊 Test Summary                                      ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════╝${NC}\n"

TESTS_PASSED=0
TESTS_TOTAL=6

# Count passed tests
[ "$NEO4J_ENABLED" = "true" ] && [ "$NEO4J_CONNECTED" = "true" ] && ((TESTS_PASSED++))
[ "$SCHEDULER_RUNNING" = "true" ] && ((TESTS_PASSED++))
[ "$CLEANUP_STATUS" = "success" ] && ((TESTS_PASSED++))
[ "$METRICS" -gt 0 ] && ((TESTS_PASSED++))
docker ps | grep -q redis && ((TESTS_PASSED++))
[ -f telethon/rag_service/enhanced_search.py ] && ((TESTS_PASSED++))

echo -e "${BLUE}Tests passed: ${TESTS_PASSED}/${TESTS_TOTAL}${NC}"

if [ "$TESTS_PASSED" -eq "$TESTS_TOTAL" ]; then
    echo -e "${GREEN}✅ All tests passed! Integration ready for use.${NC}"
elif [ "$TESTS_PASSED" -ge 4 ]; then
    echo -e "${YELLOW}⚠️  Partial success. Check warnings above.${NC}"
else
    echo -e "${RED}❌ Multiple tests failed. Check errors above.${NC}"
    exit 1
fi

# ========================================
# Next Steps
# ========================================
echo -e "\n${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Next Steps:${NC}\n"

if [ "$NEO4J_ENABLED" = "true" ] && [ "$NEO4J_CONNECTED" = "true" ]; then
    echo -e "1. ${GREEN}✅ Neo4j ready${NC} - Parse some channels to populate graph"
    echo -e "   Run: ./check_neo4j_posts.sh"
else
    echo -e "1. ${RED}❌ Fix Neo4j${NC} - Check NEO4J_QUICK_DEPLOY.md"
fi

if [ "$SCHEDULER_RUNNING" = "true" ]; then
    echo -e "2. ${GREEN}✅ Cleanup scheduler active${NC} - Will run daily at 3:00 AM"
else
    echo -e "2. ${YELLOW}Set CLEANUP_ENABLED=true${NC} and rebuild"
fi

echo -e "3. ${BLUE}Enable A/B testing:${NC}"
echo -e "   nano .env"
echo -e "   USE_HYBRID_SEARCH=true"
echo -e "   HYBRID_SEARCH_PERCENTAGE=10"
echo -e "   docker compose up -d --build telethon"

echo -e "\n4. ${BLUE}Monitor metrics:${NC}"
echo -e "   curl http://localhost:8010/metrics | grep graph_"

echo -e "\n${BLUE}═══════════════════════════════════════════════════════${NC}\n"

