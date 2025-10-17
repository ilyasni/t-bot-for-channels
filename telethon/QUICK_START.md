# 🚀 Quick Start - Neo4j + RAG Hybrid Integration

**Статус:** ✅ Реализация complete  
**Дата:** 14 октября 2025

---

## ✅ Что сделано

**11 компонентов реализовано:**

1. ✅ Neo4j Client Extensions (`graph/neo4j_client.py`)
2. ✅ Enhanced Search Service (`rag_service/enhanced_search.py`)
3. ✅ AI Digest Graph Integration (`rag_service/ai_digest_generator.py`)
4. ✅ Redis Cache Layer (`rag_service/graph_cache.py`)
5. ✅ Data Retention Service (`maintenance/data_retention.py`)
6. ✅ Cleanup Scheduler (`maintenance/cleanup_scheduler.py`)
7. ✅ Main.py Integration (startup/shutdown hooks)
8. ✅ Admin API Endpoints (`/admin/cleanup`, `/admin/cleanup/status`)
9. ✅ Documentation (3 файла)
10. ✅ Graceful Degradation (fallbacks)
11. ✅ Error Handling (try-except везде)

---

## 🎯 Следующие шаги

### Шаг 1: Добавить environment variables

```bash
# Редактировать .env
nano /home/ilyasni/n8n-server/n8n-installer/.env
```

**Добавить в конец:**

```bash
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
# Admin API (NEW)
# ========================================
# Генерация: openssl rand -hex 32
ADMIN_API_KEY=put_your_secure_key_here
```

**Генерация ADMIN_API_KEY:**

```bash
# Linux/Mac:
openssl rand -hex 32

# OR Python:
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

### Шаг 2: Rebuild telethon

```bash
cd /home/ilyasni/n8n-server/n8n-installer
docker compose up -d --build telethon
```

**Ожидаемое время:** 2-3 минуты

---

### Шаг 3: Проверить логи

```bash
# Проверить startup
docker logs telethon --tail 100 | grep -E "(EnhancedSearch|GraphCache|DataRetention|Cleanup)"
```

**Ожидаемый вывод:**

```
✅ EnhancedSearchService initialized (Neo4j: True)
✅ GraphCache initialized (Redis: redis:6379)
🗑️ DataRetentionService initialized (retention: 120 days)
📅 CleanupScheduler initialized (enabled: True)
✅ Cleanup scheduler started
```

**Если есть ошибки:**

```bash
# Полные логи
docker logs telethon --tail 200

# Проверить Neo4j
docker logs neo4j --tail 50

# Проверить Redis
docker logs redis --tail 50
```

---

### Шаг 4: Health Checks

```bash
# 1. Neo4j integration
curl http://localhost:8010/graph/health

# Ожидается:
# {"neo4j_enabled":true,"neo4j_connected":true}

# 2. Cleanup scheduler status
curl -X GET http://localhost:8010/admin/cleanup/status \
  -H "api-key: YOUR_ADMIN_API_KEY"

# Ожидается:
# {
#   "scheduler_enabled": true,
#   "scheduler_running": true,
#   "retention_days": 120,
#   "schedule": "0 3 * * *",
#   "next_run": "2025-10-15T03:00:00+00:00"
# }
```

---

### Шаг 5: Тестирование (DRY RUN)

```bash
# Dry run cleanup (без удаления)
curl -X POST "http://localhost:8010/admin/cleanup?dry_run=true" \
  -H "api-key: YOUR_ADMIN_API_KEY"

# Ожидается:
# {
#   "status": "success",
#   "dry_run": true,
#   "deleted_count": {
#     "postgres": 150,
#     "neo4j": 150,
#     "qdrant": 150
#   },
#   "errors": []
# }
```

**Интерпретация:**
- `deleted_count` показывает, сколько **будет** удалено
- `dry_run: true` = НЕ удалено (только подсчет)
- `errors: []` = нет ошибок

---

## 🧪 Testing Hybrid Search

### Test 1: Basic Hybrid Search

```python
# В Python console или Jupyter
from rag_service.enhanced_search import enhanced_search_service

# Test hybrid search
results = await enhanced_search_service.search_with_graph_context(
    query="AI новости",
    user_id=1,  # Замените на реальный user_id
    limit=10
)

print(f"Результатов: {len(results)}")
print(f"Первый result: {results[0]}")

# Проверить combined_score
assert 'combined_score' in results[0], "Combined score missing!"
assert 'vector_score' in results[0], "Vector score missing!"
assert 'graph_score' in results[0], "Graph score missing!"

print("✅ Hybrid search работает!")
```

### Test 2: AI Digest with Graph Topics

```python
from rag_service.ai_digest_generator import ai_digest_generator

# Test graph integration
topics = await ai_digest_generator._get_user_interests(
    user_id=1,
    preferred_topics=["криптовалюты"]
)

