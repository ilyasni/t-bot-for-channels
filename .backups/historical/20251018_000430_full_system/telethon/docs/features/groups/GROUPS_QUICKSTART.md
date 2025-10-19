# 👥 Telegram Groups Integration - Quick Start

**Версия:** 1.0  
**Дата:** 15 января 2025  
**Статус:** ✅ Реализовано

---

## 📋 Описание

Интеграция Telegram групп добавляет два мощных функционала:

1. **📊 Дайджесты диалогов** - AI-анализ разговоров за N часов с выделением тем и спикеров
2. **🔔 Real-time уведомления** - моментальные уведомления при упоминании (@username) с контекстом и причиной

**Ключевые возможности:**
- ✅ Multi-agent анализ через GigaChat (4 AI агента)
- ✅ Параллельная обработка для скорости (15-25 сек)
- ✅ Интеграция с n8n workflows (без увеличения Docker образа)
- ✅ Лимиты по подпискам (free: 2 группы, basic: 5, premium: 20)
- ✅ Настраиваемые уведомления через админ панель

---

## 🚀 Быстрый старт

### Шаг 1: Импорт n8n Workflows

**Важно:** Сначала импортируйте workflows в n8n!

1. Откройте n8n UI: `https://n8n.produman.studio`
2. Перейдите в **Workflows** → **Import from File**
3. Импортируйте файлы:
   - `n8n/workflows/group_dialogue_multi_agent.json`
   - `n8n/workflows/group_mention_analyzer.json`
4. **Активируйте оба workflow** (переключатель справа)

**Проверка:**
```bash
curl -X POST http://localhost:5678/webhook/group-digest \
  -H "Content-Type: application/json" \
  -d '{"messages": [], "user_id": 1, "group_id": 1, "hours": 24}'

# Должен вернуть JSON с темами, спикерами и резюме
```

### Шаг 2: Применить миграцию БД

```bash
# Из директории telethon/
cd /home/ilyasni/n8n-server/n8n-installer/telethon

# Запустить миграцию
python scripts/migrations/add_groups_support.py migrate

# Результат:
# ✅ Созданы таблицы: groups, user_group, group_mentions, group_settings
```

**Rollback (если нужно):**
```bash
python scripts/migrations/add_groups_support.py rollback
```

### Шаг 3: Перезапустить контейнеры

```bash
# Из корня проекта
docker restart telethon telethon-bot

# Проверить логи
docker logs telethon -f
# Должно быть:
# ✅ GroupMonitorService инициализирован
# 👀 Запуск мониторинга групп...
```

### Шаг 4: Добавить группу

В Telegram боте:

```
/add_group https://t.me/your_group
```

Или с ID:
```
/add_group -1001234567890
```

**Результат:**
```
✅ Группа "Моя группа" добавлена!

🔔 Мониторинг упоминаний активирован
📊 Используйте /group_digest для получения резюме разговоров

Настройки: /group_settings
```

### Шаг 5: Тестирование

**Тест 1: Упоминание в группе**
1. В добавленной группе напишите: `@ваш_username помоги с задачей`
2. В течение 5 секунд вы получите уведомление в личные сообщения:
   ```
   🟡 Вас упомянули в группе: Моя группа
   
   Контекст: Обсуждение технической проблемы
   Почему упомянули: Запрос помощи
   
   Ключевые моменты:
   • Нужна помощь с задачей
   • Срочность: medium
   
   [Перейти к сообщению](https://t.me/...)
   ```

**Тест 2: Дайджест диалога**
```
/group_digest 24
```

Через 20-30 секунд получите:
```
# 📊 Дайджест группы: Моя группа
**Период:** 24 hours
**Сообщений проанализировано:** 150

## 🎯 Основные темы:
1. Python разработка
2. Docker конфигурация
3. База данных

## 👥 Активные участники:
• @alice: Обсуждала настройку Docker...
• @bob: Предлагал решения по Python...
• @charlie: Делился опытом с PostgreSQL...

## 📝 Резюме:
Обсуждение технических вопросов...
```

---

## ⚙️ Настройки

### Настройки уведомлений

```bash
# Просмотр текущих настроек
/group_settings

# Выключить уведомления
/group_settings mentions off

# Включить уведомления
/group_settings mentions on

# Изменить контекст (сколько сообщений до/после брать)
/group_settings context 10

# Изменить период дайджестов по умолчанию
/group_settings digest_hours 48
```

### Список групп

```bash
/my_groups
```

Показывает:
```
📊 Ваши группы (2/5):

1. 🟢 Моя группа
   🔔 Упоминания | ID: -1001234567890
   
2. 🟢 Рабочий чат
   🔔 Упоминания | ID: -1009876543210

💡 Используйте /group_settings для настройки
```

---

