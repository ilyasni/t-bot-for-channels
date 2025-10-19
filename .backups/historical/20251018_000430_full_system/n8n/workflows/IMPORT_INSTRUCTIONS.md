# Инструкция по импорту V2 Workflows

**Дата:** 14 октября 2025  
**Статус:** ✅ Готово к импорту

---

## ✅ Исправлено: "Required" Error

**Проблема:** n8n не принимал файлы с непустыми `tags`  
**Решение:** Все `tags` очищены в пустые массивы `tags: []`

**Все файлы теперь валидны для импорта!**

---

## Порядок импорта (ВАЖНО!)

### 1. Сначала импортировать agent workflows

**В n8n UI:**

1. Settings → Import from File (или Workflows → Import)
2. Выбрать файл
3. Нажать Import

**Файлы импортировать в таком порядке:**

```
1. agent_dialogue_assessor.json         ← Assessor
2. agent_emotion_analyzer.json          ← Emotions  
3. agent_key_moments.json               ← Key Moments
4. agent_timeline.json                  ← Timeline
5. agent_context_links.json             ← Context Links
6. agent_supervisor_synthesizer.json    ← Synthesizer
```

**Existing workflows (REPLACE):**

```
7. agent_topic_extractor.json           ← REPLACE existing
8. agent_speaker_analyzer.json          ← REPLACE existing
9. agent_summarizer.json                ← REPLACE existing
```

После импорта каждого - **нажать Save** и **Activate**!

### 2. Импортировать Orchestrator V2

```
10. group_digest_orchestrator_v2_sequential.json
```

**НЕ активировать пока!**

### 3. Настроить Execute Workflow nodes в Orchestrator V2

**Открыть workflow "Group Digest Orchestrator V2"**

Для каждого Execute Workflow node настроить Workflow ID:

| Node Name | Select Workflow |
|-----------|-----------------|
| 1. Assessor | Agent: Dialogue Assessor |
| 2. Topics | Agent: Topic Extractor |
| 3. Emotions | Agent: Emotion Analyzer |
| 4. Speakers | Agent: Speaker Analyzer |
| 5. Summarizer | Agent: Context Summarizer |
| 6. Key Moments | Agent: Key Moments Extractor |
| 7. Timeline | Agent: Timeline Builder |
| 8. Context Links | Agent: Context Links Analyzer |
| 9. Synthesizer | Agent: Supervisor Synthesizer |

**Как настроить:**
1. Click на Execute Workflow node
2. В параметрах найти "Workflow" dropdown
3. Выбрать соответствующий workflow из списка
4. Повторить для всех 9 nodes

### 4. Save и Activate Orchestrator V2

1. Save workflow
2. Activate workflow
3. Проверить что webhook активен: `/webhook/group-digest-v2`

---

## Проверка

### Test в n8n UI

1. Открыть "Agent: Dialogue Assessor"
2. Нажать "Test workflow"
3. В Manual trigger data вставить:

```json
{
  "messages": [
    {"username": "Test", "text": "Привет! Как дела?"},
    {"username": "User2", "text": "Отлично, обсуждаем новый проект!"}
  ],
  "hours": 12,
  "messages_text": "Test: Привет! Как дела?\nUser2: Отлично, обсуждаем новый проект!"
}
```

4. Execute
5. Должен вернуть assessment с `detail_level: "micro"`

### Test через бота

```
/group_digest
→ Выбрать группу
→ Выбрать период
→ Дождаться дайджеста
```

**Проверить логи:**
```bash
docker logs telethon | grep "Pipeline:"
# Должно показать: "Pipeline: V2 Sequential"

docker logs telethon | grep "Detail Level:"
```

---

## Если всё равно ошибка импорта

### Попробуйте упрощенный метод:

1. **Скопировать содержимое файла**
   - Открыть `agent_dialogue_assessor.json` в редакторе
   - Скопировать весь JSON (Ctrl+A, Ctrl+C)

2. **Создать пустой workflow в n8n:**
   - Workflows → New Workflow
   - Назвать "Agent: Dialogue Assessor"
   - Save

3. **Вставить через Code:**
   - В n8n UI нажать три точки (...) → Download
   - Откроется редактор JSON
   - Заменить содержимое на скопированный JSON
   - Save

4. **Импортировать обратно:**
   - Settings → Import from File
   - Выбрать скачанный файл
   - Import

---

## Альтернатива: Manual Creation

Если импорт не работает, можно создать workflows вручную:

### Agent: Dialogue Assessor (Manual)

1. Create New Workflow → Name: "Agent: Dialogue Assessor"

2. Add nodes:
   - Execute Workflow Trigger
   - Code node (name: "Assess Dialogue")  
   - Code node (name: "Return Assessment")

3. В "Assess Dialogue" вставить код из `agent_dialogue_assessor.json` (строка 14)

4. В "Return Assessment" вставить:
```javascript
const items = $input.all();
return [{ json: { assessment: items[0].json }}];
```

5. Connect: Trigger → Assess → Return

6. Save & Activate

---

## Environment Variables

После импорта workflows, убедитесь что установлены:

```bash
USE_DIGEST_V2=true
N8N_GROUP_DIGEST_WEBHOOK_V2=http://n8n:5678/webhook/group-digest-v2
N8N_DIGEST_TIMEOUT_V2=180
```

Перезапустить telethon:
```bash
docker compose restart telethon
```

---

**Status:** ✅ Workflows исправлены и готовы к импорту  
**Next:** Импортировать в n8n UI по порядку

