# 🤖 n8n Workflows для Telegram Groups

**Версия:** 1.0  
**Дата:** 15 января 2025

---

## 📋 Описание

Этот каталог содержит n8n workflows для мультиагентного анализа диалогов в Telegram группах.

**Workflows:**
1. `group_dialogue_multi_agent.json` - Дайджест диалога (4 AI агента)
2. `group_mention_analyzer.json` - Анализ упоминаний пользователя

---

## 🚀 Импорт в n8n

### Метод 1: Через n8n UI

1. Откройте n8n: `https://n8n.produman.studio` (или ваш URL)
2. Войдите в систему
3. Нажмите **Workflows** → **Import from File**
4. Выберите файл:
   - `group_dialogue_multi_agent.json`
   - `group_mention_analyzer.json`
5. Нажмите **Import**
6. Активируйте workflow (переключатель в правом верхнем углу)

### Метод 2: Через копирование в контейнер

```bash
# Из корня проекта
docker cp n8n/workflows/group_dialogue_multi_agent.json n8n:/home/node/.n8n/workflows/
docker cp n8n/workflows/group_mention_analyzer.json n8n:/home/node/.n8n/workflows/
docker restart n8n
```

---

## ⚙️ Настройка GigaChat

Workflows используют `gpt2giga-proxy:8090` для доступа к GigaChat.

### Проверка доступности

```bash
# Из любого контейнера в сети localai_default
curl http://gpt2giga-proxy:8090/v1/models

# Должен вернуть список моделей:
# - GigaChat
# - GigaChat-Max
# - EmbeddingsGigaR
```

### Если gpt2giga-proxy не доступен

1. Проверьте что контейнер запущен:
```bash
docker ps | grep gpt2giga
```

2. Проверьте переменные окружения:
```bash
# В .env файле должно быть:
GIGACHAT_CREDENTIALS=your_gigachat_credentials_base64
```

3. Перезапустите proxy:
```bash
docker restart gpt2giga-proxy
docker logs gpt2giga-proxy -f
```

---

## 🧪 Тестирование Workflows

### Workflow 1: Group Dialogue Multi-Agent

**Webhook URL:** `http://n8n:5678/webhook/group-digest`

**Тестовый запрос:**

```bash
curl -X POST http://localhost:5678/webhook/group-digest \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "username": "alice",
        "text": "Привет, кто-нибудь знает как настроить Docker?",
        "date": "2025-01-15T10:00:00Z"
      },
      {
        "username": "bob",
        "text": "Да, я могу помочь. Что конкретно нужно?",
        "date": "2025-01-15T10:05:00Z"
      },
      {
        "username": "alice",
        "text": "Нужно настроить docker-compose для n8n",
        "date": "2025-01-15T10:10:00Z"
      },
      {
        "username": "bob",
        "text": "Легко! Вот пример конфига...",
        "date": "2025-01-15T10:15:00Z"
      }
    ],
    "user_id": 123,
    "group_id": 456,
    "hours": 24
  }'
```

**Ожидаемый ответ:**

```json
{
  "topics": ["Docker", "n8n", "docker-compose"],
  "speakers_summary": {
    "alice": "Спрашивала про настройку Docker и docker-compose для n8n",
    "bob": "Предлагал помощь и делился примерами конфигурации"
  },
  "overall_summary": "Обсуждение настройки Docker и docker-compose для n8n. Alice просила помощи, Bob предложил решение.",
  "message_count": 4,
  "period": "24 hours"
}
```

### Workflow 2: Group Mention Analyzer

**Webhook URL:** `http://n8n:5678/webhook/mention-analyzer`

**Тестовый запрос:**

```bash
curl -X POST http://localhost:5678/webhook/mention-analyzer \
  -H "Content-Type: application/json" \
  -d '{
    "mention_context": [
      {
        "username": "alice",
        "text": "У нас проблема с базой данных",
        "timestamp": "2025-01-15T10:00:00Z"
      },
      {
        "username": "bob",
        "text": "@charlie можешь посмотреть? Ты эксперт по PostgreSQL",
        "timestamp": "2025-01-15T10:05:00Z"
      },
      {
        "username": "alice",
        "text": "Да, срочно нужна помощь",
        "timestamp": "2025-01-15T10:06:00Z"
      }
    ],
    "mentioned_user": "charlie"
  }'
```

**Ожидаемый ответ:**

