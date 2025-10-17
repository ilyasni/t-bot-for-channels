# ✅ Исправлено: Динамические Token Budgets для n8n

## 🎯 Проблема
```
JSON parameter needs to be valid JSON
```

**Причина:** JavaScript `||` оператор и optional chaining `?.` **НЕ поддерживаются** в n8n expressions `={{ }}`.

---

## ✅ Решение: Prepare Node Pattern (Best Practice)

### ❌ Было (неправильно)
```javascript
// В n8n expression
"max_tokens": $json.assessment.token_budgets?.emotion || 400
```

### ✅ Стало (правильно)
```javascript
// В Code node (Prepare Prompt)
const maxTokens = (assessment.token_budgets && assessment.token_budgets.emotion) 
  ? assessment.token_budgets.emotion 
  : 400;

return [{json: {prompt, max_tokens: maxTokens}}];

// В HTTP Request node
"max_tokens": $json.max_tokens  // ✅ Просто ссылка
```

---

## 📝 Исправлено в workflows

1. ✅ **agent_topic_extractor.json** - динамический `max_tokens` из assessment
2. ✅ **agent_speaker_analyzer.json** - динамический `max_tokens` из assessment  
3. ✅ **agent_summarizer.json** - `max_tokens` из spec object
4. ✅ **agent_emotion_analyzer.json** - динамический `max_tokens` из assessment

**Фиксированные значения (для first launch):**
- agent_key_moments: 800
- agent_timeline: 800
- agent_supervisor_synthesizer: 1500

---

## ✅ Validation Results

```
✅ All JSONs valid
✅ No || operators in jsonBody
✅ No optional chaining in assignments
✅ All HTTP nodes use $json.max_tokens
✅ Prepare Node Pattern применен везде
```

---

## 🧪 Тестирование

```bash
# 1. Проверить что все workflows валидны
cd n8n/workflows && for f in agent_*.json; do 
  python3 -m json.tool "$f" > /dev/null && echo "✅ $f" || echo "❌ $f"
done

# 2. В Telegram
/group_digest
→ Выбрать группу → период

# 3. Проверить логи
docker logs telethon | grep "Detail Level" | tail -5
docker logs n8n | grep "max_tokens" | tail -10
```

---

## 📊 Token Budgets (Dynamic)

| Level | Topics | Emotion | Speakers | Summary | Total |
|-------|--------|---------|----------|---------|-------|
| micro | - | 100 | - | 150 | 250 |
| minimal | 200 | 200 | - | 300 | 700 |
| standard | 400 | 400 | 500 | 1000 | 3100 |
| detailed | 600 | 600 | 700 | 1500 | 5400 |
| comprehensive | 800 | 800 | 900 | 2000 | 7000 |

---

## 📚 Best Practices (из Context7)

1. ✅ **Всегда используйте Code node** для вычислений
2. ✅ **n8n expressions только для простых ссылок** (`$json.field`)
3. ✅ **Не используйте `||`** в expressions
4. ✅ **Optional chaining `?.` только в Code nodes** для чтения
5. ✅ **Ternary operator** вместо `||` для defaults

---

**Статус:** ✅ Готово к production тестированию  
**Next:** Протестировать `/group_digest` и оценить качество! 🚀

---

# ✅ Исправлено: If Node Operations Error (2)

## 🎯 Проблема #2
```
TypeError: compareOperationFunctions[compareData.operation] is not a function
```

**Причина:** If node V1 использовал неправильные названия операций.

---

## ✅ Решение

### ❌ Было
```json
"operation": "equals"      // ❌ НЕ РАБОТАЕТ в n8n 1.115.2
"operation": "notEquals"   // ❌ НЕ РАБОТАЕТ
```

### ✅ Стало  
```json
"operation": "equal"       // ✅ РАБОТАЕТ
"operation": "notEqual"    // ✅ РАБОТАЕТ
```

---

## 📝 Исправлено

1. ✅ **group_digest_orchestrator_v2_sequential.json** - 3 If nodes
2. ✅ **agent_context_links.json** - 1 If node

---

## 📚 Supported Operations (If node V1)

| Operation | Description |
|-----------|-------------|
| `equal` | Равно (НЕ "equals") |
| `notEqual` | Не равно (НЕ "notEquals") |
| `contains` | Содержит |
| `startsWith` | Начинается с |
| `endsWith` | Заканчивается на |
| `regex` | Регулярное выражение |
| `isEmpty` | Пустая строка |

💡 **Tip:** Для сложной логики используйте **Switch node (V3)**

---

**Статус:** ✅ Исправлено  
**Details:** IF_NODE_FIX.md
