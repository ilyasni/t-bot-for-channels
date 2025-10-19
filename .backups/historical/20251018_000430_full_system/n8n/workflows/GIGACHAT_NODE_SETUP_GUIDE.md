# 🔧 Настройка GigaChat нод в n8n

## 📋 Памятка по настройке GigaChat API нод

### 🎯 Основные параметры для всех GigaChat нод

#### 1. **Model** (Модель)
```
GigaChat        - для базовых задач
GigaChat-Pro    - для сложных задач (Speaker Analyzer, Summarizer, Synthesizer)
GigaChat-Max    - для максимального качества (если доступно)
```

#### 2. **Messages** (Сообщения)

**System Message** (для всех агентов):
```
Ты - [роль агента]. [описание задачи]. Возвращай ТОЛЬКО валидный JSON строго по схеме. ЗАПРЕЩЕНО: markdown, комментарии, придумывание данных.
```

**User Message** (динамическое):
```
={{ $json.prompt }}
```

#### 3. **Options** (Опции)

**Temperature:**
```
0.1  - для стабильности (все агенты)
```

**Max Tokens:**
```
={{ $json.max_tokens }}
```

**Top P:**
```
0.1  - для детерминированности
```

### 🔧 Настройка по агентам

#### **Agent: Topic Extractor**
- **Model:** `GigaChat`
- **System:** `"Ты - аналитик тем разговоров. Извлекай ключевые темы из диалогов с приоритетами и подтемами. Возвращай ТОЛЬКО валидный JSON строго по схеме. ЗАПРЕЩЕНО: markdown, комментарии, придумывание данных."`
- **User:** `={{ $json.prompt }}`
- **Temperature:** `0.1`
- **Max Tokens:** `={{ $json.max_tokens }}`

#### **Agent: Emotion Analyzer**
- **Model:** `GigaChat`
- **System:** `"Ты - эксперт по эмоциональному анализу диалогов. Анализируешь тон, атмосферу, эмоциональную динамику разговоров. Возвращай ТОЛЬКО валидный JSON строго по схеме. ЗАПРЕЩЕНО: markdown, комментарии, придумывание данных."`
- **User:** `={{ $json.prompt }}`
- **Temperature:** `0.1`
- **Max Tokens:** `={{ $json.max_tokens }}`

#### **Agent: Speaker Analyzer** ⭐ (КРИТИЧЕСКИ ВАЖНЫЙ)
- **Model:** `GigaChat-Pro`
- **System:** `"Ты - аналитик участников диалогов. Определяешь роли, позиции, вклады участников с учетом эмоционального контекста. Возвращай ТОЛЬКО валидный JSON строго по схеме. ЗАПРЕЩЕНО: markdown, комментарии, придумывание данных."`
- **User:** `={{ $json.prompt }}`
- **Temperature:** `0.1`
- **Max Tokens:** `={{ $json.max_tokens }}`

#### **Agent: Key Moments**
- **Model:** `GigaChat`
- **System:** `"Ты - аналитик ключевых моментов в диалогах. Извлекаешь решения, вопросы, проблемы, договоренности, риски с эмоциональным контекстом. Возвращай ТОЛЬКО валидный JSON строго по схеме. ЗАПРЕЩЕНО: markdown, комментарии, придумывание данных."`
- **User:** `={{ $json.prompt }}`
- **Temperature:** `0.1`
- **Max Tokens:** `={{ $json.max_tokens }}`

#### **Agent: Timeline**
- **Model:** `GigaChat`
- **System:** `"Ты - аналитик хронологии диалогов. Строишь временные линии обсуждений с учетом эмоциональной динамики. Возвращай ТОЛЬКО валидный JSON строго по схеме. ЗАПРЕЩЕНО: markdown, комментарии, придумывание данных."`
- **User:** `={{ $json.prompt }}`
- **Temperature:** `0.1`
- **Max Tokens:** `={{ $json.max_tokens }}`

#### **Agent: Summarizer**
- **Model:** `GigaChat-Pro`
- **System:** `"Ты - аналитик контекста диалогов. Создаешь адаптивные резюме разной детализации с учетом эмоционального контекста. Возвращай ТОЛЬКО валидный JSON строго по схеме. ЗАПРЕЩЕНО: markdown, комментарии, придумывание данных."`
- **User:** `={{ $json.prompt }}`
- **Temperature:** `0.1`
- **Max Tokens:** `={{ $json.max_tokens }}`

