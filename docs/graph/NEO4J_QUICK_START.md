# Neo4j Quick Start - Knowledge Graph для Telegram Bot

Neo4j используется для построения knowledge graph постов, тегов и каналов.

## 🎯 Что дает Knowledge Graph

**Возможности:**
- ✅ **Найти похожие посты** - по общим тегам
- ✅ **Анализ тегов** - какие теги связаны между собой
- ✅ **Интересы пользователей** - топ теги по активности
- ✅ **Рекомендации** - на основе graph traversal

**Преимущества перед SQL:**
- Быстрый поиск связей (relationships)
- Сложные graph queries (2-3 hop connections)
- Визуализация связей (Neo4j Browser)

## 🚀 Quick Start

### 1. Проверить что Neo4j запущен

```bash
docker ps | grep neo4j
# → neo4j  Up (healthy)

docker exec neo4j cypher-shell -u neo4j -p "your_password" "RETURN 1"
# → 1
```

### 2. Настроить environment variables

```bash
# В .env:
NEO4J_ENABLED=true
NEO4J_URI=bolt://neo4j:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password_here
NEO4J_AUTO_INDEX=true
```

### 3. Rebuild telethon

```bash
docker compose up -d --build telethon
```

### 4. Проверить constraints созданы

```bash
docker exec neo4j cypher-shell -u neo4j -p "your_password" \
  "SHOW CONSTRAINTS"
  
# Должны появиться:
# - post_id_unique
# - tag_name_unique
# - channel_id_unique
# - user_telegram_id_unique
```

### 5. Test - выполнить парсинг

```bash
# Парсинг автоматически создаст nodes в Neo4j
# Проверить:

docker exec neo4j cypher-shell -u neo4j -p "your_password" \
  "MATCH (p:Post) RETURN count(p)"
  
# Должно увеличиться после парсинга новых постов
```

## 📊 Graph Schema

### Nodes

```cypher
(:Post {
    id: Integer,           # PostgreSQL ID
    title: String,         # Первые 100 символов
    content: String,       # Полный текст
    created_at: DateTime
})

(:Tag {
    name: String,          # Имя тега
    usage_count: Integer   # Сколько раз использован
})

(:Channel {
    channel_id: String,    # @channel_name
    title: String,
    username: String
})

(:User {
    telegram_id: Integer,  # Telegram ID
    username: String
})
```

### Relationships

```cypher
(Post)-[:HAS_TAG]->(Tag)
(Post)-[:FROM_CHANNEL]->(Channel)
(User)-[:OWNS]->(Post)
(Tag)-[:RELATED_TO {weight: Integer}]-(Tag)  # Co-occurrence count
```

## 🔍 Useful Cypher Queries

### Найти похожие посты

```cypher
// По ID поста
MATCH (p:Post {id: 123})-[:HAS_TAG]->(t:Tag)<-[:HAS_TAG]-(related:Post)
WHERE p <> related
RETURN related.id, related.title, count(t) AS common_tags
ORDER BY common_tags DESC
LIMIT 10
```

### Топ 20 тегов

```cypher
MATCH (t:Tag)
RETURN t.name, t.usage_count
ORDER BY t.usage_count DESC
LIMIT 20
```

### Интересы пользователя

```cypher
MATCH (u:User {telegram_id: 123456789})-[:OWNS]->(p:Post)-[:HAS_TAG]->(t:Tag)
RETURN t.name, count(p) AS posts_count
ORDER BY posts_count DESC
LIMIT 20
```

### Связанные теги (часто встречаются вместе)

```cypher
MATCH (t1:Tag {name: 'AI'})-[r:RELATED_TO]-(t2:Tag)
RETURN t2.name, r.weight
ORDER BY r.weight DESC
LIMIT 10
```

### Топ каналов пользователя

```cypher
MATCH (u:User {telegram_id: 123456789})-[:OWNS]->(p:Post)-[:FROM_CHANNEL]->(c:Channel)
RETURN c.channel_id, count(p) AS posts_count
ORDER BY posts_count DESC
```

## 🌐 API Endpoints

### Get Related Posts

