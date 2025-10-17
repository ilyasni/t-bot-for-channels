"""
Key Moments Agent

Выделение важных решений, вопросов и поворотных моментов в диалоге.
Использует GigaChat для анализа ключевых моментов с Pydantic structured output.

Условный агент: активен при detail_level >= standard
"""

import logging
from typing import Dict, Any, List

from .base import BaseAgent
from .config import get_llm_for_agent
from .schemas import KeyMomentsOutput

logger = logging.getLogger(__name__)


class KeyMomentsAgent(BaseAgent):
    """Агент для извлечения ключевых моментов диалогов с Pydantic structured output"""
    
    def __init__(self):
        # Используем GigaChat для анализа ключевых моментов
        llm = get_llm_for_agent("emotion_analysis")
        
        system_prompt = """Ты — эксперт по извлечению ключевых моментов из диалогов.

ТВОЯ РОЛЬ: Выделять важные решения, вопросы и поворотные моменты.
ГРАНИЦЫ: Работаешь только с ключевыми моментами, не анализируешь общую атмосферу.

КРИТЕРИИ ВЫБОРА:
- key_decisions: важные решения, влияющие на проект/команду
- critical_questions: вопросы, требующие ответа для прогресса
- action_items: конкретные действия, которые нужно выполнить
- turning_points: моменты изменения направления обсуждения
- insights: важные инсайты или открытия

ПРИМЕРЫ ПРАВИЛЬНОГО ВЫВОДА:
{{
  "key_decisions": ["Использовать Docker для контейнеризации", "Принять решение о миграции на PostgreSQL"],
  "critical_questions": ["Как обеспечить безопасность API?", "Когда планируется релиз?"],
  "action_items": ["Настроить CI/CD pipeline", "Провести code review"],
  "turning_points": ["Обнаружена проблема с производительностью", "Изменены требования к архитектуре"],
  "insights": ["Текущая архитектура не масштабируется", "Команда готова к переходу на микросервисы"]
}}

ВАЖНО:
- Фокусируйся на значимых моментах, влияющих на результат
- Выделяй конкретные решения и действия
- Определяй критические вопросы, требующие ответа
- КРИТИЧНО: Сохраняй реальные usernames участников из сообщений"""

        super().__init__(
            llm=llm,
            system_prompt=system_prompt,
            agent_name="key_moments",
            output_model=KeyMomentsOutput,
            timeout=30.0
        )
    
    async def _process_input(self, input_data: Dict[str, Any]) -> str:
        """Формирование user message для анализа ключевых моментов"""
        messages_text = input_data.get("messages_text", input_data.get("messages", ""))
        assessment = input_data.get("assessment", None)
        if assessment and hasattr(assessment, 'detail_level'):
            detail_level = assessment.detail_level
        else:
            detail_level = "standard"
        
        # Получение контекста от других агентов
        topics_obj = input_data.get("topics", None)
        emotions_obj = input_data.get("emotions", None)
        
        # Извлекаем данные из Pydantic объектов или словарей
        topics = []
        if topics_obj:
            if hasattr(topics_obj, 'topics'):
                topics = topics_obj.topics
            elif isinstance(topics_obj, dict):
                topics = topics_obj.get("topics", [])
        
        emotions = {}
        if emotions_obj:
            if hasattr(emotions_obj, 'overall_tone'):
                emotions = {
                    'overall_tone': emotions_obj.overall_tone,
                    'atmosphere': emotions_obj.atmosphere
                }
            elif isinstance(emotions_obj, dict):
                emotions = emotions_obj
        
        # Формирование контекста
        context_parts = []
        
        if topics:
            if hasattr(topics[0], 'name'):
                topics_text = ", ".join([t.name for t in topics[:3]])
            else:
                topics_text = ", ".join([t.get("name", "") for t in topics[:3]])
            context_parts.append(f"Основные темы: {topics_text}")
        
        if emotions.get("overall_tone"):
            context_parts.append(f"Эмоциональный тон: {emotions['overall_tone']}")
        
        context = "\n".join(context_parts) if context_parts else "Контекст не определен"
        
        user_message = f"""Проанализируй диалог и выдели ключевые моменты.

УРОВЕНЬ ДЕТАЛИЗАЦИИ: {detail_level}

КОНТЕКСТ:
{context}

ДИАЛОГ:
{messages_text}

Выдели важные решения, критические вопросы, действия и поворотные моменты."""

        return user_message
    
    async def _process_output(self, output: KeyMomentsOutput, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка результата анализа ключевых моментов"""
        try:
            # Pydantic модель уже валидирована
            result = {
                "key_decisions": output.key_decisions,
                "critical_questions": output.critical_questions,
                "action_items": output.action_items,
                "turning_points": output.turning_points,
                "insights": output.insights
            }
            
            logger.info(f"🔑 Ключевые моменты: {len(output.key_decisions)} решений, {len(output.critical_questions)} вопросов")
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа ключевых моментов: {e}")
            return {
                "key_decisions": [],
                "critical_questions": [],
                "action_items": [],
                "turning_points": [],
                "insights": [],
                "error": str(e),
                "fallback": True
            }