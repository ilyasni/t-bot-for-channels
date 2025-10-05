from fastapi import FastAPI, HTTPException, Depends
from datetime import datetime, timedelta, timezone
from auth import get_client
from database import get_db, SessionLocal
from models import User, Channel, Post
from sqlalchemy.orm import Session
import asyncio
from telethon.errors import FloodWaitError

app = FastAPI()
client = None

@app.on_event("startup")
async def startup_event():
    global client
    try:
        # Используем улучшенную функцию get_client с настройками повторных попыток
        client = await get_client(max_retries=5, base_delay=3)
        
        if client and client.is_connected():
            print("✅ Успешное подключение к Telegram API")
        else:
            print("❌ Не удалось подключиться к Telegram API")
            raise HTTPException(500, "Не удалось подключиться к Telegram API")
            
    except Exception as e:
        print(f"❌ Критическая ошибка подключения: {str(e)}")
        raise HTTPException(500, f"Не удалось подключиться к Telegram: {str(e)}")
    
    # Создаем таблицы при запуске
    from database import create_tables
    create_tables()

@app.on_event("shutdown")
async def shutdown_event():
    if client and client.is_connected():
        await client.disconnect()


@app.get("/get_recent_posts")
async def get_recent_posts(
    channel: str,
    hours_back: int = 24,
    limit: int = 100
):
    if not client or not client.is_connected():
        raise HTTPException(503, "Telegram client not connected")
    
    try:
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(hours=hours_back)
        
        posts = []
        async for message in client.iter_messages(
            channel,
            limit=limit,
            offset_date=end_date,
            reverse=False
        ):
            message_date = message.date.replace(tzinfo=timezone.utc)
            if message_date < start_date:
                break
                
            if message.text:
                # Формируем ссылку на пост
                if isinstance(channel, str) and channel.startswith('@'):
                    channel_username = channel[1:]
                else:
                    # Если channel передан как ID, попробуем получить username
                    try:
                        entity = await client.get_entity(channel)
                        channel_username = entity.username
                    except:
                        channel_username = str(channel)
                
                post_url = f"https://t.me/{channel_username}/{message.id}"
                
                posts.append({
                    "id": message.id,
                    "date": message_date.isoformat(),
                    "text": message.text,
                    "views": getattr(message, 'views', None),
                    "url": post_url  # Добавляем URL поста
                })
        
        return {
            "channel": channel,
            "period_hours": hours_back,
            "post_count": len(posts),
            "posts": sorted(posts, key=lambda x: x['date'], reverse=True)
        }
        
    except Exception as e:
        raise HTTPException(500, f"Error processing request: {str(e)}")


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
                    "is_active": user.is_active
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
async def parse_all_channels(db: Session = Depends(get_db)):
    """Парсить все активные каналы всех пользователей"""
    if not client or not client.is_connected():
        raise HTTPException(503, "Telegram client not connected")
    
    try:
        # Получаем все активные каналы
        channels = db.query(Channel).filter(Channel.is_active == True).all()
        
        total_posts = 0
        results = []
        
        for channel in channels:
            try:
                channel_posts = await parse_channel_posts(channel, db)
                total_posts += channel_posts
                results.append({
                    "channel": channel.channel_username,
                    "posts_added": channel_posts,
                    "status": "success"
                })
            except Exception as e:
                results.append({
                    "channel": channel.channel_username,
                    "posts_added": 0,
                    "status": "error",
                    "error": str(e)
                })
        
        return {
            "total_channels": len(channels),
            "total_posts_added": total_posts,
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(500, f"Ошибка парсинга каналов: {str(e)}")


async def parse_channel_posts(channel: Channel, db: Session):
    """Парсить посты для конкретного канала"""
    try:
        # Получаем последний парсинг
        last_parsed = channel.last_parsed_at or datetime.now(timezone.utc) - timedelta(hours=24)
        
        # Получаем новые сообщения
        posts_added = 0
        async for message in client.iter_messages(
            f"@{channel.channel_username}",
            limit=100,
            offset_date=datetime.now(timezone.utc),
            reverse=False
        ):
            message_date = message.date.replace(tzinfo=timezone.utc)
            
            # Проверяем, не парсили ли мы уже это сообщение
            if message_date <= last_parsed:
                break
            
            if message.text:
                # Проверяем, существует ли уже такой пост
                existing_post = db.query(Post).filter(
                    Post.user_id == channel.user_id,
                    Post.channel_id == channel.id,
                    Post.telegram_message_id == message.id
                ).first()
                
                if not existing_post:
                    # Формируем URL поста
                    post_url = f"https://t.me/{channel.channel_username}/{message.id}"
                    
                    # Создаем новый пост
                    new_post = Post(
                        user_id=channel.user_id,
                        channel_id=channel.id,
                        telegram_message_id=message.id,
                        text=message.text,
                        views=getattr(message, 'views', None),
                        url=post_url,
                        posted_at=message_date
                    )
                    db.add(new_post)
                    posts_added += 1
        
        # Обновляем время последнего парсинга
        channel.last_parsed_at = datetime.now(timezone.utc)
        db.commit()
        
        return posts_added
        
    except Exception as e:
        db.rollback()
        raise e