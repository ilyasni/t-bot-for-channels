# 🤖 Настройка AI-классификатора голосовых команд (n8n)

**Версия:** 1.0.0  
**Дата:** 13 октября 2025  
**Статус:** ✅ Готов к использованию

---

## 🎯 Что это?

**AI-классификатор** автоматически определяет, какую команду (`/ask` или `/search`) нужно выполнить для голосового запроса пользователя.

**Преимущества:**
- 🚀 **Автоматизация** - не нужно выбирать команду вручную
- 🧠 **AI-анализ** - GigaChat определяет intent запроса
- 📈 **Масштабируемость** - легко добавить новые команды
- 💪 **Fallback** - если AI не работает, показываются кнопки

---

## 📋 Шаг 1: Импортировать n8n workflow

### 1.1. Откройте n8n

```bash
http://localhost:5678
```

### 1.2. Импортируйте workflow

1. Нажмите **"+"** → **"Import from File"**
2. Выберите файл: `n8n/workflows/voice_command_classifier.json`
3. Нажмите **"Import"**

### 1.3. Активируйте workflow

1. Откройте импортированный workflow **"Voice Command Classifier"**
2. Нажмите **"Active"** в правом верхнем углу
3. Проверьте статус: должен быть зеленый ✅

---

## 🔗 Шаг 2: Проверка webhook URL

Workflow использует endpoint:

```
http://n8n:5678/webhook/voice-classify
```

**В Telegram боте** уже настроено в `.env`:

```bash
N8N_WEBHOOK_URL=http://n8n:5678
VOICE_AI_CLASSIFIER_ENABLED=true
```

---

## 🧪 Шаг 3: Тестирование

### 3.1. Через n8n Test Webhook

1. Откройте workflow в n8n
2. Нажмите **"Listen for Test Event"** на узле Webhook
3. Отправьте тестовый запрос:

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
  "reasoning": "Пользователь задает вопрос, требующий анализа постов и генерации ответа",
  "original_transcription": "Что писали про нейросети на этой неделе?",
  "user_id": 1
}
```

### 3.2. Через Telegram бота

1. Отправьте голосовое **БЕЗ** предварительной команды `/ask` или `/search`
2. Дождитесь распознавания
3. Должно появиться:

```
✅ Распознано: "Что писали про нейросети..."

🤖 AI выбрал: /ask (95% уверенности)
🔍 Выполняю...
```

---

## 🎯 Как работает классификация

### Примеры `/ask` (RAG поиск):

| Транскрипция | Команда | Reasoning |
|-------------|---------|-----------|
| "Что писали про нейросети?" | `ask` | Вопрос требует анализа постов |
| "Расскажи о квантовых компьютерах" | `ask` | Запрос на генерацию ответа из постов |
| "Какие новости про Tesla?" | `ask` | Вопрос о конкретной информации |

### Примеры `/search` (гибридный поиск):

| Транскрипция | Команда | Reasoning |
|-------------|---------|-----------|
| "Найди информацию о блокчейне" | `search` | Информационный поиск |
| "Где найти статьи про AI?" | `search` | Поиск источников |
| "Что такое GPT-4?" | `search` | Определение термина |

---

## ⚙️ Настройка prompt (опционально)

### Где находится prompt?

Узел **"Prepare Prompt"** в workflow содержит инструкции для GigaChat.

### Как редактировать?

1. Откройте workflow в n8n
2. Кликните на узел **"Prepare Prompt"**
3. Измените текст в поле **"prompt"**
4. Нажмите **"Save"**

### Пример кастомизации:

Добавьте новую команду `/recommend`:

```javascript
**Доступные команды:**
1. `/ask` — поиск ответа в сохраненных постах (RAG)
2. `/search` — гибридный поиск (посты + интернет)  
3. `/recommend` — персональные рекомендации
   - Запросы: "Что интересного?", "Порекомендуй", "Что почитать?"
