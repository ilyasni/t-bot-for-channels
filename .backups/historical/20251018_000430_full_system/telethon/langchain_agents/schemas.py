"""
Pydantic модели для структурированных выводов всех LangChain агентов

Гарантирует валидацию и типизацию всех выходных данных агентов.
Следует best practices из LangChain для structured output.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime, timezone


class Topic(BaseModel):
    """Модель темы диалога"""
    name: str = Field(..., description="Название темы", min_length=1, max_length=100)
    priority: Literal["high", "medium", "low"] = Field(..., description="Приоритет темы")
    message_count: int = Field(..., description="Количество сообщений по теме", ge=0)
    emoji: str = Field(default="", description="Эмодзи для темы", max_length=10)


class TopicsOutput(BaseModel):
    """Вывод Topic Extractor агента"""
    topics: List[Topic] = Field(default_factory=list, description="Список тем", max_items=15)


class EmotionsOutput(BaseModel):
    """Вывод Emotion Analyzer агента"""
    overall_tone: Literal["positive", "neutral", "negative", "mixed", "concerned", "light-hearted"] = Field(
        ..., description="Общий эмоциональный тон диалога"
    )
    atmosphere: Literal[
        "collaborative", "competitive", "supportive", "tense", 
        "relaxed", "formal", "casual", "mixed", "light-hearted", "serious", "friendly"
    ] = Field(..., description="Атмосфера общения")
    emotional_indicators: List[str] = Field(
        default_factory=list, description="Эмоциональные индикаторы", max_items=10
    )
    intensity_level: Literal["low", "medium", "high"] = Field(
        ..., description="Уровень интенсивности эмоций"
    )
    intensity_score: float = Field(..., description="Числовая оценка интенсивности 0.0-1.0", ge=0.0, le=1.0)
    key_emotions: List[str] = Field(
        default_factory=list, description="Ключевые эмоции", max_items=5
    )
    conflict_indicators: bool = Field(..., description="Признаки конфликта")
    support_indicators: bool = Field(..., description="Признаки поддержки")
    conflict_percentage: float = Field(default=0.0, description="Процент конфликтности 0-100", ge=0.0, le=100.0)
    collaboration_percentage: float = Field(default=0.0, description="Процент коллаборативности 0-100", ge=0.0, le=100.0)
    stress_percentage: float = Field(default=0.0, description="Процент стресса 0-100", ge=0.0, le=100.0)
    enthusiasm_percentage: float = Field(default=0.0, description="Процент энтузиазма 0-100", ge=0.0, le=100.0)


class Speaker(BaseModel):
    """Модель участника диалога"""
    username: str = Field(..., description="Имя пользователя", min_length=1, max_length=50)
    role: Literal["leader", "supporter", "questioner", "contributor", "observer", "mixed", "participant", "absent", "инициатор", "эксперт", "лидер", "участник", "organizer"] = Field(
        ..., description="Роль участника"
    )
    activity_level: Literal["high", "medium", "low", "none"] = Field(..., description="Уровень активности")
    message_count: int = Field(..., description="Количество сообщений", ge=0)
    contribution_types: List[str] = Field(
        default_factory=list, description="Типы вкладов", max_items=3
    )
    key_contributions: List[str] = Field(
        default_factory=list, description="Ключевые вклады", max_items=3
    )
    detailed_role: str = Field(default="", description="Детальное описание роли и вклада", max_length=200)


class GroupDynamics(BaseModel):
    """Динамика группы"""
    dominant_speaker: str = Field(default="", description="Доминирующий участник", max_length=50)
    most_helpful: str = Field(default="", description="Самый полезный участник", max_length=50)
    most_questions: str = Field(default="", description="Участник с наибольшим количеством вопросов", max_length=50)
    collaboration_level: Literal["high", "medium", "low"] = Field(default="medium", description="Уровень сотрудничества")


class SpeakersOutput(BaseModel):
    """Вывод Speaker Analyzer агента"""
    speakers: List[Speaker] = Field(default_factory=list, description="Список участников")
    group_dynamics: GroupDynamics = Field(default_factory=GroupDynamics, description="Динамика группы")


class SummaryOutput(BaseModel):
    """Вывод Context Summarizer агента"""
    main_points: List[str] = Field(default_factory=list, description="Основные пункты", max_items=10)
    key_decisions: List[str] = Field(default_factory=list, description="Ключевые решения", max_items=5)
    outstanding_issues: List[str] = Field(default_factory=list, description="Нерешенные вопросы", max_items=5)
    next_steps: List[str] = Field(default_factory=list, description="Следующие шаги", max_items=5)
    summary_text: str = Field(default="", description="Текстовое резюме", max_length=2000)


class ContextAdaptation(BaseModel):
    """Адаптация контекста"""
    detail_level: Literal["micro", "brief", "standard", "detailed", "comprehensive"] = Field(
        default="standard", description="Уровень детализации"
    )
    dialogue_type: Literal["discussion", "question_answer", "announcement", "mixed"] = Field(
        default="discussion", description="Тип диалога"
    )
    focus_areas: List[str] = Field(default_factory=list, description="Фокусные области", max_items=5)
    summary_style: Literal["concise", "balanced", "detailed"] = Field(default="balanced", description="Стиль резюме")


class SummarizerOutput(BaseModel):
    """Полный вывод Context Summarizer агента"""
    summary: SummaryOutput = Field(default_factory=SummaryOutput, description="Резюме")
    context_adaptation: ContextAdaptation = Field(default_factory=ContextAdaptation, description="Адаптация контекста")


class KeyMomentsOutput(BaseModel):
    """Вывод Key Moments агента"""
    key_decisions: List[str] = Field(default_factory=list, description="Ключевые решения", max_items=5)
    critical_questions: List[str] = Field(default_factory=list, description="Критические вопросы", max_items=5)
    action_items: List[str] = Field(default_factory=list, description="Пункты действий", max_items=5)
    turning_points: List[str] = Field(default_factory=list, description="Поворотные моменты", max_items=3)
    insights: List[str] = Field(default_factory=list, description="Инсайты", max_items=3)


class TimelineEvent(BaseModel):
    """Событие в хронологии"""
    timestamp: str = Field(..., description="Время события")
    event: str = Field(..., description="Описание события", max_length=200)
    participants: List[str] = Field(default_factory=list, description="Участники события", max_items=3)
    significance: Literal["high", "medium", "low"] = Field(..., description="Значимость события")


class TimelineOutput(BaseModel):
    """Вывод Timeline Builder агента"""
    timeline_events: List[TimelineEvent] = Field(default_factory=list, description="События хронологии", max_items=15)
    discussion_phases: List[str] = Field(default_factory=list, description="Фазы обсуждения", max_items=5)
    topic_evolution: List[str] = Field(default_factory=list, description="Эволюция тем", max_items=5)


class ContextLink(BaseModel):
    """Ссылка или ресурс"""
    url: str = Field(..., description="URL ссылки")
    title: str = Field(..., description="Заголовок ссылки", max_length=200)
    link_type: Literal["external", "telegram", "mention"] = Field(..., description="Тип ссылки")
    relevance: Literal["high", "medium", "low"] = Field(..., description="Релевантность")


class ContextLinksOutput(BaseModel):
    """Вывод Context Links агента"""
    external_links: List[ContextLink] = Field(default_factory=list, description="Внешние ссылки", max_items=10)
    telegram_links: List[ContextLink] = Field(default_factory=list, description="Telegram ссылки", max_items=10)
    mentions: List[str] = Field(default_factory=list, description="Упоминания", max_items=10)


class AgentStatus(BaseModel):
    """Статус выполнения агента"""
    agent_name: str = Field(..., description="Название агента")
    status: Literal["success", "error", "fallback"] = Field(..., description="Статус выполнения")
    execution_time: float = Field(..., description="Время выполнения в секундах")
    error_message: Optional[str] = Field(None, description="Сообщение об ошибке")
    output_summary: Optional[str] = Field(None, description="Краткое описание результата")


class DigestMetadata(BaseModel):
    """Метаданные дайджеста"""
    detail_level: Literal["micro", "brief", "standard", "detailed", "comprehensive"] = Field(
        ..., description="Уровень детализации"
    )
    dialogue_type: Literal["discussion", "question_answer", "announcement", "mixed"] = Field(
        ..., description="Тип диалога"
    )
    participants_count: int = Field(..., description="Количество участников", ge=0)
    message_count: int = Field(..., description="Количество сообщений", ge=0)
    generation_timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Время создания дайджеста"
    )
    agents_status: List[AgentStatus] = Field(default_factory=list, description="Статус выполнения агентов")


class DigestSections(BaseModel):
    """Секции дайджеста"""
    summary: str = Field(..., description="Резюме", max_length=1000)
    topics: str = Field(..., description="Темы", max_length=1000)
    decisions: str = Field(default="", description="Решения", max_length=1000)
    participants: str = Field(..., description="Участники", max_length=1000)
    resources: str = Field(default="", description="Ресурсы", max_length=1000)


class SupervisorOutput(BaseModel):
    """Вывод Supervisor Synthesizer агента"""
    html_digest: str = Field(..., description="HTML дайджест", min_length=50, max_length=10000)
    metadata: DigestMetadata = Field(..., description="Метаданные")
    sections: DigestSections = Field(..., description="Секции дайджеста")
    
    @validator('html_digest')
    def validate_html_content(cls, v):
        import re
        # Убираем все style атрибуты и другие запрещенные атрибуты
        v = re.sub(r'<([^>]+)\s+[^>]*style\s*=\s*["\'][^"\']*["\'][^>]*>', r'<\1>', v)
        
        # Проверяем, что HTML содержит только разрешенные теги
        allowed_tags = ['<b>', '</b>', '<i>', '</i>', '<code>', '</code>', '<pre>', '</pre>', '<a>', '</a>', '<ul>', '</ul>', '<li>', '</li>', '<hr>', '<p>', '</p>', '<span>', '</span>']
        tags = re.findall(r'<[^>]+>', v)
        for tag in tags:
            if tag not in allowed_tags:
                # Заменяем запрещенные теги на разрешенные
                if tag == '<br>' or tag == '<br/>' or tag == '<br />':
                    v = v.replace(tag, ' ')
                else:
                    # Убираем атрибуты из тегов, оставляя только имя тега
                    clean_tag = re.sub(r'<([a-zA-Z]+)[^>]*>', r'<\1>', tag)
                    if clean_tag in allowed_tags:
                        v = v.replace(tag, clean_tag)
                    else:
                        raise ValueError(f'HTML contains forbidden tag: {tag}. Only <b>, <i>, <code>, <pre>, <a>, <ul>, <li>, <hr> are allowed.')
        return v


# Модель для Dialogue Assessor (LLM-based агент)
class AssessmentOutput(BaseModel):
    """Вывод Dialogue Assessor агента"""
    detail_level: Literal["micro", "brief", "standard", "detailed", "comprehensive"] = Field(
        ..., description="Уровень детализации"
    )
    dialogue_type: Literal["discussion", "question_answer", "announcement", "mixed", "brainstorming", "planning", "support"] = Field(
        ..., description="Тип диалога"
    )
    has_links: bool = Field(..., description="Наличие ссылок в диалоге")
    has_decisions: bool = Field(..., description="Присутствуют ли решения в диалоге")
    has_questions: bool = Field(..., description="Есть ли вопросы требующие ответа")
    has_conflicts: bool = Field(..., description="Есть ли конфликты или разногласия")
    complexity_score: float = Field(..., description="Оценка сложности диалога 0.0-1.0", ge=0.0, le=1.0)
    urgency_level: Literal["low", "medium", "high", "critical"] = Field(..., description="Уровень срочности")
    message_count: int = Field(..., description="Количество сообщений", ge=0)
    participants_count: int = Field(..., description="Количество участников", ge=0)
    dominant_topics: List[str] = Field(default_factory=list, description="Доминирующие темы", max_items=5)
    context_notes: str = Field(default="", description="Дополнительные заметки о контексте", max_length=200)


# Экспорт всех моделей
__all__ = [
    "Topic",
    "TopicsOutput", 
    "EmotionsOutput",
    "Speaker",
    "GroupDynamics",
    "SpeakersOutput",
    "SummaryOutput",
    "ContextAdaptation", 
    "SummarizerOutput",
    "KeyMomentsOutput",
    "TimelineEvent",
    "TimelineOutput",
    "ContextLink",
    "ContextLinksOutput",
    "DigestMetadata",
    "DigestSections",
    "SupervisorOutput",
    "AssessmentOutput"
]
