"""
RAG Service FastAPI Application
"""
import logging
import sys
import os

# ВАЖНО: Добавляем родительскую директорию в path ДО импортов
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Optional
from pydantic import BaseModel
from datetime import datetime, timezone

# Prometheus metrics
from prometheus_client import make_asgi_app

from database import SessionLocal
from models import User, Post, IndexingStatus, DigestSettings
import config
from schemas import (
    IndexPostRequest,
    IndexBatchRequest,
    IndexingStatusResponse,
    CollectionStatsResponse,
    HealthResponse
)
from indexer import indexer_service
from vector_db import qdrant_client
from embeddings import embeddings_service
from scheduler import digest_scheduler


# Database dependency
def get_db():
    """FastAPI dependency для получения database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI приложение
app = FastAPI(
    title="RAG Service API",
    description="Сервис векторного поиска и генерации ответов для Telegram Channel Parser",
    version="0.1.0"
)

# Mount Prometheus metrics endpoint
# Best practice from Context7: use make_asgi_app() for async ASGI integration
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    logger.info("🚀 RAG Service запускается...")
    logger.info(f"   Qdrant URL: {config.QDRANT_URL}")
    logger.info(f"   GigaChat embeddings: {config.GIGACHAT_ENABLED}")
    logger.info(f"   Database: {config.DATABASE_URL}")
    
    # Запуск планировщика дайджестов
    try:
        digest_scheduler.start()
        
        # Загрузка расписаний для всех пользователей с enabled=true
        db = SessionLocal()
        try:
            active_settings = db.query(DigestSettings).filter(
                DigestSettings.enabled == True
            ).all()
            
            logger.info(f"📅 Найдено {len(active_settings)} активных расписаний дайджестов")
            
            for idx, settings in enumerate(active_settings):
                try:
                    # Конвертируем frequency в days_of_week
                    if settings.frequency == "daily":
                        days_of_week = "mon-sun"
                    elif settings.frequency == "weekly":
                        # Для weekly используем days_of_week из настроек или понедельник по умолчанию
                        days_of_week = settings.days_of_week or "mon"
                    else:
                        days_of_week = "mon-sun"
                    
                    # Staggering: сдвиг времени на 5 минут для каждого пользователя
                    # Избегаем одновременных дайджестов → Rate Limit
                    base_time = settings.time  # "09:00"
                    hour, minute = map(int, base_time.split(":"))
                    
                    # Добавляем idx * 5 минут
                    minute += idx * 5
                    if minute >= 60:
                        hour += minute // 60
                        minute = minute % 60
                    
                    staggered_time = f"{hour:02d}:{minute:02d}"
                    
                    if idx > 0:  # Логируем только для сдвинутых пользователей
                        logger.info(f"📅 User {settings.user_id}: {base_time} → {staggered_time} (stagger +{idx*5}m)")
                    
                    await digest_scheduler.schedule_digest(
                        user_id=settings.user_id,
                        time=staggered_time,  # ← Сдвинутое время
                        days_of_week=days_of_week,
                        timezone=settings.timezone
                    )
                except Exception as e:
                    logger.error(f"❌ Не удалось запланировать дайджест для user {settings.user_id}: {e}")
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Ошибка запуска планировщика дайджестов: {e}")
    
    # Запуск cleanup scheduler для накопленных постов
    try:
        from cleanup_service import cleanup_service
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        
        cleanup_scheduler = AsyncIOScheduler()
        
        # Каждые 2 часа обрабатываем накопленные посты без тегов
        cleanup_scheduler.add_job(
            cleanup_service.process_untagged_posts,
            'interval',
            hours=2,
            id='cleanup_untagged',
            kwargs={'limit': 50}
        )
        
        # Каждые 2 часа обрабатываем посты без индексации
        cleanup_scheduler.add_job(
            cleanup_service.process_unindexed_posts,
            'interval',
            hours=2,
            id='cleanup_unindexed',
            kwargs={'limit': 50}
        )
        
        cleanup_scheduler.start()
        logger.info("✅ Cleanup scheduler запущен (каждые 2 часа)")
        
    except Exception as e:
        logger.error(f"❌ Ошибка запуска cleanup scheduler: {e}")
    
    logger.info("✅ RAG Service готов к работе")


@app.on_event("shutdown")
async def shutdown_event():
    """Корректная остановка сервиса"""
    logger.info("🛑 RAG Service останавливается...")
    try:
        digest_scheduler.stop()
    except Exception as e:
        logger.error(f"❌ Ошибка остановки планировщика: {e}")
    logger.info("✅ RAG Service остановлен")


@app.get("/")
async def root():
    """Корневой endpoint"""
    return {
        "service": "RAG Service",
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Проверка здоровья сервиса"""
    # Проверка Qdrant
    qdrant_connected = False
    try:
        collections = qdrant_client.client.get_collections()
        qdrant_connected = True
    except Exception as e:
        logger.error(f"❌ Qdrant недоступен: {e}")
    
    # Проверка GigaChat
    gigachat_available = config.GIGACHAT_ENABLED
    
    # Проверка OpenRouter (для RAG-генерации)
    openrouter_available = config.OPENROUTER_API_KEY is not None
    
    status = "healthy" if qdrant_connected else "degraded"
    
    return HealthResponse(
        status=status,
        qdrant_connected=qdrant_connected,
        gigachat_available=gigachat_available,
        openrouter_available=openrouter_available,
        version="0.1.0"
    )


