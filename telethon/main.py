from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from datetime import datetime, timedelta, timezone
from auth import get_user_client, check_user_auth_status, logout_user, disconnect_all_clients
from database import get_db, SessionLocal
from models import User, Channel, Post, InviteCode, SubscriptionHistory
from sqlalchemy.orm import Session
from sqlalchemy import func, String
from parser_service import ParserService
from pydantic import BaseModel, Field
import asyncio
from telethon.errors import FloodWaitError
import os
import logging
try:
    import zoneinfo
except ImportError:
    from backports import zoneinfo

# Prometheus metrics
from prometheus_client import make_asgi_app

# Logger для main.py
logger = logging.getLogger(__name__)

app = FastAPI()

# Mount Prometheus metrics endpoint
# Best practice from Context7: use make_asgi_app() for async ASGI integration
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# КРИТИЧНО: Глобальный parser_service из главного event loop
# Будет установлен при запуске системы (run_system.py)
global_parser_service = None

# КРИТИЧНО: Ссылка на главный event loop где работают Telethon клиенты
# API работает в отдельном потоке (uvicorn), поэтому нужно отправлять задачи в главный loop
main_event_loop = None

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

# Аутентификация пользователей:
#   - /login INVITE_CODE - QR авторизация через Telegram Mini App (рекомендуется)
#   - /auth - Расширенная авторизация через OAuth веб-форму (auth_web_server.py)
# Auth server запускается автоматически в run_system.py на порту 8001

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
    """
    Парсить каналы конкретного пользователя
    
    КРИТИЧНО (Context7 best practices):
    - API работает в uvicorn потоке (отдельный event loop)
    - Telethon клиенты живут в главном event loop (run_system)
    - Используем asyncio.run_coroutine_threadsafe() для отправки задачи в главный loop
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(404, "Пользователь не найден")
        
        if not user.is_authenticated:
            raise HTTPException(403, "Пользователь не аутентифицирован")
        
        # КРИТИЧНО: Проверяем что главный loop установлен
        if main_event_loop is None or global_parser_service is None:
            raise HTTPException(503, "ParserService не инициализирован")
        
        # КРИТИЧНО: Отправляем задачу в ГЛАВНЫЙ event loop через run_coroutine_threadsafe
        # Это позволяет вызвать async код из uvicorn потока в loop где живут Telethon клиенты
        future = asyncio.run_coroutine_threadsafe(
            global_parser_service.parse_user_channels_by_id(user_id),
            main_event_loop
        )
        
        # Ждем результат (blocking, но это OK для API эндпоинта)
        result = future.result(timeout=300)  # 5 минут timeout
        
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
    """
    Парсить все активные каналы всех аутентифицированных пользователей
    
    КРИТИЧНО: Отправляет задачу в главный event loop через run_coroutine_threadsafe
    """
    try:
        # КРИТИЧНО: Проверяем что главный loop установлен
        if main_event_loop is None or global_parser_service is None:
            raise HTTPException(503, "ParserService не инициализирован")
        
        # КРИТИЧНО: Отправляем задачу в ГЛАВНЫЙ event loop
        future = asyncio.run_coroutine_threadsafe(
            global_parser_service.parse_all_channels(),
            main_event_loop
        )
        
        # Запускаем в фоне, не ждем результата
        # (parse_all_channels может работать долго)
        
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


# ============================================================
# QR Auth Endpoints для Telegram Mini App
# ============================================================

from fastapi.responses import HTMLResponse
from qr_auth_manager import qr_auth_manager


@app.get("/qr-auth", response_class=HTMLResponse)
async def qr_auth_page(session_id: str):
    """
    Mini App страница с QR кодом для авторизации
    
    Args:
        session_id: ID QR сессии
        
    Returns:
        HTML страница с QR кодом и альтернативными способами авторизации
    """
    import qrcode
    import base64
    from io import BytesIO
    
    # Получаем данные сессии из Redis
    session = qr_auth_manager._get_session_from_redis(session_id)
    if not session:
        return HTMLResponse(content="""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Сессия не найдена</title>
            </head>
            <body>
                <h1>❌ Сессия не найдена</h1>
                <p>QR код истек или был удален</p>
            </body>
            </html>
        """)
    
    # Генерируем QR изображение
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(session["deep_link"])
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Конвертируем в base64
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    qr_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    # Возвращаем МИНИМАЛЬНУЮ HTML страницу (упрощено для Desktop Telegram)
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QR Auth</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        body {{
            font-family: -apple-system, system-ui, sans-serif;
            background: var(--tg-theme-bg-color, #fff);
            color: var(--tg-theme-text-color, #000);
            padding: 20px;
            text-align: center;
            margin: 0;
        }}
        .qr {{
            background: #fff;
            padding: 20px;
            border-radius: 12px;
            display: inline-block;
            margin: 20px 0;
        }}
        img {{
            max-width: 250px;
            width: 100%;
        }}
        button {{
            width: 100%;
            max-width: 300px;
            padding: 12px;
            margin: 10px 0;
            border: none;
            border-radius: 8px;
            background: var(--tg-theme-button-color, #0088cc);
            color: var(--tg-theme-button-text-color, #fff);
            font-size: 15px;
            cursor: pointer;
        }}
        button:active {{ opacity: 0.8; }}
        #status {{
            margin: 20px 0;
            padding: 12px;
            border-radius: 8px;
            background: var(--tg-theme-secondary-bg-color, #f0f0f0);
            font-size: 14px;
        }}
        .success {{ background: #4CAF50; color: #fff; }}
        .error {{ background: #f44336; color: #fff; }}
    </style>
</head>
<body>
    <h3>🔐 QR Авторизация</h3>
    <div class="qr">
        <img src="data:image/png;base64,{qr_base64}" alt="QR">
    </div>
    <p style="font-size: 13px; color: var(--tg-theme-hint-color, #999); margin: 10px 0;">
        Отсканируйте QR через:<br>
        Settings → Devices → Link Desktop Device
    </p>
    <button onclick="openLink()">📱 Открыть в Telegram</button>
    <div id="status">⏳ Ожидание...</div>
    
    <script>
        const tg = window.Telegram.WebApp;
        const sessionId = "{session_id}";
        const deepLink = "{session["deep_link"]}";
        const MIN_VERSION = '6.1';
        
        tg.ready();
        tg.expand();
        
        // Логируем информацию о платформе и версии
        console.log('[QR Auth] Platform:', tg.platform);
        console.log('[QR Auth] Version:', tg.version);
        console.log('[QR Auth] ViewportHeight:', tg.viewportHeight);
        
        // Проверка версии Telegram (openTelegramLink доступен с Bot API 6.1+)
        if (!tg.isVersionAtLeast(MIN_VERSION)) {{
            document.getElementById('status').className = 'error';
            document.getElementById('status').textContent = '⚠️ Обновите Telegram для использования QR авторизации';
            console.warn('[QR Auth] Telegram version is too old. Required:', MIN_VERSION, 'Current:', tg.version);
        }}
        
        function openLink() {{
            try {{
                // Показываем состояние загрузки
                document.getElementById('status').textContent = '🔄 Открываем...';
                
                // Используем openTelegramLink для tg:// ссылок (не openLink!)
                if (tg.openTelegramLink) {{
                    tg.openTelegramLink(deepLink);
                    console.log('[QR Auth] Called tg.openTelegramLink');
                    
                    // Обновляем статус после небольшой задержки
                    setTimeout(() => {{
                        document.getElementById('status').textContent = '⏳ Подтвердите в Telegram...';
                    }}, 300);
                }} else {{
                    throw new Error('openTelegramLink not available');
                }}
            }} catch (error) {{
                console.error('[QR Auth] Error:', error);
                console.log('[QR Auth] Fallback to window.location');
                window.location.href = deepLink;
            }}
        }}
        
        async function checkStatus() {{
            try {{
                const r = await fetch('/qr-auth-status?session_id=' + sessionId);
                const d = await r.json();
                
                if (d.status === 'authorized') {{
                    document.getElementById('status').className = 'success';
                    document.getElementById('status').textContent = '✅ Успешно!';
                    setTimeout(() => tg.close(), 2000);
                }} else if (d.status === 'expired') {{
                    document.getElementById('status').className = 'error';
                    document.getElementById('status').textContent = '⏰ Истек';
                }} else {{
                    setTimeout(checkStatus, 2000);
                }}
            }} catch (e) {{
                setTimeout(checkStatus, 2000);
            }}
        }}
        
        checkStatus();
        
        document.addEventListener('visibilitychange', () => {{
            if (!document.hidden) checkStatus();
        }});
    </script>
</body>
</html>"""
    
    return HTMLResponse(content=html_content)