```json
{
  "context_summary": "Обсуждение проблемы с PostgreSQL базой данных",
  "mention_reason": "Запрос технической помощи как эксперта по PostgreSQL",
  "urgency": "high",
  "key_points": [
    "Проблема с базой данных",
    "Требуется срочная помощь",
    "Charlie - эксперт по PostgreSQL"
  ]
}
```

---

## 🔧 Архитектура Workflows

### Group Dialogue Multi-Agent (4 агента)

```
Webhook → Prepare Prompts
            ↓
    ┌───────┼───────┐ (параллельно)
    ↓       ↓       ↓
 Agent1  Agent2  Agent3
 Topics  Speakers Summary
    ↓       ↓       ↓
    └───────┼───────┘
            ↓
      Merge Results
            ↓
     Agent4: Aggregator
       (GigaChat-Max)
            ↓
    Format Response → Return
```

**Timing:**
- Agent 1-3: ~5-8 сек каждый (параллельно)
- Agent 4: ~10-15 сек
- **Total:** ~15-25 сек

### Group Mention Analyzer (1 агент)

```
Webhook → Prepare Prompt
            ↓
    Analyze Mention (GigaChat)
            ↓
    Format Response → Return
```

**Timing:**
- Analysis: ~5-8 сек
- **Total:** ~5-10 сек

---

## 🐛 Troubleshooting

### Ошибка: "GigaChat proxy not available"

```bash
# Проверьте gpt2giga-proxy
docker logs gpt2giga-proxy | tail -20

# Проверьте сеть
docker exec n8n ping -c 1 gpt2giga-proxy

# Перезапустите proxy
docker restart gpt2giga-proxy
```

### Ошибка: "Webhook not found"

1. Убедитесь что workflow **активирован** (зеленый переключатель)
2. Проверьте путь webhook в настройках Webhook Node
3. Перезапустите workflow

### Медленная генерация (>30 сек)

**Причины:**
- GigaChat API перегружен
- Слишком много сообщений (>200)

**Решение:**
1. Уменьшите `digest_max_messages` в настройках
2. Используйте `GigaChat` вместо `GigaChat-Max` для Agent 4
3. Увеличьте timeout в HTTP Request nodes

---

## 📊 Мониторинг

### n8n Executions

Проверьте статус выполнений:
1. n8n UI → **Executions**
2. Фильтр по workflow: "Group Dialogue Multi-Agent"
3. Смотрите детали ошибок и время выполнения

### Логи n8n

```bash
# Смотрите логи в реальном времени
docker logs n8n -f --tail 50

# Фильтр по ошибкам
docker logs n8n 2>&1 | grep ERROR
```

---

## 🔄 Обновление Workflows

### Метод 1: Reimport

1. Измените JSON файл
2. В n8n UI: **Workflows** → найдите workflow
3. **Delete workflow**
4. **Import from File** → выберите обновленный JSON

### Метод 2: Ручное редактирование

1. Откройте workflow в n8n UI
2. Измените nodes напрямую
3. **Save** → **Activate**

---

## 💡 Best Practices

### 1. Лимиты сообщений

```javascript
// В Prepare Prompts node
const maxMessages = 200; // Не больше 200
const limitedMessages = messages.slice(0, maxMessages);
```

### 2. Timeout для GigaChat

```json
{
  "options": {
    "timeout": 60000  // 60 сек для обычных агентов
  }
}
```

Для Agent 4 (Aggregator):
```json
{
  "options": {
    "timeout": 90000  // 90 сек для сложной задачи
  }
}
```

### 3. Error Handling

Добавьте Error Trigger node для уведомлений об ошибках:

```
[Error Trigger] → [Send Notification]
```

---

## 📚 Дополнительная документация

- **n8n Docs:** https://docs.n8n.io/
- **GigaChat API:** https://developers.sber.ru/docs/ru/gigachat/
- **Telethon Groups Quickstart:** `telethon/docs/features/groups/GROUPS_QUICKSTART.md`

---

## ✅ Checklist перед использованием

- [ ] Workflows импортированы в n8n
- [ ] Workflows активированы (зеленый переключатель)
- [ ] gpt2giga-proxy доступен и работает
- [ ] Тестовые запросы выполнены успешно
- [ ] Webhook URLs сохранены в `telethon/.env`:
  ```bash
  N8N_GROUP_DIGEST_WEBHOOK=http://n8n:5678/webhook/group-digest
  N8N_MENTION_ANALYZER_WEBHOOK=http://n8n:5678/webhook/mention-analyzer
  ```

---

**Готово!** Workflows настроены и готовы к использованию из Telegram бота.