# ============================================================================
# Endpoints для индексирования
# ============================================================================

@app.post("/rag/index/post/{post_id}")
async def index_post(
    post_id: int,
    background_tasks: BackgroundTasks
):
    """
    Индексировать один пост
    
    Args:
        post_id: ID поста для индексации
    """
    # Проверяем существование поста
    db = SessionLocal()
    try:
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post:
            raise HTTPException(404, f"Пост {post_id} не найден")
        
        user_id = post.user_id
    finally:
        db.close()
    
    # Запускаем индексацию в фоне
    background_tasks.add_task(indexer_service.index_post, post_id)
    
    return {
        "status": "queued",
        "post_id": post_id,
        "user_id": user_id,
        "message": "Индексация запущена в фоне"
    }


@app.post("/rag/index/batch")
async def index_batch(
    request: IndexBatchRequest,
    background_tasks: BackgroundTasks
):
    """
    Batch индексирование постов
    
    Args:
        request: Список ID постов
    """
    if not request.post_ids:
        raise HTTPException(400, "Список post_ids не может быть пустым")
    
    # Запускаем batch индексацию в фоне
    background_tasks.add_task(
        indexer_service.index_posts_batch,
        request.post_ids
    )
    
    return {
        "status": "queued",
        "total_posts": len(request.post_ids),
        "message": f"Batch индексация {len(request.post_ids)} постов запущена в фоне"
    }


@app.post("/rag/index/user/{user_id}")
async def index_user_posts(
    user_id: int,
    limit: Optional[int] = None,
    background_tasks: BackgroundTasks = None
):
    """
    Индексировать все непроиндексированные посты пользователя
    
    Args:
        user_id: ID пользователя
        limit: Ограничение количества постов (опционально)
    """
    # Проверяем существование пользователя
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(404, f"Пользователь {user_id} не найден")
    finally:
        db.close()
    
    # Запускаем индексацию (можно запустить в фоне или синхронно)
    if background_tasks:
        background_tasks.add_task(
            indexer_service.index_user_posts,
            user_id,
            limit
        )
        return {
            "status": "queued",
            "user_id": user_id,
            "message": "Индексация постов пользователя запущена в фоне"
        }
    else:
        # Синхронное выполнение
        result = await indexer_service.index_user_posts(user_id, limit)
        return result


@app.post("/rag/reindex/user/{user_id}")
async def reindex_user_posts(
    user_id: int,
    background_tasks: BackgroundTasks
):
    """
    Переиндексировать все посты пользователя
    
    Args:
        user_id: ID пользователя
    """
    # Проверяем существование пользователя
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(404, f"Пользователь {user_id} не найден")
    finally:
        db.close()
    
    # Запускаем переиндексацию в фоне
    background_tasks.add_task(
        indexer_service.reindex_user_posts,
        user_id
    )
    
    return {
        "status": "queued",
        "user_id": user_id,
        "message": "Переиндексация постов пользователя запущена в фоне"
    }


