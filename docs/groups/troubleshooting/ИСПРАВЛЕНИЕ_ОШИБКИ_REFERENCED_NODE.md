# ✅ Исправление ошибки "Referenced node doesn't exist"

**Дата:** 13 октября 2025  
**Ошибка:** `Cannot assign to read only property 'name' of object 'Error: Referenced node doesn't exist'`

---

## 🔍 Что случилось?

Эта ошибка возникает когда **Execute Workflow узлы не настроены** - не выбраны агенты.

В оркестраторе есть 3 узла "Execute Workflow":
- Execute: Topic Extractor
- Execute: Speaker Analyzer
- Execute: Summarizer

Каждый из них должен быть настроен - нужно выбрать какой agent workflow вызывать.

---

## ✅ Решение (5 минут)

### Шаг 1: Откройте оркестратор

В n8n UI:
1. Workflows
2. Кликните на **"Group Digest Orchestrator"**

### Шаг 2: Настройте Execute Workflow узлы

Вы увидите workflow с 6 узлами. Нужно настроить 3 "Execute" узла:

#### A) Execute: Topic Extractor

1. **Кликните** на узел "Execute: Topic Extractor"
2. В правой панели найдите поле **"Workflow"**
3. Кликните на **выпадающий список**
4. Выберите **"Agent: Topic Extractor"** из списка
5. Узел обновится (галочка исчезнет если была)

#### B) Execute: Speaker Analyzer

1. **Кликните** на узел "Execute: Speaker Analyzer"
2. В поле **"Workflow"** выберите **"Agent: Speaker Analyzer"**

#### C) Execute: Summarizer

1. **Кликните** на узел "Execute: Summarizer"
2. В поле **"Workflow"** выберите **"Agent: Context Summarizer"**

### Шаг 3: Сохраните и активируйте

1. Нажмите **Save** (справа вверху)
2. Переключите **Active → ON** (зеленый)
3. Нажмите **Save** еще раз

---

## 🎯 Что должно получиться

После настройки в каждом Execute узле должно быть:

| Узел | Значение в поле "Workflow" |
|------|----------------------------|
| Execute: Topic Extractor | Agent: Topic Extractor ✅ |
| Execute: Speaker Analyzer | Agent: Speaker Analyzer ✅ |
| Execute: Summarizer | Agent: Context Summarizer ✅ |

---

## 🧪 Тестируйте

После настройки в Telegram боте:
```
/debug_group_digest 6
```

**Должно работать без ошибок!**

---

## ⚠️ Если агентов нет в списке

**Проблема:** Выпадающий список пустой или нет нужных агентов

**Причина:** Агенты не импортированы

**Решение:**
1. Вернитесь к началу инструкции
2. Импортируйте 3 агента:
   - `agent_topic_extractor.json`
   - `agent_speaker_analyzer.json`
   - `agent_summarizer.json`
3. Потом снова настройте Execute узлы

---

## 📁 Обновленные файлы

**Исправлен файл:**
- `n8n/workflows/group_digest_orchestrator.json`

**Что изменилось:**
1. Убраны некорректные `workflowId` из Execute узлов
2. Добавлена обработка ошибок в код "Aggregate Results"
3. Теперь показывается понятная ошибка если узлы не настроены

**Действие:**
- Если вы уже импортировали старый orchestrator - **удалите его**
- **Реимпортируйте** новый файл `group_digest_orchestrator.json`
- Настройте Execute узлы как описано выше

---

## 🔄 Пошаговый план

1. **Удалите старый оркестратор** (если импортировали)
   - Workflows → "Group Digest Orchestrator" → Delete

2. **Реимпортируйте новый:**
   - Import from File → `group_digest_orchestrator.json`

3. **Настройте Execute узлы:**
   - Execute: Topic Extractor → Agent: Topic Extractor
   - Execute: Speaker Analyzer → Agent: Speaker Analyzer
   - Execute: Summarizer → Agent: Context Summarizer

4. **Активируйте:**
   - Active → ON
   - Save

5. **Тестируйте:**
   ```
   /debug_group_digest 6
   ```

---

## ✅ После исправления

Должно работать:
- ✅ Нет ошибки "Referenced node doesn't exist"
- ✅ Дайджест генерируется
- ✅ message_count правильный
- ✅ period соответствует запрошенному

---

**Продолжайте настройку!** 🚀

