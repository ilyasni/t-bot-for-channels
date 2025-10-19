# LangChain Migration Guide

## Обзор

Руководство по миграции с n8n workflows на прямую интеграцию LangChain для генерации дайджестов Telegram групп.

## Подготовка к Миграции

### 1. Установка Зависимостей

```bash
# В директории telethon/
pip install langchain>=0.1.0
pip install langchain-core>=0.1.0
pip install langchain-community>=0.0.38
```

### 2. Environment Variables

Добавить в `.env`:

```bash
# LangChain Direct Integration
USE_LANGCHAIN_DIRECT=true

# Langfuse для observability (опционально)
LANGFUSE_PUBLIC_KEY=your_public_key
LANGFUSE_SECRET_KEY=your_secret_key
LANGFUSE_HOST=https://langfuse.produman.studio

# GigaChat настройки (если отличаются от дефолтных)
GIGACHAT_BASE_URL=http://gpt2giga-proxy:8000/v1
GIGACHAT_TIMEOUT=60.0
```

### 3. Проверка Конфигурации

```bash
# Проверить доступность gpt2giga-proxy
curl http://gpt2giga-proxy:8000/v1/models

# Проверить Langfuse (если настроен)
curl -H "Authorization: Bearer $LANGFUSE_PUBLIC_KEY" $LANGFUSE_HOST/api/public/health
```

## Пошаговая Миграция

### Этап 1: Подготовка (5 минут)

1. **Создать backup n8n workflows**:
   ```bash
   # Экспорт текущих workflows
   docker exec n8n n8n export:workflow --all --output=/tmp/n8n-backup.json
   ```

2. **Проверить структуру файлов**:
   ```bash
   ls -la telethon/langchain_agents/
   # Должны быть все файлы агентов
   ```

### Этап 2: Тестовый Запуск (10 минут)

1. **Включить LangChain для тестирования**:
   ```bash
   export USE_LANGCHAIN_DIRECT=true
   ```

2. **Запустить бот в debug режиме**:
   ```bash
   cd telethon/
   python bot.py
   ```

3. **Проверить логи инициализации**:
   ```
   🚀 Инициализация LangChain Direct Integration
   ✅ LangChain Orchestrator инициализирован
   ✅ Все агенты инициализированы
   ```

### Этап 3: Тестирование Функциональности (15 минут)

1. **Создать тестовую группу** с небольшим количеством сообщений (5-10)

2. **Запустить генерацию дайджеста** и проверить:
   - Успешное выполнение всех агентов
   - Корректность HTML форматирования
   - Сохранение реальных usernames
   - Адаптивность под уровень детализации

3. **Проверить Langfuse** (если настроен):
   - Трейсы всех агентов
   - Метрики производительности
   - Отсутствие ошибок

### Этап 4: Постепенное Внедрение (30 минут)

1. **A/B тестирование**:
   ```bash
   # Для тестовых пользователей
   export USE_LANGCHAIN_DIRECT=true
   
   # Для остальных пользователей
   export USE_LANGCHAIN_DIRECT=false
   ```

2. **Мониторинг метрик**:
   - Время генерации дайджестов
   - Количество ошибок
   - Качество результатов

3. **Постепенное увеличение нагрузки**:
   - Начать с 10% пользователей
   - Увеличивать до 50%, затем 100%

## Мониторинг и Валидация

### Ключевые Метрики

1. **Производительность**:
   ```bash
   # Среднее время генерации
   grep "Дайджест сгенерирован за" logs/telethon.log | \
   awk '{print $NF}' | sed 's/s//' | awk '{sum+=$1; count++} END {print sum/count "s"}'
   ```

2. **Успешность**:
   ```bash
   # Процент успешных генераций
   grep -c "✅.*сгенерирован" logs/telethon.log
   grep -c "❌.*Ошибка" logs/telethon.log
   ```

3. **Качество**:
   - Проверка HTML валидности
   - Сохранение usernames
   - Адаптивность детализации

### Langfuse Dashboard

1. **Открыть Langfuse**: `https://langfuse.produman.studio`

2. **Проверить трейсы**:
   - Sessions с тегом `telegram_bot`
   - Выполнение всех 9 агентов
   - Времена выполнения

