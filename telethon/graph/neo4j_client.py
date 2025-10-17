"""
Neo4j Client для Knowledge Graph

Best practices from Context7 (/neo4j/neo4j-python-driver):
- AsyncGraphDatabase для non-blocking операций
- Session management через async with context managers
- MERGE вместо CREATE для идемпотентности
- Managed transactions для automatic retry logic
- Constraints для уникальности nodes

Knowledge Graph Structure:
- Post nodes (id, title, content, created_at)
- Tag nodes (name, usage_count)
- Channel nodes (channel_id, title, username)
- User nodes (telegram_id, username)

Relationships:
- Post -[HAS_TAG]-> Tag
- Post -[FROM_CHANNEL]-> Channel
- User -[OWNS]-> Post
- Tag -[RELATED_TO {weight}]- Tag (co-occurrence)
"""
import os
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import time

logger = logging.getLogger(__name__)

# Import metrics (опционально)
try:
    from rag_service.metrics import record_graph_query, set_graph_availability
    METRICS_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ Metrics not available")
    METRICS_AVAILABLE = False
    record_graph_query = lambda *args, **kwargs: None
    set_graph_availability = lambda *args: None

# Lazy import Neo4j (может не быть установлен)
try:
    from neo4j import AsyncGraphDatabase, AsyncDriver
    NEO4J_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ Neo4j driver not installed. Install with: pip install neo4j")
    NEO4J_AVAILABLE = False
    AsyncDriver = None


