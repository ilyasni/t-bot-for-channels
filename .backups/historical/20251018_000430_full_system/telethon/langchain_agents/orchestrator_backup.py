"""
Digest Orchestrator - управление последовательностью агентов

Центральный компонент для управления 9-агентной sequential pipeline.
Использует LCEL для параллельного и последовательного выполнения агентов.

Архитектура:
1. Dialogue Assessor (эвристики) → detail_level, dialogue_type
2. Topic Extractor (GigaChat) → topics с приоритетами
3. Emotion Analyzer (GigaChat-Pro) → overall_tone, atmosphere
4. Speaker Analyzer (GigaChat-Pro) → роли участников
5. Context Summarizer (GigaChat-Pro) → адаптивное резюме
6. Key Moments (GigaChat-Pro, conditional) → решения, вопросы
7. Timeline Builder (GigaChat-Pro, conditional) → хронология
8. Context Links (GigaChat, conditional) → анализ ссылок
9. Supervisor Synthesizer (GigaChat-Pro) → финальный HTML дайджест
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from langchain_core.runnables import RunnableParallel, RunnableSequence

from .assessor import DialogueAssessorAgent
from .topic_extractor import TopicExtractorAgent
from .emotion_analyzer import EmotionAnalyzerAgent
from .speaker_analyzer import SpeakerAnalyzerAgent
from .summarizer import ContextSummarizerAgent
from .key_moments import KeyMomentsAgent
from .timeline import TimelineBuilderAgent
from .context_links import ContextLinksAgent
from .supervisor import SupervisorSynthesizerAgent
from .config import config
from .schemas import AgentStatus
from .observability import log_orchestrator_metrics


logger = logging.getLogger(__name__)


class DigestOrchestrator:
    """
    Оркестратор для управления последовательностью агентов дайджеста
    
    Управляет:
    - Sequential execution основной pipeline
    - Parallel execution где возможно (Topics + Emotions)
    - Conditional execution агентов 6-8
    - Error handling и fallback
    - Performance monitoring
    """
    
    def __init__(self):
        logger.info("🚀 Инициализация Digest Orchestrator")
        
        # Инициализация всех агентов
        self.assessor = DialogueAssessorAgent()
        self.topic_extractor = TopicExtractorAgent()
        self.emotion_analyzer = EmotionAnalyzerAgent()
        self.speaker_analyzer = SpeakerAnalyzerAgent()
        self.summarizer = ContextSummarizerAgent()
        self.key_moments = KeyMomentsAgent()
        self.timeline = TimelineBuilderAgent()
        self.context_links = ContextLinksAgent()
        self.supervisor = SupervisorSynthesizerAgent()
        
        # Мониторинг статуса агентов
        self.agents_status: List[AgentStatus] = []
        
        logger.info("✅ Все агенты инициализированы")
    
    def _record_agent_status(self, agent_name: str, status: str, execution_time: float, 
                           error_message: Optional[str] = None, output_summary: Optional[str] = None):
        """Записать статус выполнения агента"""
        agent_status = AgentStatus(
            agent_name=agent_name,
            status=status,
            execution_time=execution_time,
            error_message=error_message,
            output_summary=output_summary
        )
        self.agents_status.append(agent_status)
        
        # Логирование статуса
        if status == "success":
            logger.info(f"✅ {agent_name}: {output_summary} ({execution_time:.2f}s)")
        elif status == "error":
            logger.error(f"❌ {agent_name}: {error_message} ({execution_time:.2f}s)")
        elif status == "fallback":
            logger.warning(f"🔄 {agent_name}: fallback used - {error_message} ({execution_time:.2f}s)")
    
    async def generate_digest(
        self, 
        messages: List[Any], 
        hours: int = 24,
        user_id: Optional[int] = None,
        group_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Генерация дайджеста через полную 9-агентную pipeline
        
        Args:
            messages: Список сообщений Telegram
            hours: Количество часов для анализа
            user_id: ID пользователя (для логирования)
            group_id: ID группы (для логирования)
            
        Returns:
            Dict с финальным дайджестом и метаданными
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            logger.info(f"🎯 Начало генерации дайджеста для группы {group_id}")
            logger.info(f"   Сообщений: {len(messages)}")
            logger.info(f"   Часов: {hours}")
            logger.info(f"   Пользователь: {user_id}")
            
            # Подготовка данных
            messages_text = self._format_messages_for_analysis(messages)
            input_data = {
                "messages": messages,
                "messages_text": messages_text,
                "hours": hours,
                "user_id": user_id,
                "group_id": group_id
            }
            
            # Phase 1: Dialogue Assessor (быстрые эвристики)
            logger.info("📊 Phase 1: Dialogue Assessor")
            assessment = await self.assessor.ainvoke(input_data)
            input_data["assessment"] = assessment
            
            logger.info(f"   Уровень детализации: {assessment.get('detail_level')}")
            logger.info(f"   Тип диалога: {assessment.get('dialogue_type')}")
            
            # Phase 2-3: Topics + Emotions (PARALLEL execution)
            logger.info("🔄 Phase 2-3: Topics + Emotions (Parallel)")
            
            # Параллельное выполнение Topics и Emotions
            topics_task = asyncio.create_task(self.topic_extractor.ainvoke(input_data))
            emotions_task = asyncio.create_task(self.emotion_analyzer.ainvoke(input_data))
            
            topics_result, emotions_result = await asyncio.gather(topics_task, emotions_task)
            
            step1_results = {
                "topics": topics_result,
                "emotions": emotions_result
            }
            input_data.update(step1_results)
            
            logger.info(f"   Извлечено тем: {len(step1_results.get('topics', {}).get('topics', []))}")
            logger.info(f"   Тон: {step1_results.get('emotions', {}).get('overall_tone')}")
            
            # Phase 4: Speaker Analyzer (sequential, нужны topics + emotions)
            logger.info("👥 Phase 4: Speaker Analyzer")
            speakers = await self.speaker_analyzer.ainvoke(input_data)
            input_data["speakers"] = speakers
            
            logger.info(f"   Участников проанализировано: {len(speakers.get('speakers', []))}")
            
            # Phase 5: Context Summarizer (sequential, нужны все предыдущие)
            logger.info("📝 Phase 5: Context Summarizer")
            summary = await self.summarizer.ainvoke(input_data)
            input_data["summary"] = summary
            
            logger.info(f"   Основных пунктов: {len(summary.get('summary', {}).get('main_points', []))}")
            
            # Phase 6-8: Conditional agents
            conditional_results = await self._execute_conditional_agents(input_data, assessment)
            input_data.update(conditional_results)
            
            # Phase 9: Supervisor Synthesizer (финальный синтез)
            logger.info("🎭 Phase 9: Supervisor Synthesizer")
            final_digest = await self.supervisor.ainvoke(input_data)
            
            # Подготовка финального результата
            result = self._prepare_final_result(final_digest, input_data, start_time)
            
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            logger.info(f"✅ Дайджест сгенерирован за {duration:.2f}s")
            logger.info(f"   Финальный размер: {len(result.get('html_digest', ''))} символов")
            
            # Логирование метрик оркестратора в Langfuse
            log_orchestrator_metrics(
                start_time=start_time,
                end_time=end_time,
                success=True,
                user_id=user_id,
                group_id=group_id,
                result=result
            )
            
            return result
            
        except Exception as e:
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            logger.error(f"❌ Ошибка генерации дайджеста за {duration:.2f}s: {e}")
            
            # Логирование ошибки оркестратора в Langfuse
            log_orchestrator_metrics(
                start_time=start_time,
                end_time=end_time,
                success=False,
                user_id=user_id,
                group_id=group_id,
                error=e
            )
            
            # Возврат fallback результата
            return await self._handle_generation_error(e, input_data, start_time)
    
    async def _execute_conditional_agents(self, input_data: Dict[str, Any], assessment: Dict[str, Any]) -> Dict[str, Any]:
        """
        Выполнение условных агентов 6-8
        
        Args:
            input_data: Данные для агентов
            assessment: Результат Dialogue Assessor
            
        Returns:
            Dict с результатами условных агентов
        """
        detail_level = assessment.get("detail_level", "standard")
        has_links = assessment.get("has_links", False)
        
        results = {}
        
        # Phase 6: Key Moments (активен при detail_level >= standard)
        if detail_level in ["standard", "detailed", "comprehensive"]:
            logger.info("🔑 Phase 6: Key Moments")
            try:
                key_moments = await self.key_moments.ainvoke(input_data)
                results["key_moments"] = key_moments
                
                decisions_count = len(key_moments.get("key_decisions", []))
                questions_count = len(key_moments.get("critical_questions", []))
                logger.info(f"   Решений: {decisions_count}, Вопросов: {questions_count}")
                
            except Exception as e:
                logger.warning(f"⚠️ Ошибка Key Moments: {e}")
                results["key_moments"] = {"error": str(e)}
        else:
            logger.info("⏭️ Phase 6: Key Moments (пропущен - уровень детализации слишком низкий)")
            results["key_moments"] = {"skipped": True}
        
        # Phase 7: Timeline Builder (активен при detail_level >= detailed)
        if detail_level in ["detailed", "comprehensive"]:
            logger.info("⏰ Phase 7: Timeline Builder")
            try:
                timeline = await self.timeline.ainvoke(input_data)
                results["timeline"] = timeline
                
                events_count = len(timeline.get("timeline_events", []))
                phases_count = len(timeline.get("discussion_phases", []))
                logger.info(f"   Событий: {events_count}, Фаз: {phases_count}")
                
            except Exception as e:
                logger.warning(f"⚠️ Ошибка Timeline Builder: {e}")
                results["timeline"] = {"error": str(e)}
        else:
            logger.info("⏭️ Phase 7: Timeline Builder (пропущен - уровень детализации слишком низкий)")
            results["timeline"] = {"skipped": True}
        
        # Phase 8: Context Links (активен при comprehensive OR has_links)
        if detail_level == "comprehensive" or has_links:
            logger.info("🔗 Phase 8: Context Links")
            try:
                context_links = await self.context_links.ainvoke(input_data)
                results["context_links"] = context_links
                
                external_links = len(context_links.get("external_links", []))
                telegram_links = len(context_links.get("telegram_links", []))
                logger.info(f"   Внешних ссылок: {external_links}, Telegram ссылок: {telegram_links}")
                
            except Exception as e:
                logger.warning(f"⚠️ Ошибка Context Links: {e}")
                results["context_links"] = {"error": str(e)}
        else:
            logger.info("⏭️ Phase 8: Context Links (пропущен - нет ссылок и уровень не comprehensive)")
            results["context_links"] = {"skipped": True}
        
        return results
    
    def _format_messages_for_analysis(self, messages: List[Any]) -> str:
        """
        Форматирование сообщений для анализа агентами
        
        Args:
            messages: Список сообщений Telegram
            
        Returns:
            Отформатированный текст диалога
        """
        formatted_lines = []
        
        for i, msg in enumerate(messages, 1):
            # Извлечение данных сообщения - ИСПРАВЛЕНО
            if hasattr(msg, 'text') and msg.text:
                text = msg.text.strip()
            else:
                text = "[сообщение без текста]"
            
            # Извлечение username - ИСПРАВЛЕНО
            username = "unknown"
            if hasattr(msg, 'sender') and msg.sender:
                if hasattr(msg.sender, 'username') and msg.sender.username:
                    username = msg.sender.username
                elif hasattr(msg.sender, 'first_name') and msg.sender.first_name:
                    username = msg.sender.first_name
                elif hasattr(msg.sender, 'id'):
                    username = f"user_{msg.sender.id}"
            
            # Извлечение времени (опционально)
            timestamp = ""
            if hasattr(msg, 'date') and msg.date:
                timestamp = msg.date.strftime("%H:%M")
            
            # Формирование строки
            if timestamp:
                line = f"[{i}] {username} ({timestamp}): {text}"
            else:
                line = f"[{i}] {username}: {text}"
            
            formatted_lines.append(line)
        
        logger.debug(f"Отформатировано {len(formatted_lines)} сообщений")
        return "\n".join(formatted_lines)
    
    def _format_messages_to_langchain(self, messages: List[Any]) -> List[Any]:
        """
        Форматирование Telethon messages в LangChain Messages
        
        Args:
            messages: Список Telethon Message objects
            
        Returns:
            Список LangChain BaseMessage objects
        """
        from langchain_core.messages import HumanMessage
        
        langchain_messages = []
        
        for msg in messages:
            # Извлечение username
            username = "Unknown"
            if hasattr(msg, 'sender') and msg.sender:
                if hasattr(msg.sender, 'username') and msg.sender.username:
                    username = msg.sender.username
                elif hasattr(msg.sender, 'first_name') and msg.sender.first_name:
                    username = msg.sender.first_name
            
            # Извлечение текста
            text = msg.text if hasattr(msg, 'text') and msg.text else "[no text]"
            
            # Извлечение timestamp
            timestamp = msg.date.isoformat() if hasattr(msg, 'date') else None
            
            # Создание LangChain message
            langchain_msg = HumanMessage(
                content=text,
                additional_kwargs={
                    "username": username,
                    "timestamp": timestamp,
                    "message_id": msg.id if hasattr(msg, 'id') else None
                }
            )
            langchain_messages.append(langchain_msg)
        
        logger.info(f"Converted {len(langchain_messages)} messages to LangChain format")
        logger.debug(f"Usernames: {set(m.additional_kwargs['username'] for m in langchain_messages)}")
        
        return langchain_messages
    
    def _prepare_final_result(
        self, 
        final_digest: Dict[str, Any], 
        input_data: Dict[str, Any], 
        start_time: datetime
    ) -> Dict[str, Any]:
        """
        Подготовка финального результата с метаданными
        
        Args:
            final_digest: Результат Supervisor Synthesizer
            input_data: Исходные данные
            start_time: Время начала генерации
            
        Returns:
            Финальный результат с метаданными
        """
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        assessment = input_data.get("assessment", {})
        
        return {
            # Основной результат
            "html_digest": final_digest.get("html_digest", ""),
            "metadata": final_digest.get("metadata", {}),
            "sections": final_digest.get("sections", {}),
            
            # Технические метаданные
            "generation_metadata": {
                "duration_seconds": duration,
                "start_time": start_time.isoformat(),
                "end_time": datetime.now(timezone.utc).isoformat(),
                "user_id": input_data.get("user_id"),
                "group_id": input_data.get("group_id"),
                "message_count": len(input_data.get("messages", [])),
                "hours_analyzed": input_data.get("hours", 24)
            },
            
            # Результаты всех агентов (для отладки)
            "agent_results": {
                "assessment": input_data.get("assessment", {}),
                "topics": input_data.get("topics", {}),
                "emotions": input_data.get("emotions", {}),
                "speakers": input_data.get("speakers", {}),
                "summary": input_data.get("summary", {}),
                "key_moments": input_data.get("key_moments", {}),
                "timeline": input_data.get("timeline", {}),
                "context_links": input_data.get("context_links", {})
            },
            
            # Статистика агентов
            "agent_statistics": {
                "agents_executed": self._count_executed_agents(input_data),
                "detail_level": assessment.get("detail_level", "standard"),
                "dialogue_type": assessment.get("dialogue_type", "mixed"),
                "participants": assessment.get("participants", 0),
                "has_links": assessment.get("has_links", False)
            }
        }
    
    def _count_executed_agents(self, input_data: Dict[str, Any]) -> int:
        """Подсчет количества выполненных агентов"""
        count = 5  # Базовые агенты всегда выполняются
        
        # Проверка условных агентов
        if input_data.get("key_moments", {}).get("skipped") is not True:
            count += 1
        
        if input_data.get("timeline", {}).get("skipped") is not True:
            count += 1
        
        if input_data.get("context_links", {}).get("skipped") is not True:
            count += 1
        
        count += 1  # Supervisor всегда выполняется
        
        return count
    
    async def _handle_generation_error(
        self, 
        error: Exception, 
        input_data: Dict[str, Any], 
        start_time: datetime
    ) -> Dict[str, Any]:
        """
        Обработка ошибок генерации с fallback результатом
        
        Args:
            error: Исключение
            input_data: Исходные данные
            start_time: Время начала
            
        Returns:
            Fallback результат
        """
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        assessment = input_data.get("assessment", {})
        
        # Простой fallback дайджест
        fallback_html = f"""<b>Дайджест диалога</b>

