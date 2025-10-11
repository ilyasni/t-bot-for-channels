from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from datetime import datetime, timedelta, timezone
from auth import get_user_client, check_user_auth_status, logout_user, disconnect_all_clients
from database import get_db, SessionLocal
from models import User, Channel, Post
from sqlalchemy.orm import Session
from sqlalchemy import func
from parser_service import ParserService
from pydantic import BaseModel, Field
import asyncio
from telethon.errors import FloodWaitError
import os
try:
    import zoneinfo
except ImportError:
    from backports import zoneinfo

app = FastAPI()

# Локальная таймзона для конвертации datetime
LOCAL_TZ_NAME = os.getenv('TZ', 'Europe/Moscow')
try:
    LOCAL_TZ = zoneinfo.ZoneInfo(LOCAL_TZ_NAME)
except Exception:
    # Fallback для MSK (UTC+3)
    LOCAL_TZ = timezone(timedelta(hours=3))

def to_local_time(dt: datetime) -> str:
    """
    Конвертирует datetime из UTC в локальную таймзону и возвращает ISO строку
    
    Args:
        dt: datetime объект (может быть с timezone или без)
        
    Returns:
        ISO строка в локальной таймзоне
    """
    if dt is None:
        return None
    
    # Если datetime без timezone, считаем что это UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    # Конвертируем в локальную таймзону
    local_dt = dt.astimezone(LOCAL_TZ)
    return local_dt.isoformat()

