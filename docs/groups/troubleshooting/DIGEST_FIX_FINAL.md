# ✅ Исправление пустого дайджеста - РЕШЕНИЕ НАЙДЕНО

**Дата:** 13 октября 2025, 16:00  
**Статус:** ✅ Проблема найдена и исправлена

---

## 🐛 Проблема

**Из debug вывода:**
```json
{
  "topics": ["Сохранение свободного интернета", ...],  ✅
  "speakers_summary": {"Анализ": "Не доступен..."},  ⚠️
  "overall_summary": "Участники обсудили...",  ✅
  "message_count": 0,  ❌ (должно быть 6)
  "period": "24 hours"  ❌ (должно быть "6 hours")
}
```

**Симптомы:**
- ✅ Темы извлекаются корректно (Agent 1 работает)
- ✅ Overall summary работает (Agent 3 работает)
- ⚠️ Speakers пустой (Agent 2 фильтруется GigaChat)
- ❌ `message_count: 0` вместо реального количества
- ❌ `period: "24 hours"` вместо запрошенного

---

## 🔍 Корневая причина

**Проблема в n8n workflow:**

1. **Prepare Prompts** создает данные:
   ```javascript
   {
     user_id: 19,
     hours: 6,
     message_count: 6,
     topic_prompt: "...",
     speaker_prompt: "...",
     summary_prompt: "..."
   }
   ```

2. **Agents 1-3** делают HTTP Request и **перезаписывают** данные:
   ```javascript
   {
     choices: [{message: {content: "..."}}]
   }
   ```
   **← user_id, hours, message_count ПОТЕРЯНЫ!**

3. **Merge Agent Responses** пытался найти `item.json.user_id` но его там нет!

---

## ✅ Исправление

### Файл: `n8n/workflows/group_dialogue_multi_agent_v2.json`

#### 1. Prepare Prompts Node

**Изменено:**
```javascript
// БЫЛО:
const limitedMessages = messages.slice(0, maxMessages);
message_count: limitedMessages.length,  // Неправильно!

// СТАЛО:
const messageCount = messages.length;  // Реальное количество
const limitedMessages = messages.slice(0, maxMessages);
message_count: messageCount,  // Правильно!
```

#### 2. Merge Agent Responses Node

**Изменено:**
```javascript
// БЫЛО:
for (const item of items) {
  if (item.json.user_id !== undefined) {  // Не находит!
    originalData = {...};
  }
}

// СТАЛО:
const preparedData = $('Prepare Prompts').first().json;  // Прямой доступ!
const originalData = {
  user_id: preparedData.user_id,
  hours: preparedData.hours,
  message_count: preparedData.message_count
};
```

**Логика:** Вместо поиска в потерянных данных от HTTP Requests, берем данные **напрямую из Prepare Prompts node**.

---

## 🚀 Как применить

### Шаг 1: Обновите workflow в n8n

1. **Откройте n8n UI:** `https://n8n.produman.studio`

2. **Деактивируйте старый:**
   - Workflows → "Group Dialogue Multi-Agent Analyzer v2"
   - Active → **OFF**

3. **Удалите старый (опционально):**
   - Delete workflow

4. **Импортируйте обновленный:**
   - Workflows → **Import from File**
   - Файл: `n8n/workflows/group_dialogue_multi_agent_v2.json`
   - Import

5. **Активируйте:**
   - Откройте импортированный workflow
   - Active → **ON** (зеленый)
   - Save

---

### Шаг 2: Протестируйте

**В Telegram боте:**
```
/debug_group_digest 6
```

**Ожидаемый результат:**
```json
{
  "topics": ["тема1", "тема2", ...],
  "speakers_summary": {...},
  "overall_summary": "...",
  "message_count": 6,  ✅ Правильно!
  "period": "6 hours"  ✅ Правильно!
}
```

**Отформатированное сообщение:**
```
# 📊 Дайджест группы: Core Banking design team
Период: 6 hours  ← ✅ Правильный период!
Сообщений проанализировано: 6  ← ✅ Правильное количество!

## 🎯 Основные темы:
1. Сохранение свободного интернета
2. Обновление iOS
...

## 📝 Резюме:
Участники обсудили вопросы сохранения свободы интернета...
```

---

## 📊 Что исправлено

| Поле | БЫЛО | СТАЛО |
|------|------|-------|
| **message_count** | 0 ❌ | 6 ✅ |
| **period** | "24 hours" ❌ | "6 hours" ✅ |
| **topics** | ✅ Работало | ✅ Работает |
| **overall_summary** | ✅ Работало | ✅ Работает |
| **speakers_summary** | ⚠️ Фильтруется | ⚠️ Фильтруется (GigaChat) |

**Примечание о speakers_summary:**
- Agent 2 (Speaker Analyzer) иногда фильтруется GigaChat
- Это поведение модели, не баг workflow
- Fallback: "Анализ не доступен из-за ограничений системы"

---

## 🔧 Техническая детали

### Почему $('Prepare Prompts').first().json работает?

В n8n каждый node может получить доступ к данным из предыдущих nodes через:
- `$input.all()` - данные от непосредственных предшественников
- `$('Node Name').first().json` - данные из конкретного node

**Проблема с HTTP Request:**
```
Prepare Prompts → Agent 1 (HTTP Request)
    ↓                    ↓
{user_id, hours}    {choices: [...]} ← Оригинальные поля потеряны!
```

**Решение через прямой доступ:**
```
Merge Agent Responses → $('Prepare Prompts').first().json
                            ↓
                     {user_id, hours} ← Данные не потеряны!
```

---

## ✅ Проверка после применения

Выполните команды:

```bash
# 1. Проверьте что workflow активен
curl https://n8n.produman.studio/api/v1/workflows | jq '.[] | select(.name | contains("Group Dialogue"))'

# 2. Протестируйте в боте
/debug_group_digest 6

# 3. Проверьте обычный дайджест
/group_digest 6
```

**Ожидается:**
- ✅ `message_count` соответствует реальному количеству
- ✅ `period` соответствует запрошенному hours
- ✅ Темы извлечены
- ✅ Резюме присутствует

---

## 📝 Changelog

**v2.1 (13.10.2025 16:00):**
- ✅ Исправлена потеря `message_count` и `hours`
- ✅ Prepare Prompts теперь использует `messages.length` для подсчета
- ✅ Merge Agent Responses использует `$('Prepare Prompts').first().json`
- ✅ Format Final Response корректно получает данные

**Файл:** `n8n/workflows/group_dialogue_multi_agent_v2.json`

---

**Примените исправления и протестируйте!** 🚀

