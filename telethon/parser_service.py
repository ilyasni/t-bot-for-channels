import asyncio
import schedule
import time
import os
import re
from datetime import datetime, timezone, timedelta
from database import SessionLocal
from models import Channel, Post, User
from auth import get_authenticated_users, cleanup_inactive_clients
from shared_auth_manager import shared_auth_manager
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
            # Получаем клиент пользователя через shared_auth_manager
            # Важно: клиент создается с мастер credentials
            client = await shared_auth_manager.get_user_client(user.telegram_id)
            
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
                    logger.error(f"❌ ParserService: Ошибка парсинга @{channel.channel_username}: {error_msg}")
            
            return total_posts
            
        except Exception as e:
            logger.error(f"❌ ParserService: Ошибка парсинга каналов пользователя {user.telegram_id}: {str(e)}")
            return 0
        # НЕ УДАЛЯЕМ клиент! Он должен оставаться в том же event loop для последующих парсингов
    
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
                        
                        # Обогащаем пост контентом ссылок (если включено)
                        await self._enrich_post_with_links(new_post, db)
            
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
        # Сохраняем ID новых постов перед парсингом
        new_post_ids_before = list(self.new_post_ids) if hasattr(self, 'new_post_ids') else []
        
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"error": "Пользователь не найден"}
            
            if not user.is_authenticated:
                return {"error": "Пользователь не аутентифицирован"}
            
            posts_added = await self.parse_user_channels(user, db)
            
            # Запускаем фоновое тегирование для новых постов (как в parse_all_channels)
            if self.new_post_ids and len(self.new_post_ids) > len(new_post_ids_before):
                new_posts_count = len(self.new_post_ids) - len(new_post_ids_before)
                logger.info(f"🏷️ ParserService: Запуск тегирования для {new_posts_count} новых постов")
                asyncio.create_task(self._tag_new_posts_background())
            
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
            # КРИТИЧНО: НЕ используем asyncio.run() - это создает НОВЫЙ event loop!
            # Telethon клиенты должны работать в ТОМ ЖЕ event loop где были созданы
            # Просто создаем задачу в текущем running loop
            loop = asyncio.get_running_loop()
            asyncio.create_task(self.parse_all_channels())
            logger.debug("📅 ParserService: Задача парсинга создана в текущем event loop")
        except RuntimeError:
            # Если loop не запущен - логируем ошибку, schedule должен работать внутри loop!
            logger.error("❌ ParserService: ОШИБКА! run_parsing() вызван ВНЕ event loop. Это не должно происходить!")
        except Exception as e:
            logger.error(f"❌ ParserService: Ошибка запуска парсинга: {str(e)}")
    
    def run_cleanup(self):
        """Запуск очистки постов (для schedule)"""
        try:
            from cleanup_service import cleanup_service
            
            # КРИТИЧНО: НЕ используем asyncio.run() - работаем в текущем running loop
            loop = asyncio.get_running_loop()
            asyncio.create_task(cleanup_service.cleanup_old_posts())
            logger.debug("📅 ParserService: Задача очистки создана в текущем event loop")
        except RuntimeError:
            logger.error("❌ ParserService: ОШИБКА! run_cleanup() вызван ВНЕ event loop. Это не должно происходить!")
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
                
                # Уведомляем RAG-сервис о новых постах для индексации
                await self._notify_rag_service(self.new_post_ids)
        except Exception as e:
            logger.error(f"❌ ParserService: Ошибка фонового тегирования: {str(e)}")
    
    def _extract_urls(self, text: str) -> List[str]:
        """
        Извлечение URL из текста поста
        
        Args:
            text: Текст поста
            
        Returns:
            Список найденных URL
        """
        if not text:
            return []
        
        # Regex для поиска URL
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, text)
        return urls
    
    async def _enrich_post_with_links(self, post: Post, db: SessionLocal):
        """
        Обогащение поста контентом из ссылок через Crawl4AI
        
        Args:
            post: Объект Post
            db: Сессия базы данных
        """
        crawl4ai_enabled = os.getenv("CRAWL4AI_ENABLED", "false").lower() == "true"
        
        if not crawl4ai_enabled:
            return
        
        urls = self._extract_urls(post.text)
        if not urls:
            return
        
        # Берем первую ссылку для обогащения
        url = urls[0]
        crawl4ai_url = os.getenv("CRAWL4AI_URL", "http://crawl4ai:11235")
        word_threshold = int(os.getenv("CRAWL4AI_WORD_THRESHOLD", "100"))
        timeout = float(os.getenv("CRAWL4AI_TIMEOUT", "30"))
        
        try:
            import httpx
            
            async with httpx.AsyncClient(timeout=timeout) as client:
                # Правильный формат API: urls как массив
                response = await client.post(
                    f"{crawl4ai_url}/crawl",
                    json={
                        "urls": [url]  # Массив URL, не одна строка!
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Проверяем успешность и наличие результатов
                    if result.get("success") and result.get("results"):
                        first_result = result["results"][0]
                        
                        # markdown - это словарь с разными форматами
                        markdown_data = first_result.get("markdown", {})
                        
                        # Используем raw_markdown для извлечения текста
                        content = ""
                        if isinstance(markdown_data, dict):
                            content = markdown_data.get("raw_markdown", "")
                        elif isinstance(markdown_data, str):
                            content = markdown_data
                        
                        # Проверяем минимальную длину контента
                        if content and len(content) >= word_threshold:
                            # Добавляем обогащенный контент к посту (ограничиваем 3000 символов)
                            post.enriched_content = f"{post.text}\n\n[Содержимое ссылки: {url}]\n{content[:3000]}"
                            db.commit()
                            logger.info(f"✅ ParserService: Пост {post.id} обогащен контентом ссылки {url} ({len(content)} символов)")
                        else:
                            logger.debug(f"ParserService: Ссылка {url} не содержит достаточно контента ({len(content)} символов < {word_threshold})")
                    else:
                        logger.warning(f"⚠️ ParserService: Crawl4AI не вернул результаты для {url}")
                else:
                    logger.warning(f"⚠️ ParserService: Crawl4AI вернул статус {response.status_code} для {url}")
                    
        except httpx.TimeoutException:
            logger.warning(f"⏳ ParserService: Timeout при извлечении контента из {url}")
        except httpx.ConnectError:
            logger.warning(f"🔌 ParserService: Crawl4AI недоступен")
        except Exception as e:
            logger.error(f"❌ ParserService: Ошибка обогащения поста {post.id}: {e}")
    
    async def _notify_rag_service(self, post_ids: List[int]):
        """
        Уведомление RAG-сервиса о новых постах для индексации
        
        Args:
            post_ids: Список ID новых постов
        """
        try:
            import httpx
            rag_service_url = os.getenv("RAG_SERVICE_URL", "http://rag-service:8020")
            rag_enabled = os.getenv("RAG_SERVICE_ENABLED", "true").lower() == "true"
            
            if not rag_enabled or not post_ids:
                return
            
            # Пробуем уведомить RAG-сервис с retry
            max_retries = 3
            retry_delay = 2.0  # секунды
            
            for attempt in range(max_retries):
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        response = await client.post(
                            f"{rag_service_url}/rag/index/batch",
                            json={"post_ids": post_ids}
                        )
                        
                        if response.status_code == 200:
                            logger.info(f"✅ ParserService: RAG-сервис уведомлен о {len(post_ids)} новых постах")
                            return  # Успех
                        elif response.status_code >= 500:
                            # Server error - можно retry
                            if attempt < max_retries - 1:
                                logger.warning(f"⚠️ ParserService: RAG-сервис вернул {response.status_code}, retry {attempt+1}/{max_retries}")
                                await asyncio.sleep(retry_delay * (attempt + 1))
                                continue
                            else:
                                logger.error(f"❌ ParserService: RAG-сервис недоступен после {max_retries} попыток")
                        else:
                            # Client error - не retry
                            logger.warning(f"⚠️ ParserService: RAG-сервис вернул статус {response.status_code}: {response.text[:200]}")
                            return
                            
                except httpx.TimeoutException:
                    if attempt < max_retries - 1:
                        logger.warning(f"⏳ ParserService: Timeout RAG-сервиса, retry {attempt+1}/{max_retries}")
                        await asyncio.sleep(retry_delay * (attempt + 1))
                        continue
                    else:
                        logger.error(f"❌ ParserService: RAG-сервис timeout после {max_retries} попыток")
                except httpx.ConnectError:
                    if attempt < max_retries - 1:
                        logger.warning(f"🔌 ParserService: RAG-сервис недоступен, retry {attempt+1}/{max_retries}")
                        await asyncio.sleep(retry_delay * (attempt + 1))
                        continue
                    else:
                        logger.error(f"❌ ParserService: Невозможно подключиться к RAG-сервису после {max_retries} попыток")
            
            # Если все попытки неудачны, сохраняем в БД для последующей индексации
            db = SessionLocal()
            try:
                # Помечаем посты как pending для индексации
                from models import IndexingStatus
                for post_id in post_ids:
                    post = db.query(Post).filter(Post.id == post_id).first()
                    if post:
                        existing = db.query(IndexingStatus).filter(
                            IndexingStatus.user_id == post.user_id,
                            IndexingStatus.post_id == post_id
                        ).first()
                        
                        if not existing:
                            status = IndexingStatus(
                                user_id=post.user_id,
                                post_id=post_id,
                                status="pending",
                                error="RAG service unavailable during parsing"
                            )
                            db.add(status)
                
                db.commit()
                logger.info(f"💾 ParserService: {len(post_ids)} постов помечены как pending для индексации")
            except Exception as db_err:
                logger.error(f"❌ ParserService: Ошибка сохранения pending статуса: {db_err}")
                db.rollback()
            finally:
                db.close()
                    
        except Exception as e:
            logger.error(f"❌ ParserService: Критическая ошибка уведомления RAG-сервиса: {e}")
            # Не прерываем работу парсера из-за ошибки RAG-сервиса


# Функция для запуска сервиса
async def run_parser_service(interval_minutes=30):
    """
    Запуск сервиса парсинга
    
    ВАЖНО: Согласно Context7 Telethon best practices:
    - asyncio.run() должен вызываться ТОЛЬКО ОДИН РАЗ для всего приложения
    - Telethon клиенты НЕ МОГУТ работать если event loop изменился после подключения
    - Все операции должны выполняться внутри одного event loop
    """
    service = ParserService()
    await service.start_scheduler(interval_minutes)


if __name__ == "__main__":
    # КРИТИЧНО: asyncio.run() вызывается ОДИН РАЗ для создания главного event loop
    # Все Telethon клиенты будут созданы и работать внутри этого loop
    # Согласно Context7: "Only one call to asyncio.run() is needed for the entire application"
    asyncio.run(run_parser_service(30))  # Парсинг каждые 30 минут 