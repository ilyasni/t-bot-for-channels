# 🔐 Service Credentials

> **⚠️ ВАЖНО:** Храните этот файл в безопасном месте! Добавьте в `.gitignore` перед коммитом.

---

## 🌐 External Services (доступны через Caddy)

### n8n - Workflow Automation

- **Host:** https://n8n.produman.studio
- **User:** _(настраивается при первом запуске)_
- **Password:** _(настраивается при первом запуске)_

---

### Flowise - LLM Apps Builder

- **Host:** https://flowise.produman.studio
- **User:** `hello@ilyasni.com`
- **Password:**
  ```
  Tiko0tGSrYf1UTgOmBQEFgqD1yG5IgMC
  ```

---

### Supabase - Backend as a Service

- **External Host:** https://supabase.produman.studio
- **Studio User:** `hello@ilyasni.com`
- **Studio Password:**
  ```
  QrrzcZn1eepqlBEhOuP5d9f9FU6cUQuz
  ```
- **Internal API Gateway:** `http://supabase-kong:8000` (from containers)
- **Service Role Secret (JWT):**
  ```
  eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoic2VydmljZV9yb2xlIiwiaXNzIjoic3VwYWJhc2UiLCJpYXQiOjE3NTQxNjM0MjksImV4cCI6MjA2OTUyMzQyOX0.-IO9m8kTpGSyEP7YVDqv2RiD0K5FeX3eKvmUf7Tx6_4
  ```

---

### Searxng - Metasearch Engine

- **Host:** https://searxng.produman.studio
- **User:** `hello@ilyasni.com`
- **Password:**
  ```
  B5Hp8jfp7sjDnb4XwRRzPo54RYETVOhX
  ```

---

### Qdrant - Vector Database

- **External Host:** https://qdrant.produman.studio
- **API Key:**
  ```
  HY56smNEHTbE2ogKJEl6qHAGabP2eFycteeVkvKfdTZ7uoI7
  ```
- **Internal REST API:** `http://qdrant:6333` (from containers)

---

## 🔒 Internal Services (доступны только из Docker network)

### Crawl4AI - Web Scraper

- **Internal Access:** `http://crawl4ai:11235`
- **Auth:** _(не требуется для internal access)_
- **Note:** Не exposed наружу по умолчанию

---

### Redis (Valkey) - Cache & Session Store

- **Internal Host:** `redis`
- **Internal Port:** `6379`
- **Password:** `LOCALONLYREDIS` _(default, если не задано в .env)_
- **Note:** Для internal коммуникации, не exposed наружу

---

### Ollama - Local LLM Runtime

- **Internal Access:** `http://ollama:11434`
- **Profile:** `cpu` | `gpu-nvidia` | `gpu-amd` _(выбирается при установке)_
- **Note:** Используется из n8n, Open WebUI

---

## 🗄️ Database

### Standalone PostgreSQL

> Используется для: n8n, Langfuse, и других сервисов  
> **Отдельный** от встроенного PostgreSQL в Supabase

- **Host:** `db` (internal) или `localhost:5432` (from host)
- **Port:** `5432`
- **Database:** `postgres`
- **User:** `postgres`
- **Password:**
  ```
  xiNmSysbbcqTOWT4eb1KkQtM2fb8X7Ms
  ```

---

## 📋 Quick Reference Table

| Service | External URL | Internal URL | Auth Required |
|---------|-------------|--------------|---------------|
| **n8n** | n8n.produman.studio | - | ✅ First-run setup |
| **Flowise** | flowise.produman.studio | - | ✅ User/Pass |
| **Supabase** | supabase.produman.studio | supabase-kong:8000 | ✅ User/Pass + JWT |
| **Searxng** | searxng.produman.studio | - | ✅ User/Pass |
| **Qdrant** | qdrant.produman.studio | qdrant:6333 | ✅ API Key |
| **Crawl4AI** | - | crawl4ai:11235 | ❌ Internal only |
| **Redis** | - | redis:6379 | ⚠️ Password optional |
| **Ollama** | - | ollama:11434 | ❌ Internal only |
| **PostgreSQL** | localhost:5432 | db:5432 | ✅ User/Pass |

---

## 🚀 Next Steps

1. **Сохраните credentials** в password manager (1Password, Bitwarden, etc.)

2. **Проверьте доступность сервисов:**
   ```bash
   docker compose ps
   ```

3. **Первичная настройка n8n:**
   - Откройте https://n8n.produman.studio
   - Создайте admin аккаунт при первом запуске

4. **Обновление сервисов:**
   ```bash
   bash ./scripts/update.sh
   ```

5. **Добавьте этот файл в `.gitignore`:**
   ```bash
   echo "docs/SERVICE_CREDENTIALS.md" >> .gitignore
   ```

---

## 🔄 Updates

Для обновления сервисов без потери данных:

```bash
cd /home/ilyasni/n8n-server/n8n-installer
bash ./scripts/update.sh
```

---

**Generated:** October 14, 2025  
**Last Updated:** _(обновите при изменении credentials)_