```bash
GET /graph/post/{post_id}/related?limit=10

Response:
{
  "post_id": 123,
  "related_posts": [
    {
      "post_id": 456,
      "title": "Related Post",
      "common_tags": 3,
      "channel_id": "@tech_channel"
    }
  ],
  "count": 5
}
```

### Get Tag Relationships

```bash
GET /graph/tag/{tag_name}/relationships?limit=20

Response:
{
  "tag": "AI",
  "related_tags": [
    {
      "tag": "Python",
      "weight": 15,
      "posts_count": 42
    }
  ],
  "count": 10
}
```

### Get User Interests

```bash
GET /graph/user/{user_id}/interests?limit=20

Response:
{
  "user_id": 123,
  "telegram_id": 456789,
  "interests": [
    {
      "tag": "AI",
      "posts_count": 42,
      "usage_percent": 15.5
    }
  ],
  "count": 10
}
```

### Health Check

```bash
GET /graph/health

Response:
{
  "neo4j_enabled": true,
  "neo4j_connected": true
}
```

## 🔧 How It Works

### 1. Автоматическая индексация

```python
# parser_service.py

# После создания поста в PostgreSQL:
new_post = Post(...)
db.add(new_post)
db.flush()  # Получить post.id

# Автоматически создать в Neo4j (фоновая задача):
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

### 2. Graph Queries

```python
# Найти похожие посты
related = await neo4j_client.get_related_posts(post_id=123, limit=10)

# Анализ связей тегов
tags = await neo4j_client.get_tag_relationships("AI", limit=20)

# Интересы пользователя
interests = await neo4j_client.get_user_interests(telegram_id=123456, limit=20)
```

## 🐛 Troubleshooting

### Neo4j не подключается

```bash
# Проверить контейнер
docker ps | grep neo4j

# Проверить логи
docker logs neo4j

# Проверить credentials
docker exec neo4j cypher-shell -u neo4j -p "your_password" "RETURN 1"
```

### Constraints не созданы

```bash
# Проверить
docker exec neo4j cypher-shell -u neo4j -p "your_password" "SHOW CONSTRAINTS"

# Создать вручную
docker exec neo4j cypher-shell -u neo4j -p "your_password" \
  "CREATE CONSTRAINT post_id_unique IF NOT EXISTS FOR (p:Post) REQUIRE p.id IS UNIQUE"
```

### Посты не индексируются

```bash
# Проверить NEO4J_ENABLED
docker exec telethon env | grep NEO4J

# Проверить логи
docker logs telethon | grep -i neo4j

# Должна быть строка: "✅ Neo4j client initialized"
```

## 📚 Best Practices

### 1. MERGE вместо CREATE

```cypher
// ✅ Good - идемпотентность
MERGE (p:Post {id: 123})
SET p.title = "New Title"

// ❌ Bad - ошибка при повторном вызове
CREATE (p:Post {id: 123})
```

### 2. Constraints для уникальности

```cypher
// Обеспечивает что Post.id уникален
CREATE CONSTRAINT post_id_unique IF NOT EXISTS 
FOR (p:Post) REQUIRE p.id IS UNIQUE
```

### 3. Async operations

```python
# ✅ Good - non-blocking
async with driver.session() as session:
    await session.run(query)

# ❌ Bad - blocks event loop
with driver.session() as session:
    session.run(query)
```

### 4. Background indexing

```python
# ✅ Good - не блокирует парсинг
asyncio.create_task(neo4j_client.create_post_node(...))

# ❌ Bad - блокирует
await neo4j_client.create_post_node(...)
```

## 🔗 Полезные ссылки

- [Neo4j Python Driver](https://github.com/neo4j/neo4j-python-driver)
- [Cypher Manual](https://neo4j.com/docs/cypher-manual/)
- [Neo4j Browser](http://localhost:7474) (если проброшен порт)
- [Context7 Neo4j Guide](/neo4j/neo4j-python-driver)

## 🎯 Next Steps

1. ✅ **Setup Neo4j** (done)
2. ⏭️ **Visualize graph** - Neo4j Browser или neovis.js
3. ⏭️ **Advanced queries** - graph algorithms (PageRank, Community Detection)
4. ⏭️ **Recommendations** - использовать граф для рекомендаций постов

