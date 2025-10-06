from fastapi import FastAPI, HTTPException, Depends
from datetime import datetime, timedelta, timezone
from auth import get_user_client, check_user_auth_status, logout_user, disconnect_all_clients
from database import get_db, SessionLocal
from models import User, Channel, Post
from sqlalchemy.orm import Session
from parser_service import ParserService
import asyncio
from telethon.errors import FloodWaitError

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    try:
        print("✅ Многопользовательская система инициализирована")
        # Создаем таблицы при запуске
        from database import create_tables
        create_tables()
    except Exception as e:
        print(f"❌ Критическая ошибка инициализации: {str(e)}")
        raise HTTPException(500, f"Ошибка инициализации системы: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    try:
        await disconnect_all_clients()
        print("🔌 Все клиенты отключены")
    except Exception as e:
        print(f"❌ Ошибка отключения клиентов: {str(e)}")


# Новые эндпоинты для многопользовательской системы

# Устаревшие эндпоинты аутентификации удалены
# Используйте веб-сервер аутентификации: start_auth_server.py

@app.get("/users/{user_id}/auth_status")
async def get_auth_status(user_id: int, db: Session = Depends(get_db)):
    """Получить статус аутентификации пользователя"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(404, "Пользователь не найден")
        
        return {
            "user_id": user.id,
            "telegram_id": user.telegram_id,
            "is_authenticated": user.is_authenticated,
            "last_auth_check": user.last_auth_check.isoformat() if user.last_auth_check else None,
            "auth_error": user.auth_error
        }
        
    except Exception as e:
        raise HTTPException(500, f"Ошибка получения статуса: {str(e)}")

@app.post("/users/{user_id}/logout")
async def logout_user_endpoint(user_id: int, db: Session = Depends(get_db)):
    """Выход пользователя из системы"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(404, "Пользователь не найден")
        
        await logout_user(user)
        
        return {
            "user_id": user.id,
            "telegram_id": user.telegram_id,
            "status": "logged_out",
            "message": "Пользователь вышел из системы"
        }
        
    except Exception as e:
        raise HTTPException(500, f"Ошибка выхода: {str(e)}")


@app.post("/users/{user_id}/channels/parse")
async def parse_user_channels_endpoint(user_id: int, db: Session = Depends(get_db)):
    """Парсить каналы конкретного пользователя"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(404, "Пользователь не найден")
        
        if not user.is_authenticated:
            raise HTTPException(403, "Пользователь не аутентифицирован")
        
        parser_service = ParserService()
        result = await parser_service.parse_user_channels_by_id(user_id)
        
        if "error" in result:
            raise HTTPException(500, result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Ошибка парсинга каналов: {str(e)}")

@app.get("/users")
async def get_users(db: Session = Depends(get_db)):
    """Получить список всех пользователей"""
    try:
        users = db.query(User).all()
        return {
            "users": [
                {
                    "id": user.id,
                    "telegram_id": user.telegram_id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "created_at": user.created_at.isoformat(),
                    "is_active": user.is_active,
                    "is_authenticated": user.is_authenticated,
                    "last_auth_check": user.last_auth_check.isoformat() if user.last_auth_check else None
                }
                for user in users
            ]
        }
    except Exception as e:
        raise HTTPException(500, f"Ошибка получения пользователей: {str(e)}")


@app.get("/users/{telegram_id}/channels")
async def get_user_channels(telegram_id: int, db: Session = Depends(get_db)):
    """Получить каналы конкретного пользователя"""
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            raise HTTPException(404, "Пользователь не найден")
        
        channels = db.query(Channel).filter(Channel.user_id == user.id).all()
        return {
            "user_id": user.id,
            "telegram_id": user.telegram_id,
            "username": user.username,
            "is_authenticated": user.is_authenticated,
            "channels": [
                {
                    "id": channel.id,
                    "channel_username": channel.channel_username,
                    "channel_id": channel.channel_id,
                    "channel_title": channel.channel_title,
                    "is_active": channel.is_active,
                    "created_at": channel.created_at.isoformat(),
                    "last_parsed_at": channel.last_parsed_at.isoformat() if channel.last_parsed_at else None
                }
                for channel in channels
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Ошибка получения каналов: {str(e)}")


@app.get("/users/{telegram_id}/posts")
async def get_user_posts(
    telegram_id: int, 
    hours_back: int = 24,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Получить посты конкретного пользователя"""
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            raise HTTPException(404, "Пользователь не найден")
        
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(hours=hours_back)
        
        posts = db.query(Post).filter(
            Post.user_id == user.id,
            Post.posted_at >= start_date
        ).order_by(Post.posted_at.desc()).limit(limit).all()
        
        return {
            "user_id": user.id,
            "telegram_id": user.telegram_id,
            "username": user.username,
            "is_authenticated": user.is_authenticated,
            "period_hours": hours_back,
            "post_count": len(posts),
            "posts": [
                {
                    "id": post.id,
                    "channel_username": post.channel.channel_username,
                    "telegram_message_id": post.telegram_message_id,
                    "text": post.text,
                    "views": post.views,
                    "url": post.url,
                    "posted_at": post.posted_at.isoformat(),
                    "parsed_at": post.parsed_at.isoformat()
                }
                for post in posts
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Ошибка получения постов: {str(e)}")


@app.post("/parse_all_channels")
async def parse_all_channels_endpoint(db: Session = Depends(get_db)):
    """Парсить все активные каналы всех аутентифицированных пользователей"""
    try:
        parser_service = ParserService()
        await parser_service.parse_all_channels()
        
        return {
            "status": "success",
            "message": "Парсинг всех каналов запущен"
        }
        
    except Exception as e:
        raise HTTPException(500, f"Ошибка парсинга каналов: {str(e)}")