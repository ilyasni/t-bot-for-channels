#!/usr/bin/env python3
"""
Универсальная миграция базы данных: переход к Many-to-Many структуре
Поддерживает PostgreSQL (Supabase) и SQLite
"""

import sys
import os
from datetime import datetime, timezone
from sqlalchemy import text, inspect
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import engine, SessionLocal
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Определяем тип БД
DATABASE_TYPE = 'sqlite'
if hasattr(engine.url, 'drivername'):
    if 'postgresql' in engine.url.drivername:
        DATABASE_TYPE = 'postgresql'
    elif 'sqlite' in engine.url.drivername:
        DATABASE_TYPE = 'sqlite'

logger.info(f"🔍 Обнаружен тип базы данных: {DATABASE_TYPE.upper()}")


def get_sql_create_user_channel():
    """SQL для создания таблицы user_channel"""
    if DATABASE_TYPE == 'postgresql':
        return """
            CREATE TABLE IF NOT EXISTS user_channel (
                user_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_parsed_at TIMESTAMP,
                PRIMARY KEY (user_id, channel_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (channel_id) REFERENCES channels(id) ON DELETE CASCADE
            )
        """
    else:  # SQLite
        return """
            CREATE TABLE IF NOT EXISTS user_channel (
                user_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_parsed_at TIMESTAMP,
                PRIMARY KEY (user_id, channel_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (channel_id) REFERENCES channels(id) ON DELETE CASCADE
            )
        """


