#!/usr/bin/env python3
"""
Миграция базы данных: переход от связи Channel -> User к связи многие-ко-многим

Этот скрипт:
1. Создает новую таблицу user_channel для связи многие-ко-многим
2. Переносит данные из старой структуры в новую
3. Удаляет дубликаты каналов, объединяя подписки разных пользователей
4. Удаляет старую колонку user_id из таблицы channels
"""

import sys
import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, inspect, text, MetaData, Table, Column, Integer, String, DateTime, Boolean, BigInteger, ForeignKey
from sqlalchemy.orm import sessionmaker
import logging

# Добавляем путь к модулям
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import engine, SessionLocal
from sqlalchemy import text, inspect
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Определяем тип БД
DATABASE_TYPE = 'sqlite'  # по умолчанию
if hasattr(engine.url, 'drivername'):
    if 'postgresql' in engine.url.drivername:
        DATABASE_TYPE = 'postgresql'
    elif 'sqlite' in engine.url.drivername:
        DATABASE_TYPE = 'sqlite'

logger.info(f"🔍 Обнаружен тип базы данных: {DATABASE_TYPE.upper()}")


def migrate_database():
    """Выполнить миграцию базы данных"""
    
    logger.info("🔄 Начинаем миграцию базы данных...")
    
    # Создаем подключение к БД
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
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
        
        session.execute(text("""
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
        """))
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
        
        # ===== ШАГ 3: Группируем каналы и создаем новую структуру =====
        logger.info("📋 Шаг 3: Объединение дубликатов каналов...")
        
        # Группируем каналы по channel_username
        channels_map = {}  # channel_username -> {channel_data, users: [(user_id, subscription_data)]}
        
        for row in old_channels:
            old_id, user_id, username, channel_id, title, is_active, created_at, last_parsed = row
            
            if username not in channels_map:
                channels_map[username] = {
                    'channel_id': channel_id,
                    'channel_title': title,
                    'created_at': created_at,
                    'old_ids': [],  # Старые ID для обновления posts
                    'users': []
                }
            
            # Добавляем старый ID канала
            channels_map[username]['old_ids'].append(old_id)
            
            # Добавляем пользователя к этому каналу
            channels_map[username]['users'].append({
                'user_id': user_id,
                'is_active': is_active,
                'created_at': created_at,
                'last_parsed_at': last_parsed
            })
            
            # Обновляем данные канала если они были None
            if not channels_map[username]['channel_id'] and channel_id:
                channels_map[username]['channel_id'] = channel_id
            if not channels_map[username]['channel_title'] and title:
                channels_map[username]['channel_title'] = title
        
        logger.info(f"📊 Обнаружено {len(channels_map)} уникальных каналов")
        
        # ===== ШАГ 4: Создаем временную таблицу для новых каналов =====
        logger.info("📋 Шаг 4: Создание временной таблицы channels_new...")
        
        session.execute(text("""
            CREATE TABLE channels_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_username VARCHAR NOT NULL UNIQUE,
                channel_id BIGINT UNIQUE,
                channel_title VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        session.commit()
        
        # ===== ШАГ 5: Заполняем новые таблицы =====
        logger.info("📋 Шаг 5: Заполнение новых таблиц данными...")
        
        channels_id_mapping = {}  # old_id -> new_id
        
        for username, data in channels_map.items():
            # Вставляем канал в channels_new
            result = session.execute(text("""
                INSERT INTO channels_new (channel_username, channel_id, channel_title, created_at)
                VALUES (:username, :channel_id, :title, :created_at)
                RETURNING id
            """), {
                'username': username,
                'channel_id': data['channel_id'],
                'title': data['channel_title'],
                'created_at': data['created_at']
            })
            
            new_channel_id = result.fetchone()[0]
            session.commit()
            
            # Сохраняем маппинг старых ID -> новый ID
            for old_id in data['old_ids']:
                channels_id_mapping[old_id] = new_channel_id
            
            # Добавляем связи пользователей с каналом
            for user_data in data['users']:
                session.execute(text("""
                    INSERT INTO user_channel (user_id, channel_id, is_active, created_at, last_parsed_at)
                    VALUES (:user_id, :channel_id, :is_active, :created_at, :last_parsed_at)
                    ON CONFLICT (user_id, channel_id) DO UPDATE SET
                        is_active = :is_active,
                        last_parsed_at = COALESCE(user_channel.last_parsed_at, :last_parsed_at)
                """), {
                    'user_id': user_data['user_id'],
                    'channel_id': new_channel_id,
                    'is_active': user_data['is_active'],
                    'created_at': user_data['created_at'],
                    'last_parsed_at': user_data['last_parsed_at']
                })
            
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
        
        # ===== ШАГ 7: Удаляем старую таблицу и переименовываем новую =====
        logger.info("📋 Шаг 7: Замена старой таблицы channels на новую...")
        
        session.execute(text("DROP TABLE channels"))
        session.execute(text("ALTER TABLE channels_new RENAME TO channels"))
        session.commit()
        
        logger.info("✅ Таблица channels обновлена")
        
        # ===== ШАГ 8: Создаем индексы =====
        logger.info("📋 Шаг 8: Создание индексов...")
        
        session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_channels_username 
            ON channels(channel_username)
        """))
        
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
    logger.info("=" * 60)
    
    # Создаем резервную копию (если используется SQLite)
    if SQLALCHEMY_DATABASE_URL.startswith('sqlite'):
        import shutil
        db_path = SQLALCHEMY_DATABASE_URL.replace('sqlite:///', '')
        backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"💾 Создание резервной копии: {backup_path}")
        try:
            shutil.copy2(db_path, backup_path)
            logger.info(f"✅ Резервная копия создана")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось создать резервную копию: {e}")
    
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

