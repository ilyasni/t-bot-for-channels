"""
Enhanced Digest Orchestrator - управление последовательностью агентов с мониторингом

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
    Оркестратор для управления последовательностью агентов LangChain
    
    Обеспечивает:
    - Sequential и parallel execution агентов
    - Error handling с fallback
    - Мониторинг статуса каждого агента
    - Структурированное логирование
    - Langfuse integration (опционально)
    """
    
    def __init__(self):
        logger.info("🚀 Инициализация Enhanced Digest Orchestrator")
        
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
            # Извлечение данных сообщения
            if hasattr(msg, 'text') and msg.text:
                text = msg.text.strip()
            else:
                text = "[сообщение без текста]"

            # Извлечение username
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

    async def _execute_agent_with_monitoring(self, agent, agent_name: str, input_data: Dict[str, Any]) -> Optional[Any]:
        """Выполнить агента с мониторингом"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Агент теперь возвращает словарь с pydantic_result и processed_result
            agent_output = await agent.ainvoke(input_data)
            pydantic_result = agent_output["pydantic_result"]
            processed_result = agent_output["processed_result"]

            execution_time = asyncio.get_event_loop().time() - start_time
            
            # Создание краткого описания результата
            output_summary = self._create_output_summary(agent_name, processed_result)
            
            self._record_agent_status(agent_name, "success", execution_time, output_summary=output_summary)
            return pydantic_result # Возвращаем Pydantic объект для дальнейшей обработки
            
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            error_msg = str(e)
            
            self._record_agent_status(agent_name, "error", execution_time, error_message=error_msg)
            logger.error(f"❌ Агент {agent_name} завершился с ошибкой: {error_msg}")
            
            # Возвращаем None для обработки в основном коде
            return None
    
    def _extract_agent_data(self, result: Any) -> tuple[Any, Any]:
        """Извлечь pydantic_result и processed_result из результата агента"""
        if result is None:
            return None, None
            
        if isinstance(result, dict):
            if 'pydantic_result' in result and 'processed_result' in result:
                return result['pydantic_result'], result['processed_result']
            else:
                return None, result
        
        return result, None

    def _create_output_summary(self, agent_name: str, result: Any) -> str:
        """Создать краткое описание результата агента"""
        try:
            # Извлекаем данные из новой структуры результата
            pydantic_result, processed_result = self._extract_agent_data(result)
            
            if agent_name == "dialogue_assessor":
                # Для dialogue_assessor используем processed_result (эвристический агент)
                if processed_result and isinstance(processed_result, dict):
                    detail_level = processed_result.get('detail_level', 'unknown')
                    dialogue_type = processed_result.get('dialogue_type', 'unknown')
                elif pydantic_result:
                    detail_level = getattr(pydantic_result, 'detail_level', 'unknown')
                    dialogue_type = getattr(pydantic_result, 'dialogue_type', 'unknown')
                else:
                    detail_level = dialogue_type = 'unknown'
                return f"detail_level={detail_level}, dialogue_type={dialogue_type}"
            elif agent_name == "topic_extractor":
                # Используем pydantic_result для подсчета тем
                if pydantic_result and hasattr(pydantic_result, 'topics'):
                    topics_count = len(pydantic_result.topics)
                elif processed_result and isinstance(processed_result, dict):
                    topics_count = len(processed_result.get('topics', []))
                else:
                    topics_count = 0
                return f"извлечено {topics_count} тем"
            elif agent_name == "emotion_analyzer":
                # Используем pydantic_result для эмоционального анализа
                if pydantic_result and hasattr(pydantic_result, 'overall_tone'):
                    tone = pydantic_result.overall_tone
                    atmosphere = pydantic_result.atmosphere
                elif processed_result and isinstance(processed_result, dict):
                    tone = processed_result.get('overall_tone', 'unknown')
                    atmosphere = processed_result.get('atmosphere', 'unknown')
                else:
                    tone = atmosphere = 'unknown'
                return f"тон={tone}, атмосфера={atmosphere}"
            elif agent_name == "speaker_analyzer":
                # Используем pydantic_result для подсчета участников
                if pydantic_result and hasattr(pydantic_result, 'speakers'):
                    speakers_count = len(pydantic_result.speakers)
                elif processed_result and isinstance(processed_result, dict):
                    speakers_count = len(processed_result.get('speakers', []))
                else:
                    speakers_count = 0
                return f"проанализировано {speakers_count} участников"
            elif agent_name == "context_summarizer":
                if isinstance(result, dict):
                    summary = result.get('summary', {})
                    if isinstance(summary, dict):
                        points_count = len(summary.get('main_points', []))
                    else:
                        points_count = len(getattr(summary, 'main_points', []))
                else:
                    summary = getattr(result, 'summary', None)
                    if summary:
                        points_count = len(getattr(summary, 'main_points', []))
                    else:
                        points_count = 0
                return f"создано {points_count} основных пунктов"
            elif agent_name == "key_moments":
                if isinstance(result, dict):
                    decisions_count = len(result.get('key_decisions', []))
                    questions_count = len(result.get('critical_questions', []))
                else:
                    decisions_count = len(getattr(result, 'key_decisions', []))
                    questions_count = len(getattr(result, 'critical_questions', []))
                return f"{decisions_count} решений, {questions_count} вопросов"
            elif agent_name == "timeline_builder":
                if isinstance(result, dict):
                    events_count = len(result.get('timeline_events', []))
                else:
                    events_count = len(getattr(result, 'timeline_events', []))
                return f"создано {events_count} событий"
            elif agent_name == "context_links":
                if isinstance(result, dict):
                    external_count = len(result.get('external_links', []))
                    telegram_count = len(result.get('telegram_links', []))
                else:
                    external_count = len(getattr(result, 'external_links', []))
                    telegram_count = len(getattr(result, 'telegram_links', []))
                return f"{external_count} внешних, {telegram_count} Telegram ссылок"
            elif agent_name == "supervisor_synthesizer":
                if isinstance(result, dict):
                    html_length = len(result.get('html_digest', ''))
                else:
                    html_length = len(getattr(result, 'html_digest', ''))
                return f"создан дайджест {html_length} символов HTML"
            else:
                return "выполнен успешно"
        except Exception as e:
            return f"результат получен (ошибка описания: {str(e)})"
    
    async def generate_digest(
        self, 
        messages: List[Any], 
        hours: int = 24,
        user_id: Optional[int] = None,
        group_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Генерация дайджеста группы через LangChain агентов
        
        Args:
            messages: Список сообщений Telegram
            hours: Период в часах
            user_id: ID пользователя
            group_id: ID группы
            
        Returns:
            Словарь с результатами дайджеста
        """
        start_time = asyncio.get_event_loop().time()
        
        logger.info(f"🎯 Начало генерации дайджеста для группы {group_id}")
        logger.info(f"   Сообщений: {len(messages)}")
        logger.info(f"   Часов: {hours}")
        logger.info(f"   Пользователь: {user_id}")
        
        # Очистка статуса агентов для нового дайджеста
        self.agents_status.clear()
        
        try:
            # Форматирование сообщений
            formatted_messages = self._format_messages_for_analysis(messages)
            
            # Подготовка входных данных
            input_data = {
                "messages": formatted_messages,
                "hours": hours,
                "user_id": user_id,
                "group_id": group_id
            }
            
            # Phase 1: Dialogue Assessor (LLM-based анализ)
            logger.info("📊 Phase 1: Dialogue Assessor")
            assessment = await self._execute_agent_with_monitoring(
                self.assessor, "dialogue_assessor", input_data
            )
            if assessment:
                input_data["assessment"] = assessment
                # Безопасное получение значений
                if isinstance(assessment, dict):
                    detail_level = assessment.get('detail_level', 'standard')
                    dialogue_type = assessment.get('dialogue_type', 'discussion')
                else:
                    detail_level = getattr(assessment, 'detail_level', 'standard')
                    dialogue_type = getattr(assessment, 'dialogue_type', 'discussion')
                logger.info(f"   Уровень детализации: {detail_level}")
                logger.info(f"   Тип диалога: {dialogue_type}")
            else:
                # Fallback значения
                assessment = {
                    'detail_level': 'standard',
                    'dialogue_type': 'discussion'
                }
                input_data["assessment"] = assessment
                logger.warning(f"   Fallback: detail_level=standard, dialogue_type=discussion")
            
            # Phase 2-3: Topics + Emotions (PARALLEL execution)
            logger.info("🔄 Phase 2-3: Topics + Emotions (Parallel)")
            
            # Параллельное выполнение Topics и Emotions
            topics_task = asyncio.create_task(
                self._execute_agent_with_monitoring(self.topic_extractor, "topic_extractor", input_data)
            )
            emotions_task = asyncio.create_task(
                self._execute_agent_with_monitoring(self.emotion_analyzer, "emotion_analyzer", input_data)
            )
            
            topics, emotions = await asyncio.gather(topics_task, emotions_task)
            
            if topics:
                pydantic_topics, processed_topics = self._extract_agent_data(topics)
                input_data["topics"] = pydantic_topics if pydantic_topics else processed_topics
                topics_count = len(pydantic_topics.topics) if pydantic_topics and hasattr(pydantic_topics, 'topics') else 0
                logger.info(f"   Извлечено тем: {topics_count}")
            else:
                logger.warning("   Topics: fallback (нет данных)")
                
            if emotions:
                pydantic_emotions, processed_emotions = self._extract_agent_data(emotions)
                input_data["emotions"] = pydantic_emotions if pydantic_emotions else processed_emotions
                tone = pydantic_emotions.overall_tone if pydantic_emotions and hasattr(pydantic_emotions, 'overall_tone') else 'unknown'
                logger.info(f"   Тон: {tone}")
            else:
                logger.warning("   Emotions: fallback (нет данных)")
            
            # Phase 4: Speaker Analyzer
            logger.info("👥 Phase 4: Speaker Analyzer")
            speakers = await self._execute_agent_with_monitoring(
                self.speaker_analyzer, "speaker_analyzer", input_data
            )
            
            if speakers:
                pydantic_speakers, processed_speakers = self._extract_agent_data(speakers)
                input_data["speakers"] = pydantic_speakers if pydantic_speakers else processed_speakers
                speakers_count = len(pydantic_speakers.speakers) if pydantic_speakers and hasattr(pydantic_speakers, 'speakers') else 0
                logger.info(f"   Участников проанализировано: {speakers_count}")
            else:
                logger.warning("   Speakers: fallback (нет данных)")
            
            # Phase 5: Context Summarizer
            logger.info("📝 Phase 5: Context Summarizer")
            summary = await self._execute_agent_with_monitoring(
                self.summarizer, "context_summarizer", input_data
            )
            
            if summary:
                pydantic_summary, processed_summary = self._extract_agent_data(summary)
                input_data["summary"] = pydantic_summary if pydantic_summary else processed_summary
                points_count = len(pydantic_summary.summary.main_points) if pydantic_summary and hasattr(pydantic_summary, 'summary') else 0
                logger.info(f"   Основных пунктов: {points_count}")
            else:
                logger.warning("   Summary: fallback (нет данных)")
            
            # Phase 6: Key Moments (conditional)
            detail_level = assessment.get('detail_level', 'standard') if isinstance(assessment, dict) else getattr(assessment, 'detail_level', 'standard')
            if detail_level in ["detailed", "comprehensive"]:
                logger.info("🔑 Phase 6: Key Moments")
                key_moments = await self._execute_agent_with_monitoring(
                    self.key_moments, "key_moments", input_data
                )
                
                if key_moments:
                    pydantic_key_moments, processed_key_moments = self._extract_agent_data(key_moments)
                    input_data["key_moments"] = pydantic_key_moments if pydantic_key_moments else processed_key_moments
                    decisions_count = len(pydantic_key_moments.key_decisions) if pydantic_key_moments and hasattr(pydantic_key_moments, 'key_decisions') else 0
                    questions_count = len(pydantic_key_moments.critical_questions) if pydantic_key_moments and hasattr(pydantic_key_moments, 'critical_questions') else 0
                    logger.info(f"   Решений: {decisions_count}, Вопросов: {questions_count}")
                else:
                    logger.warning("   Key Moments: fallback (нет данных)")
            else:
                logger.info("⏭️ Phase 6: Key Moments (пропущен - уровень детализации слишком низкий)")
            
            # Phase 7: Timeline Builder (conditional)
            if detail_level in ["detailed", "comprehensive"]:
                logger.info("⏰ Phase 7: Timeline Builder")
                timeline = await self._execute_agent_with_monitoring(
                    self.timeline, "timeline_builder", input_data
                )
                
                if timeline:
                    pydantic_timeline, processed_timeline = self._extract_agent_data(timeline)
                    input_data["timeline"] = pydantic_timeline if pydantic_timeline else processed_timeline
                    events_count = len(pydantic_timeline.timeline_events) if pydantic_timeline and hasattr(pydantic_timeline, 'timeline_events') else 0
                    logger.info(f"   Событий: {events_count}")
                else:
                    logger.warning("   Timeline: fallback (нет данных)")
            else:
                logger.info("⏭️ Phase 7: Timeline Builder (пропущен - уровень детализации слишком низкий)")
            
            # Phase 8: Context Links (always)
            logger.info("🔗 Phase 8: Context Links")
            context_links = await self._execute_agent_with_monitoring(
                self.context_links, "context_links", input_data
            )
            
            if context_links:
                pydantic_context_links, processed_context_links = self._extract_agent_data(context_links)
                input_data["context_links"] = pydantic_context_links if pydantic_context_links else processed_context_links
                external_count = len(pydantic_context_links.external_links) if pydantic_context_links and hasattr(pydantic_context_links, 'external_links') else 0
                telegram_count = len(pydantic_context_links.telegram_links) if pydantic_context_links and hasattr(pydantic_context_links, 'telegram_links') else 0
                logger.info(f"   Внешних ссылок: {external_count}, Telegram ссылок: {telegram_count}")
            else:
                logger.warning("   Context Links: fallback (нет данных)")
            
            # Phase 9: Supervisor Synthesizer (финальный агент)
            logger.info("🎭 Phase 9: Supervisor Synthesizer")
            
            # Добавляем статус агентов в метаданные
            input_data["agents_status"] = self.agents_status
            
            final_digest = await self._execute_agent_with_monitoring(
                self.supervisor, "supervisor_synthesizer", input_data
            )
            
            if final_digest:
                # final_digest уже является Pydantic объектом (возвращается из _execute_agent_with_monitoring)
                final_result = final_digest
                
                # Добавляем статус агентов в финальный результат
                if isinstance(final_result, dict):
                    if 'metadata' in final_result and final_result['metadata']:
                        final_result['metadata']['agents_status'] = self.agents_status
                elif hasattr(final_result, 'metadata') and final_result.metadata:
                    final_result.metadata.agents_status = self.agents_status
                
                total_time = asyncio.get_event_loop().time() - start_time
                html_length = len(final_result.get('html_digest', '')) if isinstance(final_result, dict) else len(getattr(final_result, 'html_digest', ''))
                
                logger.info(f"✅ Дайджест сгенерирован за {total_time:.2f}s")
                logger.info(f"   Финальный размер: {html_length} символов")
                
                # Логирование сводки по агентам
                self._log_agents_summary()
                
                return {
                    "success": True,
                    "digest": final_result,
                    "agents_status": self.agents_status,
                    "execution_time": total_time
                }
            else:
                raise Exception("Supervisor Synthesizer failed to generate digest")
                
        except Exception as e:
            total_time = asyncio.get_event_loop().time() - start_time
            logger.error(f"❌ Ошибка генерации дайджеста: {str(e)}")
            
            return {
                "success": False,
                "error": str(e),
                "agents_status": self.agents_status,
                "execution_time": total_time
            }
    
    def _log_agents_summary(self):
        """Логировать сводку по статусу агентов"""
        logger.info("📊 Сводка по агентам:")
        
        success_count = sum(1 for status in self.agents_status if status.status == "success")
        error_count = sum(1 for status in self.agents_status if status.status == "error")
        fallback_count = sum(1 for status in self.agents_status if status.status == "fallback")
        
        logger.info(f"   ✅ Успешно: {success_count}")
        logger.info(f"   ❌ Ошибки: {error_count}")
        logger.info(f"   🔄 Fallback: {fallback_count}")
        
        # Детали по агентам с ошибками
        failed_agents = [status for status in self.agents_status if status.status in ["error", "fallback"]]
        if failed_agents:
            logger.warning("   Проблемные агенты:")
            for agent_status in failed_agents:
                logger.warning(f"     - {agent_status.agent_name}: {agent_status.error_message}")
    
    def get_agents_status(self) -> List[AgentStatus]:
        """Получить статус всех агентов"""
        return self.agents_status.copy()
