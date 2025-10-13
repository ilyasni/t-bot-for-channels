# 🎯 AI-классификатор голосовых команд - ГОТОВ К ЗАПУСКУ

**Статус:** ✅ Код развернут, осталось импортировать workflow в n8n

---

## 📋 Что уже сделано:

✅ **1. Создан n8n workflow:** `n8n/workflows/voice_command_classifier.json`
   - Webhook: `/webhook/voice-classify`
   - GigaChat для анализа intent
   - Fallback на эвристику если GigaChat не отвечает

✅ **2. Обновлен bot.py:**
   - Метод `_classify_voice_command()` для вызова n8n
   - Автоматическое выполнение определенной команды
   - Fallback на кнопки выбора если n8n недоступен

✅ **3. Добавлены переменные окружения:**
   ```bash
   VOICE_AI_CLASSIFIER_ENABLED=true  # ✅ Уже в telethon/.env
   N8N_WEBHOOK_URL=http://n8n:5678  # ✅ Уже в telethon/.env
   ```

✅ **4. Бот перезапущен** и готов к работе

---

## 🚀 ОСТАЛОСЬ: Импортировать workflow в n8n

### Шаг 1: Откройте n8n

```
http://localhost:5678
```

### Шаг 2: Импортируйте workflow

1. Нажмите **"+"** в левом меню
2. Выберите **"Import from File"**
3. Выберите файл:
   ```
   n8n/workflows/voice_command_classifier.json
   ```
4. Нажмите **"Import"**

### Шаг 3: Активируйте workflow

1. Откройте импортированный workflow **"Voice Command Classifier"**
2. Нажмите переключатель **"Active"** в правом верхнем углу
3. Должен появиться зеленый статус ✅

---

## ✅ Проверка работоспособности

### Тест 1: Проверка webhook через curl

```bash
curl -X POST http://localhost:5678/webhook/voice-classify \
  -H "Content-Type: application/json" \
  -d '{
    "transcription": "Что писали про нейросети на этой неделе?",
    "user_id": 1
  }'
```

**Ожидаемый ответ:**
```json
{
  "command": "ask",
  "confidence": 0.95,
  "reasoning": "Пользователь задает вопрос...",
  "original_transcription": "Что писали про нейросети на этой неделе?",
  "user_id": 1
}
```

### Тест 2: Через Telegram бота

1. **Отправьте голосовое БЕЗ команды:**
   - Голосовое: "Что писали про нейросети?"

2. **Ожидается:**
   ```
   ✅ Распознано: "Что писали про нейросети?"
   
   🤖 AI выбрал: /ask (95% уверенности)
   🔍 Выполняю...
   
   💡 Ответ: [ваш RAG ответ]
   ```

3. **Если AI недоступен (workflow не импортирован):**
   ```
   ✅ Распознано: "Что писали про нейросети?"
   
   🤔 Выберите команду для выполнения:
   [💡 /ask - RAG поиск]
   [🔍 /search - Гибридный поиск]
   ```

---

## 🎯 Как это работает

```
User: [голосовое без команды]
    ↓
SaluteSpeech API (транскрибация)
    ↓
Транскрипция: "Что писали про нейросети?"
    ↓
n8n webhook: /webhook/voice-classify
    ↓
GigaChat анализирует intent
    ↓
Возвращает: {"command": "ask", "confidence": 0.95}
    ↓
Bot автоматически выполняет /ask
    ↓
RAG service → Ответ пользователю
```

---

## 🧪 Примеры классификации

| Голосовой запрос | AI команда | Уверенность |
|-----------------|-----------|-------------|
| "Что писали про нейросети?" | `/ask` | 95% |
| "Найди информацию о блокчейне" | `/search` | 90% |
| "Расскажи о квантовых компьютерах" | `/ask` | 93% |
| "Где найти статьи про GPT?" | `/search` | 88% |

---

## 📊 Мониторинг

### Логи бота

```bash
docker logs telethon 2>&1 | grep "AI classification"

# Пример:
# INFO: 🤖 AI classification: ask (95%)
```

### n8n Executions

```
http://localhost:5678 → Executions → Voice Command Classifier
```

---

## 🐛 Troubleshooting

### ❌ "AI классификатор недоступен, показываем кнопки"

**Причина:** Workflow не импортирован или не активен

**Решение:**
1. Проверьте http://localhost:5678 → Workflows
2. Должен быть **"Voice Command Classifier"** со статусом ✅ Active
3. Если нет - импортируйте `n8n/workflows/voice_command_classifier.json`

### ❌ "n8n classifier error 404"

**Причина:** Неправильный путь webhook

**Решение:**
Проверьте в workflow узел **"Webhook"** → Path должен быть: `voice-classify`

### ❌ "GigaChat proxy timeout"

**Причина:** gpt2giga-proxy не отвечает

**Решение:**
```bash
docker logs gpt2giga-proxy --tail 50
docker restart gpt2giga-proxy
```

---

## 🚀 Готово к масштабированию!

Легко добавить новые команды:

1. **В prompt** (узел "Prepare Prompt"): добавить описание команды
2. **В валидации** (узел "Parse & Validate"): добавить в `validCommands`
3. **В bot.py** (`_classify_voice_command`): добавить `elif command == 'новая_команда'`

**Пример:** Добавить `/recommend`:
- Prompt: "3. `/recommend` — персональные рекомендации"
- Validation: `['ask', 'search', 'recommend']`
- Handler: `await self._execute_recommend_with_text(...)`

---

## 📚 Документация

- [VOICE_AI_CLASSIFIER_SETUP.md](docs/voice/VOICE_AI_CLASSIFIER_SETUP.md) - Подробная настройка
- [VOICE_AI_QUICK_START.md](docs/voice/VOICE_AI_QUICK_START.md) - Быстрый старт
- [voice_command_classifier.json](n8n/workflows/voice_command_classifier.json) - n8n workflow

---

## ✅ Checklist финальной проверки

- [ ] n8n workflow импортирован
- [ ] Workflow активирован (✅ Active)
- [ ] Webhook доступен (`curl http://localhost:5678/webhook/voice-classify`)
- [ ] Telegram бот перезапущен
- [ ] Голосовое БЕЗ команды работает с AI классификацией
- [ ] Логи показывают `🤖 AI classification: ...`

---

**ГОТОВО!** 🎉

Теперь импортируйте workflow в n8n и протестируйте голосовые команды!

```bash
# После импорта проверьте:
curl -X POST http://localhost:5678/webhook/voice-classify \
  -H "Content-Type: application/json" \
  -d '{"transcription": "Что нового в AI?", "user_id": 1}'
```

**Ожидается JSON с `"command": "ask"` и `"confidence": 0.XX"`** ✅