@app.get("/qr-auth-status")
async def qr_auth_status(session_id: str):
    """
    Проверка статуса QR авторизации
    
    Args:
        session_id: ID QR сессии
        
    Returns:
        JSON со статусом авторизации
    """
    status = qr_auth_manager.get_session_status(session_id)
    return status


# ============================================================
# Admin Panel Endpoints для Telegram Mini App
# ============================================================

from admin_panel_manager import admin_panel_manager
from functools import wraps
from typing import List


def require_admin(func):
    """Decorator для проверки admin прав"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Извлекаем admin_id и token из kwargs
        admin_id = kwargs.get('admin_id')
        token = kwargs.get('token')
        
        if not admin_id or not token:
            raise HTTPException(400, "Missing admin_id or token")
        
        # Проверка token в Redis
        if not admin_panel_manager.verify_admin_session(token, admin_id):
            raise HTTPException(403, "Unauthorized: Invalid or expired session")
        
        return await func(*args, **kwargs)
    return wrapper


@app.get("/api/admin/users")
@require_admin
async def get_users_api(
    admin_id: int,
    token: str,
    page: int = 1,
    limit: int = 20,
    search: str = "",
    role: str = "",
    subscription: str = "",
    db: Session = Depends(get_db)
):
    """
    Получить список пользователей (с фильтрами и поиском)
    
    Args:
        admin_id: Telegram ID админа
        token: Session token
        page: Номер страницы
        limit: Элементов на страницу
        search: Поиск по имени/username/telegram_id
        role: Фильтр по роли (admin/user)
        subscription: Фильтр по подписке
    """
    query = db.query(User)
    
    # Поиск
    if search:
        search_filter = (
            User.first_name.ilike(f"%{search}%") |
            User.last_name.ilike(f"%{search}%") |
            User.username.ilike(f"%{search}%") |
            User.telegram_id.cast(String).ilike(f"%{search}%")
        )
        query = query.filter(search_filter)
    
    # Фильтры
    if role:
        query = query.filter(User.role == role)
    if subscription:
        query = query.filter(User.subscription_type == subscription)
    
    # Pagination
    total = query.count()
    offset = (page - 1) * limit
    users = query.order_by(User.created_at.desc()).offset(offset).limit(limit).all()
    
    # Формируем ответ
    return {
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit,
        "users": [
            {
                "id": u.id,
                "telegram_id": u.telegram_id,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "username": u.username,
                "role": u.role,
                "subscription_type": u.subscription_type,
                "max_channels": u.max_channels,
                "is_authenticated": u.is_authenticated,
                "is_blocked": u.is_blocked,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "subscription_started_at": u.subscription_started_at.isoformat() if u.subscription_started_at else None,
                "subscription_expires": u.subscription_expires.isoformat() if u.subscription_expires else None,
                "channels_count": len(u.channels)
            }
            for u in users
        ]
    }


@app.get("/api/admin/user/{user_id}")
@require_admin
async def get_user_detail_api(
    user_id: int,
    admin_id: int,
    token: str,
    db: Session = Depends(get_db)
):
    """Детальная информация о пользователе"""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(404, "Пользователь не найден")
    
    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "username": user.username,
        "role": user.role,
        "subscription_type": user.subscription_type,
        "max_channels": user.max_channels,
        "is_authenticated": user.is_authenticated,
        "is_blocked": user.is_blocked,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "subscription_started_at": user.subscription_started_at.isoformat() if user.subscription_started_at else None,
        "subscription_expires": user.subscription_expires.isoformat() if user.subscription_expires else None,
        "channels": [
            {
                "id": ch.id,
                "channel_username": ch.channel_username,
                "channel_title": ch.channel_title
            }
            for ch in user.channels
        ],
        "channels_count": len(user.channels)
    }


@app.post("/api/admin/user/{user_id}/role")
@require_admin
async def update_user_role_api(
    user_id: int,
    admin_id: int,
    token: str,
    role_data: dict,
    db: Session = Depends(get_db)
):
    """Изменить роль пользователя"""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(404, "Пользователь не найден")
    
    new_role = role_data.get("role")
    if new_role not in ["admin", "user"]:
        raise HTTPException(400, "Неверная роль. Доступны: admin, user")
    
    old_role = user.role
    user.role = new_role
    db.commit()
    
    logger.info(f"👑 Админ {admin_id} изменил роль пользователя {user.telegram_id}: {old_role} → {new_role}")
    
    return {"success": True, "role": new_role}


@app.post("/api/admin/user/{user_id}/subscription")
@require_admin  
async def update_user_subscription_api(
    user_id: int,
    admin_id: int,
    token: str,
    sub_data: dict,
    db: Session = Depends(get_db)
):
    """Изменить подписку пользователя"""
    from subscription_config import get_subscription_info
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(404, "Пользователь не найден")
    
    subscription_type = sub_data.get("type")
    duration_days = sub_data.get("days")
    
    if subscription_type not in ["free", "trial", "basic", "premium", "enterprise"]:
        raise HTTPException(400, "Неверный тип подписки")
    
    # Получаем информацию о tier
    tier_info = get_subscription_info(subscription_type)
    
    old_subscription = user.subscription_type
    user.subscription_type = subscription_type
    user.max_channels = tier_info['max_channels']
    user.subscription_started_at = datetime.now(timezone.utc)
    
    # Устанавливаем expires если указан duration
    if duration_days and duration_days > 0:
        user.subscription_expires = datetime.now(timezone.utc) + timedelta(days=duration_days)
    else:
        user.subscription_expires = None
    
    # Записываем в history
    from models import SubscriptionHistory
    
    # Определяем action
    action = "created"
    if old_subscription and subscription_type != old_subscription:
        if subscription_type in ["premium", "enterprise"] and old_subscription in ["free", "trial", "basic"]:
            action = "upgraded"
        elif subscription_type in ["free", "basic"] and old_subscription in ["premium", "enterprise"]:
            action = "downgraded"
        else:
            action = "renewed"
    
    # Получаем admin user.id из telegram_id
    admin_user = db.query(User).filter(User.telegram_id == admin_id).first()
    admin_user_id = admin_user.id if admin_user else None
    
    history = SubscriptionHistory(
        user_id=user.id,
        action=action,
        old_type=old_subscription,
        new_type=subscription_type,
        changed_by=admin_user_id,  # user.id админа, не telegram_id
        notes=f"Admin panel: manual change by admin telegram_id {admin_id}"
    )
    db.add(history)
    
    db.commit()
    
    logger.info(f"💎 Админ {admin_id} изменил подписку {user.telegram_id}: {old_subscription} → {subscription_type}")
    
    return {
        "success": True,
        "subscription_type": subscription_type,
        "max_channels": user.max_channels,
        "expires": user.subscription_expires.isoformat() if user.subscription_expires else None
    }


@app.post("/api/admin/user/{user_id}/max_channels")
@require_admin
async def update_user_max_channels_api(
    user_id: int,
    admin_id: int,
    token: str,
    data: dict,
    db: Session = Depends(get_db)
):
    """Установить лимит каналов"""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(404, "Пользователь не найден")
    
    max_channels = data.get("max_channels")
    if not isinstance(max_channels, int) or max_channels < 1:
        raise HTTPException(400, "max_channels должен быть числом >= 1")
    
    old_limit = user.max_channels
    user.max_channels = max_channels
    db.commit()
    
    logger.info(f"📊 Админ {admin_id} изменил лимит каналов для {user.telegram_id}: {old_limit} → {max_channels}")
    
    return {"success": True, "max_channels": max_channels}


@app.post("/api/admin/user/{user_id}/block")
@require_admin
async def block_user_api(
    user_id: int,
    admin_id: int,
    token: str,
    data: dict,
    db: Session = Depends(get_db)
):
    """Заблокировать/разблокировать пользователя"""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(404, "Пользователь не найден")
    
    blocked = data.get("blocked", False)
    
    user.is_blocked = blocked
    if blocked:
        user.block_expires = datetime.now(timezone.utc) + timedelta(days=365)  # 1 год
    else:
        user.block_expires = None
    
    db.commit()
    
    action = "заблокировал" if blocked else "разблокировал"
    logger.info(f"🚫 Админ {admin_id} {action} пользователя {user.telegram_id}")
    
    return {"success": True, "is_blocked": blocked}


@app.delete("/api/admin/user/{user_id}/auth")
@require_admin
async def reset_user_auth_api(
    user_id: int,
    admin_id: int,
    token: str,
    db: Session = Depends(get_db)
):
    """Сбросить авторизацию пользователя"""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(404, "Пользователь не найден")
    
    # Очищаем данные авторизации
    user.is_authenticated = False
    user.auth_error = None
    user.last_auth_check = None
    user.phone_number = None
    
    # Удаляем session файл
    from shared_auth_manager import shared_auth_manager
    import os
    
    session_path = shared_auth_manager._get_session_path(user.telegram_id)
    if os.path.exists(session_path):
        try:
            os.remove(session_path)
            logger.info(f"🗑️ Session файл удален для {user.telegram_id}")
        except Exception as e:
            logger.error(f"❌ Ошибка удаления session: {e}")
    
    # Отключаем клиент если активен
    if user.telegram_id in shared_auth_manager.active_clients:
        try:
            await shared_auth_manager.disconnect_client(user.telegram_id)
        except:
            pass
    
    db.commit()
    
    logger.info(f"🔄 Админ {admin_id} сбросил авторизацию пользователя {user.telegram_id}")
    
    return {"success": True}


# ============================================================
# Admin Panel - Invite Codes API
# ============================================================

@app.get("/api/admin/invites")
@require_admin
async def get_invites_api(
    admin_id: int,
    token: str,
    page: int = 1,
    limit: int = 20,
    status: str = "",  # active, used, expired
    db: Session = Depends(get_db)
):
    """Получить список инвайт кодов"""
    query = db.query(InviteCode)
    
    # Фильтр по статусу
    if status == "active":
        query = query.filter(
            InviteCode.uses_count < InviteCode.max_uses,
            InviteCode.expires_at > datetime.now(timezone.utc)
        )
    elif status == "used":
        query = query.filter(InviteCode.uses_count >= InviteCode.max_uses)
    elif status == "expired":
        query = query.filter(InviteCode.expires_at <= datetime.now(timezone.utc))
    
    # Pagination
    total = query.count()
    offset = (page - 1) * limit
    invites = query.order_by(InviteCode.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit,
        "invites": [
            {
                "code": inv.code,
                "default_subscription": inv.default_subscription,
                "max_uses": inv.max_uses,
                "uses_count": inv.uses_count,
                "default_trial_days": inv.default_trial_days,
                "created_at": inv.created_at.isoformat() if inv.created_at else None,
                "expires_at": inv.expires_at.isoformat() if inv.expires_at else None,
                "is_valid": inv.is_valid(),
                "used_by": inv.user.telegram_id if inv.user else None,
                "used_by_name": inv.user.first_name if inv.user else None
            }
            for inv in invites
        ]
    }


@app.post("/api/admin/invite/create")
@require_admin
async def create_invite_api(
    admin_id: int,
    token: str,
    invite_data: dict,
    db: Session = Depends(get_db)
):
    """Создать новый инвайт код"""
    subscription = invite_data.get("subscription", "free")
    max_uses = invite_data.get("max_uses", 1)
    expires_days = invite_data.get("expires_days", 30)
    trial_days = invite_data.get("trial_days", 0)
    
    # Валидация
    if subscription not in ["free", "trial", "basic", "premium", "enterprise"]:
        raise HTTPException(400, "Неверный тип подписки")
    
    if max_uses < 1:
        raise HTTPException(400, "max_uses должен быть >= 1")
    
    # ВАЖНО: Получаем реальный user.id из БД по telegram_id
    # admin_id здесь - это telegram_id, а created_by должен быть users.id
    admin_user = db.query(User).filter(User.telegram_id == admin_id).first()
    if not admin_user:
        raise HTTPException(404, "Админ пользователь не найден")
    
    # Создаем код
    new_code = InviteCode.generate_code()
    
    invite = InviteCode(
        code=new_code,
        created_by=admin_user.id,  # Используем user.id, а не telegram_id!
        default_subscription=subscription,
        max_uses=max_uses,
        default_trial_days=trial_days,
        expires_at=datetime.now(timezone.utc) + timedelta(days=expires_days)
    )
    
    db.add(invite)
    db.commit()
    db.refresh(invite)
    
    logger.info(f"🎫 Админ {admin_id} создал инвайт код {new_code} ({subscription}, {max_uses} uses, {expires_days} days)")
    
    return {
        "success": True,
        "code": new_code,
        "subscription": subscription,
        "max_uses": max_uses,
        "expires_at": invite.expires_at.isoformat()
    }


@app.post("/api/admin/invite/{code}/deactivate")
@require_admin
async def deactivate_invite_api(
    code: str,
    admin_id: int,
    token: str,
    db: Session = Depends(get_db)
):
    """Деактивировать инвайт код"""
    invite = db.query(InviteCode).filter(InviteCode.code == code).first()
    
    if not invite:
        raise HTTPException(404, "Инвайт код не найден")
    
    # Устанавливаем expires в прошлое
    invite.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    db.commit()
    
    logger.info(f"🚫 Админ {admin_id} деактивировал инвайт код {code}")
    
    return {"success": True}


@app.get("/api/admin/invite/{code}/usage")
@require_admin
async def get_invite_usage_api(
    code: str,
    admin_id: int,
    token: str,
    db: Session = Depends(get_db)
):
    """Посмотреть кто использовал инвайт код"""
    invite = db.query(InviteCode).filter(InviteCode.code == code).first()
    
    if not invite:
        raise HTTPException(404, "Инвайт код не найден")
    
    # Получаем всех пользователей приглашенных этим кодом
    users = db.query(User).filter(User.invited_by == invite.created_by).all()
    
    return {
        "code": code,
        "uses_count": invite.uses_count,
        "max_uses": invite.max_uses,
        "users": [
            {
                "telegram_id": u.telegram_id,
                "first_name": u.first_name,
                "username": u.username,
                "created_at": u.created_at.isoformat() if u.created_at else None
            }
            for u in users
        ]
    }


# ============================================================
# Admin Panel - Statistics API
# ============================================================

@app.get("/api/admin/stats/summary")
@require_admin
async def get_stats_summary_api(
    admin_id: int,
    token: str,
    db: Session = Depends(get_db)
):
    """Общая статистика"""
    total_users = db.query(User).count()
    authenticated_users = db.query(User).filter(User.is_authenticated == True).count()
    
    # По подпискам
    subscription_counts = {}
    for sub_type in ["free", "trial", "basic", "premium", "enterprise"]:
        count = db.query(User).filter(User.subscription_type == sub_type).count()
        subscription_counts[sub_type] = count
    
    # По ролям
    admins_count = db.query(User).filter(User.role == "admin").count()
    
    # Инвайт коды
    total_invites = db.query(InviteCode).count()
    active_invites = db.query(InviteCode).filter(
        InviteCode.uses_count < InviteCode.max_uses,
        InviteCode.expires_at > datetime.now(timezone.utc)
    ).count()
    
    # Группы (новое)
    from models import Group, GroupMention
    total_groups = db.query(Group).count()
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    mentions_today = db.query(GroupMention).filter(
        GroupMention.mentioned_at >= today
    ).count()
    
    return {
        "users": {
            "total": total_users,
            "authenticated": authenticated_users,
            "admins": admins_count
        },
        "subscriptions": subscription_counts,
        "invites": {
            "total": total_invites,
            "active": active_invites
        },
        "groups": {
            "total": total_groups,
            "mentions_today": mentions_today
        }
    }


@app.get("/api/admin/stats/registrations")
@require_admin
async def get_registrations_stats_api(
    admin_id: int,
    token: str,
    days: int = 7,
    db: Session = Depends(get_db)
):
    """Статистика регистраций по дням"""
    from sqlalchemy import func, Date, cast
    
    # Получаем регистрации за последние N дней
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Группируем по дням
    registrations = db.query(
        func.date(User.created_at).label('date'),
        func.count(User.id).label('count')
    ).filter(
        User.created_at >= start_date
    ).group_by(
        func.date(User.created_at)
    ).order_by(
        func.date(User.created_at)
    ).all()
    
    # Формируем массив для Chart.js
    labels = []
    data = []
    
    for reg in registrations:
        labels.append(reg.date.strftime('%d.%m'))
        data.append(reg.count)
    
    return {
        "labels": labels,
        "data": data,
        "days": days
    }


@app.get("/api/admin/stats/subscriptions")
@require_admin
async def get_subscriptions_stats_api(
    admin_id: int,
    token: str,
    db: Session = Depends(get_db)
):
    """Breakdown подписок для Pie chart"""
    subscriptions = {}
    
    for sub_type in ["free", "trial", "basic", "premium", "enterprise"]:
        count = db.query(User).filter(User.subscription_type == sub_type).count()
        subscriptions[sub_type] = count
    
    return subscriptions


# ============================================================
# Admin API - Groups Management
# ============================================================

@app.get("/api/admin/groups")
@require_admin
async def get_all_groups_api(
    admin_id: int,
    token: str,
    db: Session = Depends(get_db)
):
    """Получить список всех групп в системе"""
    from models import Group
    
    groups = db.query(Group).all()
    
    return {
        "total": len(groups),
        "groups": [
            {
                "id": g.id,
                "group_id": g.group_id,
                "group_title": g.group_title,
                "group_username": g.group_username,
                "created_at": g.created_at.isoformat() if g.created_at else None,
                "users_count": len(g.users)
            }
            for g in groups
        ]
    }


@app.get("/api/admin/user/{user_id}/groups")
@require_admin
async def get_user_groups_api(
    user_id: int,
    admin_id: int,
    token: str,
    db: Session = Depends(get_db)
):
    """Получить группы конкретного пользователя"""
    from models import Group, user_group
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Получаем группы с настройками
    groups = db.query(Group).join(
        user_group,
        Group.id == user_group.c.group_id
    ).filter(
        user_group.c.user_id == user.id
    ).all()
    
    result = []
    for group in groups:
        subscription = db.execute(
            user_group.select().where(
                (user_group.c.user_id == user.id) &
                (user_group.c.group_id == group.id)
            )
        ).fetchone()
        
        result.append({
            "id": group.id,
            "group_id": group.group_id,
            "group_title": group.group_title,
            "group_username": group.group_username,
            "is_active": subscription.is_active if subscription else False,
            "mentions_enabled": subscription.mentions_enabled if subscription else False,
            "created_at": subscription.created_at.isoformat() if subscription and subscription.created_at else None
        })
    
    return {
        "user_id": user_id,
        "telegram_id": user.telegram_id,
        "total_groups": len(result),
        "groups": result
    }


@app.post("/api/admin/user/{user_id}/group/{group_id}/mentions")
@require_admin
async def toggle_group_mentions_api(
    user_id: int,
    group_id: int,
    admin_id: int,
    token: str,
    enabled: bool,
    db: Session = Depends(get_db)
):
    """Включить/выключить уведомления об упоминаниях для группы"""
    from models import user_group
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Обновляем настройку
    db.execute(
        user_group.update().where(
            (user_group.c.user_id == user_id) &
            (user_group.c.group_id == group_id)
        ).values(mentions_enabled=enabled)
    )
    db.commit()
    
    return {
        "success": True,
        "user_id": user_id,
        "group_id": group_id,
        "mentions_enabled": enabled
    }


@app.get("/api/admin/stats/groups")
@require_admin
async def get_groups_stats_api(
    admin_id: int,
    token: str,
    db: Session = Depends(get_db)
):
    """Статистика по группам"""
    from models import Group, GroupMention
    from datetime import timedelta
    
    total_groups = db.query(Group).count()
    
    # Упоминания за сегодня
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    mentions_today = db.query(GroupMention).filter(
        GroupMention.mentioned_at >= today
    ).count()
    
    # Упоминания за неделю
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    mentions_week = db.query(GroupMention).filter(
        GroupMention.mentioned_at >= week_ago
    ).count()
    
    # Статус мониторинга
    from group_monitor_service import group_monitor_service
    monitor_status = group_monitor_service.get_status()
    
    return {
        "total_groups": total_groups,
        "mentions_today": mentions_today,
        "mentions_week": mentions_week,
        "active_monitors": monitor_status["active_monitors"],
        "monitored_groups_total": monitor_status["monitored_groups_total"]
    }


# ============================================================
# Admin Panel - Optimized Multi-Page UI (Lightweight)
# ============================================================

@app.get("/admin-panel", response_class=HTMLResponse)
async def admin_panel_menu(admin_id: int, token: str):
    """
    Admin Panel - Главное меню (оптимизированная версия)
    
    Args:
        admin_id: Telegram ID админа
        token: Session token из Redis
    """
    # Проверяем права
    if not admin_panel_manager.verify_admin_session(token, admin_id):
        return HTMLResponse(content="""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Unauthorized</title>
                <script src="https://telegram.org/js/telegram-web-app.js"></script>
            </head>
            <body style="font-family: -apple-system, sans-serif; padding: 20px; text-align: center;">
                <h1>❌ Unauthorized</h1>
                <p>Session истекла или вы не являетесь администратором</p>
                <p>Закройте это окно и отправьте /admin снова</p>
                <script>
                    window.Telegram.WebApp.ready();
                    window.Telegram.WebApp.expand();
                </script>
            </body>
            </html>
        """)
    
    # Получаем данные admin session для отображения имени
    session_data = admin_panel_manager.get_session_data(token)
    admin_name = session_data.get("admin_name", "Admin") if session_data else "Admin"
    
    # Получаем базовую статистику для меню
    db = SessionLocal()
    try:
        total_users = db.query(User).count()
        total_invites = db.query(InviteCode).count()
    finally:
        db.close()
    
    # Упрощенное меню Admin Panel (по аналогии с QR Auth)
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Panel</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        body {{
            font-family: -apple-system, system-ui, sans-serif;
            background: var(--tg-theme-bg-color, #fff);
            color: var(--tg-theme-text-color, #000);
            padding: 20px;
            text-align: center;
            margin: 0;
        }}
        h2 {{
            margin-bottom: 10px;
        }}
        .subtitle {{
            color: var(--tg-theme-hint-color, #999);
            font-size: 14px;
            margin-bottom: 30px;
        }}
        .menu {{
            max-width: 400px;
            margin: 0 auto;
        }}
        .menu-item {{
            background: var(--tg-theme-secondary-bg-color, #f0f0f0);
            padding: 16px;
            margin: 12px 0;
            border-radius: 12px;
            cursor: pointer;
            transition: opacity 0.2s;
        }}
        .menu-item:active {{
            opacity: 0.7;
        }}
        .menu-item-title {{
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 4px;
        }}
        .menu-item-desc {{
            font-size: 13px;
            color: var(--tg-theme-hint-color, #999);
        }}
        .stats {{
            display: flex;
            justify-content: space-around;
            margin: 20px 0 30px 0;
        }}
        .stat {{
            text-align: center;
        }}
        .stat-value {{
            font-size: 24px;
            font-weight: 700;
            color: var(--tg-theme-button-color, #0088cc);
        }}
        .stat-label {{
            font-size: 12px;
            color: var(--tg-theme-hint-color, #999);
            margin-top: 4px;
        }}
    </style>
</head>
<body>
    <h2>👑 Admin Panel</h2>
    <div class="subtitle">Привет, {admin_name}!</div>
    
    <div class="stats">
        <div class="stat">
            <div class="stat-value">{total_users}</div>
            <div class="stat-label">Пользователей</div>
        </div>
        <div class="stat">
            <div class="stat-value">{total_invites}</div>
            <div class="stat-label">Инвайт кодов</div>
        </div>
    </div>
    
    <div class="menu">
        <div class="menu-item" onclick="openPage('users')">
            <div class="menu-item-title">👥 Пользователи</div>
            <div class="menu-item-desc">Управление пользователями и подписками</div>
        </div>
        
        <div class="menu-item" onclick="openPage('invites')">
            <div class="menu-item-title">🎫 Инвайт коды</div>
            <div class="menu-item-desc">Создание и управление кодами</div>
        </div>
    </div>
    
    <script>
        const tg = window.Telegram.WebApp;
        const adminId = {admin_id};
        const token = "{token}";
        
        tg.ready();
        tg.expand();
        
        function openPage(page) {{
            const baseUrl = window.location.origin + window.location.pathname;
            const url = baseUrl + '/' + page + '?admin_id=' + adminId + '&token=' + token;
            
            if (tg.openLink) {{
                tg.openLink(url);
            }} else {{
                window.location.href = url;
            }}
        }}
    </script>
</body>
</html>"""
    
    return HTMLResponse(content=html_content)


