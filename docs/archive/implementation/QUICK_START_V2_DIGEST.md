# 🚀 Быстрый старт V2 Adaptive Digest

**Дата:** 14 октября 2025  
**Статус:** ✅ Код готов, требуется импорт workflows в n8n

---

## Что уже работает ✅

### 1. Улучшенный UX для работы с группами

**Попробуйте сейчас:**

```
/group_digest
```

**Что произойдет:**
1. Появятся кнопки для выбора группы (если групп несколько)
2. После выбора группы → кнопки для выбора периода: **2ч, 8ч, 12ч, 24ч**
3. Дайджест генерируется автоматически

**Или:**

```
/my_groups
```

Появится список групп с кнопками "📊 Название группы" - нажмите для быстрого дайджеста!

### 2. Копируемые команды

Все команды в сообщениях бота теперь можно скопировать одним кликом:
- `/add_group`
- `/group_settings`
- `/ask`
- `/search`
- и т.д.

### 3. Кликабельные username

В дайджестах `@username` теперь кликабельны - нажмите чтобы открыть профиль.

---

## Что нужно настроить для V2 📋

### V2 = Адаптивные дайджесты с эмоциями

**5 уровней детализации автоматически:**

| Сообщений | Уровень | Что показывает |
|-----------|---------|----------------|
| 1-5 | micro | Одно предложение + эмодзи |
| 6-15 | minimal | Темы + тон + параграф |
| 16-50 | standard | Полный анализ + ключевые моменты + эмоции |
| 51-100 | detailed | + хронология + эмоциональная динамика |
| >100 | comprehensive | + внешние ссылки + Neo4j |

**Эмоциональный анализ:**
- 😊 Тон диалога (positive/neutral/negative)
- 🎭 Атмосфера обсуждения
- 📈 Эмоциональная динамика
- ⚡ Индикаторы: конфликт, сотрудничество, стресс, энтузиазм

**Ключевые моменты:**
- ✅ Решения
- ❓ Вопросы
- ⚠️ Проблемы
- 🤝 Договоренности
- 🔴 Риски

---

## Настройка V2 (в n8n UI)

### Шаг 1: Импорт workflows

1. Открыть n8n: `http://your-domain:5678`

2. Импортировать файлы (в порядке):
   ```
   n8n/workflows/agent_dialogue_assessor.json
   n8n/workflows/agent_emotion_analyzer.json
   n8n/workflows/agent_key_moments.json
   n8n/workflows/agent_timeline.json
   n8n/workflows/agent_context_links.json
   n8n/workflows/agent_supervisor_synthesizer.json
   n8n/workflows/agent_topic_extractor.json      (REPLACE existing)
   n8n/workflows/agent_speaker_analyzer.json     (REPLACE existing)
   n8n/workflows/agent_summarizer.json           (REPLACE existing)
   n8n/workflows/group_digest_orchestrator_v2_sequential.json
   ```

3. Для каждого файла:
   - Settings → Import from File
   - Выбрать файл
   - Нажать Import
   - Activate workflow

### Шаг 2: Настроить Orchestrator V2

1. Открыть workflow "Group Digest Orchestrator V2"

2. Для каждого Execute Workflow node настроить:
   - Node "1. Assessor" → Select Workflow: "Agent: Dialogue Assessor"
   - Node "2. Topics" → Select Workflow: "Agent: Topic Extractor"
   - Node "3. Emotions" → Select Workflow: "Agent: Emotion Analyzer"
   - Node "4. Speakers" → Select Workflow: "Agent: Speaker Analyzer"
   - Node "5. Summarizer" → Select Workflow: "Agent: Context Summarizer"
   - Node "6. Key Moments" → Select Workflow: "Agent: Key Moments Extractor"
   - Node "7. Timeline" → Select Workflow: "Agent: Timeline Builder"
   - Node "8. Context Links" → Select Workflow: "Agent: Context Links Analyzer"
   - Node "9. Synthesizer" → Select Workflow: "Agent: Supervisor Synthesizer"

3. Save workflow

4. Activate workflow

### Шаг 3: Проверить что работает

```
/group_digest
→ Выбрать группу
→ Выбрать период
→ Ожидать дайджест
```

**Логи:**
```bash
docker logs telethon | grep "Pipeline:"
# Должно показать: "Pipeline: V2 Sequential"

docker logs telethon | grep "Detail Level:"
# Должно показать определенный уровень
```

---

## Если что-то не работает

### V2 workflows не импортированы?

**Симптом:** Дайджесты генерируются, но структура старая

**Решение:** V1 pipeline используется как fallback - это нормально!

**Отключить V2 пока не готово:**
```bash
# В .env или через environment:
USE_DIGEST_V2=false

docker compose restart telethon
```

### Timeouts?

**Симптом:** "n8n workflow timeout"

**Решение:** Увеличить timeout
```bash
N8N_DIGEST_TIMEOUT_V2=240  # 4 минуты

docker compose restart telethon
```

### Пустые ключевые моменты?

**Это нормально!** Для уровней micro/minimal ключевые моменты не извлекаются.

---

## Текущий статус

✅ **Работает прямо сейчас:**
- Inline keyboards для /group_digest
- Inline keyboards для /my_groups
- Копируемые команды
- Кликабельные @username

⚠️ **Требует настройки в n8n:**
- Импорт 10 новых/обновленных workflows
- Настройка Execute Workflow nodes в orchestrator v2

📋 **Опционально (для comprehensive level):**
- Neo4j integration
- Crawl4AI integration
- Searxng integration

---

## Следующие действия

1. ✅ **Протестировать текущий UX** - `/group_digest` и `/my_groups`

2. **Когда готовы к V2:**
   - Импортировать workflows в n8n
   - Настроить orchestrator
   - Протестировать разные уровни детализации

3. **Позже (optional):**
   - Включить Neo4j для comprehensive level
   - Настроить Crawl4AI для анализа ссылок
   - Настроить Searxng для topic research

---

**Документация:**
- Полная: `docs/groups/V2_ADAPTIVE_DIGEST_COMPLETE.md`
- n8n Guide: `n8n/workflows/V2_SEQUENTIAL_PIPELINE_GUIDE.md`
- Summary: `IMPLEMENTATION_SUMMARY_2025-10-14.md`

