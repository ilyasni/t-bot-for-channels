#!/usr/bin/env python3
"""
Миграция: Добавление поля enriched_content в таблицу posts

Это поле используется для хранения обогащенного контента постов:
- Оригинальный текст поста
- Контент извлеченный из ссылок через Crawl4AI

Это позволяет RAG-системе индексировать не только текст поста,
но и содержимое связанных веб-страниц.

Дата: 11 октября 2025
Версия: 2.2.1
"""

import sys
import os
from datetime import datetime
import shutil

# Добавляем родительскую директорию в path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv

load_dotenv()

def get_database_url():
    """Получить URL базы данных из переменных окружения"""
    return os.getenv("DATABASE_URL", "sqlite:///./data/telethon_bot.db")

def backup_database():
    """Создать backup базы данных перед миграцией"""
    db_url = get_database_url()
    
    # Backup только для SQLite
    if db_url.startswith('sqlite'):
        db_path = db_url.replace('sqlite:///', '')
        if os.path.exists(db_path):
            try:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_path = f"{db_path}.backup_{timestamp}"
                shutil.copy(db_path, backup_path)
                print(f"✅ Backup создан: {backup_path}")
                return backup_path
            except PermissionError:
                print("⚠️ Нет прав для создания backup (это нормально в Docker)")
                print("💡 Backup будет создан автоматически Docker volumes")
                return None
            except Exception as e:
                print(f"⚠️ Не удалось создать backup: {e}")
                print("💡 Миграция продолжится без backup")
                return None
    else:
        print("⚠️ Автоматический backup доступен только для SQLite")
        print("💡 Для PostgreSQL создайте backup вручную:")
        print("   docker exec supabase-db pg_dump -U postgres postgres > backup.sql")
    
    return None

def check_column_exists(engine, table_name: str, column_name: str) -> bool:
    """Проверить существование столбца в таблице"""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def add_enriched_content_column(engine):
    """Добавить столбец enriched_content в таблицу posts"""
    
    # Проверяем существование столбца
    if check_column_exists(engine, 'posts', 'enriched_content'):
        print("✅ Столбец 'enriched_content' уже существует")
        return True
    
    print("🔄 Добавление столбца enriched_content...")
    
    try:
        with engine.connect() as conn:
            # Для SQLite и PostgreSQL синтаксис одинаковый
            conn.execute(text(
                "ALTER TABLE posts ADD COLUMN enriched_content TEXT"
            ))
            conn.commit()
        
        print("✅ Столбец enriched_content успешно добавлен")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка добавления столбца: {e}")
        return False

def main():
    """Главная функция миграции"""
    print("=" * 60)
    print("Миграция: Добавление поля enriched_content")
    print("=" * 60)
    
    # Получаем URL базы данных
    db_url = get_database_url()
    print(f"📊 База данных: {db_url.split('@')[0] if '@' in db_url else db_url.split('///')[0]}")
    
    # Создаем backup
    backup_path = backup_database()
    
    # Подтверждение
    response = input("\n⚠️ Продолжить миграцию? (yes/no): ")
    if response.lower() not in ['yes', 'y', 'да', 'д']:
        print("❌ Миграция отменена")
        return
    
    # Создаем engine
    engine = create_engine(db_url)
    
    # Выполняем миграцию
    print("\n🚀 Начало миграции...")
    
    success = add_enriched_content_column(engine)
    
    if success:
        print("\n" + "=" * 60)
        print("✅ Миграция завершена успешно!")
        print("=" * 60)
        print("\n💡 Теперь:")
        print("1. Установите CRAWL4AI_ENABLED=true в .env")
        print("2. Новые посты с ссылками будут автоматически обогащаться")
        print("3. RAG-система будет индексировать обогащенный контент")
        if backup_path:
            print(f"\n📦 Backup сохранен: {backup_path}")
    else:
        print("\n" + "=" * 60)
        print("❌ Миграция завершилась с ошибками")
        print("=" * 60)
        if backup_path:
            print(f"\n🔄 Для отката восстановите backup: {backup_path}")
            print("   cp {backup_path} {db_url.replace('sqlite:///', '')}")

if __name__ == "__main__":
    main()

