# Neo4j Knowledge Graph - Overview

Neo4j Knowledge Graph для построения и анализа связей в Telegram Bot.

## 🎯 Зачем Knowledge Graph?

**PostgreSQL** хорош для:
- Хранение данных (posts, users, channels)
- CRUD операции
- Transactional integrity

**Neo4j** лучше для:
- Поиск связей (relationships)
- Graph traversal (2-3+ hop queries)
- Рекомендательные системы
- Визуализация связей

**Решение:** Hybrid approach
- PostgreSQL = source of truth (все данные)
- Neo4j = derived graph (relationships)
- Qdrant = vector search (embeddings)

---

## 📊 Что в графе

### Nodes (4 типа)

| Node | Properties | Constraint |
|------|------------|------------|
| **Post** | id, title, content, created_at | Post.id UNIQUE |
| **Tag** | name, usage_count | Tag.name UNIQUE |
| **Channel** | channel_id, title, username | Channel.channel_id UNIQUE |
| **User** | telegram_id, username | User.telegram_id UNIQUE |

### Relationships (4 типа)

| Relationship | From | To | Properties |
|--------------|------|-----|------------|
| **HAS_TAG** | Post | Tag | none |
| **FROM_CHANNEL** | Post | Channel | none |
| **OWNS** | User | Post | none |
| **RELATED_TO** | Tag | Tag | weight (co-occurrence) |

---

## 🚀 Quick Start

### 1. Enable Neo4j

```bash
# В .env:
NEO4J_ENABLED=true
NEO4J_URI=bolt://neo4j:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
```

### 2. Rebuild telethon

```bash
docker compose up -d --build telethon
```

### 3. Проверить

```bash
# Health check
curl http://localhost:8010/graph/health

# Response:
# {"neo4j_enabled": true, "neo4j_connected": true}
```

### 4. Выполнить парсинг

```bash
# Новые посты автоматически индексируются в Neo4j
# Проверить:

docker exec neo4j cypher-shell -u neo4j -p "your_password" \
  "MATCH (p:Post) RETURN count(p)"
```

---

## 💡 Use Cases

### 1. Похожие посты

**API:**
```bash
GET /graph/post/123/related?limit=10
```

**Response:**
```json
{
  "post_id": 123,
  "related_posts": [
    {
      "post_id": 456,
      "title": "Similar post about AI",
      "common_tags": 3,
      "channel_id": "@ai_news"
    }
  ]
}
```

**Cypher:**
```cypher
MATCH (p:Post {id: 123})-[:HAS_TAG]->(t:Tag)<-[:HAS_TAG]-(related:Post)
WHERE p <> related
RETURN related, count(t) AS common_tags
ORDER BY common_tags DESC
LIMIT 10
```

---

### 2. Tag Relationships

**API:**
```bash
GET /graph/tag/AI/relationships?limit=20
```

**Response:**
```json
{
  "tag": "AI",
  "related_tags": [
    {
      "tag": "Python",
      "weight": 15,
      "posts_count": 42
    },
    {
      "tag": "MachineLearning",
      "weight": 12,
      "posts_count": 38
    }
  ]
}
```

**Cypher:**
```cypher
MATCH (t1:Tag {name: 'AI'})-[r:RELATED_TO]-(t2:Tag)
RETURN t2.name, r.weight, t2.usage_count AS posts_count
ORDER BY r.weight DESC
LIMIT 20
```

---

### 3. User Interests

**API:**
```bash
GET /graph/user/123/interests?limit=20
```

**Response:**
```json
{
  "user_id": 123,
  "telegram_id": 456789,
  "interests": [
    {
      "tag": "AI",
      "posts_count": 42,
      "usage_percent": 15.5
    }
  ]
}
```

**Cypher:**
```cypher
MATCH (u:User {telegram_id: 456789})-[:OWNS]->(p:Post)-[:HAS_TAG]->(t:Tag)
RETURN t.name, count(p) AS posts_count
ORDER BY posts_count DESC
LIMIT 20
```

---

## 🔄 Indexing Process

### Автоматическая индексация (новые посты)

```python
# parser_service.py

# 1. Парсинг Telegram
messages = await client.iter_messages(...)

# 2. Сохранение в PostgreSQL
new_post = Post(text=message.text, ...)
db.add(new_post)
db.flush()  # → post.id

# 3. Индексация в Neo4j (фоновая задача)
asyncio.create_task(
    neo4j_client.create_post_node(
        post_id=new_post.id,
        user_id=user.telegram_id,
        channel_id=channel.channel_username,
        title=new_post.text[:100],
        tags=new_post.tags or [],
        created_at=new_post.posted_at.isoformat()
    )
)
```

### Что НЕ индексируется

