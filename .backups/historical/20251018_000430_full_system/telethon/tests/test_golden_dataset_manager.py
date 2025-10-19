"""
Unit tests for GoldenDatasetManager
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from evaluation.golden_dataset_manager import GoldenDatasetManager
from evaluation.schemas import GoldenDatasetItem, TelegramContext, ContextType, DifficultyLevel, ToneType


class TestGoldenDatasetManager:
    """Tests for GoldenDatasetManager"""
    
    @pytest.fixture
    def mock_pool(self):
        """Mock asyncpg pool"""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        return mock_pool, mock_conn
    
    @pytest.fixture
    def sample_item(self):
        """Sample GoldenDatasetItem for testing"""
        telegram_context = TelegramContext(
            user_id=12345,
            channels=["automotive_news"],
            context_type=ContextType.SINGLE_CHANNEL
        )
        
        return GoldenDatasetItem(
            item_id="test_001",
            dataset_name="test_dataset",
            category="automotive",
            input={"message_text": "Test query"},
            query="Test query",
            telegram_context=telegram_context,
            expected_output="Expected response",
            retrieved_contexts=["Context 1", "Context 2"],
            metadata={"source": "test"},
            difficulty=DifficultyLevel.BEGINNER,
            tone=ToneType.TECHNICAL,
            requires_multi_source=False
        )
    
    @pytest.fixture
    def manager(self, mock_pool):
        """GoldenDatasetManager with mocked pool"""
        pool, _ = mock_pool
        return GoldenDatasetManager(pool)
    
    @pytest.mark.asyncio
    async def test_add_item_success(self, manager, mock_pool, sample_item):
        """Test successful item addition"""
        pool, mock_conn = mock_pool
        mock_conn.execute.return_value = "INSERT 0 1"
        
        result = await manager.add_item(sample_item)
        
        # Verify database call
        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args[0][0]
        assert "INSERT INTO evaluation_golden_dataset" in call_args
        assert "test_001" in call_args
        assert "test_dataset" in call_args
        assert "automotive" in call_args
        
        # Verify parameters
        call_kwargs = mock_conn.execute.call_args[0][1]
        assert call_kwargs == (
            "test_001",
            "test_dataset", 
            "automotive",
            "Test query",
            json.dumps(sample_item.telegram_context.dict()),
            "Expected response",
            json.dumps(["Context 1", "Context 2"]),
            json.dumps({"source": "test"}),
            "beginner",
            "technical",
            False
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_add_item_database_error(self, manager, mock_pool, sample_item):
        """Test item addition with database error"""
        pool, mock_conn = mock_pool
        mock_conn.execute.side_effect = Exception("Database error")
        
        with pytest.raises(Exception, match="Database error"):
            await manager.add_item(sample_item)
    
    @pytest.mark.asyncio
    async def test_get_item_success(self, manager, mock_pool):
        """Test successful item retrieval"""
        pool, mock_conn = mock_pool
        mock_row = {
            "item_id": "test_001",
            "dataset_name": "test_dataset",
            "category": "automotive",
            "user_query": "Test query",
            "telegram_context": json.dumps({"user_id": 12345, "context_type": "single_channel"}),
            "reference_answer": "Expected response",
            "retrieved_context": json.dumps(["Context 1"]),
            "metadata": json.dumps({"source": "test"}),
            "difficulty": "beginner",
            "tone": "technical",
            "requires_multi_source": False,
            "created_at": datetime.now(timezone.utc),
            "updated_at": None
        }
        mock_conn.fetchrow.return_value = mock_row
        
        item = await manager.get_item("test_001", "test_dataset")
        
        assert item is not None
        assert item.item_id == "test_001"
        assert item.dataset_name == "test_dataset"
        assert item.category == "automotive"
        assert item.query == "Test query"
        assert item.expected_output == "Expected response"
        assert item.difficulty == DifficultyLevel.BEGINNER
        assert item.tone == ToneType.TECHNICAL
    
    @pytest.mark.asyncio
    async def test_get_item_not_found(self, manager, mock_pool):
        """Test item retrieval when item doesn't exist"""
        pool, mock_conn = mock_pool
        mock_conn.fetchrow.return_value = None
        
        item = await manager.get_item("nonexistent", "test_dataset")
        
        assert item is None
    
    @pytest.mark.asyncio
    async def test_list_items_success(self, manager, mock_pool):
        """Test successful items listing"""
        pool, mock_conn = mock_pool
        mock_rows = [
            {
                "item_id": "test_001",
                "category": "automotive",
                "difficulty": "beginner",
                "created_at": datetime.now(timezone.utc)
            },
            {
                "item_id": "test_002", 
                "category": "tech",
                "difficulty": "intermediate",
                "created_at": datetime.now(timezone.utc)
            }
        ]
        mock_conn.fetch.return_value = mock_rows
        
        items = await manager.list_items("test_dataset", limit=10, offset=0)
        
        assert len(items) == 2
        assert items[0]["item_id"] == "test_001"
        assert items[0]["category"] == "automotive"
        assert items[1]["item_id"] == "test_002"
        assert items[1]["category"] == "tech"
    
    @pytest.mark.asyncio
    async def test_list_items_with_filters(self, manager, mock_pool):
        """Test items listing with category and difficulty filters"""
        pool, mock_conn = mock_pool
        mock_conn.fetch.return_value = []
        
        await manager.list_items(
            "test_dataset",
            category="automotive",
            difficulty=DifficultyLevel.BEGINNER,
            limit=5,
            offset=0
        )
        
        # Verify query includes filters
        call_args = mock_conn.fetch.call_args[0][0]
        assert "WHERE dataset_name = $1" in call_args
        assert "AND category = $2" in call_args
        assert "AND difficulty = $3" in call_args
    
    @pytest.mark.asyncio
    async def test_update_item_success(self, manager, mock_pool, sample_item):
        """Test successful item update"""
        pool, mock_conn = mock_pool
        mock_conn.execute.return_value = "UPDATE 1"
        
        # Update some fields
        sample_item.expected_output = "Updated response"
        sample_item.difficulty = DifficultyLevel.INTERMEDIATE
        
        result = await manager.update_item(sample_item)
        
        # Verify database call
        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args[0][0]
        assert "UPDATE evaluation_golden_dataset" in call_args
        assert "SET" in call_args
        assert "updated_at = CURRENT_TIMESTAMP" in call_args
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_delete_item_success(self, manager, mock_pool):
        """Test successful item deletion"""
        pool, mock_conn = mock_pool
        mock_conn.execute.return_value = "DELETE 1"
        
        result = await manager.delete_item("test_001", "test_dataset")
        
        # Verify database call
        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args[0][0]
        assert "DELETE FROM evaluation_golden_dataset" in call_args
        assert "WHERE item_id = $1 AND dataset_name = $2" in call_args
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_delete_item_not_found(self, manager, mock_pool):
        """Test item deletion when item doesn't exist"""
        pool, mock_conn = mock_pool
        mock_conn.execute.return_value = "DELETE 0"
        
        result = await manager.delete_item("nonexistent", "test_dataset")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_dataset_stats_success(self, manager, mock_pool):
        """Test successful dataset statistics retrieval"""
        pool, mock_conn = mock_pool
        mock_stats = {
            "total": 10,
            "categories": json.dumps({"automotive": 5, "tech": 3, "groups": 2}),
            "difficulties": json.dumps({"beginner": 4, "intermediate": 4, "advanced": 2}),
            "tones": json.dumps({"technical": 6, "casual": 3, "formal": 1}),
            "multi_source": 3
        }
        mock_conn.fetchrow.return_value = mock_stats
        
        stats = await manager.get_dataset_stats("test_dataset")
        
        assert stats["total"] == 10
        assert stats["categories"] == {"automotive": 5, "tech": 3, "groups": 2}
        assert stats["difficulties"] == {"beginner": 4, "intermediate": 4, "advanced": 2}
        assert stats["tones"] == {"technical": 6, "casual": 3, "formal": 1}
        assert stats["multi_source_count"] == 3
    
    @pytest.mark.asyncio
    async def test_get_dataset_stats_empty_dataset(self, manager, mock_pool):
        """Test dataset statistics for empty dataset"""
        pool, mock_conn = mock_pool
        mock_stats = {
            "total": 0,
            "categories": None,
            "difficulties": None,
            "tones": None,
            "multi_source": 0
        }
        mock_conn.fetchrow.return_value = mock_stats
        
        stats = await manager.get_dataset_stats("empty_dataset")
        
        assert stats["total"] == 0
        assert stats["categories"] == {}
        assert stats["difficulties"] == {}
        assert stats["tones"] == {}
        assert stats["multi_source_count"] == 0
    
    @pytest.mark.asyncio
    async def test_list_datasets_success(self, manager, mock_pool):
        """Test successful datasets listing"""
        pool, mock_conn = mock_pool
        mock_datasets = [
            {
                "dataset_name": "automotive_qa",
                "total_items": 50,
                "categories": json.dumps({"automotive": 50}),
                "created_at": datetime.now(timezone.utc)
            },
            {
                "dataset_name": "tech_qa",
                "total_items": 30,
                "categories": json.dumps({"tech": 30}),
                "created_at": datetime.now(timezone.utc)
            }
        ]
        mock_conn.fetch.return_value = mock_datasets
        
        datasets = await manager.list_datasets()
        
        assert len(datasets) == 2
        assert datasets[0]["dataset_name"] == "automotive_qa"
        assert datasets[0]["total_items"] == 50
        assert datasets[1]["dataset_name"] == "tech_qa"
        assert datasets[1]["total_items"] == 30


