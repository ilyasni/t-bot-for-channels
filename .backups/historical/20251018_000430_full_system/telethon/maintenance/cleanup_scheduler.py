"""
Cleanup Scheduler
APScheduler job для автоматической очистки данных

Best practices:
- Запуск в off-peak hours (3:00 AM)
- Logging + alerts при ошибках
- Graceful shutdown
"""
import logging
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from maintenance.unified_retention_service import unified_retention_service

logger = logging.getLogger(__name__)


class CleanupScheduler:
    """
    Scheduler для автоматической очистки данных
    
    Usage:
        ```python
        scheduler = CleanupScheduler()
        scheduler.start()
        
        # В shutdown event
        scheduler.stop()
        ```
    """
    
    def __init__(self):
        """Инициализация scheduler"""
        self.scheduler = AsyncIOScheduler()
        self.enabled = os.getenv("CLEANUP_ENABLED", "false").lower() == "true"
        
        # Cron schedule (default: 3:00 AM daily)
        self.schedule = os.getenv("CLEANUP_SCHEDULE", "0 3 * * *")
        
        logger.info(f"📅 CleanupScheduler initialized (enabled: {self.enabled})")
        logger.info(f"   Schedule: {self.schedule}")
    
    def start(self):
        """
        Запустить scheduler
        
        Добавляет job и запускает scheduler
        """
        if not self.enabled:
            logger.info("⚠️ Cleanup scheduler disabled (CLEANUP_ENABLED=false)")
            return
        
        try:
            # Добавить job
            self.scheduler.add_job(
                self._scheduled_cleanup,
                trigger=CronTrigger.from_crontab(self.schedule),
                id='data_retention_cleanup',
                name='Data Retention Cleanup',
                replace_existing=True,
                max_instances=1,  # Только одна инстанция одновременно
                coalesce=True  # Если пропущен запуск, выполнить только один раз
            )
            
            # Запустить scheduler
            self.scheduler.start()
            
            logger.info(f"✅ Cleanup scheduler started (schedule: {self.schedule})")
            
        except Exception as e:
            logger.error(f"❌ Failed to start cleanup scheduler: {e}", exc_info=True)
    
    def stop(self):
        """
        Остановить scheduler
        
        Вызывать при shutdown приложения
        """
        if self.scheduler.running:
            try:
                self.scheduler.shutdown(wait=True)
                logger.info("✅ Cleanup scheduler stopped")
            except Exception as e:
                logger.error(f"❌ Cleanup scheduler stop error: {e}")
    
    async def _scheduled_cleanup(self):
        """
        Запланированный cleanup
        
        Вызывается по расписанию (default: 3:00 AM daily)
        """
        logger.info("🕒 Starting scheduled unified cleanup (3:00 AM)")
        
        try:
            # Выполнить unified cleanup (реальное удаление)
            result = await unified_retention_service.cleanup_all_users(dry_run=False)
            
            # Log results
            total_deleted = result.get('total_posts_deleted', 0)
            users_processed = result.get('users_processed', 0)
            errors = result.get('errors', [])
            
            logger.info(f"🧹 Unified cleanup result:")
            logger.info(f"   Users processed: {users_processed}")
            logger.info(f"   Total posts deleted: {total_deleted}")
            
            # Alert if errors
            if errors:
                logger.error(f"⚠️ Cleanup errors: {errors}")
                # TODO: Send alert (email, Slack, etc.)
            else:
                logger.info("✅ Unified cleanup completed successfully")
                
        except Exception as e:
            logger.error(f"❌ Scheduled unified cleanup failed: {e}", exc_info=True)
            # TODO: Send critical alert


# Singleton instance
cleanup_scheduler = CleanupScheduler()

