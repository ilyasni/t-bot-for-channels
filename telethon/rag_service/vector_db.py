"""
Qdrant Client для работы с векторной БД
"""
import logging
from typing import List, Dict, Optional, Any
from qdrant_client import QdrantClient as QdrantClientBase
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    Range
)
from datetime import datetime
import config

logger = logging.getLogger(__name__)


class QdrantClient:
    """Клиент для работы с Qdrant векторной БД"""
    
    def __init__(self):
        """Инициализация клиента Qdrant"""
        self.client = QdrantClientBase(
            url=config.QDRANT_URL,
            api_key=config.QDRANT_API_KEY,
            timeout=config.QDRANT_TIMEOUT
        )
        logger.info(f"✅ Qdrant клиент инициализирован: {config.QDRANT_URL}")
    
    def get_collection_name(self, user_id: int) -> str:
        """Получить имя коллекции для пользователя"""
        return f"telegram_posts_{user_id}"
    
    async def ensure_collection(self, user_id: int, vector_size: int = 768):
        """
        Создать коллекцию для пользователя если не существует
        
        Args:
            user_id: ID пользователя
            vector_size: Размерность векторов (768 для GigaChat/sentence-transformers)
        """
        collection_name = self.get_collection_name(user_id)
        
        try:
            # Проверяем существование коллекции
            collections = self.client.get_collections().collections
            exists = any(c.name == collection_name for c in collections)
            
            if not exists:
                # Создаем коллекцию
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=vector_size,
                        distance=Distance.COSINE
                    )
                )
                
                # Создаем индексы для фильтров
                self.client.create_payload_index(
                    collection_name=collection_name,
                    field_name="channel_id",
                    field_schema="integer"
                )
                self.client.create_payload_index(
                    collection_name=collection_name,
                    field_name="posted_at",
                    field_schema="keyword"  # datetime хранится как ISO string
                )
                self.client.create_payload_index(
                    collection_name=collection_name,
                    field_name="tags",
                    field_schema="keyword"
                )
                
                logger.info(f"✅ Создана коллекция: {collection_name} (vector_size={vector_size})")
            else:
                logger.debug(f"Коллекция уже существует: {collection_name}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка создания коллекции {collection_name}: {e}")
            raise
    
    async def upsert_point(
        self,
        user_id: int,
        point_id: str,
        vector: List[float],
        payload: Dict[str, Any]
    ) -> str:
        """
        Добавить или обновить точку в коллекции
        
        Args:
            user_id: ID пользователя
            point_id: ID точки (обычно post_id)
            vector: Вектор embeddings
            payload: Метаданные (text, channel_id, posted_at, tags, url, etc.)
            
        Returns:
            ID добавленной точки
        """
        collection_name = self.get_collection_name(user_id)
        
        try:
            # Убеждаемся что коллекция существует
            await self.ensure_collection(user_id, vector_size=len(vector))
            
            # Создаем точку (ID должен быть строкой)
            point = PointStruct(
                id=str(point_id),
                vector=vector,
                payload=payload
            )
            
            # Добавляем в Qdrant
            self.client.upsert(
                collection_name=collection_name,
                points=[point]
            )
            
            logger.debug(f"✅ Точка {point_id} добавлена в {collection_name}")
            return point_id
            
        except Exception as e:
            logger.error(f"❌ Ошибка добавления точки {point_id}: {e}")
            raise
    
    async def upsert_points_batch(
        self,
        user_id: int,
        points: List[Dict[str, Any]]
    ) -> int:
        """
        Batch добавление точек
        
        Args:
            user_id: ID пользователя
            points: Список точек [{id, vector, payload}, ...]
            
        Returns:
            Количество добавленных точек
        """
        collection_name = self.get_collection_name(user_id)
        
        try:
            if not points:
                return 0
            
            # Убеждаемся что коллекция существует
            vector_size = len(points[0]["vector"])
            await self.ensure_collection(user_id, vector_size=vector_size)
            
            # Создаем список PointStruct (ID должны быть строками)
            point_structs = [
                PointStruct(
                    id=str(p["id"]),
                    vector=p["vector"],
                    payload=p["payload"]
                )
                for p in points
            ]
            
            # Batch upsert
            self.client.upsert(
                collection_name=collection_name,
                points=point_structs
            )
            
            logger.info(f"✅ Batch добавлено {len(points)} точек в {collection_name}")
            return len(points)
            
        except Exception as e:
            logger.error(f"❌ Ошибка batch добавления: {e}")
            raise
    
    async def search(
        self,
        user_id: int,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: Optional[float] = None,
        channel_id: Optional[int] = None,
        tags: Optional[List[str]] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Векторный поиск с фильтрами
        
        Args:
            user_id: ID пользователя
            query_vector: Вектор запроса
            limit: Количество результатов
            score_threshold: Минимальный score
            channel_id: Фильтр по каналу
            tags: Фильтр по тегам
            date_from: Фильтр по дате (от)
            date_to: Фильтр по дате (до)
            
        Returns:
            Список найденных точек с payload и score
        """
        collection_name = self.get_collection_name(user_id)
        
        try:
            # Проверяем существование коллекции
            collections = self.client.get_collections().collections
            if not any(c.name == collection_name for c in collections):
                logger.warning(f"Коллекция {collection_name} не существует")
                return []
            
            # Формируем фильтры
            filter_conditions = []
            
            if channel_id is not None:
                filter_conditions.append(
                    FieldCondition(
                        key="channel_id",
                        match=MatchValue(value=channel_id)
                    )
                )
            
            if tags:
                for tag in tags:
                    filter_conditions.append(
                        FieldCondition(
                            key="tags",
                            match=MatchValue(value=tag)
                        )
                    )
            
            # NOTE: date_from/date_to фильтр применяется на уровне БД при обогащении,
            # т.к. posted_at хранится как keyword (ISO string), а Range работает только с числами
            
            # Собираем Filter объект
            search_filter = Filter(must=filter_conditions) if filter_conditions else None
            
            # Выполняем поиск
            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=search_filter
            )
            
            # Форматируем результаты
            formatted_results = [
                {
                    "id": result.id,
                    "score": result.score,
                    "payload": result.payload
                }
                for result in results
            ]
            
            logger.info(f"🔍 Найдено {len(formatted_results)} результатов для user {user_id}")
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска: {e}")
            raise
    
    async def delete_point(self, user_id: int, point_id: str) -> bool:
        """Удалить точку из коллекции"""
        collection_name = self.get_collection_name(user_id)
        
        try:
            self.client.delete(
                collection_name=collection_name,
                points_selector=[str(point_id)]
            )
            logger.debug(f"🗑️ Точка {point_id} удалена из {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка удаления точки {point_id}: {e}")
            return False
    
    async def delete_collection(self, user_id: int) -> bool:
        """Удалить коллекцию пользователя"""
        collection_name = self.get_collection_name(user_id)
        
        try:
            self.client.delete_collection(collection_name=collection_name)
            logger.info(f"🗑️ Коллекция {collection_name} удалена")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка удаления коллекции {collection_name}: {e}")
            return False
    
    async def get_collection_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получить информацию о коллекции"""
        collection_name = self.get_collection_name(user_id)
        
        try:
            info = self.client.get_collection(collection_name=collection_name)
            return {
                "name": collection_name,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": info.status
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения информации о коллекции: {e}")
            return None


# Глобальный экземпляр клиента
qdrant_client = QdrantClient()

