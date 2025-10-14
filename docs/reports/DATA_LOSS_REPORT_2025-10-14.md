# 🚨 Отчет о потере данных n8n - 14.10.2025

## ❌ Резюме

**Данные n8n (workflows, credentials, пользователи) безвозвратно потеряны.**

---

## 📊 Факты

### Что потеряно:

- ✅ Все workflows (включая Voice Command Classifier, Group Digest, и др.)
- ✅ Все credentials (API ключи, токены)
- ✅ Все executions (история выполнений)
- ✅ Пользователи n8n

### Что сохранилось:

- ✅ Конфигурационные файлы (docker-compose.yml, .env)
- ✅ Код Telegram Bot (telethon/)
- ✅ Демонстрационные workflows (n8n/backup/workflows/)
- ✅ Supabase БД (если там были данные)
- ✅ Qdrant векторная БД
- ✅ Redis кеш

---

## 🕐 Хронология событий

```
06.10.2025 22:55:09  ← Созданы volumes n8n-installer_*
13.10.2025 22:35:00  ← Последнее обновление n8n (работали workflows)
14.10.2025 00:49:00  ← Создан бэкап конфигов (.backups/pre-update-20251014-004900/)
14.10.2025 07:50:28  ← PostgreSQL ПЕРЕСОЗДАН (localai_langfuse_postgres_data)
14.10.2025 10:50:28  ← Созданы volumes localai_* (НОВЫЕ ПУСТЫЕ)
14.10.2025 11:00:00  ← Обнаружена потеря данных
```

---

## 🔍 Причина

При обновлении произошла **смена префикса Docker Compose проекта**:

```bash
# ДО обновления:
n8n-installer_langfuse_postgres_data  # Старый volume с данными

# ПОСЛЕ обновления:
localai_langfuse_postgres_data        # Новый ПУСТОЙ volume
```

**Docker Compose создал новые volumes вместо использования старых.**

### Возможные причины смены префикса:

1. Запуск `docker-compose` из другой директории
2. Смена переменной `COMPOSE_PROJECT_NAME` в .env
3. Использование флага `-p` или `--project-name`
4. Запуск команды типа `docker-compose -f localai/docker-compose.yml up`

---

## 🔎 Проверенные источники восстановления

### ❌ НЕ НАЙДЕНО:

1. **SQL дампы PostgreSQL:**
   ```bash
   find /home/ilyasni/n8n-server/ -name "*.sql*" -o -name "*dump*"
   # Результат: ПУСТО
   ```

2. **Старый PostgreSQL volume:**
   ```bash
   docker volume ls | grep postgres
   # Результат: только localai_langfuse_postgres_data (новый)
   ```

3. **Пользовательские workflows в Git:**
   ```bash
   git log --grep="Voice Command\|Group Digest"
   # Результат: НЕТ коммитов с пользовательскими workflows
   ```

4. **Экспорты из n8n UI:**
   ```bash
   find ~ -name "*.json" -path "*Download*" -mtime -30
   # Результат: только демо workflows
   ```

5. **Dangling volumes:**
   ```bash
   docker volume ls -f dangling=true
   # Результат: 4 пустых volume по 4KB каждый
   ```

### ✅ ЧТО ЕСТЬ:

- Демонстрационные workflows (310 шт.) в `n8n/backup/workflows/`
- Бэкапы конфигов в `.backups/pre-update-20251014-004900/`
- Пустая PostgreSQL БД с правильной структурой таблиц

---

## 📋 Текущее состояние

```bash
PostgreSQL volume: localai_langfuse_postgres_data
Создан: 2025-10-14T10:50:28+03:00
Размер: 65 MB (пустая БД с структурой таблиц)

Workflows: 0
Credentials: 0  
Executions: 0
Пользователи: 1 (без email - пустой)
```

---

## ✅ Что сделано для предотвращения

### 1. Созданы скрипты автоматического бэкапа:

```bash
./scripts/backup-n8n-postgres.sh       # Создать бэкап
./scripts/restore-n8n-postgres.sh      # Восстановить из бэкапа
./scripts/inspect-volume.sh            # Проверить содержимое volume
```

### 2. Создана документация:

- `DATA_LOSS_PREVENTION.md` - Полное руководство по предотвращению потери данных

### 3. Рекомендации для настройки автобэкапов:

```bash
# Добавить в crontab (бэкап каждый день в 03:00):
crontab -e

# Добавить:
0 3 * * * /home/ilyasni/n8n-server/n8n-installer/scripts/backup-n8n-postgres.sh >> /home/ilyasni/n8n-server/n8n-installer/.backups/postgres/backup.log 2>&1
```

---

## 🎯 Что делать дальше

### Вариант 1: Начать с нуля ✅ РЕКОМЕНДУЕТСЯ

```bash
# 1. Настроить автобэкапы
crontab -e
# Добавить строку:
0 3 * * * /home/ilyasni/n8n-server/n8n-installer/scripts/backup-n8n-postgres.sh >> /home/ilyasni/n8n-server/n8n-installer/.backups/postgres/backup.log 2>&1

# 2. Создать первого пользователя n8n
# Откройте http://localhost:5678 или https://ваш-домен

# 3. Пересоздать workflows вручную
# (к сожалению, нет других вариантов)

# 4. Настроить экспорт workflows в Git (рекомендуется)
# Settings → Import/Export → Enable Git sync
```

### Вариант 2: Попытаться найти старые данные

```bash
# Проверить все volumes детально
docker volume ls -q | while read vol; do
    echo "=== $vol ==="
    ./scripts/inspect-volume.sh "$vol"
done > all-volumes-inspection.txt

# Проверить backups на сервере (если есть внешние бэкапы)
# ...

# Проверить snapshots (если используется LVM/ZFS/Btrfs)
# ...
```

---

## 🛡️ Обязательно ПЕРЕД следующим обновлением

### ✅ Checklist:

```bash
# 1. Создать бэкап PostgreSQL
./scripts/backup-n8n-postgres.sh

# 2. Экспортировать workflows из UI
# n8n → Settings → Import/Export → Export all workflows

# 3. Проверить бэкап
ls -lh .backups/postgres/ | tail -5

# 4. Записать имена текущих volumes
docker volume ls > volumes-before-update.txt

# 5. НИКОГДА не использовать:
# ❌ docker-compose down -v
# ❌ docker volume prune --all
```

---

## 📞 Дополнительная информация

**Дата потери:** 14.10.2025  
**Время обнаружения:** ~11:00 MSK  
**Причина:** Смена Docker Compose проекта → новые volumes  
**Восстановление:** НЕВОЗМОЖНО (нет бэкапов)  
**Решение:** Начать с нуля + настроить автобэкапы

---

**Файл создан:** 14.10.2025  
**Автор:** AI Assistant

