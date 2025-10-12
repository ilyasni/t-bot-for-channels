#!/usr/bin/env python3
"""
Миграция БД: Добавление системы ролей и подписок

Добавляет:
- Новые поля в таблицу users (role, subscription_type, etc.)
- Таблицу invite_codes
- Таблицу subscription_history

Использование:
    python scripts/migrations/add_roles_and_subscriptions.py
"""

import sys
import os
from pathlib import Path

# Добавляем корневую директорию в PYTHONPATH
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from sqlalchemy import create_engine, text, inspect
from datetime import datetime, timezone
import logging
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_database_url():
    """Получить URL базы данных - ТОЛЬКО PostgreSQL"""
    db_url = os.getenv("TELEGRAM_DATABASE_URL")
    if not db_url:
        raise ValueError(
            "❌ TELEGRAM_DATABASE_URL не установлен!\n"
            "Установите в .env:\n"
            "TELEGRAM_DATABASE_URL=postgresql://postgres:password@supabase-db:5432/postgres?sslmode=disable"
        )
    
    if not db_url.startswith("postgresql://"):
        raise ValueError(
            f"❌ Поддерживается только PostgreSQL!\n"
            f"Текущий URL: {db_url}"
        )
    
    return db_url


def backup_database(engine):
    """Создать бэкап базы данных"""
    if "sqlite" in str(engine.url):
        import shutil
        db_path = str(engine.url).replace("sqlite:///", "")
        backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if os.path.exists(db_path):
            shutil.copy2(db_path, backup_path)
            logger.info(f"✅ Создан бэкап: {backup_path}")
            return backup_path
    return None


def column_exists(engine, table_name, column_name):
    """Проверка существования столбца"""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def table_exists(engine, table_name):
    """Проверка существования таблицы"""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def add_user_fields(engine):
    """Добавить новые поля в таблицу users"""
    logger.info("📝 Добавление новых полей в таблицу users...")
    
    # Определяем тип для дат в зависимости от БД
    datetime_type = "TIMESTAMP" if "postgresql" in str(engine.url) else "DATETIME"
    
    fields_to_add = [
        ("role", "VARCHAR", "user"),
        ("subscription_type", "VARCHAR", "free"),
        ("subscription_expires", datetime_type, None),
        ("subscription_started_at", datetime_type, None),
        ("max_channels", "INTEGER", 3),
        ("invited_by", "INTEGER", None),
    ]
    
    for field_name, field_type, default_value in fields_to_add:
        if not column_exists(engine, "users", field_name):
            if default_value is not None:
                if isinstance(default_value, str):
                    default_clause = f"DEFAULT '{default_value}'"
                else:
                    default_clause = f"DEFAULT {default_value}"
            else:
                default_clause = ""
            
            try:
                with engine.connect() as conn:
                    conn.execute(text(f"ALTER TABLE users ADD COLUMN {field_name} {field_type} {default_clause}"))
                    conn.commit()
                    logger.info(f"  ✅ Добавлено поле: {field_name}")
            except Exception as e:
                logger.warning(f"  ⚠️ Поле {field_name} возможно уже существует: {e}")
        else:
            logger.info(f"  ℹ️ Поле {field_name} уже существует")


def create_invite_codes_table(engine):
    """Создать таблицу invite_codes"""
    logger.info("📝 Создание таблицы invite_codes...")
    
    if table_exists(engine, "invite_codes"):
        logger.info("  ℹ️ Таблица invite_codes уже существует")
        return
    
    # Определяем тип для дат
    datetime_type = "TIMESTAMP" if "postgresql" in str(engine.url) else "DATETIME"
    
    create_table_sql = f"""
    CREATE TABLE invite_codes (
        code VARCHAR PRIMARY KEY,
        created_by INTEGER NOT NULL,
        created_at {datetime_type} NOT NULL,
        used_by INTEGER,
        used_at {datetime_type},
        expires_at {datetime_type} NOT NULL,
        max_uses INTEGER DEFAULT 1,
        uses_count INTEGER DEFAULT 0,
        default_subscription VARCHAR DEFAULT 'free',
        default_trial_days INTEGER DEFAULT 0,
        FOREIGN KEY (created_by) REFERENCES users(id),
        FOREIGN KEY (used_by) REFERENCES users(id)
    )
    """
    
    with engine.connect() as conn:
        conn.execute(text(create_table_sql))
        conn.commit()
        logger.info("  ✅ Таблица invite_codes создана")
    
    # Создаем индексы
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_invite_codes_created_by ON invite_codes(created_by)",
        "CREATE INDEX IF NOT EXISTS idx_invite_codes_used_by ON invite_codes(used_by)"
    ]
    
    for idx_sql in indexes:
        try:
            with engine.connect() as conn:
                conn.execute(text(idx_sql))
                conn.commit()
        except Exception as e:
            logger.warning(f"  ⚠️ Ошибка создания индекса: {e}")
    
    logger.info("  ✅ Индексы для invite_codes созданы")