class TestGoldenDatasetManagerImportExport:
    """Tests for import/export functionality"""
    
    @pytest.fixture
    def mock_pool(self):
        """Mock asyncpg pool"""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        return mock_pool, mock_conn
    
    @pytest.fixture
    def manager(self, mock_pool):
        """GoldenDatasetManager with mocked pool"""
        pool, _ = mock_pool
        return GoldenDatasetManager(pool)
    
    @pytest.mark.asyncio
    async def test_import_from_json_success(self, manager, mock_pool, tmp_path):
        """Test successful import from JSON file"""
        pool, mock_conn = mock_pool
        mock_conn.execute.return_value = "INSERT 0 1"
        
        # Create test JSON file
        json_data = {
            "name": "test_dataset",
            "description": "Test dataset",
            "category": "general",
            "items": [
                {
                    "item_id": "import_001",
                    "dataset_name": "test_dataset",
                    "category": "automotive",
                    "input": {"message_text": "Test query"},
                    "query": "Test query",
                    "telegram_context": {
                        "user_id": 12345,
                        "channels": ["automotive_news"],
                        "context_type": "single_channel"
                    },
                    "expected_output": "Expected response",
                    "difficulty": "beginner",
                    "tone": "technical"
                }
            ]
        }
        
        json_file = tmp_path / "test_dataset.json"
        json_file.write_text(json.dumps(json_data))
        
        result = await manager.import_from_json(str(json_file))
        
        assert result["imported"] == 1
        assert result["failed"] == 0
        assert result["dataset_name"] == "test_dataset"
        
        # Verify database calls
        assert mock_conn.execute.call_count == 1
    
    @pytest.mark.asyncio
    async def test_import_from_json_validation_error(self, manager, mock_pool, tmp_path):
        """Test import from JSON with validation error"""
        pool, mock_conn = mock_pool
        
        # Create invalid JSON file
        json_data = {
            "name": "test_dataset",
            "items": [
                {
                    "item_id": "invalid_001",
                    # Missing required fields
                    "dataset_name": "test_dataset"
                }
            ]
        }
        
        json_file = tmp_path / "invalid_dataset.json"
        json_file.write_text(json.dumps(json_data))
        
        result = await manager.import_from_json(str(json_file))
        
        assert result["imported"] == 0
        assert result["failed"] == 1
        assert len(result["errors"]) == 1
        assert "validation error" in result["errors"][0].lower()
    
    @pytest.mark.asyncio
    async def test_export_to_json_success(self, manager, mock_pool, tmp_path):
        """Test successful export to JSON file"""
        pool, mock_conn = mock_pool
        mock_items = [
            {
                "item_id": "export_001",
                "dataset_name": "test_dataset",
                "category": "automotive",
                "user_query": "Test query",
                "telegram_context": json.dumps({"user_id": 12345, "context_type": "single_channel"}),
                "reference_answer": "Expected response",
                "retrieved_context": None,
                "metadata": json.dumps({}),
                "difficulty": "beginner",
                "tone": "technical",
                "requires_multi_source": False,
                "created_at": datetime.now(timezone.utc),
                "updated_at": None
            }
        ]
        mock_conn.fetch.return_value = mock_items
        
        output_file = tmp_path / "exported_dataset.json"
        result = await manager.export_to_json("test_dataset", str(output_file))
        
        assert result is True
        assert output_file.exists()
        
        # Verify exported content
        exported_data = json.loads(output_file.read_text())
        assert exported_data["name"] == "test_dataset"
        assert len(exported_data["items"]) == 1
        assert exported_data["items"][0]["item_id"] == "export_001"
    
    @pytest.mark.asyncio
    async def test_export_to_json_empty_dataset(self, manager, mock_pool, tmp_path):
        """Test export of empty dataset"""
        pool, mock_conn = mock_pool
        mock_conn.fetch.return_value = []
        
        output_file = tmp_path / "empty_dataset.json"
        result = await manager.export_to_json("empty_dataset", str(output_file))
        
        assert result is True
        assert output_file.exists()
        
        # Verify exported content
        exported_data = json.loads(output_file.read_text())
        assert exported_data["name"] == "empty_dataset"
        assert len(exported_data["items"]) == 0


