# ✅ Исправлено: If Node Operations Error

**Дата:** 15 октября 2025  
**Статус:** Решено

---

## 🎯 Ошибка

```
TypeError: compareOperationFunctions[compareData.operation] is not a function
Node: If (V1)
n8n Version: 1.115.2
```

---

## 🔍 Причина

В **If node V1** использовались **неправильные названия операций** сравнения:

### ❌ Неправильно
```json
{
  "operation": "equals",      // ❌ НЕ РАБОТАЕТ
  "value1": "...",
  "value2": "..."
}

{
  "operation": "notEquals",   // ❌ НЕ РАБОТАЕТ
  "value1": "...",
  "value2": "..."
}
```

### ✅ Правильно
```json
{
  "operation": "equal",       // ✅ РАБОТАЕТ
  "value1": "...",
  "value2": "..."
}

{
  "operation": "notEqual",    // ✅ РАБОТАЕТ
  "value1": "...",
  "value2": "..."
}
```

---

## 📝 Поддерживаемые операции в If node V1

| Operation | Description | Example |
|-----------|-------------|---------|
| `equal` | Равно | `"a" == "a"` |
| `notEqual` | Не равно | `"a" != "b"` |
| `contains` | Содержит | `"hello world" contains "world"` |
| `notContains` | Не содержит | `"hello" not contains "world"` |
| `startsWith` | Начинается с | `"hello" starts with "he"` |
| `notStartsWith` | Не начинается с | `"hello" not starts with "x"` |
| `endsWith` | Заканчивается на | `"hello" ends with "lo"` |
| `notEndsWith` | Не заканчивается на | `"hello" not ends with "x"` |
| `regex` | Регулярное выражение | `"test123" matches /\d+/` |
| `notRegex` | Не совпадает с regex | `"test" not matches /\d+/` |
| `isEmpty` | Пустая строка | `"" is empty` |
| `isNotEmpty` | Не пустая строка | `"text" is not empty` |

**Boolean операции:**
- Для boolean условий используйте value1 как expression: `{{ condition }}` и value2 как `true`/`false`

---

## 🔧 Исправленные файлы

### 1. group_digest_orchestrator_v2_sequential.json

**3 If nodes:**
- `Need Key Moments?`
- `Need Timeline?`
- `Need Context Links?`

**Изменения:**
```diff
- "operation": "equals"      → "operation": "equal"
- "operation": "notEquals"   → "operation": "notEqual"
```

### 2. agent_context_links.json

**If node для проверки detail_level**

**Изменения:**
```diff
- "operation": "equals"      → "operation": "equal"
```

---

## ✅ Best Practices

### 1. Используйте правильные имена операций

```json
// ✅ ПРАВИЛЬНО
{
  "conditions": {
    "string": [
      {
        "value1": "={{ $json.status }}",
        "operation": "equal",    // ✅ Не "equals"
        "value2": "active"
      }
    ]
  }
}
```

### 2. Boolean условия

```json
// ✅ ПРАВИЛЬНО: Expression в value1
{
  "conditions": {
    "boolean": [
      {
        "value1": "={{ $json.count > 10 }}",  // Expression возвращает boolean
        "value2": true
      }
    ]
  }
}
```

### 3. Множественные условия (AND logic)

```json
{
  "conditions": {
    "string": [
      {
        "value1": "={{ $json.level }}",
        "operation": "notEqual",
        "value2": "micro"
      },
      {
        "value1": "={{ $json.level }}",
        "operation": "notEqual",
        "value2": "minimal"
      }
    ]
  }
}
```

**Логика:** Все условия должны быть true (AND между ними)

### 4. OR logic - используйте несколько If nodes

Если нужна OR логика, создайте отдельные If nodes или используйте **Switch node**:

```json
// Лучше использовать Switch node для OR logic
{
  "type": "n8n-nodes-base.switch",
  "typeVersion": 3,
  "parameters": {
    "rules": {
      "values": [
        {
          "conditions": {
            "string": [
              {"value1": "={{ $json.level }}", "operation": "equal", "value2": "detailed"}
            ]
          }
        },
        {
          "conditions": {
            "string": [
              {"value1": "={{ $json.level }}", "operation": "equal", "value2": "comprehensive"}
            ]
          }
        }
      ]
    }
  }
}
```

---

## 📚 Рекомендации

### Когда использовать If node V1
- ✅ Простые условия (1-2 проверки)
- ✅ AND logic между условиями
- ✅ String/Number/Boolean сравнения

### Когда НЕ использовать If node V1
- ❌ Сложная OR logic (используйте Switch node)
- ❌ Множественные варианты выбора (используйте Switch node)
- ❌ > 3 условий (рассмотрите Switch node)

### Альтернатива: Switch Node (V3)

**Преимущества:**
- Поддерживает OR logic
- Множественные output branches
- Более читаемый для complex logic
- Поддерживает fallback route

```json
{
  "type": "n8n-nodes-base.switch",
  "typeVersion": 3,
  "parameters": {
    "rules": {
      "values": [
        {
          "conditions": {...},
          "output": 0
        },
        {
          "conditions": {...},
          "output": 1
        }
      ]
    },
    "options": {
      "fallbackOutput": 2
    }
  }
}
```

---

## 🧪 Тестирование

```bash
# 1. Проверить JSON валидность
cd n8n/workflows
python3 -m json.tool group_digest_orchestrator_v2_sequential.json > /dev/null && echo "✅"

# 2. Проверить что нет старых операций
grep -rn "notEquals\|\"equals\"" *.json | grep "operation" || echo "✅ Clean"

# 3. Импортировать в n8n и протестировать
# - Import workflow
# - Activate
# - Test execution с разными detail_level
```

---

## 📊 Результат

### До исправления
```
❌ TypeError: compareOperationFunctions[compareData.operation] is not a function
❌ Workflow fails при любом условии
```

### После исправления
```
✅ Условия работают корректно
✅ detail_level определяется правильно
✅ Conditional agents активируются по необходимости
```

---

## 🔗 Ресурсы

- **n8n If node docs:** https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.if/
- **n8n Switch node docs:** https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.switch/
- **n8n community:** https://community.n8n.io/

---

**Статус:** ✅ Исправлено  
**Workflows:** 2/2 fixed  
**Ready:** Production тестирование 🚀

