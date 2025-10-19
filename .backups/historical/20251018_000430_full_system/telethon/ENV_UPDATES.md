# Environment Variables - Neo4j RAG Integration

Добавить в `.env` файл для полной функциональности Neo4j + RAG hybrid интеграции.

---

## Data Retention (обязательные)

```bash
# Data Retention Policy
DATA_RETENTION_DAYS=120        # Retention period в днях (4 месяца)
CLEANUP_ENABLED=true           # Включить автоматическую очистку
CLEANUP_SCHEDULE="0 3 * * *"   # Cron schedule (default: 3:00 AM daily)
```

**Описание:**
- `DATA_RETENTION_DAYS` - посты старше этого периода будут удалены
- `CLEANUP_ENABLED` - вкл/выкл автоматический cleanup scheduler
- `CLEANUP_SCHEDULE` - расписание в cron формате

---

## Graph-Enhanced Search (опциональные)

```bash
# Hybrid Search Configuration
GRAPH_WEIGHT=0.3               # Вес graph score (0.0-1.0, default: 0.3)
ENABLE_GRAPH_EXPANSION=true    # Расширять результаты через граф (default: true)
```

**Описание:**
- `GRAPH_WEIGHT` - как сильно влияет граф на ranking (0.3 = 30%)
- `ENABLE_GRAPH_EXPANSION` - вкл/выкл graph context expansion

---

## Cache Configuration (опциональные)

```bash
# Redis Cache for Graph Queries
GRAPH_CACHE_ENABLED=true       # Включить кеширование (default: true)
GRAPH_CACHE_USER_INTERESTS_TTL=3600      # 1 hour
GRAPH_CACHE_TRENDING_TTL=21600           # 6 hours
GRAPH_CACHE_POST_CONTEXT_TTL=86400       # 24 hours
```

**Описание:**
- `GRAPH_CACHE_*_TTL` - время жизни cache ключей в секундах

---

## Admin API (для manual cleanup)

```bash
# Admin API Key
ADMIN_API_KEY=your_secure_random_key_here
```

**Описание:**
- Используется для защиты admin endpoints (`/admin/cleanup`)

**Генерация:**
```bash
# Linux/Mac:
openssl rand -hex 32

# Python:
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Полный пример .env

```bash
# ========================================
# Neo4j Configuration (уже есть)
# ========================================
NEO4J_ENABLED=true
NEO4J_URI=bolt://neo4j:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=YourSecurePassword123
NEO4J_AUTO_INDEX=true

# ========================================
# Data Retention (NEW)
# ========================================
DATA_RETENTION_DAYS=120
CLEANUP_ENABLED=true
CLEANUP_SCHEDULE="0 3 * * *"

# ========================================
# Hybrid Search (NEW, опционально)
# ========================================
GRAPH_WEIGHT=0.3
ENABLE_GRAPH_EXPANSION=true

# ========================================
# Cache Configuration (NEW, опционально)
# ========================================
GRAPH_CACHE_ENABLED=true
GRAPH_CACHE_USER_INTERESTS_TTL=3600
GRAPH_CACHE_TRENDING_TTL=21600
GRAPH_CACHE_POST_CONTEXT_TTL=86400

# ========================================
# Admin API (NEW)
# ========================================
ADMIN_API_KEY=generated_secure_key_here
```

---

## Применение изменений

1. **Скопировать в .env:**
   ```bash
   nano /home/ilyasni/n8n-server/n8n-installer/.env
   # Добавить новые переменные
   ```

2. **Rebuild telethon:**
   ```bash
   cd /home/ilyasni/n8n-server/n8n-installer
   docker compose up -d --build telethon
   ```

3. **Проверить логи:**
   ```bash
   docker logs telethon | grep -E "(DataRetention|EnhancedSearch|GraphCache)"
   
   # Ожидаемые сообщения:
   # ✅ DataRetentionService initialized (retention: 120 days)
   # ✅ EnhancedSearchService initialized (Neo4j: True)
   # ✅ GraphCache initialized (Redis: redis:6379)
   # 📅 CleanupScheduler initialized (enabled: true)
   ```

---

## Проверка конфигурации

### 1. Data Retention

```bash
# Dry run cleanup
curl -X POST http://localhost:8010/admin/cleanup?dry_run=true \
  -H "api-key: your_admin_key"

# Ожидаемый результат:
# {
#   "deleted_count": {"postgres": X, "neo4j": Y, "qdrant": Z},
#   "dry_run": true,
#   "errors": []
# }
```

### 2. Hybrid Search

```python
# В Python console:
from rag_service.enhanced_search import enhanced_search_service

results = await enhanced_search_service.search_with_graph_context(
    query="test",
    user_id=1,
    limit=5
)

print(f"Results: {len(results)}")
print(f"First result score: {results[0].get('combined_score')}")
# Должен быть combined_score (вместо просто score)
```

### 3. Cache

```bash
# Проверить Redis keys
docker exec -it redis redis-cli

> KEYS graph:*
# Должны появиться:
# 1) "graph:interests:123"
# 2) "graph:trending:tags:d7"
# ...

> TTL graph:interests:123
# (integer) 3598  # Примерно 1 час
```

---

## Rollback

Если нужно отключить новую функциональность:

```bash
# В .env:
CLEANUP_ENABLED=false
ENABLE_GRAPH_EXPANSION=false
GRAPH_CACHE_ENABLED=false

# Rebuild
docker compose up -d --build telethon
```

Система вернется к baseline функциональности (только Qdrant, без графа).

