"""
Pydantic schemas для evaluation system

Определяет типы данных для golden dataset, evaluation runs,
и результатов оценки качества ответов бота.
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field, validator


class ContextType(str, Enum):
    """Типы контекста для Telegram Bot"""
    SINGLE_CHANNEL = "single_channel"
    MULTI_CHANNEL = "multi_channel" 
    GROUP_DIGEST = "group_digest"
    GROUP_MENTION = "group_mention"
    SEARCH_QUERY = "search_query"


class DifficultyLevel(str, Enum):
    """Уровни сложности вопросов"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate" 
    ADVANCED = "advanced"
    EXPERT = "expert"


class ToneType(str, Enum):
    """Типы тона для ответов"""
    TECHNICAL = "technical"
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    FRIENDLY = "friendly"
    FORMAL = "formal"


class TelegramContext(BaseModel):
    """Контекст Telegram для evaluation"""
    user_id: int = Field(..., description="ID пользователя")
    channels: Optional[List[str]] = Field(default_factory=list, description="Список каналов для контекста")
    groups: Optional[List[str]] = Field(default_factory=list, description="Список групп для контекста")
    group_id: Optional[int] = Field(None, description="ID группы (для group_digest)")
    context_type: ContextType = Field(..., description="Тип контекста")
    message_history: Optional[List[str]] = Field(default_factory=list, description="История сообщений")
    
    class Config:
        use_enum_values = True


class GoldenDatasetItem(BaseModel):
    """Элемент golden dataset"""
    item_id: str = Field(..., description="Уникальный ID элемента")
    dataset_name: str = Field(..., description="Название dataset")
    category: str = Field(..., description="Категория (automotive, tech, groups)")
    
    # Input data
    input: Dict[str, Any] = Field(..., description="Входные данные для бота")
    query: str = Field(..., description="Текст запроса пользователя")
    telegram_context: TelegramContext = Field(..., description="Контекст Telegram")
    
    # Expected output
    expected_output: str = Field(..., description="Ожидаемый ответ бота")
    retrieved_contexts: Optional[List[str]] = Field(None, description="Retrieved контексты для RAG")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Дополнительные метаданные")
    difficulty: Optional[DifficultyLevel] = Field(None, description="Уровень сложности")
    tone: Optional[ToneType] = Field(None, description="Требуемый тон ответа")
    requires_multi_source: bool = Field(False, description="Требует ли синтез из нескольких источников")
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True


class GoldenDatasetCreate(BaseModel):
    """Создание нового golden dataset"""
    name: str = Field(..., description="Название dataset")
    description: str = Field("", description="Описание dataset")
    category: str = Field(..., description="Категория dataset")
    items: List[GoldenDatasetItem] = Field(..., description="Элементы dataset")
    sync_to_langfuse: bool = Field(True, description="Синхронизировать с Langfuse")


class EvaluationRun(BaseModel):
    """Запуск evaluation"""
    run_id: Optional[str] = Field(None, description="ID запуска")
    run_name: str = Field(..., description="Название run")
    dataset_name: str = Field(..., description="Название dataset для оценки")
    model_provider: str = Field(..., description="Провайдер модели (gigachat, openrouter)")
    model_name: str = Field(..., description="Название модели")
    
    # Configuration
    parallel_workers: int = Field(4, description="Количество параллельных воркеров")
    timeout_seconds: int = Field(300, description="Timeout для одного evaluation")
    
    # Status
    status: str = Field("pending", description="Статус run")
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = Field(0.0, description="Прогресс (0.0-1.0)")
    
    # Results
    total_items: int = Field(0, description="Общее количество элементов")
    processed_items: int = Field(0, description="Обработано элементов")
    successful_items: int = Field(0, description="Успешно обработано")
    failed_items: int = Field(0, description="Ошибок")
    avg_score: Optional[float] = Field(None, description="Общий score")
    scores: Optional[Dict[str, float]] = Field(None, description="Средние scores")
    duration_seconds: Optional[float] = Field(None, description="Длительность в секундах")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Метаданные")
    
    class Config:
        use_enum_values = True


