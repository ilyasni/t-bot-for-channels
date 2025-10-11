#!/usr/bin/env python3
"""
Скрипт миграции базы данных для безопасной системы аутентификации
Добавляет новые колонки в существующую таблицу users
"""

import logging
import os
import sys
from sqlalchemy import text, inspect
from sqlalchemy.exc import OperationalError

# Добавляем текущую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import engine, SessionLocal
from models import Base, User
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_column_exists(table_name, column_name):
    """Проверяет существование колонки в таблице"""
    try:
        with engine.connect() as conn:
            inspector = inspect(engine)
            columns = [col['name'] for col in inspector.get_columns(table_name)]
            return column_name in columns
    except Exception as e:
        logger.error(f"❌ Ошибка проверки колонки {column_name}: {str(e)}")
        return False

def add_column_if_not_exists(table_name, column_name, column_type, default_value=None):
    """Добавляет колонку если она не существует"""
    try:
        if check_column_exists(table_name, column_name):
            logger.info(f"✅ Колонка {column_name} уже существует")
            return True
        
        with engine.connect() as conn:
            if default_value is not None:
                sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type} DEFAULT {default_value}"
            else:
                sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
            
            conn.execute(text(sql))
            conn.commit()
            
            logger.info(f"✅ Добавлена колонка {column_name}")
            return True
            
    except Exception as e:
        logger.error(f"❌ Ошибка добавления колонки {column_name}: {str(e)}")
        return False

def migrate_database():
    """Выполняет миграцию базы данных"""
    logger.info("🔄 Начало миграции базы данных...")
    
    try:
        # Проверяем подключение к БД
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ Подключение к базе данных успешно")
        
        # Список новых колонок для добавления
        new_columns = [
            ("auth_session_id", "VARCHAR", None),
            ("auth_session_expires", "TIMESTAMP", None),
            ("failed_auth_attempts", "INTEGER", 0),
            ("last_auth_attempt", "TIMESTAMP", None),
            ("is_blocked", "BOOLEAN", False),
            ("block_expires", "TIMESTAMP", None),
        ]
        
        # Добавляем каждую колонку
        success_count = 0
        for column_name, column_type, default_value in new_columns:
            if add_column_if_not_exists("users", column_name, column_type, default_value):
                success_count += 1
        
        logger.info(f"✅ Миграция завершена: {success_count}/{len(new_columns)} колонок добавлено")
        
        # Проверяем что все колонки добавлены
        missing_columns = []
        for column_name, _, _ in new_columns:
            if not check_column_exists("users", column_name):
                missing_columns.append(column_name)
        
        if missing_columns:
            logger.error(f"❌ Не удалось добавить колонки: {missing_columns}")
            return False
        else:
            logger.info("✅ Все колонки успешно добавлены")
            return True
            
    except Exception as e:
        logger.error(f"❌ Критическая ошибка миграции: {str(e)}")
        return False

def encrypt_existing_data():
    """Шифрует существующие данные в базе"""
    logger.info("🔐 Начало шифрования существующих данных...")
    
    try:
        from crypto_utils import crypto_manager
        
        db = SessionLocal()
        
        # Получаем пользователей с незашифрованными данными
        users = db.query(User).filter(
            User.api_hash.isnot(None),
            User.api_hash != ''
        ).all()
        
        encrypted_count = 0
        
        for user in users:
            try:
                # Проверяем нужно ли шифровать API hash
                if user.api_hash and not isinstance(user.api_hash, bytes):
                    try:
                        logger.info(f"🔐 Шифрование API hash для пользователя {user.telegram_id}")
                        user.set_encrypted_api_hash(user.api_hash)
                        encrypted_count += 1
                    except Exception as e:
                        logger.error(f"❌ Ошибка шифрования API hash для пользователя {user.telegram_id}: {str(e)}")
                
                # Проверяем нужно ли шифровать номер телефона
                if user.phone_number and not isinstance(user.phone_number, bytes):
                    try:
                        logger.info(f"🔐 Шифрование номера телефона для пользователя {user.telegram_id}")
                        user.set_encrypted_phone_number(user.phone_number)
                        encrypted_count += 1
                    except Exception as e:
                        logger.error(f"❌ Ошибка шифрования номера телефона для пользователя {user.telegram_id}: {str(e)}")
                    
            except Exception as e:
                logger.error(f"❌ Ошибка шифрования данных пользователя {user.telegram_id}: {str(e)}")
        
        db.commit()
        db.close()
        
        logger.info(f"✅ Шифрование завершено: {encrypted_count} полей зашифровано")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка шифрования данных: {str(e)}")
        return False

def verify_migration():
    """Проверяет успешность миграции"""
    logger.info("🔍 Проверка миграции...")
    
    try:
        db = SessionLocal()
        
        # Пытаемся выполнить запрос к новой модели
        user = db.query(User).first()
        if user:
            # Проверяем доступность новых полей
            _ = user.auth_session_id
            _ = user.auth_session_expires
            _ = user.failed_auth_attempts
            _ = user.last_auth_attempt
            _ = user.is_blocked
            _ = user.block_expires
            
            logger.info("✅ Миграция прошла успешно - все поля доступны")
            return True
        else:
            logger.info("ℹ️ В базе нет пользователей для проверки")
            return True
            
    except Exception as e:
        logger.error(f"❌ Ошибка проверки миграции: {str(e)}")
        return False
    finally:
        db.close()

def main():
    """Главная функция миграции"""
    logger.info("🚀 Запуск миграции базы данных для безопасной системы аутентификации")
    logger.info("=" * 70)
    
    try:
        # Шаг 1: Миграция структуры БД
        logger.info("📊 Шаг 1: Добавление новых колонок...")
        if not migrate_database():
            logger.error("❌ Миграция структуры БД не удалась")
            return False
        
        # Шаг 2: Шифрование существующих данных
        logger.info("🔐 Шаг 2: Шифрование существующих данных...")
        if not encrypt_existing_data():
            logger.error("❌ Шифрование данных не удалось")
            return False
        
        # Шаг 3: Проверка миграции
        logger.info("🔍 Шаг 3: Проверка миграции...")
        if not verify_migration():
            logger.error("❌ Проверка миграции не удалась")
            return False
        
        logger.info("=" * 70)
        logger.info("🎉 Миграция успешно завершена!")
        logger.info("✅ База данных готова для безопасной системы аутентификации")
        logger.info("🚀 Теперь можно запускать обновленную систему")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка миграции: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
