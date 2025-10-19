"""
Evaluation module для Telegram Bot

Этот модуль предоставляет систему оценки качества ответов бота
с использованием RAGAS metrics и golden dataset.

Компоненты:
- golden_dataset_manager: CRUD операции для golden Q&A
- bot_evaluator: RAGAS integration и custom metrics
- evaluation_runner: Batch evaluation и progress tracking
- langfuse_integration: Langfuse Datasets API integration
- metrics: Prometheus metrics для evaluation
- schemas: Pydantic models для типизации

Best practices:
- Переиспользуем существующую инфраструктуру (Langfuse, PostgreSQL, Redis)
- Telegram-specific metrics для каналов и групп
- Graceful degradation если компоненты недоступны
- Async/await везде для производительности
"""

from .schemas import (
    GoldenDatasetItem,
    GoldenDatasetCreate,
    EvaluationRun,
    EvaluationResult,
    EvaluationMetrics,
    TelegramContext
)

from .metrics import (
    evaluation_answer_correctness,
    evaluation_faithfulness,
    evaluation_runs_total,
    evaluation_duration_seconds
)

__all__ = [
    # Schemas
    "GoldenDatasetItem",
    "GoldenDatasetCreate", 
    "EvaluationRun",
    "EvaluationResult",
    "EvaluationMetrics",
    "TelegramContext",
    
    # Metrics
    "evaluation_answer_correctness",
    "evaluation_faithfulness", 
    "evaluation_runs_total",
    "evaluation_duration_seconds"
]

__version__ = "1.0.0"