## 🏗️ Архитектура

### Multi-Agent система (n8n Workflow)

```
📥 Input: Сообщения из группы
     ↓
  Webhook
     ↓
  Prepare Prompts
     ↓
  ┌──┴──┬──────┐  (Параллельно ~5-8 сек)
  ↓     ↓      ↓
Agent1 Agent2 Agent3
Topics Speakers Summary
  ↓     ↓      ↓
  └──┬──┴──────┘
     ↓
  Merge Results
     ↓
  Agent4: Aggregator (~10-15 сек)
  (GigaChat-Max)
     ↓
📤 Output: Структурированный дайджест
```

**Используемые модели:**
- **Agent 1-3**: `GigaChat` (быстрая модель)
- **Agent 4**: `GigaChat-Max` (для сложной задачи агрегации)

**Timing:**
- Agent 1-3: 5-8 сек каждый (параллельно)
- Agent 4: 10-15 сек
- **Total: 15-25 секунд**

### Real-Time мониторинг

```
Telethon Event Handler
     ↓
NewMessage событие
     ↓
Проверка упоминания
(@username или mention entity)
     ↓
Получение контекста
(5 сообщений до/после)
     ↓
n8n Workflow
Analyze Mention
     ↓
Сохранение в БД
(group_mentions)
     ↓
Уведомление пользователю
```

---

## 📊 Лимиты по подпискам

| Подписка | Групп | Упоминания |
|----------|-------|------------|
| **Free** | 2 | ✅ |
| **Trial** | 5 | ✅ |
| **Basic** | 5 | ✅ |
| **Premium** | 20 | ✅ |
| **Enterprise** | 100 | ✅ |

Проверить подписку: `/subscription`

---

## 🔧 Переменные окружения

Добавьте в `telethon/.env`:

```bash
# n8n Webhooks для групп
N8N_GROUP_DIGEST_WEBHOOK=http://n8n:5678/webhook/group-digest
N8N_MENTION_ANALYZER_WEBHOOK=http://n8n:5678/webhook/mention-analyzer

# Timeouts (секунды)
N8N_DIGEST_TIMEOUT=120    # 2 минуты для дайджеста
N8N_MENTION_TIMEOUT=60    # 1 минута для анализа упоминания

# Лимиты
DIGEST_MAX_MESSAGES=200   # Максимум сообщений для анализа
```

---

## 🐛 Troubleshooting

### Ошибка: "n8n workflow not found"

**Причина:** Workflow не активирован в n8n

**Решение:**
1. Откройте n8n UI
2. Найдите workflow "Group Dialogue Multi-Agent"
3. Включите переключатель (должен стать зеленым)
4. Повторите для "Group Mention Analyzer"

### Ошибка: "gpt2giga-proxy unavailable"

**Причина:** GigaChat proxy не доступен

**Решение:**
```bash
# Проверьте статус
docker ps | grep gpt2giga

# Проверьте логи
docker logs gpt2giga-proxy

# Перезапустите
docker restart gpt2giga-proxy
```

### Не приходят уведомления об упоминаниях

**Проверка:**

1. **Мониторинг запущен?**
   ```bash
   docker logs telethon | grep "Мониторинг запущен"
   ```

2. **Группа добавлена?**
   ```
   /my_groups
   ```

3. **Уведомления включены?**
   ```
   /group_settings
   # Должно быть: ✅ Включены
   ```

4. **Вы упомянуты правильно?**
   - Используйте @username (не @first_name!)
   - Проверьте username: /auth_status

### Дайджест генерируется долго (>60 сек)

**Причины:**
- Слишком много сообщений (>200)
- GigaChat API перегружен

**Решение:**
1. Уменьшите период: `/group_digest 12` (вместо 24)
2. Уменьшите DIGEST_MAX_MESSAGES в .env
3. Проверьте статус GigaChat proxy

---

## 📊 Мониторинг

### Логи мониторинга групп

```bash
# Общие логи
docker logs telethon -f | grep -E "(GroupMonitor|группа|упоминание)"

# Только упоминания
docker logs telethon | grep "🔔 Упоминание"

# Ошибки
docker logs telethon 2>&1 | grep -E "(ERROR|❌)" | grep -i group
```

### Статус мониторинга (Admin API)

```bash
curl "http://localhost:8010/api/admin/stats/groups?admin_id=123&token=xxx"

# Ответ:
{
  "total_groups": 15,
  "mentions_today": 42,
  "mentions_week": 187,
  "active_monitors": 8,
  "monitored_groups_total": 15
}
```

### n8n Executions

1. Откройте n8n UI: `https://n8n.produman.studio`
2. Перейдите в **Executions**
3. Фильтр: "Group Dialogue Multi-Agent"
4. Смотрите статусы и время выполнения

---

## 🎯 Примеры использования