class EvaluationMetrics(BaseModel):
    """Метрики оценки качества"""
    # Standard RAGAS metrics
    answer_correctness: Optional[float] = Field(None, description="Correctness (0.0-1.0)")
    faithfulness: Optional[float] = Field(None, description="Faithfulness to context (0.0-1.0)")
    context_relevance: Optional[float] = Field(None, description="Context relevance (0.0-1.0)")
    factual_correctness: Optional[float] = Field(None, description="Factual correctness (0.0-1.0)")
    
    # Telegram-specific metrics
    channel_context_awareness: Optional[float] = Field(None, description="Channel context awareness (0.0-1.0)")
    group_synthesis_quality: Optional[float] = Field(None, description="Group synthesis quality (0.0-1.0)")
    multi_source_coherence: Optional[float] = Field(None, description="Multi-source coherence (0.0-1.0)")
    tone_appropriateness: Optional[float] = Field(None, description="Tone appropriateness (0.0-1.0)")
    
    # Overall score
    overall_score: Optional[float] = Field(None, description="Overall quality score (0.0-1.0)")
    
    # Metadata
    evaluation_time: Optional[float] = Field(None, description="Время evaluation в секундах")
    model_used: Optional[str] = Field(None, description="Модель для evaluation")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EvaluationResult(BaseModel):
    """Результат evaluation одного элемента"""
    item_id: str = Field(..., description="ID элемента")
    run_id: str = Field(..., description="ID запуска")
    model_response: str = Field(..., description="Ответ модели")
    scores: EvaluationMetrics = Field(..., description="Метрики качества")
    overall_score: float = Field(..., description="Общий score")
    status: str = Field(..., description="Статус evaluation")
    error_message: Optional[str] = Field(None, description="Ошибка если есть")
    langfuse_trace_id: Optional[str] = Field(None, description="ID trace в Langfuse")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EvaluationBatchRequest(BaseModel):
    """Запрос на batch evaluation"""
    dataset_name: str = Field(..., description="Название dataset")
    run_name: str = Field(..., description="Название run")
    model_provider: str = Field(..., description="Провайдер модели")
    model_name: str = Field(..., description="Название модели")
    max_items: Optional[int] = Field(None, description="Максимальное количество элементов")
    parallel_workers: int = Field(4, description="Количество воркеров")
    timeout_seconds: int = Field(300, description="Timeout")


class EvaluationBatchResponse(BaseModel):
    """Ответ на batch evaluation"""
    run_id: str = Field(..., description="ID запуска")
    run_name: str = Field(..., description="Название запуска")
    status: str = Field(..., description="Статус")
    total_items: int = Field(..., description="Общее количество элементов")
    message: str = Field(..., description="Сообщение")
    estimated_duration: Optional[int] = Field(None, description="Ожидаемое время в секундах")


class EvaluationStatusResponse(BaseModel):
    """Статус evaluation run"""
    run_id: str = Field(..., description="ID запуска")
    run_name: str = Field(..., description="Название запуска")
    status: str = Field(..., description="Статус")
    progress_percentage: float = Field(..., description="Прогресс в процентах")
    progress: float = Field(..., description="Прогресс (0.0-1.0)")
    total_items: int = Field(..., description="Всего элементов")
    processed_items: int = Field(..., description="Обработано")
    successful_items: int = Field(..., description="Успешно обработано")
    failed_items: int = Field(..., description="Ошибок")
    avg_score: Optional[float] = Field(None, description="Средний score")
    estimated_completion_time: Optional[str] = Field(None, description="Ожидаемое время завершения")
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class EvaluationResultsResponse(BaseModel):
    """Результаты evaluation run"""
    run_id: str = Field(..., description="ID запуска")
    dataset_name: str = Field(..., description="Название dataset")
    model_provider: str = Field(..., description="Провайдер модели")
    model_name: str = Field(..., description="Название модели")
    
    # Summary
    total_items: int = Field(..., description="Всего элементов")
    successful_items: int = Field(..., description="Успешно оценено")
    failed_items: int = Field(..., description="Ошибки")
    
    # Scores
    avg_scores: Dict[str, float] = Field(..., description="Средние scores по метрикам")
    overall_score: float = Field(..., description="Общий score")
    
    # Results
    results: List[EvaluationResult] = Field(..., description="Детальные результаты")
    
    # Timestamps
    started_at: datetime = Field(..., description="Время начала")
    completed_at: datetime = Field(..., description="Время завершения")
    duration_seconds: float = Field(..., description="Длительность в секундах")
