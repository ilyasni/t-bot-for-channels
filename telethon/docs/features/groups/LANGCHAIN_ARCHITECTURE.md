# LangChain Direct Integration Architecture

## Обзор

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

### Условная Активация Агентов

- **Key Moments**: `detail_level >= standard`
- **Timeline Builder**: `detail_level >= detailed`
- **Context Links**: `detail_level == comprehensive OR has_links == true`

### Параллельное Выполнение

- **Topics + Emotions**: Выполняются параллельно после Dialogue Assessor
- **Остальные агенты**: Sequential execution с зависимостями

## Компоненты

### 1. Базовые Классы

#### `BaseAgent`
- Абстрактный базовый класс для всех агентов
- LCEL chain composition
- Async execution с timeout
- Structured logging
- Error handling с fallback
- Langfuse integration

#### `HeuristicAgent`
- Для эвристических вычислений без LLM
- Используется в Dialogue Assessor

### 2. Конфигурация

#### `LangChainConfig`
- Настройки GigaChat через gpt2giga-proxy
- Temperature settings per agent type
- Timeouts и Langfuse settings

#### `get_gigachat_llm()`
- Создание GigaChat LLM instances
- Оптимальные настройки для разных типов агентов

### 3. Агенты

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

### 4. Оркестратор

#### `DigestOrchestrator`
- Управление всей pipeline
- Sequential + Parallel execution
- Conditional agent activation
- Error handling и fallback
- Performance monitoring

### 5. Observability

#### `LangfuseObserver`
- Интеграция с Langfuse для трейсинга
- Мониторинг производительности агентов
- Логирование ошибок
- Анализ качества результатов

## Интеграция с Ботом

### Feature Flag
```bash
USE_LANGCHAIN_DIRECT=true  # Включить LangChain
USE_LANGCHAIN_DIRECT=false # Использовать n8n (fallback)
```

### Модификация `GroupDigestGenerator`
- Автоматическое переключение между LangChain и n8n
- Graceful fallback при ошибках импорта
- Совместимость с существующим API

## Преимущества vs n8n

| Аспект | n8n | LangChain Direct |
|--------|-----|------------------|
| Отладка | ❌ Сложно (UI only) | ✅ Python debugger, logs |
| Промпты | ❌ В JSON, неудобно | ✅ Python код, version control |
| Тесты | ❌ Невозможны | ✅ pytest, coverage |
| Observability | ❌ n8n executions | ✅ Langfuse, custom metrics |
| Гибкость | ❌ Ограничены nodes | ✅ Полный Python |
| Performance | 🟡 ~30-50s | 🟢 ~20-30s (параллелизм) |

## Мониторинг и Логирование

### Структурированное Логирование
- Детальные логи каждого агента
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

## Производительность

### Оптимизации
- Параллельное выполнение Topics + Emotions
- Conditional execution агентов 6-8
- Timeout protection для всех агентов
- Эффективная обработка больших диалогов

### Ожидаемые Времена
- **Micro**: ~5-10 секунд
- **Brief**: ~10-15 секунд
- **Standard**: ~15-25 секунд
- **Detailed**: ~20-30 секунд
- **Comprehensive**: ~25-40 секунд

## Безопасность

### HTML Sanitization
- Только разрешенные HTML теги
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
   - Решение: `pip install langchain langchain-core langchain-community`

2. **GigaChat Timeout**: Медленный ответ от LLM
   - Решение: Увеличить timeout в конфигурации

3. **Memory Issues**: Слишком много сообщений
   - Решение: Уменьшить `DIGEST_MAX_MESSAGES`

### Логи для Отладки
```bash
# Включить debug логи
export LOG_LEVEL=DEBUG

# Проверить Langfuse
export LANGFUSE_PUBLIC_KEY=your_key
export LANGFUSE_SECRET_KEY=your_secret
```

## Миграция с n8n

### Пошаговый План
1. Установить LangChain зависимости
2. Настроить environment variables
3. Включить feature flag `USE_LANGCHAIN_DIRECT=true`
4. Тестировать на небольшой группе пользователей
5. Мониторить производительность через Langfuse
6. Постепенно переводить всех пользователей

### Rollback Plan
1. `USE_LANGCHAIN_DIRECT=false` - мгновенный возврат на n8n
2. n8n workflows остаются активными как fallback
3. Мониторинг ошибок для быстрого реагирования