def get_sql_create_channels_new():
    """SQL для создания новой таблицы channels"""
    if DATABASE_TYPE == 'postgresql':
        return """
            CREATE TABLE channels_new (
                id SERIAL PRIMARY KEY,
                channel_username VARCHAR NOT NULL UNIQUE,
                channel_id BIGINT UNIQUE,
                channel_title VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
    else:  # SQLite
        return """
            CREATE TABLE channels_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_username VARCHAR NOT NULL UNIQUE,
                channel_id BIGINT UNIQUE,
                channel_title VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """


def get_sql_insert_channel(username, channel_id, title, created_at):
    """SQL для вставки канала с возвратом ID"""
    if DATABASE_TYPE == 'postgresql':
        return text("""
            INSERT INTO channels_new (channel_username, channel_id, channel_title, created_at)
            VALUES (:username, :channel_id, :title, :created_at)
            RETURNING id
        """), {
            'username': username,
            'channel_id': channel_id,
            'title': title,
            'created_at': created_at
        }
    else:  # SQLite
        return text("""
            INSERT INTO channels_new (channel_username, channel_id, channel_title, created_at)
            VALUES (:username, :channel_id, :title, :created_at)
        """), {
            'username': username,
            'channel_id': channel_id,
            'title': title,
            'created_at': created_at
        }


def get_sql_upsert_user_channel(user_id, channel_id, is_active, created_at, last_parsed_at):
    """SQL для вставки/обновления связи user_channel"""
    if DATABASE_TYPE == 'postgresql':
        return text("""
            INSERT INTO user_channel (user_id, channel_id, is_active, created_at, last_parsed_at)
            VALUES (:user_id, :channel_id, :is_active, :created_at, :last_parsed_at)
            ON CONFLICT (user_id, channel_id) DO UPDATE SET
                is_active = EXCLUDED.is_active,
                last_parsed_at = COALESCE(user_channel.last_parsed_at, EXCLUDED.last_parsed_at)
        """), {
            'user_id': user_id,
            'channel_id': channel_id,
            'is_active': is_active,
            'created_at': created_at,
            'last_parsed_at': last_parsed_at
        }
    else:  # SQLite
        return text("""
            INSERT INTO user_channel (user_id, channel_id, is_active, created_at, last_parsed_at)
            VALUES (:user_id, :channel_id, :is_active, :created_at, :last_parsed_at)
            ON CONFLICT (user_id, channel_id) DO UPDATE SET
                is_active = :is_active,
                last_parsed_at = COALESCE(user_channel.last_parsed_at, :last_parsed_at)
        """), {
            'user_id': user_id,
            'channel_id': channel_id,
            'is_active': is_active,
            'created_at': created_at,
            'last_parsed_at': last_parsed_at
        }


def migrate_database():
    """Выполнить миграцию базы данных"""
    
    logger.info("🔄 Начинаем миграцию базы данных...")
    
    session = SessionLocal()
    
    try:
        inspector = inspect(engine)
        
        # Проверяем, существует ли уже таблица user_channel
        if 'user_channel' in inspector.get_table_names():
            logger.warning("⚠️ Таблица user_channel уже существует. Проверяем необходимость миграции...")
            
            # Проверяем, есть ли еще user_id в channels
            columns = [col['name'] for col in inspector.get_columns('channels')]
            if 'user_id' not in columns:
                logger.info("✅ Миграция уже выполнена ранее. Выход.")
                return True
        
        # ===== ШАГ 1: Создаем таблицу user_channel =====
        logger.info("📋 Шаг 1: Создание таблицы user_channel...")
        
        session.execute(text(get_sql_create_user_channel()))
        session.commit()
        logger.info("✅ Таблица user_channel создана")
        
        # ===== ШАГ 2: Получаем старые данные =====
        logger.info("📋 Шаг 2: Получение старых данных из таблицы channels...")
        
        result = session.execute(text("""
            SELECT id, user_id, channel_username, channel_id, channel_title, 
                   is_active, created_at, last_parsed_at
            FROM channels
            ORDER BY channel_username, id
        """))
        
        old_channels = result.fetchall()
        logger.info(f"📊 Найдено {len(old_channels)} записей в старой структуре")
        
        if not old_channels:
            logger.warning("⚠️ Нет данных для миграции")
        
        # ===== ШАГ 3: Группируем каналы =====
        logger.info("📋 Шаг 3: Объединение дубликатов каналов...")
        
        channels_map = {}
        
        for row in old_channels:
            old_id, user_id, username, channel_id, title, is_active, created_at, last_parsed = row
            
            if username not in channels_map:
                channels_map[username] = {
                    'channel_id': channel_id,
                    'channel_title': title,
                    'created_at': created_at,
                    'old_ids': [],
                    'users': []
                }
            
            channels_map[username]['old_ids'].append(old_id)
            channels_map[username]['users'].append({
                'user_id': user_id,
                'is_active': is_active,
                'created_at': created_at,
                'last_parsed_at': last_parsed
            })
            
            if not channels_map[username]['channel_id'] and channel_id:
                channels_map[username]['channel_id'] = channel_id
            if not channels_map[username]['channel_title'] and title:
                channels_map[username]['channel_title'] = title
        
        logger.info(f"📊 Обнаружено {len(channels_map)} уникальных каналов")
        
        # ===== ШАГ 4: Создаем временную таблицу =====
        logger.info("📋 Шаг 4: Создание временной таблицы channels_new...")
        
        session.execute(text(get_sql_create_channels_new()))
        session.commit()
        
        # ===== ШАГ 5: Заполняем новые таблицы =====
        logger.info("📋 Шаг 5: Заполнение новых таблиц данными...")
        
        channels_id_mapping = {}
        
        for username, data in channels_map.items():
            # Вставляем канал
            sql, params = get_sql_insert_channel(
                username,
                data['channel_id'],
                data['channel_title'],
                data['created_at']
            )
            
            result = session.execute(sql, params)
            
            if DATABASE_TYPE == 'postgresql':
                new_channel_id = result.fetchone()[0]
            else:
                session.commit()
                # Получаем последний вставленный ID для SQLite
                result = session.execute(text("SELECT last_insert_rowid()"))
                new_channel_id = result.fetchone()[0]
            
            session.commit()
            
            # Маппинг старых ID -> новый ID
            for old_id in data['old_ids']:
                channels_id_mapping[old_id] = new_channel_id
            
            # Добавляем связи user_channel
            for user_data in data['users']:
                sql, params = get_sql_upsert_user_channel(
                    user_data['user_id'],
                    new_channel_id,
                    user_data['is_active'],
                    user_data['created_at'],
                    user_data['last_parsed_at']
                )
                session.execute(sql, params)
            
            session.commit()
            logger.info(f"✅ Канал @{username}: {len(data['users'])} подписчиков")
        
        # ===== ШАГ 6: Обновляем posts =====
        logger.info("📋 Шаг 6: Обновление ссылок в таблице posts...")
        
        for old_id, new_id in channels_id_mapping.items():
            session.execute(text("""
                UPDATE posts
                SET channel_id = :new_id
                WHERE channel_id = :old_id
            """), {'old_id': old_id, 'new_id': new_id})
        
        session.commit()
        logger.info(f"✅ Обновлено постов: {len(channels_id_mapping)} каналов")
        
        # ===== ШАГ 7: Удаляем старую таблицу и переименовываем =====
        logger.info("📋 Шаг 7: Замена старой таблицы channels...")
        
        if DATABASE_TYPE == 'postgresql':
            # PostgreSQL: используем CASCADE для удаления зависимостей
            session.execute(text("DROP TABLE channels CASCADE"))
        else:
            # SQLite
            session.execute(text("DROP TABLE channels"))
        
        session.execute(text("ALTER TABLE channels_new RENAME TO channels"))
        session.commit()
        
        logger.info("✅ Таблица channels обновлена")
        
        # ===== ШАГ 7.5: Восстанавливаем foreign key constraints =====
        logger.info("📋 Шаг 7.5: Восстановление foreign key constraints...")
        
        if DATABASE_TYPE == 'postgresql':
            # Восстанавливаем constraint для posts
            session.execute(text("""
                ALTER TABLE posts 
                ADD CONSTRAINT posts_channel_id_fkey 
                FOREIGN KEY (channel_id) REFERENCES channels(id) ON DELETE CASCADE
            """))
            
            # Восстанавливаем constraint для user_channel (если еще не создан)
            # Он уже должен быть создан при создании таблицы, но проверим
            try:
                session.execute(text("""
                    ALTER TABLE user_channel 
                    ADD CONSTRAINT user_channel_channel_id_fkey 
                    FOREIGN KEY (channel_id) REFERENCES channels(id) ON DELETE CASCADE
                """))
            except:
                # Constraint уже существует
                pass
            
            session.commit()
            logger.info("✅ Foreign key constraints восстановлены")
        
        # ===== ШАГ 8: Создаем индексы =====
        logger.info("📋 Шаг 8: Создание индексов...")
        
        # Индекс на channel_username уже создан через UNIQUE
        
        if DATABASE_TYPE == 'postgresql':
            # PostgreSQL - создаем индекс на channel_id
            session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_channels_channel_id 
                ON channels(channel_id)
            """))
        else:
            # SQLite
            session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_channels_channel_id 
                ON channels(channel_id)
            """))
        
        session.commit()
        logger.info("✅ Индексы созданы")
        
        # ===== ЗАВЕРШЕНИЕ =====
        logger.info("✅ Миграция успешно завершена!")
        logger.info(f"📊 Итоговая статистика:")
        
        # Статистика
        channels_count = session.execute(text("SELECT COUNT(*) FROM channels")).fetchone()[0]
        user_channel_count = session.execute(text("SELECT COUNT(*) FROM user_channel")).fetchone()[0]
        
        logger.info(f"  - Уникальных каналов: {channels_count}")
        logger.info(f"  - Подписок пользователей: {user_channel_count}")
        logger.info(f"  - Устранено дубликатов: {len(old_channels) - channels_count}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка миграции: {str(e)}")
        session.rollback()
        return False
        
    finally:
        session.close()


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("МИГРАЦИЯ БАЗЫ ДАННЫХ: ПЕРЕХОД К СТРУКТУРЕ МНОГИЕ-КО-МНОГИМ")
    logger.info(f"Тип БД: {DATABASE_TYPE.upper()}")
    logger.info("=" * 60)
    
    # Запускаем миграцию
    success = migrate_database()
    
    if success:
        logger.info("=" * 60)
        logger.info("✅ МИГРАЦИЯ ЗАВЕРШЕНА УСПЕШНО")
        logger.info("=" * 60)
        sys.exit(0)
    else:
        logger.error("=" * 60)
        logger.error("❌ МИГРАЦИЯ ЗАВЕРШИЛАСЬ С ОШИБКАМИ")
        logger.error("=" * 60)
        sys.exit(1)