class TestGoldenDatasetManagerErrorHandling:
    """Tests for error handling scenarios"""
    
    @pytest.fixture
    def mock_pool_with_error(self):
        """Mock asyncpg pool that raises errors"""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_conn.execute.side_effect = Exception("Database connection error")
        return mock_pool, mock_conn
    
    @pytest.fixture
    def manager_with_error(self, mock_pool_with_error):
        """GoldenDatasetManager with error-throwing pool"""
        pool, _ = mock_pool_with_error
        return GoldenDatasetManager(pool)
    
    @pytest.mark.asyncio
    async def test_add_item_database_error(self, manager_with_error, sample_item):
        """Test add_item with database error"""
        with pytest.raises(Exception, match="Database connection error"):
            await manager_with_error.add_item(sample_item)
    
    @pytest.mark.asyncio
    async def test_get_item_database_error(self, manager_with_error):
        """Test get_item with database error"""
        with pytest.raises(Exception, match="Database connection error"):
            await manager_with_error.get_item("test_001", "test_dataset")
    
    @pytest.mark.asyncio
    async def test_import_from_json_file_not_found(self, manager, tmp_path):
        """Test import from non-existent file"""
        non_existent_file = tmp_path / "nonexistent.json"
        
        with pytest.raises(FileNotFoundError):
            await manager.import_from_json(str(non_existent_file))
    
    @pytest.mark.asyncio
    async def test_import_from_json_invalid_json(self, manager, tmp_path):
        """Test import from invalid JSON file"""
        invalid_json_file = tmp_path / "invalid.json"
        invalid_json_file.write_text("invalid json content")
        
        with pytest.raises(json.JSONDecodeError):
            await manager.import_from_json(str(invalid_json_file))