def create_subscription_history_table(engine):
    """Создать таблицу subscription_history"""
    logger.info("📝 Создание таблицы subscription_history...")
    
    if table_exists(engine, "subscription_history"):
        logger.info("  ℹ️ Таблица subscription_history уже существует")
        return
    
    # Определяем тип для дат и автоинкремент
    datetime_type = "TIMESTAMP" if "postgresql" in str(engine.url) else "DATETIME"
    autoincrement = "SERIAL PRIMARY KEY" if "postgresql" in str(engine.url) else "INTEGER PRIMARY KEY AUTOINCREMENT"
    
    create_table_sql = f"""
    CREATE TABLE subscription_history (
        id {autoincrement},
        user_id INTEGER NOT NULL,
        action VARCHAR NOT NULL,
        old_type VARCHAR,
        new_type VARCHAR NOT NULL,
        changed_by INTEGER,
        changed_at {datetime_type} NOT NULL,
        notes TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (changed_by) REFERENCES users(id)
    )
    """
    
    with engine.connect() as conn:
        conn.execute(text(create_table_sql))
        conn.commit()
        logger.info("  ✅ Таблица subscription_history создана")
    
    # Создаем индексы
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_subscription_history_user_id ON subscription_history(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_subscription_history_changed_at ON subscription_history(changed_at)"
    ]
    
    for idx_sql in indexes:
        try:
            with engine.connect() as conn:
                conn.execute(text(idx_sql))
                conn.commit()
        except Exception as e:
            logger.warning(f"  ⚠️ Ошибка создания индекса: {e}")
    
    logger.info("  ✅ Индексы для subscription_history созданы")


def assign_first_admin(engine):
    """Назначить первого администратора"""
    logger.info("👑 Назначение первого администратора...")
    
    admin_ids = os.getenv("ADMIN_TELEGRAM_IDS", "").split(",")
    if not admin_ids or not admin_ids[0]:
        logger.warning("  ⚠️ ADMIN_TELEGRAM_IDS не установлен в .env")
        return
    
    first_admin_id = admin_ids[0].strip()
    
    with engine.connect() as conn:
        # Проверяем существует ли пользователь
        result = conn.execute(
            text("SELECT id, telegram_id, first_name FROM users WHERE telegram_id = :telegram_id"),
            {"telegram_id": int(first_admin_id)}
        )
        user = result.fetchone()
        
        if user:
            # Назначаем администратором
            conn.execute(
                text("UPDATE users SET role = 'admin' WHERE telegram_id = :telegram_id"),
                {"telegram_id": int(first_admin_id)}
            )
            conn.commit()
            logger.info(f"  ✅ Пользователь {user[2]} ({first_admin_id}) назначен администратором")
        else:
            logger.warning(f"  ⚠️ Пользователь с telegram_id {first_admin_id} не найден в БД")
            logger.info(f"  💡 Администратор будет назначен автоматически при первом запуске /start")


def migrate_existing_users(engine):
    """Миграция существующих пользователей"""
    logger.info("🔄 Миграция существующих пользователей...")
    
    with engine.connect() as conn:
        # Устанавливаем дефолтные значения для существующих пользователей
        result = conn.execute(text("SELECT COUNT(*) FROM users"))
        count = result.fetchone()[0]
        
        if count > 0:
            # Обновляем существующих пользователей с NULL значениями
            conn.execute(text("""
                UPDATE users 
                SET 
                    role = COALESCE(role, 'user'),
                    subscription_type = COALESCE(subscription_type, 'free'),
                    max_channels = COALESCE(max_channels, 3)
                WHERE role IS NULL OR subscription_type IS NULL OR max_channels IS NULL
            """))
            conn.commit()
            logger.info(f"  ✅ Обновлено {count} существующих пользователей")


def main():
    """Главная функция миграции"""
    logger.info("=" * 60)
    logger.info("🚀 Начало миграции: Роли и подписки")
    logger.info("=" * 60)
    
    try:
        # Получаем URL БД
        db_url = get_database_url()
        logger.info(f"📊 База данных: {db_url}")
        
        # Создаем engine
        engine = create_engine(db_url)
        
        # Создаем бэкап
        backup_path = backup_database(engine)
        
        # Выполняем миграцию
        add_user_fields(engine)
        create_invite_codes_table(engine)
        create_subscription_history_table(engine)
        migrate_existing_users(engine)
        assign_first_admin(engine)
        
        logger.info("=" * 60)
        logger.info("✅ Миграция успешно завершена!")
        logger.info("=" * 60)
        
        if backup_path:
            logger.info(f"💡 Бэкап сохранен: {backup_path}")
        
        logger.info("\n📋 Следующие шаги:")
        logger.info("1. Установите MASTER_API_ID и MASTER_API_HASH в .env")
        logger.info("2. Установите ADMIN_TELEGRAM_IDS в .env")
        logger.info("3. Перезапустите бота")
        logger.info("4. Используйте /admin_invite для создания инвайт кодов")
        
    except Exception as e:
        logger.error(f"❌ Ошибка миграции: {e}")
        logger.error("💡 Восстановите БД из бэкапа если необходимо")
        sys.exit(1)


if __name__ == "__main__":
    main()

