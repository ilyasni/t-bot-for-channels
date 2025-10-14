# 🛡️ Предотвращение потери данных n8n

## ❌ Что произошло 14 октября 2025

**PostgreSQL volume был удален/пересоздан во время обновления, все workflows и credentials потеряны.**

### Хронология:

```
06.10.2025 22:55 - Созданы первые volumes (n8n-installer_*)
13.10.2025 22:35 - Последнее сохранение workflows
14.10.2025 07:50 - PostgreSQL volume ПЕРЕСОЗДАН (localai_langfuse_postgres_data)
14.10.2025 10:50 - Обнаружена потеря данных
```

### Причина:

При обновлении произошла смена проекта или конфигурации, что привело к:
1. Созданию новых volumes с префиксом `localai_*` вместо `n8n-installer_*`
2. PostgreSQL запустился с пустой БД
3. Старые volumes возможно удалены командой `docker-compose down -v` или `docker volume prune`

---

## ✅ Решение: Автоматические бэкапы

### 1. Создание бэкапа вручную

```bash
cd /home/ilyasni/n8n-server/n8n-installer

# Создать бэкап
./scripts/backup-n8n-postgres.sh

# Результат:
# .backups/postgres/n8n-postgres-backup-YYYYMMDD-HHMMSS.sql.gz
```

### 2. Настройка автоматических бэкапов (cron)

```bash
# Добавить в crontab
crontab -e

# Добавить строку (бэкап каждый день в 03:00):
0 3 * * * /home/ilyasni/n8n-server/n8n-installer/scripts/backup-n8n-postgres.sh >> /home/ilyasni/n8n-server/n8n-installer/.backups/postgres/backup.log 2>&1
```

### 3. Восстановление из бэкапа

```bash
# Посмотреть доступные бэкапы
ls -lh .backups/postgres/

# Восстановить
./scripts/restore-n8n-postgres.sh n8n-postgres-backup-20251014-030000.sql.gz
```

---

## 🔒 Предотвращение в будущем

### 1. Перед ЛЮБЫМ обновлением

```bash
# 1. Создать бэкап PostgreSQL
./scripts/backup-n8n-postgres.sh

# 2. Экспортировать workflows вручную
# Откройте n8n UI → Settings → Import/Export → Export all workflows

# 3. Создать бэкап конфигов (уже есть в .backups/)
cp docker-compose.yml .backups/docker-compose.yml.$(date +%Y%m%d-%H%M%S)
```

### 2. НИКОГДА не используйте `-v` флаг

```bash
# ❌ ОПАСНО - удалит все volumes!
docker-compose down -v

# ✅ БЕЗОПАСНО - остановит контейнеры, volume останутся
docker-compose down
```

### 3. Проверка volumes перед удалением

```bash
# Посмотреть все volumes
docker volume ls

# Посмотреть что внутри volume
docker run --rm -v VOLUME_NAME:/data:ro alpine ls -lah /data/

# Удалить только неиспользуемые (dangling) volumes
docker volume prune

# НИКОГДА не используйте --all без проверки!
# docker volume prune --all  # ❌ ОПАСНО!
```

---

## 📋 Регулярные проверки

### Ежедневно (автоматически через cron):

```bash
0 3 * * * /home/ilyasni/n8n-server/n8n-installer/scripts/backup-n8n-postgres.sh
```

### Еженедельно (вручную):

```bash
# Проверить количество workflows
docker exec postgres psql -U postgres -d postgres -c "SELECT COUNT(*) FROM workflow_entity;"

# Проверить размер БД
docker exec postgres psql -U postgres -d postgres -c "SELECT pg_size_pretty(pg_database_size('postgres'));"

# Проверить наличие бэкапов
ls -lh .backups/postgres/ | tail -10
```

---

## 🆘 Аварийное восстановление

### Если данные потеряны:

1. **Проверить старые volumes:**
   ```bash
   docker volume ls -f dangling=true
   docker run --rm -v OLD_VOLUME:/data:ro alpine ls -lah /data/
   ```

2. **Поискать SQL дампы:**
   ```bash
   find /home/ilyasni/ -name "*.sql*" -mtime -30
   ```

3. **Проверить экспорты из n8n UI:**
   ```bash
   find ~ -name "*.json" -path "*/Downloads/*" -mtime -30
   ```

4. **Восстановить из бэкапа:**
   ```bash
   ./scripts/restore-n8n-postgres.sh LATEST_BACKUP.sql.gz
   ```

---

## 🎯 Рекомендации

### ✅ ДЕЛАТЬ:

- ✅ Создавать бэкап перед каждым обновлением
- ✅ Экспортировать workflows вручную из UI
- ✅ Использовать named volumes в docker-compose.yml
- ✅ Регулярно проверять наличие бэкапов
- ✅ Хранить бэкапы вне Docker volumes

### ❌ НЕ ДЕЛАТЬ:

- ❌ Использовать `docker-compose down -v`
- ❌ Запускать `docker volume prune --all`
- ❌ Удалять volumes без проверки содержимого
- ❌ Обновлять систему без бэкапов
- ❌ Полагаться только на Docker volumes

---

## 📞 В случае проблем

1. **Остановить все операции**
2. **НЕ УДАЛЯТЬ volumes**
3. **Создать список всех volumes:** `docker volume ls > volumes.txt`
4. **Проверить содержимое:** `./scripts/inspect-volume.sh VOLUME_NAME`
5. **Обратиться за помощью с логами**

---

**Дата создания:** 14.10.2025  
**Автор:** AI Assistant  
**Последнее обновление:** 14.10.2025

