# 🎯 Voice Command Classifier - ФИНАЛЬНАЯ НАСТРОЙКА

**Дата:** 13 октября 2025  
**Статус:** ✅ Код готов, осталось импортировать workflow

---

## ✅ ЧТО УЖЕ СДЕЛАНО:

1. ✅ **bot.py обновлен:**
   - Метод `_classify_voice_command()` для вызова n8n
   - Fallback на кнопки если AI недоступен
   - Исправлен `/rag/search` метод: POST → GET

2. ✅ **Переменные окружения добавлены:**
   ```bash
   # В telethon/.env:
   N8N_WEBHOOK_URL=http://n8n:5678
   VOICE_AI_CLASSIFIER_ENABLED=true
   ```

3. ✅ **n8n workflow создан:**
   - `n8n/workflows/voice_command_classifier.json`
   - БЕЗ требования credentials (authentication: none)
   - С fallback на эвристику если GigaChat не отвечает

4. ✅ **Бот перезапущен** и готов к работе

---

## 🚨 ОСТАЛОСЬ: Импортировать workflow в n8n

### Шаг 1: Откройте n8n

```
http://localhost:5678
```

### Шаг 2: Импортируйте workflow

1. **Нажмите "+" в левом меню**
2. **Выберите "Import from File"**
3. **Выберите файл:**
   ```
   n8n/workflows/voice_command_classifier.json
   ```
4. **Нажмите "Import"**

**Важно:** Workflow импортируется БЕЗ ошибок и БЕЗ требования credentials!

### Шаг 3: Активируйте workflow

1. Откройте импортированный workflow **"Voice Command Classifier"**
2. **Нажмите переключатель "Active" ✅** в правом верхнем углу
3. Статус должен стать зеленым

---

## ✅ ПРОВЕРКА РАБОТОСПОСОБНОСТИ

### Тест 1: Проверка webhook через curl

```bash
curl -X POST http://localhost:5678/webhook/voice-classify \
  -H "Content-Type: application/json" \
  -d '{
    "transcription": "Найди информацию по авто",
    "user_id": 1
  }'
```

**Ожидаемый ответ:**
```json
{
  "command": "search",
  "confidence": 0.9,
  "reasoning": "Информационный поиск",
  "original_transcription": "Найди информацию по авто",
  "user_id": 1
}
```

**Если ответа нет:**
- ❌ Workflow не импортирован
- ❌ Workflow не активирован
- ❌ n8n недоступен

### Тест 2: Через Telegram бота

**Отправьте голосовое БЕЗ команды:**

```
[Голосовое: "Найди информацию по авто"]
```

**Ожидается:**

#### ✅ С активным workflow:
```
✅ Распознано: "Найди информацию по авто"

🤖 AI выбрал: /search (90% уверенности)
🔍 Выполняю...

🔍 Результаты поиска: "Найди информацию по авто"
📱 Ваши посты (3):...
```

#### ⚠️ БЕЗ активного workflow (fallback):
```
✅ Распознано: "Найди информацию по авто"

🤔 Выберите команду для выполнения:
[💡 /ask - RAG поиск]
[🔍 /search - Гибридный поиск]
```

---

## 📊 Логи для проверки

### Логи бота (если AI работает):

```bash
docker logs telethon 2>&1 | grep -E "(AI классиф|classify)" | tail -10

# Ожидается:
INFO: 🤖 AI classification: search (confidence: 90%)
```

### Логи бота (если AI НЕ работает):

```bash
docker logs telethon 2>&1 | grep -E "(AI классиф|недоступ)" | tail -10

# Ожидается:
WARNING: ⚠️ AI классификатор недоступен, показываем кнопки
```

### n8n Executions:

```
http://localhost:5678 → Executions → Voice Command Classifier

Должны появиться записи с:
- Timestamp
- Success ✅
- Input data
```

---

## 🎯 Примеры классификации

