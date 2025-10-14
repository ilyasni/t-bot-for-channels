# 🔍 Проверка RAG, /ask, /search и Voice Classifier

**Дата:** 14 октября 2025, 13:58  
**Статус:** Частично работает

---

## ✅ ЧТО РАБОТАЕТ

### 1. Голосовая транскрипция ✅

```
INFO:voice_transcription_service:✅ Транскрипция получена: Что нового в крипте?
```

- SaluteSpeech API работает
- OAuth2 token получается
- Распознавание работает корректно

### 2. AI классификация (ВНУТРЕННЯЯ) ✅

```
INFO:bot:🤖 AI classification: ask (80%)
INFO:bot:🤖 AI классификация: ask (confidence: 80%)
```

- GigaChat классифицирует команды
- Определяет /ask vs /search
- Работает напрямую в боте (не через n8n webhook)

### 3. RAG /ask с РАЗВЕРНУТЫМИ запросами ✅

```bash
# Тест:
curl -X POST http://localhost:8020/rag/ask \
  -d '{"user_id": 6, "query": "Что нового в мире криптовалют?", "context_limit": 10}'

# Результат:
{
  "answer": "В посте из канала @MarketOverview...",
  "sources": [{"post_id": 692, ...}, {"post_id": 716, ...}],
  "context_used": 2
}
```

✅ Находит релевантные посты  
✅ Генерирует ответы  
✅ Цитирует источники

---

## ❌ ЧТО НЕ РАБОТАЕТ

### 1. Voice Command Classifier n8n webhook ❌

```bash
# Тест:
curl -X POST http://localhost:5678/webhook/voice-classify \
  -d '{"transcription": "Что нового по банкам", "user_id": 6}'

# Результат:
Exit code: 7 (Connection refused / Not Found)
```

**Причина:** Workflow **НЕ ИМПОРТИРОВАН** или **НЕ АКТИВИРОВАН** в n8n

**Файл:** `n8n/workflows/voice_command_classifier.json` (существует, но не импортирован)

### 2. RAG /ask с КОРОТКИМИ запросами ❌

```bash
# Тест:
curl -X POST http://localhost:8020/rag/ask \
  -d '{"user_id": 6, "query": "банки", "context_limit": 10}'

# Результат:
{
  "answer": "По данному вопросу информации в постах не найдено",
  "sources": [],
  "context_used": 0
}
```

```bash
# Тест:
curl -X POST http://localhost:8020/rag/ask \
  -d '{"user_id": 6, "query": "крипта", "context_limit": 10}'

# Результат:
{
  "answer": "По данному вопросу информации в постах не найдено",
  "sources": [],
  "context_used": 0
}
```

**Причина:** Векторный поиск требует семантического контекста. Слова "банки", "крипта" слишком короткие.

**Решение:** Query Expander workflow (создан, но не импортирован)

---

## 🔧 ЧТО НУЖНО ИСПРАВИТЬ

### Приоритет 1: Импортировать Voice Command Classifier

**Шаги:**

1. Откройте n8n: `http://localhost:5678`

2. Import workflow:
   - Workflows → **Import from File**
   - Выберите: `n8n/workflows/voice_command_classifier.json`
   - Нажмите **Import**

3. Активируйте:
   - Переключатель **Active → ON** (зеленый)
   - Нажмите **Save**

4. Протестируйте:
   ```bash
   curl -X POST http://localhost:5678/webhook/voice-classify \
     -H "Content-Type: application/json" \
     -d '{"transcription": "Что нового по банкам", "user_id": 6}'
   ```

   **Ожидается:**
   ```json
   {
     "command": "ask",
     "confidence": 0.8,
     "reasoning": "...",
     "original_transcription": "Что нового по банкам",
     "user_id": 6
   }
   ```

### Приоритет 2 (Опционально): Импортировать Query Expander

**Зачем:** Автоматически расширять короткие запросы:
- "банки" → "Что нового по банкам и депозитам?"
- "крипта" → "Что нового в мире криптовалют?"

**Шаги:**

1. Import workflow:
   - `n8n/workflows/query_expander.json`

2. Активируйте: **Active → ON**

3. Протестируйте:
   ```bash
   curl -X POST http://localhost:5678/webhook/expand-query \
     -H "Content-Type: application/json" \
     -d '{"query": "банки", "user_id": 6}'
   ```

   **Ожидается:**
   ```json
   {
     "original_query": "банки",
     "expanded_query": "Что нового по банкам и депозитам?",
     "was_expanded": true,
     "user_id": 6
   }
   ```

