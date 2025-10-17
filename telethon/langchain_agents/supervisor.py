"""
Supervisor Synthesizer Agent

Создание финального HTML дайджеста на основе всех данных от предыдущих агентов.
Использует GigaChat для синтеза с Pydantic structured output.

КРИТИЧНО: HTML форматирование только <b>, <i>, <code>, <a> тегами!
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timezone

from .base import BaseAgent
from .config import get_llm_for_agent
from .schemas import SupervisorOutput

logger = logging.getLogger(__name__)


class SupervisorSynthesizerAgent(BaseAgent):
    """Агент для финального синтеза дайджеста с Pydantic structured output"""
    
    def __init__(self):
        # Используем GigaChat для финального синтеза
        llm = get_llm_for_agent("synthesis")
        
        system_prompt = """Ты — эксперт по созданию финальных дайджестов диалогов.

ТВОЯ РОЛЬ: Создавать HTML дайджест с указанными полями.
ГРАНИЦЫ: Возвращай ТОЛЬКО JSON с полями html_digest, metadata, sections.

ФОРМАТ ВЫВОДА:
{{
  \"html_digest\": \"HTML текст дайджеста\",
  \"metadata\": {{
    \"detail_level\": \"brief\",
    \"dialogue_type\": \"mixed\",
    \"participants_count\": 3,
    \"message_count\": 8,
    \"generation_timestamp\": \"2025-10-15T18:25:00Z\"
  }},
  \"sections\": {{
    \"summary\": \"краткое резюме\",
    \"topics\": \"основные темы\",
    \"decisions\": \"решения\",
    \"participants\": \"участники\",
    \"resources\": \"ресурсы\"
  }}
}}

HTML ОГРАНИЧЕНИЯ:
- ТОЛЬКО разрешенные теги: <b>, <i>, <code>, <pre>, <a>
- НЕ используй: <br>, <p>, <div>, <span>, <ul>, <li>, <h1>-<h6>
- Используй пробелы и • для разделения элементов

