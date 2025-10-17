"""
Timeline Builder Agent

Создание временной последовательности событий и развития обсуждения.
Использует GigaChat для построения хронологии с Pydantic structured output.

Условный агент: активен при detail_level >= detailed
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timezone

from .base import BaseAgent
from .config import get_llm_for_agent
from .schemas import TimelineOutput

logger = logging.getLogger(__name__)


class TimelineBuilderAgent(BaseAgent):
    """Агент для построения хронологии диалогов с Pydantic structured output"""
    
    def __init__(self):
        # Используем GigaChat для построения хронологии
        llm = get_llm_for_agent("emotion_analysis")
        
        system_prompt = """Ты — эксперт по построению хронологии диалогов.

ТВОЯ РОЛЬ: Создавать временную последовательность событий и развития обсуждения.
ГРАНИЦЫ: Работаешь только с хронологией, не анализируешь эмоции или темы отдельно.

КРИТЕРИИ АНАЛИЗА:
- timeline_events: важные события в хронологическом порядке
- discussion_phases: фазы развития обсуждения
- topic_evolution: как темы развивались во времени

ПРИМЕРЫ ПРАВИЛЬНОГО ВЫВОДА:
{{
  "timeline_events": [
    {{
      "timestamp": "10:30",
      "event": "Обсуждение архитектуры проекта началось",
      "participants": ["john_doe", "alice_smith"],
      "significance": "high"
    }},
    {{
      "timestamp": "11:15",
      "event": "Принято решение использовать Docker",
      "participants": ["john_doe"],
      "significance": "high"
    }}
  ],
  "discussion_phases": ["Планирование", "Обсуждение решений", "Подведение итогов"],
  "topic_evolution": ["Архитектура → Контейнеризация → Безопасность"]
}}

ВАЖНО:
- Создавай хронологическую последовательность событий
- Выделяй фазы развития обсуждения
- Отслеживай эволюцию тем во времени
- Указывай участников и значимость событий
- КРИТИЧНО: Сохраняй реальные usernames участников из сообщений
- ОБЯЗАТЕЛЬНО: Возвращай валидный JSON объект, НЕ null
- Если нет событий, возвращай пустые массивы, но НЕ null"""

        super().__init__(
            llm=llm,
            system_prompt=system_prompt,
            agent_name="timeline_builder",
            output_model=TimelineOutput,
            timeout=30.0
        )
    
    async def _process_input(self, input_data: Dict[str, Any]) -> str:
        """Формирование user message для построения хронологии"""
        messages_text = input_data.get("messages_text", input_data.get("messages", ""))
        assessment = input_data.get("assessment", None)
        if assessment and hasattr(assessment, 'detail_level'):
            detail_level = assessment.detail_level
        else:
            detail_level = "detailed"
        
        # Получение контекста от других агентов
        topics_obj = input_data.get("topics", None)
        
        # Извлекаем данные из Pydantic объектов или словарей
        topics = []
        if topics_obj:
            if hasattr(topics_obj, 'topics'):
                topics = topics_obj.topics
            elif isinstance(topics_obj, dict):
                topics = topics_obj.get("topics", [])
        speakers_obj = input_data.get("speakers", None)
        
        # Извлекаем данные из Pydantic объектов или словарей
        speakers = []
        if speakers_obj:
            if hasattr(speakers_obj, 'speakers'):
                speakers = speakers_obj.speakers
            elif isinstance(speakers_obj, dict):
                speakers = speakers_obj.get("speakers", [])
        
        # Формирование контекста
        context_parts = []
        
        if topics:
            if hasattr(topics[0], 'name'):
                topics_text = ", ".join([t.name for t in topics[:3]])
            else:
                topics_text = ", ".join([t.get("name", "") for t in topics[:3]])
            context_parts.append(f"Основные темы: {topics_text}")
        
        if speakers:
            if hasattr(speakers[0], 'username'):
                speakers_text = ", ".join([s.username for s in speakers[:3]])
            else:
                speakers_text = ", ".join([s.get("username", "") for s in speakers[:3]])
            context_parts.append(f"Ключевые участники: {speakers_text}")
        
        context = "\n".join(context_parts) if context_parts else "Контекст не определен"
        
        user_message = f"""Построй хронологию диалога.

УРОВЕНЬ ДЕТАЛИЗАЦИИ: {detail_level}

КОНТЕКСТ:
{context}

ДИАЛОГ:
{messages_text}

Создай временную последовательность событий, фазы обсуждения и эволюцию тем."""

        return user_message
    
    async def _process_output(self, output: TimelineOutput, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка результата построения хронологии"""
        try:
            # Pydantic модель уже валидирована
            timeline_events = [
                {
                    "timestamp": event.timestamp,
                    "event": event.event,
                    "participants": event.participants,
                    "significance": event.significance
                }
                for event in output.timeline_events
            ]
            
            result = {
                "timeline_events": timeline_events,
                "discussion_phases": output.discussion_phases,
                "topic_evolution": output.topic_evolution
            }
            
            logger.info(f"⏰ Хронология: {len(timeline_events)} событий, {len(output.discussion_phases)} фаз")
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка построения хронологии: {e}")
            return {
                "timeline_events": [],
                "discussion_phases": [],
                "topic_evolution": [],
                "error": str(e),
                "fallback": True
            }