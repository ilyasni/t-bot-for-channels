#!/usr/bin/env python3
"""
Скрипт для очистки всех сессий Telegram.
Используйте этот скрипт если Telegram блокирует аутентификацию.
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Добавляем текущую директорию в путь для импортов
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from auth import clear_all_sessions
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Очистка всех сессий"""
    try:
        logger.info("🧹 Начинаем очистку всех сессий...")
        
        # Очищаем все сессии
        result = await clear_all_sessions()
        
        if result:
            logger.info("✅ Все сессии успешно очищены!")
            logger.info("💡 Теперь можно попробовать аутентификацию заново")
        else:
            logger.error("❌ Ошибка очистки сессий")
        
    except Exception as e:
        logger.error(f"❌ Ошибка: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    print("🧹 Очистка сессий Telegram...")
    print("=" * 50)
    asyncio.run(main())
