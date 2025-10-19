# LangChain Agents для Telegram Bot

Прямая интеграция LangChain в Telegram Bot для генерации дайджестов групп, заменяющая n8n workflows на более гибкую и отлаживаемую Python-основу.

## Архитектура

### 9-Агентная Sequential Pipeline

```
1. Dialogue Assessor (эвристики) → detail_level, dialogue_type
2. Topic Extractor (GigaChat) → topics с приоритетами
3. Emotion Analyzer (GigaChat-Pro) → overall_tone, atmosphere
4. Speaker Analyzer (GigaChat-Pro) → роли участников
5. Context Summarizer (GigaChat-Pro) → адаптивное резюме
6. Key Moments (GigaChat-Pro, conditional) → решения, вопросы
7. Timeline Builder (GigaChat-Pro, conditional) → хронология
8. Context Links (GigaChat, conditional) → анализ ссылок
9. Supervisor Synthesizer (GigaChat-Pro) → финальный HTML дайджест
```

## Структура Файлов

```
langchain_agents/
├── __init__.py              # Основные экспорты
├── base.py                  # Базовые классы для агентов
├── config.py                # Конфигурация LLM и настроек
├── orchestrator.py          # Центральный оркестратор
├── observability.py         # Langfuse интеграция
├── README.md               # Эта документация
│
├── assessor.py             # Dialogue Assessor (эвристики)
├── topic_extractor.py      # Topic Extractor Agent
├── emotion_analyzer.py     # Emotion Analyzer Agent
├── speaker_analyzer.py     # Speaker Analyzer Agent
├── summarizer.py           # Context Summarizer Agent
│
├── key_moments.py          # Key Moments Agent (conditional)
├── timeline.py             # Timeline Builder Agent (conditional)
├── context_links.py        # Context Links Agent (conditional)
│
└── supervisor.py           # Supervisor Synthesizer Agent
```

## Быстрый Старт

### 1. Установка Зависимостей

```bash
pip install langchain>=0.1.0
pip install langchain-core>=0.1.0
pip install langchain-community>=0.0.38
```

### 2. Настройка Environment Variables

```bash
# Включить LangChain Direct Integration
export USE_LANGCHAIN_DIRECT=true

# Langfuse для observability (опционально)
export LANGFUSE_PUBLIC_KEY=your_public_key
export LANGFUSE_SECRET_KEY=your_secret_key
export LANGFUSE_HOST=https://langfuse.produman.studio

# GigaChat настройки
export GIGACHAT_BASE_URL=http://gpt2giga-proxy:8000/v1
export GIGACHAT_TIMEOUT=60.0
```

### 3. Использование

```python
from langchain_agents import DigestOrchestrator

# Создание оркестратора
orchestrator = DigestOrchestrator()

# Генерация дайджеста
result = await orchestrator.generate_digest(
    messages=messages,
    hours=24,
    user_id=user_id,
    group_id=group_id
)

# Результат содержит HTML дайджест и метаданные
html_digest = result["html_digest"]
metadata = result["metadata"]
```

## Компоненты

### Базовые Классы

#### `BaseAgent`
Абстрактный базовый класс для всех агентов с поддержкой:
- LCEL chain composition
- Async execution с timeout
- Structured logging
- Error handling с fallback
- Langfuse integration

#### `HeuristicAgent`
Для эвристических вычислений без LLM (Dialogue Assessor).

### Конфигурация

#### `LangChainConfig`
Централизованная конфигурация:
- GigaChat proxy settings
- Temperature settings per agent type
- Timeouts и Langfuse settings

#### `get_gigachat_llm()`
Создание оптимизированных GigaChat LLM instances.

### Агенты

#### Dialogue Assessor Agent
- **Тип**: Эвристический (без LLM)
- **Функция**: Быстрый анализ диалогов
- **Выход**: `detail_level`, `dialogue_type`, `has_links`, `participants`

#### Topic Extractor Agent
- **LLM**: GigaChat (консервативная температура)
- **Функция**: Извлечение тем с приоритетами
- **Выход**: `topics` с `name` и `priority`

#### Emotion Analyzer Agent
- **LLM**: GigaChat-Pro (творческая температура)
- **Функция**: Анализ эмоциональной атмосферы
- **Выход**: `overall_tone`, `atmosphere`, `emotional_indicators`

#### Speaker Analyzer Agent
- **LLM**: GigaChat-Pro
- **Функция**: Анализ ролей участников
- **ВАЖНО**: Сохраняет реальные usernames
- **Выход**: `speakers` с ролями и активностью

#### Context Summarizer Agent
- **LLM**: GigaChat-Pro
- **Функция**: Адаптивное резюмирование
- **Выход**: `main_points`, `key_decisions`, `summary_text`

#### Key Moments Agent (Conditional)
- **LLM**: GigaChat-Pro
- **Условие**: `detail_level >= standard`
- **Функция**: Извлечение ключевых моментов
- **Выход**: `key_decisions`, `critical_questions`, `action_items`

#### Timeline Builder Agent (Conditional)
- **LLM**: GigaChat-Pro
- **Условие**: `detail_level >= detailed`
- **Функция**: Построение хронологии
- **Выход**: `timeline_events`, `discussion_phases`, `topic_evolution`