- ❌ **Старые посты** - только новые с момента интеграции
- ❌ **Deleted posts** - при удалении из PostgreSQL остаются в Neo4j
- ❌ **Embeddings** - хранятся в Qdrant, не в Neo4j

---

## 📐 Architecture

```
PostgreSQL (source of truth)
    │
    │ Parser создает посты
    ↓
┌───────────┐
│   Post    │ ← Сохранено в PostgreSQL
│ (id: 123) │
└───────────┘
    │
    │ Background task
    ↓
┌──────────────────────────────────┐
│         Neo4j Graph              │
│                                  │
│  (User)-[:OWNS]->(Post)          │
│       (Post)-[:HAS_TAG]->(Tag)   │
│       (Post)-[:FROM_CHANNEL]->   │
│              (Channel)           │
│  (Tag)-[:RELATED_TO]-(Tag)       │
└──────────────────────────────────┘
```

---

## 🔧 Configuration

### Environment Variables

```bash
# Neo4j Connection
NEO4J_ENABLED=true                    # Enable/disable graph
NEO4J_URI=bolt://neo4j:7687           # Connection URI
NEO4J_USERNAME=neo4j                  # Username
NEO4J_PASSWORD=your_password          # Password

# Auto-indexing
NEO4J_AUTO_INDEX=true                 # Index new posts automatically
```

### Docker Networks

Neo4j должен быть в той же сети что и telethon:
```yaml
# docker-compose.yml
services:
  neo4j:
    networks:
      - default
      - localai_default
```

---

## 🐛 Troubleshooting

### Neo4j client not initialized

```bash
# Проверить переменные
docker exec telethon env | grep NEO4J

# Должно быть:
NEO4J_ENABLED=true
NEO4J_URI=bolt://neo4j:7687
NEO4J_PASSWORD=...

# Проверить логи
docker logs telethon | grep Neo4j
# Должно быть: "✅ Neo4j client initialized"
```

### Constraints не создаются

```bash
# Проверить вручную
docker exec neo4j cypher-shell -u neo4j -p "password" \
  "SHOW CONSTRAINTS"

# Если пусто - создать:
docker exec neo4j cypher-shell -u neo4j -p "password" \
  "CREATE CONSTRAINT post_id_unique IF NOT EXISTS FOR (p:Post) REQUIRE p.id IS UNIQUE"
```

### Посты не индексируются

```bash
# 1. Проверить что NEO4J_AUTO_INDEX=true
# 2. Проверить логи парсера
docker logs telethon | grep "indexed in Neo4j"

# 3. Проверить есть ли посты в графе
docker exec neo4j cypher-shell -u neo4j -p "password" \
  "MATCH (p:Post) RETURN count(p)"
```

---

## 📚 Best Practices

### 1. MERGE для идемпотентности

```cypher
// ✅ Good - можно вызывать много раз
MERGE (p:Post {id: 123})
SET p.title = "New Title"

// ❌ Bad - ошибка при повторе
CREATE (p:Post {id: 123})
```

### 2. Async operations

```python
# ✅ Good - non-blocking
async with driver.session() as session:
    await session.run(query)

# ❌ Bad - blocks event loop
with driver.session() as session:
    session.run(query)
```

### 3. Background indexing

```python
# ✅ Good - не блокирует парсинг
asyncio.create_task(neo4j_client.create_post_node(...))

# ❌ Bad - замедляет парсинг
await neo4j_client.create_post_node(...)
```

### 4. Graceful degradation

```python
# Код работает БЕЗ Neo4j
if neo4j_client and neo4j_client.enabled:
    await neo4j_client.create_post_node(...)
# Если Neo4j disabled - просто пропускаем
```

---

## 📖 Documentation

- [NEO4J_QUICK_START.md](./NEO4J_QUICK_START.md) - быстрый старт
- [KNOWLEDGE_GRAPH_SCHEMA.md](./KNOWLEDGE_GRAPH_SCHEMA.md) - детальная схема
- [Context7 Best Practices](/neo4j/neo4j-python-driver)

---

## 🎯 Roadmap

**Completed:**
1. ✅ Neo4j client (async driver)
2. ✅ Auto-indexing новых постов
3. ✅ API endpoints (related posts, tag relationships, user interests)
4. ✅ Constraints и indexes

**TODO:**
1. ⏭️ **Visualization** - Neo4j Browser или custom UI
2. ⏭️ **Graph algorithms** - PageRank, Community Detection (через GDS)
3. ⏭️ **Recommendations** - использовать граф для персональных рекомендаций
4. ⏭️ **Graph export** - export граф для анализа
5. ⏭️ **Re-indexing** - команда для переиндексации всех постов

---

**Status:** ✅ Knowledge Graph Ready!

Граф автоматически строится для новых постов, доступен через API endpoints.

