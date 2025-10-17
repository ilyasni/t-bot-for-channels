# ✅ V2 Digest System - Testing Checklist

**Дата:** 14 октября 2025  
**Статус:** Ready for Testing

---

## Pre-Check: Статус системы

### Контейнеры

```bash
✅ telethon - Up 29 minutes
✅ n8n - Up 14 hours (executions успешны)
✅ gpt2giga-proxy - (предполагается работает)
```

### V2 Pipeline Configuration

```bash
✅ USE_DIGEST_V2=True (активирован)
✅ V2 Webhook: http://n8n:5678/webhook/group-digest-v2
✅ Timeout: 180 seconds
```

### n8n Workflows Status

**Проверьте в n8n UI (http://your-domain:5678):**

- [ ] Agent: Dialogue Assessor - Imported & Active
- [ ] Agent: Emotion Analyzer - Imported & Active
- [ ] Agent: Topic Extractor - Updated & Active
- [ ] Agent: Speaker Analyzer - Updated & Active
- [ ] Agent: Context Summarizer - Updated & Active
- [ ] Agent: Key Moments Extractor - Imported & Active
- [ ] Agent: Timeline Builder - Imported & Active
- [ ] Agent: Context Links Analyzer - Imported & Active
- [ ] Agent: Supervisor Synthesizer - Imported & Active
- [ ] Group Digest Orchestrator V2 - Imported & Active
  - [ ] Execute Workflow node "1. Assessor" → выбран "Agent: Dialogue Assessor"
  - [ ] Execute Workflow node "2. Topics" → выбран "Agent: Topic Extractor"
  - [ ] Execute Workflow node "3. Emotions" → выбран "Agent: Emotion Analyzer"
  - [ ] Execute Workflow node "4. Speakers" → выбран "Agent: Speaker Analyzer"
  - [ ] Execute Workflow node "5. Summarizer" → выбран "Agent: Context Summarizer"
  - [ ] Execute Workflow node "6. Key Moments" → выбран "Agent: Key Moments Extractor"
  - [ ] Execute Workflow node "7. Timeline" → выбран "Agent: Timeline Builder"
  - [ ] Execute Workflow node "8. Context Links" → выбран "Agent: Context Links Analyzer"
  - [ ] Execute Workflow node "9. Synthesizer" → выбран "Agent: Supervisor Synthesizer"

---

## Test 1: UX Improvements (Already Working)

### ✅ Test Inline Keyboards

**В Telegram боте:**

```
/group_digest
```

**Ожидаемое поведение:**
- ✅ Появляются кнопки для выбора группы
- ✅ После выбора группы → кнопки периодов (2ч, 8ч, 12ч, 24ч)
- ✅ После выбора периода → начинается генерация

```
/my_groups
```

**Ожидаемое поведение:**
- ✅ Список групп с inline кнопками
- ✅ Кнопка "📊 Название группы" для быстрого дайджеста
- ✅ Кнопка "⚙️ Настройки уведомлений"

### ✅ Test Copyable Commands

```
/group_settings
```

**Ожидаемое поведение:**
- ✅ Команды в сообщении с тегом `<code>`
- ✅ Можно скопировать одним кликом

### ✅ Test Clickable Usernames

**Запросить любой дайджест и проверить:**
- ✅ `@username` в секции "Активные участники" кликабельны
- ✅ При клике открывается профиль пользователя

---

## Test 2: V2 Pipeline (Micro Level)

### Создать тестовую группу с 3-5 сообщениями

**В боте:**

```
/group_digest
→ Выбрать группу с малым количеством сообщений
→ Выбрать период: 2ч
→ Ожидать <15 секунд
```

**Ожидаемый результат (micro level):**

```
😊 Повседневная беседа

Обсудили [краткая суть]. Тон: [эмоциональный окрас].
```

**Проверить в логах:**

```bash
docker logs telethon | grep -A5 "Detail Level:"
```

Должно показать:
```
Detail Level: micro
Dialogue Type: casual_chat
```

---

## Test 3: V2 Pipeline (Minimal Level)

### Группа с 6-15 сообщениями

```
/group_digest
→ Выбрать группу со средним количеством сообщений
→ Выбрать период: 8ч
→ Ожидать <25 секунд
```

**Ожидаемый результат (minimal level):**

```
📊 Дайджест: [период] | [сообщений] сообщений

🎯 Темы:
1. Тема 1
2. Тема 2

😊/😐/😔 Тон: [описание] (интенсивность: 0.X)

📝 Суть:
[Один параграф резюме]
```

**Проверить:**
- [ ] Есть темы
- [ ] Есть эмоциональный тон с эмодзи
- [ ] Есть описание атмосферы
- [ ] Резюме краткое (1 параграф)

---

## Test 4: V2 Pipeline (Standard Level) ⭐

### Группа с 16-50 сообщениями

```
/group_digest
→ Выбрать активную группу
→ Выбрать период: 12ч
→ Ожидать 40-60 секунд
```

**Ожидаемый результат (standard level):**

```
📊 Дайджест: [группа] | [период] | [сообщений] сообщений
📋 Тип: problem_solving | Уровень: standard

🎯 Основные темы:
1. 🔴/🟡/🟢 Тема 1 (приоритет: high/medium/low)
2. Тема 2 (приоритет: ...)

😐 Эмоциональный тон: [описание] (0.XX)
   Атмосфера: [детальное описание]
   Индикаторы: conflict: XX%, collaboration: XX%, stress: XX%, enthusiasm: XX%

👥 Активные участники:
• @username1: [роль] - [вклад]
• @username2: [роль] - [вклад]

⚡ Ключевые моменты:

✅ РЕШЕНИЕ: [описание]
   Контекст: [контекст]
   Участники: @user1, @user2
   Последствия: [последствия]
   Эмоц. контекст: [эмоции]
   Срочность: high/medium/low

📝 Резюме:
[2-3 параграфа с эмоциональным контекстом]
```

**Проверить:**
- [ ] Есть темы с приоритетами (high/medium/low)
- [ ] Есть эмоциональный анализ с индикаторами
- [ ] Есть участники с ролями
- [ ] Есть ключевые моменты (✅ решения, ❓ вопросы, ⚠️ проблемы)
- [ ] Резюме учитывает эмоциональный контекст
- [ ] Username кликабельны
- [ ] Время генерации <60 секунд

---

## Test 5: V2 Pipeline (Detailed Level)

### Группа с 51-100 сообщениями

```
/group_digest
→ Выбрать очень активную группу
→ Выбрать период: 24ч
→ Ожидать 75-100 секунд
```

**Ожидаемый результат (detailed level):**

```
[Весь Standard формат] +

📅 Хронология:
12:30 🟢 [Событие 1]
13:00 🟡 [Событие 2]
13:30 🟠 [Событие 3]
...

📈 Эмоциональная динамика:
[Описание как менялась атмосфера]
Преобладающие эмоции: [список с процентами]
```

**Проверить:**
- [ ] Есть хронология с временными метками
- [ ] Есть эмоциональные эмодзи (🟢🟡🟠🔴🔵)
- [ ] Есть описание эмоциональной динамики
- [ ] Есть преобладающие эмоции с процентами

---

## Test 6: Error Handling

### Test пустой результат

```
/group_digest
→ Выбрать группу
→ Выбрать период: 2ч (где нет сообщений)
```

**Ожидаемое поведение:**
```
📭 За последние 2 часов в группе нет текстовых сообщений

Проверено сообщений: 0
```

### Test timeout (если долго)

**Если дайджест генерируется >3 минут:**

```
❌ Ошибка генерации дайджеста: n8n workflow timeout after 180s
```

**Решение:**
```bash
# Увеличить timeout
echo "N8N_DIGEST_TIMEOUT_V2=240" >> .env
docker compose restart telethon
```

---

## Проверка логов

### Check Detail Level Detection

```bash
docker logs telethon | grep "Detail Level:" | tail -5
```

**Должно показывать:**
```
Detail Level: micro        (для 1-5 messages)
Detail Level: minimal      (для 6-15 messages)
Detail Level: standard     (для 16-50 messages)
Detail Level: detailed     (для 51-100 messages)
Detail Level: comprehensive (для >100 messages)
```

### Check Pipeline Execution

```bash
docker logs telethon | grep "Pipeline:" | tail -3
```

**Должно показывать:**
```
Pipeline: V2 Sequential
```

### Check Agent Results

```bash
docker logs telethon | grep -E "(Topics extracted|Emotion analysis|Key moments)" | tail -10
```

**Ожидаемые записи:**
```
✅ Topics extracted: 3
✅ Emotion analysis успешно: neutral
✅ Key moments extracted: 2 моментов
```

---

## Сравнение V1 vs V2

### Попробуйте один и тот же дайджест дважды

**Test V1 (временно отключить V2):**

```bash
# В .env или через environment
USE_DIGEST_V2=false
docker compose restart telethon

# Запросить дайджест
/group_digest → [выбрать группу и период]

# Сохранить результат для сравнения
```

**Test V2 (включить обратно):**

```bash
USE_DIGEST_V2=true
docker compose restart telethon

# Запросить тот же дайджест
/group_digest → [та же группа и период]
```

**Сравнить:**
- V2 должен быть более структурированным
- V2 содержит эмоциональный анализ
- V2 содержит ключевые моменты (для standard+)
- V2 адаптивный (короче для малых диалогов)

---

## Known Issues & Solutions

### Issue 1: "n8n workflow failed: 404"

**Причина:** Orchestrator V2 не настроен (Execute Workflow nodes пустые)

**Решение:**
1. Открыть workflow "Group Digest Orchestrator V2" в n8n UI
2. Для каждого Execute Workflow node выбрать workflow
3. Save & Activate

### Issue 2: "Assessment not available"

**Причина:** Agent: Dialogue Assessor не импортирован или неактивен

**Решение:**
1. Проверить что workflow импортирован
2. Активировать workflow
3. Проверить что Execute Workflow Trigger доступен

### Issue 3: Пустые key_moments

**Это нормально для micro/minimal levels!**

Key moments активны только для:
- standard (16+ messages)
- detailed (51+ messages)
- comprehensive (101+ messages)

### Issue 4: Timeout для detailed/comprehensive

**Нормально!** Эти уровни требуют больше времени.

**Если timeout:**
```bash
N8N_DIGEST_TIMEOUT_V2=300  # 5 минут
docker compose restart telethon
```

---

## Success Criteria

### ✅ UX Improvements Working

- [x] Inline keyboards показываются
- [x] Выбор группы работает
- [x] Выбор периода работает
- [x] Команды копируемые
- [x] Username кликабельные

### ✅ V2 Pipeline Working

- [ ] Micro digests генерируются (<15s)
- [ ] Minimal digests генерируются (<25s)
- [ ] Standard digests с ключевыми моментами (<60s)
- [ ] Эмоциональный анализ присутствует
- [ ] Detail level определяется автоматически
- [ ] Адаптивная структура в зависимости от количества сообщений

### ✅ Quality Improvements

- [ ] Дайджесты более структурированы
- [ ] Есть приоритеты тем
- [ ] Есть ключевые моменты (решения, вопросы, проблемы)
- [ ] Эмоциональный контекст добавляет понимание
- [ ] Малые диалоги не избыточны (micro/minimal)
- [ ] Большие диалоги не поверхностны (detailed/comprehensive)

---

## Debug Commands

### Check последний дайджест в логах

```bash
docker logs telethon | grep -A20 "Генерация дайджеста" | tail -25
```

### Check n8n execution logs

```bash
docker logs n8n | grep -E "(Enqueued|finished|Error)" | tail -20
```

### Check V2 webhook calls

```bash
docker logs telethon | grep "group-digest-v2" | tail -5
```

### Manual test V2 webhook (если workflows настроены)

```bash
curl -X POST http://n8n:5678/webhook/group-digest-v2 \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"username": "Test1", "text": "Привет! Как дела?", "date": "2025-10-14T12:00:00Z"},
      {"username": "Test2", "text": "Отлично! Обсуждаем проект", "date": "2025-10-14T12:05:00Z"}
    ],
    "user_id": 123,
    "group_id": 456,
    "group_title": "Test Group",
    "hours": 12
  }'
```

Должен вернуть JSON с:
```json
{
  "detail_level": "micro",
  "dialogue_type": "casual_chat",
  "emotions": {...},
  "topics": [...],
  "digest_html": "..."
}
```

---

## Rollback Plan

### Если V2 работает плохо

```bash
# 1. Отключить V2
USE_DIGEST_V2=false

# 2. Restart
docker compose restart telethon

# 3. Verify
docker logs telethon | grep "Use V2 Pipeline:"
# Output: Use V2 Pipeline: False

# 4. Test
/group_digest
# Должен использовать V1 parallel pipeline
```

---

## Next Steps

После успешного тестирования:

### Week 1: Monitor & Tune

- Собрать feedback от пользователей
- Оптимизировать промпты если нужно
- Настроить thresholds для detail levels

### Week 2: External Integrations

- Включить Crawl4AI для анализа ссылок
- Включить Searxng для topic research
- Протестировать comprehensive level

### Week 3: Neo4j Knowledge Graph

- Реализовать сохранение дайджестов в граф
- Реализовать поиск похожих дискуссий
- Добавить в comprehensive level

---

## Quick Test Scenarios

### Scenario 1: Casual Chat (Micro)

**Setup:** Группа с 2-3 сообщениями за последние 2 часа

**Expected:**
- Detail level: micro
- Format: одно предложение + эмодзи
- Time: <10s

### Scenario 2: Work Discussion (Standard)

**Setup:** Рабочая группа с обсуждением задач (20-30 сообщений за 12ч)

**Expected:**
- Detail level: standard
- Format: темы + участники + ключевые моменты + эмоции
- Time: <50s
- Ключевые моменты должны быть извлечены

### Scenario 3: Long Meeting (Detailed)

**Setup:** Активная группа с долгим обсуждением (60+ сообщений за 24ч)

**Expected:**
- Detail level: detailed
- Format: + хронология + эмоциональная динамика
- Time: <90s
- Timeline должна быть построена

---

**Статус:** ✅ Ready for Testing  
**Next:** Протестировать через бота и заполнить checklist  
**Documentation:** See IMPLEMENTATION_SUMMARY_2025-10-14.md

