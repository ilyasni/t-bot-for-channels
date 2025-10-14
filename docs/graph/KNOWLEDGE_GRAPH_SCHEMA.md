# Knowledge Graph Schema - Telegram Bot

Схема Neo4j Knowledge Graph для анализа связей между постами, тегами и каналами.

## 🎯 Концепция

Knowledge Graph позволяет:
- Находить похожие посты через общие теги
- Анализировать co-occurrence тегов (какие теги часто встречаются вместе)
- Строить профиль интересов пользователя
- Делать graph-based рекомендации

## 📐 Graph Schema

```
┌─────────┐                    ┌──────┐
│  User   │──[OWNS]───────────>│ Post │
└─────────┘                    └──────┘
     │                             │
     │                             │HAS_TAG
     │                             ↓
     │                         ┌──────┐
     │                         │ Tag  │<───[RELATED_TO]───┐
     │                         └──────┘                   │
     │                             │                       │
     │                             └───────────────────────┘
     │
     │                         ┌──────────┐
     └──[SUBSCRIBED_TO]───────>│ Channel  │
                               └──────────┘
                                    ↑
                                    │FROM_CHANNEL
                               ┌────┘
                               │
                            ┌──────┐
                            │ Post │
                            └──────┘
```

## 📦 Node Types

### Post Node

```cypher
(:Post {
    id: Integer,              # UNIQUE - PostgreSQL ID
    title: String,            # Первые 100 символов текста
    content: String,          # Полный текст (опционально)
    created_at: String,       # ISO datetime
    updated_at: DateTime      # Neo4j datetime (auto-updated)
})
```

**Constraints:**
```cypher
CREATE CONSTRAINT post_id_unique IF NOT EXISTS 
FOR (p:Post) REQUIRE p.id IS UNIQUE
```

**Index автоматически создается** при constraint.

---

### Tag Node

```cypher
(:Tag {
    name: String,             # UNIQUE - имя тега
    usage_count: Integer      # Сколько постов имеют этот тег
})
```

**Constraints:**
```cypher
CREATE CONSTRAINT tag_name_unique IF NOT EXISTS 
FOR (t:Tag) REQUIRE t.name IS UNIQUE
```

**Usage count:**
- Increment при каждом `MERGE (p)-[:HAS_TAG]->(t)`
- `ON CREATE SET t.usage_count = 1`
- `ON MATCH SET t.usage_count = t.usage_count + 1`

---

### Channel Node

```cypher
(:Channel {
    channel_id: String,       # UNIQUE - @channel_name
    title: String,            # Название канала (опционально)
    username: String          # Username без @ (опционально)
})
```

**Constraints:**
```cypher
CREATE CONSTRAINT channel_id_unique IF NOT EXISTS 
FOR (c:Channel) REQUIRE c.channel_id IS UNIQUE
```

---

### User Node

```cypher
(:User {
    telegram_id: Integer,     # UNIQUE - Telegram ID
    username: String,         # Telegram username
    updated_at: DateTime      # Последнее обновление
})
```

**Constraints:**
```cypher
CREATE CONSTRAINT user_telegram_id_unique IF NOT EXISTS 
FOR (u:User) REQUIRE u.telegram_id IS UNIQUE
```

---

## 🔗 Relationship Types

### HAS_TAG

```cypher
(Post)-[:HAS_TAG]->(Tag)
```

**Создается:** При индексации поста с тегами  
**Свойства:** Нет  
**Направление:** Post → Tag

**Query example:**
```cypher
// Посты с тегом "AI"
MATCH (p:Post)-[:HAS_TAG]->(t:Tag {name: 'AI'})
RETURN p.title, p.created_at
ORDER BY p.created_at DESC
LIMIT 10
```

---

### FROM_CHANNEL

```cypher
(Post)-[:FROM_CHANNEL]->(Channel)
```

**Создается:** При индексации каждого поста  
**Свойства:** Нет  
**Направление:** Post → Channel

**Query example:**
```cypher
// Все посты из канала
MATCH (p:Post)-[:FROM_CHANNEL]->(c:Channel {channel_id: '@tech_news'})
RETURN p.title, p.created_at
ORDER BY p.created_at DESC
```

---

### OWNS

```cypher
(User)-[:OWNS]->(Post)
```

**Создается:** При индексации поста  
**Свойства:** Нет  
**Направление:** User → Post

**Query example:**
```cypher
// Все посты пользователя
MATCH (u:User {telegram_id: 123456})-[:OWNS]->(p:Post)
RETURN count(p) AS total_posts
```

---

### RELATED_TO (Tag Co-occurrence)

```cypher
(Tag)-[:RELATED_TO {weight: Integer}]-(Tag)
```

**Создается:** Автоматически при наличии 2+ тегов в посте  
**Свойства:** `weight` - сколько раз теги встретились вместе  
**Направление:** Undirected (симметричная связь)

**Update logic:**
```cypher
// Если теги встречаются вместе
MERGE (t1:Tag)-[r:RELATED_TO]-(t2:Tag)
ON CREATE SET r.weight = 1
ON MATCH SET r.weight = r.weight + 1
```

