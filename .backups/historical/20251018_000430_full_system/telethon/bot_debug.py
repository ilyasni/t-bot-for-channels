#!/usr/bin/env python3
"""Debug запуск бота с детальными логами"""

import logging
import os
from dotenv import load_dotenv

load_dotenv()

# Включаем DEBUG для всех логгеров
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Отключаем лишний шум от httpx
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

from bot import TelegramBot
from database import create_tables

logger.info("="*60)
logger.info("🐛 DEBUG MODE - Запуск бота с детальными логами")
logger.info("="*60)

# Проверяем переменные
logger.info(f"BOT_TOKEN: {'установлен' if os.getenv('BOT_TOKEN') else 'НЕ установлен'}")
logger.info(f"TELEGRAM_DATABASE_URL: {'установлен' if os.getenv('TELEGRAM_DATABASE_URL') else 'НЕ установлен'}")
logger.info(f"MASTER_API_ID: {os.getenv('MASTER_API_ID')}")

# Создаем таблицы
logger.info("Создание таблиц...")
create_tables()
logger.info("✅ Таблицы созданы")

# Создаем бота
logger.info("Создание бота...")
bot = TelegramBot()

# Показываем зарегистрированные handlers
logger.info("="*60)
logger.info("Зарегистрированные handlers:")
for group, handlers in bot.application.handlers.items():
    logger.info(f"  Group {group}: {len(handlers)} handlers")
    for h in handlers[:5]:
        handler_type = type(h).__name__
        logger.info(f"    - {handler_type}")
        if hasattr(h, 'entry_points'):
            logger.info(f"      Entry points: {len(h.entry_points)}")
logger.info("="*60)

# Запускаем
logger.info("🚀 Запуск бота в DEBUG режиме...")
bot.run()