ВАЖНО:
- Возвращай ТОЛЬКО валидный JSON
- Все поля обязательны
- HTML без запрещенных тегов
- Сохраняй реальные usernames участников
- Если агенты завершились с ошибками, упомяни это в дайджесте
- Используй формат как в примере:
  📊 Дайджест: [Группа] | 24 часа | 32 сообщения
  🎯 Основные темы:
  - ❗️ Проблема с вебвью (приоритет high, 15 сообщений)
  - ✨ Обновление приложения (приоритет medium, 7 сообщений)
  😐 Эмоциональный тон: нейтральный, интенсивность 0.6
  Атмосфера: Профессиональное обсуждение с элементами беспокойства
  Индикаторы: conflict 20%, collaboration 80%, stress 40%, enthusiasm 60%
  👥 Активные участники:
  - @boyversus (инициатор, общий контекст обсуждения)
  - @KseniaKrasnobaeva (эксперт, общий контекст обсуждения, поддержала инициативу)
  📝 Резюме: [развернутое описание диалога]"""

        super().__init__(
            llm=llm,
            system_prompt=system_prompt,
            agent_name="supervisor_synthesizer",
            output_model=SupervisorOutput,
            timeout=45.0
        )
    
    async def _process_input(self, input_data: Dict[str, Any]) -> str:
        """Формирование user message для синтеза дайджеста"""
        # Сбор всех результатов от предыдущих агентов
        assessment = input_data.get("assessment", {})
        topics = input_data.get("topics", {})
        emotions = input_data.get("emotions", {})
        speakers = input_data.get("speakers", {})
        summary = input_data.get("summary", {})
        key_moments = input_data.get("key_moments", {})
        timeline = input_data.get("timeline", {})
        context_links = input_data.get("context_links", {})
        
        # Формирование контекста
        context_parts = []
        
        # Assessment
        if assessment:
            if hasattr(assessment, 'detail_level'):
                context_parts.append(f"УРОВЕНЬ ДЕТАЛИЗАЦИИ: {assessment.detail_level}")
            if hasattr(assessment, 'dialogue_type'):
                context_parts.append(f"ТИП ДИАЛОГА: {assessment.dialogue_type}")
            if hasattr(assessment, 'participants_count'):
                context_parts.append(f"УЧАСТНИКОВ: {assessment.participants_count}")
        
        # Topics
        topics_list = []
        if topics:
            if hasattr(topics, 'topics'):
                topics_list = [f"• {t.name} ({t.priority})" for t in topics.topics[:5]]
            elif isinstance(topics, dict) and topics.get("topics"):
                topics_list = [f"• {t.get('name', '')} ({t.get('priority', 'medium')})" for t in topics["topics"][:5]]
        if topics_list:
            context_parts.append(f"ОСНОВНЫЕ ТЕМЫ:\n" + "\n".join(topics_list))
        
        # Emotions
        if emotions:
            if hasattr(emotions, 'overall_tone'):
                context_parts.append(f"ЭМОЦИОНАЛЬНЫЙ ТОН: {emotions.overall_tone}")
                context_parts.append(f"АТМОСФЕРА: {emotions.atmosphere}")
            elif isinstance(emotions, dict):
                context_parts.append(f"ЭМОЦИОНАЛЬНЫЙ ТОН: {emotions.get('overall_tone', 'neutral')}")
                context_parts.append(f"АТМОСФЕРА: {emotions.get('atmosphere', 'mixed')}")
        
        # Speakers
        speakers_list = []
        if speakers:
            if hasattr(speakers, 'speakers'):
                speakers_list = [f"• @{s.username} - {s.role} ({s.message_count} сообщений)" for s in speakers.speakers[:5]]
            elif isinstance(speakers, dict) and speakers.get("speakers"):
                speakers_list = [f"• @{s.get('username', '')} - {s.get('role', 'unknown')} ({s.get('message_count', 0)} сообщений)" for s in speakers["speakers"][:5]]
        if speakers_list:
            context_parts.append(f"УЧАСТНИКИ:\n" + "\n".join(speakers_list))
        
        # Summary
        summary_text = ""
        if summary:
            if hasattr(summary, 'summary') and hasattr(summary.summary, 'summary_text'):
                summary_text = summary.summary.summary_text
            elif isinstance(summary, dict) and summary.get("summary", {}).get("summary_text"):
                summary_text = summary['summary']['summary_text']
        if summary_text:
            context_parts.append(f"РЕЗЮМЕ: {summary_text[:200]}...")
        
        # Key Moments
        decisions_list = []
        if key_moments:
            if hasattr(key_moments, 'key_decisions'):
                decisions_list = [f"• {d}" for d in key_moments.key_decisions[:3]]
            elif isinstance(key_moments, dict) and key_moments.get("key_decisions"):
                decisions_list = [f"• {d}" for d in key_moments["key_decisions"][:3]]
        if decisions_list:
            context_parts.append(f"КЛЮЧЕВЫЕ РЕШЕНИЯ:\n" + "\n".join(decisions_list))
        
        # Context Links
        external_links = []
        telegram_links = []
        if context_links:
            if hasattr(context_links, 'external_links'):
                external_links = context_links.external_links
            elif isinstance(context_links, dict):
                external_links = context_links.get("external_links", [])
            
            if hasattr(context_links, 'telegram_links'):
                telegram_links = context_links.telegram_links
            elif isinstance(context_links, dict):
                telegram_links = context_links.get("telegram_links", [])
        
        if external_links or telegram_links:
            links_count = len(external_links) + len(telegram_links)
            context_parts.append(f"ССЫЛКИ И РЕСУРСЫ: {links_count} ссылок")
        
        context = "\n\n".join(context_parts)
        
        user_message = f"""Создай финальный HTML дайджест диалога.

КОНТЕКСТ АНАЛИЗА:
{context}

Создай структурированный HTML дайджест, используя только разрешенные теги: <b>, <i>, <code>, <pre>, <a>."""

        return user_message
    
    async def _process_output(self, output: SupervisorOutput, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка результата синтеза дайджеста"""
        try:
            # Pydantic модель уже валидирована
            result = {
                "html_digest": output.html_digest,
                "metadata": {
                    "detail_level": output.metadata.detail_level,
                    "dialogue_type": output.metadata.dialogue_type,
                    "participants_count": output.metadata.participants_count,
                    "message_count": output.metadata.message_count,
                    "generation_timestamp": output.metadata.generation_timestamp
                },
                "sections": {
                    "summary": output.sections.summary,
                    "topics": output.sections.topics,
                    "decisions": output.sections.decisions,
                    "participants": output.sections.participants,
                    "resources": output.sections.resources
                }
            }
            
            logger.info(f"📄 Дайджест создан: {len(output.html_digest)} символов HTML")
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка синтеза дайджеста: {e}")
            return {
                "html_digest": "<b>Ошибка создания дайджеста</b>",
                "metadata": {
                    "detail_level": "standard",
                    "dialogue_type": "mixed",
                    "participants_count": 0,
                    "message_count": 0,
                    "generation_timestamp": datetime.now(timezone.utc).isoformat()
                },
                "sections": {
                    "summary": "Ошибка создания резюме",
                    "topics": "",
                    "decisions": "",
                    "participants": "",
                    "resources": ""
                },
                "error": str(e),
                "fallback": True
            }