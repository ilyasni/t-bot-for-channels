"""
Планировщик для автоматических дайджестов
Базовая реализация
"""
import logging
import os
import sys
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
import httpx
import pytz

# Добавляем родительскую директорию в path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import SessionLocal
from models import DigestSettings

logger = logging.getLogger(__name__)


class DigestScheduler:
    """Планировщик дайджестов"""
    
    def __init__(self):
        """Инициализация планировщика"""
        self.scheduler = AsyncIOScheduler()
        logger.info("✅ Digest Scheduler инициализирован")
    
    def start(self):
        """Запустить планировщик"""
        try:
            if not self.scheduler.running:
                self.scheduler.start()
                logger.info("🕐 Digest Scheduler запущен")
        except Exception as e:
            logger.error(f"❌ Ошибка запуска планировщика: {e}")
    
    def stop(self):
        """Остановить планировщик"""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown()
                logger.info("🛑 Digest Scheduler остановлен")
        except Exception as e:
            logger.error(f"❌ Ошибка остановки планировщика: {e}")
    
    async def schedule_digest(
        self,
        user_id: int,
        time: str = "09:00",
        days_of_week: str = "mon-sun",
        timezone: str = "Europe/Moscow"
    ):
        """
        Запланировать дайджест для пользователя
        
        Args:
            user_id: ID пользователя
            time: Время отправки (HH:MM)
            days_of_week: Дни недели
            timezone: Часовой пояс (например, 'Europe/Moscow')
        """
        try:
            hour, minute = time.split(":")
            
            # Создаем timezone объект
            tz = pytz.timezone(timezone)
            
            trigger = CronTrigger(
                hour=int(hour),
                minute=int(minute),
                day_of_week=days_of_week,
                timezone=tz
            )
            
            job_id = f"digest_user_{user_id}"
            
            # Удаляем существующее задание если есть
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
            
            # Добавляем новое задание
            self.scheduler.add_job(
                self._send_digest,
                trigger=trigger,
                id=job_id,
                args=[user_id],
                replace_existing=True
            )
            
            logger.info(f"📅 Дайджест запланирован для user {user_id} ({time} {timezone}, {days_of_week})")
            
        except Exception as e:
            logger.error(f"❌ Ошибка планирования дайджеста: {e}")
            raise
    
    async def _send_digest(self, user_id: int):
        """
        Отправить дайджест пользователю
        
        Args:
            user_id: ID пользователя
        """
        db = SessionLocal()
        
        try:
            logger.info(f"📧 Генерация и отправка дайджеста для user {user_id}")
            
            # Получаем настройки дайджеста из БД
            settings = db.query(DigestSettings).filter(
                DigestSettings.user_id == user_id
            ).first()
            
            if not settings or not settings.enabled:
                logger.warning(f"⚠️ Дайджест отключен или не найден для user {user_id}")
                return
            
            # Определяем период для дайджеста
            now = datetime.now(pytz.timezone(settings.timezone))
            
            if settings.frequency == "daily":
                date_from = now - timedelta(days=1)
            elif settings.frequency == "weekly":
                date_from = now - timedelta(days=7)
            else:
                date_from = now - timedelta(days=1)
            
            date_to = now
            
            # Вызываем RAG Service для генерации дайджеста
            rag_url = os.getenv("RAG_SERVICE_URL", "http://localhost:8020")
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                try:
                    # Генерация AI-дайджеста
                    response = await client.post(
                        f"{rag_url}/rag/digest/generate",
                        json={
                            "user_id": user_id,
                            "date_from": date_from.isoformat(),
                            "date_to": date_to.isoformat(),
                            "preferred_topics": settings.preferred_topics,
                            "topics_limit": settings.topics_limit or 5,
                            "summary_style": settings.summary_style or "concise",
                            "format": settings.format or "markdown",
                            "max_posts": settings.max_posts or 200,
                            "channels": settings.channels,
                            "tags": settings.tags
                        }
                    )
                    
                    if response.status_code != 200:
                        logger.error(f"❌ Ошибка генерации дайджеста: {response.status_code} - {response.text[:200]}")
                        return
                    
                    result = response.json()
                    digest_text = result.get("digest", "")
                    
                    if not digest_text:
                        logger.warning(f"⚠️ Пустой дайджест для user {user_id}")
                        return
                    
                except httpx.TimeoutException:
                    logger.error(f"❌ Timeout при генерации дайджеста для user {user_id}")
                    return
                except Exception as e:
                    logger.error(f"❌ Ошибка вызова RAG service: {e}")
                    return
            
            # Отправка через Telegram Bot
            bot_token = os.getenv("BOT_TOKEN")
            
            if not bot_token:
                logger.error("❌ BOT_TOKEN не найден в переменных окружения")
                return
            
            # Получаем telegram_id пользователя из БД
            from models import User
            user = db.query(User).filter(User.id == user_id).first()
            
            if not user:
                logger.error(f"❌ Пользователь {user_id} не найден в БД")
                return
            
            telegram_id = user.telegram_id
            
            # Отправка через Telegram Bot API с retry механизмом
            max_retries = 3
            retry_delay = 2  # секунды
            
            for attempt in range(max_retries):
                try:
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        # Разбиваем длинный дайджест на части (макс 4096 символов в Telegram)
                        max_length = 4000  # Оставляем запас
                        
                        if len(digest_text) <= max_length:
                            messages = [digest_text]
                        else:
                            # Разбиваем по параграфам
                            messages = []
                            current_message = ""
                            
                            for line in digest_text.split("\n"):
                                if len(current_message) + len(line) + 1 <= max_length:
                                    current_message += line + "\n"
                                else:
                                    if current_message:
                                        messages.append(current_message)
                                    current_message = line + "\n"
                            
                            if current_message:
                                messages.append(current_message)
                        
                        # Отправляем все части
                        for i, message in enumerate(messages):
                            response = await client.post(
                                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                                json={
                                    "chat_id": telegram_id,
                                    "text": message,
                                    "parse_mode": "HTML",  # Всегда HTML, форматирование в digest_generator
                                    "disable_web_page_preview": True
                                }
                            )
                            
                            if response.status_code != 200:
                                logger.error(f"❌ Ошибка отправки дайджеста в Telegram: {response.status_code} - {response.text[:200]}")
                                raise Exception(f"Telegram API returned {response.status_code}")
                            
                            logger.info(f"✅ Часть {i+1}/{len(messages)} дайджеста отправлена user {user_id}")
                        
                        # Успешная отправка - выходим из retry loop
                        break
                        
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"⚠️ Попытка {attempt + 1}/{max_retries} не удалась: {e}. Повтор через {retry_delay} сек...")
                        import asyncio
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        logger.error(f"❌ Все {max_retries} попытки отправки дайджеста провалились: {e}")
                        return
            
            # Обновляем last_sent_at в БД
            settings.last_sent_at = datetime.now(pytz.UTC)
            
            # Вычисляем next_scheduled_at
            job_id = f"digest_user_{user_id}"
            job = self.scheduler.get_job(job_id)
            
            if job and job.next_run_time:
                settings.next_scheduled_at = job.next_run_time
            
            db.commit()
            
            logger.info(f"✅ Дайджест успешно отправлен user {user_id} (telegram_id: {telegram_id})")
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки дайджеста для user {user_id}: {e}", exc_info=True)
            db.rollback()
        finally:
            db.close()


# Глобальный экземпляр планировщика
digest_scheduler = DigestScheduler()

