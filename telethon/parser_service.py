import asyncio
import schedule
import time
from datetime import datetime, timezone, timedelta
from database import SessionLocal
from models import Channel, Post, User
from auth import get_authenticated_users, get_user_client, cleanup_inactive_clients
from telethon.errors import FloodWaitError
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ParserService:
    def __init__(self):
        self.is_running = False
    
    async def initialize(self):
        """Инициализация сервиса парсинга"""
        try:
            logger.info("✅ ParserService: Сервис инициализирован для многопользовательского режима")
            return True
        except Exception as e:
            logger.error(f"❌ ParserService: Ошибка инициализации: {str(e)}")
            return False
    
    async def parse_all_channels(self):
        """Парсить все активные каналы для всех аутентифицированных пользователей"""
        db = SessionLocal()
        try:
            # Получаем всех аутентифицированных пользователей
            authenticated_users = await get_authenticated_users(db)
            
            if not authenticated_users:
                logger.info("📭 ParserService: Нет аутентифицированных пользователей для парсинга")
                return
            
            logger.info(f"🔄 ParserService: Начинаем парсинг для {len(authenticated_users)} пользователей")
            
            total_posts = 0
            for user in authenticated_users:
                try:
                    user_posts = await self.parse_user_channels(user, db)
                    total_posts += user_posts
                    if user_posts > 0:
                        logger.info(f"✅ ParserService: Пользователь {user.telegram_id} - добавлено {user_posts} постов")
                except Exception as e:
                    logger.error(f"❌ ParserService: Ошибка парсинга для пользователя {user.telegram_id}: {str(e)}")
            
            logger.info(f"✅ ParserService: Парсинг завершен. Всего добавлено {total_posts} постов")
            
        except Exception as e:
            logger.error(f"❌ ParserService: Общая ошибка парсинга: {str(e)}")
        finally:
            db.close()
    
    async def parse_user_channels(self, user: User, db: SessionLocal) -> int:
        """Парсить каналы конкретного пользователя"""
        try:
            # Получаем клиент пользователя
            client = await get_user_client(user)
            if not client:
                logger.warning(f"⚠️ ParserService: Не удалось получить клиент для пользователя {user.telegram_id}")
                return 0
            
            # Получаем каналы пользователя
            channels = db.query(Channel).filter(
                Channel.user_id == user.id,
                Channel.is_active == True
            ).all()
            
            if not channels:
                logger.info(f"📭 ParserService: У пользователя {user.telegram_id} нет активных каналов")
                return 0
            
            logger.info(f"🔄 ParserService: Парсинг {len(channels)} каналов для пользователя {user.telegram_id}")
            
            total_posts = 0
            for channel in channels:
                try:
                    posts_added = await self.parse_channel_posts(channel, client, db)
                    total_posts += posts_added
                    if posts_added > 0:
                        logger.info(f"✅ ParserService: @{channel.channel_username} - добавлено {posts_added} постов")
                except FloodWaitError as e:
                    logger.warning(f"⏳ ParserService: Ожидание {e.seconds} сек для @{channel.channel_username}")
                    await asyncio.sleep(e.seconds)
                except Exception as e:
                    logger.error(f"❌ ParserService: Ошибка парсинга @{channel.channel_username}: {str(e)}")
            
            return total_posts
            
        except Exception as e:
            logger.error(f"❌ ParserService: Ошибка парсинга каналов пользователя {user.telegram_id}: {str(e)}")
            return 0
    
    async def parse_channel_posts(self, channel: Channel, client, db):
        """Парсить посты для конкретного канала с использованием персонального клиента"""
        try:
            # Получаем последний парсинг
            last_parsed = channel.last_parsed_at or datetime.now(timezone.utc) - timedelta(hours=24)
            
            # Получаем новые сообщения
            posts_added = 0
            async for message in client.iter_messages(
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
    
    async def parse_user_channels_by_id(self, user_id: int) -> dict:
        """Парсить каналы конкретного пользователя по ID"""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"error": "Пользователь не найден"}
            
            if not user.is_authenticated:
                return {"error": "Пользователь не аутентифицирован"}
            
            posts_added = await self.parse_user_channels(user, db)
            return {
                "user_id": user.id,
                "telegram_id": user.telegram_id,
                "posts_added": posts_added,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"❌ ParserService: Ошибка парсинга пользователя {user_id}: {str(e)}")
            return {"error": str(e)}
        finally:
            db.close()
    
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
            # Очищаем неактивные клиенты каждые 10 минут
            if int(time.time()) % 600 == 0:
                await cleanup_inactive_clients()
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