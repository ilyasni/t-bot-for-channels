# 🚀 Telegram Groups - Deployment Guide

**Quick deployment guide для функционала групп**

---

## ⚡ Быстрое развертывание (5 минут)

### 1. Импорт n8n Workflows (2 мин)

```bash
# Вариант A: Через UI
1. Откройте https://n8n.produman.studio
2. Workflows → Import from File
3. Выберите:
   - n8n/workflows/group_dialogue_multi_agent.json
   - n8n/workflows/group_mention_analyzer.json
4. Активируйте оба (зеленый переключатель)

# Вариант B: Через копирование
docker cp n8n/workflows/group_dialogue_multi_agent.json n8n:/home/node/.n8n/workflows/
docker cp n8n/workflows/group_mention_analyzer.json n8n:/home/node/.n8n/workflows/
docker restart n8n
```

**Проверка:**
```bash
curl http://localhost:5678/webhook/group-digest
# Не должно быть 404
```

### 2. Миграция БД (1 мин)

```bash
cd /home/ilyasni/n8n-server/n8n-installer/telethon
python scripts/migrations/add_groups_support.py migrate
```

**Ожидаемый вывод:**
```
✅ Таблица 'groups' создана
✅ Таблица 'user_group' создана
✅ Таблица 'group_mentions' создана
✅ Таблица 'group_settings' создана
✅ Миграция успешно завершена!
```

### 3. Обновление .env (30 сек)

```bash
# Добавить в telethon/.env
cat >> /home/ilyasni/n8n-server/n8n-installer/telethon/.env << 'EOF'

# Groups Integration
N8N_GROUP_DIGEST_WEBHOOK=http://n8n:5678/webhook/group-digest
N8N_MENTION_ANALYZER_WEBHOOK=http://n8n:5678/webhook/mention-analyzer
N8N_DIGEST_TIMEOUT=120
N8N_MENTION_TIMEOUT=60
DIGEST_MAX_MESSAGES=200
EOF
```

### 4. Перезапуск (1 мин)

```bash
docker restart telethon telethon-bot

# Проверка
docker logs telethon -f | grep -E "(GroupMonitor|группа)"
```

**Должно быть:**
```
✅ GroupMonitorService инициализирован
👀 Запуск мониторинга групп...
✅ Мониторинг запущен для N пользователей
```

### 5. Тест (30 сек)

В Telegram боте:
```
/add_group https://t.me/your_test_group
/my_groups
/group_digest 24
```

---

## ✅ Финальный Checklist

**Перед production:**
- [ ] n8n workflows импортированы и активны
- [ ] Миграция БД выполнена без ошибок
- [ ] .env обновлен с новыми переменными
- [ ] Контейнеры перезапущены
- [ ] gpt2giga-proxy работает
- [ ] Тестовая группа добавлена
- [ ] Тестовое упоминание получено
- [ ] Тестовый дайджест сгенерирован
- [ ] Логи не показывают ошибок

---

## 🐛 Если что-то не работает

### n8n Workflow 404

```bash
# Проверить активацию
# n8n UI → Workflows → Group Dialogue Multi-Agent
# Переключатель должен быть зеленым
```

### GroupMonitor не запускается

```bash
# Проверить логи
docker logs telethon 2>&1 | grep -A 10 "GroupMonitor"

# Перезапустить
docker restart telethon
```

### GigaChat не отвечает

```bash
# Проверить proxy
docker logs gpt2giga-proxy

# Тест
curl http://gpt2giga-proxy:8090/v1/models
```

### Миграция упала

```bash
# Rollback
python scripts/migrations/add_groups_support.py rollback

# Попробовать снова
python scripts/migrations/add_groups_support.py migrate
```

---

## 📚 Документация

**Полная документация:**
- `telethon/docs/features/groups/GROUPS_QUICKSTART.md`

**n8n Workflows:**
- `n8n/workflows/README_GROUP_WORKFLOWS.md`

**Архитектура:**
- `.cursor/rules/telegram-bot/02-architecture.mdc`

---

**Развертывание завершено!** 🎉

Теперь ваш бот может анализировать диалоги и уведомлять об упоминаниях.

