"""
Topic Extractor Agent

Извлекает и классифицирует основные темы диалога с приоритетами.
Использует GigaChat для анализа контента с Pydantic structured output.
"""

import logging
from typing import Dict, Any, List

from .base import BaseAgent
from .config import get_llm_for_agent
from .schemas import TopicsOutput

logger = logging.getLogger(__name__)


class TopicExtractorAgent(BaseAgent):
    """Агент для извлечения тем диалога с Pydantic structured output"""
    
    def __init__(self):
        llm = get_llm_for_agent("fact_extraction")
        
        system_prompt = """Ты — эксперт-аналитик тем в Telegram диалогах.

ТВОЯ РОЛЬ: Извлекать и классифицировать темы обсуждения.
ГРАНИЦЫ: Работаешь только с темами, не анализируешь эмоции или участников.

КРИТЕРИИ ВЫБОРА ТЕМ:
- Тема должна быть значимой для участников
- Отражать суть обсуждения
- Быть конкретной и понятной
- Не дублировать другие темы

ПРИОРИТЕТЫ ТЕМ:
- high: Ключевые решения, важные проблемы, основные цели
- medium: Вспомогательные темы, детали реализации
- low: Мелкие вопросы, уточнения, технические детали

ПРИМЕРЫ ПРАВИЛЬНОГО ВЫВОДА:
{{
  "topics": [
    {{"name": "Проблема с вебвью", "priority": "high", "message_count": 15, "emoji": "❗️"}},
    {{"name": "Обновление приложения", "priority": "medium", "message_count": 7, "emoji": "✨"}},
    {{"name": "Поддержка устройств", "priority": "low", "message_count": 3, "emoji": "🏠"}}
  ]
}}

ВАЖНО:
- Максимум 15 тем
- Каждая тема уникальна
- Названия тем на русском языке
- Приоритеты обоснованы
- КРИТИЧНО: Сохраняй реальные usernames участников из сообщений"""

        super().__init__(
            llm=llm,
            system_prompt=system_prompt,
            agent_name="topic_extractor",
            output_model=TopicsOutput,
            timeout=30.0
        )
    
    async def _process_input(self, input_data: Dict[str, Any]) -> str:
        """Формирование user message для анализа тем"""
        messages_text = input_data.get("messages_text", input_data.get("messages", ""))
        assessment = input_data.get("assessment", None)
        if assessment and hasattr(assessment, 'detail_level'):
            detail_level = assessment.detail_level
        else:
            detail_level = "standard"
        
        # Адаптация под уровень детализации
        max_topics = self._get_max_topics_for_level(detail_level)
        
        user_message = f"""Проанализируй диалог и извлеки основные темы.

УРОВЕНЬ ДЕТАЛИЗАЦИИ: {detail_level}
МАКСИМУМ ТЕМ: {max_topics}

ДИАЛОГ:
{messages_text}

Извлеки темы согласно критериям и верни структурированный результат с приоритетами."""

        return user_message
    
    async def _process_output(self, output: TopicsOutput, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка результата извлечения тем"""
        try:
            # Pydantic модель уже валидирована
            topics_data = output.topics
            
            # Преобразуем в список словарей
            topics_list = [
                {
                    "name": topic.name,
                    "priority": topic.priority
                }
                for topic in topics_data
            ]
            
            result = {
                "topics": topics_list,
                "count": len(topics_list)
            }
            
            logger.info(f"📊 Извлечено {len(topics_list)} тем")
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки тем: {e}")
            return {
                "topics": [],
                "count": 0,
                "error": str(e),
                "fallback": True
            }
    
    def _get_max_topics_for_level(self, detail_level: str) -> int:
        """Определение максимального количества тем для уровня детализации"""
        limits = {
            "micro": 3,
            "brief": 5,
            "standard": 8,
            "detailed": 12,
            "comprehensive": 15
        }
        return limits.get(detail_level, 8)