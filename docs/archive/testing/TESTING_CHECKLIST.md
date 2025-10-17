# 🧪 Чеклист тестирования V2 Adaptive Digest

## ✅ Pre-flight Check

```bash
cd /home/ilyasni/n8n-server/n8n-installer/n8n/workflows

# 1. Все workflows валидны
for f in agent_*.json group_digest_orchestrator_v2_sequential.json; do
  python3 -m json.tool "$f" > /dev/null && echo "✅ $f" || echo "❌ $f"
done

# 2. Нет || в jsonBody
grep " || " agent_*.json | grep "jsonBody" || echo "✅ Clean"

# 3. Docker services running
docker ps | grep -E "(n8n|telethon|gpt2giga)" | wc -l
# Должно быть >= 3
```

---

## 📋 Import Workflows в n8n

1. **Зайти в n8n UI:** `http://your-server:5678`

2. **Import workflows в следующем порядке:**
   - ✅ `agent_dialogue_assessor.json` (первым!)
   - ✅ `agent_topic_extractor.json`
   - ✅ `agent_emotion_analyzer.json`
   - ✅ `agent_speaker_analyzer.json`
   - ✅ `agent_key_moments.json`
   - ✅ `agent_timeline.json`
   - ✅ `agent_summarizer.json`
   - ✅ `agent_supervisor_synthesizer.json`
   - ✅ `group_digest_orchestrator_v2_sequential.json` (последним!)

3. **Activate all workflows**

4. **В orchestrator:** Для каждого `Execute Workflow` node:
   - Открыть node
   - Выбрать workflow из dropdown
   - Save

---

## 🧪 Тест 1: Micro Digest (1-5 сообщений)

```bash
# Telegram → отправить боту
/group_digest
→ Выбрать малоактивную группу (или test group с 2-3 сообщениями)
→ Выбрать период: 2ч или 8ч

# Ожидаемый результат:
Detail Level: micro
Длина дайджеста: 1 предложение + эмодзи
Время генерации: <10s
```

**Пример output:**
```
😊 Повседневная беседа о планах на выходные.
```

---

## 🧪 Тест 2: Minimal Digest (6-15 сообщений)

```bash
/group_digest
→ Выбрать среднеактивную группу
→ Период: 12ч

# Ожидаемый результат:
Detail Level: minimal
Длина: 2-3 предложения
Темы: 2-3
Время: <20s
```

**Пример output:**
```
📊 Дайджест: 12 часов | 8 сообщений

🎯 Темы:
1. Планы на выходные
2. Новый ресторан

😊 Тон: Позитивный, дружелюбный

Участники обсудили планы на выходные...
```

---

## 🧪 Тест 3: Standard Digest (16-50 сообщений)

```bash
/group_digest
→ Выбрать активную рабочую группу
→ Период: 24ч

# Ожидаемый результат:
Detail Level: standard
Темы: 3-5 с приоритетами
Участники: роли и вклад
Ключевые моменты: решения, вопросы
Время: <45s
```

**Пример output:**
```
📊 Дайджест: Core Banking team | 24 часа | 35 сообщений

🎯 Основные темы:
1. 🔴 Проблема с вебвью (high)
2. ⚙️ Корректировка витрины (medium)
3. 📋 Инструкция (low)

😐 Тон: Нейтрально-озабоченный (0.55)
   Атмосфера: Профессиональное обсуждение с элементами беспокойства

👥 Активные участники:
• @Оксана: Инициатор, выявила проблему
• @Иван: Эксперт, предложил решение

⚡ Ключевые моменты:
✅ РЕШЕНИЕ: Отложить использование нового вебвью
   ...

📝 Резюме:
Команда обсуждала проблемы с новым функционалом...
```

---

## 🧪 Тест 4: Detailed Digest (51-100 сообщений)

```bash
/group_digest
→ Очень активная группа
→ Период: 24ч

# Ожидаемый результат:
Detail Level: detailed
+ Хронология с эмоциональной динамикой
+ Эмоциональная arc
Время: <75s
```

---

## 📊 Проверка логов

```bash
# 1. Telethon logs - Pipeline info
docker logs telethon 2>&1 | grep -E "(Pipeline|Detail Level|Token Budget)" | tail -20

# Ожидаемое:
# Pipeline: V2 Sequential
# Detail Level: standard
# Dialogue Type: problem_solving
# Token Budget - Topics: 400

# 2. n8n logs - Workflow execution
docker logs n8n 2>&1 | grep -E "(Enqueued|finished successfully|ERROR)" | tail -30

# 3. GigaChat proxy logs
docker logs gpt2giga-proxy 2>&1 | tail -20

# 4. Errors?
docker logs n8n 2>&1 | grep -i "error" | tail -10
docker logs telethon 2>&1 | grep "❌" | tail -10
```

---

## ✅ Success Criteria

### Технические
- ✅ Все workflows imported и active
- ✅ Нет ошибок "JSON parameter needs to be valid JSON"
- ✅ max_tokens динамически вычисляются
- ✅ Dialogue Assessor определяет правильный detail_level
- ✅ Каждый агент получает соответствующий token_budget

### Качество дайджестов
- ✅ **Micro:** Действительно краткий (1 предложение)
- ✅ **Minimal:** Темы + короткое резюме (2-3 предложения)
- ✅ **Standard:** Полноценный анализ с участниками и ключевыми моментами
- ✅ **Detailed:** Хронология + эмоциональная динамика

### Эмоциональный анализ
- ✅ Определяется общий тон (positive/neutral/negative)
- ✅ Атмосфера описывается адекватно
- ✅ Индикаторы (conflict, collaboration, stress) корректны

### Performance
- ✅ Micro: <10s
- ✅ Minimal: <20s
- ✅ Standard: <45s
- ✅ Detailed: <75s

---

## 🐛 Troubleshooting

### Ошибка: "Required property workflowId missing"
**Решение:** В orchestrator для каждого Execute Workflow node выбрать workflow через dropdown

### Ошибка: "JSON parameter needs to be valid JSON"
**Решение:** Проверить что в HTTP Request nodes используется `$json.max_tokens`, а не `|| 400`

### Дайджест всегда одинаковый уровень
**Решение:** Проверить Dialogue Assessor - правильно ли определяется messageCount и detailLevel

### max_tokens всегда фиксированный
**Решение:** Проверить что assessment.token_budgets передается из Dialogue Assessor

### Агенты не видят результаты друг друга
**Решение:** Проверить структуру orchestrator - должен быть sequential, не parallel

---

## 📝 Результаты

| Test | Detail Level | Messages | Time | Status | Notes |
|------|-------------|----------|------|--------|-------|
| 1 | micro | 3 | ? | ⏳ | |
| 2 | minimal | 12 | ? | ⏳ | |
| 3 | standard | 35 | ? | ⏳ | |
| 4 | detailed | 75 | ? | ⏳ | |

---

## ✅ Sign-off

- [ ] Все тесты пройдены
- [ ] Логи чистые (нет errors)
- [ ] Качество дайджестов соответствует ожиданиям
- [ ] Performance в рамках нормы
- [ ] Готово к production использованию

**Тестировал:** _____________  
**Дата:** _____________  
**Статус:** ⏳ В процессе / ✅ Готово / ❌ Требует доработки

