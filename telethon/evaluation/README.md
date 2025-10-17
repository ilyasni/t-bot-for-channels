# Telegram Bot Evaluation System

Полноценная система оценки качества ответов Telegram бота с использованием RAGAS metrics и golden dataset.

## 🎯 Возможности

### ✅ Реализованные функции

- **Golden Dataset Management** - CRUD операции для эталонных Q&A
- **RAGAS Integration** - стандартные и custom Telegram-specific метрики
- **Batch Evaluation** - параллельная оценка на больших datasets
- **Langfuse Integration** - traces, scores, A/B testing
- **Prometheus Metrics** - детальные метрики качества
- **Admin Commands** - управление через Telegram бота
- **CLI Tools** - автоматизация через командную строку
- **Grafana Dashboard** - визуализация метрик

### 📊 Метрики качества

**Стандартные RAGAS метрики:**
- `AnswerCorrectness` - semantic similarity + factual overlap
- `FactualCorrectness` - проверка фактической точности
- `Faithfulness` - соответствие retrieved context
- `ContextRelevance` - релевантность найденных постов

**Telegram-specific custom метрики:**
- `ChannelContextAwareness` - понимает ли бот специфику канала
- `GroupSynthesisQuality` - качество синтеза group discussions
- `MultiSourceCoherence` - согласованность при синтезе из разных каналов
- `ToneAppropriateness` - соответствие тона аудитории

## 🏗️ Архитектура

```
telethon/evaluation/
├── __init__.py                    # Module exports
├── schemas.py                     # Pydantic models
├── metrics.py                     # Prometheus metrics
├── golden_dataset_manager.py      # CRUD для golden data
├── bot_evaluator.py              # RAGAS integration
├── evaluation_runner.py          # Batch evaluation
├── langfuse_integration.py       # Langfuse Datasets API
└── cli.py                        # Command line tools
```

## 📁 Golden Datasets

### Структура dataset

```json
{
  "version": "2.0.0",
  "dataset_name": "automotive_tech_channels_v1",
  "items": [
    {
      "dataset_name": "automotive_tech_channels_v1",
      "item_id": "auto_001",
      "category": "automotive_tech",
      "input": {
        "user_id": 123456,
        "channels": ["@drifting_channel", "@automotive_tech"],
        "context_type": "multi_channel"
      },
      "query": "Как настроить дифференциал для дрифта?",
      "telegram_context": {...},
      "expected_output": "Для дрифта нужно настроить...",
      "retrieved_contexts": [...],
      "metadata": {...},
      "difficulty": "advanced",
      "tone": "technical",
      "requires_multi_source": true
    }
  ]
}
```

### Доступные datasets

- **`automotive_tech_channels_v1`** - automotive и tech каналы (5 items)
- **`team_discussions_groups_v1`** - group discussions (3 items)

## 🚀 Использование

### 1. Telegram Admin Commands

```bash
# Показать доступные datasets
/evaluate_datasets

# Запустить evaluation
/evaluate automotive_tech_channels_v1 eval_v1

# Запустить с конкретной моделью
/evaluate automotive_tech_channels_v1 eval_gpt4o openrouter gpt-4o

# Статус evaluation runs
/evaluate_status

# Результаты конкретного run
/evaluate_results eval_v1
```

### 2. CLI Tools

```bash
# Создать dataset из JSON файла
python -m evaluation.cli create-dataset \
    --name "my_dataset" \
    --file "data/golden_qa.json" \
    --sync-langfuse

# Запустить evaluation
python -m evaluation.cli run-evaluation \
    --dataset "automotive_tech_channels_v1" \
    --run-name "eval_gpt4o" \
    --model-provider "openrouter" \
    --model-name "gpt-4o" \
    --workers 4

# Экспортировать результаты
python -m evaluation.cli export-results \
    --run-name "eval_gpt4o" \
    --output "results.json"

# Статистика dataset
python -m evaluation.cli dataset-stats \
    --dataset "automotive_tech_channels_v1"
```