### Кейс 1: Мониторинг рабочего чата

```bash
# 1. Добавить рабочий чат
/add_group https://t.me/work_chat

# 2. Настроить уведомления
/group_settings context 3  # Меньше контекста для рабочих вопросов

# 3. Ежедневный дайджест
/group_digest 24
```

**Результат:**
- Получаете уведомления когда вас упоминают
- Видите резюме обсуждений за день
- Не пропускаете важные моменты

### Кейс 2: Анализ активности сообщества

```bash
# 1. Добавить группу сообщества
/add_group https://t.me/community_group

# 2. Генерировать дайджесты за неделю
/group_digest 168  # 7 дней

# 3. Анализ активных участников
```

**Результат:**
- Видите основные темы обсуждений
- Понимаете кто наиболее активен
- Выявляете тренды и интересы

### Кейс 3: Управление несколькими группами

```bash
# 1. Посмотреть все группы
/my_groups

# 2. Настроить разные параметры для каждой
/group_settings mentions on    # Глобально
# Или per-group через админ панель

# 3. Генерировать дайджесты по требованию
/group_digest 24
```

---

## 🔐 Безопасность

### Принципы

1. **User Isolation** - каждый пользователь видит только свои группы
2. **QR Authorization** - используется существующая userbot авторизация
3. **No Message Storage** - сообщения НЕ сохраняются постоянно (только анализ)
4. **Redis Sessions** - secure admin sessions с TTL
5. **Per-Group Settings** - индивидуальные настройки для каждой группы

### Права доступа

**Что видит пользователь:**
- ✅ Только группы, которые он добавил
- ✅ Только свои упоминания
- ✅ Только свои настройки

**Что видит админ:**
- ✅ Все группы в системе
- ✅ Статистику упоминаний
- ✅ Управление настройками пользователей

---

## 🤖 AI Multi-Agent Архитектура

### Agent 1: Topic Extractor

**Задача:** Извлечь 3-5 основных тем обсуждения

**Промпт:**
```
Проанализируй диалог в Telegram группе.
Извлеки 3-5 основных тем обсуждения.
Верни JSON: {"topics": ["тема1", "тема2"]}
```

**Модель:** GigaChat  
**Timeout:** 60 сек

### Agent 2: Speaker Analyzer

**Задача:** Проанализировать кто о чем говорил

**Промпт:**
```
Проанализируй кто о чем говорил в диалоге.
Создай резюме по каждому активному участнику (топ-5).
Верни JSON: {"speakers": {"username": "резюме"}}
```

**Модель:** GigaChat  
**Timeout:** 60 сек

### Agent 3: Context Summarizer

**Задача:** Создать краткое резюме разговора

**Промпт:**
```
Создай краткое резюме разговора в группе (2-3 предложения).
Верни JSON: {"summary": "текст"}
```

**Модель:** GigaChat  
**Timeout:** 60 сек

### Agent 4: Aggregator

**Задача:** Объединить результаты всех агентов

**Промпт:**
```
На основе анализа создай финальный дайджест:
- Темы: [...]
- Спикеры: {...}
- Резюме: "..."

Верни структурированный JSON
```

**Модель:** GigaChat-Max  
**Timeout:** 90 сек

---

## 📈 Performance

### Ожидаемое время

| Операция | Время | Модель |
|----------|-------|--------|
| Добавление группы | 2-5 сек | - |
| Анализ упоминания | 5-10 сек | GigaChat |
| Дайджест (50 сообщений) | 15-20 сек | 4x GigaChat |
| Дайджест (200 сообщений) | 20-30 сек | 4x GigaChat |

### Оптимизация

**Для ускорения дайджеста:**
1. Уменьшите период: `/group_digest 12` вместо 24
2. Используйте `GigaChat` вместо `GigaChat-Max` для Agent 4
3. Уменьшите DIGEST_MAX_MESSAGES до 100

**Для уменьшения нагрузки:**
1. Лимитируйте количество групп по подпискам
2. Используйте rate limiting через Redis
3. Настройте автоочистку старых упоминаний (retention)

---

## 🔌 Интеграция с другими сервисами

### Open WebUI

n8n workflows доступны из Open WebUI через `n8n_pipe.py`:

```python
# В Open WebUI Functions
# Загрузите n8n_pipe.py с настройкой:
n8n_url = "https://n8n.produman.studio/webhook/group-digest"
```

### Flowise

Можно создать Chatflow в Flowise с вызовом n8n webhook:

```
HTTP Request Node → n8n Workflow → Return Result
```

### API напрямую

```bash
# Прямой вызов n8n workflow
curl -X POST http://n8n:5678/webhook/group-digest \
  -H "Content-Type: application/json" \
  -d @group_messages.json
```

---

## 📚 API Endpoints

