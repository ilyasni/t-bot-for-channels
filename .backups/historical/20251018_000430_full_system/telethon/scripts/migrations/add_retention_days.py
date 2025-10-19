"""
Скрипт миграции: Добавление поля retention_days в таблицу users

Этот скрипт добавляет колонку retention_days со значением по умолчанию 30 дней
в таблицу users для настройки периода хранения постов.

Поддерживает SQLite и PostgreSQL.

Использование:
    python add_retention_days.py
"""

import os
import sys
from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv

load_dotenv()

# Получаем URL базы данных
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/telethon_bot.db")

# Если используется PostgreSQL, добавляем поддержку SSL
if DATABASE_URL.startswith("postgresql://"):
    if "?sslmode=" not in DATABASE_URL:
        DATABASE_URL += "?sslmode=require"

def check_column_exists(engine, table_name, column_name):
    """Проверяет, существует ли колонка в таблице"""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def add_retention_days_column():
    """Добавление колонки retention_days в таблицу users"""
    try:
        # Создаем подключение к базе данных
        engine = create_engine(DATABASE_URL)
        
        print(f"🔗 Подключение к базе данных: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL}")
        
        # Проверяем, существует ли колонка
        if check_column_exists(engine, 'users', 'retention_days'):
            print("✅ Колонка 'retention_days' уже существует в таблице 'users'")
            print("ℹ️  Миграция не требуется")
            return True
        
        print("📝 Добавление колонки 'retention_days' в таблицу 'users'...")
        
        # Определяем тип базы данных
        is_sqlite = DATABASE_URL.startswith("sqlite://")
        is_postgresql = DATABASE_URL.startswith("postgresql://")
        
        with engine.connect() as conn:
            if is_sqlite:
                # SQLite синтаксис
                sql = text("ALTER TABLE users ADD COLUMN retention_days INTEGER DEFAULT 30")
                conn.execute(sql)
                conn.commit()
                print("✅ Колонка 'retention_days' успешно добавлена (SQLite)")
                
            elif is_postgresql:
                # PostgreSQL синтаксис
                sql = text("ALTER TABLE users ADD COLUMN retention_days INTEGER DEFAULT 30")
                conn.execute(sql)
                conn.commit()
                print("✅ Колонка 'retention_days' успешно добавлена (PostgreSQL)")
                
            else:
                print("❌ Неподдерживаемый тип базы данных")
                return False
        
        # Проверяем, что колонка добавлена
        if check_column_exists(engine, 'users', 'retention_days'):
            print("✅ Миграция успешно завершена!")
            print("ℹ️  Все пользователи получили значение retention_days = 30 дней")
            
            # Выводим количество пользователей
            with engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM users"))
                user_count = result.scalar()
                print(f"📊 Обновлено записей пользователей: {user_count}")
            
            return True
        else:
            print("❌ Ошибка: колонка не была добавлена")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка миграции: {str(e)}")
        return False

def rollback_migration():
    """Откат миграции: удаление колонки retention_days"""
    try:
        engine = create_engine(DATABASE_URL)
        
        print(f"🔗 Подключение к базе данных для отката...")
        
        # Проверяем, существует ли колонка
        if not check_column_exists(engine, 'users', 'retention_days'):
            print("ℹ️  Колонка 'retention_days' не существует, откат не требуется")
            return True
        
        print("⚠️  Откат миграции: удаление колонки 'retention_days'...")
        
        is_sqlite = DATABASE_URL.startswith("sqlite://")
        is_postgresql = DATABASE_URL.startswith("postgresql://")
        
        with engine.connect() as conn:
            if is_postgresql:
                # PostgreSQL поддерживает DROP COLUMN
                sql = text("ALTER TABLE users DROP COLUMN retention_days")
                conn.execute(sql)
                conn.commit()
                print("✅ Колонка 'retention_days' успешно удалена (PostgreSQL)")
                
            elif is_sqlite:
                # SQLite не поддерживает DROP COLUMN напрямую
                print("⚠️  SQLite не поддерживает DROP COLUMN")
                print("ℹ️  Для отката в SQLite требуется пересоздание таблицы")
                print("ℹ️  Используйте восстановление из резервной копии")
                return False
            else:
                print("❌ Неподдерживаемый тип базы данных")
                return False
        
        print("✅ Откат миграции успешно завершен")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка отката: {str(e)}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Миграция базы данных: Добавление retention_days")
    print("=" * 60)
    print()
    
    # Проверяем аргументы командной строки
    if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
        print("⚠️  РЕЖИМ ОТКАТА МИГРАЦИИ")
        print()
        response = input("Вы уверены, что хотите откатить миграцию? (yes/no): ")
        if response.lower() == "yes":
            success = rollback_migration()
        else:
            print("❌ Откат отменен пользователем")
            success = False
    else:
        # Создаем резервную копию для SQLite
        if DATABASE_URL.startswith("sqlite://"):
            db_path = DATABASE_URL.replace("sqlite:///", "")
            if os.path.exists(db_path):
                import shutil
                backup_path = f"{db_path}.backup_{os.path.getmtime(db_path)}"
                shutil.copy2(db_path, backup_path)
                print(f"💾 Создана резервная копия: {backup_path}")
                print()
        
        success = add_retention_days_column()
    
    print()
    print("=" * 60)
    if success:
        print("✅ Операция завершена успешно")
    else:
        print("❌ Операция завершена с ошибками")
    print("=" * 60)
    
    sys.exit(0 if success else 1)