```

---

## 🐛 Troubleshooting

### ❌ Проблема: "AI классификатор недоступен, показываем кнопки"

**Причины:**
1. n8n workflow не активен
2. Webhook URL недоступен
3. GigaChat proxy не отвечает

**Решение:**

```bash
# 1. Проверьте статус workflow
http://localhost:5678 → Workflows → Voice Command Classifier
# Должен быть ✅ Active

# 2. Проверьте доступность webhook
curl http://localhost:5678/webhook/voice-classify \
  -X POST -H "Content-Type: application/json" \
  -d '{"transcription": "test", "user_id": 1}'

# 3. Проверьте GigaChat proxy
docker logs gpt2giga-proxy --tail 50

# 4. Проверьте логи бота
docker logs telethon 2>&1 | grep "AI классиф"
```

### ❌ Проблема: Всегда возвращается `/ask`, даже для поисковых запросов

**Причины:**
- Prompt недостаточно точный
- GigaChat не может разобрать запрос

**Решение:**

1. Откройте workflow → узел **"Prepare Prompt"**
2. Добавьте больше примеров для `/search`:

```
**Дополнительные примеры /search:**
- "Найди статьи о...", "Покажи информацию про..."
- "Где найти...", "Ссылки на...", "Источники по..."
```

3. Увеличьте `temperature` в узле **"GigaChat Classify"**:

```json
"temperature": 0.2  // Было 0.1
```

### ❌ Проблема: Timeout при классификации

**Причины:**
- GigaChat медленно отвечает
- Сетевые задержки

**Решение:**

Увеличьте timeout в `bot.py`:

```python
async with httpx.AsyncClient(timeout=15.0) as client:  # Было 10.0
```

Или отключите AI классификатор:

```bash
# В telethon/.env
VOICE_AI_CLASSIFIER_ENABLED=false
```

---

## 📊 Мониторинг

### Логи бота

```bash
# Смотрим классификации
docker logs telethon 2>&1 | grep "AI classification"

# Пример лога:
# INFO: 🤖 AI classification: ask (confidence: 95%, reason: Question requires RAG search)
```

### n8n Executions

1. Откройте n8n → **"Executions"**
2. Посмотрите последние запуски **"Voice Command Classifier"**
3. Проверьте:
   - ✅ Success/Error
   - ⏱️ Execution time
   - 📋 Input/Output data

---

## 🚀 Масштабирование

### Добавление новых команд

**Шаг 1:** Добавьте команду в prompt (узел "Prepare Prompt"):

```
3. `/recommend` — персональные рекомендации
   - Запросы: "Что почитать?", "Порекомендуй"
```

**Шаг 2:** Обновите валидацию в узле "Parse & Validate":

```javascript
const validCommands = ['ask', 'search', 'recommend'];  // Добавили recommend
```

**Шаг 3:** Добавьте обработку в `bot.py`:

```python
elif command == 'recommend':
    await self._execute_recommend_with_text(update, context, transcription, db_user)
```

---

## 💡 Best Practices

1. **Всегда тестируйте** изменения prompt через n8n Test Webhook
2. **Логируйте результаты** для анализа точности классификации
3. **Используйте fallback** на кнопки, если AI недоступен
4. **Мониторьте confidence** - если < 0.5, показывайте кнопки выбора
5. **Собирайте обратную связь** от пользователей для улучшения prompt

---

## 📚 Связанные документы

- [VOICE_COMMANDS.md](../../telethon/docs/features/voice/VOICE_COMMANDS.md) - Документация по голосовым командам
- [VOICE_QUICK_START.md](../../telethon/docs/features/voice/VOICE_QUICK_START.md) - Быстрый старт
- [voice_command_classifier.json](../../n8n/workflows/voice_command_classifier.json) - n8n workflow

---

**Готово!** 🎉 Теперь голосовые команды работают с AI-классификацией через n8n!