### 3. API Endpoints

```bash
# Запустить batch evaluation
curl -X POST http://localhost:8020/evaluation/batch \
    -H "Content-Type: application/json" \
    -d '{
        "dataset_name": "automotive_tech_channels_v1",
        "run_name": "eval_api_test",
        "model_provider": "openrouter",
        "model_name": "gpt-4o-mini"
    }'

# Статус evaluation run
curl http://localhost:8020/evaluation/status/eval_api_test

# Результаты evaluation run
curl http://localhost:8020/evaluation/results/eval_api_test
```

## 📊 Метрики и мониторинг

### Prometheus Metrics

- `bot_evaluation_answer_correctness` - распределение correctness scores
- `bot_evaluation_faithfulness` - распределение faithfulness scores
- `bot_evaluation_channel_context_awareness` - channel awareness scores
- `bot_evaluation_group_synthesis_quality` - group synthesis scores
- `bot_evaluation_runs_total` - счетчик evaluation runs
- `bot_evaluation_duration_seconds` - длительность evaluation runs
- `bot_evaluation_runs_active` - активные evaluation runs
- `bot_evaluation_items_processed_total` - обработанные items

### Grafana Dashboard

Dashboard доступен по адресу: `http://grafana:3000/d/bot-evaluation`

**Панели:**
- Answer Correctness Rate over time
- Faithfulness Rate over time
- Average scores by dataset (gauges)
- Evaluation runs total
- Duration percentiles
- Items processed

### Langfuse Integration

- **Datasets** - golden Q&A с метаданными
- **Traces** - детальные traces для каждого evaluation
- **Scores** - метрики качества по каждому item
- **Runs** - A/B testing разных моделей

URL: `https://langfuse.produman.studio/datasets/{dataset_name}/runs/{run_name}`

## ⚙️ Конфигурация

### Environment Variables

```bash
# Evaluation metrics
EVALUATION_METRICS_ENABLED=true

# Langfuse integration
LANGFUSE_URL=http://localhost:3000

# Evaluation settings
EVALUATION_ITEM_TIMEOUT=300
EVALUATION_PARALLEL_WORKERS=4
EVALUATION_DEFAULT_MODEL_PROVIDER=openrouter
EVALUATION_DEFAULT_MODEL_NAME=gpt-4o-mini
```

### Database Schema

```sql
-- Golden dataset items
CREATE TABLE evaluation_golden_dataset (
    id SERIAL PRIMARY KEY,
    dataset_name VARCHAR(255) NOT NULL,
    item_id VARCHAR(255) UNIQUE NOT NULL,
    category VARCHAR(100) NOT NULL,
    input_data JSONB NOT NULL,
    query TEXT NOT NULL,
    telegram_context JSONB NOT NULL,
    expected_output TEXT NOT NULL,
    retrieved_contexts JSONB,
    metadata JSONB DEFAULT '{}',
    difficulty VARCHAR(20),
    tone VARCHAR(20),
    requires_multi_source BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Evaluation runs
CREATE TABLE evaluation_runs (
    id SERIAL PRIMARY KEY,
    run_name VARCHAR(255) UNIQUE NOT NULL,
    dataset_name VARCHAR(255) NOT NULL,
    model_provider VARCHAR(50) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    progress FLOAT DEFAULT 0.0,
    total_items INTEGER DEFAULT 0,
    processed_items INTEGER DEFAULT 0,
    avg_score FLOAT,
    scores JSONB,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

-- Evaluation results
CREATE TABLE evaluation_results (
    id SERIAL PRIMARY KEY,
    run_id INTEGER REFERENCES evaluation_runs(id),
    item_id VARCHAR(255) NOT NULL,
    query TEXT NOT NULL,
    expected_output TEXT NOT NULL,
    actual_output TEXT NOT NULL,
    answer_correctness FLOAT,
    faithfulness FLOAT,
    context_relevance FLOAT,
    channel_context_awareness FLOAT,
    group_synthesis_quality FLOAT,
    multi_source_coherence FLOAT,
    tone_appropriateness FLOAT,
    overall_score FLOAT,
    evaluated_at TIMESTAMPTZ DEFAULT NOW()
);
```

