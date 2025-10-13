# ✅ Cursor Rules v3.3.0 - Groups Module Added

**Дата:** 13 октября 2025  
**Статус:** ✅ Полностью актуализировано с Groups функционалом

---

## 🎯 Что добавлено

### 🆕 Модуль 10-groups.mdc (472 строки)

Полностью задокументирован функционал **Telegram Groups**:

#### 📊 Database Models

```python
# Модели для работы с группами
- Group                  # Telegram группы
- GroupMention          # @упоминания пользователей
- GroupSettings         # Настройки групп
- user_group           # Association table
```

#### 🤖 Bot Commands

```python
/add_group              # Добавить группу (public/private)
/my_groups             # Список групп пользователя
/group_digest [hours]  # AI-дайджест диалогов
/group_settings        # Настройки группы
/debug_group_digest    # Отладка дайджестов
/debug_n8n             # Отладка n8n workflows
```

#### 🔄 n8n Multi-Agent Workflows

**Sub-workflows архитектура:**

```
Group Digest Orchestrator (main workflow)
    ↓
    ├── Agent 1: Topic Extractor      # Извлечение тем
    ├── Agent 2: Speaker Analyzer     # Анализ спикеров
    └── Agent 3: Summarizer           # Общее резюме
    ↓
Aggregate Results → Format Response
```

**Workflows:**
- `group_digest_orchestrator.json` - главный workflow (активный)
- `agent_topic_extractor.json` - sub-workflow 1
- `agent_speaker_analyzer.json` - sub-workflow 2
- `agent_summarizer.json` - sub-workflow 3
- `group_mention_analyzer_v2.json` - анализ упоминаний

#### ✍️ Markdown V2 Escaping

```python
# markdown_utils.py
from markdown_utils import escape_markdown_v2

# ✅ ВСЕГДА экранируйте текст для Telegram
group_name = escape_markdown_v2(group.group_name)
summary = escape_markdown_v2(digest["overall_summary"])

await update.message.reply_text(
    f"📊 Дайджест: {group_name}\n\n{summary}",
    parse_mode="MarkdownV2"
)
```

#### 🔐 Subscription Limits

```python
# Проверка лимита групп
class User(Base):
    def can_add_group(self) -> bool:
        tier = SUBSCRIPTION_TIERS.get(self.subscription_type, {})
        max_groups = tier.get("max_groups", 0)
        return len(self.groups) < max_groups

# Usage
if not user.can_add_group():
    await update.message.reply_text(
        f"❌ Лимит групп: {user.max_groups}"
    )
```

#### 🔍 Private Groups Support

```python
# Обработка приватных групп (invite links)
if "+c4BzS2" in group_url or group_url.startswith("https://t.me/+"):
    # Iterate through user's dialogs
    async for dialog in client.iter_dialogs():
        if dialog.is_group or dialog.is_channel:
            # Match by invite hash or ID
            ...
```

---

## 📁 Файлы проекта

### Python Files

```bash
telethon/
├── group_monitor_service.py      # Мониторинг @упоминаний
├── group_digest_generator.py     # Генерация дайджестов
├── bot_group_debug.py            # Debug commands
├── markdown_utils.py             # Markdown V2 escaping
├── bot.py                        # Bot commands (updated)
└── models.py                     # Database models (updated)
```

### n8n Workflows

```bash
n8n/workflows/
├── group_digest_orchestrator.json     # Main workflow ⭐
├── agent_topic_extractor.json        # Sub-workflow 1
├── agent_speaker_analyzer.json       # Sub-workflow 2
├── agent_summarizer.json             # Sub-workflow 3
├── group_mention_analyzer_v2.json    # Mention analysis
├── НАСТРОЙКА_SUB_WORKFLOWS.md        # Setup guide (RU)
└── SUB_WORKFLOWS_GUIDE.md            # Setup guide (EN)
```

### Documentation

