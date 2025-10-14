# 🚀 Быстрый старт после потери данных

## ❌ Данные безвозвратно потеряны

**К сожалению, workflows и credentials восстановить невозможно.**

---

## ✅ План действий (30 минут)

### 1. Настроить автобэкапы (5 мин)

```bash
# Добавить в crontab
crontab -e

# Добавить строку (бэкап каждый день в 03:00):
0 3 * * * /home/ilyasni/n8n-server/n8n-installer/scripts/backup-n8n-postgres.sh >> /home/ilyasni/n8n-server/n8n-installer/.backups/postgres/backup.log 2>&1

# Сохранить и выйти (Ctrl+O, Enter, Ctrl+X)
```

### 2. Создать первого пользователя n8n (2 мин)

```bash
# Открыть n8n в браузере
echo "Откройте: http://localhost:5678"

# Создать аккаунт:
# Email: ваш_email
# Password: надежный_пароль
```

### 3. Пересоздать критичные workflows (20 мин)

Вам нужно пересоздать:

- ✅ **Voice Command Classifier**
- ✅ **Group Dialogue Multi-Agent**
- ✅ **Group Mention Analyzer**

**Если есть документация или схемы workflows - используйте их.**

### 4. Создать первый бэкап (1 мин)

```bash
cd /home/ilyasni/n8n-server/n8n-installer
./scripts/backup-n8n-postgres.sh
```

### 5. Настроить Git sync для workflows (2 мин)

```bash
# В n8n UI:
# Settings → Version Control → Enable Git sync
# Repository: ваш Git репозиторий
# Branch: main
```

---

## 📚 Полезные ресурсы

- **Предотвращение потери:** `DATA_LOSS_PREVENTION.md`
- **Детальный отчет:** `DATA_LOSS_REPORT_2025-10-14.md`
- **Скрипты бэкапа:** `scripts/backup-n8n-postgres.sh`

---

**Важно:** Теперь автобэкапы будут создаваться КАЖДЫЙ ДЕНЬ!

