# 🚨 ВОССТАНОВЛЕНИЕ N8N ДАННЫХ

**Проблема:** После перезапуска n8n потерял workflows и пользователя!

**Причина:** Запустился **новый n8n** с пустым volume `n8n-installer_n8n_storage`

**ТВОИ ДАННЫЕ СОХРАНЕНЫ** в volume: `localai_n8n_storage` ✅

---

## ✅ БЫСТРОЕ РЕШЕНИЕ: Скопировать данные

### Вариант 1: Скопировать volume (РЕКОМЕНДУЮ)

```bash
# 1. Останови n8n
docker stop n8n n8n-installer-n8n-worker-1

# 2. Скопируй данные из старого volume в новый
docker run --rm \
  -v localai_n8n_storage:/source:ro \
  -v n8n-installer_n8n_storage:/target \
  alpine sh -c "cd /source && cp -av . /target/"

# 3. Запусти n8n обратно
cd /home/ilyasni/n8n-server/n8n-installer
docker compose --profile n8n up -d

# 4. Проверь http://localhost:5678
```

### Вариант 2: Использовать старый volume напрямую

Изменить `docker-compose.yml`:

```yaml
n8n:
  volumes:
    - localai_n8n_storage:/home/node/.n8n  # Используем старый volume!
```

---

## 🎯 ЧТО ПРОИЗОШЛО:

**1. ДО перезапуска:**
```
localai/n8n → localai_n8n_storage
  ├── User: ilyasni@...
  ├── Workflows:
  │   ├── Voice Command Classifier ✅
  │   ├── Group Dialogue Multi-Agent v3 ✅
  │   └── Group Mention Analyzer v2 ✅
  └── Credentials: все настроено
```

**2. ПОСЛЕ `docker compose down`:**
```
n8n-installer/n8n → n8n-installer_n8n_storage (ПУСТОЙ!)
  ├── User: пустой email
  ├── Workflows: 310 demo workflows
  └── Credentials: нет
```

---

## 🛡️ ПОЧЕМУ ЭТО ПРОИЗОШЛО:

```yaml
# docker-compose.yml (n8n-installer):
volumes:
  n8n_storage:  ← НОВЫЙ VOLUME СОЗДАЛСЯ!

n8n:
  volumes:
    - n8n_storage:/home/node/.n8n  ← ПОДКЛЮЧИЛСЯ К НОВОМУ!
```

**Docker Compose создал НОВЫЙ volume** вместо использования старого!

---

## ✅ ВЫПОЛНИ СЕЙЧАС:

```bash
# 1. Останови новый n8n
docker stop n8n n8n-installer-n8n-worker-1

# 2. Скопируй данные
docker run --rm \
  -v localai_n8n_storage:/source:ro \
  -v n8n-installer_n8n_storage:/target \
  alpine sh -c "cd /source && cp -av . /target/"

# 3. Запусти обратно
cd /home/ilyasni/n8n-server/n8n-installer
docker compose --profile n8n up -d

# 4. Проверь http://localhost:5678
```

**ТВОИ WORKFLOWS ВЕРНУТСЯ!** ✅

---

## 📊 Проверка после восстановления:

```bash
# Должны увидеть твои workflows:
docker exec postgres psql -U postgres -d postgres \
  -c "SELECT name, active FROM workflow_entity WHERE name LIKE '%Voice Command%' OR name LIKE '%Group Digest%'"
```

---

**ВАЖНО:** В будущем используй правильный volume в `docker-compose.yml`!