```bash
docs/groups/
├── quickstart/
│   ├── БЫСТРЫЙ_СТАРТ.md             # Quick start (RU)
│   └── QUICK_START_SUB_WORKFLOWS.md # Quick start (EN)
├── deployment/
│   ├── GROUPS_DEPLOYMENT_GUIDE.md
│   └── PRIVATE_GROUPS_GUIDE.md
├── implementation/
│   ├── SUB_WORKFLOWS_IMPLEMENTATION.md
│   └── GROUPS_FINAL_REPORT.md
└── troubleshooting/
    ├── ПРОВЕРКА_N8N_WORKFLOWS.md
    ├── ИСПРАВЛЕНИЕ_ОШИБКИ_REFERENCED_NODE.md
    └── ИТОГОВОЕ_ИСПРАВЛЕНИЕ.md
```

---

## 🎯 Критичные паттерны в 10-groups.mdc

### 1. User + Group Filtering

```python
# ✅ ВСЕГДА фильтруйте по user_id И group_id
mentions = db.query(GroupMention).filter(
    GroupMention.user_id == user_id,
    GroupMention.group_id == group_id
).all()

# ❌ НИКОГДА без фильтрации
mentions = db.query(GroupMention).all()  # NO! Data leak!
```

### 2. Markdown V2 Escaping

```python
# ✅ ВСЕГДА экранируйте спецсимволы
from markdown_utils import escape_markdown_v2

text = escape_markdown_v2(user_input)

# ❌ НИКОГДА без экранирования
text = user_input  # NO! Может упасть на символе '_'
```

### 3. Subscription Checks

```python
# ✅ ВСЕГДА проверяйте лимиты
if user.can_add_group():
    user.groups.append(group)
else:
    raise HTTPException(403, "Group limit reached")

# ❌ НИКОГДА без проверки
user.groups.append(group)  # NO! Превышение лимита!
```

### 4. n8n Workflow References

```javascript
// ✅ ВСЕГДА по имени workflow
{
  "workflowId": "Agent: Topic Extractor",  // По имени!
  "source": "data"
}

// ❌ НИКОГДА по ID
{
  "workflowId": "123"  // NO! ID может измениться!
}
```

### 5. Aggregate Fallbacks

```javascript
// ✅ ВСЕГДА с fallback
const topics = $('Agent 4: Aggregator').first().json?.topics || 
               $('Agent 1: Topic Extractor').first().json?.topics || 
               [];

// ❌ НИКОГДА без fallback
const topics = $('Agent 4').first().json.topics;  // NO! Может быть null!
```

---

## 📊 Обновленная статистика

### Cursor Rules Modules

| # | Модуль | Строк | Функционал |
|---|--------|-------|------------|
| 0 | `.cursorrules` | 280 | Entry point + Groups |
| 1 | `01-core.mdc` | 406 | Core patterns |
| 2 | `02-architecture.mdc` | 332 | Microservices |
| 3 | `03-database.mdc` | 433 | PostgreSQL, Redis |
| 4 | `04-development.mdc` | 487 | Workflow |
| 5 | `05-security.mdc` | 463 | QR Login, auth |
| 6 | `06-admin.mdc` | 537 | Admin Panel |
| 7 | `07-rag.mdc` | 543 | RAG, AI |
| 8 | `08-api.mdc` | 525 | FastAPI |
| 9 | `09-external.mdc` | 424 | External services |
| **10** | **`10-groups.mdc`** | **472** | **🆕 Groups** |

**Total:** 10 modules, ~4,900 строк, avg ~463 строк/модуль

---

## ✅ Что теперь документировано

### Database Layer

- [x] Group model
- [x] GroupMention model
- [x] GroupSettings model
- [x] user_group association table
- [x] User.can_add_group() method
- [x] Timezone-aware datetime
- [x] User + Group filtering patterns

### Bot Layer

- [x] /add_group command
- [x] /my_groups command
- [x] /group_digest command
- [x] /group_settings command
- [x] /debug_group_digest command
- [x] Private groups support (invite links)
- [x] Markdown V2 escaping
- [x] Subscription limit checks

### n8n Layer