@app.get("/admin-panel/users", response_class=HTMLResponse)
async def admin_panel_users(admin_id: int, token: str):
    """Admin Panel - Управление пользователями"""
    # Проверяем права
    if not admin_panel_manager.verify_admin_session(token, admin_id):
        return HTMLResponse(content="""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <script src="https://telegram.org/js/telegram-web-app.js"></script>
            </head>
            <body style="font-family: -apple-system, sans-serif; padding: 20px; text-align: center;">
                <h1>❌ Unauthorized</h1>
                <p>Session истекла</p>
                <script>window.Telegram.WebApp.ready(); window.Telegram.WebApp.expand();</script>
            </body>
            </html>
        """)
    
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Users</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        body {{
            font-family: -apple-system, system-ui, sans-serif;
            background: var(--tg-theme-bg-color, #fff);
            color: var(--tg-theme-text-color, #000);
            padding: 16px;
            margin: 0;
        }}
        h3 {{
            margin-bottom: 16px;
        }}
        input {{
            width: 100%;
            padding: 12px;
            border: 1px solid var(--tg-theme-hint-color, #ccc);
            border-radius: 8px;
            background: var(--tg-theme-secondary-bg-color, #f0f0f0);
            color: var(--tg-theme-text-color, #000);
            font-size: 14px;
            margin-bottom: 16px;
        }}
        .user-card {{
            background: var(--tg-theme-secondary-bg-color, #f0f0f0);
            padding: 12px;
            margin-bottom: 10px;
            border-radius: 10px;
        }}
        .user-name {{
            font-weight: 600;
            font-size: 15px;
            margin-bottom: 6px;
        }}
        .user-info {{
            font-size: 12px;
            color: var(--tg-theme-hint-color, #999);
            margin-bottom: 8px;
        }}
        .badges {{
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
        }}
        .badge {{
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 500;
        }}
        .badge-admin {{ background: #ff9800; color: #fff; }}
        .badge-premium {{ background: #4caf50; color: #fff; }}
        .badge-basic {{ background: #2196f3; color: #fff; }}
        .badge-free {{ background: #9e9e9e; color: #fff; }}
        button {{
            width: 100%;
            padding: 12px;
            margin: 10px 0;
            border: none;
            border-radius: 8px;
            background: var(--tg-theme-button-color, #0088cc);
            color: var(--tg-theme-button-text-color, #fff);
            font-size: 15px;
            cursor: pointer;
        }}
        button:active {{ opacity: 0.8; }}
        .loading {{
            text-align: center;
            padding: 20px;
            color: var(--tg-theme-hint-color, #999);
        }}
        .modal {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            z-index: 1000;
        }}
        .modal.active {{ display: flex; align-items: center; justify-content: center; }}
        .modal-content {{
            background: var(--tg-theme-bg-color, #fff);
            padding: 20px;
            border-radius: 16px;
            max-width: 90%;
            width: 400px;
        }}
        .form-group {{
            margin-bottom: 12px;
            text-align: left;
        }}
        .form-group label {{
            display: block;
            margin-bottom: 6px;
            font-size: 13px;
            font-weight: 500;
        }}
        .form-group select {{
            width: 100%;
            padding: 10px;
            border: 1px solid var(--tg-theme-hint-color, #ccc);
            border-radius: 8px;
            background: var(--tg-theme-secondary-bg-color, #f0f0f0);
            color: var(--tg-theme-text-color, #000);
        }}
        .btn-secondary {{
            background: var(--tg-theme-secondary-bg-color, #f0f0f0);
            color: var(--tg-theme-text-color, #000);
        }}
    </style>
</head>
<body>
    <h3>👥 Пользователи</h3>
    <input type="text" id="search" placeholder="🔍 Поиск по имени..." oninput="searchUsers()">
    
    <div id="usersList" class="loading">Загрузка...</div>
    
    <button onclick="goBack()">← Назад в меню</button>
    
    <!-- Edit User Modal -->
    <div id="editModal" class="modal">
        <div class="modal-content">
            <h4 style="margin-bottom: 16px;">Редактировать пользователя</h4>
            <div id="editForm"></div>
        </div>
    </div>
    
    <script>
        const tg = window.Telegram.WebApp;
        const adminId = {admin_id};
        const token = "{token}";
        let allUsers = [];
        
        tg.ready();
        tg.expand();
        
        async function loadUsers() {{
            try {{
                const r = await fetch(`/api/admin/users?admin_id=${{adminId}}&token=${{token}}&limit=100`);
                const data = await r.json();
                allUsers = data.users || [];
                renderUsers(allUsers);
            }} catch (e) {{
                document.getElementById('usersList').innerHTML = '❌ Ошибка загрузки';
            }}
        }}
        
        function renderUsers(users) {{
            const html = users.map(u => `
                <div class="user-card" onclick="editUser(${{u.id}})">
                    <div class="user-name">${{u.first_name || 'Пользователь'}} ${{u.last_name || ''}}</div>
                    <div class="user-info">ID: ${{u.telegram_id}}</div>
                    <div class="badges">
                        ${{u.role === 'admin' ? '<span class="badge badge-admin">👑 Admin</span>' : ''}}
                        <span class="badge badge-${{u.subscription_type}}">${{u.subscription_type}}</span>
                        ${{u.is_authenticated ? '<span class="badge" style="background: #4caf50; color: #fff;">✅ Auth</span>' : ''}}
                    </div>
                </div>
            `).join('');
            
            document.getElementById('usersList').innerHTML = html || '<div class="loading">Нет пользователей</div>';
        }}
        
        function searchUsers() {{
            const query = document.getElementById('search').value.toLowerCase();
            const filtered = allUsers.filter(u => 
                (u.first_name || '').toLowerCase().includes(query) ||
                (u.last_name || '').toLowerCase().includes(query) ||
                String(u.telegram_id).includes(query)
            );
            renderUsers(filtered);
        }}
        
        function editUser(userId) {{
            const user = allUsers.find(u => u.id === userId);
            if (!user) return;
            
            document.getElementById('editForm').innerHTML = `
                <div class="form-group">
                    <label>Роль:</label>
                    <select id="editRole">
                        <option value="user" ${{user.role === 'user' ? 'selected' : ''}}>User</option>
                        <option value="admin" ${{user.role === 'admin' ? 'selected' : ''}}>Admin</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Подписка:</label>
                    <select id="editSub">
                        <option value="free" ${{user.subscription_type === 'free' ? 'selected' : ''}}>Free</option>
                        <option value="trial" ${{user.subscription_type === 'trial' ? 'selected' : ''}}>Trial</option>
                        <option value="basic" ${{user.subscription_type === 'basic' ? 'selected' : ''}}>Basic</option>
                        <option value="premium" ${{user.subscription_type === 'premium' ? 'selected' : ''}}>Premium</option>
                        <option value="enterprise" ${{user.subscription_type === 'enterprise' ? 'selected' : ''}}>Enterprise</option>
                    </select>
                </div>
                <button onclick="saveChanges(${{userId}})">Сохранить</button>
                <button class="btn-secondary" onclick="closeModal()">Отмена</button>
            `;
            
            document.getElementById('editModal').classList.add('active');
        }}
        
        async function saveChanges(userId) {{
            const role = document.getElementById('editRole').value;
            const sub = document.getElementById('editSub').value;
            
            try {{
                await fetch(`/api/admin/user/${{userId}}/role?admin_id=${{adminId}}&token=${{token}}`, {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{role}})
                }});
                
                await fetch(`/api/admin/user/${{userId}}/subscription?admin_id=${{adminId}}&token=${{token}}`, {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{type: sub, days: 0}})
                }});
                
                closeModal();
                loadUsers();
                tg.showAlert('✅ Сохранено!');
            }} catch (e) {{
                tg.showAlert('❌ Ошибка: ' + e.message);
            }}
        }}
        
        function closeModal() {{
            document.getElementById('editModal').classList.remove('active');
        }}
        
        function goBack() {{
            const url = window.location.origin + '/admin-panel?admin_id=' + adminId + '&token=' + token;
            if (tg.openLink) {{
                tg.openLink(url);
            }} else {{
                window.location.href = url;
            }}
        }}
        
        loadUsers();
    </script>
</body>
</html>"""
    
    return HTMLResponse(content=html_content)


@app.get("/admin-panel/invites", response_class=HTMLResponse)
async def admin_panel_invites(admin_id: int, token: str):
    """Admin Panel - Управление инвайт кодами"""
    # Проверяем права
    if not admin_panel_manager.verify_admin_session(token, admin_id):
        return HTMLResponse(content="""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <script src="https://telegram.org/js/telegram-web-app.js"></script>
            </head>
            <body style="font-family: -apple-system, sans-serif; padding: 20px; text-align: center;">
                <h1>❌ Unauthorized</h1>
                <p>Session истекла</p>
                <script>window.Telegram.WebApp.ready(); window.Telegram.WebApp.expand();</script>
            </body>
            </html>
        """)
    
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Invite Codes</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        body {{
            font-family: -apple-system, system-ui, sans-serif;
            background: var(--tg-theme-bg-color, #fff);
            color: var(--tg-theme-text-color, #000);
            padding: 16px;
            margin: 0;
        }}
        h3 {{
            margin-bottom: 16px;
        }}
        .invite-card {{
            background: var(--tg-theme-secondary-bg-color, #f0f0f0);
            padding: 12px;
            margin-bottom: 10px;
            border-radius: 10px;
        }}
        .invite-code {{
            font-family: monospace;
            font-size: 18px;
            font-weight: 700;
            margin-bottom: 8px;
            color: var(--tg-theme-button-color, #0088cc);
        }}
        .invite-info {{
            font-size: 12px;
            color: var(--tg-theme-hint-color, #999);
            margin-bottom: 4px;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 500;
            margin-right: 6px;
        }}
        .badge-active {{ background: #4caf50; color: #fff; }}
        .badge-expired {{ background: #f44336; color: #fff; }}
        .badge-used {{ background: #9e9e9e; color: #fff; }}
        button {{
            width: 100%;
            padding: 12px;
            margin: 10px 0;
            border: none;
            border-radius: 8px;
            background: var(--tg-theme-button-color, #0088cc);
            color: var(--tg-theme-button-text-color, #fff);
            font-size: 15px;
            cursor: pointer;
        }}
        button:active {{ opacity: 0.8; }}
        .btn-secondary {{
            background: var(--tg-theme-secondary-bg-color, #f0f0f0);
            color: var(--tg-theme-text-color, #000);
        }}
        .loading {{
            text-align: center;
            padding: 20px;
            color: var(--tg-theme-hint-color, #999);
        }}
        .modal {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            z-index: 1000;
        }}
        .modal.active {{ display: flex; align-items: center; justify-content: center; }}
        .modal-content {{
            background: var(--tg-theme-bg-color, #fff);
            padding: 20px;
            border-radius: 16px;
            max-width: 90%;
            width: 400px;
        }}
        .form-group {{
            margin-bottom: 12px;
            text-align: left;
        }}
        .form-group label {{
            display: block;
            margin-bottom: 6px;
            font-size: 13px;
            font-weight: 500;
        }}
        .form-group select,
        .form-group input {{
            width: 100%;
            padding: 10px;
            border: 1px solid var(--tg-theme-hint-color, #ccc);
            border-radius: 8px;
            background: var(--tg-theme-secondary-bg-color, #f0f0f0);
            color: var(--tg-theme-text-color, #000);
        }}
    </style>
</head>
<body>
    <h3>🎫 Инвайт коды</h3>
    
    <button onclick="showCreateModal()">+ Создать код</button>
    
    <div id="invitesList" class="loading">Загрузка...</div>
    
    <button class="btn-secondary" onclick="goBack()">← Назад в меню</button>
    
    <!-- Create Invite Modal -->
    <div id="createModal" class="modal">
        <div class="modal-content">
            <h4 style="margin-bottom: 16px;">Создать инвайт код</h4>
            <div class="form-group">
                <label>Подписка:</label>
                <select id="inviteSub">
                    <option value="free">Free (3 канала)</option>
                    <option value="trial">Trial (10 каналов, 7 дней)</option>
                    <option value="basic">Basic (10 каналов)</option>
                    <option value="premium" selected>Premium (50 каналов)</option>
                    <option value="enterprise">Enterprise (999 каналов)</option>
                </select>
            </div>
            <div class="form-group">
                <label>Макс. использований:</label>
                <input type="number" id="inviteMaxUses" value="1" min="1">
            </div>
            <div class="form-group">
                <label>Trial период (дней):</label>
                <input type="number" id="inviteTrialDays" value="0" min="0">
            </div>
            <div class="form-group">
                <label>Срок действия (дней):</label>
                <input type="number" id="inviteExpires" value="30" min="1">
            </div>
            <button onclick="createInvite()">Создать</button>
            <button class="btn-secondary" onclick="closeModal()">Отмена</button>
        </div>
    </div>
    
    <script>
        const tg = window.Telegram.WebApp;
        const adminId = {admin_id};
        const token = "{token}";
        
        tg.ready();
        tg.expand();
        
        async function loadInvites() {{
            try {{
                const r = await fetch(`/api/admin/invites?admin_id=${{adminId}}&token=${{token}}&limit=100`);
                const data = await r.json();
                renderInvites(data.invites || []);
            }} catch (e) {{
                document.getElementById('invitesList').innerHTML = '❌ Ошибка загрузки';
            }}
        }}
        
        function renderInvites(invites) {{
            const html = invites.map(inv => {{
                const now = new Date();
                const expires = new Date(inv.expires_at);
                const isExpired = expires < now;
                const isUsed = inv.uses_count >= inv.max_uses;
                
                let status = '';
                if (isUsed) status = '<span class="badge badge-used">Использован</span>';
                else if (isExpired) status = '<span class="badge badge-expired">Истек</span>';
                else status = '<span class="badge badge-active">Активен</span>';
                
                return `
                    <div class="invite-card">
                        <div class="invite-code">${{inv.code}}</div>
                        <div class="invite-info">Подписка: ${{inv.default_subscription}}</div>
                        <div class="invite-info">Использовано: ${{inv.uses_count}}/${{inv.max_uses}}</div>
                        <div class="invite-info">Истекает: ${{expires.toLocaleDateString('ru-RU')}}</div>
                        <div>${{status}}</div>
                    </div>
                `;
            }}).join('');
            
            document.getElementById('invitesList').innerHTML = html || '<div class="loading">Нет кодов</div>';
        }}
        
        function showCreateModal() {{
            document.getElementById('createModal').classList.add('active');
        }}
        
        async function createInvite() {{
            const sub = document.getElementById('inviteSub').value;
            const maxUses = parseInt(document.getElementById('inviteMaxUses').value);
            const trialDays = parseInt(document.getElementById('inviteTrialDays').value);
            const expiresDays = parseInt(document.getElementById('inviteExpires').value);
            
            try {{
                const r = await fetch(`/api/admin/invite/create?admin_id=${{adminId}}&token=${{token}}`, {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        subscription: sub,
                        max_uses: maxUses,
                        trial_days: trialDays,
                        expires_days: expiresDays
                    }})
                }});
                
                if (!r.ok) {{
                    const err = await r.json();
                    throw new Error(err.detail || 'Ошибка создания');
                }}
                
                const data = await r.json();
                closeModal();
                loadInvites();
                tg.showAlert('✅ Код создан: ' + data.code);
            }} catch (e) {{
                tg.showAlert('❌ Ошибка: ' + e.message);
            }}
        }}
        
        function closeModal() {{
            document.getElementById('createModal').classList.remove('active');
        }}
        
        function goBack() {{
            const url = window.location.origin + '/admin-panel?admin_id=' + adminId + '&token=' + token;
            if (tg.openLink) {{
                tg.openLink(url);
            }} else {{
                window.location.href = url;
            }}
        }}
        
        loadInvites();
        
        // Close modal on click outside
        document.getElementById('createModal').addEventListener('click', (e) => {{
            if (e.target.id === 'createModal') closeModal();
        }});
    </script>
</body>
</html>"""
    
    return HTMLResponse(content=html_content)


# ============================================================
# End of Admin Panel endpoints
# ============================================================

# ============================================================================
# Neo4j Knowledge Graph API Endpoints
# ============================================================================

# Neo4j client
try:
    from graph.neo4j_client import neo4j_client
except ImportError:
    neo4j_client = None
    logger.warning("⚠️ Neo4j graph module not available")


@app.get("/graph/post/{post_id}/related")
async def get_related_posts_endpoint(post_id: int, limit: int = 10):
    """
    Получить посты связанные через общие теги
    
    Args:
        post_id: ID поста из PostgreSQL
        limit: Количество результатов (default: 10)
        
    Returns:
        {
            "post_id": 123,
            "related_posts": [
                {
                    "post_id": 456,
                    "title": "Related Post",
                    "common_tags": 3,
                    "channel_id": "@channel"
                }
            ]
        }
    """
    if not neo4j_client or not neo4j_client.enabled:
        raise HTTPException(
            503,
            "Neo4j Knowledge Graph disabled. Set NEO4J_ENABLED=true in .env"
        )
    
    try:
        related = await neo4j_client.get_related_posts(post_id, limit)
        return {
            "post_id": post_id,
            "related_posts": related,
            "count": len(related)
        }
    except Exception as e:
        logger.error(f"❌ Graph query error: {e}")
        raise HTTPException(500, f"Graph query failed: {str(e)}")


@app.get("/graph/tag/{tag_name}/relationships")
async def get_tag_relationships_endpoint(tag_name: str, limit: int = 20):
    """
    Получить связи тега с другими тегами (co-occurrence)
    
    Args:
        tag_name: Имя тега
        limit: Количество результатов (default: 20)
        
    Returns:
        {
            "tag": "AI",
            "related_tags": [
                {
                    "tag": "Python",
                    "weight": 15,
                    "posts_count": 42
                }
            ]
        }
    """
    if not neo4j_client or not neo4j_client.enabled:
        raise HTTPException(
            503,
            "Neo4j Knowledge Graph disabled. Set NEO4J_ENABLED=true in .env"
        )
    
    try:
        relationships = await neo4j_client.get_tag_relationships(tag_name, limit)
        return {
            "tag": tag_name,
            "related_tags": relationships,
            "count": len(relationships)
        }
    except Exception as e:
        logger.error(f"❌ Graph query error: {e}")
        raise HTTPException(500, f"Graph query failed: {str(e)}")


@app.get("/graph/user/{user_id}/interests")
async def get_user_interests_endpoint(user_id: int, limit: int = 20, db: Session = Depends(get_db)):
    """
    Анализ интересов пользователя через граф
    
    Args:
        user_id: ID пользователя из PostgreSQL
        limit: Количество топ тегов (default: 20)
        
    Returns:
        {
            "user_id": 123,
            "telegram_id": 456789,
            "interests": [
                {
                    "tag": "AI",
                    "posts_count": 42,
                    "usage_percent": 15.5
                }
            ]
        }
    """
    if not neo4j_client or not neo4j_client.enabled:
        raise HTTPException(
            503,
            "Neo4j Knowledge Graph disabled. Set NEO4J_ENABLED=true in .env"
        )
    
    # Получить telegram_id пользователя
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    
    try:
        interests = await neo4j_client.get_user_interests(user.telegram_id, limit)
        return {
            "user_id": user_id,
            "telegram_id": user.telegram_id,
            "interests": interests,
            "count": len(interests)
        }
    except Exception as e:
        logger.error(f"❌ Graph query error: {e}")
        raise HTTPException(500, f"Graph query failed: {str(e)}")


@app.get("/graph/health")
async def graph_health_check():
    """
    Проверить подключение к Neo4j
    
    Returns:
        {
            "neo4j_enabled": true,
            "neo4j_connected": true
        }
    """
    if not neo4j_client:
        return {"neo4j_enabled": False, "neo4j_connected": False}
    
    is_healthy = await neo4j_client.health_check() if neo4j_client.enabled else False
    
    return {
        "neo4j_enabled": neo4j_client.enabled,
        "neo4j_connected": is_healthy
    }
