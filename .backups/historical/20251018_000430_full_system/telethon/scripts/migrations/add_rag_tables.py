#!/usr/bin/env python3
"""
Миграция БД: Добавление таблиц для RAG-системы

Добавляет:
- digest_settings - настройки дайджестов пользователей
- indexing_status - статус индексации постов в Qdrant

Использование:
    python scripts/migrations/add_rag_tables.py

Автор: RAG System
Дата: 2025-01-11
"""

import os
import sys
from datetime import datetime, timezone
import logging

# Добавляем корневую директорию в path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from sqlalchemy import create_engine, text, inspect
from database import SessionLocal, engine
from models import Base, User, Channel, Post

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_table_exists(engine, table_name: str) -> bool:
    """Проверить существование таблицы"""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def create_digest_settings_table(engine):
    """Создать таблицу digest_settings"""
    
    # SQL для SQLite
    sqlite_sql = """
    CREATE TABLE IF NOT EXISTS digest_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        enabled BOOLEAN DEFAULT 0,
        frequency VARCHAR DEFAULT 'daily',
        time VARCHAR DEFAULT '09:00',
        days_of_week TEXT,
        timezone VARCHAR DEFAULT 'Europe/Moscow',
        channels TEXT,
        tags TEXT,
        format VARCHAR DEFAULT 'markdown',
        max_posts INTEGER DEFAULT 20,
        delivery_method VARCHAR DEFAULT 'telegram',
        email VARCHAR,
        last_sent_at TIMESTAMP,
        next_scheduled_at TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """
    
    # SQL для PostgreSQL
    postgres_sql = """
    CREATE TABLE IF NOT EXISTS digest_settings (
        id SERIAL PRIMARY KEY,
        user_id INTEGER UNIQUE NOT NULL,
        enabled BOOLEAN DEFAULT FALSE,
        frequency VARCHAR DEFAULT 'daily',
        time VARCHAR DEFAULT '09:00',
        days_of_week JSON,
        timezone VARCHAR DEFAULT 'Europe/Moscow',
        channels JSON,
        tags JSON,
        format VARCHAR DEFAULT 'markdown',
        max_posts INTEGER DEFAULT 20,
        delivery_method VARCHAR DEFAULT 'telegram',
        email VARCHAR,
        last_sent_at TIMESTAMP WITH TIME ZONE,
        next_scheduled_at TIMESTAMP WITH TIME ZONE,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """
    
    # Определяем тип БД
    db_url = str(engine.url)
    is_postgres = db_url.startswith('postgresql')
    
    sql = postgres_sql if is_postgres else sqlite_sql
    
    try:
        with engine.connect() as conn:
            conn.execute(text(sql))
            conn.commit()
        logger.info("✅ Таблица digest_settings создана")
    except Exception as e:
        logger.error(f"❌ Ошибка создания таблицы digest_settings: {e}")
        raise


def create_indexing_status_table(engine):
    """Создать таблицу indexing_status"""
    
    # SQL для SQLite
    sqlite_sql = """
    CREATE TABLE IF NOT EXISTS indexing_status (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        post_id INTEGER NOT NULL,
        indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        vector_id VARCHAR,
        status VARCHAR DEFAULT 'success',
        error TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(post_id) REFERENCES posts(id) ON DELETE CASCADE,
        UNIQUE(user_id, post_id)
    );
    """
    
    # SQL для PostgreSQL
    postgres_sql = """
    CREATE TABLE IF NOT EXISTS indexing_status (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        post_id INTEGER NOT NULL,
        indexed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        vector_id VARCHAR,
        status VARCHAR DEFAULT 'success',
        error TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(post_id) REFERENCES posts(id) ON DELETE CASCADE,
        UNIQUE(user_id, post_id)
    );
    """
    
    # Определяем тип БД
    db_url = str(engine.url)
    is_postgres = db_url.startswith('postgresql')
    
    sql = postgres_sql if is_postgres else sqlite_sql
    
    try:
        with engine.connect() as conn:
            conn.execute(text(sql))
            conn.commit()
        logger.info("✅ Таблица indexing_status создана")
    except Exception as e:
        logger.error(f"❌ Ошибка создания таблицы indexing_status: {e}")
        raise


def create_indexes(engine):
    """Создать индексы для новых таблиц"""
    
    indexes_sql = [
        # Индексы для digest_settings
        "CREATE INDEX IF NOT EXISTS idx_digest_settings_user_id ON digest_settings(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_digest_settings_enabled ON digest_settings(enabled);",
        
        # Индексы для indexing_status
        "CREATE INDEX IF NOT EXISTS idx_indexing_status_user_id ON indexing_status(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_indexing_status_post_id ON indexing_status(post_id);",
        "CREATE INDEX IF NOT EXISTS idx_indexing_status_status ON indexing_status(status);",
    ]
    
    try:
        with engine.connect() as conn:
            for sql in indexes_sql:
                conn.execute(text(sql))
            conn.commit()
        logger.info("✅ Индексы созданы")
    except Exception as e:
        logger.error(f"❌ Ошибка создания индексов: {e}")
        raise


def main():
    """Основная функция миграции"""
    logger.info("🔄 Начало миграции: Добавление таблиц для RAG-системы")
    
    # Проверяем существование таблиц
    if check_table_exists(engine, 'digest_settings'):
        logger.warning("⚠️ Таблица digest_settings уже существует")
    else:
        create_digest_settings_table(engine)
    
    if check_table_exists(engine, 'indexing_status'):
        logger.warning("⚠️ Таблица indexing_status уже существует")
    else:
        create_indexing_status_table(engine)
    
    # Создаем индексы
    create_indexes(engine)
    
    # Проверяем результат
    logger.info("\n📊 Проверка созданных таблиц:")
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    for table in ['digest_settings', 'indexing_status']:
        if table in tables:
            columns = inspector.get_columns(table)
            logger.info(f"  ✅ {table}: {len(columns)} столбцов")
        else:
            logger.error(f"  ❌ {table}: НЕ НАЙДЕНА")
    
    logger.info("\n✅ Миграция завершена успешно!")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"\n❌ Миграция прервана с ошибкой: {e}")
        sys.exit(1)