### User API

```bash
# Текущих endpoints для пользователей нет
# Используйте Telegram Bot команды
```

### Admin API

```bash
# Все группы
GET /api/admin/groups?admin_id=123&token=xxx

# Группы пользователя
GET /api/admin/user/456/groups?admin_id=123&token=xxx

# Toggle уведомлений
POST /api/admin/user/456/group/789/mentions?admin_id=123&token=xxx&enabled=true

# Статистика групп
GET /api/admin/stats/groups?admin_id=123&token=xxx
```

**Пример ответа:**
```json
{
  "total_groups": 15,
  "mentions_today": 42,
  "mentions_week": 187,
  "active_monitors": 8,
  "monitored_groups_total": 15
}
```

---

## 🗄️ Database Schema

### Таблицы

**groups** - Telegram группы
```sql
CREATE TABLE groups (
    id SERIAL PRIMARY KEY,
    group_id BIGINT UNIQUE NOT NULL,
    group_title VARCHAR,
    group_username VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE
);
```

**user_group** - Many-to-many связь
```sql
CREATE TABLE user_group (
    user_id INTEGER REFERENCES users(id),
    group_id INTEGER REFERENCES groups(id),
    is_active BOOLEAN DEFAULT TRUE,
    mentions_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (user_id, group_id)
);
```

**group_mentions** - История упоминаний
```sql
CREATE TABLE group_mentions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    group_id INTEGER REFERENCES groups(id),
    message_id BIGINT NOT NULL,
    mentioned_at TIMESTAMP WITH TIME ZONE,
    context TEXT,
    reason TEXT,
    urgency VARCHAR,
    notified BOOLEAN DEFAULT FALSE,
    notified_at TIMESTAMP WITH TIME ZONE,
    UNIQUE (user_id, group_id, message_id)
);
```

**group_settings** - Настройки пользователя
```sql
CREATE TABLE group_settings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE REFERENCES users(id),
    mentions_enabled BOOLEAN DEFAULT TRUE,
    mention_context_messages INTEGER DEFAULT 5,
    digest_default_hours INTEGER DEFAULT 24,
    digest_max_messages INTEGER DEFAULT 200
);
```

---

## ✅ Checklist развертывания

- [ ] n8n workflows импортированы и активированы
- [ ] Миграция БД выполнена успешно
- [ ] Контейнеры telethon/telethon-bot перезапущены
- [ ] gpt2giga-proxy доступен и работает
- [ ] Переменные окружения добавлены в .env
- [ ] Команды /add_group, /my_groups работают
- [ ] Тестовое упоминание получено успешно
- [ ] Тестовый дайджест сгенерирован

---

## 🎓 Best Practices

### 1. Лимиты сообщений

Не анализируйте слишком много сообщений за раз:
- ✅ Оптимально: 50-100 сообщений (быстро, точно)
- ⚠️ Приемлемо: 100-200 сообщений (медленнее)
- ❌ Избегайте: >200 сообщений (очень медленно, неточно)

### 2. Период дайджестов

Выбирайте разумные периоды:
- ✅ Активная группа: 12-24 часа
- ✅ Средняя активность: 24-48 часов
- ⚠️ Низкая активность: 48-168 часов (неделя)

### 3. Настройка уведомлений

Для высокоактивных групп:
- `/group_settings context 3` - меньше контекста
- Отключите неважные группы

Для важных групп:
- `/group_settings context 10` - больше контекста
- Включите уведомления

### 4. Мониторинг производительности

Проверяйте логи регулярно:
```bash
# Ошибки мониторинга
docker logs telethon | grep "GroupMonitor.*ERROR"

# Производительность n8n workflows
# n8n UI → Executions → смотрите время выполнения
```

---

## 🔄 Обновления и миграции

### Откат миграции

Если нужно откатить изменения:

```bash
cd /home/ilyasni/n8n-server/n8n-installer/telethon
python scripts/migrations/add_groups_support.py rollback

# ВНИМАНИЕ: Удалит все данные групп!
```

### Обновление n8n Workflows

1. Измените JSON файлы в `n8n/workflows/`
2. Удалите старые workflows в n8n UI
3. Импортируйте обновленные
4. Активируйте

---

## 📞 Support

**Вопросы и баги:**
- GitHub Issues: создайте issue с тегом `groups`
- Logs: прикрепите вывод `docker logs telethon`

**Документация:**
- n8n Workflows: `n8n/workflows/README_GROUP_WORKFLOWS.md`
- Database: `.cursor/rules/telegram-bot/03-database.mdc`
- Architecture: `.cursor/rules/telegram-bot/02-architecture.mdc`

---

**Готово!** Теперь ваш бот может анализировать диалоги в группах и уведомлять об упоминаниях с AI-контекстом 🚀

