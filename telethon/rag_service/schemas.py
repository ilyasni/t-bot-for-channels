"""
Pydantic модели для RAG Service API
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


# ============================================================================
# Request Models
# ============================================================================

class IndexPostRequest(BaseModel):
    """Запрос на индексацию поста"""
    post_id: int


class IndexBatchRequest(BaseModel):
    """Запрос на batch индексацию"""
    post_ids: List[int] = Field(..., description="Список ID постов для индексации")


class SearchRequest(BaseModel):
    """Запрос на поиск"""
    query: str = Field(..., description="Поисковый запрос")
    user_id: int = Field(..., description="ID пользователя")
    limit: int = Field(10, ge=1, le=100, description="Количество результатов")
    channel_id: Optional[int] = Field(None, description="Фильтр по каналу")
    tags: Optional[List[str]] = Field(None, description="Фильтр по тегам")
    date_from: Optional[datetime] = Field(None, description="Фильтр по дате (от)")
    date_to: Optional[datetime] = Field(None, description="Фильтр по дате (до)")
    min_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Минимальный score релевантности")


class AskRequest(BaseModel):
    """Запрос на RAG-ответ"""
    query: str = Field(..., description="Вопрос пользователя")
    user_id: int = Field(..., description="ID пользователя")
    context_limit: int = Field(10, ge=1, le=20, description="Количество документов для контекста")
    channels: Optional[List[int]] = Field(None, description="Фильтр по каналам")
    tags: Optional[List[str]] = Field(None, description="Фильтр по тегам")
    date_from: Optional[datetime] = Field(None, description="Фильтр по дате (от)")
    date_to: Optional[datetime] = Field(None, description="Фильтр по дате (до)")


class DigestRequest(BaseModel):
    """Запрос на генерацию дайджеста"""
    user_id: int = Field(..., description="ID пользователя")
    date_from: datetime = Field(..., description="Начало периода")
    date_to: datetime = Field(..., description="Конец периода")
    channels: Optional[List[int]] = Field(None, description="Фильтр по каналам")
    tags: Optional[List[str]] = Field(None, description="Фильтр по тегам")
    format: str = Field("markdown", description="Формат дайджеста (markdown/html/plain)")
    max_posts: int = Field(20, ge=1, le=500, description="Максимум постов в дайджесте")


class DigestSettingsUpdate(BaseModel):
    """Обновление настроек дайджеста"""
    enabled: Optional[bool] = Field(None, description="Включить/выключить дайджест")
    frequency: Optional[str] = Field(None, description="Частота (daily/weekly/custom)")
    time: Optional[str] = Field(None, description="Время отправки (HH:MM)")
    days_of_week: Optional[List[int]] = Field(None, description="Дни недели для weekly (1-7)")
    timezone: Optional[str] = Field(None, description="Часовой пояс")
    channels: Optional[List[int]] = Field(None, description="Каналы для дайджеста")
    tags: Optional[List[str]] = Field(None, description="Теги для дайджеста")
    format: Optional[str] = Field(None, description="Формат дайджеста")
    max_posts: Optional[int] = Field(None, ge=1, le=500, description="Максимум постов")
    delivery_method: Optional[str] = Field(None, description="Метод доставки (telegram/email)")
    email: Optional[str] = Field(None, description="Email для доставки")
    
    # AI Summarization
    ai_summarize: Optional[bool] = Field(None, description="Использовать AI-суммаризацию")
    preferred_topics: Optional[List[str]] = Field(None, description="Предпочитаемые темы пользователя")
    summary_style: Optional[str] = Field(None, description="Стиль саммари (concise/detailed/executive)")
    topics_limit: Optional[int] = Field(None, ge=3, le=5, description="Максимум тем в AI-дайджесте (3-5)")


# ============================================================================
# Response Models
# ============================================================================

class SearchResult(BaseModel):
    """Результат поиска"""
    post_id: int
    score: float
    text: str
    channel_id: int
    channel_username: str
    posted_at: datetime
    url: Optional[str] = None
    tags: Optional[List[str]] = None
    views: Optional[int] = None


class SearchResponse(BaseModel):
    """Ответ на поиск"""
    query: str
    user_id: int
    results_count: int
    results: List[SearchResult]
    filters_applied: dict


class Source(BaseModel):
    """Источник для RAG-ответа"""
    post_id: int
    channel_username: str
    posted_at: datetime
    url: Optional[str] = None
    excerpt: str


class AskResponse(BaseModel):
    """Ответ на RAG-запрос"""
    query: str
    answer: str
    sources: List[Source]
    context_used: int


class DigestResponse(BaseModel):
    """Ответ с дайджестом"""
    user_id: int
    period: dict
    posts_count: int
    digest: str
    format: str
    generated_at: datetime
    ai_generated: bool = False  # Признак AI-генерации


class DigestSettingsResponse(BaseModel):
    """Настройки дайджеста пользователя"""
    user_id: int
    enabled: bool
    frequency: str
    time: str
    days_of_week: Optional[List[int]] = None
    timezone: str
    channels: Optional[List[int]] = None
    tags: Optional[List[str]] = None
    format: str
    max_posts: int
    delivery_method: str
    email: Optional[str] = None
    last_sent_at: Optional[datetime] = None
    next_scheduled_at: Optional[datetime] = None
    
    # AI Summarization
    ai_summarize: bool = False
    preferred_topics: Optional[List[str]] = None
    summary_style: str = "concise"
    topics_limit: int = 5


class IndexingStatusResponse(BaseModel):
    """Статус индексации"""
    post_id: int
    user_id: int
    status: str
    indexed_at: Optional[datetime] = None
    error: Optional[str] = None


class CollectionStatsResponse(BaseModel):
    """Статистика коллекции пользователя"""
    user_id: int
    collection_name: str
    vectors_count: int
    points_count: int
    indexed_posts: int
    pending_posts: int
    failed_posts: int


class HealthResponse(BaseModel):
    """Статус здоровья сервиса"""
    status: str
    qdrant_connected: bool
    gigachat_available: bool
    openrouter_available: bool
    version: str


class UserInterestsResponse(BaseModel):
    """Интересы пользователя (вручную + из истории запросов)"""
    user_id: int
    preferred_topics: List[str]  # Вручную указанные темы
    inferred_topics: List[str]   # Из истории RAG-запросов
    combined_topics: List[str]   # Финальный список