4. Интегрировать в бота (требует изменения кода `bot.py`)

---

## 📊 Текущий статус workflows

| Workflow | Файл | Импортирован? | Активен? | Работает? |
|----------|------|---------------|----------|-----------|
| **Group Digest Orchestrator** | `group_digest_orchestrator.json` | ✅ | ✅ | ✅ |
| **Agent: Topic Extractor** | `agent_topic_extractor.json` | ✅ | 🔴 NO (Execute Trigger) | ✅ |
| **Agent: Speaker Analyzer** | `agent_speaker_analyzer.json` | ✅ | 🔴 NO (Execute Trigger) | ✅ |
| **Agent: Context Summarizer** | `agent_summarizer.json` | ✅ | 🔴 NO (Execute Trigger) | ✅ |
| **Group Mention Analyzer v2** | `group_mention_analyzer_v2.json` | ✅ | ✅ | ✅ |
| **Voice Command Classifier** | `voice_command_classifier.json` | ❌ | ❌ | ❌ |
| **Query Expander** | `query_expander.json` | ❌ | ❌ | ❌ |

---

## 🧪 Тесты для проверки

### Тест 1: Voice Command Classifier

**В Telegram:**
1. Отправьте `/reset`
2. Нажмите кнопку "🤖 AI режим"
3. Отправьте голосовое: "Что писали про нейросети?"

**Ожидается:**
```
✅ Распознано: "Что писали про нейросети?"

🤖 AI выбрал: /ask (95% уверенности)
🔍 Выполняю...

💡 Ответ: [RAG ответ]
```

**Если НЕ работает:**
- Проверьте что Voice Command Classifier импортирован и активен в n8n
- Проверьте n8n Executions (должны появиться записи)

### Тест 2: RAG /ask

**В Telegram:**
```
/ask Что нового в мире криптовалют и блокчейна?
```

**Ожидается:**
```
🔍 Ищу ответ в ваших постах...

💡 Ответ:
В посте из канала @MarketOverview от 2025-10-14 упоминается...

📚 Источники:
• @MarketOverview (14.10.2025 07:30)
```

### Тест 3: RAG /search

**В Telegram:**
```
/search блокчейн
```

**Ожидается:**
```
🔍 Результаты поиска: "блокчейн"

📱 Ваши посты (X):
[посты про блокчейн]

🌐 Интернет (X):
[результаты веб-поиска]
```

---

## 🎯 Рекомендации

### Краткосрочные (Сейчас)

1. ✅ **Импортируйте Voice Command Classifier** - это критично для работы голосовых команд
2. ✅ **Протестируйте голосовые команды** в Telegram
3. ⚠️ **Объясните пользователям** формулировать развернутые вопросы для `/ask`:
   - ❌ "банки" → 0 результатов
   - ✅ "Что нового по банкам?" → результаты

### Среднесрочные (На будущее)

4. 💡 **Импортируйте Query Expander** для автоматического расширения коротких запросов
5. 💡 **Интегрируйте Query Expander** в бота (требует изменения `bot.py`)

---

## 📁 Файлы

**Готовые workflows (нужно импортировать):**
- ✅ `n8n/workflows/voice_command_classifier.json` - **КРИТИЧНО**
- 💡 `n8n/workflows/query_expander.json` - опционально

**Уже импортированные:**
- ✅ `n8n/workflows/group_digest_orchestrator.json`
- ✅ `n8n/workflows/agent_topic_extractor.json`
- ✅ `n8n/workflows/agent_speaker_analyzer.json`
- ✅ `n8n/workflows/agent_summarizer.json`
- ✅ `n8n/workflows/group_mention_analyzer_v2.json`

**Документация:**
- `VOICE_CLASSIFIER_WEBHOOK_FIX.md` - исправление Voice Classifier
- `VOICE_CLASSIFIER_FINAL_SETUP.md` - настройка Voice Classifier
- `VOICE_AI_CLASSIFIER_READY.md` - готовность Voice AI

---

## ✅ Checklist

- [x] RAG endpoint исправлен (`/rag/query` → `/rag/ask`)
- [x] RAG_MIN_SCORE понижен (0.7 → 0.5)
- [x] Голосовая транскрибация работает (SaluteSpeech)
- [x] AI классификация работает (GigaChat в боте)
- [ ] **Voice Command Classifier импортирован в n8n**
- [ ] **Voice Command Classifier активирован**
- [ ] Голосовые команды тестированы в Telegram
- [ ] Query Expander импортирован (опционально)

---

**Следующий шаг:** Импортировать `voice_command_classifier.json` в n8n! 🚀