- [x] Sub-workflows architecture
- [x] group_digest_orchestrator.json
- [x] agent_topic_extractor.json
- [x] agent_speaker_analyzer.json
- [x] agent_summarizer.json
- [x] Execute Workflow nodes patterns
- [x] Aggregate Results fallbacks
- [x] Webhook configuration

### Utilities

- [x] markdown_utils.py
- [x] escape_markdown_v2() function
- [x] GroupDigestGenerator client
- [x] format_digest_for_telegram()

---

## 🚀 Как использовать

### 1. Cursor автоматически загрузит правила

При редактировании файлов Groups:

```python
# Эти файлы автоматически загрузят 10-groups.mdc:
telethon/group_monitor_service.py
telethon/group_digest_generator.py
telethon/bot.py (group commands)
n8n/workflows/group*.json
```

### 2. Quick Reference

```python
# Database
from models import Group, GroupMention, GroupSettings

# Markdown
from markdown_utils import escape_markdown_v2

# Digest
from group_digest_generator import GroupDigestGenerator

# Check limit
if user.can_add_group():
    # Add group
```

### 3. Verification

```bash
# Проверить что модуль загружен
grep -r "10-groups" .cursor/rules/

# Проверить размер
wc -l .cursor/rules/telegram-bot/10-groups.mdc
# 472 строк ✅
```

---

## 📖 Документация

### Cursor Rules

- `.cursor/rules/telegram-bot/10-groups.mdc` - **новый модуль**
- `.cursor/rules/telegram-bot/README.md` - обновлен (10 modules)
- `.cursor/rules/telegram-bot/CHANGELOG.mdc` - обновлен (v3.3.0 + Groups)

### Project Docs

- `docs/groups/` - вся документация Groups
- `n8n/workflows/НАСТРОЙКА_SUB_WORKFLOWS.md` - setup guide
- `CURSOR_RULES_V3.3_SUMMARY.md` - полный отчет

### Quick Links

- [10-groups.mdc](.cursor/rules/telegram-bot/10-groups.mdc) - модуль
- [БЫСТРЫЙ_СТАРТ.md](groups/quickstart/БЫСТРЫЙ_СТАРТ.md) - импорт workflows
- [GROUPS_DEPLOYMENT_GUIDE.md](groups/deployment/GROUPS_DEPLOYMENT_GUIDE.md) - развертывание

---

## ✅ Verification Checklist

- [x] 10-groups.mdc создан (472 строки)
- [x] Scope настроен (`telethon/*group*.py`, `n8n/workflows/group*.json`)
- [x] YAML frontmatter корректен
- [x] Rule Type: autoAttached
- [x] Priority: medium
- [x] Database models задокументированы
- [x] Bot commands задокументированы
- [x] n8n workflows задокументированы
- [x] Markdown V2 escaping включен
- [x] Subscription limits описаны
- [x] Private groups support описан
- [x] Quick Examples (✅/❌) добавлены
- [x] Verification Checklist добавлен
- [x] Deprecated Patterns описаны
- [x] README обновлен (10 modules)
- [x] CHANGELOG обновлен (v3.3.0 + Groups)
- [x] .cursorrules обновлен (10 modules)

---

## 🎯 Результат

✅ **Cursor Rules полностью актуализированы с Groups функционалом!**

**Теперь включает:**
- ✅ 10 модулей (было 9)
- ✅ Groups functionality полностью задокументирован
- ✅ Database models, Bot commands, n8n workflows
- ✅ Markdown V2 escaping patterns
- ✅ Subscription limits, Private groups
- ✅ Все < 550 строк (target: 500)
- ✅ Best practices от Cursor, Trigger.dev

**Version:** 3.3.0 ⭐  
**Status:** ✅ Production Ready + Groups  
**Total modules:** 10  
**Total lines:** ~4,900

---

**Готово к использованию!** 🚀

Cursor автоматически применит правила Groups при редактировании:
- `telethon/*group*.py`
- `n8n/workflows/group*.json`
- `telethon/bot.py` (group commands)