## 🔧 Разработка

### Добавление новых метрик

1. Создать custom AspectCritic в `bot_evaluator.py`:

```python
def _create_custom_metric(self) -> AspectCritic:
    return AspectCritic(
        name="custom_metric_name",
        definition="""
        Описание метрики...
        Верните 1.0 если условие выполнено, 0.0 иначе.
        """,
        llm=self.ragas_llm
    )
```

2. Добавить в список метрик в `_setup_ragas_metrics()`

3. Добавить Prometheus metric в `metrics.py`

4. Обновить схемы в `schemas.py`

### Добавление новых datasets

1. Создать JSON файл в `data/` директории
2. Использовать CLI для импорта:

```bash
python -m evaluation.cli create-dataset \
    --name "new_dataset" \
    --file "data/new_dataset.json"
```

### Расширение API

Добавить новые endpoints в `rag_service/main.py`:

```python
@app.get("/evaluation/custom-endpoint")
async def custom_endpoint():
    # Implementation
    pass
```

## 🧪 Тестирование

### Запуск evaluation

```bash
# Тест на sample dataset
python -m evaluation.cli run-evaluation \
    --dataset "automotive_tech_channels_v1" \
    --run-name "test_run" \
    --workers 2 \
    --timeout 60
```

### Проверка метрик

```bash
# Prometheus metrics
curl http://localhost:9090/metrics | grep bot_evaluation

# Grafana dashboard
open http://grafana:3000/d/bot-evaluation
```

### Langfuse traces

```bash
# Проверить traces в Langfuse UI
open https://langfuse.produman.studio/datasets
```

## 📈 Best Practices

### Golden Dataset

- **Качество over количество** - лучше 10 качественных items чем 100 плохих
- **Разнообразие** - включайте разные категории, сложности, типы контекста
- **Актуальность** - регулярно обновляйте dataset
- **Валидация** - проверяйте expected_output вручную

### Evaluation

- **A/B testing** - сравнивайте разные модели на одном dataset
- **Регулярность** - запускайте evaluation после изменений в боте
- **Мониторинг** - отслеживайте тренды качества
- **Анализ** - изучайте ошибки и улучшайте систему

### Production

- **Graceful degradation** - система работает даже если компоненты недоступны
- **Resource limits** - ограничивайте параллельность и timeout
- **Error handling** - логируйте ошибки и продолжайте работу
- **Security** - проверяйте права доступа к admin командам

## 🐛 Troubleshooting

### RAGAS не работает

```bash
# Проверить установку
pip list | grep ragas

# Проверить импорты
python -c "from ragas import evaluate; print('RAGAS OK')"
```

### Langfuse недоступен

```bash
# Проверить статус
docker ps | grep langfuse

# Проверить логи
docker logs langfuse-web
```

### Evaluation fails

```bash
# Проверить логи
docker logs telethon | grep evaluation

# Проверить database
docker exec -it postgres psql -U postgres -d postgres -c "SELECT * FROM evaluation_runs;"
```

### Prometheus metrics отсутствуют

```bash
# Проверить конфигурацию
echo $EVALUATION_METRICS_ENABLED

# Проверить endpoint
curl http://localhost:8020/metrics | grep bot_evaluation
```

## 📚 Дополнительные ресурсы

- [RAGAS Documentation](https://docs.ragas.io/)
- [Langfuse Documentation](https://langfuse.com/docs)
- [Prometheus Client Python](https://github.com/prometheus/client_python)
- [Telegram Bot API](https://core.telegram.org/bots/api)

## 🤝 Contributing

1. Создайте feature branch
2. Добавьте тесты для новых функций
3. Обновите документацию
4. Создайте pull request

## 📄 License

Этот проект использует ту же лицензию что и основной Telegram Bot проект.
