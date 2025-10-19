#!/usr/bin/env python3
"""
Migration: Add Groups Support
Date: 2025-10-13
Description: Добавляет поддержку Telegram групп с мониторингом упоминаний и дайджестами диалогов
"""
import os
import sys
from datetime import datetime, timezone
import psycopg2
from psycopg2.extras import RealDictCursor

# Добавляем родительскую директорию в path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


def get_database_url() -> str:
    """Получить URL базы данных"""
    from dotenv import load_dotenv
    load_dotenv()
    
    url = os.getenv("TELEGRAM_DATABASE_URL")
    
    if not url:
        raise ValueError(
            "TELEGRAM_DATABASE_URL не установлен!\n"
            "Должен быть: postgresql://postgres:password@db:5432/postgres"
        )
    
    if "sqlite" in url.lower():
        raise ValueError(
            "SQLite НЕ поддерживается!\n"
            "Используйте только PostgreSQL"
        )
    
    return url


def backup_info():
    """Информация о бэкапе"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    print(f"\n📦 Рекомендуется создать backup БД перед миграцией")
    print(f"   Команда: docker exec postgres pg_dump -U postgres postgres > backup_{timestamp}.sql")
    print()


def migrate():
    """Выполнить миграцию"""
    database_url = get_database_url()
    
    print("=" * 80)
    print("🚀 Migration: Add Groups Support")
    print("=" * 80)
    
    backup_info()
    
    response = input("Продолжить миграцию? (yes/no): ")
    if response.lower() != "yes":
        print("❌ Миграция отменена")
        return
    
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        print("\n📋 Начинаем миграцию...\n")
        
        # 1. Создание таблицы groups
        print("1️⃣  Создание таблицы 'groups'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                id SERIAL PRIMARY KEY,
                group_id BIGINT UNIQUE NOT NULL,
                group_title VARCHAR,
                group_username VARCHAR,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() AT TIME ZONE 'UTC')
            );
        """)
        
        # Индексы для groups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_groups_group_id ON groups(group_id);
            CREATE INDEX IF NOT EXISTS idx_groups_group_username ON groups(group_username);
        """)
        print("   ✅ Таблица 'groups' создана")
        
        # 2. Создание таблицы user_group (many-to-many)
        print("2️⃣  Создание таблицы 'user_group'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_group (
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
                is_active BOOLEAN DEFAULT TRUE,
                mentions_enabled BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() AT TIME ZONE 'UTC'),
                PRIMARY KEY (user_id, group_id)
            );
        """)
        
        # Индексы для user_group
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_group_user_id ON user_group(user_id);
            CREATE INDEX IF NOT EXISTS idx_user_group_group_id ON user_group(group_id);
        """)
        print("   ✅ Таблица 'user_group' создана")
        
        # 3. Создание таблицы group_mentions
        print("3️⃣  Создание таблицы 'group_mentions'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS group_mentions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                group_id INTEGER NOT NULL REFERENCES groups(id),
                message_id BIGINT NOT NULL,
                mentioned_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() AT TIME ZONE 'UTC'),
                context TEXT,
                reason TEXT,
                urgency VARCHAR,
                notified BOOLEAN DEFAULT FALSE,
                notified_at TIMESTAMP WITH TIME ZONE,
                CONSTRAINT uix_user_group_message UNIQUE (user_id, group_id, message_id)
            );
        """)
        
        # Индексы для group_mentions
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_group_mentions_user_id ON group_mentions(user_id);
            CREATE INDEX IF NOT EXISTS idx_group_mentions_group_id ON group_mentions(group_id);
            CREATE INDEX IF NOT EXISTS idx_group_mentions_mentioned_at ON group_mentions(mentioned_at);
        """)
        print("   ✅ Таблица 'group_mentions' создана")
        
        # 4. Создание таблицы group_settings
        print("4️⃣  Создание таблицы 'group_settings'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS group_settings (
                id SERIAL PRIMARY KEY,
                user_id INTEGER UNIQUE NOT NULL REFERENCES users(id),
                mentions_enabled BOOLEAN DEFAULT TRUE,
                mention_context_messages INTEGER DEFAULT 5,
                digest_default_hours INTEGER DEFAULT 24,
                digest_max_messages INTEGER DEFAULT 200
            );
        """)
        
        # Индекс для group_settings
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_group_settings_user_id ON group_settings(user_id);
        """)
        print("   ✅ Таблица 'group_settings' создана")
        
        # 5. Проверка созданных таблиц
        print("\n📊 Проверка созданных таблиц...")
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('groups', 'user_group', 'group_mentions', 'group_settings')
            ORDER BY table_name;
        """)
        
        tables = cursor.fetchall()
        print(f"   Найдено таблиц: {len(tables)}")
        for table in tables:
            print(f"     ✓ {table['table_name']}")
        
        # Commit изменений
        conn.commit()
        
        print("\n" + "=" * 80)
        print("✅ Миграция успешно завершена!")
        print("=" * 80)
        print("\n📝 Что дальше:")
        print("   1. Перезапустите telethon контейнеры: docker restart telethon telethon-bot")
        print("   2. Проверьте логи: docker logs telethon -f")
        print("   3. Протестируйте команды: /add_group, /my_groups")
        print()
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Ошибка миграции: {e}")
        print("   Изменения откачены (rollback)")
        raise
        
    finally:
        cursor.close()
        conn.close()


def rollback():
    """Откат миграции (если нужно)"""
    database_url = get_database_url()
    
    print("=" * 80)
    print("⚠️  ROLLBACK: Remove Groups Support")
    print("=" * 80)
    print("\n⚠️  ВНИМАНИЕ: Это удалит все таблицы групп и данные!")
    print()
    
    response = input("Вы уверены? Введите 'DELETE ALL GROUPS' для подтверждения: ")
    if response != "DELETE ALL GROUPS":
        print("❌ Rollback отменен")
        return
    
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()
    
    try:
        print("\n🗑️  Удаление таблиц...")
        
        cursor.execute("DROP TABLE IF EXISTS group_mentions CASCADE;")
        print("   ✓ group_mentions удалена")
        
        cursor.execute("DROP TABLE IF EXISTS group_settings CASCADE;")
        print("   ✓ group_settings удалена")
        
        cursor.execute("DROP TABLE IF EXISTS user_group CASCADE;")
        print("   ✓ user_group удалена")
        
        cursor.execute("DROP TABLE IF EXISTS groups CASCADE;")
        print("   ✓ groups удалена")
        
        conn.commit()
        print("\n✅ Rollback завершен")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Ошибка rollback: {e}")
        raise
        
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Migration: Add Groups Support')
    parser.add_argument('action', choices=['migrate', 'rollback'], 
                       help='Действие: migrate (применить) или rollback (откатить)')
    
    args = parser.parse_args()
    
    if args.action == 'migrate':
        migrate()
    elif args.action == 'rollback':
        rollback()

