"""
Context Links Agent

Анализ ссылок, упоминаний и внешних ресурсов в диалогах.
Использует GigaChat для анализа ссылок с Pydantic structured output.

Условный агент: активен при detail_level == comprehensive OR has_links == true
"""

import logging
from typing import Dict, Any, List
import re

from .base import BaseAgent
from .config import get_llm_for_agent
from .schemas import ContextLinksOutput

logger = logging.getLogger(__name__)


class ContextLinksAgent(BaseAgent):
    """Агент для анализа ссылок и внешних ресурсов с Pydantic structured output"""
    
    def __init__(self):
        # Используем GigaChat для анализа ссылок
        llm = get_llm_for_agent("fact_extraction")
        
        system_prompt = """Ты — эксперт по анализу ссылок и внешних ресурсов в диалогах.

ТВОЯ РОЛЬ: Анализировать ссылки, упоминания и внешние ресурсы.
ГРАНИЦЫ: Работаешь только с ссылками и ресурсами, не анализируешь содержание диалога.

КРИТЕРИИ АНАЛИЗА:
- external_links: внешние HTTP/HTTPS ссылки
- telegram_links: ссылки на Telegram каналы/группы
- mentions: упоминания пользователей (@username) и каналов

ПРИМЕРЫ ПРАВИЛЬНОГО ВЫВОДА:
{{
  "external_links": [
    {{
      "url": "https://docs.docker.com/",
      "title": "Docker Documentation",
      "link_type": "external",
      "relevance": "high"
    }}
  ],
  "telegram_links": [
    {{
      "url": "https://t.me/tech_channel",
      "title": "Tech Channel",
      "link_type": "telegram",
      "relevance": "medium"
    }}
  ],
  "mentions": ["@john_doe", "@alice_smith", "#project"]
}}

ВАЖНО:
- Извлекай все ссылки и упоминания из диалога
- Определяй тип ссылки (external, telegram, mention)
- Оценивай релевантность для контекста
- Группируй по типам для удобства
- КРИТИЧНО: Сохраняй реальные usernames участников из сообщений"""

        super().__init__(
            llm=llm,
            system_prompt=system_prompt,
            agent_name="context_links",
            output_model=ContextLinksOutput,
            timeout=30.0
        )
    
    async def _process_input(self, input_data: Dict[str, Any]) -> str:
        """Формирование user message для анализа ссылок"""
        messages_text = input_data.get("messages_text", input_data.get("messages", ""))
        assessment = input_data.get("assessment", None)
        if assessment and hasattr(assessment, 'detail_level'):
            detail_level = assessment.detail_level
        else:
            detail_level = "comprehensive"
            
        if assessment and hasattr(assessment, 'has_links'):
            has_links = assessment.has_links
        else:
            has_links = False
        
        user_message = f"""Проанализируй ссылки и ресурсы в диалоге.

УРОВЕНЬ ДЕТАЛИЗАЦИИ: {detail_level}
НАЛИЧИЕ ССЫЛОК: {has_links}

ДИАЛОГ:
{messages_text}

Извлеки все ссылки, упоминания и внешние ресурсы, сгруппируй по типам."""

        return user_message
    
    async def _process_output(self, output: ContextLinksOutput, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка результата анализа ссылок"""
        try:
            # Pydantic модель уже валидирована
            external_links = [
                {
                    "url": link.url,
                    "title": link.title,
                    "link_type": link.link_type,
                    "relevance": link.relevance
                }
                for link in output.external_links
            ]
            
            telegram_links = [
                {
                    "url": link.url,
                    "title": link.title,
                    "link_type": link.link_type,
                    "relevance": link.relevance
                }
                for link in output.telegram_links
            ]
            
            result = {
                "external_links": external_links,
                "telegram_links": telegram_links,
                "mentions": output.mentions
            }
            
            total_links = len(external_links) + len(telegram_links) + len(output.mentions)
            logger.info(f"🔗 Ссылки: {total_links} всего ({len(external_links)} внешних, {len(telegram_links)} Telegram)")
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа ссылок: {e}")
            return {
                "external_links": [],
                "telegram_links": [],
                "mentions": [],
                "error": str(e),
                "fallback": True
            }