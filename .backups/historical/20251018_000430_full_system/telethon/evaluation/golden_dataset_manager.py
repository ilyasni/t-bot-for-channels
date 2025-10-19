"""
Golden Dataset Manager

Управляет golden dataset для evaluation system.
Обеспечивает CRUD операции для golden Q&A, import/export,
и синхронизацию с Langfuse Datasets.

Best practices:
- Async/await для всех операций
- Graceful degradation если Langfuse недоступен
- Валидация данных с Pydantic
- PostgreSQL connection pooling
- JSON import/export с валидацией
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Union
from pathlib import Path

import asyncpg
from pydantic import ValidationError

from .schemas import (
    GoldenDatasetItem,
    GoldenDatasetCreate,
    TelegramContext,
    ContextType,
    DifficultyLevel,
    ToneType
)

logger = logging.getLogger(__name__)


class GoldenDatasetManager:
    """Manager для golden dataset operations"""
    
    def __init__(self, database_url: str):
        """
        Initialize Golden Dataset Manager
        
        Args:
            database_url: PostgreSQL connection URL
        """
        self.database_url = database_url
        self._pool: Optional[asyncpg.Pool] = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()
    
    async def initialize(self):
        """Инициализация manager (alias для connect)"""
        await self.connect()
    
    async def connect(self):
        """Создать connection pool"""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=10,
                command_timeout=60
            )
            logger.info("✅ Golden Dataset Manager connected to PostgreSQL")
    
    async def disconnect(self):
        """Закрыть connection pool"""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("✅ Golden Dataset Manager disconnected")
    
    async def create_dataset(self, dataset: GoldenDatasetCreate) -> Dict[str, Any]:
        """
        Создать новый golden dataset
        
        Args:
            dataset: Dataset configuration и items
            
        Returns:
            Dict с результатами создания
        """
        if not self._pool:
            await self.connect()
            
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                # Insert items
                inserted_count = 0
                errors = []
                
                for item in dataset.items:
                    try:
                        await self._insert_golden_item(conn, item)
                        inserted_count += 1
                    except Exception as e:
                        error_msg = f"Failed to insert item {item.item_id}: {str(e)}"
                        errors.append(error_msg)
                        logger.error(error_msg)
                
                result = {
                    "dataset_name": dataset.name,
                    "total_items": len(dataset.items),
                    "inserted_items": inserted_count,
                    "errors": errors,
                    "success": len(errors) == 0
                }
                
                logger.info(f"✅ Created dataset '{dataset.name}': {inserted_count}/{len(dataset.items)} items")
                return result
    
    async def _insert_golden_item(self, conn: asyncpg.Connection, item: GoldenDatasetItem):
        """Insert single golden item"""
        query = """
        INSERT INTO evaluation_golden_dataset (
            dataset_name, item_id, category, input_data, query,
            telegram_context, expected_output, retrieved_contexts,
            metadata, difficulty, tone, requires_multi_source
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        ON CONFLICT (item_id) DO UPDATE SET
            dataset_name = EXCLUDED.dataset_name,
            category = EXCLUDED.category,
            input_data = EXCLUDED.input_data,
            query = EXCLUDED.query,
            telegram_context = EXCLUDED.telegram_context,
            expected_output = EXCLUDED.expected_output,
            retrieved_contexts = EXCLUDED.retrieved_contexts,
            metadata = EXCLUDED.metadata,
            difficulty = EXCLUDED.difficulty,
            tone = EXCLUDED.tone,
            requires_multi_source = EXCLUDED.requires_multi_source,
            updated_at = NOW()
        """
        
        await conn.execute(
            query,
            item.dataset_name,
            item.item_id,
            item.category,
            json.dumps(item.input),
            item.query,
            json.dumps(item.telegram_context.dict()),
            item.expected_output,
            json.dumps(item.retrieved_contexts) if item.retrieved_contexts else None,
            json.dumps(item.metadata),
            item.difficulty if item.difficulty else None,
            item.tone if item.tone else None,
            item.requires_multi_source
        )
    
    async def get_dataset_items(
        self, 
        dataset_name: str,
        category: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[GoldenDatasetItem]:
        """
        Получить items из dataset
        
        Args:
            dataset_name: Название dataset
            category: Фильтр по категории (optional)
            limit: Максимальное количество items
            offset: Смещение для пагинации
            
        Returns:
            List of GoldenDatasetItem
        """
        if not self._pool:
            await self.connect()
            
        query = """
        SELECT 
            dataset_name, item_id, category, input_data, query,
            telegram_context, expected_output, retrieved_contexts,
            metadata, difficulty, tone, requires_multi_source,
            created_at, updated_at
        FROM evaluation_golden_dataset
        WHERE dataset_name = $1
        """
        params = [dataset_name]
        
        if category:
            query += " AND category = $" + str(len(params) + 1)
            params.append(category)
            
        query += " ORDER BY created_at DESC LIMIT $" + str(len(params) + 1) + " OFFSET $" + str(len(params) + 2)
        params.extend([limit, offset])
        
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            
            items = []
            for row in rows:
                try:
                    item = GoldenDatasetItem(
                        dataset_name=row['dataset_name'],
                        item_id=row['item_id'],
                        category=row['category'],
                        input=json.loads(row['input_data']),
                        query=row['query'],
                        telegram_context=TelegramContext(**json.loads(row['telegram_context'])),
                        expected_output=row['expected_output'],
                        retrieved_contexts=json.loads(row['retrieved_contexts']) if row['retrieved_contexts'] else None,
                        metadata=json.loads(row['metadata']) if row['metadata'] else {},
                        difficulty=DifficultyLevel(row['difficulty']) if row['difficulty'] else None,
                        tone=ToneType(row['tone']) if row['tone'] else None,
                        requires_multi_source=row['requires_multi_source'],
                        created_at=row['created_at'],
                        updated_at=row['updated_at']
                    )
                    items.append(item)
                except (ValidationError, json.JSONDecodeError) as e:
                    logger.error(f"❌ Failed to parse item {row['item_id']}: {e}")
                    
            return items
    
    async def get_dataset_stats(self, dataset_name: str) -> Dict[str, Any]:
        """
        Получить статистику dataset
        
        Args:
            dataset_name: Название dataset
            
        Returns:
            Dict со статистикой
        """
        if not self._pool:
            await self.connect()
            
        async with self._pool.acquire() as conn:
            # Общая статистика
            stats_query = """
            SELECT 
                COUNT(*) as total_items,
                COUNT(DISTINCT category) as categories_count,
                COUNT(DISTINCT difficulty) as difficulty_levels,
                AVG(CASE WHEN requires_multi_source THEN 1 ELSE 0 END) as multi_source_ratio
            FROM evaluation_golden_dataset
            WHERE dataset_name = $1
            """
            
            stats_row = await conn.fetchrow(stats_query, dataset_name)
            
            # Статистика по категориям
            category_query = """
            SELECT category, COUNT(*) as count
            FROM evaluation_golden_dataset
            WHERE dataset_name = $1
            GROUP BY category
            ORDER BY count DESC
            """
            
            category_rows = await conn.fetch(category_query, dataset_name)
            categories = {row['category']: row['count'] for row in category_rows}
            
            # Статистика по сложности
            difficulty_query = """
            SELECT difficulty, COUNT(*) as count
            FROM evaluation_golden_dataset
            WHERE dataset_name = $1 AND difficulty IS NOT NULL
            GROUP BY difficulty
            ORDER BY count DESC
            """
            
            difficulty_rows = await conn.fetch(difficulty_query, dataset_name)
            difficulties = {row['difficulty']: row['count'] for row in difficulty_rows}
            
            return {
                "dataset_name": dataset_name,
                "total_items": stats_row['total_items'],
                "categories_count": stats_row['categories_count'],
                "difficulty_levels": stats_row['difficulty_levels'],
                "multi_source_ratio": float(stats_row['multi_source_ratio']) if stats_row['multi_source_ratio'] else 0.0,
                "categories": categories,
                "difficulties": difficulties
            }
    
    async def delete_dataset(self, dataset_name: str) -> Dict[str, Any]:
        """
        Удалить dataset
        
        Args:
            dataset_name: Название dataset
            
        Returns:
            Dict с результатами удаления
        """
        if not self._pool:
            await self.connect()
            
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                # Count items before deletion
                count_query = "SELECT COUNT(*) FROM evaluation_golden_dataset WHERE dataset_name = $1"
                count = await conn.fetchval(count_query, dataset_name)
                
                # Delete items
                delete_query = "DELETE FROM evaluation_golden_dataset WHERE dataset_name = $1"
                deleted_rows = await conn.execute(delete_query, dataset_name)
                
                result = {
                    "dataset_name": dataset_name,
                    "deleted_items": count,
                    "success": True
                }
                
                logger.info(f"✅ Deleted dataset '{dataset_name}': {count} items")
                return result
    
    async def export_dataset(self, dataset_name: str, file_path: str) -> Dict[str, Any]:
        """
        Экспортировать dataset в JSON файл
        
        Args:
            dataset_name: Название dataset
            file_path: Путь к файлу для экспорта
            
        Returns:
            Dict с результатами экспорта
        """
        items = await self.get_dataset_items(dataset_name)
        
        export_data = {
            "version": "2.0.0",
            "dataset_name": dataset_name,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "total_items": len(items),
            "items": [item.dict() for item in items]
        }
        
        # Создать директорию если не существует
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        result = {
            "dataset_name": dataset_name,
            "file_path": file_path,
            "exported_items": len(items),
            "success": True
        }
        
        logger.info(f"✅ Exported dataset '{dataset_name}' to {file_path}: {len(items)} items")
        return result
    
    async def import_dataset(self, file_path: str) -> Dict[str, Any]:
        """
        Импортировать dataset из JSON файла
        
        Args:
            file_path: Путь к файлу для импорта
            
        Returns:
            Dict с результатами импорта
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Валидация структуры
            if not isinstance(data, dict) or 'items' not in data:
                raise ValueError("Invalid dataset format: missing 'items' field")
            
            items = []
            errors = []
            
            for item_data in data['items']:
                try:
                    item = GoldenDatasetItem(**item_data)
                    items.append(item)
                except ValidationError as e:
                    error_msg = f"Validation error for item {item_data.get('item_id', 'unknown')}: {e}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            if not items:
                raise ValueError("No valid items found in dataset")
            
            # Создать dataset
            dataset = GoldenDatasetCreate(
                name=data.get('dataset_name', 'imported_dataset'),
                description=data.get('description', 'Imported from file'),
                category=items[0].category,  # Assume all items have same category
                items=items,
                sync_to_langfuse=False  # Manual sync later
            )
            
            result = await self.create_dataset(dataset)
            result.update({
                "file_path": file_path,
                "imported_items": len(items),
                "validation_errors": errors
            })
            
            return result
            
        except Exception as e:
            error_msg = f"Import failed: {str(e)}"
            logger.error(error_msg)
            return {
                "file_path": file_path,
                "success": False,
                "error": error_msg
            }


# ============================================================================
# Singleton Instance
# ============================================================================

_golden_dataset_manager: Optional[GoldenDatasetManager] = None


async def get_golden_dataset_manager() -> GoldenDatasetManager:
    """
    Get singleton instance of Golden Dataset Manager
    
    Returns:
        GoldenDatasetManager instance
    """
    global _golden_dataset_manager
    
    if _golden_dataset_manager is None:
        database_url = os.getenv("TELEGRAM_DATABASE_URL") or os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("TELEGRAM_DATABASE_URL or DATABASE_URL environment variable not set")
            
        _golden_dataset_manager = GoldenDatasetManager(database_url)
        await _golden_dataset_manager.connect()
    
    return _golden_dataset_manager


async def close_golden_dataset_manager():
    """Close singleton instance"""
    global _golden_dataset_manager
    
    if _golden_dataset_manager:
        await _golden_dataset_manager.disconnect()
        _golden_dataset_manager = None
