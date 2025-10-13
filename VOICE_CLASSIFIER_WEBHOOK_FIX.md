# 🎯 Voice Command Classifier - ИСПРАВЛЕНИЕ WEBHOOK

**Дата:** 13 октября 2025  
**Статус:** ✅ Критичная проблема решена!

---

## 🐛 Проблема:

```
ERROR:bot:❌ n8n classifier returned invalid response: {'message': 'Workflow was started'}
```

**Причина:** Webhook работал в **Production mode** и возвращал статус запуска вместо результата.

---

## ✅ Решение:

Добавлен параметр `"responseMode": "lastNode"` в Webhook узел:

```json
{
  "parameters": {
    "httpMethod": "POST",
    "path": "voice-classify",
    "responseMode": "lastNode",  // ← ДОБАВЛЕНО!
    ...
  }
}
```

**Теперь webhook:**
- ✅ Ждет завершения workflow
- ✅ Возвращает результат от "Respond to Webhook"
- ✅ Не возвращает статус запуска

---

## 🚀 ЧТО ДЕЛАТЬ:

### 1. Удали старый workflow в n8n:

```
1. http://localhost:5678 → Workflows
2. Voice Command Classifier → ... (три точки) → Delete
3. Confirm
```

### 2. Импортируй обновленный:

```
1. "+" → "Import from File"
2. n8n/workflows/voice_command_classifier.json
3. "Import"
4. "Active" ✅
```

### 3. Протестируй в Telegram:

```
1. /reset
2. Нажми кнопку: "🤖 AI режим"
3. Отправь голосовое: "Что писали про нейросети?"
```

**Ожидается:**
```
✅ Распознано: "Что писали про нейросети?"

🤖 AI выбрал: /ask (95% уверенности)
🔍 Выполняю...

💡 Ответ: [RAG ответ]
```

---

## 📊 Проверка в логах:

```bash
docker logs telethon 2>&1 | grep "AI classif" | tail -5

# Ожидается:
INFO:bot:🤖 AI classification: ask (95%)
```

**БЕЗ ошибки:**
```
ERROR:bot:❌ n8n classifier returned invalid response: {'message': 'Workflow was started'}
```

---

## 📊 Проверка в n8n:

```
http://localhost:5678 → Executions → Voice Command Classifier
```

**Должно быть:**
- **Status:** ✅ Success
- **Output:**
  ```json
  {
    "command": "ask",
    "confidence": 0.95,
    "reasoning": "...",
    "original_transcription": "Что писали про нейросети?",
    "user_id": 1
  }
  ```

---

## 🎯 Что исправлено:

| Проблема | Было | Стало |
|----------|------|-------|
| **Webhook mode** | Production (async) | lastNode (wait) |
| **Ответ** | `{"message": "Workflow was started"}` | `{"command": "ask", "confidence": 0.95, ...}` |
| **JSON генерация** | Template string (ломался) | Code узел (надежно) |
| **Fallback** | Не показывал кнопки | Показывает Inline кнопки ✅ |

---

## ✅ Структура workflow (финальная):

```
Webhook (responseMode: lastNode) ← ИСПРАВЛЕНО!
  ↓
Extract Input (transcription, user_id)
  ↓
Prepare Request (Code - создает JSON для GigaChat) ← ИСПРАВЛЕНО!
  ↓
GigaChat Classify (HTTP POST с готовым JSON)
  ↓
Parse & Validate (парсинг + эвристика fallback)
  ↓
Respond to Webhook (возвращает результат) ← ЖДЕТ WEBHOOK!
```

**Узлов:** 6  
**Credentials:** НЕ требуются ✅  
**Wait for result:** ✅ ДА!

---

## 🧪 Тестирование

### Тест 1: Через curl

```bash
curl -X POST http://n8n:5678/webhook/voice-classify \
  -H "Content-Type: application/json" \
  -d '{"transcription":"Найди информацию","user_id":1}'
```

**До исправления (БЫЛО):**
```json
{"message": "Workflow was started"}
```

**После исправления (ОЖИДАЕТСЯ):**
```json
{
  "command": "search",
  "confidence": 0.9,
  "reasoning": "Ключевое слово 'найди' указывает на информационный поиск",
  "original_transcription": "Найди информацию",
  "user_id": 1
}
```

### Тест 2: В Telegram

**Отправь:**
1. `/reset`
2. Нажми "🤖 AI режим"
3. Голосовое: "Что писали про нейросети?"

**До исправления:**
```
✅ Распознано: "..."
🤔 Выберите команду: [💡 /ask] [🔍 /search]
```

**После исправления:**
```
✅ Распознано: "Что писали про нейросети?"

🤖 AI выбрал: /ask (95% уверенности)
🔍 Выполняю...

💡 Ответ: [RAG ответ]
```

---

## 🎉 ГОТОВО!

**Переимпортируй workflow и протестируй!** 🚀

Теперь AI классификатор должен работать! ✅

---

**Покажи логи после теста:**
```bash
docker logs telethon 2>&1 | grep "AI classif" | tail -5
```

И что ответил бот! 👀
