import asyncio
import schedule
import time
import os
from datetime import datetime, timezone, timedelta
from database import SessionLocal
from models import Channel, Post, User
from auth import get_authenticated_users, get_user_client, cleanup_inactive_clients
from telethon.errors import FloodWaitError
import logging
from typing import List
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ParserService:
    def __init__(self):
        self.is_running = False
        self.new_post_ids = []  # Список ID новых постов для тегирования
    
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
        self.new_post_ids = []  # Сбрасываем список новых постов
        
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
            
            # Запускаем фоновое тегирование для новых постов
            if self.new_post_ids:
                logger.info(f"🏷️ ParserService: Запуск тегирования для {len(self.new_post_ids)} новых постов")
                asyncio.create_task(self._tag_new_posts_background())
            
        except Exception as e:
            logger.error(f"❌ ParserService: Общая ошибка парсинга: {str(e)}")
        finally:
            db.close()
    
    async def parse_user_channels(self, user: User, db: SessionLocal) -> int:
        """Парсить каналы конкретного пользователя"""
        client = None
        try:
            # Получаем клиент пользователя
            # Важно: клиент должен быть создан в текущем event loop
            from secure_auth_manager import secure_auth_manager
            
            # Очищаем старый клиент если есть (может быть из другого event loop)
            if user.id in secure_auth_manager.active_clients:
                old_client = secure_auth_manager.active_clients[user.id]
                try:
                    if old_client.is_connected():
                        await old_client.disconnect()
                except:
                    pass
                del secure_auth_manager.active_clients[user.id]
            
            # Создаем новый клиент в текущем event loop
            client = await get_user_client(user)
            if not client:
                logger.warning(f"⚠️ ParserService: Не удалось получить клиент для пользователя {user.telegram_id}")
                return 0
            
            # Проверяем, что клиент подключен
            if not client.is_connected():
                logger.warning(f"⚠️ ParserService: Клиент для пользователя {user.telegram_id} не подключен")
                return 0
            
            # Получаем активные каналы пользователя
            channels = user.get_active_channels(db)
            
            if not channels:
                logger.info(f"📭 ParserService: У пользователя {user.telegram_id} нет активных каналов")
                return 0
            
            logger.info(f"🔄 ParserService: Парсинг {len(channels)} каналов для пользователя {user.telegram_id}")
            
            total_posts = 0
            for channel in channels:
                try:
                    posts_added = await self.parse_channel_posts(channel, user, client, db)
                    total_posts += posts_added
                    if posts_added > 0:
                        logger.info(f"✅ ParserService: @{channel.channel_username} - добавлено {posts_added} постов")
                except FloodWaitError as e:
                    logger.warning(f"⏳ ParserService: Ожидание {e.seconds} сек для @{channel.channel_username}")
                    await asyncio.sleep(e.seconds)
                except Exception as e:
                    error_msg = str(e)
                    if "event loop must not change" in error_msg:
                        logger.error(f"❌ ParserService: Ошибка event loop для @{channel.channel_username} - переподключение клиента")
                        # Попробуем переподключить клиент
                        try:
                            await client.disconnect()
                            await client.connect()
                        except:
                            pass
                    else:
                        logger.error(f"❌ ParserService: Ошибка парсинга @{channel.channel_username}: {error_msg}")
            
            return total_posts
            
        except Exception as e:
            logger.error(f"❌ ParserService: Ошибка парсинга каналов пользователя {user.telegram_id}: {str(e)}")
            return 0
        finally:
            # Очищаем клиент после парсинга чтобы избежать проблем с event loop
            if client:
                try:
                    from secure_auth_manager import secure_auth_manager
                    if user.id in secure_auth_manager.active_clients:
                        try:
                            await client.disconnect()
                        except:
                            pass
                        del secure_auth_manager.active_clients[user.id]
                    logger.debug(f"🧹 ParserService: Клиент пользователя {user.telegram_id} очищен")
                except:
                    pass
    
    async def parse_channel_posts(self, channel: Channel, user, client, db):
        """Парсить посты для конкретного канала с использованием персонального клиента"""
        try:
            # Получаем информацию о подписке пользователя
            subscription = channel.get_user_subscription(db, user)
            if not subscription:
                logger.warning(f"⚠️ ParserService: Пользователь {user.telegram_id} не подписан на канал @{channel.channel_username}")
                return 0
            
            # Получаем последний парсинг для этого пользователя
            last_parsed = subscription['last_parsed_at'] or datetime.now(timezone.utc) - timedelta(hours=24)
            
            # Убеждаемся, что last_parsed имеет timezone
            if last_parsed.tzinfo is None:
                last_parsed = last_parsed.replace(tzinfo=timezone.utc)
            
            # Получаем новые сообщения
            posts_added = 0
            async for message in client.iter_messages(
                f"@{channel.channel_username}",
                limit=50,  # Ограничиваем количество для производительности
                offset_date=datetime.now(timezone.utc),
                reverse=False
            ):
                # Убеждаемся, что message_date имеет timezone
                message_date = message.date
                if message_date.tzinfo is None:
                    message_date = message_date.replace(tzinfo=timezone.utc)
                else:
                    # Если уже есть timezone, конвертируем в UTC
                    message_date = message_date.astimezone(timezone.utc)
                
                # Проверяем, не парсили ли мы уже это сообщение
                if message_date <= last_parsed:
                    break
                
                if message.text:
                    # Проверяем, существует ли уже такой пост (от этого пользователя)
                    existing_post = db.query(Post).filter(
                        Post.user_id == user.id,
                        Post.channel_id == channel.id,
                        Post.telegram_message_id == message.id
                    ).first()
                    
                    if not existing_post:
                        # Формируем URL поста
                        post_url = f"https://t.me/{channel.channel_username}/{message.id}"
                        
                        # Создаем новый пост
                        new_post = Post(
                            user_id=user.id,
                            channel_id=channel.id,
                            telegram_message_id=message.id,
                            text=message.text,
                            views=getattr(message, 'views', None),
                            url=post_url,
                            posted_at=message_date
                        )
                        db.add(new_post)
                        db.flush()  # Получаем ID нового поста
                        self.new_post_ids.append(new_post.id)  # Добавляем ID для тегирования
                        posts_added += 1
            
            # Обновляем время последнего парсинга для этого пользователя
            channel.update_user_subscription(db, user, last_parsed_at=datetime.now(timezone.utc))
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
    
    def schedule_cleanup(self, cleanup_time="03:00"):
        """Настройка расписания очистки постов"""
        schedule.every().day.at(cleanup_time).do(self.run_cleanup)
        logger.info(f"📅 ParserService: Очистка постов запланирована ежедневно в {cleanup_time}")
    
    def run_parsing(self):
        """Запуск парсинга (для schedule)"""
        try:
            # Проверяем, есть ли уже запущенный event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Если event loop уже запущен, создаем задачу
                asyncio.create_task(self.parse_all_channels())
            else:
                # Если event loop не запущен, используем asyncio.run()
                asyncio.run(self.parse_all_channels())
        except RuntimeError:
            # Если не можем получить event loop, создаем новый
            asyncio.run(self.parse_all_channels())
        except Exception as e:
            logger.error(f"❌ ParserService: Ошибка запуска парсинга: {str(e)}")
    
    def run_cleanup(self):
        """Запуск очистки постов (для schedule)"""
        try:
            from cleanup_service import cleanup_service
            
            # Проверяем, есть ли уже запущенный event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Если event loop уже запущен, создаем задачу
                asyncio.create_task(cleanup_service.cleanup_old_posts())
            else:
                # Если event loop не запущен, используем asyncio.run()
                asyncio.run(cleanup_service.cleanup_old_posts())
        except RuntimeError:
            # Если не можем получить event loop, создаем новый
            asyncio.run(cleanup_service.cleanup_old_posts())
        except Exception as e:
            logger.error(f"❌ ParserService: Ошибка запуска очистки: {str(e)}")
    
    async def start_scheduler(self, interval_minutes=30, cleanup_time=None):
        """Запуск планировщика"""
        if not await self.initialize():
            return False
        
        # Настройка расписания парсинга
        self.schedule_parsing(interval_minutes)
        
        # Настройка расписания очистки постов
        if cleanup_time is None:
            cleanup_time = os.getenv("CLEANUP_SCHEDULE_TIME", "03:00")
        self.schedule_cleanup(cleanup_time)
        
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
    
    async def _tag_new_posts_background(self):
        """Фоновая задача для тегирования новых постов"""
        try:
            from tagging_service import tagging_service
            if self.new_post_ids:
                await tagging_service.process_posts_batch(self.new_post_ids)
        except Exception as e:
            logger.error(f"❌ ParserService: Ошибка фонового тегирования: {str(e)}")


# Функция для запуска сервиса
async def run_parser_service(interval_minutes=30):
    """Запуск сервиса парсинга"""
    service = ParserService()
    await service.start_scheduler(interval_minutes)


if __name__ == "__main__":
    # Запуск сервиса парсинга
    asyncio.run(run_parser_service(30))  # Парсинг каждые 30 минут 