print(f"Topics найдено: {len(topics)}")
print(f"Topics: {topics[:10]}")

# Ожидается 8-10+ topics (manual + history + graph + trending)
assert len(topics) >= 5, "Not enough topics!"

print("✅ AI Digest graph integration работает!")
```

### Test 3: Cache Hit Rate

```bash
# Первый запрос (cache miss)
time curl http://localhost:8010/graph/user/123/interests

# Второй запрос (cache hit, должен быть быстрее)
time curl http://localhost:8010/graph/user/123/interests

# Проверить Redis
docker exec -it redis redis-cli

> KEYS graph:*
# Должны появиться cache keys

> TTL graph:interests:123
# (integer) ~3600 (1 час)

> EXIT
```

---

## 📊 Мониторинг

### Метрики для отслеживания

```bash
# Prometheus metrics endpoint
curl http://localhost:8010/metrics | grep graph

# TODO: Добавить custom metrics:
# - hybrid_search_duration_seconds
# - graph_cache_hit_rate
# - data_cleanup_total
```

### Логи

```bash
# Real-time logs
docker logs -f telethon | grep -E "(Hybrid|Graph|Cleanup)"

# Ошибки
docker logs telethon | grep -i error | tail -50

# Performance
docker logs telethon | grep -E "(latency|duration|ms)" | tail -50
```

---

## 🔧 Troubleshooting

### Проблема: Neo4j не подключается

```bash
# 1. Проверить контейнер
docker ps | grep neo4j

# 2. Проверить логи
docker logs neo4j --tail 50

# 3. Проверить пароль
docker exec neo4j cypher-shell -u neo4j -p "YOUR_PASSWORD" "RETURN 1"

# 4. Если забыли пароль:
docker exec neo4j cypher-shell -u neo4j -p "neo4j" \
  "ALTER USER neo4j SET PASSWORD 'NewPassword123'"

# 5. Обновить .env
nano .env
# NEO4J_PASSWORD=NewPassword123

# 6. Rebuild
docker compose up -d --build telethon
```

### Проблема: Cleanup не работает

```bash
# 1. Проверить scheduler
curl http://localhost:8010/admin/cleanup/status \
  -H "api-key: YOUR_KEY"

# 2. Если scheduler_enabled=false:
nano .env
# CLEANUP_ENABLED=true

# 3. Rebuild
docker compose up -d --build telethon

# 4. Manual trigger
curl -X POST "http://localhost:8010/admin/cleanup?dry_run=false" \
  -H "api-key: YOUR_KEY"
```

### Проблема: Cache не работает

```bash
# 1. Проверить Redis
docker ps | grep redis
docker logs redis --tail 50

# 2. Проверить keys
docker exec redis redis-cli KEYS "graph:*"

# 3. Если пусто:
# - Сделать несколько запросов к graph API
# - Проверить опять

# 4. Если всё ещё пусто:
docker logs telethon | grep -i "GraphCache"
# Смотреть на ошибки
```

### Проблема: Hybrid search медленный

```bash
# 1. Проверить latency
time curl -X POST http://localhost:8010/rag/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "user_id": 1}'

# 2. Если > 500ms:
# - Проверить cache hit rate
# - Проверить Neo4j query performance
# - Уменьшить GRAPH_WEIGHT в .env

# 3. Снизить graph weight:
nano .env
# GRAPH_WEIGHT=0.2  # Было 0.3

docker compose up -d --build telethon
```

---

## ⏭️ Следующие шаги (опционально)

### Phase 2: Query Expansion

```bash
# Создать query_expander.py (см. plan)
# Интегрировать в enhanced_search.py
# Тестировать улучшение Precision@10
```

### Phase 3: Metrics & Monitoring

```bash
# Добавить Prometheus metrics
# Создать Grafana dashboard
# Настроить alerts
```

### Phase 4: A/B Testing

```bash
# Feature flag в .env
USE_HYBRID_SEARCH=true

# 10% users → hybrid
# 90% users → baseline
# Сравнить метрики
```

---

## 📚 Полная документация

- **NEO4J_RAG_INTEGRATION.md** - детальная документация
- **ENV_UPDATES.md** - все environment variables
- **IMPLEMENTATION_COMPLETE.md** - deployment план

---

## ✅ Success Criteria

После выполнения всех шагов:

- [ ] Neo4j health check возвращает `connected: true`
- [ ] Cleanup scheduler запущен (`scheduler_running: true`)
- [ ] Dry run cleanup работает без ошибок
- [ ] Hybrid search возвращает `combined_score`
- [ ] AI digest использует graph topics
- [ ] Cache keys появляются в Redis
- [ ] Логи без критических ошибок

---

**Время выполнения:** 15-20 минут  
**Сложность:** Средняя  
**Rollback:** Установить `CLEANUP_ENABLED=false`, `ENABLE_GRAPH_EXPANSION=false`

**Готово к запуску! 🚀**