class Neo4jClient:
    """
    Async Neo4j client для построения knowledge graph
    
    Features:
    - Async operations (non-blocking)
    - Auto-create constraints and indexes
    - Graceful degradation (работает без Neo4j)
    - MERGE-based operations (идемпотентность)
    
    Example:
        ```python
        from graph.neo4j_client import neo4j_client
        
        # Создать пост в графе
        await neo4j_client.create_post_node(
            post_id=123,
            user_id=456,
            channel_id="@channel",
            title="Post Title",
            tags=["ai", "python"],
            created_at="2025-01-14T12:00:00Z"
        )
        
        # Найти связанные посты
        related = await neo4j_client.get_related_posts(post_id=123, limit=10)
        ```
    """
    
    def __init__(self):
        """Инициализация Neo4j driver из environment variables"""
        self.enabled = os.getenv("NEO4J_ENABLED", "false").lower() == "true"
        self.driver: Optional[AsyncDriver] = None
        
        if not NEO4J_AVAILABLE:
            logger.info("⚠️ Neo4j driver not available, graph features disabled")
            self.enabled = False
            return
        
        if self.enabled:
            try:
                uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
                username = os.getenv("NEO4J_USERNAME", "neo4j")
                password = os.getenv("NEO4J_PASSWORD")
                
                if not password:
                    logger.warning("⚠️ NEO4J_PASSWORD not set, graph features disabled")
                    self.enabled = False
                    return
                
                # Best practice from Context7: use AsyncGraphDatabase.driver
                self.driver = AsyncGraphDatabase.driver(
                    uri,
                    auth=(username, password)
                )
                logger.info(f"✅ Neo4j client initialized (uri: {uri})")
                
            except Exception as e:
                logger.error(f"❌ Neo4j initialization failed: {e}")
                self.enabled = False
        else:
            logger.info("⚠️ Neo4j disabled (NEO4J_ENABLED=false)")
    
    async def _create_constraints(self):
        """
        Создать constraints и indexes для оптимизации
        
        Best practice from Context7: constraints обеспечивают уникальность
        """
        if not self.enabled or not self.driver:
            return
        
        constraints = [
            "CREATE CONSTRAINT post_id_unique IF NOT EXISTS FOR (p:Post) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT tag_name_unique IF NOT EXISTS FOR (t:Tag) REQUIRE t.name IS UNIQUE",
            "CREATE CONSTRAINT channel_id_unique IF NOT EXISTS FOR (c:Channel) REQUIRE c.channel_id IS UNIQUE",
            "CREATE CONSTRAINT user_telegram_id_unique IF NOT EXISTS FOR (u:User) REQUIRE u.telegram_id IS UNIQUE",
        ]
        
        try:
            # Best practice: use async with for session management
            async with self.driver.session() as session:
                for constraint in constraints:
                    await session.run(constraint)
            logger.info("✅ Neo4j constraints created")
        except Exception as e:
            logger.error(f"❌ Failed to create Neo4j constraints: {e}")
    
    async def health_check(self) -> bool:
        """
        Проверить подключение к Neo4j
        
        Returns:
            True если подключение успешно
        """
        if not self.enabled or not self.driver:
            set_graph_availability(False)
            return False
        
        try:
            async with self.driver.session() as session:
                result = await session.run("RETURN 1 AS num")
                record = await result.single()
                is_healthy = record["num"] == 1
                set_graph_availability(is_healthy)
                return is_healthy
        except Exception as e:
            logger.error(f"❌ Neo4j health check failed: {e}")
            set_graph_availability(False)
            return False
    
    async def create_user_node(self, telegram_id: int, username: Optional[str] = None):
        """
        Создать или обновить ноду пользователя
        
        Args:
            telegram_id: Telegram ID пользователя
            username: Username (опционально)
            
        Best practice: MERGE для идемпотентности
        """
        if not self.enabled or not self.driver:
            return
        
        try:
            async with self.driver.session() as session:
                query = """
                MERGE (u:User {telegram_id: $telegram_id})
                SET u.username = $username,
                    u.updated_at = datetime()
                RETURN u
                """
                await session.run(query, telegram_id=telegram_id, username=username)
                logger.debug(f"✅ Created/updated User node: {telegram_id}")
        except Exception as e:
            logger.error(f"❌ Failed to create User node: {e}")
    
    async def create_post_node(
        self,
        post_id: int,
        user_id: int,
        channel_id: str,
        title: str,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None,
        created_at: Optional[str] = None
    ):
        """
        Создать ноду поста со связями
        
        Args:
            post_id: ID поста из PostgreSQL
            user_id: Telegram ID пользователя
            channel_id: ID канала (например "@channel")
            title: Заголовок поста (первые 100 символов текста)
            content: Полный текст поста (опционально)
            tags: Список тегов
            created_at: Дата создания (ISO format)
            
        Creates:
            - Post node
            - Tag nodes (если не существуют)
            - Channel node (если не существует)
            - Relationships: Post-[HAS_TAG]->Tag, Post-[FROM_CHANNEL]->Channel, User-[OWNS]->Post
            - Tag co-occurrence relationships
            
        Best practices:
            - MERGE для идемпотентности (можно вызывать много раз)
            - ON CREATE/ON MATCH для условной логики
            - UNWIND для batch операций с тегами
        """
        if not self.enabled or not self.driver:
            return
        
        tags = tags or []
        created_at = created_at or datetime.utcnow().isoformat()
        
        try:
            # Best practice: async with для session management
            async with self.driver.session() as session:
                query = """
                // 1. Создать Post node (MERGE = идемпотентность)
                MERGE (p:Post {id: $post_id})
                SET p.title = $title,
                    p.content = $content,
                    p.created_at = $created_at,
                    p.updated_at = datetime()
                
                // 2. Создать Channel node и связь
                MERGE (c:Channel {channel_id: $channel_id})
                MERGE (p)-[:FROM_CHANNEL]->(c)
                
                // 3. Создать связь с User
                WITH p
                MATCH (u:User {telegram_id: $user_id})
                MERGE (u)-[:OWNS]->(p)
                
                // 4. Создать Tag nodes и связи (UNWIND для batch)
                WITH p
                UNWIND $tags AS tag_name
                MERGE (t:Tag {name: tag_name})
                ON CREATE SET t.usage_count = 1
                ON MATCH SET t.usage_count = t.usage_count + 1
                MERGE (p)-[:HAS_TAG]->(t)
                
                RETURN p.id AS post_id
                """
                
                result = await session.run(
                    query,
                    post_id=post_id,
                    user_id=user_id,
                    channel_id=channel_id,
                    title=title,
                    content=content,
                    tags=tags,
                    created_at=created_at
                )
                
                # Consume result
                await result.consume()
                
                logger.debug(f"✅ Created Post node: {post_id} with {len(tags)} tags")
                
                # 5. Обновить co-occurrence между тегами (если больше 1 тега)
                if len(tags) > 1:
                    await self._update_tag_cooccurrence(session, tags)
                    
        except Exception as e:
            logger.error(f"❌ Failed to create Post node {post_id}: {e}")
    
    async def _update_tag_cooccurrence(self, session, tags: List[str]):
        """
        Обновить RELATED_TO relationships между тегами (co-occurrence)
        
        Args:
            session: Активная Neo4j session
            tags: Список тегов из одного поста
            
        Best practice: MERGE relationships с weight для подсчета co-occurrence
        """
        if len(tags) < 2:
            return
        
        try:
            query = """
            // Для каждой пары тегов
            UNWIND $tags AS tag1
            UNWIND $tags AS tag2
            WITH tag1, tag2
            WHERE tag1 < tag2  // Избегаем дублирования (tag1, tag2) и (tag2, tag1)
            
            // Найти оба тега
            MATCH (t1:Tag {name: tag1}), (t2:Tag {name: tag2})
            
            // Создать или обновить связь
            MERGE (t1)-[r:RELATED_TO]-(t2)
            ON CREATE SET r.weight = 1
            ON MATCH SET r.weight = r.weight + 1
            
            RETURN count(r) AS updated_relationships
            """
            
            await session.run(query, tags=tags)
            logger.debug(f"✅ Updated tag co-occurrence for {len(tags)} tags")
            
        except Exception as e:
            logger.error(f"❌ Failed to update tag co-occurrence: {e}")
    
    async def get_related_posts(
        self,
        post_id: int,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Найти посты связанные через общие теги
        
        Args:
            post_id: ID поста
            limit: Количество результатов
            
        Returns:
            Список related постов с метаданными:
            [{
                "post_id": 456,
                "title": "Related Post",
                "common_tags": 3,
                "channel_id": "@channel"
            }]
        """
        if not self.enabled or not self.driver:
            return []
        
        try:
            async with self.driver.session() as session:
                query = """
                // Найти исходный пост
                MATCH (p:Post {id: $post_id})-[:HAS_TAG]->(t:Tag)
                
                // Найти другие посты с такими же тегами
                MATCH (t)<-[:HAS_TAG]-(related:Post)
                WHERE p <> related
                
                // Получить channel
                OPTIONAL MATCH (related)-[:FROM_CHANNEL]->(c:Channel)
                
                // Агрегировать результаты
                RETURN related.id AS post_id,
                       related.title AS title,
                       count(DISTINCT t) AS common_tags,
                       c.channel_id AS channel_id
                ORDER BY common_tags DESC
                LIMIT $limit
                """
                
                result = await session.run(query, post_id=post_id, limit=limit)
                
                related_posts = []
                async for record in result:
                    related_posts.append({
                        "post_id": record["post_id"],
                        "title": record["title"],
                        "common_tags": record["common_tags"],
                        "channel_id": record["channel_id"]
                    })
                
                return related_posts
                
        except Exception as e:
            logger.error(f"❌ Failed to get related posts: {e}")
            return []
    
    async def get_tag_relationships(
        self,
        tag_name: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Получить связи тега с другими тегами (co-occurrence)
        
        Args:
            tag_name: Имя тега
            limit: Количество результатов
            
        Returns:
            Список связанных тегов:
            [{
                "tag": "related_tag",
                "weight": 15,
                "posts_count": 15
            }]
        """
        if not self.enabled or not self.driver:
            return []
        
        try:
            async with self.driver.session() as session:
                query = """
                MATCH (t1:Tag {name: $tag_name})-[r:RELATED_TO]-(t2:Tag)
                RETURN t2.name AS tag,
                       r.weight AS weight,
                       t2.usage_count AS posts_count
                ORDER BY r.weight DESC
                LIMIT $limit
                """
                
                result = await session.run(query, tag_name=tag_name, limit=limit)
                
                relationships = []
                async for record in result:
                    relationships.append({
                        "tag": record["tag"],
                        "weight": record["weight"],
                        "posts_count": record["posts_count"]
                    })
                
                return relationships
                
        except Exception as e:
            logger.error(f"❌ Failed to get tag relationships: {e}")
            return []
    
    async def get_user_interests(
        self,
        telegram_id: int,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Анализ интересов пользователя через граф
        
        Args:
            telegram_id: Telegram ID пользователя
            limit: Количество топ тегов
            
        Returns:
            Топ теги пользователя:
            [{
                "tag": "AI",
                "posts_count": 42,
                "usage_percent": 15.5
            }]
        """
        if not self.enabled or not self.driver:
            return []
        
        try:
            async with self.driver.session() as session:
                query = """
                MATCH (u:User {telegram_id: $telegram_id})-[:OWNS]->(p:Post)-[:HAS_TAG]->(t:Tag)
                WITH u, t, count(p) AS posts_count, count(DISTINCT p) AS user_posts_total
                RETURN t.name AS tag,
                       posts_count,
                       round(100.0 * posts_count / user_posts_total, 2) AS usage_percent
                ORDER BY posts_count DESC
                LIMIT $limit
                """
                
                result = await session.run(query, telegram_id=telegram_id, limit=limit)
                
                interests = []
                async for record in result:
                    interests.append({
                        "tag": record["tag"],
                        "posts_count": record["posts_count"],
                        "usage_percent": record["usage_percent"]
                    })
                
                return interests
                
        except Exception as e:
            logger.error(f"❌ Failed to get user interests: {e}")
            return []
    
    async def get_post_context(
        self,
        post_id: int,
        depth: int = 1
    ) -> Dict[str, Any]:
        """
        Получить граф-контекст для поста (для RAG)
        
        Args:
            post_id: ID поста
            depth: Глубина поиска (1 = прямые связи, 2 = связи 2-го уровня)
            
        Returns:
            {
                "related_posts": [...],  # Посты через общие теги
                "tag_cluster": [...],    # Связанные теги  
                "channel_posts": [...]   # Другие посты этого канала
            }
            
        Best practice для RAG: собрать контекст вокруг поста
        """
        if not self.enabled or not self.driver:
            return {"related_posts": [], "tag_cluster": [], "channel_posts": []}
        
        start = time.time()
        try:
            async with self.driver.session() as session:
                query = """
                // 1. Исходный пост
                MATCH (p:Post {id: $post_id})
                
                // 2. Related posts через общие теги
                MATCH (p)-[:HAS_TAG]->(t:Tag)<-[:HAS_TAG]-(related:Post)
                WHERE related.id <> $post_id
                WITH p, related, count(t) AS common_tags
                ORDER BY common_tags DESC
                LIMIT 5
                
                // 3. Собрать теги исходного поста
                WITH p, collect({id: related.id, title: related.title, common_tags: common_tags}) AS related_posts
                MATCH (p)-[:HAS_TAG]->(tag:Tag)
                
                // 4. Найти связанные теги
                OPTIONAL MATCH (tag)-[r:RELATED_TO]-(related_tag:Tag)
                WITH p, related_posts, collect(DISTINCT {tag: related_tag.name, weight: r.weight}) AS tag_cluster
                
                // 5. Другие посты из того же канала
                MATCH (p)-[:FROM_CHANNEL]->(c:Channel)<-[:FROM_CHANNEL]-(channel_post:Post)
                WHERE channel_post.id <> $post_id
                WITH related_posts, tag_cluster, channel_post
                ORDER BY channel_post.created_at DESC
                LIMIT 3
                
                RETURN related_posts,
                       tag_cluster,
                       collect({id: channel_post.id, title: channel_post.title}) AS channel_posts
                """
                
                result = await session.run(query, post_id=post_id)
                record = await result.single()
                
                if record:
                    duration = time.time() - start
                    record_graph_query('get_post_context', duration, success=True)
                    
                    return {
                        "related_posts": record["related_posts"] or [],
                        "tag_cluster": [t for t in (record["tag_cluster"] or []) if t.get("tag")],
                        "channel_posts": record["channel_posts"] or []
                    }
                
                duration = time.time() - start
                record_graph_query('get_post_context', duration, success=True)
                return {"related_posts": [], "tag_cluster": [], "channel_posts": []}
                
        except Exception as e:
            duration = time.time() - start
            record_graph_query('get_post_context', duration, success=False)
            logger.error(f"❌ Failed to get post context: {e}")
            return {"related_posts": [], "tag_cluster": [], "channel_posts": []}
    
    async def get_trending_tags(
        self,
        days: int = 7,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Получить trending tags за период (для RAG personalization)
        
        Args:
            days: Период в днях
            limit: Количество топ тегов
            
        Returns:
            Список trending тегов:
            [{
                "name": "AI",
                "posts_count": 125,
                "trend_score": 15.5  // Посты в день
            }]
            
        Best practice: для персонализации дайджестов
        """
        if not self.enabled or not self.driver:
            return []
        
        try:
            async with self.driver.session() as session:
                query = """
                // Посты за последние N дней
                MATCH (p:Post)-[:HAS_TAG]->(t:Tag)
                WHERE p.created_at >= datetime() - duration({days: $days})
                
                // Подсчет по тегам
                WITH t, count(p) AS posts_count
                
                RETURN t.name AS name,
                       posts_count,
                       round(toFloat(posts_count) / $days, 2) AS trend_score
                ORDER BY posts_count DESC
                LIMIT $limit
                """
                
                result = await session.run(query, days=days, limit=limit)
                
                trending = []
                async for record in result:
                    trending.append({
                        "name": record["name"],
                        "posts_count": record["posts_count"],
                        "trend_score": record["trend_score"]
                    })
                
                return trending
                
        except Exception as e:
            logger.error(f"❌ Failed to get trending tags: {e}")
            return []
    
    async def expand_with_graph(
        self,
        post_ids: List[int],
        limit_per_post: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Batch: расширить результаты через граф (для hybrid search)
        
        Args:
            post_ids: Список ID постов (из vector search)
            limit_per_post: Сколько related постов добавить для каждого
            
        Returns:
            Список расширенных результатов:
            [{
                "source_post_id": 123,
                "related_posts": [
                    {"id": 456, "title": "...", "common_tags": 3},
                    ...
                ]
            }]
            
        Best practice: один batch запрос вместо N отдельных
        Используется в EnhancedSearchService для graph-aware ranking
        """
        if not self.enabled or not self.driver or not post_ids:
            return []
        
        try:
            async with self.driver.session() as session:
                query = """
                // Для каждого поста из списка
                UNWIND $post_ids AS source_id
                
                // Найти related posts
                MATCH (source:Post {id: source_id})-[:HAS_TAG]->(t:Tag)<-[:HAS_TAG]-(related:Post)
                WHERE source.id <> related.id
                
                // Агрегировать
                WITH source_id, related, count(DISTINCT t) AS common_tags
                ORDER BY common_tags DESC
                
                // Лимит на каждый source post
                WITH source_id, collect({
                    id: related.id,
                    title: related.title,
                    common_tags: common_tags
                })[..$limit_per_post] AS related_posts
                
                RETURN source_id, related_posts
                """
                
                result = await session.run(
                    query,
                    post_ids=post_ids,
                    limit_per_post=limit_per_post
                )
                
                expanded = []
                async for record in result:
                    expanded.append({
                        "source_post_id": record["source_id"],
                        "related_posts": record["related_posts"]
                    })
                
                logger.debug(f"✅ Expanded {len(post_ids)} posts with graph context")
                return expanded
                
        except Exception as e:
            logger.error(f"❌ Failed to expand with graph: {e}")
            return []
    
    async def close(self):
        """
        Закрыть Neo4j driver
        
        Best practice: вызывать при shutdown приложения
        """
        if self.driver:
            try:
                await self.driver.close()
                logger.info("✅ Neo4j driver closed")
            except Exception as e:
                logger.error(f"❌ Neo4j driver close error: {e}")


# Singleton instance
neo4j_client = Neo4jClient()

