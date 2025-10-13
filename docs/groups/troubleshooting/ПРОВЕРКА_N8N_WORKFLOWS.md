# 🔍 Проверка n8n workflows - Решение 500 ошибки

**Дата:** 13 октября 2025  
**Проблема:** n8n возвращает 500 ошибку, бот показывает старые данные

---

## 🐛 Что происходит

**Логи бота показывают:**
```
ERROR:group_digest_generator:❌ n8n workflow error: 500
ERROR:group_digest_generator:❌ Ошибка генерации дайджеста: n8n workflow failed: 500
```

**n8n возвращает правильные данные**, но бот их не получает из-за 500 ошибки.

---

## ✅ Что нужно проверить в n8n UI

### Шаг 1: Откройте n8n

```
https://n8n.produman.studio
```

### Шаг 2: Проверьте какие workflows активны

**Workflows → Проверьте статус:**

| Workflow | Должен быть |
|----------|-------------|
| Group Digest Orchestrator (Sub-workflows) | ✅ **Active (зеленый)** |
| Group Dialogue Multi-Agent Analyzer v2 | ❌ **Inactive (серый)** |
| Agent: Topic Extractor | ⚪ Не активен (нормально!) |
| Agent: Speaker Analyzer | ⚪ Не активен (нормально!) |
| Agent: Context Summarizer | ⚪ Не активен (нормально!) |

**Если v2 активен:**
1. Откройте "Group Dialogue Multi-Agent Analyzer v2"
2. Active → **OFF**
3. Save

**Если Orchestrator НЕ активен:**
1. Откройте "Group Digest Orchestrator"
2. Active → **ON**
3. Save

---

### Шаг 3: Проверьте Execute Workflow узлы в Orchestrator

1. Откройте **"Group Digest Orchestrator"**
2. Кликните на узел **"Execute: Topic Extractor"**
3. В поле **"Workflow"** должно быть выбрано: **"Agent: Topic Extractor"**
4. Повторите для других Execute узлов:
   - Execute: Speaker Analyzer → Agent: Speaker Analyzer
   - Execute: Summarizer → Agent: Context Summarizer

**Если не выбрано:**
- Выберите нужный agent из выпадающего списка
- Save
- Active → ON

---

### Шаг 4: Проверьте последние Executions

1. В меню слева: **Executions**
2. Посмотрите последние выполнения

**Должны видеть:**
- ✅ Group Digest Orchestrator - **зеленый** (success)
- ✅ Agent: Topic Extractor - зеленый
- ✅ Agent: Speaker Analyzer - зеленый
- ✅ Agent: Context Summarizer - зеленый

**Если видите красные (ошибки):**
1. Кликните на красный execution
2. Посмотрите какой узел упал
3. Откройте этот узел
4. Прочитайте ошибку в логах

**Возможные ошибки:**
- "Referenced node doesn't exist" → Execute узлы не настроены (Шаг 3)
- "Workflow not found" → Агенты не импортированы
- GigaChat timeout → Проверьте gpt2giga-proxy

---

### Шаг 5: Протестируйте workflow вручную

1. Откройте **"Group Digest Orchestrator"**
2. Нажмите **Execute Workflow** (справа вверху)
3. В test panel укажите тестовые данные:

```json
{
  "messages": [
    {"username": "alice", "text": "Привет всем!", "date": "2025-10-13T10:00:00Z"},
    {"username": "bob", "text": "Как дела?", "date": "2025-10-13T10:01:00Z"}
  ],
  "user_id": 1,
  "group_id": 1,
  "hours": 6
}
```

4. Нажмите **Execute**
5. Проверьте что все узлы зеленые
6. Откройте узел **"Aggregate Results"**
7. Проверьте что в Output есть:
   - topics: [...]
   - speakers_summary: {...}
   - overall_summary: "..."
   - message_count: 2
   - period: "6 hours"

**Если тест прошел успешно** → workflow настроен правильно, проблема в чем-то другом.

**Если тест провалился** → смотрите какой узел красный и исправляйте.

---

## 🔧 Решение проблем

### Проблема: v2 и Orchestrator оба активны

**Симптом:** В списке workflows оба зеленые

**Решение:**
1. Деактивируйте v2: Active OFF
2. Оставьте только Orchestrator: Active ON

**Причина:** Оба слушают `/webhook/group-digest`, конфликт!

---

### Проблема: Orchestrator падает с ошибкой

**Симптом:** Красные executions в логах

**Причины:**
1. Execute узлы не настроены
2. Агенты не импортированы
3. gpt2giga-proxy недоступен

**Решение:**
1. Проверьте Execute узлы (Шаг 3)
2. Реимпортируйте агентов если нужно
3. Проверьте gpt2giga-proxy:
   ```bash
   docker ps | grep gpt2giga
   docker logs gpt2giga-proxy
   ```

---

### Проблема: Агенты не в выпадающем списке

**Симптом:** Не могу выбрать Agent в Execute узле

**Причина:** Агенты не импортированы

**Решение:**
1. Import from File → agent_topic_extractor.json
2. Import from File → agent_speaker_analyzer.json
3. Import from File → agent_summarizer.json
4. НЕ активируйте агентов!
5. Потом настройте Execute узлы в Orchestrator

---

## ✅ После исправления

1. **Протестируйте в Telegram боте:**
   ```
   /group_digest 8
   ```

2. **Должно показать:**
   - ✅ Правильный period: "8 hours"
   - ✅ Правильный message_count (реальное число)
   - ✅ Темы извлечены
   - ✅ Спикеры проанализированы
   - ✅ Резюме сгенерировано
   - ✅ **БЕЗ ошибки Markdown!**

3. **Проверьте n8n Executions:**
   - Должны видеть 4 зеленых execution
   - Orchestrator + 3 агента

---

## 📊 Чеклист диагностики

- [ ] v2 деактивирован (Active OFF)
- [ ] Orchestrator активен (Active ON)
- [ ] Execute узлы в Orchestrator настроены (агенты выбраны)
- [ ] Агенты импортированы (НЕ активны)
- [ ] Ручной тест Orchestrator прошел успешно
- [ ] gpt2giga-proxy работает (docker ps)
- [ ] `/group_digest 8` работает без ошибок
- [ ] Нет ошибки "Can't parse entities"

---

## 🎓 Что было исправлено в Python

**Файл:** `telethon/group_digest_generator.py`

**Изменения:**
- ✅ Добавлено экранирование Markdown в `format_digest_for_telegram`
- ✅ Экранированы: topics, usernames, summaries, reasons, key_points
- ✅ Используется `escape_markdown_v2()` из `markdown_utils.py`

**Результат:**
- Больше нет ошибки "Can't parse entities"
- Все специальные символы корректно отображаются

---

**Выполните проверку по этому чеклисту и сообщите результат!** 🚀

