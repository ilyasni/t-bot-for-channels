#!/usr/bin/env python3
"""
Отдельный скрипт для запуска Telegram бота
Этот скрипт запускает только бота, без API сервера и парсера
"""

import asyncio
import logging
import os
import sys
from dotenv import load_dotenv

# Добавляем текущую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bot import TelegramBot
from database import create_tables

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Главная функция для запуска бота"""
    logger.info("🤖 Запуск Telegram бота (standalone)")
    logger.info("=" * 50)
    
    # Проверяем наличие BOT_TOKEN
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token or bot_token == "your_bot_token_here":
        logger.error("❌ BOT_TOKEN не установлен в .env файле")
        logger.info("💡 Получите токен у @BotFather и добавьте в .env файл")
        return
    
    try:
        # Создаем таблицы базы данных
        logger.info("📊 Инициализация базы данных...")
        create_tables()
        logger.info("✅ База данных готова")
        
        # Создаем и запускаем бота
        logger.info("🤖 Инициализация Telegram бота...")
        bot = TelegramBot()
        
        logger.info("🚀 Запуск бота...")
        logger.info("💡 Найдите вашего бота в Telegram и отправьте /start")
        
        # Запускаем бота
        bot.run()
        
    except KeyboardInterrupt:
        logger.info("🛑 Получен сигнал остановки...")
    except Exception as e:
        logger.error(f"❌ Ошибка запуска бота: {str(e)}")
        logger.info("💡 Проверьте:")
        logger.info("   1. Правильность BOT_TOKEN в .env файле")
        logger.info("   2. Интернет-соединение")
        logger.info("   3. Что бот создан у @BotFather")

if __name__ == "__main__":
    main()
