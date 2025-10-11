#!/usr/bin/env python3
"""
Скрипт миграции для добавления поля tags в таблицу posts
Добавляет колонку tags типа JSON для хранения массива тегов
"""

import logging
import os
import sys
from sqlalchemy import text, inspect
from sqlalchemy.exc import OperationalError

# Добавляем текущую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import engine, SessionLocal
from models import Base, Post
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_column_exists(table_name, column_name):
    """Проверяет существование колонки в таблице"""
    try:
        with engine.connect() as conn:
            inspector = inspect(engine)
            columns = [col['name'] for col in inspector.get_columns(table_name)]
            return column_name in columns
    except Exception as e:
        logger.error(f"❌ Ошибка проверки колонки {column_name}: {str(e)}")
        return False


def get_database_type():
    """Определяет тип базы данных (SQLite или PostgreSQL)"""
    db_url = os.getenv("DATABASE_URL", "sqlite:///./telethon_bot.db")
    if db_url.startswith("postgresql://"):
        return "postgresql"
    else:
        return "sqlite"


def add_tags_column():
    """Добавляет колонку tags в таблицу posts"""
    try:
        if check_column_exists("posts", "tags"):
            logger.info("✅ Колонка tags уже существует")
            return True
        
        db_type = get_database_type()
        logger.info(f"📊 Тип базы данных: {db_type}")
        
        with engine.connect() as conn:
            # Определяем правильный тип колонки для JSON
            if db_type == "postgresql":
                # PostgreSQL поддерживает нативный тип JSON
                column_type = "JSON"
            else:
                # SQLite хранит JSON как TEXT
                column_type = "TEXT"
            
            sql = f"ALTER TABLE posts ADD COLUMN tags {column_type}"
            
            logger.info(f"🔄 Добавление колонки tags с типом {column_type}...")
            conn.execute(text(sql))
            conn.commit()
            
            logger.info("✅ Колонка tags успешно добавлена")
            return True
            
    except Exception as e:
        logger.error(f"❌ Ошибка добавления колонки tags: {str(e)}")
        return False


def verify_migration():
    """Проверяет успешность миграции"""
    logger.info("🔍 Проверка миграции...")
    
    try:
        # Проверяем, что колонка существует
        if not check_column_exists("posts", "tags"):
            logger.error("❌ Колонка tags не найдена после миграции")
            return False
        
        db = SessionLocal()
        
        # Пытаемся прочитать данные с новой колонкой
        post = db.query(Post).first()
        if post:
            # Проверяем доступность нового поля
            _ = post.tags
            logger.info("✅ Миграция прошла успешно - поле tags доступно")
        else:
            logger.info("ℹ️ В базе нет постов для проверки")
        
        db.close()
        return True
            
    except Exception as e:
        logger.error(f"❌ Ошибка проверки миграции: {str(e)}")
        return False


def show_migration_info():
    """Показывает информацию о миграции"""
    logger.info("=" * 70)
    logger.info("📊 Информация о миграции")
    logger.info("=" * 70)
    
    try:
        db = SessionLocal()
        
        # Статистика по постам
        total_posts = db.query(Post).count()
        logger.info(f"📝 Всего постов в базе: {total_posts}")
        
        if check_column_exists("posts", "tags"):
            posts_with_tags = db.query(Post).filter(Post.tags != None).count()
            posts_without_tags = db.query(Post).filter(Post.tags == None).count()
            
            logger.info(f"✅ Постов с тегами: {posts_with_tags}")
            logger.info(f"📭 Постов без тегов: {posts_without_tags}")
        
        db.close()
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения статистики: {str(e)}")
    
    logger.info("=" * 70)


def main():
    """Главная функция миграции"""
    logger.info("🚀 Запуск миграции для добавления системы тегирования")
    logger.info("=" * 70)
    
    try:
        # Шаг 1: Проверка подключения к БД
        logger.info("📊 Шаг 1: Проверка подключения к базе данных...")
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("✅ Подключение к базе данных успешно")
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к БД: {str(e)}")
            return False
        
        # Шаг 2: Добавление колонки tags
        logger.info("📊 Шаг 2: Добавление колонки tags...")
        if not add_tags_column():
            logger.error("❌ Не удалось добавить колонку tags")
            return False
        
        # Шаг 3: Проверка миграции
        logger.info("🔍 Шаг 3: Проверка миграции...")
        if not verify_migration():
            logger.error("❌ Проверка миграции не удалась")
            return False
        
        # Шаг 4: Показываем статистику
        logger.info("📊 Шаг 4: Статистика...")
        show_migration_info()
        
        logger.info("=" * 70)
        logger.info("🎉 Миграция успешно завершена!")
        logger.info("✅ Поле tags добавлено в таблицу posts")
        logger.info("🏷️ Теперь можно использовать систему автоматического тегирования")
        logger.info("")
        logger.info("📋 Следующие шаги:")
        logger.info("  1. Убедитесь, что в .env установлен OPENROUTER_API_KEY")
        logger.info("  2. Установите зависимости: pip install httpx")
        logger.info("  3. Перезапустите систему")
        logger.info("  4. Теги будут автоматически генерироваться при парсинге")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка миграции: {str(e)}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