<i>Статус:</i> <i>Ошибка генерации</i>

<b>Основная информация:</b>
- Сообщений: {len(input_data.get('messages', []))}
- Уровень детализации: {assessment.get('detail_level', 'standard')}
- Тип диалога: {assessment.get('dialogue_type', 'mixed')}

<b>Ошибка:</b>
<code>{str(error)}</code>

<i>Попробуйте повторить запрос позже</i>"""
        
        return {
            "html_digest": fallback_html,
            "metadata": {
                "detail_level": assessment.get("detail_level", "standard"),
                "dialogue_type": assessment.get("dialogue_type", "mixed"),
                "participants_count": assessment.get("participants", 0),
                "message_count": len(input_data.get("messages", [])),
                "generation_timestamp": datetime.now(timezone.utc).isoformat()
            },
            "sections": {
                "summary": "Ошибка генерации дайджеста",
                "topics": "",
                "decisions": "",
                "participants": "",
                "resources": ""
            },
            "generation_metadata": {
                "duration_seconds": duration,
                "start_time": start_time.isoformat(),
                "end_time": datetime.now(timezone.utc).isoformat(),
                "user_id": input_data.get("user_id"),
                "group_id": input_data.get("group_id"),
                "message_count": len(input_data.get("messages", [])),
                "hours_analyzed": input_data.get("hours", 24),
                "error": str(error)
            },
            "agent_results": {},
            "agent_statistics": {
                "agents_executed": 0,
                "detail_level": assessment.get("detail_level", "standard"),
                "dialogue_type": assessment.get("dialogue_type", "mixed"),
                "participants": assessment.get("participants", 0),
                "has_links": assessment.get("has_links", False),
                "error": True
            }
        }