@app.post("/rag/retry/pending")
async def retry_pending_posts(
    user_id: Optional[int] = None,
    limit: int = 100,
    background_tasks: BackgroundTasks = None
):
    """
    Повторная индексация постов со статусом pending или failed
    
    Args:
        user_id: ID пользователя (опционально, если не указан - для всех)
        limit: Максимальное количество постов для обработки
    """
    db = SessionLocal()
    try:
        # Получаем посты со статусом pending или failed
        query = db.query(IndexingStatus).filter(
            IndexingStatus.status.in_(["pending", "failed"])
        )
        
        if user_id:
            # Проверяем существование пользователя
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(404, f"Пользователь {user_id} не найден")
            query = query.filter(IndexingStatus.user_id == user_id)
        
        pending_statuses = query.limit(limit).all()
        
        if not pending_statuses:
            return {
                "status": "success",
                "user_id": user_id,
                "total": 0,
                "message": "Нет постов для повторной индексации"
            }
        
        post_ids = [status.post_id for status in pending_statuses]
        
        logger.info(f"🔄 Retry индексации: {len(post_ids)} постов (user_id={user_id or 'all'})")
        
        # Запускаем индексацию в фоне
        if background_tasks:
            background_tasks.add_task(
                indexer_service.index_posts_batch,
                post_ids
            )
            return {
                "status": "queued",
                "user_id": user_id,
                "total": len(post_ids),
                "message": f"Повторная индексация {len(post_ids)} постов запущена в фоне"
            }
        else:
            # Синхронное выполнение
            result = await indexer_service.index_posts_batch(post_ids)
            result["user_id"] = user_id
            return result
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка retry pending posts: {e}")
        raise HTTPException(500, f"Ошибка retry: {str(e)}")
    finally:
        db.close()


# ============================================================================
# Endpoints для управления и статистики
# ============================================================================

