#!/bin/bash
# Quick fix script после update.sh
# Восстанавливает критичные настройки для Neo4j и Prometheus

set -e

BACKUP_DIR="/home/ilyasni/n8n-server/n8n-installer/.backups/pre-update-20251014-004900"

echo "🔧 Checking what needs to be restored..."
echo ""

# 1. Check Neo4j networks
echo "1️⃣ Checking Neo4j networks..."
if grep -A10 "neo4j:" docker-compose.yml | grep -q "networks:"; then
    echo "   ✅ Neo4j networks: OK"
else
    echo "   ❌ Neo4j networks: MISSING"
    echo "   Fix: Add networks to neo4j service in docker-compose.yml"
fi

# 2. Check Prometheus networks
echo "2️⃣ Checking Prometheus networks..."
if grep -A10 "prometheus:" docker-compose.yml | grep -q "networks:"; then
    echo "   ✅ Prometheus networks: OK"
else
    echo "   ❌ Prometheus networks: MISSING"
    echo "   Fix: Add networks to prometheus service in docker-compose.yml"
fi

# 3. Check Caddy port 7687
echo "3️⃣ Checking Caddy ports..."
if grep -A10 "caddy:" docker-compose.yml | grep -q "7687"; then
    echo "   ❌ Caddy port 7687: PRESENT (should be removed)"
    echo "   Fix: Remove '- \"7687:7687\"' from caddy ports"
else
    echo "   ✅ Caddy port 7687: OK (not present)"
fi

# 4. Check NEO4J_HOSTNAME in .env
echo "4️⃣ Checking NEO4J_HOSTNAME..."
if grep -q "NEO4J_HOSTNAME=neo4j.produman.studio" .env; then
    echo "   ✅ NEO4J_HOSTNAME: OK"
else
    echo "   ❌ NEO4J_HOSTNAME: MISSING"
    echo "   Fix: Add NEO4J_HOSTNAME=neo4j.produman.studio to .env"
fi

# 5. Check COMPOSE_PROFILES
echo "5️⃣ Checking COMPOSE_PROFILES..."
if grep -q "COMPOSE_PROFILES=.*neo4j" .env; then
    echo "   ✅ COMPOSE_PROFILES contains neo4j: OK"
else
    echo "   ⚠️ COMPOSE_PROFILES: neo4j not in profiles"
    echo "   Check if you selected neo4j in wizard"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📝 To restore all configs:"
echo "   cp $BACKUP_DIR/docker-compose.yml docker-compose.yml"
echo ""
echo "📝 To compare:"
echo "   diff $BACKUP_DIR/docker-compose.yml docker-compose.yml"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
