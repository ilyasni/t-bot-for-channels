# 📦 Backup перед update.sh

**Дата backup:** 2025-10-14 00:49 UTC  
**Причина:** Перед запуском update.sh для сравнения конфигураций

---

## 📁 **Что сохранено:**

### **Основная конфигурация:**

```
✅ docker-compose.yml          - Главный compose файл
✅ docker-compose.override.yml - Override для telethon, gpt2giga, rag-service
✅ .env                         - Credentials, settings, COMPOSE_PROFILES
✅ Caddyfile                    - Reverse proxy конфигурация
```

### **Специфические конфигурации:**

```
✅ prometheus/prometheus.yml   - Prometheus scrape config
✅ telethon/.env               - Telegram Bot настройки (включая NEO4J_*)
✅ grafana/provisioning/       - Grafana datasources и dashboards
```

---

## 🔄 **Как восстановить после update.sh:**

### **Шаг 1: Сравнить изменения**

```bash
cd /home/ilyasni/n8n-server/n8n-installer

# Сравнить docker-compose.yml
diff .backups/pre-update-20251014-004900/docker-compose.yml docker-compose.yml

# Сравнить .env
diff .backups/pre-update-20251014-004900/.env .env

# Сравнить Caddyfile
diff .backups/pre-update-20251014-004900/Caddyfile Caddyfile

# Сравнить prometheus config
diff .backups/pre-update-20251014-004900/prometheus/prometheus.yml prometheus/prometheus.yml
```

---

### **Шаг 2: Выборочное восстановление**

#### **Вариант A: Восстановить конкретный файл**

```bash
# Восстановить только docker-compose.yml
cp .backups/pre-update-20251014-004900/docker-compose.yml docker-compose.yml

# Восстановить Caddyfile
cp .backups/pre-update-20251014-004900/Caddyfile Caddyfile

# Восстановить prometheus config
cp .backups/pre-update-20251014-004900/prometheus/prometheus.yml prometheus/prometheus.yml
```

#### **Вариант B: Восстановить всё**

```bash
# Восстановить все конфиги
cp .backups/pre-update-20251014-004900/docker-compose.yml docker-compose.yml
cp .backups/pre-update-20251014-004900/docker-compose.override.yml docker-compose.override.yml
cp .backups/pre-update-20251014-004900/Caddyfile Caddyfile
cp .backups/pre-update-20251014-004900/prometheus/prometheus.yml prometheus/prometheus.yml

# .env НЕ восстанавливайте! (может быть обновлен с новыми переменными)
```

---

### **Шаг 3: Merge изменения вручную**

**Рекомендуется для критичных изменений:**

```bash
# 1. Посмотреть что изменилось в upstream
diff -u .backups/pre-update-20251014-004900/docker-compose.yml docker-compose.yml > docker-compose.diff

# 2. Проверить diff
cat docker-compose.diff

# 3. Применить только нужные изменения вручную
# Например, добавить обратно:
#   - neo4j networks
#   - prometheus networks
#   - убрать caddy port 7687
```

---

## 📊 **Критичные изменения для восстановления:**

### **docker-compose.yml:**

```yaml
# После update.sh проверьте и восстановите:

neo4j:
  networks:              # ← Добавить обратно
    - default
    - localai_default

prometheus:
  networks:              # ← Добавить обратно
    - default
    - localai_default

caddy:
  ports:
    - "80:80"
    - "443:443"
    # УДАЛИТЬ строку:
    # - "7687:7687"     # ← Убрать этот порт!
```

### **Caddyfile:**

```nginx
# Проверить что НЕТ блока:
# Neo4j Bolt Protocol (wss)
# https://{$NEO4J_HOSTNAME}:7687 {
#     reverse_proxy neo4j:7687
# }

# Должен быть ТОЛЬКО:
{$NEO4J_HOSTNAME} {
    reverse_proxy neo4j:7474
}
```

### **prometheus/prometheus.yml:**

```yaml
# Если вернулась старая версия, проверьте:

scrape_configs:
  - job_name: "telegram-bot"
    metrics_path: "/metrics/"   # ← С trailing slash!
    static_configs:
      - targets: ["telethon:8010"]

  - job_name: "rag-service"
    metrics_path: "/metrics/"   # ← С trailing slash!
    static_configs:
      - targets: ["rag-service:8020"]
```

---

## 🔍 **Quick Comparison Commands:**

```bash
# Сравнить все конфиги одной командой
for file in docker-compose.yml Caddyfile .env; do
  echo "=== $file ==="
  diff -u ".backups/pre-update-20251014-004900/$file" "$file" | head -20
  echo ""
done

# Найти отличия в .env (только ключи)
diff <(grep "^[A-Z]" .backups/pre-update-20251014-004900/.env | cut -d= -f1 | sort) \
     <(grep "^[A-Z]" .env | cut -d= -f1 | sort)

# Показать добавленные переменные
comm -13 \
  <(grep "^[A-Z]" .backups/pre-update-20251014-004900/.env | cut -d= -f1 | sort) \
  <(grep "^[A-Z]" .env | cut -d= -f1 | sort)
```

---

## ⚠️ **Важно: .env handling**

### **НЕ восстанавливайте .env целиком!**

**Почему:**
- update.sh может добавить НОВЫЕ переменные
- Старые credentials СОХРАНЯТСЯ автоматически
- Нужно MERGE, не replace

**Правильный подход:**

```bash
# 1. Проверить что добавилось
diff .backups/pre-update-20251014-004900/.env .env | grep "^>"

# 2. Проверить что удалилось
diff .backups/pre-update-20251014-004900/.env .env | grep "^<"

# 3. Если что-то важное удалилось - добавить вручную
# Например:
echo "NEO4J_HOSTNAME=neo4j.produman.studio" >> .env
```

---

## 🎯 **Post-Update Checklist:**

```bash
# После update.sh проверьте:

# 1. COMPOSE_PROFILES сохранился
grep COMPOSE_PROFILES .env
# Expected: langfuse,neo4j,monitoring

# 2. Neo4j hostname сохранился
grep NEO4J_HOSTNAME .env
# Expected: neo4j.produman.studio

# 3. telethon/.env сохранился
cat telethon/.env | grep NEO4J
# Expected: NEO4J_ENABLED=true, NEO4J_URI=bolt://neo4j:7687

# 4. Docker containers работают
docker ps | grep -E "telethon|neo4j|prometheus"

# 5. Git clean
git status
```

---

## 📚 **Backup Location:**

```
Path: /home/ilyasni/n8n-server/n8n-installer/.backups/pre-update-20251014-004900/

Contents:
- docker-compose.yml
- docker-compose.override.yml
- .env
- Caddyfile
- prometheus/prometheus.yml
- telethon/.env
- grafana/provisioning/
- RESTORE_INSTRUCTIONS.md (this file)
```

---

## 🔧 **Restore Commands Summary:**

```bash
BACKUP_DIR=".backups/pre-update-20251014-004900"

# Compare
diff "$BACKUP_DIR/docker-compose.yml" docker-compose.yml

# Restore specific file
cp "$BACKUP_DIR/docker-compose.yml" docker-compose.yml

# Restore all
cp "$BACKUP_DIR"/* . -r  # ⚠️ Осторожно с .env!
```

---

**Status:** ✅ Backup ready for update.sh

**Next:** Запустите `bash scripts/update.sh` безопасно

