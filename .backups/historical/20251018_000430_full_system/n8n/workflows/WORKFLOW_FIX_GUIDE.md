# 🔧 n8n Workflows Fix Guide

**Проблема:** HTTP Request nodes использовали GET вместо POST, неправильные headers

**Решение:** Обновленные workflows v2

---

## ⚡ Быстрое исправление

### Вариант A: Удалить и реимпортировать (Рекомендуется)

1. Откройте n8n UI: `https://n8n.produman.studio`

2. **Удалите старые workflows:**
   - Workflows → "Group Dialogue Multi-Agent Analyzer"
   - Нажмите **Delete**
   - Повторите для "Group Mention Analyzer"

3. **Импортируйте новые v2:**
   - Workflows → **Import from File**
   - Выберите:
     - `n8n/workflows/group_dialogue_multi_agent_v2.json`
     - `n8n/workflows/group_mention_analyzer_v2.json`

4. **Активируйте оба:**
   - Откройте каждый workflow
   - Переключатель **Active** → **ON** (зеленый)
   - Нажмите **Save**

### Вариант B: Ручное исправление HTTP Request nodes

Для каждого HTTP Request node (Agent 1, 2, 3, 4):

**Что исправить:**

1. **Method:**
   - Было: `GET`
   - Стало: `POST` ✅

2. **Headers:**
   - Добавить: `Content-Type: application/json`

3. **Body:**
   - Включить: **Send Body** = `true`
   - Specify Body: **JSON**
   - JSON Body:
```json
{
  "model": "GigaChat",
  "messages": [
    {
      "role": "system",
      "content": "Системный промпт для агента"
    },
    {
      "role": "user",
      "content": "={{ $json.prompt_field }}"
    }
  ],
  "temperature": 0.3,
  "max_tokens": 300
}
```

---

## 🔍 Что исправлено в v2

### HTTP Request Node (правильная конфигурация)

**Было (v1 - неправильно):**
```json
{
  "parameters": {
    "url": "...",
    "sendBody": true,
    "bodyParameters": {
      "parameters": [
        {"name": "model", "value": "GigaChat"}
      ]
    }
  }
}
```

**Стало (v2 - правильно):**
```json
{
  "parameters": {
    "method": "POST",
    "url": "http://gpt2giga-proxy:8090/v1/chat/completions",
    "authentication": "none",
    "sendHeaders": true,
    "headerParameters": {
      "parameters": [
        {
          "name": "Content-Type",
          "value": "application/json"
        }
      ]
    },
    "sendBody": true,
    "specifyBody": "json",
    "jsonBody": "={{ {\"model\": \"GigaChat\", \"messages\": [...], \"temperature\": 0.3} }}"
  }
}
```

### Prepare Prompts Node

**Улучшено:**
- Обрабатывает как `body`, так и прямой `json` от webhook
- Более надежный парсинг входных данных

---

## ✅ После обновления

### Тест workflows

```bash
# Test 1: Group Digest
curl -X POST http://localhost:5678/webhook/group-digest \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"username": "alice", "text": "Привет всем!", "date": "2025-01-15T10:00:00Z"},
      {"username": "bob", "text": "Привет! Как дела?", "date": "2025-01-15T10:05:00Z"}
    ],
    "user_id": 1,
    "group_id": 1,
    "hours": 24
  }'

# Должен вернуть HTTP 200 с JSON:
# {"topics": [...], "speakers_summary": {...}, ...}
```

```bash
# Test 2: Mention Analyzer
curl -X POST http://localhost:5678/webhook/mention-analyzer \
  -H "Content-Type: application/json" \
  -d '{
    "mention_context": [
      {"username": "alice", "text": "Помогите с проблемой", "timestamp": "2025-01-15T10:00:00Z"},
      {"username": "bob", "text": "@charlie можешь помочь?", "timestamp": "2025-01-15T10:05:00Z"}
    ],
    "mentioned_user": "charlie"
  }'

# Должен вернуть HTTP 200 с JSON:
# {"context_summary": "...", "mention_reason": "...", ...}
```

---

## 🐛 Troubleshooting

### Ошибка: HPE_INVALID_HEADER_TOKEN

**Причина:** Неправильный метод HTTP (GET вместо POST) или некорректные headers

**Решение:** Используйте workflows v2 (исправлены)

### Ошибка: Invalid JSON Body

**Причина:** jsonBody использует неправильный формат выражений

**Решение:** 
- Используйте `specifyBody: "json"`
- jsonBody должен быть n8n expression: `={{ {...} }}`

### GigaChat возвращает ошибку

**Проверка:**
```bash
docker logs gpt2giga-proxy | tail -20
```

**Если proxy не работает:**
```bash
docker restart gpt2giga-proxy
```

---

## 📝 Файлы

**Исправленные workflows:**
- ✅ `group_dialogue_multi_agent_v2.json` - исправлен
- ✅ `group_mention_analyzer_v2.json` - исправлен

**Оригинальные (с ошибками):**
- ❌ `group_dialogue_multi_agent.json` - удалить
- ❌ `group_mention_analyzer.json` - удалить

---

## ✅ Готово!

После импорта v2 workflows должны работать корректно с GigaChat API.

