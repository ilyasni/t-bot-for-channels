# Порядок запуска контейнеров - RAG System

**Дата:** 11 октября 2025  
**Статус:** ✅ Настроено и работает

## Порядок запуска сервисов

### 1. Базовые сервисы (запускаются первыми)

#### Supabase (если включен профиль)
```bash
# Запуск через start_services.py
# Порядок внутри Supabase:
1. supabase-db (PostgreSQL)
2. supabase-auth, supabase-rest, supabase-storage...
3. supabase-kong (API Gateway)
```

**Статус:** ✅ Up 4 days (healthy)

#### Базы данных
- `postgres` - PostgreSQL (для n8n, langfuse)
- `redis` - Redis (для n8n workers, langfuse)
- `clickhouse` - ClickHouse (для langfuse analytics)

### 2. Сетевая инфраструктура

#### Сети Docker
- `n8n-installer_default` - основная сеть
- `localai_default` - сеть для AI сервисов (external)

**Критично:** Сервисы должны быть в правильных сетях для общения!

### 3. AI Infrastructure

#### Qdrant (векторная БД) ✅
```yaml
qdrant:
  profiles: ["qdrant"]
  networks:
    - default           # для общения с основными сервисами
    - localai_default   # для общения с AI сервисами
```

**Порт:** 6333 (internal)  
**Статус:** ✅ Up, healthy

#### Ollama (опционально)
```yaml
ollama:
  profiles: ["cpu", "gpu-nvidia", "gpu-amd"]
```

### 4. Telegram Parser Stack

#### 4.1. GigaChat Proxy (запускается рано)
```yaml
gpt2giga-proxy:
  networks:
    - localai_default
```

**Порт:** 8090  
**Зависимости:** Нет  
**Статус:** ✅ Up 9 minutes

#### 4.2. Telethon Parser
```yaml
telethon:
  networks:
    - localai_default
  depends_on:
    # Нет явных зависимостей
```

**Порты:** 8001 (auth), 8010 (API)  
**Статус:** ✅ Up 9 minutes

#### 4.3. Telethon Bot (standalone)
```yaml
telethon-bot:
  networks:
    - localai_default
```

**Статус:** ✅ Up 9 minutes

#### 4.4. RAG Service
```yaml
rag-service:
  networks:
    - default           # для доступа к Qdrant
    - localai_default   # для общения с telethon, gpt2giga
  depends_on:
    telethon:
      condition: service_started
    gpt2giga-proxy:
      condition: service_started
```

**Порт:** 8020  
**Зависимости:** telethon, gpt2giga-proxy  
**Статус:** ✅ Up 6 minutes, healthy

### 5. n8n Stack

```yaml
n8n-import:
  depends_on:
    postgres:
      condition: service_healthy

n8n:
  depends_on:
    n8n-import:
      condition: service_completed_successfully

n8n-worker:
  depends_on:
    n8n:
      condition: service_started
    redis:
      condition: service_healthy
    postgres:
      condition: service_healthy
  deploy:
    replicas: ${N8N_WORKER_COUNT:-1}
```

**Порт:** 5678  
**Статус:** ✅ Up 4 days

### 6. Reverse Proxy

#### Caddy
```yaml
caddy:
  volumes:
    - ./Caddyfile:/etc/caddy/Caddyfile:ro
    - ./caddy-addon:/etc/caddy/addons:ro
```

**Порты:** 80, 443, 7687  
**Статус:** ✅ Up, обновлен с RAG-конфигурацией

**Новое в Caddyfile:**
```
# RAG Service API
{$RAG_SERVICE_HOSTNAME:rag.produman.studio} {
    reverse_proxy rag-service:8020
}
```

## Правильный порядок запуска

### При первом старте системы:

```bash
# 1. Базовые сервисы (БД, кеш)
docker compose up -d postgres redis clickhouse

# 2. Supabase (если нужен)
docker compose --profile supabase up -d

# 3. AI infrastructure  
docker compose --profile qdrant up -d qdrant

# 4. Telegram Parser Stack
docker compose up -d gpt2giga-proxy telethon telethon-bot

# 5. RAG Service (зависит от telethon и gpt2giga)
docker compose up -d rag-service

# 6. n8n (зависит от postgres)
docker compose --profile n8n up -d

# 7. Caddy (reverse proxy)
docker compose up -d caddy
```

### Через start_services.py (рекомендуется):

```bash
python start_services.py
```

Скрипт автоматически:
1. Запускает Supabase первым (если включен)
2. Ждет инициализации
3. Запускает остальные сервисы в правильном порядке

## Критичные зависимости

### RAG-сервис требует:

**Обязательные:**
- ✅ `telethon` - для доступа к БД через shared volumes
- ✅ `gpt2giga-proxy` - для embeddings

**Опциональные:**
- ⚠️ `qdrant` - для векторного поиска (работает, но не обязателен)
- ℹ️ Без Qdrant: сервис запустится, но поиск не будет работать

### Сетевая конфигурация

**Критично для RAG:**
```yaml
rag-service:
  networks:
    - default           # ← Для доступа к Qdrant
    - localai_default   # ← Для telethon, gpt2giga
```

**Критично для Qdrant:**
```yaml
qdrant:
  networks:
    - default           # ← Для n8n, flowise
    - localai_default   # ← Для RAG-service
```

## Текущий статус контейнеров

```bash
$ docker ps --format "table {{.Names}}\t{{.Status}}"

NAMES                STATUS
rag-service          Up 6 minutes   ✅ HEALTHY
telethon             Up 9 minutes   ✅
telethon-bot         Up 9 minutes   ✅
gpt2giga-proxy       Up 9 minutes   ✅
qdrant               Up 22 seconds  ✅
supabase-db          Up 4 days      ✅ (healthy)
n8n                  Up 4 days      ✅
n8n-worker-1         Up 4 days      ✅
caddy                Up 41 seconds  ✅
```

## Health Check результаты

### RAG Service
```json
{
  "status": "healthy",
  "qdrant_connected": true,    ← ✅ ПОДКЛЮЧЕН!
  "gigachat_available": true,
  "openrouter_available": true,
  "version": "0.1.0"
}
```

## Проблемы и решения

### Проблема 1: Qdrant не подключается
**Причина:** RAG-сервис и Qdrant в разных сетях

**Решение:** Добавлены обе сети для Qdrant и RAG:
```yaml
networks:
  - default
  - localai_default
```

### Проблема 2: ModuleNotFoundError
**Причина:** database.py не в PYTHON PATH

**Решение:** Volumes mapping в docker-compose:
```yaml
volumes:
  - ./telethon/database.py:/app/database.py
  - ./telethon/models.py:/app/models.py
  - ./telethon/crypto_utils.py:/app/crypto_utils.py
```

### Проблема 3: Конфликт имен (models.py, qdrant_client.py)
**Решение:** Переименованы файлы:
- `rag_service/models.py` → `schemas.py`
- `rag_service/qdrant_client.py` → `vector_db.py`

### Проблема 4: No space left on device
**Решение:** Упрощены requirements.txt:
- Убрали torch (~3GB)
- Убрали sentence-transformers
- Используем только GigaChat для embeddings

## Caddy конфигурация

### Главный Caddyfile
```
# RAG Service API
{$RAG_SERVICE_HOSTNAME:rag.produman.studio} {
    reverse_proxy rag-service:8020
}
```

### Переменные окружения Caddy
Добавить в .env:
```bash
RAG_SERVICE_HOSTNAME=rag.produman.studio
```

## API доступ

### Локально (внутри Docker)
```bash
http://rag-service:8020
```

### Через порт (с хоста)
```bash
http://localhost:8020
```

### Через Caddy (production)
```bash
https://rag.produman.studio
```

## Проверка работы системы

```bash
# 1. Health check
curl http://localhost:8020/health

# 2. API документация
open http://localhost:8020/docs

# 3. Проверка сетей
docker network inspect localai_default | grep -A 3 "rag-service\|qdrant\|telethon"

# 4. Логи всех сервисов
docker logs rag-service --tail 20
docker logs telethon --tail 20
docker logs gpt2giga-proxy --tail 20
docker logs qdrant --tail 20
```

## Порты сервисов

```
Supabase:
  5432  - PostgreSQL (pooler)
  8000  - Kong API Gateway
  8443  - Kong HTTPS

n8n:
  5678  - n8n UI/API

Telegram Parser:
  8001  - telethon auth web
  8010  - telethon API

AI Services:
  8020  - RAG Service API  ← НОВЫЙ
  8090  - GigaChat proxy
  6333  - Qdrant (internal)

Monitoring:
  3000  - Grafana
  9090  - Prometheus
  4000  - Supabase Analytics

Caddy:
  80    - HTTP
  443   - HTTPS
  7687  - Neo4j Bolt
```

## Успешное развертывание! ✅

Все сервисы запущены и работают:
- ✅ RAG-сервис: healthy
- ✅ Qdrant: connected
- ✅ GigaChat: available
- ✅ OpenRouter: available
- ✅ Telethon: running
- ✅ Caddy: configured

**API Docs:** http://localhost:8020/docs  
**External URL:** https://rag.produman.studio (после настройки DNS)

