#!/bin/bash
# 🔍 Neo4j Integration Health Check Script
# Автоматическая проверка состояния Neo4j Knowledge Graph

set -e  # Exit on error

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Загрузить пароль из .env
if [ -f .env ]; then
    export $(grep -v '^#' .env | grep NEO4J_PASSWORD | xargs)
else
    echo -e "${RED}❌ .env file not found!${NC}"
    exit 1
fi

if [ -z "$NEO4J_PASSWORD" ]; then
    echo -e "${RED}❌ NEO4J_PASSWORD not set in .env${NC}"
    exit 1
fi

echo -e "${BLUE}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  🔍 Neo4j Knowledge Graph Health Check     ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════╝${NC}\n"

# 1. Проверить что Neo4j контейнер запущен
echo -e "${YELLOW}1️⃣  Checking Neo4j container...${NC}"
if docker ps | grep -q neo4j; then
    echo -e "${GREEN}   ✅ Neo4j container is running${NC}"
else
    echo -e "${RED}   ❌ Neo4j container is NOT running!${NC}"
    echo -e "${YELLOW}   → Run: docker compose up -d neo4j${NC}"
    exit 1
fi

# 2. Health check через API
echo -e "\n${YELLOW}2️⃣  API Health Status:${NC}"
HEALTH_RESPONSE=$(curl -s http://localhost:8010/graph/health 2>/dev/null || echo '{"error": "API not reachable"}')
echo "   $HEALTH_RESPONSE"

# Парсинг JSON без jq
NEO4J_ENABLED=$(echo "$HEALTH_RESPONSE" | grep -oP '"neo4j_enabled":\s*\K(true|false)' || echo "false")
NEO4J_CONNECTED=$(echo "$HEALTH_RESPONSE" | grep -oP '"neo4j_connected":\s*\K(true|false)' || echo "false")

if [ "$NEO4J_ENABLED" = "true" ] && [ "$NEO4J_CONNECTED" = "true" ]; then
    echo -e "${GREEN}   ✅ Neo4j integration is active and connected${NC}"
else
    echo -e "${RED}   ❌ Neo4j not properly configured${NC}"
    if [ "$NEO4J_ENABLED" != "true" ]; then
        echo -e "${YELLOW}   → Set NEO4J_ENABLED=true in .env${NC}"
    fi
    if [ "$NEO4J_CONNECTED" != "true" ]; then
        echo -e "${YELLOW}   → Check NEO4J_PASSWORD and Neo4j logs${NC}"
    fi
fi

# 3. Подсчет узлов в графе
echo -e "\n${YELLOW}3️⃣  Graph Statistics:${NC}"

# Posts count
POST_COUNT=$(docker exec neo4j cypher-shell -u neo4j -p "$NEO4J_PASSWORD" \
    "MATCH (p:Post) RETURN count(p) AS count" 2>/dev/null | grep -oP '\d+' | tail -1 || echo "0")
echo -e "   📝 Posts: ${GREEN}${POST_COUNT}${NC}"

# Tags count
TAG_COUNT=$(docker exec neo4j cypher-shell -u neo4j -p "$NEO4J_PASSWORD" \
    "MATCH (t:Tag) RETURN count(t) AS count" 2>/dev/null | grep -oP '\d+' | tail -1 || echo "0")
echo -e "   🏷️  Tags: ${GREEN}${TAG_COUNT}${NC}"

# Channels count
CHANNEL_COUNT=$(docker exec neo4j cypher-shell -u neo4j -p "$NEO4J_PASSWORD" \
    "MATCH (c:Channel) RETURN count(c) AS count" 2>/dev/null | grep -oP '\d+' | tail -1 || echo "0")
echo -e "   📢 Channels: ${GREEN}${CHANNEL_COUNT}${NC}"

# Users count
USER_COUNT=$(docker exec neo4j cypher-shell -u neo4j -p "$NEO4J_PASSWORD" \
    "MATCH (u:User) RETURN count(u) AS count" 2>/dev/null | grep -oP '\d+' | tail -1 || echo "0")
echo -e "   👤 Users: ${GREEN}${USER_COUNT}${NC}"

# 4. Relationships count
echo -e "\n${YELLOW}4️⃣  Relationships:${NC}"
HAS_TAG_COUNT=$(docker exec neo4j cypher-shell -u neo4j -p "$NEO4J_PASSWORD" \
    "MATCH ()-[r:HAS_TAG]->() RETURN count(r) AS count" 2>/dev/null | grep -oP '\d+' | tail -1 || echo "0")
echo -e "   🔗 HAS_TAG: ${GREEN}${HAS_TAG_COUNT}${NC}"

FROM_CHANNEL_COUNT=$(docker exec neo4j cypher-shell -u neo4j -p "$NEO4J_PASSWORD" \
    "MATCH ()-[r:FROM_CHANNEL]->() RETURN count(r) AS count" 2>/dev/null | grep -oP '\d+' | tail -1 || echo "0")
echo -e "   🔗 FROM_CHANNEL: ${GREEN}${FROM_CHANNEL_COUNT}${NC}"

RELATED_TO_COUNT=$(docker exec neo4j cypher-shell -u neo4j -p "$NEO4J_PASSWORD" \
    "MATCH ()-[r:RELATED_TO]->() RETURN count(r) AS count" 2>/dev/null | grep -oP '\d+' | tail -1 || echo "0")
echo -e "   🔗 RELATED_TO: ${GREEN}${RELATED_TO_COUNT}${NC}"

# 5. Последние 5 постов
echo -e "\n${YELLOW}5️⃣  Latest 5 Posts:${NC}"
docker exec neo4j cypher-shell -u neo4j -p "$NEO4J_PASSWORD" \
    "MATCH (p:Post) RETURN p.id AS id, substring(p.title, 0, 50) AS title ORDER BY p.id DESC LIMIT 5" 2>/dev/null | tail -n +2 || echo "   No posts found"

# 6. Top 5 tags
echo -e "\n${YELLOW}6️⃣  Top 5 Tags:${NC}"
docker exec neo4j cypher-shell -u neo4j -p "$NEO4J_PASSWORD" \
    "MATCH (t:Tag) RETURN t.name AS tag, t.usage_count AS count ORDER BY t.usage_count DESC LIMIT 5" 2>/dev/null | tail -n +2 || echo "   No tags found"

# 7. Проверить логи telethon
echo -e "\n${YELLOW}7️⃣  Recent Telethon Logs (Neo4j related):${NC}"
NEO4J_LOGS=$(docker logs telethon --tail 50 2>&1 | grep -i neo4j || echo "   No Neo4j logs found")
if [ "$NEO4J_LOGS" = "   No Neo4j logs found" ]; then
    echo -e "${YELLOW}   ⚠️  No Neo4j-related logs in last 50 lines${NC}"
else
    echo "$NEO4J_LOGS" | tail -10
fi

# 8. Constraints check
echo -e "\n${YELLOW}8️⃣  Neo4j Constraints:${NC}"
CONSTRAINTS=$(docker exec neo4j cypher-shell -u neo4j -p "$NEO4J_PASSWORD" \
    "SHOW CONSTRAINTS" 2>/dev/null | grep -c "UNIQUE" || echo "0")
echo -e "   🔒 Unique constraints: ${GREEN}${CONSTRAINTS}${NC} (expected: 4)"

if [ "$CONSTRAINTS" -lt 4 ]; then
    echo -e "${RED}   ❌ Missing constraints! Expected 4, found ${CONSTRAINTS}${NC}"
else
    echo -e "${GREEN}   ✅ All constraints present${NC}"
fi

# Summary
echo -e "\n${BLUE}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  📊 Summary                                   ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════╝${NC}\n"

if [ "$POST_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✅ Graph contains data (${POST_COUNT} posts, ${TAG_COUNT} tags)${NC}"
    echo -e "${GREEN}✅ Posts ARE being indexed into Neo4j!${NC}"
else
    echo -e "${YELLOW}⚠️  Graph is empty (0 posts)${NC}"
    echo -e "${YELLOW}   → Parse some Telegram channels to populate the graph${NC}"
    echo -e "${YELLOW}   → Use /parse command in the bot${NC}"
fi

if [ "$NEO4J_ENABLED" = "true" ] && [ "$NEO4J_CONNECTED" = "true" ]; then
    echo -e "${GREEN}✅ Neo4j integration is working correctly${NC}"
else
    echo -e "${RED}❌ Neo4j integration has issues${NC}"
    echo -e "${YELLOW}   → Check .env configuration${NC}"
    echo -e "${YELLOW}   → Run: docker logs telethon | grep -i neo4j${NC}"
fi

echo -e "\n${BLUE}═══════════════════════════════════════════════${NC}\n"

