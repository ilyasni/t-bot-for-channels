"""
Group Digest Generator
Генерация дайджестов диалогов в Telegram группах через n8n multi-agent workflows
"""
import logging
import os
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from telethon.tl.types import Message
from dotenv import load_dotenv
from markdown_utils import escape_markdown_v2

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GroupDigestGenerator:
    """Генератор дайджестов для Telegram групп через n8n workflows"""
    
    def __init__(self):
        # n8n webhook URLs
        self.n8n_digest_webhook = os.getenv(
            "N8N_GROUP_DIGEST_WEBHOOK", 
            "http://n8n:5678/webhook/group-digest"
        )
        self.n8n_mention_webhook = os.getenv(
            "N8N_MENTION_ANALYZER_WEBHOOK",
            "http://n8n:5678/webhook/mention-analyzer"
        )
        
        # Timeouts
        self.digest_timeout = float(os.getenv("N8N_DIGEST_TIMEOUT", "120"))  # 2 минуты
        self.mention_timeout = float(os.getenv("N8N_MENTION_TIMEOUT", "60"))  # 1 минута
        
        logger.info(f"✅ GroupDigestGenerator инициализирован")
        logger.info(f"   Digest webhook: {self.n8n_digest_webhook}")
        logger.info(f"   Mention webhook: {self.n8n_mention_webhook}")
    
    async def generate_digest(
        self, 
        user_id: int, 
        group_id: int, 
        messages: List[Message],
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Генерирует дайджест разговора через n8n multi-agent workflow
        
        Args:
            user_id: ID пользователя
            group_id: ID группы
            messages: Список сообщений Telethon
            hours: Период в часах
            
        Returns:
            {
                "topics": List[str],
                "speakers_summary": Dict[str, str],
                "overall_summary": str,
                "message_count": int,
                "period": str
            }
        """
        try:
            logger.info(f"🤖 Генерация дайджеста для группы {group_id} (user {user_id})")
            logger.info(f"   Сообщений: {len(messages)}, период: {hours}ч")
            
            # Ограничиваем количество сообщений
            max_messages = int(os.getenv("DIGEST_MAX_MESSAGES", "200"))
            limited_messages = messages[:max_messages]
            
            # Форматируем сообщения для n8n
            formatted_messages = []
            for msg in limited_messages:
                # Безопасное получение username
                username = "Unknown"
                if hasattr(msg, 'sender') and msg.sender:
                    if hasattr(msg.sender, 'username') and msg.sender.username:
                        username = msg.sender.username
                    elif hasattr(msg.sender, 'first_name') and msg.sender.first_name:
                        username = msg.sender.first_name
                
                formatted_messages.append({
                    "username": username,
                    "text": msg.text or "",
                    "date": msg.date.isoformat() if hasattr(msg.date, 'isoformat') else str(msg.date)
                })
            
            # Вызываем n8n workflow
            async with httpx.AsyncClient(timeout=self.digest_timeout) as client:
                logger.info(f"📡 Вызов n8n workflow: {self.n8n_digest_webhook}")
                
                response = await client.post(
                    self.n8n_digest_webhook,
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
                logger.info(f"✅ Дайджест сгенерирован успешно")
                logger.info(f"   Тем: {len(result.get('topics', []))}")
                logger.info(f"   Спикеров: {len(result.get('speakers_summary', {}))}")
                
                return result
                
        except httpx.TimeoutException:
            logger.error(f"⏰ Timeout при генерации дайджеста ({self.digest_timeout}s)")
            raise Exception(f"n8n workflow timeout after {self.digest_timeout}s")
        
        except httpx.ConnectError as e:
            logger.error(f"🔌 Не удалось подключиться к n8n: {e}")
            logger.error(f"   Проверьте что n8n запущен и доступен по адресу {self.n8n_digest_webhook}")
            raise Exception(f"n8n unavailable: {str(e)}")
        
        except Exception as e:
            logger.error(f"❌ Ошибка генерации дайджеста: {e}")
            raise
    
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
        
        Args:
            digest: Результат от generate_digest()
            group_title: Название группы
            
        Returns:
            Отформатированное сообщение в Markdown
        """
        lines = []
        
        # Экранируем спецсимволы Markdown в названии группы
        safe_title = escape_markdown_v2(group_title)
        
        # Заголовок
        lines.append(f"# 📊 Дайджест группы: {safe_title}")
        lines.append(f"**Период:** {digest.get('period', 'unknown')}")
        lines.append(f"**Сообщений проанализировано:** {digest.get('message_count', 0)}")
        lines.append("")
        
        # Темы
        topics = digest.get('topics', [])
        if topics:
            lines.append("## 🎯 Основные темы:")
            for i, topic in enumerate(topics, 1):
                safe_topic = escape_markdown_v2(str(topic))
                lines.append(f"{i}\\. {safe_topic}")
            lines.append("")
        
        # Спикеры
        speakers = digest.get('speakers_summary', {})
        if speakers:
            lines.append("## 👥 Активные участники:")
            for username, summary in speakers.items():
                safe_username = escape_markdown_v2(str(username))
                safe_summary = escape_markdown_v2(str(summary))
                lines.append(f"• @{safe_username}: {safe_summary}")
            lines.append("")
        
        # Общее резюме
        overall = digest.get('overall_summary', '')
        if overall:
            lines.append("## 📝 Резюме:")
            safe_overall = escape_markdown_v2(str(overall))
            lines.append(safe_overall)
            lines.append("")
        
        # Футер
        lines.append("\\-\\-\\-")
        lines.append(f"*Дайджест сгенерирован AI \\(GigaChat Multi\\-Agent\\) • {datetime.now().strftime('%d.%m.%Y %H:%M')}*")
        
        return "\n".join(lines)
    
    def format_mention_for_telegram(
        self, 
        analysis: Dict[str, Any], 
        group_title: str,
        message_link: str = None
    ) -> str:
        """
        Форматирует анализ упоминания для уведомления в Telegram
        
        Args:
            analysis: Результат от analyze_mention()
            group_title: Название группы
            message_link: Ссылка на сообщение (опционально)
            
        Returns:
            Отформатированное сообщение в Markdown
        """
        urgency_emoji = {
            "low": "🟢",
            "medium": "🟡",
            "high": "🔴"
        }
        
        urgency = analysis.get('urgency', 'medium')
        emoji = urgency_emoji.get(urgency, '🟡')
        
        lines = []
        
        # Экранируем спецсимволы Markdown в названии группы
        safe_title = escape_markdown_v2(group_title)
        
        # Заголовок
        lines.append(f"{emoji} **Вас упомянули в группе: {safe_title}**")
        lines.append("")
        
        # Контекст
        context = analysis.get('context_summary', '')
        if context:
            safe_context = escape_markdown_v2(str(context))
            lines.append(f"**Контекст:** {safe_context}")
            lines.append("")
        
        # Причина
        reason = analysis.get('mention_reason', '')
        if reason:
            safe_reason = escape_markdown_v2(str(reason))
            lines.append(f"**Почему упомянули:** {safe_reason}")
            lines.append("")
        
        # Ключевые моменты
        key_points = analysis.get('key_points', [])
        if key_points:
            lines.append("**Ключевые моменты:**")
            for point in key_points:
                safe_point = escape_markdown_v2(str(point))
                lines.append(f"• {safe_point}")
            lines.append("")
        
        # Ссылка на сообщение
        if message_link:
            lines.append(f"[Перейти к сообщению]({message_link})")
            lines.append("")
        
        # Футер
        lines.append(f"*Срочность: {urgency.upper()} • {datetime.now().strftime('%H:%M')}*")
        
        return "\n".join(lines)


# Глобальный экземпляр
group_digest_generator = GroupDigestGenerator()

