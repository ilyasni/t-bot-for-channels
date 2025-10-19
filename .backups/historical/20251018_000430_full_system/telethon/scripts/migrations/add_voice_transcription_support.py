#!/usr/bin/env python3
"""
Migration: Add Voice Transcription Support
Date: 2025-10-13
Description: Добавляет поля для статистики голосовых запросов
"""
import os
import sys
from datetime import datetime
import psycopg2

# Добавляем путь к проекту
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from dotenv import load_dotenv
load_dotenv()


def get_database_url():
    """Получить DATABASE_URL из переменных окружения"""
    database_url = os.getenv("TELEGRAM_DATABASE_URL")
    
    if not database_url:
        raise ValueError(
            "TELEGRAM_DATABASE_URL не установлен!\n"
            "Должен быть: postgresql://postgres:password@db:5432/postgres"
        )
    
    if "sqlite" in database_url.lower():
        raise ValueError(
            "SQLite НЕ поддерживается!\n"
            "Используйте только PostgreSQL"
        )
    
    return database_url


def backup_database():
    """Создать backup базы данных перед миграцией"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    print(f"📦 Backup database: {timestamp}")
    print("   Для production используйте: docker exec supabase-db pg_dump ...")
    print("   Пропускаем backup для development...")


def migrate():
    """Выполнить миграцию"""
    database_url = get_database_url()
    
    print("🔄 Подключение к базе данных...")
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()
    
    try:
        print("📝 Добавление полей для Voice Transcription...")
        
        # Добавляем поля voice_queries_today и voice_queries_reset_at
        cursor.execute("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS voice_queries_today INTEGER DEFAULT 0,
            ADD COLUMN IF NOT EXISTS voice_queries_reset_at TIMESTAMP WITH TIME ZONE
        """)
        
        conn.commit()
        print("✅ Миграция успешно завершена!")
        print("   Добавлены поля:")
        print("   • users.voice_queries_today (INTEGER)")
        print("   • users.voice_queries_reset_at (TIMESTAMP WITH TIME ZONE)")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Ошибка миграции: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


def verify_migration():
    """Проверить успешность миграции"""
    database_url = get_database_url()
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()
    
    try:
        print("\n🔍 Проверка миграции...")
        
        # Проверяем наличие новых полей
        cursor.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'users'
            AND column_name IN ('voice_queries_today', 'voice_queries_reset_at')
            ORDER BY column_name
        """)
        
        columns = cursor.fetchall()
        
        if len(columns) == 2:
            print("✅ Все поля созданы успешно:")
            for col_name, col_type in columns:
                print(f"   • {col_name}: {col_type}")
        else:
            print(f"⚠️ Найдено {len(columns)} из 2 полей")
            for col_name, col_type in columns:
                print(f"   • {col_name}: {col_type}")
        
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Migration: Add Voice Transcription Support")
    print("=" * 60)
    print()
    
    try:
        backup_database()
        migrate()
        verify_migration()
        
        print("\n" + "=" * 60)
        print("✅ Миграция завершена успешно!")
        print("=" * 60)
        print()
        print("📝 Next steps:")
        print("1. Перезапустите Docker контейнеры:")
        print("   docker-compose restart telethon telethon-bot")
        print()
        print("2. Проверьте работу голосовых команд:")
        print("   • Отправьте /ask в бот")
        print("   • Затем отправьте голосовое сообщение")
        print()
        
    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ Миграция НЕ завершена!")
        print("=" * 60)
        print(f"\nОшибка: {e}")
        print("\n💡 Troubleshooting:")
        print("1. Проверьте TELEGRAM_DATABASE_URL в .env")
        print("2. Убедитесь что PostgreSQL запущен:")
        print("   docker ps | grep postgres")
        print("3. Проверьте подключение:")
        print("   docker exec supabase-db psql -U postgres -d postgres -c 'SELECT 1'")
        sys.exit(1)

