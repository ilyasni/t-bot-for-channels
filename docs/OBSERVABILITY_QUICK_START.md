# 🚀 Observability Quick Start

**TL;DR:** Langfuse + Prometheus + Grafana интегрированы. Трейсится /ask, GigaChat, RAG search, parsing.

## ⚡ 3 минуты до запуска

### 1. Настроить credentials

```bash
# Редактировать .env
nano .env

# Добавить:
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-YOUR_KEY
LANGFUSE_SECRET_KEY=sk-lf-YOUR_KEY
LANGFUSE_HOST=https://langfuse.produman.studio

PROMETHEUS_METRICS_ENABLED=true
```

### 2. Rebuild контейнеры

```bash
cd /home/ilyasni/n8n-server/n8n-installer

docker compose up -d --build telethon rag-service
docker compose restart prometheus grafana
```

### 3. Verify

```bash
# Metrics endpoints
curl http://localhost:8000/metrics | grep rag_
curl http://localhost:8001/metrics | grep rag_

# Prometheus targets (должны быть UP)
open https://prometheus.produman.studio/targets

# Grafana dashboards (загрузятся автоматически)
open https://grafana.produman.studio
```

### 4. Test

```bash
# Выполнить /ask команду в боте
# → Langfuse: trace появится
# → Grafana: метрики обновятся
```

## 📊 Что измеряется

**Langfuse traces:**
- /ask команды (query, sources, latency)
- GigaChat embeddings (provider, dimensions)
- RAG search (results, latency)

**Prometheus metrics:**
- RAG search latency (p50, p95, p99)
- Embeddings duration (by provider)
- Parsing queue size
- Posts parsed (by user)

**Grafana dashboards:**
- Telegram Bot - RAG Performance
- Telegram Bot - Parsing Metrics

## 📚 Документация

- **Overview:** `/docs/observability/README.md`
- **Langfuse:** `/docs/observability/LANGFUSE_SETUP.md`
- **Prometheus:** `/docs/observability/PROMETHEUS_GRAFANA.md`
- **Full report:** `/OBSERVABILITY_INTEGRATION_COMPLETE.md`

## 🔗 Quick Links

- Langfuse UI: https://langfuse.produman.studio
- Prometheus UI: https://prometheus.produman.studio
- Grafana UI: https://grafana.produman.studio

---

**Status:** ✅ Ready to use!
