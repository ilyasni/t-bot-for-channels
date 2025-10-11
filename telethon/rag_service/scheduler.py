"""
Планировщик для автоматических дайджестов
Базовая реализация
"""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

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
        days_of_week: str = "mon-sun"
    ):
        """
        Запланировать дайджест для пользователя
        
        Args:
            user_id: ID пользователя
            time: Время отправки (HH:MM)
            days_of_week: Дни недели
        """
        try:
            hour, minute = time.split(":")
            
            trigger = CronTrigger(
                hour=int(hour),
                minute=int(minute),
                day_of_week=days_of_week
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
            
            logger.info(f"📅 Дайджест запланирован для user {user_id} ({time}, {days_of_week})")
            
        except Exception as e:
            logger.error(f"❌ Ошибка планирования дайджеста: {e}")
            raise
    
    async def _send_digest(self, user_id: int):
        """
        Отправить дайджест пользователю
        
        Args:
            user_id: ID пользователя
        """
        try:
            logger.info(f"📧 Отправка дайджеста для user {user_id}")
            # TODO: Реализовать отправку дайджеста через Telegram
            # Это будет реализовано в интеграции с Telegram Bot
        except Exception as e:
            logger.error(f"❌ Ошибка отправки дайджеста: {e}")


# Глобальный экземпляр планировщика
digest_scheduler = DigestScheduler()

