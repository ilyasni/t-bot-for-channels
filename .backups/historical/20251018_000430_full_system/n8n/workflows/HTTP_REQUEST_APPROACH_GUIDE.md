# HTTP Request Approach Guide

## Обзор

Все агенты n8n workflows были переведены с использования `n8n-nodes-gigachat` на прямой HTTP Request к `gpt2giga-proxy`. Это решение обеспечивает:

- ✅ **Надежность**: Прямой контроль над запросами и ответами
- ✅ **Совместимость**: Работа с `gpt2giga-proxy` без проблем с форматом ответов
- ✅ **JSON Mode**: Поддержка `response_format: {"type": "json_object"}`
- ✅ **Валидация**: Интеграция с `Utility: JSON Guardrail`

## Архитектура

### Стандартная схема агента

```
Execute Workflow Trigger
    ↓
Prepare [Agent] Prompt (Code)
    ↓
GigaChat: [Agent] (HTTP Request)
    ↓
Parse Response (Code)
    ↓
Execute Guardrail
    ↓
[Output/Next Agent]
```

### Компоненты

#### 1. Prepare [Agent] Prompt (Code Node)
- **Назначение**: Формирует `system_message` и `user_message` для HTTP Request
- **Входные данные**: Результаты предыдущих агентов + исходные сообщения
- **Выходные данные**: `{system_message, user_message, max_tokens, ...}`

#### 2. GigaChat: [Agent] (HTTP Request Node)
- **URL**: `http://gpt2giga-proxy:8000/v1/chat/completions`
- **Method**: POST
- **Headers**: `Content-Type: application/json`
- **Body**: JSON с параметрами GigaChat API

#### 3. Parse Response (Code Node)
- **Назначение**: Извлекает `content` из `choices[0].message.content`
- **Выходные данные**: `{raw_content: "..."}`

#### 4. Execute Guardrail
- **Назначение**: Валидация и парсинг JSON ответа
- **Входные данные**: `raw_content` от Parse Response

## Конфигурация HTTP Request

### Базовые параметры

```json
{
  "url": "http://gpt2giga-proxy:8000/v1/chat/completions",
  "authentication": "none",
  "requestMethod": "POST",
  "sendHeaders": true,
  "headerParameters": {
    "parameters": [
      {
        "name": "Content-Type",
        "value": "application/json"
      }
    ]
  },
  "sendBody": true,
  "bodyContentType": "json",
  "jsonBody": "={{ {\"model\": \"GigaChat-Pro\", \"messages\": [{\"role\": \"system\", \"content\": $json.system_message}, {\"role\": \"user\", \"content\": $json.user_message}], \"temperature\": 0.1, \"max_tokens\": $json.max_tokens, \"response_format\": {\"type\": \"json_object\"}} }}",
  "options": {}
}
```

### Ключевые особенности

- **Model**: `GigaChat-Pro` (через gpt2giga-proxy)
- **Temperature**: `0.1` (низкая стохастичность)
- **Response Format**: `{"type": "json_object"}` (строгий JSON)
- **Max Tokens**: Динамически из `$json.max_tokens`

## Обновленные агенты

### ✅ Завершено

1. **Agent: Dialogue Assessor** → Code node с эвристиками
2. **Agent: Speaker Analyzer** → HTTP Request + Parse Response
3. **Agent: Supervisor Synthesizer** → HTTP Request + Parse Response  
4. **Agent: Topic Extractor** → HTTP Request + Parse Response
5. **Agent: Emotion Analyzer** → HTTP Request + Parse Response
6. **Agent: Key Moments** → HTTP Request + Parse Response
7. **Agent: Timeline** → HTTP Request + Parse Response
8. **Agent: Summarizer** → HTTP Request + Parse Response
9. **Agent: Context Links** → HTTP Request + Parse Response

### 🔧 Utility: JSON Guardrail

Обновлен для работы с `gpt2giga-proxy`:
- Убрана обработка экранированных кавычек
- Ожидается чистый JSON от прокси
- Улучшено логирование

## Преимущества нового подхода

### 1. Надежность
- Прямой контроль над HTTP запросами
- Нет проблем с форматом ответов GigaChat node
- Четкая обработка ошибок

### 2. Производительность
- Низкая temperature (0.1) для стабильных результатов
- JSON Mode для гарантированного формата
- Оптимизированные token budgets

### 3. Валидация
- Универсальный Guardrail для всех агентов
- Автоматическая валидация JSON
- Fallback на пустые структуры при ошибках

### 4. Масштабируемость
- Единообразная архитектура всех агентов
- Легко добавлять новые агенты
- Простое тестирование и отладка

## Миграция с GigaChat Node

### Что изменилось

| Компонент | Было | Стало |
|-----------|------|-------|
| **API Call** | `n8n-nodes-gigachat.gigaChat` | `n8n-nodes-base.httpRequest` |
| **Prompt** | Прямо в GigaChat node | Отдельный Code node |
| **Response** | `$json.response` | `$json.choices[0].message.content` |
| **Validation** | Встроенная | Через Guardrail sub-workflow |

### Преимущества миграции

- ✅ **Совместимость**: Работает с gpt2giga-proxy
- ✅ **JSON Mode**: Поддержка `response_format`
- ✅ **Контроль**: Полный контроль над запросами
- ✅ **Валидация**: Универсальная система валидации
- ✅ **Отладка**: Лучшее логирование и мониторинг

## Тестирование

### Проверка работы агента

1. **Импорт workflow** в n8n
2. **Тестовый запуск** с реальными данными
3. **Проверка логов** Guardrail
4. **Валидация JSON** ответов

### Ожидаемые результаты

- ✅ Чистый JSON без markdown блоков
- ✅ Реальные имена пользователей (не @user1, @user2)
- ✅ Корректная структура данных
- ✅ Отсутствие экранированных кавычек

## Troubleshooting

### Частые проблемы

1. **JSON Parse Error**
   - Проверить логи Guardrail
   - Убедиться в корректности `response_format`

2. **Empty Response**
   - Проверить доступность gpt2giga-proxy
   - Проверить параметры HTTP Request

3. **Invalid JSON Structure**
   - Проверить промпты в Prepare Prompt node
   - Убедиться в корректности system_message

### Логи для отладки

- **Prepare Prompt**: Проверить формирование system_message/user_message
- **HTTP Request**: Проверить URL и параметры запроса
- **Parse Response**: Проверить извлечение content
- **Guardrail**: Проверить валидацию JSON

## Заключение

HTTP Request подход обеспечивает надежную работу всех агентов с gpt2giga-proxy, поддерживает JSON Mode и предоставляет полный контроль над процессом генерации дайджестов. Все агенты теперь используют единообразную архитектуру с валидацией через Guardrail.
