"""
Group Digest Generator
Генерация дайджестов диалогов в Telegram группах через n8n multi-agent workflows
Поддерживает как n8n, так и прямую LangChain интеграцию
"""
import logging
import os
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from telethon.tl.types import Message
from dotenv import load_dotenv
import telegram_formatter

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GroupDigestGenerator:
    """Генератор дайджестов для Telegram групп через n8n workflows или LangChain"""
    
    def __init__(self):
        # Feature flags
        self.use_langchain_direct = os.getenv("USE_LANGCHAIN_DIRECT", "false").lower() == "true"
        self.use_v2_pipeline = os.getenv("USE_DIGEST_V2", "true").lower() == "true"
        
        if self.use_langchain_direct:
            # LangChain Direct Integration
            logger.info("🚀 Инициализация LangChain Direct Integration")
            try:
                from langchain_agents.orchestrator import DigestOrchestrator
                self.orchestrator = DigestOrchestrator()
                logger.info("✅ LangChain Orchestrator инициализирован")
            except ImportError as e:
                logger.error(f"❌ Ошибка импорта LangChain: {e}")
                logger.info("🔄 Переключение на n8n fallback")
                self.use_langchain_direct = False
        
        if not self.use_langchain_direct:
            # n8n webhook URLs (fallback)
            self.n8n_digest_webhook = os.getenv(
                "N8N_GROUP_DIGEST_WEBHOOK", 
                "http://n8n:5678/webhook/group-digest"
            )
            self.n8n_digest_webhook_v2 = os.getenv(
                "N8N_GROUP_DIGEST_WEBHOOK_V2",
                "http://n8n:5678/webhook/group-digest-v2"
            )
            self.n8n_mention_webhook = os.getenv(
                "N8N_MENTION_ANALYZER_WEBHOOK",
                "http://n8n:5678/webhook/mention-analyzer"
            )
            
            # Timeouts
            self.digest_timeout = float(os.getenv("N8N_DIGEST_TIMEOUT", "120"))
            self.digest_timeout_v2 = float(os.getenv("N8N_DIGEST_TIMEOUT_V2", "180"))
            self.mention_timeout = float(os.getenv("N8N_MENTION_TIMEOUT", "60"))
            
            logger.info("✅ GroupDigestGenerator инициализирован с n8n")
            logger.info(f"   V1 Webhook: {self.n8n_digest_webhook}")
            logger.info(f"   V2 Webhook: {self.n8n_digest_webhook_v2}")
            logger.info(f"   Use V2 Pipeline: {self.use_v2_pipeline}")
            logger.info(f"   Mention webhook: {self.n8n_mention_webhook}")
    
    async def generate_digest(
        self, 
        user_id: int, 
        group_id: int, 
        messages: List[Message],
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Генерирует дайджест разговора через n8n multi-agent workflow или LangChain
        
        Args:
            user_id: ID пользователя
            group_id: ID группы
            messages: Список сообщений Telethon
            hours: Период в часах
            
        Returns:
            Dict с результатами дайджеста
        """
        try:
            logger.info(f"🤖 Генерация дайджеста для группы {group_id} (user {user_id})")
            logger.info(f"   Сообщений: {len(messages)}, период: {hours}ч")
            logger.info(f"   Используется: {'LangChain Direct' if self.use_langchain_direct else 'n8n'}")
            
            # Ограничиваем количество сообщений
            max_messages = int(os.getenv("DIGEST_MAX_MESSAGES", "200"))
            limited_messages = messages[:max_messages]
            
            # Выбор метода генерации
            if self.use_langchain_direct:
                return await self._generate_with_langchain(user_id, group_id, limited_messages, hours)
            else:
                return await self._generate_with_n8n(user_id, group_id, limited_messages, hours)
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации дайджеста: {e}")
            raise
    
    async def _generate_with_langchain(
        self, 
        user_id: int, 
        group_id: int, 
        messages: List[Message],
        hours: int
    ) -> Dict[str, Any]:
        """
        Генерация дайджеста через LangChain Direct Integration
        
        Args:
            user_id: ID пользователя
            group_id: ID группы
            messages: Список сообщений Telethon
            hours: Период в часах
            
        Returns:
            Dict с результатами дайджеста
        """
        try:
            logger.info("🚀 Генерация через LangChain Direct Integration")
            
            # Вызов LangChain Orchestrator
            result = await self.orchestrator.generate_digest(
                messages=messages,
                hours=hours,
                user_id=user_id,
                group_id=group_id
            )
            
            # Проверяем успешность генерации
            if not result.get("success", False):
                raise Exception(f"LangChain generation failed: {result.get('error', 'Unknown error')}")
            
            # Получаем Pydantic объект дайджеста
            digest_obj = result["digest"]
            
            # Адаптация результата для совместимости с существующим кодом
            adapted_result = {
                "html_digest": digest_obj.html_digest,
                "topics": self._extract_topics_from_langchain_result(digest_obj),
                "speakers_summary": self._extract_speakers_from_langchain_result(digest_obj),
                "overall_summary": digest_obj.sections.summary,
                "message_count": len(messages),
                "period": f"{hours}ч",
                "detail_level": digest_obj.metadata.detail_level,
                "dialogue_type": digest_obj.metadata.dialogue_type,
                "generation_method": "langchain_direct",
                "generation_metadata": {
                    "execution_time": result.get("execution_time", 0),
                    "agents_status": result.get("agents_status", [])
                },
                "agent_results": result.get("agent_results", {}),
                "agent_statistics": {
                    "agents_executed": len(result.get("agents_status", [])),
                    "successful_agents": len([s for s in result.get("agents_status", []) if s.status == "success"])
                }
            }
            
            # DEBUG: Логируем что получили от LangChain
            logger.info(f"📊 LangChain результат:")
            logger.info(f"   HTML дайджест: {len(digest_obj.html_digest)} символов")
            logger.info(f"   Темы: {len(adapted_result['topics'])}")
            logger.info(f"   Спикеры: {len(adapted_result['speakers_summary'])}")
            logger.info(f"   Резюме: {len(adapted_result['overall_summary'])} символов")
            
            logger.info("✅ LangChain дайджест сгенерирован успешно")
            logger.info(f"   Детализация: {adapted_result['detail_level']}")
            logger.info(f"   Тип диалога: {adapted_result['dialogue_type']}")
            logger.info(f"   Агентов выполнено: {adapted_result['agent_statistics'].get('agents_executed', 0)}")
            
            return adapted_result
            
        except Exception as e:
            logger.error(f"❌ Ошибка LangChain генерации: {e}")
            raise
    
    async def _generate_with_n8n(
        self, 
        user_id: int, 
        group_id: int, 
        messages: List[Message],
        hours: int
    ) -> Dict[str, Any]:
        """
        Генерация дайджеста через n8n workflows (fallback)
        
        Args:
            user_id: ID пользователя
            group_id: ID группы
            messages: Список сообщений Telethon
            hours: Период в часах
            
        Returns:
            Dict с результатами дайджеста
        """
        try:
            logger.info("📡 Генерация через n8n workflows")
            
            # Форматируем сообщения для n8n
            formatted_messages = []
            for msg in messages:
                # Безопасное получение username
                username = "Unknown"
                if hasattr(msg, 'sender') and msg.sender:
                    if hasattr(msg.sender, 'username') and msg.sender.username:
                        username = msg.sender.username
                    elif hasattr(msg.sender, 'first_name') and msg.sender.first_name:
                        username = msg.sender.first_name
                    
                    logger.debug(f"Message sender: {username}")
                else:
                    logger.warning(f"Message has no sender information!")
                
                formatted_messages.append({
                    "username": username,
                    "text": msg.text or "",
                    "date": msg.date.isoformat() if hasattr(msg.date, 'isoformat') else str(msg.date)
                })
            
            # DEBUG: Логируем уникальные usernames что отправляем
            unique_usernames = set(m['username'] for m in formatted_messages)
            logger.info(f"📤 Отправляем в n8n {len(formatted_messages)} сообщений от {len(unique_usernames)} пользователей: {', '.join(unique_usernames)}")
            
            # Вызываем n8n workflow (V1 или V2)
            webhook_url = self.n8n_digest_webhook_v2 if self.use_v2_pipeline else self.n8n_digest_webhook
            timeout = self.digest_timeout_v2 if self.use_v2_pipeline else self.digest_timeout
            
            async with httpx.AsyncClient(timeout=timeout) as client:
                logger.info(f"📡 Вызов n8n workflow: {webhook_url}")
                logger.info(f"   Pipeline: {'V2 Sequential' if self.use_v2_pipeline else 'V1 Parallel'}")
                
                response = await client.post(
                    webhook_url,
                    json={
                        "messages": formatted_messages,
                        "user_id": user_id,
                        "group_id": group_id,
                        "hours": hours
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"❌ n8n workflow error: {response.status_code}")
                    logger.error(f"   Response: {response.text[:500]}")
                    raise Exception(f"n8n workflow failed: {response.status_code}")
                
                result = response.json()
                logger.info(f"✅ n8n дайджест сгенерирован успешно")
                logger.info(f"   Тем: {len(result.get('topics', []))}")
                logger.info(f"   Спикеров: {len(result.get('speakers_summary', {}))}")
                
                # Добавляем информацию о методе генерации
                result["generation_method"] = "n8n"
                
                return result
                
        except httpx.TimeoutException:
            logger.error(f"⏰ Timeout при генерации дайджеста ({self.digest_timeout}s)")
            raise Exception(f"n8n workflow timeout after {self.digest_timeout}s")
        
        except httpx.ConnectError as e:
            logger.error(f"🔌 Не удалось подключиться к n8n: {e}")
            logger.error(f"   Проверьте что n8n запущен и доступен по адресу {self.n8n_digest_webhook}")
            raise Exception(f"n8n unavailable: {str(e)}")
        
        except Exception as e:
            logger.error(f"❌ Ошибка n8n генерации: {e}")
            raise
    
    def _extract_topics_from_langchain_result(self, digest_obj) -> List[str]:
        """Извлечение тем из результата LangChain для совместимости"""
        try:
            # digest_obj теперь является Pydantic объектом SupervisorOutput
            # Темы находятся в sections.topics как строка
            topics_text = digest_obj.sections.topics
            logger.debug(f"📝 Темы из LangChain: {topics_text[:200]}...")
            
            # Парсим темы из HTML/текста
            import re
            
            # Убираем HTML теги
            clean_text = re.sub(r'<[^>]+>', '', topics_text)
            
            # Ищем темы в различных форматах
            topics = []
            
            # Формат 1: "• Название (приоритет)"
            pattern1 = r'•\s*([^(]+)\s*\([^)]*\)'
            matches1 = re.findall(pattern1, clean_text)
            if matches1:
                topics.extend([topic.strip() for topic in matches1])
            
            # Формат 2: "1. Название (приоритет)"
            pattern2 = r'\d+\.\s*([^(]+)\s*\([^)]*\)'
            matches2 = re.findall(pattern2, clean_text)
            if matches2:
                topics.extend([topic.strip() for topic in matches2])
            
            # Формат 3: Просто названия без приоритетов
            if not topics:
                # Разбиваем по строкам и берем непустые
                lines = [line.strip() for line in clean_text.split('\n') if line.strip()]
                topics = [line for line in lines if not line.startswith(('🎯', '📊', '👥', '📝'))]
            
            # Убираем дубликаты и пустые строки
            unique_topics = []
            seen = set()
            for topic in topics:
                if topic and topic not in seen:
                    unique_topics.append(topic)
                    seen.add(topic)
            
            logger.debug(f"📝 Извлечено тем: {len(unique_topics)}")
            return unique_topics
            
        except Exception as e:
            logger.warning(f"Ошибка извлечения тем: {e}")
            return []
    
    def _extract_speakers_from_langchain_result(self, digest_obj) -> Dict[str, str]:
        """Извлечение спикеров из результата LangChain для совместимости"""
        try:
            # digest_obj теперь является Pydantic объектом SupervisorOutput
            # Спикеры находятся в sections.participants как строка
            participants_text = digest_obj.sections.participants
            logger.debug(f"👥 Участники из LangChain: {participants_text[:200]}...")
            
            # Парсим участников из текста
            import re
            
            speakers_summary = {}
            
            # Убираем HTML теги
            clean_text = re.sub(r'<[^>]+>', '', participants_text)
            
            # Формат 1: "@username (роль, количество сообщений)"
            pattern1 = r'@(\w+)\s*\(([^,]+)'
            matches1 = re.findall(pattern1, clean_text)
            for username, role in matches1:
                speakers_summary[username] = role.strip()
            
            # Формат 2: "@username - роль (количество сообщений)"
            pattern2 = r'@(\w+)\s*-\s*([^(]+)'
            matches2 = re.findall(pattern2, clean_text)
            for username, role in matches2:
                speakers_summary[username] = role.strip()
            
            # Формат 3: "• @username (роль)"
            pattern3 = r'•\s*@(\w+)\s*\(([^)]+)\)'
            matches3 = re.findall(pattern3, clean_text)
            for username, role in matches3:
                speakers_summary[username] = role.strip()
            
            logger.debug(f"👥 Извлечено участников: {len(speakers_summary)}")
            return speakers_summary
            
        except Exception as e:
            logger.warning(f"Ошибка извлечения спикеров: {e}")
            return {}
    
    async def analyze_mention(
        self,
        mentioned_user: str,
        context_messages: List[Message]
    ) -> Dict[str, Any]:
        """
        Анализирует контекст упоминания пользователя через n8n workflow
        
        Args:
            mentioned_user: Username упомянутого пользователя
            context_messages: Список сообщений контекста (до/после упоминания)
            
        Returns:
            {
                "context_summary": str,
                "mention_reason": str,
                "urgency": str,
                "key_points": List[str]
            }
        """
        try:
            logger.info(f"🔍 Анализ упоминания @{mentioned_user}")
            logger.info(f"   Контекст: {len(context_messages)} сообщений")
            
            # Форматируем контекст для n8n
            formatted_context = []
            for msg in context_messages:
                # Безопасное получение username
                username = "Unknown"
                if hasattr(msg, 'sender') and msg.sender:
                    if hasattr(msg.sender, 'username') and msg.sender.username:
                        username = msg.sender.username
                    elif hasattr(msg.sender, 'first_name') and msg.sender.first_name:
                        username = msg.sender.first_name
                
                formatted_context.append({
                    "username": username,
                    "text": msg.text or "",
                    "timestamp": msg.date.isoformat() if hasattr(msg.date, 'isoformat') else str(msg.date)
                })
            
            # Вызываем n8n workflow
            async with httpx.AsyncClient(timeout=self.mention_timeout) as client:
                logger.info(f"📡 Вызов n8n workflow: {self.n8n_mention_webhook}")
                
                response = await client.post(
                    self.n8n_mention_webhook,
                    json={
                        "mention_context": formatted_context,
                        "mentioned_user": mentioned_user
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"❌ n8n workflow error: {response.status_code}")
                    logger.error(f"   Response: {response.text[:500]}")
                    raise Exception(f"n8n workflow failed: {response.status_code}")
                
                result = response.json()
                logger.info(f"✅ Анализ упоминания завершен")
                logger.info(f"   Срочность: {result.get('urgency', 'unknown')}")
                logger.info(f"   Причина: {result.get('mention_reason', 'unknown')[:50]}...")
                
                return result
                
        except httpx.TimeoutException:
            logger.error(f"⏰ Timeout при анализе упоминания ({self.mention_timeout}s)")
            raise Exception(f"n8n workflow timeout after {self.mention_timeout}s")
        
        except httpx.ConnectError as e:
            logger.error(f"🔌 Не удалось подключиться к n8n: {e}")
            raise Exception(f"n8n unavailable: {str(e)}")
        
        except Exception as e:
            logger.error(f"❌ Ошибка анализа упоминания: {e}")
            raise
    
    def format_digest_for_telegram(self, digest: Dict[str, Any], group_title: str) -> str:
        """
        Форматирует дайджест для отправки в Telegram
        
        V2: Если используется V2 pipeline, digest уже содержит готовый HTML в поле digest_html
        V1: Делегирует форматирование в telegram_formatter
        
        Args:
            digest: Результат от generate_digest()
            group_title: Название группы
            
        Returns:
            Отформатированное сообщение в HTML
        """
        # V2 Pipeline: используем готовый HTML от Supervisor Synthesizer
        if self.use_v2_pipeline and 'digest_html' in digest:
            logger.info("📄 Используем готовый HTML digest из V2 pipeline")
            return digest['digest_html']
        
        # V1 Pipeline: форматируем через telegram_formatter
        logger.info("📄 Форматируем digest через telegram_formatter (V1)")
        return telegram_formatter.format_digest_for_telegram(digest, group_title)
    
    def format_mention_for_telegram(
        self, 
        analysis: Dict[str, Any], 
        group_title: str,
        message_link: str = None
    ) -> str:
        """
        Форматирует анализ упоминания для уведомления в Telegram
        
        Делегирует форматирование в telegram_formatter для автоматической
        конвертации Markdown → MarkdownV2 с правильным экранированием.
        
        Args:
            analysis: Результат от analyze_mention()
            group_title: Название группы
            message_link: Ссылка на сообщение (опционально)
            
        Returns:
            Отформатированное сообщение в MarkdownV2
        """
        # Маппинг urgency для совместимости с telegram_formatter
        urgency_mapping = {
            "low": "normal",
            "medium": "important",
            "high": "urgent"
        }
        
        # Создаем копию analysis с нормализованным urgency
        normalized_analysis = analysis.copy()
        old_urgency = normalized_analysis.get('urgency', 'medium')
        normalized_analysis['urgency'] = urgency_mapping.get(old_urgency, 'important')
        
        # Маппинг полей для совместимости
        if 'context_summary' in normalized_analysis:
            normalized_analysis['context'] = normalized_analysis.pop('context_summary')
        
        return telegram_formatter.format_mention_for_telegram(
            normalized_analysis,
            group_title,
            message_link
        )


# Глобальный экземпляр
group_digest_generator = GroupDigestGenerator()

