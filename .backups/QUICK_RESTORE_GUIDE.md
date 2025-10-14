# 🚀 Quick Restore Guide

**Backup Directory:** `.backups/pre-update-20251014-004900/`

---

## ⚡ **После update.sh - Quick Actions:**

### **1. Сравнить что изменилось (1 минута)**

```bash
cd /home/ilyasni/n8n-server/n8n-installer

# One-liner для всех файлов
for f in docker-compose.yml Caddyfile; do 
  echo "=== $f ===" && diff -u .backups/pre-update-20251014-004900/$f $f | head -30; 
done
```

---

### **2. Восстановить критичные изменения (2 минуты)**

```bash
BACKUP=".backups/pre-update-20251014-004900"

# Вариант A: Полное восстановление docker-compose.yml
cp $BACKUP/docker-compose.yml docker-compose.yml

# Вариант B: Выборочно (рекомендуется)
# Откройте в редакторе и добавьте обратно:
nano docker-compose.yml

# Добавить в neo4j:
networks:
  - default
  - localai_default

# Добавить в prometheus:
networks:
  - default  
  - localai_default

# Убрать из caddy ports:
# - "7687:7687"  # ← Удалить эту строку
```

---

### **3. Проверить .env (3 минуты)**

```bash
BACKUP=".backups/pre-update-20251014-004900"

# Проверить добавленные переменные
comm -13 \
  <(grep "^[A-Z_]*=" $BACKUP/.env | cut -d= -f1 | sort) \
  <(grep "^[A-Z_]*=" .env | cut -d= -f1 | sort)

# Проверить удаленные переменные
comm -23 \
  <(grep "^[A-Z_]*=" $BACKUP/.env | cut -d= -f1 | sort) \
  <(grep "^[A-Z_]*=" .env | cut -d= -f1 | sort)

# Если NEO4J_HOSTNAME удалился - добавить:
grep NEO4J_HOSTNAME .env || echo "NEO4J_HOSTNAME=neo4j.produman.studio" >> .env

# Проверить COMPOSE_PROFILES
grep COMPOSE_PROFILES .env
```

---

### **4. Restart сервисы (5 минут)**

```bash
# После восстановления конфигов
docker compose up -d neo4j prometheus grafana

# Rebuild если нужно
docker compose up -d --build telethon rag-service
```

---

## 📋 **Critical Settings Checklist:**

```bash
# ✅ Проверьте после update.sh:

# 1. Neo4j networks
grep -A5 "neo4j:" docker-compose.yml | grep networks

# 2. Prometheus networks
grep -A5 "prometheus:" docker-compose.yml | grep networks

# 3. Caddy port 7687 УДАЛЕН
grep "7687" docker-compose.yml | grep caddy
# Expected: ПУСТО (порт не должен быть в caddy)

# 4. NEO4J_HOSTNAME
grep NEO4J_HOSTNAME .env

# 5. COMPOSE_PROFILES
grep COMPOSE_PROFILES .env
```

---

## 🔧 **Common Fixes:**

### **Fix 1: Neo4j не резолвится**

```yaml
# docker-compose.yml
neo4j:
  networks:    # ← ДОБАВИТЬ
    - default
    - localai_default
```

### **Fix 2: Prometheus не scrape metrics**

```yaml
# docker-compose.yml
prometheus:
  networks:    # ← ДОБАВИТЬ
    - default
    - localai_default
```

```yaml
# prometheus/prometheus.yml
- job_name: "telegram-bot"
  metrics_path: "/metrics/"   # ← С trailing slash!
  static_configs:
    - targets: ["telethon:8010"]
```

### **Fix 3: Caddy слушает порт 7687**

```yaml
# docker-compose.yml
caddy:
  ports:
    - "80:80"
    - "443:443"
    # - "7687:7687"  # ← УДАЛИТЬ эту строку
```

---

## 📝 **Restore Commands:**

```bash
BACKUP=".backups/pre-update-20251014-004900"

# Docker Compose
cp $BACKUP/docker-compose.yml docker-compose.yml

# Caddyfile
cp $BACKUP/Caddyfile Caddyfile

# Prometheus
cp $BACKUP/prometheus/prometheus.yml prometheus/prometheus.yml

# Grafana provisioning
cp -r $BACKUP/provisioning/* grafana/provisioning/

# telethon config
cp $BACKUP/telethon/.env telethon/.env
```

---

**Status:** ✅ Ready for update.sh