#### Context Links Agent (Conditional)
- **LLM**: GigaChat
- **Условие**: `detail_level == comprehensive OR has_links`
- **Функция**: Анализ ссылок и ресурсов
- **Выход**: `external_links`, `telegram_links`, `mentions`

#### Supervisor Synthesizer Agent
- **LLM**: GigaChat-Pro
- **Функция**: Финальный синтез HTML дайджеста
- **КРИТИЧНО**: Только HTML теги `<b>`, `<i>`, `<code>`, `<a>`
- **Выход**: `html_digest`, `metadata`, `sections`

### Оркестратор

#### `DigestOrchestrator`
Центральный компонент для управления:
- Sequential + Parallel execution
- Conditional agent activation
- Error handling и fallback
- Performance monitoring

### Observability

#### `LangfuseObserver`
Интеграция с Langfuse для:
- Трейсинг всех LLM вызовов
- Мониторинг производительности
- Логирование ошибок
- Анализ качества результатов

## Условная Активация

Агенты 6-8 выполняются только при определенных условиях:

- **Key Moments**: `detail_level >= standard`
- **Timeline Builder**: `detail_level >= detailed`
- **Context Links**: `detail_level == comprehensive OR has_links == true`

## Параллельное Выполнение

- **Topics + Emotions**: Выполняются параллельно после Dialogue Assessor
- **Остальные агенты**: Sequential execution с зависимостями

## Преимущества vs n8n

| Аспект | n8n | LangChain Direct |
|--------|-----|------------------|
| Отладка | ❌ Сложно (UI only) | ✅ Python debugger, logs |
| Промпты | ❌ В JSON, неудобно | ✅ Python код, version control |
| Тесты | ❌ Невозможны | ✅ pytest, coverage |
| Observability | ❌ n8n executions | ✅ Langfuse, custom metrics |
| Гибкость | ❌ Ограничены nodes | ✅ Полный Python |
| Performance | 🟡 ~30-50s | 🟢 ~20-30s (параллелизм) |

## Производительность

### Ожидаемые Времена
- **Micro**: ~5-10 секунд
- **Brief**: ~10-15 секунд
- **Standard**: ~15-25 секунд
- **Detailed**: ~20-30 секунд
- **Comprehensive**: ~25-40 секунд

### Оптимизации
- Параллельное выполнение Topics + Emotions
- Conditional execution агентов 6-8
- Timeout protection для всех агентов
- Эффективная обработка больших диалогов

## Мониторинг

### Логирование
- Структурированные логи каждого агента
- Performance метрики
- Error tracking с context

### Langfuse Integration
- Трейсинг всех LLM вызовов
- Анализ качества результатов
- Мониторинг пользователей

### Fallback Strategy
- Graceful degradation при ошибках
- Fallback на n8n при проблемах с LangChain
- Сохранение функциональности

## Безопасность

### HTML Sanitization
- Только разрешенные HTML теги: `<b>`, `<i>`, `<code>`, `<a>`
- Защита от XSS атак
- Валидация всех пользовательских данных

### User Isolation
- Все запросы изолированы по user_id
- Нет утечки данных между пользователями
- Безопасная обработка usernames

## Расширяемость

### Добавление Новых Агентов
1. Наследование от `BaseAgent`
2. Реализация `_process_input` и `_process_output`
3. Добавление в `DigestOrchestrator`
4. Обновление документации

### Кастомизация Промптов
- Прямое редактирование в Python коде
- Version control через Git
- A/B тестирование промптов

### Интеграция с Другими LLM
- Поддержка различных провайдеров
- Легкое переключение моделей
- Конфигурируемые настройки

## Troubleshooting

### Частые Проблемы

1. **Import Error**: LangChain не установлен
   ```bash
   pip install langchain langchain-core langchain-community
   ```

2. **GigaChat Timeout**: Медленный ответ от LLM
   ```bash
   export GIGACHAT_TIMEOUT=90.0
   ```

3. **Memory Issues**: Слишком много сообщений
   ```bash
   export DIGEST_MAX_MESSAGES=100
   ```

### Логи для Отладки
```bash
# Включить debug логи
export LOG_LEVEL=DEBUG

# Проверить Langfuse
export LANGFUSE_PUBLIC_KEY=your_key
export LANGFUSE_SECRET_KEY=your_secret
```

## Тестирование

### Unit Tests
```bash
# Запуск тестов
pytest telethon/tests/test_langchain_agents/ -v

# Покрытие кода
pytest --cov=langchain_agents telethon/tests/test_langchain_agents/
```

### Integration Tests
```bash
# Тестирование с реальными данными
python telethon/tests/test_integration_langchain.py
```

## Документация

- **Архитектура**: `docs/features/groups/LANGCHAIN_ARCHITECTURE.md`
- **Migration Guide**: `docs/features/groups/LANGCHAIN_MIGRATION.md`
- **API Reference**: [ссылка на документацию]

## Поддержка

### Контакты
- **Техническая поддержка**: [ссылка на тикет-систему]
- **Документация**: [ссылка на wiki]

### Ресурсы
- **LangChain Documentation**: https://python.langchain.com/
- **Langfuse Documentation**: https://langfuse.com/docs
- **GigaChat API**: https://developers.sber.ru/portal/products/gigachat