| Голосовой запрос | AI команда | Confidence |
|-----------------|-----------|------------|
| "Найди информацию по авто" | `/search` | 90% |
| "Что писали про нейросети?" | `/ask` | 95% |
| "Где найти статьи про AI?" | `/search` | 88% |
| "Расскажи о блокчейне" | `/ask` | 92% |
| "Покажи новости про Tesla" | `/search` | 87% |

---

## 🔧 Структура workflow

```
Webhook (POST /webhook/voice-classify)
  ↓
Extract Input (transcription, user_id)
  ↓
Prepare Prompt (промпт для GigaChat)
  ↓
GigaChat Classify (HTTP POST к gpt2giga-proxy) [БЕЗ AUTH]
  ↓
Parse & Validate (парсинг JSON + fallback эвристика)
  ↓
Respond to Webhook (JSON результат)
```

**Узлов:** 6  
**Credentials:** НЕ требуются ✅  
**Fallback:** Встроен в "Parse & Validate" ✅

---

## 🐛 Troubleshooting

### ❌ "Credentials for 'Header Auth' are not set"

**НЕ ДОЛЖНО появляться!** Если появилось:
- Вы импортировали старую версию workflow
- Удалите и импортируйте заново исправленный файл

### ❌ Webhook возвращает 404

**Причины:**
1. Workflow не активирован
2. Path в Webhook узле не `voice-classify`

**Решение:**
1. Откройте workflow в n8n
2. Проверьте узел "Webhook" → Path = `voice-classify`
3. Активируйте workflow (переключатель Active ✅)

### ❌ В n8n нет Executions для Voice Command Classifier

**Причина:** Workflow не получает запросы

**Проверка:**

```bash
# 1. Workflow активен?
http://localhost:5678 → Workflows → Voice Command Classifier
# Должен быть ✅ Active

# 2. Webhook доступен?
curl -X POST http://localhost:5678/webhook/voice-classify \
  -H "Content-Type: application/json" \
  -d '{"transcription":"тест","user_id":1}'
# Должен вернуть JSON

# 3. Бот вызывает n8n?
docker logs telethon 2>&1 | grep "classify"
# Должны быть логи вызовов
```

### ❌ GigaChat timeout в workflow

**Причина:** gpt2giga-proxy не отвечает

**Решение:**

```bash
docker logs gpt2giga-proxy --tail 50
docker restart gpt2giga-proxy
```

Workflow автоматически использует fallback на эвристику!

---

## 📚 Связанные файлы

- **Workflow:** `n8n/workflows/voice_command_classifier.json`
- **Код бота:** `telethon/bot.py` (метод `_classify_voice_command`)
- **Env:** `telethon/.env` (переменная `N8N_WEBHOOK_URL`)
- **Документация:**
  - [WORKFLOW_FIXED.md](WORKFLOW_FIXED.md) - детали исправлений
  - [VOICE_AI_CLASSIFIER_READY.md](VOICE_AI_CLASSIFIER_READY.md) - полная инструкция

---

## ✅ CHECKLIST ФИНАЛЬНОЙ ПРОВЕРКИ

После импорта workflow в n8n:

- [ ] Workflow "Voice Command Classifier" импортирован
- [ ] Workflow активирован (✅ Active в n8n)
- [ ] НЕТ ошибки "Credentials required"
- [ ] Webhook доступен (`curl` возвращает JSON)
- [ ] В n8n → Executions появляются записи
- [ ] Логи бота показывают `🤖 AI classification: ...`
- [ ] Голосовое БЕЗ команды автоматически выполняет `/ask` или `/search`

---

## 🎉 ГОТОВО!

**Следующий шаг:**

1. Импортируйте `voice_command_classifier.json` в n8n
2. Активируйте workflow
3. Отправьте голосовое БЕЗ команды в Telegram
4. Наслаждайтесь AI-классификацией! 🚀

---

**Если что-то не работает** - проверьте раздел Troubleshooting выше! ☝️

