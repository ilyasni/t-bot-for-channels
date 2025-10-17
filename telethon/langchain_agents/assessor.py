"""
Dialogue Assessor Agent - интеллектуальная оценка диалога через LLM

LLM-based агент для глубокого анализа диалога и определения оптимальных параметров
для последующей обработки другими агентами.
"""

import logging
from typing import Dict, Any
from .base import BaseAgent
from .schemas import AssessmentOutput
from .config import config

logger = logging.getLogger(__name__)


class DialogueAssessorAgent(BaseAgent):
    """
    LLM-based агент для оценки диалога
    
    Определяет:
    - detail_level: уровень детализации анализа
    - dialogue_type: тип диалога
    - has_links: наличие ссылок
    - has_decisions: наличие решений
    - has_questions: наличие вопросов
    - has_conflicts: наличие конфликтов
    - complexity_score: оценка сложности 0.0-1.0
    - urgency_level: уровень срочности
    - participants_count: количество участников
    - dominant_topics: доминирующие темы
    - context_notes: дополнительные заметки
    """
    
    def __init__(self):
        system_prompt = """Ты - эксперт по анализу диалогов. Твоя задача - быстро и точно оценить диалог и определить оптимальные параметры для его обработки.

АНАЛИЗИРУЙ ДИАЛОГ И ОПРЕДЕЛИ:

1. **Уровень детализации (detail_level):**
   - micro: ≤5 сообщений, простой обмен информацией
   - brief: 6-15 сообщений, краткое обсуждение
   - standard: 16-30 сообщений, обычное обсуждение
   - detailed: 31-50 сообщений, детальное обсуждение
   - comprehensive: >50 сообщений, комплексный диалог

2. **Тип диалога (dialogue_type):**
   - discussion: обсуждение тем, обмен мнениями
   - question_answer: вопросы и ответы
   - announcement: объявления, уведомления
   - brainstorming: мозговой штурм, генерация идей
   - planning: планирование, организация
   - support: поддержка, помощь
   - mixed: смешанный тип

3. **Характеристики диалога:**
   - has_links: есть ли ссылки (http, www, .com, .ru, t.me/, @)
   - has_decisions: принимались ли решения
   - has_questions: есть ли вопросы требующие ответа
   - has_conflicts: есть ли конфликты или разногласия

4. **Оценки:**
   - complexity_score: сложность диалога 0.0-1.0 (0=простой, 1=очень сложный)
   - urgency_level: срочность (low/medium/high/critical)

5. **Контекст:**
   - participants_count: количество уникальных участников
   - dominant_topics: 3-5 ключевых тем диалога
   - context_notes: краткие заметки о специфике диалога

ФОРМАТ ОТВЕТА:
```json
{{
  "detail_level": "standard",
  "dialogue_type": "discussion",
  "has_links": false,
  "has_decisions": true,
  "has_questions": true,
  "has_conflicts": false,
  "complexity_score": 0.6,
  "urgency_level": "medium",
  "message_count": 25,
  "participants_count": 5,
  "dominant_topics": ["проект", "дедлайн", "команда"],
  "context_notes": "Обсуждение проекта с дедлайном, есть вопросы по команде"
}}
```

ВАЖНО: Будь точным и объективным в оценке. Учитывай контекст и специфику диалога."""

        super().__init__(
            llm=config.get_llm("gpt2giga"),
            system_prompt=system_prompt,
            agent_name="dialogue_assessor",
            output_model=AssessmentOutput,
            timeout=config.agent_timeouts["dialogue_assessor"]
        )
        logger.info("🤖 Инициализирован LLM агент: dialogue_assessor")
    
    async def _process_input(self, input_data: Dict[str, Any]) -> str:
        """Формирование user message для анализа диалога"""
        messages_text = input_data.get("messages", "")
        hours = input_data.get("hours", 24)
        
        user_message = f"""Проанализируй диалог и определи оптимальные параметры для его обработки.

ПЕРИОД: {hours} часов
ДИАЛОГ:
{messages_text}

Проведи комплексный анализ и верни результат в указанном JSON формате."""
        
        return user_message
    
    async def _process_output(self, result: AssessmentOutput, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка результата анализа"""
        logger.info(f"📊 Оценка диалога: {result.detail_level} детализация, {result.dialogue_type} тип")
        logger.info(f"   Участников: {result.participants_count}, Сообщений: {result.message_count}")
        logger.info(f"   Сложность: {result.complexity_score:.1f}, Срочность: {result.urgency_level}")
        logger.info(f"   Решения: {result.has_decisions}, Вопросы: {result.has_questions}, Конфликты: {result.has_conflicts}")
        
        return {
            "detail_level": result.detail_level,
            "dialogue_type": result.dialogue_type,
            "has_links": result.has_links,
            "has_decisions": result.has_decisions,
            "has_questions": result.has_questions,
            "has_conflicts": result.has_conflicts,
            "complexity_score": result.complexity_score,
            "urgency_level": result.urgency_level,
            "message_count": result.message_count,
            "participants_count": result.participants_count,
            "dominant_topics": result.dominant_topics,
            "context_notes": result.context_notes
        }