# Pydantic модели для запросов
class RetentionSettingsUpdate(BaseModel):
    retention_days: int = Field(..., ge=1, le=365, description="Период хранения постов в днях (от 1 до 365)")
    run_cleanup_immediately: bool = Field(False, description="Запустить очистку немедленно после изменения")

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
            "last_auth_check": to_local_time(user.last_auth_check),
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
async def get_users(
    authenticated_only: bool = False,
    active_only: bool = False,
    db: Session = Depends(get_db)
):
    """
    Получить список пользователей
    
    Параметры:
    - authenticated_only: если True, вернуть только аутентифицированных пользователей
    - active_only: если True, вернуть только активных пользователей
    """
    try:
        query = db.query(User)
        
        # Фильтрация по аутентификации
        if authenticated_only:
            query = query.filter(User.is_authenticated == True)
        
        # Фильтрация по активности
        if active_only:
            query = query.filter(User.is_active == True)
        
        users = query.all()
        
        return {
            "total": len(users),
            "filters": {
                "authenticated_only": authenticated_only,
                "active_only": active_only
            },
            "users": [
                {
                    "id": user.id,
                    "telegram_id": user.telegram_id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "created_at": to_local_time(user.created_at),
                    "is_active": user.is_active,
                    "is_authenticated": user.is_authenticated,
                    "last_auth_check": to_local_time(user.last_auth_check)
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
        
        # Получаем каналы с информацией о подписке
        channels_with_info = user.get_all_channels(db)
        
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
                    "is_active": sub_info['is_active'],
                    "created_at": to_local_time(channel.created_at),
                    "subscription_created_at": to_local_time(sub_info['created_at']),
                    "last_parsed_at": to_local_time(sub_info['last_parsed_at'])
                }
                for channel, sub_info in channels_with_info
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
                    "posted_at": to_local_time(post.posted_at),
                    "parsed_at": to_local_time(post.parsed_at),
                    "tags": post.tags
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


# ============================================================================
# Endpoints для тегирования постов
# ============================================================================

@app.post("/posts/{post_id}/generate_tags")
async def generate_tags_for_post(post_id: int, db: Session = Depends(get_db)):
    """
    Генерация тегов для конкретного поста
    
    Args:
        post_id: ID поста
    """
    try:
        from tagging_service import tagging_service
        
        # Проверяем существование поста
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post:
            raise HTTPException(404, "Пост не найден")
        
        if not post.text:
            raise HTTPException(400, "Пост не содержит текста для тегирования")
        
        # Генерируем теги
        success = await tagging_service.update_post_tags(post_id, db)
        
        if success:
            # Обновляем данные поста
            db.refresh(post)
            return {
                "status": "success",
                "post_id": post.id,
                "tags": post.tags,
                "message": "Теги успешно сгенерированы"
            }
        else:
            raise HTTPException(500, "Не удалось сгенерировать теги")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Ошибка генерации тегов: {str(e)}")


@app.post("/users/{telegram_id}/posts/generate_tags")
async def generate_tags_for_user_posts(
    telegram_id: int,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Генерация тегов для всех постов пользователя без тегов
    
    Args:
        telegram_id: Telegram ID пользователя
        limit: Максимальное количество постов для обработки
    """
    try:
        from tagging_service import tagging_service
        
        # Проверяем существование пользователя
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            raise HTTPException(404, "Пользователь не найден")
        
        # Получаем посты без тегов
        posts = db.query(Post).filter(
            Post.user_id == user.id,
            Post.tags == None,
            Post.text != None
        ).limit(limit).all()
        
        if not posts:
            return {
                "status": "success",
                "user_id": user.id,
                "telegram_id": user.telegram_id,
                "posts_processed": 0,
                "message": "Все посты уже имеют теги"
            }
        
        post_ids = [post.id for post in posts]
        
        # Запускаем фоновую обработку
        asyncio.create_task(tagging_service.process_posts_batch(post_ids))
        
        return {
            "status": "success",
            "user_id": user.id,
            "telegram_id": user.telegram_id,
            "posts_to_process": len(post_ids),
            "message": f"Запущено тегирование {len(post_ids)} постов"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Ошибка запуска тегирования: {str(e)}")


@app.get("/posts/tags/stats")
async def get_tags_statistics(db: Session = Depends(get_db)):
    """
    Получить статистику по тегам
    
    Возвращает общее количество постов с тегами и без тегов
    """
    try:
        total_posts = db.query(Post).count()
        posts_with_tags = db.query(Post).filter(Post.tags != None).count()
        posts_without_tags = db.query(Post).filter(Post.tags == None).count()
        
        # Получаем все уникальные теги
        posts_with_tags_list = db.query(Post).filter(Post.tags != None).all()
        all_tags = {}
        
        for post in posts_with_tags_list:
            if post.tags:
                for tag in post.tags:
                    if tag in all_tags:
                        all_tags[tag] += 1
                    else:
                        all_tags[tag] = 1
        
        # Топ-20 тегов
        top_tags = sorted(all_tags.items(), key=lambda x: x[1], reverse=True)[:20]
        
        return {
            "total_posts": total_posts,
            "posts_with_tags": posts_with_tags,
            "posts_without_tags": posts_without_tags,
            "unique_tags_count": len(all_tags),
            "top_tags": [
                {"tag": tag, "count": count}
                for tag, count in top_tags
            ]
        }
        
    except Exception as e:
        raise HTTPException(500, f"Ошибка получения статистики: {str(e)}")


# ============================================================================
# Endpoints для управления периодом хранения постов
# ============================================================================

@app.get("/users/{user_id}/retention_settings")
async def get_retention_settings(user_id: int, db: Session = Depends(get_db)):
    """
    Получить настройки хранения постов пользователя
    
    Args:
        user_id: ID пользователя
        
    Returns:
        Настройки хранения постов, количество постов и дата самого старого поста
    """
    try:
        # Проверяем существование пользователя
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(404, "Пользователь не найден")
        
        # Получаем статистику постов пользователя
        total_posts = db.query(Post).filter(Post.user_id == user_id).count()
        
        # Получаем самый старый пост
        oldest_post = db.query(func.min(Post.posted_at)).filter(
            Post.user_id == user_id
        ).scalar()
        
        # Получаем самый новый пост
        newest_post = db.query(func.max(Post.posted_at)).filter(
            Post.user_id == user_id
        ).scalar()
        
        # Статистика по каналам
        from sqlalchemy import select
        from models import user_channel
        
        # Общее количество подписок пользователя
        channels_count_stmt = select(func.count()).select_from(user_channel).where(
            user_channel.c.user_id == user_id
        )
        channels_count = db.execute(channels_count_stmt).scalar()
        
        # Количество активных подписок
        active_channels_count_stmt = select(func.count()).select_from(user_channel).where(
            user_channel.c.user_id == user_id,
            user_channel.c.is_active == True
        )
        active_channels_count = db.execute(active_channels_count_stmt).scalar()
        
        return {
            "user_id": user.id,
            "telegram_id": user.telegram_id,
            "retention_days": user.retention_days,
            "posts_stats": {
                "total_posts": total_posts,
                "oldest_post_date": to_local_time(oldest_post),
                "newest_post_date": to_local_time(newest_post),
                "channels_count": channels_count,
                "active_channels_count": active_channels_count
            },
            "message": f"Период хранения: {user.retention_days} дней от последнего поста каждого канала"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Ошибка получения настроек: {str(e)}")


@app.put("/users/{user_id}/retention_settings")
async def update_retention_settings(
    user_id: int, 
    settings: RetentionSettingsUpdate,
    db: Session = Depends(get_db)
):
    """
    Обновить период хранения постов для пользователя
    
    Args:
        user_id: ID пользователя
        settings: Новые настройки (retention_days от 1 до 365 дней)
        
    Returns:
        Обновленные настройки и результаты очистки (если запрошена)
    """
    try:
        # Проверяем существование пользователя
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(404, "Пользователь не найден")
        
        old_retention_days = user.retention_days
        
        # Обновляем период хранения
        user.retention_days = settings.retention_days
        db.commit()
        db.refresh(user)
        
        response = {
            "user_id": user.id,
            "telegram_id": user.telegram_id,
            "old_retention_days": old_retention_days,
            "new_retention_days": user.retention_days,
            "updated_at": to_local_time(datetime.now(timezone.utc)),
            "message": f"Период хранения обновлен: {user.retention_days} дней"
        }
        
        # Запускаем немедленную очистку, если запрошено
        if settings.run_cleanup_immediately:
            from cleanup_service import cleanup_service
            
            cleanup_result = await cleanup_service.cleanup_user_posts_immediately(user_id)
            response["cleanup_result"] = cleanup_result
            response["message"] += f" | Очистка выполнена: удалено {cleanup_result.get('posts_deleted', 0)} постов"
        else:
            response["message"] += " | Очистка будет выполнена по расписанию"
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Ошибка обновления настроек: {str(e)}")


@app.post("/cleanup/run")
async def run_cleanup_manually(db: Session = Depends(get_db)):
    """
    Запустить очистку устаревших постов вручную для всех пользователей
    
    Returns:
        Статистика очистки
    """
    try:
        from cleanup_service import cleanup_service
        
        result = await cleanup_service.cleanup_old_posts()
        
        return result
        
    except Exception as e:
        raise HTTPException(500, f"Ошибка запуска очистки: {str(e)}")


# ============================================================================
# Endpoints для управления тегированием
# ============================================================================

@app.get("/users/{user_id}/posts/tagging_stats")
async def get_tagging_stats(user_id: int, db: Session = Depends(get_db)):
    """
    Получить статистику тегирования постов пользователя
    
    Args:
        user_id: ID пользователя
        
    Returns:
        Статистика по статусам тегирования
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(404, "Пользователь не найден")
        
        # Общая статистика
        total_posts = db.query(Post).filter(Post.user_id == user_id).count()
        
        # Статистика по статусам
        stats_by_status = {}
        for status in ["pending", "success", "failed", "retrying", "skipped"]:
            count = db.query(Post).filter(
                Post.user_id == user_id,
                Post.tagging_status == status
            ).count()
            stats_by_status[status] = count
        
        # Посты без статуса (старые, до добавления статуса)
        no_status_count = db.query(Post).filter(
            Post.user_id == user_id,
            Post.tagging_status == None
        ).count()
        stats_by_status["no_status"] = no_status_count
        
        # Посты с тегами
        posts_with_tags = db.query(Post).filter(
            Post.user_id == user_id,
            Post.tags != None
        ).count()
        
        # Посты без тегов но с текстом
        posts_without_tags = db.query(Post).filter(
            Post.user_id == user_id,
            Post.tags == None,
            Post.text != None
        ).count()
        
        # Посты требующие retry (failed или retrying, не превысившие лимит)
        from tagging_service import tagging_service
        posts_need_retry = db.query(Post).filter(
            Post.user_id == user_id,
            Post.tagging_status.in_(["failed", "retrying"]),
            Post.tagging_attempts < tagging_service.max_retry_attempts
        ).count()
        
        return {
            "user_id": user_id,
            "total_posts": total_posts,
            "posts_with_tags": posts_with_tags,
            "posts_without_tags": posts_without_tags,
            "posts_need_retry": posts_need_retry,
            "stats_by_status": stats_by_status,
            "tagging_enabled": tagging_service.enabled,
            "max_retry_attempts": tagging_service.max_retry_attempts
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Ошибка получения статистики тегирования: {str(e)}")


@app.post("/users/{user_id}/posts/retry_tagging")
async def retry_failed_tagging(
    user_id: int,
    background_tasks: BackgroundTasks,
    force: bool = False,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Повторная генерация тегов для постов с ошибками
    
    Args:
        user_id: ID пользователя
        background_tasks: FastAPI BackgroundTasks для async обработки
        force: Принудительный retry даже для постов с превышенным лимитом
        limit: Максимальное количество постов для обработки
        
    Returns:
        Мгновенный ответ о постановке задачи в очередь
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(404, "Пользователь не найден")
        
        from tagging_service import tagging_service
        
        if not tagging_service.enabled:
            raise HTTPException(503, "Тегирование отключено (отсутствует OPENROUTER_API_KEY)")
        
        # Запускаем retry в фоне (неблокирующая операция)
        background_tasks.add_task(
            tagging_service.retry_failed_posts,
            user_id=user_id,
            limit=limit,
            force=force
        )
        
        # Возвращаем мгновенный ответ
        return {
            "user_id": user_id,
            "status": "queued",
            "force_mode": force,
            "requested_limit": limit,
            "message": "Повторная генерация тегов запущена в фоне"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Ошибка retry тегирования: {str(e)}")


@app.post("/posts/{post_id}/regenerate_tags")
async def regenerate_post_tags(
    post_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Перегенерация тегов для конкретного поста
    
    Args:
        post_id: ID поста
        background_tasks: FastAPI BackgroundTasks для async обработки
        
    Returns:
        Мгновенный ответ о постановке задачи в очередь
    """
    try:
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post:
            raise HTTPException(404, "Пост не найден")
        
        from tagging_service import tagging_service
        
        if not tagging_service.enabled:
            raise HTTPException(503, "Тегирование отключено (отсутствует OPENROUTER_API_KEY)")
        
        # Запускаем в фоне (неблокирующая операция)
        background_tasks.add_task(
            tagging_service.update_post_tags,
            post_id,
            None,  # db=None, сервис создаст новую сессию
            True   # force_retry=True
        )
        
        return {
            "post_id": post_id,
            "status": "queued",
            "message": "Перегенерация тегов запущена в фоне"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Ошибка перегенерации тегов: {str(e)}")