@app.get("/rag/stats/{user_id}", response_model=CollectionStatsResponse)
async def get_collection_stats(user_id: int):
    """
    Получить статистику индексации пользователя
    
    Args:
        user_id: ID пользователя
    """
    db = SessionLocal()
    try:
        # Проверяем существование пользователя
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(404, f"Пользователь {user_id} не найден")
        
        # Получаем информацию о коллекции Qdrant
        collection_info = await qdrant_client.get_collection_info(user_id)
        
        # Получаем статистику из БД
        total_posts = db.query(Post).filter(Post.user_id == user_id).count()
        
        indexed_posts = db.query(IndexingStatus).filter(
            IndexingStatus.user_id == user_id,
            IndexingStatus.status == "success"
        ).count()
        
        pending_posts = db.query(IndexingStatus).filter(
            IndexingStatus.user_id == user_id,
            IndexingStatus.status == "pending"
        ).count()
        
        failed_posts = db.query(IndexingStatus).filter(
            IndexingStatus.user_id == user_id,
            IndexingStatus.status == "failed"
        ).count()
        
        # Если коллекция не существует
        if not collection_info:
            return CollectionStatsResponse(
                user_id=user_id,
                collection_name=qdrant_client.get_collection_name(user_id),
                vectors_count=0,
                points_count=0,
                indexed_posts=indexed_posts,
                pending_posts=pending_posts,
                failed_posts=failed_posts
            )
        
        return CollectionStatsResponse(
            user_id=user_id,
            collection_name=collection_info["name"],
            vectors_count=collection_info["vectors_count"],
            points_count=collection_info["points_count"],
            indexed_posts=indexed_posts,
            pending_posts=pending_posts,
            failed_posts=failed_posts
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка получения статистики: {e}")
        raise HTTPException(500, f"Ошибка получения статистики: {str(e)}")
    finally:
        db.close()


@app.delete("/rag/index/user/{user_id}")
async def delete_user_index(user_id: int):
    """
    Удалить индекс пользователя (коллекцию в Qdrant)
    
    Args:
        user_id: ID пользователя
    """
    db = SessionLocal()
    try:
        # Проверяем существование пользователя
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(404, f"Пользователь {user_id} не найден")
        
        # Удаляем коллекцию из Qdrant
        success = await qdrant_client.delete_collection(user_id)
        
        if not success:
            raise HTTPException(500, "Ошибка удаления коллекции из Qdrant")
        
        # Удаляем записи из indexing_status
        deleted_count = db.query(IndexingStatus).filter(
            IndexingStatus.user_id == user_id
        ).delete()
        db.commit()
        
        return {
            "user_id": user_id,
            "collection_deleted": True,
            "indexing_records_deleted": deleted_count,
            "message": "Индекс пользователя успешно удален"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка удаления индекса: {e}")
        raise HTTPException(500, f"Ошибка удаления индекса: {str(e)}")
    finally:
        db.close()


# ============================================================================
# Endpoints для поиска
# ============================================================================

from search import search_service
from schemas import SearchRequest, SearchResponse, SearchResult


@app.get("/rag/search", response_model=SearchResponse)
async def search_posts(
    query: str,
    user_id: int,
    limit: int = 10,
    channel_id: Optional[int] = None,
    tags: Optional[str] = None,  # Comma-separated tags
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    min_score: Optional[float] = None
):
    """
    Гибридный поиск по постам
    
    Args:
        query: Поисковый запрос
        user_id: ID пользователя
        limit: Количество результатов (1-100)
        channel_id: Фильтр по каналу (опционально)
        tags: Фильтр по тегам, разделенные запятой (опционально)
        date_from: Фильтр по дате от (ISO format)
        date_to: Фильтр по дате до (ISO format)
        min_score: Минимальный score (0.0-1.0)
    """
    try:
        from datetime import datetime as dt
        
        # Проверяем пользователя
        db = SessionLocal()
        user = db.query(User).filter(User.id == user_id).first()
        db.close()
        
        if not user:
            raise HTTPException(404, f"Пользователь {user_id} не найден")
        
        # Парсим теги
        tags_list = None
        if tags:
            tags_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        
        # Парсим даты
        date_from_obj = None
        date_to_obj = None
        if date_from:
            date_from_obj = dt.fromisoformat(date_from.replace('Z', '+00:00'))
        if date_to:
            date_to_obj = dt.fromisoformat(date_to.replace('Z', '+00:00'))
        
        # Выполняем поиск
        results = await search_service.search(
            query=query,
            user_id=user_id,
            limit=limit,
            channel_id=channel_id,
            tags=tags_list,
            date_from=date_from_obj,
            date_to=date_to_obj,
            min_score=min_score
        )
        
        # Форматируем результаты
        search_results = [
            SearchResult(
                post_id=r["post_id"],
                score=r["score"],
                text=r["text"],
                channel_id=r["channel_id"],
                channel_username=r["channel_username"],
                posted_at=r["posted_at"],
                url=r["url"],
                tags=r["tags"],
                views=r["views"]
            )
            for r in results
        ]
        
        return SearchResponse(
            query=query,
            user_id=user_id,
            results_count=len(search_results),
            results=search_results,
            filters_applied={
                "channel_id": channel_id,
                "tags": tags_list,
                "date_from": date_from,
                "date_to": date_to,
                "min_score": min_score or config.RAG_MIN_SCORE
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка поиска: {e}")
        raise HTTPException(500, f"Ошибка поиска: {str(e)}")


@app.get("/rag/search/similar/{post_id}")
async def search_similar(
    post_id: int,
    limit: int = 5
):
    """
    Найти похожие посты
    
    Args:
        post_id: ID поста
        limit: Количество результатов
    """
    try:
        results = await search_service.search_similar_posts(post_id, limit)
        
        # Исключаем сам пост из результатов
        results = [r for r in results if r["post_id"] != post_id][:limit]
        
        return {
            "post_id": post_id,
            "similar_count": len(results),
            "similar_posts": results
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка поиска похожих постов: {e}")
        raise HTTPException(500, f"Ошибка поиска похожих постов: {str(e)}")


@app.get("/rag/tags/popular/{user_id}")
async def get_popular_tags(
    user_id: int,
    limit: int = 20
):
    """
    Получить популярные теги пользователя
    
    Args:
        user_id: ID пользователя
        limit: Количество тегов
    """
    try:
        tags = await search_service.get_popular_tags(user_id, limit)
        
        return {
            "user_id": user_id,
            "tags_count": len(tags),
            "tags": tags
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения популярных тегов: {e}")
        raise HTTPException(500, f"Ошибка получения тегов: {str(e)}")


@app.get("/rag/channels/stats/{user_id}")
async def get_channel_stats(user_id: int):
    """
    Получить статистику по каналам пользователя
    
    Args:
        user_id: ID пользователя
    """
    try:
        stats = await search_service.get_channel_stats(user_id)
        
        return {
            "user_id": user_id,
            "channels_count": len(stats),
            "channels": stats
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения статистики каналов: {e}")
        raise HTTPException(500, f"Ошибка получения статистики: {str(e)}")


# ============================================================================
# Endpoints для RAG-генерации
# ============================================================================

from generator import rag_generator
from schemas import AskRequest, AskResponse, Source


@app.post("/rag/ask", response_model=AskResponse)
async def ask_question(request: AskRequest):
    """
    Задать вопрос и получить RAG-ответ
    
    Args:
        request: Запрос с вопросом и параметрами фильтрации
    """
    try:
        # Генерируем ответ
        result = await rag_generator.generate_answer(
            query=request.query,
            user_id=request.user_id,
            context_limit=request.context_limit,
            channels=request.channels,
            tags=request.tags,
            date_from=request.date_from,
            date_to=request.date_to
        )
        
        # Проверяем на ошибки
        if "error" in result and not result.get("answer"):
            raise HTTPException(500, result["error"])
        
        # Форматируем источники
        sources = [
            Source(
                post_id=s["post_id"],
                channel_username=s["channel_username"],
                posted_at=s["posted_at"],
                url=s["url"],
                excerpt=s["excerpt"]
            )
            for s in result.get("sources", [])
        ]
        
        return AskResponse(
            query=request.query,
            answer=result["answer"],
            sources=sources,
            context_used=result["context_used"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка RAG-генерации: {e}")
        raise HTTPException(500, f"Ошибка генерации ответа: {str(e)}")


# ============================================================================
# Endpoints для дайджестов
# ============================================================================

from digest_generator import digest_generator
from schemas import DigestRequest, DigestResponse, DigestSettingsUpdate, DigestSettingsResponse, UserInterestsResponse


@app.post("/rag/digest/generate", response_model=DigestResponse)
async def generate_digest(request: DigestRequest):
    """
    Сгенерировать дайджест постов
    
    Args:
        request: Параметры дайджеста
    """
    try:
        result = await digest_generator.generate_digest(
            user_id=request.user_id,
            date_from=request.date_from,
            date_to=request.date_to,
            channels=request.channels,
            tags=request.tags,
            format=request.format,
            max_posts=request.max_posts
        )
        
        return DigestResponse(**result)
        
    except Exception as e:
        logger.error(f"❌ Ошибка генерации дайджеста: {e}")
        raise HTTPException(500, f"Ошибка генерации дайджеста: {str(e)}")


@app.get("/rag/digest/settings/{user_id}", response_model=DigestSettingsResponse)
async def get_digest_settings(user_id: int):
    """Получить настройки дайджеста пользователя"""
    db = SessionLocal()
    try:
        from models import DigestSettings
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(404, f"Пользователь {user_id} не найден")
        
        settings = db.query(DigestSettings).filter(
            DigestSettings.user_id == user_id
        ).first()
        
        if not settings:
            # Создаем настройки по умолчанию
            settings = DigestSettings(user_id=user_id)
            db.add(settings)
            db.commit()
            db.refresh(settings)
        
        return DigestSettingsResponse(
            user_id=settings.user_id,
            enabled=settings.enabled,
            frequency=settings.frequency,
            time=settings.time,
            days_of_week=settings.days_of_week,
            timezone=settings.timezone,
            channels=settings.channels,
            tags=settings.tags,
            format=settings.format,
            max_posts=settings.max_posts,
            delivery_method=settings.delivery_method,
            email=settings.email,
            last_sent_at=settings.last_sent_at,
            next_scheduled_at=settings.next_scheduled_at,
            # AI Summarization
            ai_summarize=settings.ai_summarize if hasattr(settings, 'ai_summarize') else False,
            preferred_topics=settings.preferred_topics if hasattr(settings, 'preferred_topics') else None,
            summary_style=settings.summary_style if hasattr(settings, 'summary_style') else "concise",
            topics_limit=settings.topics_limit if hasattr(settings, 'topics_limit') else 5
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка получения настроек дайджеста: {e}")
        raise HTTPException(500, f"Ошибка получения настроек: {str(e)}")
    finally:
        db.close()


@app.put("/rag/digest/settings/{user_id}")
async def update_digest_settings(user_id: int, request: DigestSettingsUpdate):
    """Обновить настройки дайджеста"""
    db = SessionLocal()
    try:
        from models import DigestSettings
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(404, f"Пользователь {user_id} не найден")
        
        settings = db.query(DigestSettings).filter(
            DigestSettings.user_id == user_id
        ).first()
        
        if not settings:
            settings = DigestSettings(user_id=user_id)
            db.add(settings)
        
        # Обновляем поля
        if request.enabled is not None:
            settings.enabled = request.enabled
        if request.frequency is not None:
            settings.frequency = request.frequency
        if request.time is not None:
            settings.time = request.time
        if request.days_of_week is not None:
            settings.days_of_week = request.days_of_week
        if request.timezone is not None:
            settings.timezone = request.timezone
        if request.channels is not None:
            settings.channels = request.channels
        if request.tags is not None:
            settings.tags = request.tags
        if request.format is not None:
            settings.format = request.format
        if request.max_posts is not None:
            settings.max_posts = request.max_posts
        if request.delivery_method is not None:
            settings.delivery_method = request.delivery_method
        if request.email is not None:
            settings.email = request.email
        
        # AI Summarization поля
        if request.ai_summarize is not None:
            settings.ai_summarize = request.ai_summarize
        if request.preferred_topics is not None:
            settings.preferred_topics = request.preferred_topics
        if request.summary_style is not None:
            settings.summary_style = request.summary_style
        if request.topics_limit is not None:
            settings.topics_limit = request.topics_limit
        
        db.commit()
        
        return {"message": "Настройки дайджеста обновлены", "user_id": user_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка обновления настроек дайджеста: {e}")
        raise HTTPException(500, f"Ошибка обновления настроек: {str(e)}")
    finally:
        db.close()


@app.get("/rag/digest/interests/{user_id}", response_model=UserInterestsResponse)
async def get_user_interests(user_id: int):
    """
    Получить интересы пользователя (вручную указанные + из истории запросов)
    
    Args:
        user_id: ID пользователя
        
    Returns:
        Сводка интересов пользователя
    """
    try:
        from ai_digest_generator import ai_digest_generator
        
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(404, f"Пользователь {user_id} не найден")
            
            # Получаем сводку интересов
            interests = await ai_digest_generator.get_user_interests_summary(user_id)
            
            return UserInterestsResponse(
                user_id=user_id,
                preferred_topics=interests['preferred_topics'],
                inferred_topics=interests['inferred_topics'],
                combined_topics=interests['combined_topics']
            )
            
        finally:
            db.close()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка получения интересов: {e}")
        raise HTTPException(500, f"Ошибка получения интересов: {str(e)}")


@app.post("/rag/digest/send/{user_id}")
async def send_digest_now(user_id: int):
    """
    Отправить дайджест пользователю прямо сейчас (ручной триггер)
    
    Args:
        user_id: ID пользователя
        
    Returns:
        Статус отправки
    """
    try:
        logger.info(f"🔔 Ручная отправка дайджеста для user {user_id}")
        
        # Вызываем метод scheduler для отправки дайджеста
        await digest_scheduler._send_digest(user_id)
        
        return {
            "status": "success",
            "message": f"Дайджест отправлен пользователю {user_id}",
            "user_id": user_id
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка ручной отправки дайджеста: {e}")
        raise HTTPException(500, f"Ошибка отправки дайджеста: {str(e)}")


# ============================================================================
# Endpoints для cleanup накопленных постов
# ============================================================================

@app.post("/rag/cleanup/backlog")
async def cleanup_backlog(background_tasks: BackgroundTasks):
    """
    Ручная очистка накопленных постов
    
    Запускает обработку:
    - Постов без тегов (в статусе pending/failed)
    - Постов без индексации в Qdrant
    
    Returns:
        Статус запуска cleanup
    """
    try:
        from cleanup_service import cleanup_service
        
        # Запускаем в фоне обработку накопленных постов
        background_tasks.add_task(cleanup_service.process_untagged_posts, limit=100)
        background_tasks.add_task(cleanup_service.process_unindexed_posts, limit=100)
        
        logger.info("🧹 Запущен manual cleanup накопленных постов")
        
        return {
            "status": "queued",
            "message": "Cleanup запущен в фоне (тегирование + индексация)",
            "tasks": ["process_untagged_posts", "process_unindexed_posts"]
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка запуска cleanup: {e}")
        raise HTTPException(500, f"Ошибка запуска cleanup: {str(e)}")


@app.get("/rag/cleanup/stats")
async def get_cleanup_stats():
    """
    Получить статистику накопленных постов
    
    Returns:
        Статистика по постам без тегов/индексации
    """
    try:
        from cleanup_service import cleanup_service
        
        stats = await cleanup_service.get_backlog_stats()
        
        return {
            "status": "success",
            "stats": stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения статистики cleanup: {e}")
        raise HTTPException(500, f"Ошибка получения статистики: {str(e)}")


@app.get("/rag/recommend/{user_id}")
async def get_recommendations(user_id: int, limit: int = 5):
    """
    Получить персональные рекомендации на основе интересов пользователя
    
    Args:
        user_id: ID пользователя
        limit: Количество рекомендаций (по умолчанию 5)
        
    Returns:
        Список рекомендованных постов с релевантностью
    """
    try:
        from ai_digest_generator import ai_digest_generator
        from sqlalchemy.orm import joinedload
        
        logger.info(f"🎯 Генерация рекомендаций для user {user_id}")
        
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(404, f"Пользователь {user_id} не найден")
            
            # Получаем интересы пользователя
            interests = await ai_digest_generator.get_user_interests_summary(user_id)
            combined_topics = interests.get('combined_topics', [])
            
            if not combined_topics:
                logger.info(f"   💡 Нет данных об интересах для user {user_id}")
                return {
                    "recommendations": [],
                    "message": "Недостаточно данных для рекомендаций. Используйте /ask для анализа интересов."
                }
            
            logger.info(f"   🔍 Темы интересов: {', '.join(combined_topics[:3])}...")
            
            # Собираем релевантные посты для каждой темы
            all_recommendations = []
            seen_post_ids = set()
            
            for topic in combined_topics[:3]:  # Топ-3 темы
                try:
                    # Векторный поиск по теме
                    embedding, provider = await embeddings_service.generate_embedding(topic)
                    if not embedding:
                        continue
                    
                    results = await qdrant_client.search(
                        user_id=user_id,
                        query_vector=embedding,
                        limit=5,
                        score_threshold=0.6
                    )
                    
                    # Добавляем уникальные результаты
                    for result in results:
                        post_id = result['payload']['post_id']
                        if post_id not in seen_post_ids:
                            seen_post_ids.add(post_id)
                            all_recommendations.append({
                                'post_id': post_id,
                                'score': result['score'],
                                'topic': topic
                            })
                    
                except Exception as e:
                    logger.error(f"   ❌ Ошибка поиска по теме '{topic}': {e}")
                    continue
            
            # Сортируем по score
            all_recommendations.sort(key=lambda x: x['score'], reverse=True)
            top_recommendations = all_recommendations[:limit]
            
            if not top_recommendations:
                logger.info(f"   💡 Посты не найдены для тем: {combined_topics}")
                return {
                    "recommendations": [],
                    "message": "Релевантные посты не найдены. Попробуйте добавить больше каналов."
                }
            
            # Обогащаем данными из БД
            enriched_recommendations = []
            for rec in top_recommendations:
                post = db.query(Post).options(
                    joinedload(Post.channel)
                ).filter(Post.id == rec['post_id']).first()
                
                if post:
                    enriched_recommendations.append({
                        'post_id': post.id,
                        'channel': post.channel.channel_username if post.channel else 'unknown',
                        'title': post.text[:100] if post.text else 'Без текста',
                        'url': post.url,
                        'score': rec['score'],
                        'topic': rec['topic'],
                        'posted_at': post.posted_at.isoformat() if post.posted_at else None
                    })
            
            logger.info(f"   ✅ Найдено {len(enriched_recommendations)} рекомендаций")
            
            return {
                "recommendations": enriched_recommendations,
                "based_on_topics": combined_topics[:3]
            }
            
        finally:
            db.close()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка генерации рекомендаций: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(500, f"Ошибка генерации рекомендаций: {str(e)}")


# ============================================================================
# Hybrid Search (Посты + Веб через Searxng)
# ============================================================================

async def search_web_searxng(query: str, limit: int = 5) -> list:
    """
    Поиск в интернете через Searxng
    
    Args:
        query: Поисковый запрос
        limit: Максимальное количество результатов
        
    Returns:
        Список результатов веб-поиска
    """
    import httpx
    
    searxng_url = os.getenv("SEARXNG_URL", "https://searxng.produman.studio")
    searxng_user = os.getenv("SEARXNG_USER", "")
    searxng_password = os.getenv("SEARXNG_PASSWORD", "")
    searxng_enabled = os.getenv("SEARXNG_ENABLED", "false").lower() == "true"
    
    if not searxng_enabled:
        logger.warning("⚠️ Searxng отключен")
        return []
    
    try:
        auth = httpx.BasicAuth(searxng_user, searxng_password) if searxng_user and searxng_password else None
        
        async with httpx.AsyncClient(auth=auth, timeout=10.0) as client:
            response = await client.get(
                f"{searxng_url}/search",
                params={
                    "q": query,
                    "format": "json",
                    "categories": "general",
                    "engines": "google,bing,duckduckgo"
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                results = result.get("results", [])
                
                # Форматируем результаты
                web_results = []
                for r in results[:limit]:
                    web_results.append({
                        "title": r.get("title", "Без названия"),
                        "url": r.get("url", ""),
                        "content": r.get("content", ""),
                        "engine": r.get("engine", "unknown")
                    })
                
                logger.info(f"✅ Searxng: найдено {len(web_results)} результатов для '{query}'")
                return web_results
            else:
                logger.warning(f"⚠️ Searxng вернул статус {response.status_code}")
                return []
                
    except httpx.ConnectError as e:
        logger.warning(f"🔌 Searxng недоступен: {e}")
        return []
    except httpx.TimeoutException:
        logger.warning(f"⏳ Searxng timeout")
        return []
    except Exception as e:
        logger.error(f"❌ Ошибка Searxng: {e}")
        return []


class HybridSearchRequest(BaseModel):
    user_id: int
    query: str
    include_posts: bool = True
    include_web: bool = True
    limit: int = 5


@app.post("/rag/hybrid_search")
async def hybrid_search(request: HybridSearchRequest):
    """
    Гибридный поиск: посты пользователя + веб-поиск через Searxng
    
    Args:
        user_id: ID пользователя
        query: Поисковый запрос
        include_posts: Искать в постах пользователя
        include_web: Искать в интернете через Searxng
        limit: Максимальное количество результатов на каждый источник
        
    Returns:
        Результаты поиска из постов и веба
    """
    try:
        logger.info(f"🔍 Гибридный поиск для user {request.user_id}: '{request.query}'")
        
        results = {
            "query": request.query,
            "posts": [],
            "web": []
        }
        
        # Поиск в постах пользователя (через векторный поиск)
        if request.include_posts:
            try:
                from sqlalchemy.orm import joinedload
                
                # Используем векторный поиск для семантического понимания
                embedding, provider = await embeddings_service.generate_embedding(request.query)
                
                if embedding:
                    # Векторный поиск в Qdrant
                    search_results = await qdrant_client.search(
                        user_id=request.user_id,
                        query_vector=embedding,
                        limit=request.limit,
                        score_threshold=0.5  # Более низкий порог для широкого поиска
                    )
                    
                    # Обогащаем данными из БД
                    db = SessionLocal()
                    try:
                        matched_posts = []
                        for result in search_results:
                            post_id = result['payload']['post_id']
                            
                            post = db.query(Post).options(
                                joinedload(Post.channel)
                            ).filter(Post.id == post_id).first()
                            
                            if post:
                                matched_posts.append({
                                    "post_id": post.id,
                                    "channel": post.channel.channel_username if post.channel else "unknown",
                                    "text": post.text[:300] if post.text else "",
                                    "snippet": post.text[:150] if post.text else "",
                                    "url": post.url,
                                    "posted_at": post.posted_at.isoformat() if post.posted_at else None,
                                    "tags": post.tags,
                                    "score": result['score']
                                })
                        
                        results["posts"] = matched_posts
                        logger.info(f"   📱 Найдено постов: {len(matched_posts)}")
                    finally:
                        db.close()
                else:
                    logger.warning(f"   ⚠️ Не удалось сгенерировать embedding для запроса")
                    results["posts"] = []
                
            except Exception as e:
                logger.error(f"❌ Ошибка поиска в постах: {e}")
                import traceback
                logger.error(traceback.format_exc())
                results["posts"] = []
        
        # Поиск в интернете через Searxng
        if request.include_web:
            web_results = await search_web_searxng(request.query, limit=request.limit)
            results["web"] = web_results
            logger.info(f"   🌐 Найдено в вебе: {len(web_results)}")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Ошибка гибридного поиска: {e}")
        raise HTTPException(500, f"Ошибка поиска: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=config.HOST,
        port=config.PORT,
        log_level=config.LOG_LEVEL.lower()
    )

