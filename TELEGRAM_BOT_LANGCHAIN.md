# Telegram Bot с LangChain Direct Integration

## 🚀 Быстрый Запуск

### 1. Подготовка Environment

```bash
# Скопировать .env.example в .env
cp .env.example .env

# Настроить обязательные переменные в .env
nano .env
```

**Обязательные переменные:**
```bash
# Telegram Bot
BOT_TOKEN=your_bot_token_from_botfather
MASTER_API_ID=your_api_id_from_my_telegram
MASTER_API_HASH=your_api_hash_from_my_telegram
ENCRYPTION_KEY=your_encryption_key

# LangChain Direct Integration
USE_LANGCHAIN_DIRECT=true

# Langfuse (опционально)
LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
LANGFUSE_SECRET_KEY=your_langfuse_secret_key
```

### 2. Запуск с LangChain Direct Integration

```bash
# Автоматический запуск с проверками
./start_telethon_langchain.sh
```

### 3. Переключение на n8n (fallback)

```bash
# Переключение на n8n
./start_telethon_n8n.sh
```

## 🔧 Ручной Запуск

### Запуск с LangChain

```bash
# Установить переменную
export USE_LANGCHAIN_DIRECT=true

# Запустить все сервисы
docker-compose up -d postgres redis gpt2giga-proxy n8n

# Собрать и запустить telethon
docker-compose up -d --build telethon
```

### Запуск с n8n

```bash
# Установить переменную
export USE_LANGCHAIN_DIRECT=false

# Запустить n8n
docker-compose up -d n8n

# Перезапустить telethon
docker-compose restart telethon
```

## 📊 Мониторинг

### Логи

```bash
# Логи telethon
docker-compose logs -f telethon

# Логи всех сервисов
docker-compose logs -f
```

### Статус Сервисов

```bash
# Статус всех контейнеров
docker-compose ps

# Статус telethon
docker-compose ps telethon
```

### Observability

- **Langfuse**: https://langfuse.produman.studio (трейсинг LLM)
- **Prometheus**: http://localhost:9090 (метрики)
- **Grafana**: http://localhost:3000 (дашборды)

## 🏗️ Архитектура

### LangChain Direct Integration

```
Telegram Bot → LangChain Agents → GigaChat → HTML Digest
                    ↓
                Langfuse (трейсинг)
```

**9-Агентная Pipeline:**
1. Dialogue Assessor (эвристики)
2. Topic Extractor (GigaChat)
3. Emotion Analyzer (GigaChat-Pro)
4. Speaker Analyzer (GigaChat-Pro)
5. Context Summarizer (GigaChat-Pro)
6. Key Moments (GigaChat-Pro, conditional)
7. Timeline Builder (GigaChat-Pro, conditional)
8. Context Links (GigaChat, conditional)
9. Supervisor Synthesizer (GigaChat-Pro)

### n8n Fallback

```
Telegram Bot → n8n Workflows → GigaChat → HTML Digest
```

## 🔄 Переключение между LangChain и n8n

### Через Feature Flag

```bash
# Включить LangChain
sed -i 's/USE_LANGCHAIN_DIRECT=false/USE_LANGCHAIN_DIRECT=true/' .env
docker-compose restart telethon

# Включить n8n
sed -i 's/USE_LANGCHAIN_DIRECT=true/USE_LANGCHAIN_DIRECT=false/' .env
docker-compose restart telethon
```

### Через Environment Variables

```bash
# LangChain
USE_LANGCHAIN_DIRECT=true docker-compose restart telethon

# n8n
USE_LANGCHAIN_DIRECT=false docker-compose restart telethon
```

## 🧪 Тестирование

### Unit Tests

```bash
# Запуск тестов в контейнере
docker-compose -f telethon/docker-compose.test.yml up telethon-test-unit

# Локальные тесты (если Python установлен)
cd telethon
pytest tests/test_langchain_agents/ -v
```

### Integration Tests

```bash
# Полные тесты
docker-compose -f telethon/docker-compose.test.yml up telethon-test-all
```

## 🐛 Troubleshooting

### Частые Проблемы

#### 1. Ошибка импорта LangChain

```
❌ Ошибка импорта LangChain: No module named 'langchain'
```

**Решение:** Пересобрать контейнер
```bash
docker-compose build telethon
docker-compose up -d telethon
```

#### 2. GigaChat недоступен

```
❌ Ошибка GigaChat: Connection refused
```

**Решение:** Проверить gpt2giga-proxy
```bash
docker-compose ps gpt2giga-proxy
docker-compose logs gpt2giga-proxy
docker-compose restart gpt2giga-proxy
```

#### 3. PostgreSQL недоступен

```
❌ Ошибка подключения к PostgreSQL
```

**Решение:** Запустить PostgreSQL
```bash
docker-compose up -d postgres
sleep 10
docker-compose restart telethon
```

#### 4. Redis недоступен

```
❌ Ошибка подключения к Redis
```

**Решение:** Запустить Redis
```bash
docker-compose up -d redis
docker-compose restart telethon
```

### Логи для Отладки

```bash
# Детальные логи
docker-compose logs telethon | grep -E "(LangChain|n8n|ERROR|✅|❌)"

# Логи последних 100 строк
docker-compose logs --tail 100 telethon

# Логи в реальном времени
docker-compose logs -f telethon
```

## 📈 Производительность

### Ожидаемые Времена

| Уровень | LangChain | n8n |
|---------|-----------|-----|
| Micro | ~5-10s | ~15-20s |
| Brief | ~10-15s | ~20-25s |
| Standard | ~15-25s | ~30-40s |
| Detailed | ~20-30s | ~40-50s |
| Comprehensive | ~25-40s | ~50-60s |

### Оптимизации

- **Параллельное выполнение**: Topics + Emotions
- **Conditional execution**: Агенты 6-8 по необходимости
- **Timeout protection**: Защита от зависания
- **Fallback strategy**: Автоматический переход на n8n

## 🔒 Безопасность

### HTML Sanitization

- Только разрешенные теги: `<b>`, `<i>`, `<code>`, `<a>`
- Защита от XSS атак
- Валидация пользовательских данных

### User Isolation

- Все запросы изолированы по user_id
- Нет утечки данных между пользователями
- Безопасная обработка usernames

## 📚 Документация

- **Архитектура**: `telethon/docs/features/groups/LANGCHAIN_ARCHITECTURE.md`
- **Migration Guide**: `telethon/docs/features/groups/LANGCHAIN_MIGRATION.md`
- **Implementation Summary**: `telethon/docs/features/groups/LANGCHAIN_IMPLEMENTATION_SUMMARY.md`
- **LangChain Agents**: `telethon/langchain_agents/README.md`

## 🆘 Поддержка

### Контакты

- **Техническая поддержка**: [ссылка на тикет-систему]
- **Документация**: [ссылка на wiki]

### Ресурсы

- **LangChain Documentation**: https://python.langchain.com/
- **Langfuse Documentation**: https://langfuse.com/docs
- **GigaChat API**: https://developers.sber.ru/portal/products/gigachat
