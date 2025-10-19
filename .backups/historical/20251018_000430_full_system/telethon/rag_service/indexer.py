"""
Сервис индексирования постов в Qdrant
"""
import logging
import sys
import os
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone

# Добавляем родительскую директорию в path для импорта models
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import SessionLocal
from models import Post, User, IndexingStatus
from vector_db import qdrant_client
from embeddings import embeddings_service
import config

logger = logging.getLogger(__name__)


class IndexerService:
    """Сервис для индексации постов в Qdrant"""
    
    def __init__(self):
        """Инициализация сервиса индексирования"""
        self.qdrant = qdrant_client
        self.embeddings = embeddings_service
        logger.info("✅ Indexer Service инициализирован")
    
    async def index_post(
        self,
        post_id: int,
        db: Optional[Any] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Индексировать один пост
        
        Args:
            post_id: ID поста
            db: Сессия БД (опционально)
            
        Returns:
            Кортеж (успех, сообщение об ошибке)
        """
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True
        
        try:
            # Получаем пост
            post = db.query(Post).filter(Post.id == post_id).first()
            if not post:
                error_msg = f"Пост {post_id} не найден"
                logger.warning(f"⚠️ {error_msg}")
                return False, error_msg
            
            # Проверяем наличие текста
            if not post.text or not post.text.strip():
                error_msg = "Пост не содержит текста"
                logger.debug(f"⏭️ Пост {post_id}: {error_msg}")
                
                # Сохраняем статус как skipped
                self._save_indexing_status(
                    db, post.user_id, post_id,
                    status="skipped",
                    error=error_msg
                )
                return False, error_msg
            
            # Проверяем, нужно ли разбивать на chunks
            token_count = self.embeddings.count_tokens(post.text)
            max_tokens, overlap_tokens = self.embeddings.get_chunking_params("gigachat")
            
            if token_count <= max_tokens:
                # Индексируем пост целиком
                success = await self._index_single_chunk(
                    db, post, post.text, chunk_index=0, total_chunks=1
                )
                return success, None if success else "Ошибка индексации"
            else:
                # Разбиваем на chunks
                chunks = self.embeddings.chunk_text(
                    post.text,
                    max_tokens=max_tokens,
                    overlap_tokens=overlap_tokens
                )
                
                logger.info(f"📄 Пост {post_id}: разбит на {len(chunks)} chunks")
                
                # Индексируем каждый chunk
                success_count = 0
                for i, (chunk_text, start_pos, end_pos) in enumerate(chunks):
                    success = await self._index_single_chunk(
                        db, post, chunk_text,
                        chunk_index=i,
                        total_chunks=len(chunks),
                        start_pos=start_pos,
                        end_pos=end_pos
                    )
                    if success:
                        success_count += 1
                
                if success_count == len(chunks):
                    return True, None
                else:
                    error_msg = f"Проиндексировано {success_count}/{len(chunks)} chunks"
                    return False, error_msg
                    
        except Exception as e:
            error_msg = f"Ошибка индексации поста {post_id}: {e}"
            logger.error(f"❌ {error_msg}")
            
            # Сохраняем статус ошибки
            try:
                post = db.query(Post).filter(Post.id == post_id).first()
                if post:
                    self._save_indexing_status(
                        db, post.user_id, post_id,
                        status="failed",
                        error=str(e)[:500]
                    )
            except:
                pass
            
            return False, error_msg
            
        finally:
            if close_db:
                db.close()
    
    async def _index_single_chunk(
        self,
        db: Any,
        post: Post,
        chunk_text: str,
        chunk_index: int = 0,
        total_chunks: int = 1,
        start_pos: int = 0,
        end_pos: Optional[int] = None
    ) -> bool:
        """
        Индексировать один chunk текста
        
        Args:
            db: Сессия БД
            post: Объект Post
            chunk_text: Текст chunk'а
            chunk_index: Индекс chunk'а
            total_chunks: Общее количество chunks
            start_pos: Начальная позиция в оригинальном тексте
            end_pos: Конечная позиция в оригинальном тексте
            
        Returns:
            Успех операции
        """
        try:
            # Генерируем embedding
            result = await self.embeddings.generate_embedding(chunk_text)
            if not result:
                logger.error(f"❌ Не удалось сгенерировать embedding для поста {post.id}")
                return False
            
            embedding, provider = result
            
            # Формируем payload для Qdrant
            payload = {
                "post_id": post.id,
                "text": chunk_text,
                "channel_id": post.channel_id,
                "channel_username": post.channel.channel_username,
                "posted_at": post.posted_at.isoformat(),
                "tags": post.tags or [],
                "url": post.url,
                "views": post.views,
                "chunk_index": chunk_index,
                "total_chunks": total_chunks,
                "start_pos": start_pos,
                "end_pos": end_pos or len(chunk_text),
                "embedding_provider": provider
            }
            
            # Формируем уникальный ID для chunk'а (используем UUID формат)
            import uuid
            if total_chunks > 1:
                # Для chunks используем комбинацию post_id + chunk_index
                point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"post_{post.id}_chunk_{chunk_index}"))
            else:
                # Для одного chunk используем UUID на основе post_id
                point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"post_{post.id}"))
            
            # Сохраняем в Qdrant
            vector_id = await self.qdrant.upsert_point(
                user_id=post.user_id,
                point_id=point_id,
                vector=embedding,
                payload=payload
            )
            
            # Сохраняем статус индексации (только для первого chunk'а или если один chunk)
            if chunk_index == 0:
                self._save_indexing_status(
                    db, post.user_id, post.id,
                    vector_id=vector_id,
                    status="success"
                )
            
            logger.debug(f"✅ Пост {post.id} chunk {chunk_index+1}/{total_chunks} проиндексирован ({provider})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка индексации chunk'а {chunk_index} поста {post.id}: {e}")
            return False
    
    def _save_indexing_status(
        self,
        db: Any,
        user_id: int,
        post_id: int,
        vector_id: Optional[str] = None,
        status: str = "success",
        error: Optional[str] = None
    ):
        """
        Сохранить статус индексации в БД
        
        Args:
            db: Сессия БД
            user_id: ID пользователя
            post_id: ID поста
            vector_id: ID вектора в Qdrant
            status: Статус (success/failed/skipped)
            error: Сообщение об ошибке
        """
        try:
            # Проверяем существующий статус
            existing = db.query(IndexingStatus).filter(
                IndexingStatus.user_id == user_id,
                IndexingStatus.post_id == post_id
            ).first()
            
            if existing:
                # Обновляем существующий
                existing.indexed_at = datetime.now(timezone.utc)
                existing.vector_id = vector_id
                existing.status = status
                existing.error = error
            else:
                # Создаем новый
                indexing_status = IndexingStatus(
                    user_id=user_id,
                    post_id=post_id,
                    vector_id=vector_id,
                    status=status,
                    error=error
                )
                db.add(indexing_status)
            
            db.commit()
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения статуса индексации: {e}")
            db.rollback()
    
    async def index_posts_batch(
        self,
        post_ids: List[int]
    ) -> Dict[str, Any]:
        """
        Batch индексирование постов
        
        Args:
            post_ids: Список ID постов
            
        Returns:
            Статистика индексации
        """
        if not post_ids:
            return {
                "total": 0,
                "success": 0,
                "failed": 0,
                "skipped": 0,
                "errors": []
            }
        
        logger.info(f"🔄 Начало batch индексации {len(post_ids)} постов")
        
        db = SessionLocal()
        try:
            success_count = 0
            failed_count = 0
            skipped_count = 0
            errors = []
            
            for post_id in post_ids:
                success, error = await self.index_post(post_id, db)
                
                if success:
                    success_count += 1
                elif error and "не содержит текста" in error:
                    skipped_count += 1
                else:
                    failed_count += 1
                    if error:
                        errors.append({"post_id": post_id, "error": error})
            
            result = {
                "total": len(post_ids),
                "success": success_count,
                "failed": failed_count,
                "skipped": skipped_count,
                "errors": errors[:10]  # Ограничиваем количество ошибок
            }
            
            logger.info(
                f"✅ Batch индексация завершена: "
                f"успешно={success_count}, пропущено={skipped_count}, ошибок={failed_count}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Критическая ошибка batch индексации: {e}")
            raise
        finally:
            db.close()
    
    async def index_user_posts(
        self,
        user_id: int,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Индексировать все посты пользователя
        
        Args:
            user_id: ID пользователя
            limit: Ограничение количества постов (опционально)
            
        Returns:
            Статистика индексации
        """
        db = SessionLocal()
        try:
            # Получаем посты пользователя, которые еще не проиндексированы
            query = db.query(Post).filter(Post.user_id == user_id)
            
            # Исключаем уже проиндексированные
            indexed_post_ids = db.query(IndexingStatus.post_id).filter(
                IndexingStatus.user_id == user_id,
                IndexingStatus.status == "success"
            ).subquery()
            
            query = query.filter(~Post.id.in_(indexed_post_ids))
            
            if limit:
                query = query.limit(limit)
            
            posts = query.all()
            post_ids = [post.id for post in posts]
            
            logger.info(f"📊 Пользователь {user_id}: найдено {len(post_ids)} непроиндексированных постов")
            
            if not post_ids:
                return {
                    "user_id": user_id,
                    "total": 0,
                    "success": 0,
                    "failed": 0,
                    "skipped": 0,
                    "message": "Все посты уже проиндексированы"
                }
            
            # Индексируем batch
            result = await self.index_posts_batch(post_ids)
            result["user_id"] = user_id
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка индексации постов пользователя {user_id}: {e}")
            raise
        finally:
            db.close()
    
    async def reindex_user_posts(
        self,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Переиндексировать все посты пользователя (включая уже проиндексированные)
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Статистика индексации
        """
        db = SessionLocal()
        try:
            # Получаем все посты пользователя
            posts = db.query(Post).filter(Post.user_id == user_id).all()
            post_ids = [post.id for post in posts]
            
            logger.info(f"🔄 Переиндексация {len(post_ids)} постов пользователя {user_id}")
            
            if not post_ids:
                return {
                    "user_id": user_id,
                    "total": 0,
                    "success": 0,
                    "failed": 0,
                    "skipped": 0,
                    "message": "У пользователя нет постов"
                }
            
            # Удаляем существующие записи в indexing_status
            db.query(IndexingStatus).filter(
                IndexingStatus.user_id == user_id
            ).delete()
            db.commit()
            
            # Индексируем заново
            result = await self.index_posts_batch(post_ids)
            result["user_id"] = user_id
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка переиндексации постов пользователя {user_id}: {e}")
            raise
        finally:
            db.close()


# Глобальный экземпляр сервиса
indexer_service = IndexerService()

