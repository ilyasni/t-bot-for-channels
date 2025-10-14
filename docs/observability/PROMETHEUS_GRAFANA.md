# Prometheus + Grafana - Metrics и Dashboards

Prometheus собирает метрики производительности, Grafana визуализирует их.

## 📊 Что измеряется

### RAG Service Metrics

**Latency (Histogram):**
- `rag_search_duration_seconds` - время поиска в Qdrant
  - Buckets: 50ms, 100ms, 200ms, 500ms, 1s, 2s
  - Labels: none
  
- `rag_embeddings_duration_seconds` - время генерации embeddings
  - Buckets: 100ms, 500ms, 1s, 2s, 5s
  - Labels: `provider` (gigachat, sentence-transformers)

**Errors (Counter):**
- `rag_query_errors_total` - ошибки RAG операций
  - Labels: `error_type` (embedding_failed, qdrant_timeout, gigachat_api_error, etc.)

### Parsing Metrics

**Queue (Gauge):**
- `bot_parsing_queue_size` - размер очереди парсинга

**Posts (Counter):**
- `bot_posts_parsed_total` - количество спарсенных постов
  - Labels: `user_id`

## 🚀 Quick Start

### 1. Проверить что Prometheus scraping работает

```bash
# Проверить /metrics endpoints
curl http://localhost:8000/metrics | grep rag_
curl http://localhost:8001/metrics | grep rag_

# Ожидаемый output:
# rag_search_duration_seconds_bucket{le="0.05"} 10
# rag_embeddings_duration_seconds_count{provider="gigachat"} 42
# bot_posts_parsed_total{user_id="123"} 290
```

### 2. Проверить Prometheus targets

```bash
# Открыть Prometheus UI
open https://prometheus.produman.studio

# Status → Targets
# Должны быть UP:
# ✅ telegram-bot (telethon:8000)
# ✅ rag-service (rag-service:8001)
```

### 3. Открыть Grafana dashboards

```bash
# Открыть Grafana UI
open https://grafana.produman.studio

# Должны автоматически загрузиться:
# ✅ Telegram Bot - RAG Performance
# ✅ Telegram Bot - Parsing Metrics
```

## 📈 Grafana Dashboards

### Dashboard 1: RAG Performance

**Panels:**

1. **RAG Search Latency (Qdrant)**
   - p50, p95, p99 percentiles
   - Показывает насколько быстро работает векторный поиск
   - Threshold: p99 < 500ms (good), < 1s (acceptable), > 1s (slow)

2. **Embeddings Generation Time**
   - По провайдерам (gigachat vs fallback)
   - p50, p95 percentiles
   - Threshold: p95 < 2s (good), < 5s (acceptable)

3. **RAG Errors Rate**
   - Stacked area chart по типам ошибок
   - Threshold: < 1 error/min (good), < 5 errors/min (warning)

4. **Vector Search QPS**
   - Queries per second
   - Stat panel с color thresholds

5. **Total RAG Queries**
   - Общее количество запросов
   - Counter

6. **Embeddings by Provider**
   - Pie chart: gigachat vs fallback
   - Помогает понять reliability GigaChat API

### Dashboard 2: Parsing Metrics

**Panels:**

1. **Parsing Queue Size**
   - Time series с thresholds (green < 5, yellow < 10, red >= 10)
   - Показывает загрузку парсера

2. **Posts Parsed Rate**
   - Posts/second
   - Помогает понять throughput

3. **Posts Parsed by User (Top 10)**
   - Top N пользователей по активности
   - Table legend с mean, last, sum

4. **Total Posts Parsed**
   - Stat panel - общее количество
   - Counter

5. **Average Queue Size**
   - Stat panel с thresholds
   - Помогает оценить среднюю нагрузку

6. **Posts Parsed per User**
   - Bar gauge - горизонтальный бар на каждого пользователя
   - Показывает распределение нагрузки

## 🔧 Как добавить свои метрики

### 1. Определить метрику в observability/metrics.py

```python
from prometheus_client import Counter, Histogram, Gauge

# Counter - для монотонных значений
my_counter = Counter(
    'my_operation_total',
    'Description of operation',
    ['label1', 'label2']  # Labels для группировки
)

# Histogram - для latency
my_histogram = Histogram(
    'my_operation_duration_seconds',
    'Operation latency',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0]
)

# Gauge - для текущих значений
my_gauge = Gauge(
    'my_current_value',
    'Current state'
)
```

### 2. Использовать в коде

```python
from observability.metrics import my_counter, my_histogram, my_gauge

# Counter
my_counter.labels(label1='value1', label2='value2').inc()

# Histogram
with my_histogram.time():
    await some_operation()

# Gauge
my_gauge.set(42)
my_gauge.inc()  # +1
my_gauge.dec()  # -1
```

