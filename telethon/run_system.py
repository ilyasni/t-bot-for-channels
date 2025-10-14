import asyncio
import threading
import uvicorn
from fastapi import FastAPI
from bot import TelegramBot
from parser_service import ParserService
from database import create_tables
import logging
import os
from dotenv import load_dotenv

load_dotenv()

# Настройка логирования с поддержкой DEBUG режима
log_level = logging.DEBUG if os.getenv('DEBUG_LOGS', 'false').lower() == 'true' else logging.INFO
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if os.getenv('DEBUG_LOGS', 'false').lower() == 'true':
    logger.info("🐛 DEBUG режим включен для run_system.py")
    logging.getLogger('httpx').setLevel(logging.DEBUG)
else:
    # Отключаем избыточные логи библиотек
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('telethon').setLevel(logging.WARNING)
    logging.getLogger('telegram.ext').setLevel(logging.WARNING)

class TelegramSystem:
    def __init__(self):
        self.bot = None
        self.parser_service = None
        self.group_monitor_service = None
        self.api_app = None
        self.is_running = False
    
    async def initialize(self):
        """Инициализация всех компонентов системы"""
        try:
            # Создаем таблицы базы данных
            create_tables()
            logger.info("✅ База данных инициализирована")
            
            # Инициализируем парсер (многопользовательский режим)
            self.parser_service = ParserService()
            await self.parser_service.initialize()
            logger.info("✅ ParserService инициализирован для многопользовательского режима")
            
            # Инициализируем бота (теперь в том же контейнере!)
            self.bot = TelegramBot()
            logger.info("✅ TelegramBot инициализирован")
            
            # Инициализируем Group Monitor Service
            from group_monitor_service import group_monitor_service
            self.group_monitor_service = group_monitor_service
            logger.info("✅ GroupMonitorService инициализирован")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации системы: {str(e)}")
            return False
    
    async def start_bot(self):
        """Запуск бота (async)"""
        try:
            logger.info("🤖 Запуск Telegram бота...")
            # Запускаем бота в async режиме
            await self.bot.run_async()
        except Exception as e:
            logger.error(f"❌ Ошибка запуска бота: {str(e)}")
    
    async def start_parser(self):
        """Запуск парсера"""
        try:
            interval = int(os.getenv("PARSER_INTERVAL_MINUTES", 30))
            logger.info(f"🔄 Запуск парсера с интервалом {interval} минут...")
            await self.parser_service.start_scheduler(interval)
        except Exception as e:
            logger.error(f"❌ Ошибка запуска парсера: {str(e)}")
    
    async def start_group_monitor(self):
        """Запуск мониторинга групп"""
        try:
            # Задержка чтобы дать боту и парсеру запуститься
            await asyncio.sleep(5)
            
            logger.info("👀 Запуск мониторинга групп...")
            monitors_started = await self.group_monitor_service.start_all_monitors()
            logger.info(f"✅ Мониторинг запущен для {monitors_started} пользователей")
        except Exception as e:
            logger.error(f"❌ Ошибка запуска мониторинга групп: {str(e)}")
    
    def start_api(self, main_loop):
        """
        Запуск API сервера
        
        Args:
            main_loop: Главный event loop где работают Telethon клиенты
        """
        try:
            import main
            
            # КРИТИЧНО: Передаем parser_service И главный event loop в API
            # API работает в отдельном потоке (uvicorn), но должен отправлять задачи в главный loop
            # где живут Telethon клиенты (Context7 best practices)
            main.global_parser_service = self.parser_service
            main.main_event_loop = main_loop
            logger.info("✅ ParserService и главный event loop переданы в API")
            logger.info(f"   Main event loop ID: {id(main_loop)}")
            
            host = os.getenv("HOST", "0.0.0.0")
            port = int(os.getenv("PORT", 8010))
            
            logger.info(f"🌐 Запуск API сервера на {host}:{port}...")
            uvicorn.run(main.app, host=host, port=port)
        except Exception as e:
            logger.error(f"❌ Ошибка запуска API: {str(e)}")
    
    def start_auth_server(self):
        """Запуск веб-сервера аутентификации"""
        try:
            from auth_web_server import app as auth_app
            
            logger.info("🔐 Запуск веб-сервера аутентификации на 0.0.0.0:8001...")
            uvicorn.run(auth_app, host="0.0.0.0", port=8001, log_level="info")
        except Exception as e:
            logger.error(f"❌ Ошибка запуска веб-сервера аутентификации: {str(e)}")
    
    async def start_all(self):
        """Запуск всех компонентов системы"""
        if not await self.initialize():
            return
        
        self.is_running = True
        
        # Запускаем бота в async task (теперь в том же контейнере!)
        asyncio.create_task(self.start_bot())
        logger.info("🤖 Telegram Bot запущен в async task")
        
        # Запускаем Group Monitor в async task
        asyncio.create_task(self.start_group_monitor())
        logger.info("👀 Group Monitor запущен в async task")
        
        # КРИТИЧНО: Получаем текущий event loop (главный loop где работают клиенты)
        main_loop = asyncio.get_running_loop()
        logger.info(f"🔄 Главный event loop ID: {id(main_loop)}")
        
        # Запускаем API в отдельном потоке, передаем главный loop
        # API будет отправлять задачи парсинга обратно в этот loop через run_coroutine_threadsafe
        api_thread = threading.Thread(target=self.start_api, args=(main_loop,), daemon=True)
        api_thread.start()
        
        # Запускаем веб-сервер аутентификации в отдельном потоке
        auth_thread = threading.Thread(target=self.start_auth_server, daemon=True)
        auth_thread.start()
        
        # Запускаем парсер в основном потоке
        await self.start_parser()
    
    def stop(self):
        """Остановка системы"""
        self.is_running = False
        if self.parser_service:
            self.parser_service.stop()
        if self.group_monitor_service:
            asyncio.create_task(self.group_monitor_service.stop_all_monitors())
        logger.info("🛑 Система остановлена")


async def main():
    """Главная функция"""
    system = TelegramSystem()
    
    try:
        await system.start_all()
    except KeyboardInterrupt:
        logger.info("🛑 Получен сигнал остановки...")
        system.stop()
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {str(e)}")
        system.stop()


if __name__ == "__main__":
    print("🚀 Запуск Telegram Channel Parser System (Многопользовательский режим)...")
    print("=" * 70)
    print("📋 Компоненты системы:")
    print("  🤖 Telegram Bot - управление каналами и аутентификация пользователей")
    print("  🔄 Parser Service - автоматический парсинг постов для каждого пользователя")
    print("  🌐 API Server - REST API для интеграции с n8n")
    print("  🔐 Auth Web Server - безопасная веб-аутентификация")
    print("  💾 Database - хранение пользователей, каналов и постов")
    print("  🔐 User Auth Manager - управление персональными клиентами")
    print("=" * 70)
    print("🔐 Каждый пользователь настраивает свои API данные через бота")
    print("📱 Парсинг работает с персональными клиентами пользователей")
    print("=" * 70)
    
    # КРИТИЧНО (Context7 best practices):
    # asyncio.run() вызывается ТОЛЬКО ОДИН РАЗ - это создает главный event loop
    # Все Telethon клиенты будут работать внутри этого loop
    # Согласно Telethon docs: "Only one call to asyncio.run() is needed for the entire application"
    asyncio.run(main()) 