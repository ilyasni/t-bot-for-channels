from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

# Конфигурация базы данных
# Поддерживаем как SQLite, так и PostgreSQL (Supabase)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./telethon_bot.db")

# Если используется PostgreSQL, добавляем поддержку SSL
if DATABASE_URL.startswith("postgresql://"):
    # Для Supabase обычно требуется SSL
    if "?sslmode=" not in DATABASE_URL:
        DATABASE_URL += "?sslmode=require"

engine = create_engine(DATABASE_URL)
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