#### **Agent: Supervisor Synthesizer** ⭐ (ФИНАЛЬНЫЙ)
- **Model:** `GigaChat-Pro`
- **System:** `"Ты - supervisor синтезирующий финальные дайджесты из данных от всех агентов. Создаешь адаптивные дайджесты разных уровней детализации с эмоциональным контекстом. Возвращай ТОЛЬКО валидный JSON строго по схеме. ЗАПРЕЩЕНО: markdown, комментарии, придумывание данных."`
- **User:** `={{ $json.prompt }}`
- **Temperature:** `0.1`
- **Max Tokens:** `={{ $json.max_tokens }}`

#### **Agent: Context Links Analyzer** 🔗 (НОВЫЙ)
- **Model:** `GigaChat`
- **System:** `"Ты - эксперт по анализу контекстных ссылок в диалогах. Твоя задача - извлечь и проанализировать ссылки из сообщений. Возвращай ТОЛЬКО валидный JSON без markdown. Структура ответа: {\"context_links\": [{\"url\": \"...\", \"title\": \"...\", \"description\": \"...\"}]}. Если ссылок нет, верни {\"context_links\": []}. Анализируй только реальные ссылки из сообщений."`
- **User:** `={{ $json.prompt }}`
- **Temperature:** `0.1`
- **Max Tokens:** `={{ $json.max_tokens || 500 }}`

#### **Agent: Dialogue Assessor** 📊 (НОВЫЙ)
- **Model:** `GigaChat`
- **System:** `"Ты - эксперт по анализу диалогов. Твоя задача - оценить диалог и определить его характеристики. Возвращай ТОЛЬКО валидный JSON без markdown. Структура ответа: {\"assessment\": {\"detail_level\": \"...\", \"dialogue_type\": \"...\", \"message_count\": ..., \"token_budgets\": {...}}}. detail_level: micro, minimal, standard, detailed, comprehensive. dialogue_type: casual_chat, technical_discussion, problem_solving, conflict, collaboration."`
- **User:** `={{ $json.prompt }}`
- **Temperature:** `0.1`
- **Max Tokens:** `={{ $json.max_tokens || 800 }}`

### 🔑 Credentials (Учетные данные)

**Для всех GigaChat нод:**
- **Type:** `GigaChat API`
- **Name:** `GigaChat account`
- **ID:** `B0z9RpNctWVlh4up`

### ⚠️ Важные моменты

1. **User Message всегда:** `={{ $json.prompt }}`
2. **Temperature всегда:** `0.1` (не 0.3-0.4!)
3. **Max Tokens всегда:** `={{ $json.max_tokens }}`
4. **System Message содержит:** "ЗАПРЕЩЕНО: markdown, комментарии, придумывание данных"
5. **Speaker Analyzer, Summarizer и Synthesizer:** используют `GigaChat-Pro`
6. **Context Links Analyzer и Dialogue Assessor:** используют `GigaChat` (базовая модель)

### 🔄 После настройки

1. **Подключить Execute Guardrail** после каждой GigaChat ноды
2. **Проверить connections** в orchestrator
3. **Протестировать** через `/group_digest`
4. **Проверить логи** на `✅ Guardrail` сообщения

### 🚨 Частые ошибки

- ❌ **Пустое User Message** → должно быть `={{ $json.prompt }}`
- ❌ **Temperature 0.3-0.4** → должно быть `0.1`
- ❌ **Отсутствие "ЗАПРЕЩЕНО"** в System Message
- ❌ **Неправильные Credentials** → проверить ID
- ❌ **Отсутствие Execute Guardrail** после GigaChat ноды
- ❌ **Context Links Analyzer:** неправильная структура JSON → должно быть `{"context_links": [...]}`
- ❌ **Dialogue Assessor:** неправильные значения detail_level/dialogue_type → проверить допустимые значения

### ✅ Чек-лист настройки

- [ ] Model выбран правильно (GigaChat/GigaChat-Pro)
- [ ] System Message содержит "ЗАПРЕЩЕНО: markdown, комментарии, придумывание данных"
- [ ] User Message: `={{ $json.prompt }}`
- [ ] Temperature: `0.1`
- [ ] Max Tokens: `={{ $json.max_tokens }}`
- [ ] Credentials: GigaChat account (B0z9RpNctWVlh4up)
- [ ] Execute Guardrail подключен после GigaChat ноды
- [ ] Connections в orchestrator обновлены
- [ ] **Context Links Analyzer:** System Message содержит структуру `{"context_links": [...]}`
- [ ] **Dialogue Assessor:** System Message содержит допустимые значения detail_level/dialogue_type

---

**Время настройки:** ~5 минут на ноду  
**Критичность:** ВЫСОКАЯ - неправильная настройка = артефакты в JSON  
**Всего нод:** 9 (включая 2 новые: Context Links Analyzer, Dialogue Assessor)
