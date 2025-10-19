"""
Emotion Analyzer Agent

Определение общего тона, атмосферы и эмоциональных паттернов в диалогах.
Использует GigaChat для анализа эмоций с Pydantic structured output.
"""

import logging
from typing import Dict, Any, List

from .base import BaseAgent
from .config import get_llm_for_agent
from .schemas import EmotionsOutput

logger = logging.getLogger(__name__)


class EmotionAnalyzerAgent(BaseAgent):
    """Агент для анализа эмоциональной атмосферы диалогов с Pydantic structured output"""
    
    def __init__(self):
        # Используем GigaChat для анализа эмоций (более творческий подход)
        llm = get_llm_for_agent("emotion_analysis")
        
        system_prompt = """Ты — эксперт по анализу эмоциональной атмосферы в диалогах.

ТВОЯ РОЛЬ: Анализировать эмоциональный тон и атмосферу общения.
ГРАНИЦЫ: Работаешь только с эмоциями, не анализируешь темы или участников.

КРИТЕРИИ АНАЛИЗА:
- overall_tone: общий эмоциональный тон диалога
- atmosphere: атмосфера взаимодействия участников
- emotional_indicators: конкретные эмоциональные маркеры
- intensity_level: уровень эмоциональной интенсивности

ПРИМЕРЫ ПРАВИЛЬНОГО ВЫВОДА:
{{
  "overall_tone": "neutral",
  "atmosphere": "casual",
  "emotional_indicators": ["беспокойство", "конструктивность", "нейтральность"],
  "intensity_level": "medium",
  "intensity_score": 0.6,
  "key_emotions": ["беспокойство", "конструктивность"],
  "conflict_indicators": false,
  "support_indicators": true,
  "conflict_percentage": 20.0,
  "collaboration_percentage": 80.0,
  "stress_percentage": 40.0,
  "enthusiasm_percentage": 60.0
}}

ОПРЕДЕЛЕНИЯ:
- positive: преобладают позитивные эмоции, поддержка, одобрение
- neutral: нейтральный тон, деловое общение
- negative: преобладают негативные эмоции, критика, недовольство
- mixed: сочетание позитивных и негативных эмоций

ВАЖНО:
- Анализируй эмоциональную составляющую сообщений
- Учитывай контекст и тон общения
- Определяй признаки конфликтов и поддержки
- КРИТИЧНО: Сохраняй реальные usernames участников из сообщений"""

        super().__init__(
            llm=llm,
            system_prompt=system_prompt,
            agent_name="emotion_analyzer",
            output_model=EmotionsOutput,
            timeout=30.0
        )
    
    async def _process_input(self, input_data: Dict[str, Any]) -> str:
        """Формирование user message для анализа эмоций"""
        messages_text = input_data.get("messages_text", input_data.get("messages", ""))
        assessment = input_data.get("assessment", None)
        if assessment and hasattr(assessment, 'detail_level'):
            detail_level = assessment.detail_level
        else:
            detail_level = "standard"
        
        user_message = f"""Проанализируй эмоциональную атмосферу диалога.

УРОВЕНЬ ДЕТАЛИЗАЦИИ: {detail_level}

ДИАЛОГ:
{messages_text}

Определи эмоциональный тон, атмосферу и ключевые эмоциональные индикаторы."""

        return user_message
    
    async def _process_output(self, output: EmotionsOutput, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка результата анализа эмоций"""
        try:
            # Pydantic модель уже валидирована
            result = {
                "overall_tone": output.overall_tone,
                "atmosphere": output.atmosphere,
                "emotional_indicators": output.emotional_indicators,
                "intensity_level": output.intensity_level,
                "key_emotions": output.key_emotions,
                "conflict_indicators": output.conflict_indicators,
                "support_indicators": output.support_indicators
            }
            
            logger.info(f"😊 Эмоциональный анализ: {output.overall_tone} тон, {output.atmosphere} атмосфера")
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа эмоций: {e}")
            return {
                "overall_tone": "neutral",
                "atmosphere": "mixed",
                "emotional_indicators": [],
                "intensity_level": "low",
                "key_emotions": [],
                "conflict_indicators": False,
                "support_indicators": False,
                "error": str(e),
                "fallback": True
            }