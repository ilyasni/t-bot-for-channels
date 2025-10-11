#!/usr/bin/env python3
"""
Миграция: Добавление полей для отслеживания статуса тегирования

Дата: 2025-10-11
Описание: Добавляет поля tagging_status, tagging_attempts, last_tagging_attempt, 
          tagging_error в таблицу posts для отслеживания процесса тегирования.

Поля:
- tagging_status: статус тегирования (pending, success, failed, retrying, skipped)
- tagging_attempts: количество попыток тегирования
- last_tagging_attempt: время последней попытки тегирования
- tagging_error: последняя ошибка тегирования

Совместимость: SQLite и PostgreSQL
"""

import os
import sys
import logging
from datetime import datetime, timezone
from pathlib import Path

# Добавляем корневую директорию в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text, inspect
from database import engine, SessionLocal
from models import Base, Post

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_column_exists(table_name: str, column_name: str) -> bool:
    """Проверить существует ли колонка в таблице"""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def migrate_sqlite():
    """Миграция для SQLite"""
    logger.info("🔄 Запуск миграции для SQLite...")
    
    with engine.connect() as conn:
        # Проверяем какие поля уже существуют
        existing_columns = []
        for col in ['tagging_status', 'tagging_attempts', 'last_tagging_attempt', 'tagging_error']:
            if check_column_exists('posts', col):
                existing_columns.append(col)
                logger.info(f"✅ Поле '{col}' уже существует")
        
        # Добавляем недостающие поля
        if 'tagging_status' not in existing_columns:
            conn.execute(text(
                "ALTER TABLE posts ADD COLUMN tagging_status VARCHAR DEFAULT 'pending'"
            ))
            conn.commit()
            logger.info("✅ Добавлено поле: tagging_status")
        
        if 'tagging_attempts' not in existing_columns:
            conn.execute(text(
                "ALTER TABLE posts ADD COLUMN tagging_attempts INTEGER DEFAULT 0"
            ))
            conn.commit()
            logger.info("✅ Добавлено поле: tagging_attempts")
        
        if 'last_tagging_attempt' not in existing_columns:
            conn.execute(text(
                "ALTER TABLE posts ADD COLUMN last_tagging_attempt DATETIME"
            ))
            conn.commit()
            logger.info("✅ Добавлено поле: last_tagging_attempt")
        
        if 'tagging_error' not in existing_columns:
            conn.execute(text(
                "ALTER TABLE posts ADD COLUMN tagging_error TEXT"
            ))
            conn.commit()
            logger.info("✅ Добавлено поле: tagging_error")
    
    logger.info("✅ Миграция SQLite завершена")


def migrate_postgresql():
    """Миграция для PostgreSQL"""
    logger.info("🔄 Запуск миграции для PostgreSQL...")
    
    with engine.connect() as conn:
        # Проверяем какие поля уже существуют
        existing_columns = []
        for col in ['tagging_status', 'tagging_attempts', 'last_tagging_attempt', 'tagging_error']:
            if check_column_exists('posts', col):
                existing_columns.append(col)
                logger.info(f"✅ Поле '{col}' уже существует")
        
        # Добавляем недостающие поля
        if 'tagging_status' not in existing_columns:
            conn.execute(text(
                "ALTER TABLE posts ADD COLUMN tagging_status VARCHAR DEFAULT 'pending'"
            ))
            conn.commit()
            logger.info("✅ Добавлено поле: tagging_status")
        
        if 'tagging_attempts' not in existing_columns:
            conn.execute(text(
                "ALTER TABLE posts ADD COLUMN tagging_attempts INTEGER DEFAULT 0"
            ))
            conn.commit()
            logger.info("✅ Добавлено поле: tagging_attempts")
        
        if 'last_tagging_attempt' not in existing_columns:
            conn.execute(text(
                "ALTER TABLE posts ADD COLUMN last_tagging_attempt TIMESTAMP WITH TIME ZONE"
            ))
            conn.commit()
            logger.info("✅ Добавлено поле: last_tagging_attempt")
        
        if 'tagging_error' not in existing_columns:
            conn.execute(text(
                "ALTER TABLE posts ADD COLUMN tagging_error TEXT"
            ))
            conn.commit()
            logger.info("✅ Добавлено поле: tagging_error")
    
    logger.info("✅ Миграция PostgreSQL завершена")


def update_existing_posts():
    """Обновить статус существующих постов"""
    logger.info("🔄 Обновление статуса существующих постов...")
    
    db = SessionLocal()
    try:
        # Посты с тегами - статус success
        result = db.execute(text(
            "UPDATE posts SET tagging_status = 'success' WHERE tags IS NOT NULL AND tagging_status IS NULL"
        ))
        db.commit()
        logger.info(f"✅ Обновлено {result.rowcount} постов со статусом 'success'")
        
        # Посты без тегов но с текстом - статус pending
        result = db.execute(text(
            "UPDATE posts SET tagging_status = 'pending' WHERE tags IS NULL AND text IS NOT NULL AND tagging_status IS NULL"
        ))
        db.commit()
        logger.info(f"✅ Обновлено {result.rowcount} постов со статусом 'pending'")
        
        # Посты без текста - статус skipped
        result = db.execute(text(
            "UPDATE posts SET tagging_status = 'skipped' WHERE text IS NULL AND tagging_status IS NULL"
        ))
        db.commit()
        logger.info(f"✅ Обновлено {result.rowcount} постов со статусом 'skipped'")
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Ошибка обновления постов: {str(e)}")
        raise
    finally:
        db.close()


def main():
    """Основная функция миграции"""
    try:
        logger.info("=" * 60)
        logger.info("🚀 Миграция: Добавление полей статуса тегирования")
        logger.info("=" * 60)
        
        # Определяем тип БД
        db_url = str(engine.url)
        logger.info(f"📊 База данных: {db_url.split('://')[0]}")
        
        # Выполняем миграцию
        if 'sqlite' in db_url:
            migrate_sqlite()
        elif 'postgresql' in db_url:
            migrate_postgresql()
        else:
            raise Exception(f"Неподдерживаемая БД: {db_url}")
        
        # Обновляем существующие посты
        update_existing_posts()
        
        logger.info("=" * 60)
        logger.info("✅ Миграция успешно завершена!")
        logger.info("=" * 60)
        logger.info("\n📝 Новые возможности:")
        logger.info("  - Отслеживание статуса тегирования постов")
        logger.info("  - Автоматический retry при ошибках")
        logger.info("  - Fallback на альтернативные модели OpenRouter")
        logger.info("  - API endpoints для повторной генерации тегов:")
        logger.info("    GET  /users/{user_id}/posts/tagging_stats")
        logger.info("    POST /users/{user_id}/posts/retry_tagging")
        logger.info("    POST /posts/{post_id}/regenerate_tags")
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка миграции: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