### 3. Добавить в Grafana dashboard

```json
{
  "targets": [
    {
      "expr": "rate(my_operation_total[5m])",
      "legendFormat": "{{label1}} - {{label2}}"
    }
  ]
}
```

## 📊 PromQL Queries Examples

### RAG Performance

```promql
# Average search latency (p50)
histogram_quantile(0.50, sum(rate(rag_search_duration_seconds_bucket[5m])) by (le))

# p95 latency
histogram_quantile(0.95, sum(rate(rag_search_duration_seconds_bucket[5m])) by (le))

# Queries per second
sum(rate(rag_search_duration_seconds_count[5m]))

# Error rate
sum(rate(rag_query_errors_total[5m])) by (error_type)

# Embeddings by provider
sum(rag_embeddings_duration_seconds_count) by (provider)
```

### Parsing

```promql
# Current queue size
bot_parsing_queue_size

# Posts parsed rate
sum(rate(bot_posts_parsed_total[5m]))

# Top 10 users
topk(10, sum(rate(bot_posts_parsed_total[5m])) by (user_id))

# Total posts
sum(bot_posts_parsed_total)
```

## 🎯 Alerting Rules (TODO)

Можно добавить в `prometheus/alert_rules.yml`:

```yaml
groups:
  - name: telegram_bot_alerts
    rules:
      # RAG too slow
      - alert: RAGSearchSlow
        expr: histogram_quantile(0.95, rate(rag_search_duration_seconds_bucket[5m])) > 2
        for: 5m
        annotations:
          summary: "RAG search is slow (p95 > 2s)"
      
      # High error rate
      - alert: RAGHighErrorRate
        expr: sum(rate(rag_query_errors_total[5m])) > 0.1
        for: 5m
        annotations:
          summary: "RAG error rate > 0.1 errors/sec"
      
      # Parsing queue growing
      - alert: ParsingQueueGrowing
        expr: bot_parsing_queue_size > 10
        for: 10m
        annotations:
          summary: "Parsing queue > 10 for 10 minutes"
```

## 🐛 Troubleshooting

### Metrics не появляются

```bash
# 1. Проверить что /metrics endpoint работает
curl http://localhost:8000/metrics
curl http://localhost:8001/metrics

# 2. Проверить Prometheus targets
# https://prometheus.produman.studio/targets
# Должны быть UP

# 3. Проверить scrape config
docker exec prometheus cat /etc/prometheus/prometheus.yml | grep telegram-bot
```

### Grafana dashboards не загружаются

```bash
# 1. Проверить provisioning
docker exec grafana ls /etc/grafana/provisioning/dashboards/

# 2. Проверить dashboard files
docker exec grafana ls /var/lib/grafana/dashboards/

# 3. Проверить логи
docker logs grafana | grep -i dashboard
```

### Metrics показывают 0

```bash
# Возможно операции еще не выполнялись
# Попробовать:
# 1. Выполнить /ask команду в боте
# 2. Запустить парсинг вручную
# 3. Подождать 1-2 минуты для scraping
```

## 📚 Best Practices

### 1. Labels Usage

```python
# ✅ Good - meaningful labels
posts_parsed.labels(user_id=str(user_id)).inc(5)

# ❌ Bad - too many unique labels (cardinality explosion)
posts_parsed.labels(post_id=str(post_id)).inc()  # Миллионы уникальных значений!
```

### 2. Histogram Buckets

```python
# ✅ Good - покрывают диапазон от min до max
buckets=[0.05, 0.1, 0.2, 0.5, 1.0, 2.0]

# ❌ Bad - слишком мало buckets
buckets=[0.1, 1.0, 10.0]  # Не видно p50, p95
```

### 3. Metric Naming

```python
# ✅ Good - следует convention
rag_search_duration_seconds  # <subsystem>_<metric>_<unit>
bot_posts_parsed_total       # <app>_<metric>_total

# ❌ Bad
search_time  # Нет unit, нет subsystem
```

## 🔗 Полезные ссылки

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Prometheus Python Client](https://github.com/prometheus/client_python)
- [Grafana Documentation](https://grafana.com/docs/)
- [PromQL Cheatsheet](https://promlabs.com/promql-cheat-sheet/)
- [Context7 Prometheus Guide](/prometheus/client_python)

## 🎯 Next Steps

1. ✅ **Setup Metrics** (done)
2. ✅ **Setup Dashboards** (done)
3. ⏭️ **Add Alerting** - настроить уведомления
4. ⏭️ **Add more metrics** - команды бота, subscription usage
5. ⏭️ **Retention policy** - настроить хранение метрик

