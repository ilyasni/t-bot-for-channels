"""
Speaker Analyzer Agent

Определение ролей, активности и вклада каждого участника в диалог.
Использует GigaChat для анализа участников с Pydantic structured output.

ВАЖНО: Сохраняет реальные usernames, не заменяет на user1, user2!
"""

import logging
from typing import Dict, Any, List
from collections import Counter

from .base import BaseAgent
from .config import get_llm_for_agent
from .schemas import SpeakersOutput

logger = logging.getLogger(__name__)


class SpeakerAnalyzerAgent(BaseAgent):
    """Агент для анализа ролей участников диалогов с Pydantic structured output"""
    
    def __init__(self):
        # Используем GigaChat для анализа ролей (творческий подход)
        llm = get_llm_for_agent("emotion_analysis")
        
        system_prompt = """Ты — эксперт по анализу ролей участников в диалогах.

ТВОЯ РОЛЬ: Анализировать роли и вклад каждого участника.
ГРАНИЦЫ: Работаешь только с участниками, не анализируешь темы или эмоции.

КРИТИЧНО: Сохраняй реальные usernames участников из сообщений!
НЕ заменяй на user1, user2, unknown или другие синтетические имена.

КРИТЕРИИ АНАЛИЗА:
- role: роль участника в диалоге
- activity_level: уровень активности
- contribution_types: типы вклада
- key_contributions: ключевые вклады

ПРИМЕРЫ ПРАВИЛЬНОГО ВЫВОДА:
{{
  "speakers": [
    {{
      "username": "boyversus",
      "role": "инициатор",
      "activity_level": "high",
      "message_count": 15,
      "contribution_types": ["suggestion", "decision"],
      "key_contributions": ["Предложил использовать Docker", "Принял решение о архитектуре"],
      "detailed_role": "инициатор, общий контекст обсуждения"
    }},
    {{
      "username": "KseniaKrasnobaeva",
      "role": "эксперт",
      "activity_level": "medium",
      "message_count": 8,
      "contribution_types": ["answer", "support"],
      "key_contributions": ["Дала экспертное мнение", "Поддержала предложение"],
      "detailed_role": "эксперт, общий контекст обсуждения, поддержала инициативу"
    }}
  ],
  "group_dynamics": {{
    "dominant_speaker": "boyversus",
    "most_helpful": "KseniaKrasnobaeva",
    "most_questions": "boyversus",
    "collaboration_level": "high"
  }}
}}

ОПРЕДЕЛЕНИЯ РОЛЕЙ:
- leader: ведет обсуждение, принимает решения
- supporter: поддерживает идеи, помогает другим
- questioner: задает вопросы, уточняет детали
- contributor: вносит идеи и предложения
- observer: минимально участвует, наблюдает

ВАЖНО:
- Используй только реальные usernames из сообщений
- Анализируй активность и вклад каждого участника
- Определяй динамику группы и взаимодействия
- Сохраняй конкретные примеры вкладов"""

        super().__init__(
            llm=llm,
            system_prompt=system_prompt,
            agent_name="speaker_analyzer",
            output_model=SpeakersOutput,
            timeout=30.0
        )
    
    async def _process_input(self, input_data: Dict[str, Any]) -> str:
        """Формирование user message для анализа участников"""
        # Поддержка как messages_text, так и messages
        messages_text = input_data.get("messages_text", input_data.get("messages", ""))
        assessment = input_data.get("assessment", None)
        if assessment and hasattr(assessment, 'detail_level'):
            detail_level = assessment.detail_level
        else:
            detail_level = "standard"
        
        # Извлечение реальных usernames для контекста
        usernames = self._extract_real_usernames(messages_text)
        usernames_context = ", ".join(usernames) if usernames else "не определены"
        
        user_message = f"""Проанализируй роли участников в диалоге.

УРОВЕНЬ ДЕТАЛИЗАЦИИ: {detail_level}
УЧАСТНИКИ: {usernames_context}

ДИАЛОГ:
{messages_text}

Определи роли, активность и вклад каждого участника. КРИТИЧНО: используй только реальные usernames из сообщений!"""

        return user_message
    
    async def _process_output(self, output: SpeakersOutput, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка результата анализа участников"""
        try:
            # Pydantic модель уже валидирована
            speakers_list = []
            for speaker in output.speakers:
                speakers_list.append({
                    "username": speaker.username,
                    "role": speaker.role,
                    "activity_level": speaker.activity_level,
                    "message_count": speaker.message_count,
                    "contribution_types": speaker.contribution_types,
                    "key_contributions": speaker.key_contributions
                })
            
            result = {
                "speakers": speakers_list,
                "group_dynamics": {
                    "dominant_speaker": output.group_dynamics.dominant_speaker,
                    "most_helpful": output.group_dynamics.most_helpful,
                    "most_questions": output.group_dynamics.most_questions,
                    "collaboration_level": output.group_dynamics.collaboration_level
                },
                "participants_count": len(speakers_list)
            }
            
            logger.info(f"👥 Анализ участников: {len(speakers_list)} человек")
            logger.debug(f"   Usernames: {[s['username'] for s in speakers_list]}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа участников: {e}")
            return {
                "speakers": [],
                "group_dynamics": {
                    "dominant_speaker": "",
                    "most_helpful": "",
                    "most_questions": "",
                    "collaboration_level": "low"
                },
                "participants_count": 0,
                "error": str(e),
                "fallback": True
            }
    
    def _extract_real_usernames(self, messages_text: str) -> List[str]:
        """
        Извлечение реальных usernames из форматированного текста сообщений
        
        Args:
            messages_text: Текст в формате "[ID] username (timestamp): message"
            
        Returns:
            Список уникальных usernames
        """
        usernames = set()
        lines = messages_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Парсинг формата "[ID] username (timestamp): message"
            if ']: ' in line:
                try:
                    # Извлекаем часть после первого ']' и до '('
                    after_bracket = line.split(']', 1)[1]
                    if '(' in after_bracket:
                        username_part = after_bracket.split('(', 1)[0].strip()
                        if username_part:
                            usernames.add(username_part)
                except (IndexError, ValueError):
                    continue
        
        return list(usernames)