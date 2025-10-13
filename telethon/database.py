from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Конфигурация базы данных - ТОЛЬКО PostgreSQL (Supabase)
DATABASE_URL = os.getenv("TELEGRAM_DATABASE_URL")

if not DATABASE_URL:
    raise ValueError(
        "❌ TELEGRAM_DATABASE_URL не установлен!\n"
        "Установите в .env:\n"
        "TELEGRAM_DATABASE_URL=postgresql://postgres:password@supabase-db:5432/postgres?sslmode=disable"
    )

if not DATABASE_URL.startswith("postgresql://"):
    raise ValueError(
        f"❌ Поддерживается только PostgreSQL!\n"
        f"Текущий DATABASE_URL: {DATABASE_URL}\n"
        f"Используйте: postgresql://..."
    )

logger.info(f"📊 Database: PostgreSQL (Supabase)")

engine = create_engine(
    DATABASE_URL,
    pool_size=20,           # Connection pool для production
    max_overflow=10,
    pool_pre_ping=True,     # Проверка соединения перед использованием
    pool_recycle=3600       # Пересоздавать соединения каждый час
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Создание таблиц
def create_tables():
    from models import Base
    Base.metadata.create_all(bind=engine)

# Dependency для получения сессии БД
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 