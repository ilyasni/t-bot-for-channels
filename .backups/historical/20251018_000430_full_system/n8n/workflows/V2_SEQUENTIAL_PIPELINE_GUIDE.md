# Group Digest V2: Adaptive Sequential Multi-Agent Pipeline

**Created:** October 14, 2025  
**Status:** ✅ Implementation Complete  
**Pipeline:** Sequential 8-Agent System with Emotion Analysis

---

## Overview

V2 Pipeline улучшает генерацию дайджестов через:

1. **Адаптивность** - 5 уровней детализации (micro → comprehensive)
2. **Эмоциональный анализ** - тон, атмосфера, динамика
3. **Последовательная обработка** - каждый агент получает результаты предыдущих
4. **Интеграции** - Neo4j, Crawl4AI, Searxng для обогащения контекста
5. **Ключевые моменты** - решения, вопросы, проблемы с эмоц. контекстом

---

## Архитектура: 8 Агентов

### Sequential Pipeline

```
Webhook → Prepare Data →

  1. Dialogue Assessor     (defines detail_level, dialogue_type)
        ↓
  2. Topic Extractor       (+ assessment context)
        ↓
  3. Emotion Analyzer      (+ topics)
        ↓
  4. Speaker Analyzer      (+ topics + emotions)
        ↓
  5. Summarizer           (+ all previous)
        ↓
  [Conditional: >= standard]
  6. Key Moments          (+ all previous)
        ↓
  [Conditional: >= detailed]
  7. Timeline Builder     (+ all previous)
        ↓
  [Conditional: comprehensive OR has_links]
  8. Context Links        (Crawl4AI + Searxng)
        ↓
  Aggregate → Supervisor Synthesizer → Response
```

---

## Detail Levels

| Level | Messages | Agents | Example Output |
|-------|----------|--------|----------------|
| **micro** | 1-5 | 2 | "😊 Дружелюбная беседа. Обсудили планы." |
| **minimal** | 6-15 | 3 | Темы + тон + параграф |
| **standard** | 16-50 | 6 | Полный анализ + ключевые моменты |
| **detailed** | 51-100 | 7 | + хронология + эмоц. динамика |
| **comprehensive** | >100 | 8 | + внешние ссылки + Neo4j |

---

## Dialogue Types

- **business_meeting** - решения, action items
- **brainstorming** - идеи, альтернативы
- **problem_solving** - проблемы, решения
- **casual_chat** - темы, мнения
- **conflict_resolution** - конфликты, компромиссы

---

## Workflows to Import

### Core Agents (Required)

1. **agent_dialogue_assessor.json** - Оценка и классификация диалога
2. **agent_emotion_analyzer.json** - Эмоциональный анализ
3. **agent_topic_extractor.json** - Извлечение тем (UPDATED)
4. **agent_speaker_analyzer.json** - Анализ участников (UPDATED)  
5. **agent_summarizer.json** - Адаптивное резюме (UPDATED)
6. **agent_key_moments.json** - Ключевые моменты
7. **agent_timeline.json** - Хронология (conditional)
8. **agent_context_links.json** - Внешний контекст (conditional)
9. **agent_supervisor_synthesizer.json** - Финальный синтез

### Orchestrator

10. **group_digest_orchestrator_v2_sequential.json** - Главный оркестратор

---

## Import Instructions

### 1. Backup Current Workflows

```bash
cd /home/ilyasni/n8n-server/n8n-installer
cp n8n/workflows/group_digest_orchestrator.json \
   n8n/workflows/group_digest_orchestrator_v1_backup.json
```

### 2. Import New Workflows in n8n

**Порядок импорта:**

1. Import все agent workflows (1-9)
2. Import orchestrator v2
3. Configure Execute Workflow nodes:
   - В orchestrator v2 настроить каждый Execute Workflow node
   - Выбрать соответствующий agent workflow

**Шаги в n8n UI:**

```
1. Settings → Import from File
2. Выбрать agent_dialogue_assessor.json → Import
3. Повторить для всех agent_*.json файлов
4. Import group_digest_orchestrator_v2_sequential.json
5. Открыть orchestrator v2
6. Для каждого Execute Workflow node:
   - Click node → Select Workflow
   - Выбрать соответствующий Agent workflow
7. Save workflow
8. Activate workflow
```

### 3. Configure Environment

**В `.env` или через docker-compose:**

```bash
# V2 Pipeline Settings
USE_DIGEST_V2=false  # Start with V1, switch to V2 after testing
N8N_GROUP_DIGEST_WEBHOOK_V2=http://n8n:5678/webhook/group-digest-v2
N8N_DIGEST_TIMEOUT_V2=180  # 3 minutes for sequential pipeline

# Optional: Neo4j (for comprehensive level)
NEO4J_ENABLED=false
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Optional: Crawl4AI (for link analysis)
CRAWL4AI_ENABLED=false
CRAWL4AI_URL=http://crawl4ai:11235

# Optional: Searxng (for topic research)
SEARXNG_ENABLED=false
SEARXNG_URL=http://searxng:8080
```

### 4. Test Pipeline

**Test V1 (current):**
```bash
curl -X POST http://localhost:5678/webhook/group-digest \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [/* test messages */],
    "user_id": 123,
    "group_id": 456,
    "hours": 24
  }'
```

**Test V2 (sequential):**
```bash
curl -X POST http://localhost:5678/webhook/group-digest-v2 \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [/* test messages */],
    "user_id": 123,
    "group_id": 456,
    "hours": 24
  }'
```

### 5. Switch to V2

После успешного тестирования:

```bash
# В .env или через environment variables
USE_DIGEST_V2=true

# Restart telethon
docker compose restart telethon
```

---

## Performance Expectations

| Level | Agents Active | Expected Time |
|-------|---------------|---------------|
| micro | 2 | <10s |
| minimal | 3 | <20s |
| standard | 6 | <50s |
| detailed | 7 | <90s |
| comprehensive | 8 + external | <150s |

---

## Troubleshooting

### Issue: Workflows not executing sequentially

**Solution:** Check Execute Workflow node configuration
- Убедитесь что выбран правильный workflow
- Проверьте что все workflows активны

### Issue: Timeout errors

**Solution:** Increase timeout
```bash
N8N_DIGEST_TIMEOUT_V2=240  # 4 minutes
```

### Issue: Empty emotions/key_moments

**Solution:** Normal for micro/minimal levels
- micro: только emotion tone
- minimal: нет key moments
- standard+: full analysis

---

## Migration Path

### Week 1: Test V2 in Parallel

```bash
USE_DIGEST_V2=false  # Stay on V1
```

Test V2 manually через `/webhook/group-digest-v2`

### Week 2: Gradual Rollout

```bash
USE_DIGEST_V2=true   # Switch to V2
```

Monitor logs, compare quality

### Week 3: Enable Integrations

```bash
NEO4J_ENABLED=true
CRAWL4AI_ENABLED=true
SEARXNG_ENABLED=true
```

---

## Rollback Plan

Если V2 вызывает проблемы:

```bash
# 1. Switch back to V1
USE_DIGEST_V2=false

# 2. Restart
docker compose restart telethon

# 3. Check logs
docker logs telethon --tail 50 | grep "Pipeline:"
# Should show: "Pipeline: V1 Parallel"
```

---

**Status:** ✅ V2 workflows created, ready for import  
**Next Step:** Import workflows в n8n UI и настроить Execute Workflow nodes

