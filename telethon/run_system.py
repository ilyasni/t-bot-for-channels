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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelegramSystem:
    def __init__(self):
        self.bot = None
        self.parser_service = None
        self.api_app = None
        self.is_running = False
    
    async def initialize(self):
        """Инициализация всех компонентов системы"""
        try:
            # Создаем таблицы базы данных
            create_tables()
            logger.info("✅ База данных инициализирована")
            
            # Инициализируем парсер
            self.parser_service = ParserService()
            await self.parser_service.initialize()
            logger.info("✅ ParserService инициализирован")
            
            # Инициализируем бота (отключено - запускается отдельно)
            # self.bot = TelegramBot()
            # logger.info("✅ TelegramBot инициализирован")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации системы: {str(e)}")
            return False
    
    def start_bot(self):
        """Запуск бота в отдельном потоке"""
        try:
            logger.info("🤖 Запуск Telegram бота...")
            # Запускаем бота синхронно в отдельном потоке
            self.bot.run()
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
    
    def start_api(self):
        """Запуск API сервера"""
        try:
            from main import app
            host = os.getenv("HOST", "0.0.0.0")
            port = int(os.getenv("PORT", 8010))
            
            logger.info(f"🌐 Запуск API сервера на {host}:{port}...")
            uvicorn.run(app, host=host, port=port)
        except Exception as e:
            logger.error(f"❌ Ошибка запуска API: {str(e)}")
    
    async def start_all(self):
        """Запуск всех компонентов системы"""
        if not await self.initialize():
            return
        
        self.is_running = True
        
        # Бот запускается отдельно через bot_standalone.py
        
        # Запускаем API в отдельном потоке
        api_thread = threading.Thread(target=self.start_api, daemon=True)
        api_thread.start()
        
        # Запускаем парсер в основном потоке
        await self.start_parser()
    
    def stop(self):
        """Остановка системы"""
        self.is_running = False
        if self.parser_service:
            self.parser_service.stop()
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
    print("🚀 Запуск Telegram Channel Parser System...")
    print("=" * 50)
    print("📋 Компоненты системы:")
    print("  🤖 Telegram Bot - управление каналами пользователей")
    print("  🔄 Parser Service - автоматический парсинг постов")
    print("  🌐 API Server - REST API для интеграции с n8n")
    print("  💾 Database - хранение пользователей, каналов и постов")
    print("=" * 50)
    
    asyncio.run(main()) 