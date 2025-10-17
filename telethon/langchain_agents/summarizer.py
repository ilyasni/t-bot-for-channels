"""
Context Summarizer Agent

Создание резюме диалога, адаптированного под уровень детализации и контекст.
Использует GigaChat для адаптивного резюмирования с Pydantic structured output.
"""

import logging
from typing import Dict, Any, List

from .base import BaseAgent
from .config import get_llm_for_agent
from .schemas import SummarizerOutput

logger = logging.getLogger(__name__)


class ContextSummarizerAgent(BaseAgent):
    """Агент для адаптивного резюмирования диалогов с Pydantic structured output"""
    
    def __init__(self):
        # Используем GigaChat для создания резюме (творческий подход)
        llm = get_llm_for_agent("emotion_analysis")
        
        system_prompt = """Ты — эксперт по созданию адаптивных резюме диалогов.

ТВОЯ РОЛЬ: Создавать резюме, адаптированное под специфику диалога.
ГРАНИЦЫ: Работаешь только с резюмированием, не анализируешь отдельные темы или эмоции.

АДАПТАЦИЯ ПОД КОНТЕКСТ:
- Уровень детализации (micro, brief, standard, detailed, comprehensive)
- Тип диалога (discussion, question_answer, announcement, mixed)
- Эмоциональный контекст и атмосферу
- Роли участников и их вклад

СТРУКТУРА РЕЗЮМЕ:
- main_points: основные пункты обсуждения
- key_decisions: ключевые решения и выводы
- outstanding_issues: нерешенные вопросы
- next_steps: следующие шаги и действия
- summary_text: краткое текстовое резюме

ПРИМЕРЫ ПРАВИЛЬНОГО ВЫВОДА:
{{
  "summary": {{
    "main_points": ["Обсуждение Docker конфигурации", "Вопросы безопасности API"],
    "key_decisions": ["Принято решение использовать Docker Compose", "Утвержден план тестирования"],
    "outstanding_issues": ["Не определена стратегия мониторинга"],
    "next_steps": ["Настроить CI/CD pipeline", "Провести code review"],
    "summary_text": "Команда обсудила архитектуру проекта..."
  }},
  "context_adaptation": {{
    "detail_level": "standard",
    "dialogue_type": "discussion",
    "focus_areas": ["архитектура", "безопасность"],
    "summary_style": "balanced"
  }}
}}

ВАЖНО:
- Адаптируй детализацию под требуемый уровень
- Сохраняй ключевую информацию и решения
- Выделяй нерешенные вопросы
- КРИТИЧНО: Сохраняй реальные usernames участников из сообщений"""

        super().__init__(
            llm=llm,
            system_prompt=system_prompt,
            agent_name="context_summarizer",
            output_model=SummarizerOutput,
            timeout=30.0
        )
    
    async def _process_input(self, input_data: Dict[str, Any]) -> str:
        """Формирование user message для создания резюме"""
        messages_text = input_data.get("messages_text", input_data.get("messages", ""))
        assessment = input_data.get("assessment", None)
        if assessment and hasattr(assessment, 'detail_level'):
            detail_level = assessment.detail_level
        else:
            detail_level = "standard"
            
        if assessment and hasattr(assessment, 'dialogue_type'):
            dialogue_type = assessment.dialogue_type
        else:
            dialogue_type = "mixed"
        
        # Получение результатов других агентов для контекста
        topics_obj = input_data.get("topics", None)
        emotions_obj = input_data.get("emotions", None)
        speakers_obj = input_data.get("speakers", None)
        
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
                topics_text = ", ".join([t.name for t in topics[:5]])
            else:
                topics_text = ", ".join([t.get("name", "") for t in topics[:5]])
            context_parts.append(f"Основные темы: {topics_text}")
        
        if emotions.get("overall_tone"):
            context_parts.append(f"Эмоциональный тон: {emotions['overall_tone']}")
        
        if speakers:
            if hasattr(speakers[0], 'username'):
                speakers_text = ", ".join([s.username for s in speakers[:3]])
            else:
                speakers_text = ", ".join([s.get("username", "") for s in speakers[:3]])
            context_parts.append(f"Ключевые участники: {speakers_text}")
        
        # Добавляем базовый контекст даже если нет данных от других агентов
        if not context_parts:
            context_parts.append("Диалог содержит обсуждение различных тем")
        
        context = "\n".join(context_parts)
        
        user_message = f"""Создай адаптивное резюме диалога.

УРОВЕНЬ ДЕТАЛИЗАЦИИ: {detail_level}
ТИП ДИАЛОГА: {dialogue_type}

КОНТЕКСТ:
{context}

ДИАЛОГ:
{messages_text}

Создай структурированное резюме, адаптированное под указанный уровень детализации и тип диалога."""

        return user_message
    
    async def _process_output(self, output: SummarizerOutput, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка результата создания резюме"""
        try:
            # Pydantic модель уже валидирована
            result = {
                "summary": {
                    "main_points": output.summary.main_points,
                    "key_decisions": output.summary.key_decisions,
                    "outstanding_issues": output.summary.outstanding_issues,
                    "next_steps": output.summary.next_steps,
                    "summary_text": output.summary.summary_text
                },
                "context_adaptation": {
                    "detail_level": output.context_adaptation.detail_level,
                    "dialogue_type": output.context_adaptation.dialogue_type,
                    "focus_areas": output.context_adaptation.focus_areas,
                    "summary_style": output.context_adaptation.summary_style
                }
            }
            
            logger.info(f"📝 Резюме создано: {len(output.summary.main_points)} основных пунктов")
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания резюме: {e}")
            return {
                "summary": {
                    "main_points": [],
                    "key_decisions": [],
                    "outstanding_issues": [],
                    "next_steps": [],
                    "summary_text": "Ошибка создания резюме"
                },
                "context_adaptation": {
                    "detail_level": "standard",
                    "dialogue_type": "mixed",
                    "focus_areas": [],
                    "summary_style": "concise"
                },
                "error": str(e),
                "fallback": True
            }