3. **Анализ ошибок**:
   - Failed traces
   - Timeout issues
   - LLM errors

## Troubleshooting

### Частые Проблемы

#### 1. Import Error: No module named 'langchain'

**Симптомы**:
```
❌ Ошибка импорта LangChain: No module named 'langchain'
🔄 Переключение на n8n fallback
```

**Решение**:
```bash
pip install langchain langchain-core langchain-community
```

#### 2. GigaChat Connection Error

**Симптомы**:
```
❌ Ошибка GigaChat: Connection refused
```

**Решение**:
```bash
# Проверить доступность gpt2giga-proxy
docker ps | grep gpt2giga-proxy

# Перезапустить если нужно
docker-compose restart gpt2giga-proxy
```

#### 3. Timeout Issues

**Симптомы**:
```
⏰ Timeout агента TopicExtractor (25.0s)
```

**Решение**:
```bash
# Увеличить timeout в .env
GIGACHAT_TIMEOUT=90.0
AGENT_TIMEOUT=45.0
```

#### 4. Memory Issues

**Симптомы**:
```
❌ Ошибка: Out of memory
```

**Решение**:
```bash
# Уменьшить количество сообщений
export DIGEST_MAX_MESSAGES=100
```

#### 5. HTML Validation Errors

**Симптомы**:
```
❌ Invalid HTML: <div> not allowed
```

**Решение**:
- Проверить `supervisor.py` - только `<b>`, `<i>`, `<code>`, `<a>` теги
- Использовать `_sanitize_html()` метод

### Логи для Отладки

#### Включить Debug Логирование

```bash
export LOG_LEVEL=DEBUG
```

#### Ключевые Логи

```bash
# Успешная инициализация
grep "LangChain Orchestrator инициализирован" logs/telethon.log

# Выполнение агентов
grep "Phase.*:" logs/telethon.log

# Производительность
grep "завершен за" logs/telethon.log

# Ошибки
grep "❌" logs/telethon.log
```

## Rollback Plan

### Быстрый Rollback (1 минута)

```bash
# Отключить LangChain
export USE_LANGCHAIN_DIRECT=false

# Перезапустить бот
docker-compose restart telethon
```

### Полный Rollback (5 минут)

1. **Отключить LangChain**:
   ```bash
   export USE_LANGCHAIN_DIRECT=false
   ```

2. **Восстановить n8n workflows**:
   ```bash
   docker exec n8n n8n import:workflow --input=/tmp/n8n-backup.json
   ```

3. **Проверить работу n8n**:
   ```bash
   curl http://n8n:5678/health
   ```

### Восстановление Данных

1. **Проверить базу данных**:
   ```bash
   # Нет изменений в схеме БД
   # Все данные сохранены
   ```

2. **Проверить Redis**:
   ```bash
   # Кэш остается валидным
   # Сессии пользователей сохранены
   ```

## Post-Migration

### Оптимизация

1. **Настройка Langfuse**:
   - Настройка алертов на ошибки
   - Анализ производительности
   - Оптимизация промптов

2. **Мониторинг ресурсов**:
   - CPU usage агентов
   - Memory consumption
   - LLM API costs

3. **A/B тестирование промптов**:
   - Сравнение качества результатов
   - Оптимизация temperature settings
   - Улучшение промптов на основе Langfuse данных

### Документация

1. **Обновить README**:
   - Добавить информацию о LangChain
   - Обновить архитектурные диаграммы

2. **Создать runbooks**:
   - Troubleshooting guide
   - Performance tuning
   - Monitoring procedures

3. **Обучение команды**:
   - LangChain best practices
   - Debugging techniques
   - Performance optimization

## Поддержка

### Контакты

- **Техническая поддержка**: [ссылка на тикет-систему]
- **Документация**: [ссылка на wiki]
- **Мониторинг**: [ссылка на dashboard]

### Ресурсы

- **LangChain Documentation**: https://python.langchain.com/
- **Langfuse Documentation**: https://langfuse.com/docs
- **GigaChat API**: https://developers.sber.ru/portal/products/gigachat

### Мониторинг

- **Логи**: `logs/telethon.log`
- **Langfuse**: https://langfuse.produman.studio
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000