**Query example:**
```cypher
// С каким тегами чаще всего встречается "AI"
MATCH (t1:Tag {name: 'AI'})-[r:RELATED_TO]-(t2:Tag)
RETURN t2.name, r.weight
ORDER BY r.weight DESC
LIMIT 10
```

---

## 🔄 Indexing Flow

### Автоматическая индексация новых постов

```
1. Parser парсит новый пост
   ↓
2. Сохранение в PostgreSQL (Post table)
   ↓
3. db.flush() → получить post.id
   ↓
4. Фоновая задача: neo4j_client.create_post_node()
   ↓
5. Neo4j создает:
   - Post node
   - Relationships (OWNS, FROM_CHANNEL, HAS_TAG)
   - Tag co-occurrence (RELATED_TO)
```

### Что индексируется

**Сразу при парсинге:**
- ✅ Post node (id, title, content, created_at)
- ✅ User node (если не существует)
- ✅ Channel node (если не существует)
- ✅ Relationships: OWNS, FROM_CHANNEL

**После тегирования:**
- ✅ HAS_TAG relationships (когда теги установлены)
- ✅ RELATED_TO relationships (co-occurrence)

**Не индексируется:**
- ❌ Старые посты (только новые с момента интеграции)
- ❌ Embeddings vectors (хранятся в Qdrant)
- ❌ Full post text > 1000 chars (только title)

---

## 📊 Use Cases

### 1. Похожие посты (Recommendation)

**Задача:** Пользователь читает пост про "AI", показать похожие.

**Cypher:**
```cypher
MATCH (p:Post {id: 123})-[:HAS_TAG]->(t:Tag)<-[:HAS_TAG]-(related:Post)
WHERE p <> related
WITH related, count(DISTINCT t) AS common_tags
ORDER BY common_tags DESC
LIMIT 5
MATCH (related)-[:FROM_CHANNEL]->(c:Channel)
RETURN related.id, related.title, common_tags, c.channel_id
```

**API:**
```bash
GET /graph/post/123/related?limit=5
```

---

### 2. Tag Analysis (Tag Cloud)

**Задача:** Построить tag cloud с весами.

**Cypher:**
```cypher
MATCH (t:Tag)
RETURN t.name, t.usage_count
ORDER BY t.usage_count DESC
LIMIT 50
```

**Visualization:**
- Размер тега = usage_count
- Цвет = категория (если классифицируем)

---

### 3. User Profiling

**Задача:** Понять интересы пользователя.

**Cypher:**
```cypher
MATCH (u:User {telegram_id: 123456})-[:OWNS]->(p:Post)-[:HAS_TAG]->(t:Tag)
WITH u, t, count(p) AS posts_count
WITH u, collect({tag: t.name, count: posts_count}) AS tags,
     sum(posts_count) AS total_posts
RETURN tags, total_posts
```

**API:**
```bash
GET /graph/user/123/interests?limit=20
```

---

### 4. Tag Relationships Network

**Задача:** Построить граф связей между тегами.

**Cypher:**
```cypher
MATCH (t1:Tag)-[r:RELATED_TO]-(t2:Tag)
WHERE r.weight > 5  // Только часто встречающиеся
RETURN t1.name, t2.name, r.weight
ORDER BY r.weight DESC
LIMIT 100
```

**Visualization:** Force-directed graph в Neo4j Browser или neovis.js.

---

## 🎨 Visualizing Graph

### Neo4j Browser (built-in)

```bash
# Открыть Neo4j Browser (если порт проброшен)
open http://localhost:7474

# Или через docker exec:
docker exec -it neo4j cypher-shell -u neo4j -p "your_password"

# Выполнить query:
MATCH (p:Post)-[:HAS_TAG]->(t:Tag)
RETURN p, t
LIMIT 50
```

### Python Visualization (опционально)

```python
# Использовать neo4j.graph для получения nodes/relationships
async with driver.session() as session:
    result = await session.run("""
        MATCH (p:Post)-[:HAS_TAG]->(t:Tag)
        RETURN p, t
        LIMIT 100
    """)
    
    graph = await result.graph()
    # graph.nodes - все ноды
    # graph.relationships - все связи
```

---

## ⚠️ Important Notes

**Performance:**
- Constraints автоматически создают indexes
- Graph queries быстрые для 2-3 hop connections
- Для миллионов nodes - используйте pagination

**Storage:**
- Neo4j хранит данные в `/data` volume
- Backup: `docker exec neo4j neo4j-admin backup`

**Consistency:**
- PostgreSQL = source of truth
- Neo4j = derived graph (можно пересоздать)
- При удалении поста из PostgreSQL - НЕ удаляется из Neo4j (by design)

---

## 🔗 См. также

- [NEO4J_QUICK_START.md](./NEO4J_QUICK_START.md) - быстрый старт
- [README.md](./README.md) - overview
- [Context7 Best Practices](/neo4j/neo4j-python-driver)

