#!/usr/bin/env python3
"""
Миграция: Добавление AI-фич для дайджестов

Добавляет:
1. Поля в digest_settings для AI-суммаризации
2. Таблицу rag_query_history для истории запросов

Дата: 11 октября 2025
"""

import sys
import os
import logging
from datetime import datetime
from sqlalchemy import create_engine, text, inspect

# Добавляем корневую директорию в path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from database import SessionLocal, engine
from models import Base, User, DigestSettings, RAGQueryHistory

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def backup_database():
    """Создать backup базы данных"""
    db_url = str(engine.url)
    
    if 'sqlite' in db_url:
        import shutil
        db_path = db_url.replace('sqlite:///', '')
        if os.path.exists(db_path):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = f"{db_path}.backup_{timestamp}"
            shutil.copy(db_path, backup_path)
            logger.info(f"✅ Backup создан: {backup_path}")
            return backup_path
    else:
        logger.info("⚠️ PostgreSQL: создайте backup вручную с помощью pg_dump")
        return None


def check_column_exists(engine, table_name: str, column_name: str) -> bool:
    """Проверить существование колонки"""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def check_table_exists(engine, table_name: str) -> bool:
    """Проверить существование таблицы"""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def add_ai_digest_columns(engine):
    """Добавить колонки для AI-дайджеста в digest_settings"""
    
    columns_to_add = [
        ("ai_summarize", "BOOLEAN DEFAULT 0", "BOOLEAN DEFAULT FALSE"),
        ("preferred_topics", "TEXT", "JSON"),
        ("summary_style", "VARCHAR DEFAULT 'concise'", "VARCHAR DEFAULT 'concise'"),
        ("topics_limit", "INTEGER DEFAULT 5", "INTEGER DEFAULT 5")
    ]
    
    db_url = str(engine.url)
    is_postgres = db_url.startswith('postgresql')
    
    with engine.connect() as conn:
        for col_name, sqlite_type, postgres_type in columns_to_add:
            if check_column_exists(engine, 'digest_settings', col_name):
                logger.info(f"⏭️  Колонка digest_settings.{col_name} уже существует")
                continue
            
            col_type = postgres_type if is_postgres else sqlite_type
            sql = f"ALTER TABLE digest_settings ADD COLUMN {col_name} {col_type}"
            
            try:
                conn.execute(text(sql))
                conn.commit()
                logger.info(f"✅ Добавлена колонка digest_settings.{col_name}")
            except Exception as e:
                logger.error(f"❌ Ошибка добавления колонки {col_name}: {e}")
                raise


def create_rag_query_history_table(engine):
    """Создать таблицу rag_query_history"""
    
    if check_table_exists(engine, 'rag_query_history'):
        logger.info("⏭️  Таблица rag_query_history уже существует")
        return
    
    # SQL для SQLite
    sqlite_sql = """
    CREATE TABLE rag_query_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        query TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        extracted_topics TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    
    CREATE INDEX ix_rag_query_history_user_id ON rag_query_history(user_id);
    CREATE INDEX ix_rag_query_history_created_at ON rag_query_history(created_at);
    """
    
    # SQL для PostgreSQL
    postgres_sql = """
    CREATE TABLE rag_query_history (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        query TEXT NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        extracted_topics JSON,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    
    CREATE INDEX ix_rag_query_history_user_id ON rag_query_history(user_id);
    CREATE INDEX ix_rag_query_history_created_at ON rag_query_history(created_at);
    """
    
    db_url = str(engine.url)
    is_postgres = db_url.startswith('postgresql')
    
    sql = postgres_sql if is_postgres else sqlite_sql
    
    try:
        with engine.connect() as conn:
            # Разбиваем на отдельные команды
            for statement in sql.strip().split(';'):
                statement = statement.strip()
                if statement:
                    conn.execute(text(statement))
            conn.commit()
        logger.info("✅ Таблица rag_query_history создана")
    except Exception as e:
        logger.error(f"❌ Ошибка создания таблицы rag_query_history: {e}")
        raise


def verify_migration(engine):
    """Проверить успешность миграции"""
    logger.info("\n🔍 Проверка миграции...")
    
    # Проверка колонок
    required_columns = ['ai_summarize', 'preferred_topics', 'summary_style', 'topics_limit']
    for col in required_columns:
        exists = check_column_exists(engine, 'digest_settings', col)
        status = "✅" if exists else "❌"
        logger.info(f"{status} digest_settings.{col}: {'существует' if exists else 'отсутствует'}")
    
    # Проверка таблицы
    table_exists = check_table_exists(engine, 'rag_query_history')
    status = "✅" if table_exists else "❌"
    logger.info(f"{status} rag_query_history: {'существует' if table_exists else 'отсутствует'}")
    
    return all([
        check_column_exists(engine, 'digest_settings', col) 
        for col in required_columns
    ]) and table_exists


def main():
    """Запуск миграции"""
    logger.info("="*60)
    logger.info("🚀 Миграция: AI Digest Features")
    logger.info("="*60)
    
    # Проверка .env
    if not os.path.exists('.env'):
        logger.warning("⚠️ Файл .env не найден (опционально)")
    
    # Backup
    logger.info("\n📦 Создание backup...")
    backup_path = backup_database()
    
    # Выполнение миграции
    try:
        logger.info("\n🔄 Добавление AI колонок в digest_settings...")
        add_ai_digest_columns(engine)
        
        logger.info("\n🔄 Создание таблицы rag_query_history...")
        create_rag_query_history_table(engine)
        
        # Проверка
        if verify_migration(engine):
            logger.info("\n✅ Миграция успешно выполнена!")
            logger.info("\nТеперь доступны:")
            logger.info("  • AI-суммаризация дайджестов")
            logger.info("  • История RAG-запросов")
            logger.info("  • Анализ интересов пользователей")
            logger.info("\nНастройте для пользователя:")
            logger.info("  PUT /rag/digest/settings/{user_id}")
            logger.info("  {")
            logger.info('    "ai_summarize": true,')
            logger.info('    "preferred_topics": ["криптовалюты", "авто", "финансы"],')
            logger.info('    "summary_style": "concise",')
            logger.info('    "topics_limit": 5')
            logger.info("  }")
        else:
            logger.error("\n❌ Миграция выполнена с ошибками!")
            return 1
            
    except Exception as e:
        logger.error(f"\n❌ Ошибка выполнения миграции: {e}")
        if backup_path:
            logger.info(f"💾 Восстановите из backup: {backup_path}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

