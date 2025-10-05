import asyncio
import schedule
import time
from datetime import datetime, timezone, timedelta
from database import SessionLocal
from models import Channel, Post
from auth import get_client
from telethon.errors import FloodWaitError
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ParserService:
    def __init__(self):
        self.client = None
        self.is_running = False
    
    async def initialize(self):
        """Инициализация клиента Telegram"""
        try:
            # Используем улучшенную функцию get_client с настройками повторных попыток
            self.client = await get_client(max_retries=3, base_delay=5)
            
            if self.client and self.client.is_connected():
                logger.info("✅ ParserService: Успешное подключение к Telegram")
                return True
            else:
                logger.error("❌ ParserService: Не удалось подключиться к Telegram")
                return False
                
        except Exception as e:
            logger.error(f"❌ ParserService: Ошибка подключения к Telegram: {str(e)}")
            return False
    
    async def parse_all_channels(self):
        """Парсить все активные каналы"""
        if not self.client or not self.client.is_connected():
            logger.error("❌ ParserService: Telegram client не подключен")
            return
        
        db = SessionLocal()
        try:
            # Получаем все активные каналы
            channels = db.query(Channel).filter(Channel.is_active == True).all()
            
            if not channels:
                logger.info("📭 ParserService: Нет активных каналов для парсинга")
                return
            
            logger.info(f"🔄 ParserService: Начинаем парсинг {len(channels)} каналов")
            
            total_posts = 0
            for channel in channels:
                try:
                    posts_added = await self.parse_channel_posts(channel, db)
                    total_posts += posts_added
                    if posts_added > 0:
                        logger.info(f"✅ ParserService: @{channel.channel_username} - добавлено {posts_added} постов")
                except FloodWaitError as e:
                    logger.warning(f"⏳ ParserService: Ожидание {e.seconds} сек для @{channel.channel_username}")
                    await asyncio.sleep(e.seconds)
                except Exception as e:
                    logger.error(f"❌ ParserService: Ошибка парсинга @{channel.channel_username}: {str(e)}")
            
            logger.info(f"✅ ParserService: Парсинг завершен. Всего добавлено {total_posts} постов")
            
        except Exception as e:
            logger.error(f"❌ ParserService: Общая ошибка парсинга: {str(e)}")
        finally:
            db.close()
    
    async def parse_channel_posts(self, channel: Channel, db):
        """Парсить посты для конкретного канала"""
        try:
            # Получаем последний парсинг
            last_parsed = channel.last_parsed_at or datetime.now(timezone.utc) - timedelta(hours=24)
            
            # Получаем новые сообщения
            posts_added = 0
            async for message in self.client.iter_messages(
                f"@{channel.channel_username}",
                limit=50,  # Ограничиваем количество для производительности
                offset_date=datetime.now(timezone.utc),
                reverse=False
            ):
                message_date = message.date.replace(tzinfo=timezone.utc)
                
                # Проверяем, не парсили ли мы уже это сообщение
                if message_date <= last_parsed:
                    break
                
                if message.text:
                    # Проверяем, существует ли уже такой пост
                    existing_post = db.query(Post).filter(
                        Post.user_id == channel.user_id,
                        Post.channel_id == channel.id,
                        Post.telegram_message_id == message.id
                    ).first()
                    
                    if not existing_post:
                        # Формируем URL поста
                        post_url = f"https://t.me/{channel.channel_username}/{message.id}"
                        
                        # Создаем новый пост
                        new_post = Post(
                            user_id=channel.user_id,
                            channel_id=channel.id,
                            telegram_message_id=message.id,
                            text=message.text,
                            views=getattr(message, 'views', None),
                            url=post_url,
                            posted_at=message_date
                        )
                        db.add(new_post)
                        posts_added += 1
            
            # Обновляем время последнего парсинга
            channel.last_parsed_at = datetime.now(timezone.utc)
            db.commit()
            
            return posts_added
            
        except Exception as e:
            db.rollback()
            raise e
    
    def schedule_parsing(self, interval_minutes=30):
        """Настройка расписания парсинга"""
        schedule.every(interval_minutes).minutes.do(self.run_parsing)
        logger.info(f"📅 ParserService: Парсинг запланирован каждые {interval_minutes} минут")
    
    def run_parsing(self):
        """Запуск парсинга (для schedule)"""
        asyncio.run(self.parse_all_channels())
    
    async def start_scheduler(self, interval_minutes=30):
        """Запуск планировщика"""
        if not await self.initialize():
            return False
        
        self.schedule_parsing(interval_minutes)
        self.is_running = True
        
        logger.info("🚀 ParserService: Планировщик запущен")
        
        while self.is_running:
            schedule.run_pending()
            await asyncio.sleep(60)  # Проверяем каждую минуту
    
    def stop(self):
        """Остановка сервиса"""
        self.is_running = False
        logger.info("🛑 ParserService: Сервис остановлен")


# Функция для запуска сервиса
async def run_parser_service(interval_minutes=30):
    """Запуск сервиса парсинга"""
    service = ParserService()
    await service.start_scheduler(interval_minutes)


if __name__ == "__main__":
    # Запуск сервиса парсинга
    asyncio.run(run_parser_service(30))  # Парсинг каждые 30 минут 