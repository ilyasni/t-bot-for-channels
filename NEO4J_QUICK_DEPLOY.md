# 🚀 Neo4j Knowledge Graph - Quick Deploy

**TL;DR:** Neo4j интегрирован. Новые посты автоматически индексируются в граф.

## ⚡ 5 минут до запуска

### 1. Настроить Neo4j password

```bash
# Проверить что Neo4j запущен
docker ps | grep neo4j

# Установить новый пароль (первый раз используйте "neo4j")
docker exec neo4j cypher-shell -u neo4j -p "neo4j" \
  "ALTER USER neo4j SET PASSWORD 'YourSecurePassword123'"
```

### 2. Добавить в .env

```bash
nano /home/ilyasni/n8n-server/n8n-installer/.env

# Добавить:
NEO4J_ENABLED=true
NEO4J_URI=bolt://neo4j:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=YourSecurePassword123
NEO4J_AUTO_INDEX=true
```

### 3. Rebuild telethon

```bash
cd /home/ilyasni/n8n-server/n8n-installer
docker compose up -d --build telethon
```

### 4. Verify

```bash
# Health check
curl http://localhost:8010/graph/health

# Должно быть:
# {"neo4j_enabled": true, "neo4j_connected": true}

# Constraints созданы
docker exec neo4j cypher-shell -u neo4j -p "YourSecurePassword123" \
  "SHOW CONSTRAINTS"

# Должно быть 4 constraints
```

### 5. Test - автоматическая индексация

```bash
# Выполнить парсинг нового канала в боте
# → Новые посты автоматически индексируются в Neo4j

# Проверить:
docker exec neo4j cypher-shell -u neo4j -p "YourSecurePassword123" \
  "MATCH (p:Post) RETURN count(p) AS total_posts"

# Количество должно увеличиться
```

---

## 📊 Graph Schema (кратко)

**Nodes:**
- Post (id, title, content)
- Tag (name, usage_count)
- Channel (channel_id)
- User (telegram_id)

**Relationships:**
- Post → Tag (HAS_TAG)
- Post → Channel (FROM_CHANNEL)
- User → Post (OWNS)
- Tag ↔ Tag (RELATED_TO with weight)

---

## 🌐 API Endpoints

```bash
# Похожие посты
GET /graph/post/123/related?limit=10

# Tag relationships
GET /graph/tag/AI/relationships?limit=20

# User interests
GET /graph/user/123/interests?limit=20

# Health
GET /graph/health
```

---

## 🔍 Cypher Query Examples

### Похожие посты

```bash
docker exec neo4j cypher-shell -u neo4j -p "password" \
  "MATCH (p:Post {id: 123})-[:HAS_TAG]->(t:Tag)<-[:HAS_TAG]-(related:Post)
   WHERE p <> related
   RETURN related.title, count(t) AS common_tags
   ORDER BY common_tags DESC
   LIMIT 10"
```

### Топ теги

```bash
docker exec neo4j cypher-shell -u neo4j -p "password" \
  "MATCH (t:Tag)
   RETURN t.name, t.usage_count
   ORDER BY t.usage_count DESC
   LIMIT 20"
```

### Tag co-occurrence

```bash
docker exec neo4j cypher-shell -u neo4j -p "password" \
  "MATCH (t1:Tag {name: 'AI'})-[r:RELATED_TO]-(t2:Tag)
   RETURN t2.name, r.weight
   ORDER BY r.weight DESC
   LIMIT 10"
```

---

## 📚 Документация

- **Overview:** `/docs/graph/README.md`
- **Quick Start:** `/docs/graph/NEO4J_QUICK_START.md`
- **Schema:** `/docs/graph/KNOWLEDGE_GRAPH_SCHEMA.md`
- **Full Report:** `/NEO4J_INTEGRATION_COMPLETE.md`

---

## 🐛 Troubleshooting

### Neo4j не подключается

```bash
docker logs neo4j
docker exec neo4j cypher-shell -u neo4j -p "password" "RETURN 1"
```

### Posty не индексируются

```bash
# Проверить логи
docker logs telethon | grep -i neo4j

# Должно быть: "✅ Neo4j client initialized"
```

### Graph queries не работают

```bash
# Проверить health
curl http://localhost:8010/graph/health

# Если neo4j_connected: false
# → Проверить NEO4J_PASSWORD в .env
```

---

**Status:** ✅ Ready to use!

Новые посты автоматически индексируются в Neo4j Knowledge Graph!
