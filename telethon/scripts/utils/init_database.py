#!/usr/bin/env python3
"""
Скрипт для инициализации базы данных с новой схемой.
Запустите этот скрипт после удаления старых таблиц в Supabase.
"""

import os
import sys
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Добавляем текущую директорию в путь для импортов
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import create_tables, engine
from models import Base
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Создание всех таблиц в базе данных"""
    try:
        logger.info("🔄 Начинаем создание таблиц в базе данных...")
        
        # Создаем все таблицы
        create_tables()
        
        logger.info("✅ Таблицы успешно созданы!")
        logger.info("📋 Созданные таблицы:")
        
        # Получаем список созданных таблиц
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        for table in tables:
            logger.info(f"  - {table}")
        
        logger.info("🎉 База данных готова к работе!")
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания таблиц: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    print("🚀 Инициализация базы данных...")
    print("=" * 50)
    main()
