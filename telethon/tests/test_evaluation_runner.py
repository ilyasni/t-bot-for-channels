"""
Unit tests for EvaluationRunner
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from datetime import datetime, timezone
import asyncio

from evaluation.evaluation_runner import EvaluationRunner
from evaluation.schemas import (
    GoldenDatasetItem, 
    TelegramContext, 
    ContextType,
    EvaluationResult,
    EvaluationMetrics,
    EvaluationRun
)


class TestEvaluationRunner:
    """Tests for EvaluationRunner"""
    
    @pytest.fixture
    def mock_pool(self):
        """Mock asyncpg pool"""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        return mock_pool, mock_conn
    
    @pytest.fixture
    def mock_golden_dataset_manager(self):
        """Mock GoldenDatasetManager"""
        mock_manager = AsyncMock()
        return mock_manager
    
    @pytest.fixture
    def mock_bot_evaluator(self):
        """Mock BotEvaluator"""
        mock_evaluator = AsyncMock()
        return mock_evaluator
    
    @pytest.fixture
    def sample_items(self):
        """Sample GoldenDatasetItems for testing"""
        telegram_context = TelegramContext(
            user_id=12345,
            channels=["automotive_news"],
            context_type=ContextType.SINGLE_CHANNEL
        )
        
        return [
            GoldenDatasetItem(
                item_id="test_001",
                dataset_name="test_dataset",
                category="automotive",
                input={"message_text": "Test query 1"},
                query="Test query 1",
                telegram_context=telegram_context,
                expected_output="Expected response 1",
                retrieved_contexts=["Context 1"]
            ),
            GoldenDatasetItem(
                item_id="test_002",
                dataset_name="test_dataset",
                category="tech",
                input={"message_text": "Test query 2"},
                query="Test query 2",
                telegram_context=telegram_context,
                expected_output="Expected response 2",
                retrieved_contexts=["Context 2"]
            )
        ]
    
    @pytest.fixture
    def runner(self, mock_pool, mock_golden_dataset_manager, mock_bot_evaluator):
        """EvaluationRunner with mocked dependencies"""
        pool, _ = mock_pool
        return EvaluationRunner(
            db_pool=pool,
            golden_dataset_manager=mock_golden_dataset_manager,
            bot_evaluator=mock_bot_evaluator
        )
    
    @pytest.mark.asyncio
    async def test_init_success(self, runner):
        """Test EvaluationRunner initialization"""
        assert runner.db_pool is not None
        assert runner.golden_dataset_manager is not None
        assert runner.bot_evaluator is not None
    
    @pytest.mark.asyncio
    async def test_create_evaluation_run_success(self, runner, mock_pool):
        """Test successful evaluation run creation"""
        pool, mock_conn = mock_pool
        mock_conn.fetchrow.return_value = {"id": 123, "run_id": "run_123"}
        
        run_id = await runner.create_evaluation_run(
            run_name="test_run",
            dataset_name="test_dataset",
            model_provider="openrouter",
            model_name="gpt-4o-mini",
            total_items=10
        )
        
        assert run_id == "run_123"
        
        # Verify database call
        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args[0][0]
        assert "INSERT INTO evaluation_run" in call_args
        assert "test_run" in call_args
        assert "test_dataset" in call_args
    
    @pytest.mark.asyncio
    async def test_create_evaluation_run_database_error(self, runner, mock_pool):
        """Test evaluation run creation with database error"""
        pool, mock_conn = mock_pool
        mock_conn.execute.side_effect = Exception("Database error")
        
        with pytest.raises(Exception, match="Database error"):
            await runner.create_evaluation_run(
                run_name="test_run",
                dataset_name="test_dataset",
                model_provider="openrouter",
                model_name="gpt-4o-mini",
                total_items=10
            )
    
    @pytest.mark.asyncio
    async def test_update_evaluation_run_status_success(self, runner, mock_pool):
        """Test successful evaluation run status update"""
        pool, mock_conn = mock_pool
        mock_conn.execute.return_value = "UPDATE 1"
        
        result = await runner.update_evaluation_run_status(
            run_id="run_123",
            status="completed",
            processed_items=10,
            successful_items=9,
            failed_items=1,
            overall_score=0.85
        )
        
        assert result is True
        
        # Verify database call
        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args[0][0]
        assert "UPDATE evaluation_run" in call_args
        assert "status = $2" in call_args
    
    @pytest.mark.asyncio
    async def test_save_evaluation_result_success(self, runner, mock_pool):
        """Test successful evaluation result saving"""
        pool, mock_conn = mock_pool
        mock_conn.execute.return_value = "INSERT 0 1"
        
        metrics = EvaluationMetrics(
            answer_correctness=0.85,
            faithfulness=0.90,
            context_relevance=0.75
        )
        
        result = EvaluationResult(
            item_id="test_001",
            run_id="run_123",
            model_response="Generated response",
            scores=metrics,
            overall_score=0.83,
            status="success"
        )
        
        success = await runner.save_evaluation_result(result)
        
        assert success is True
        
        # Verify database call
        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args[0][0]
        assert "INSERT INTO evaluation_result" in call_args
    
    @pytest.mark.asyncio
    async def test_run_evaluation_batch_success(self, runner, sample_items):
        """Test successful batch evaluation run"""
        # Mock dependencies
        runner.golden_dataset_manager.list_items.return_value = sample_items
        runner.bot_evaluator.evaluate_item.return_value = {
            "overall_score": 0.85,
            "scores": {"answer_correctness": 0.85},
            "status": "success",
            "error_message": None
        }
        
        # Mock create_evaluation_run and save_evaluation_result
        with patch.object(runner, 'create_evaluation_run', return_value="run_123"):
            with patch.object(runner, 'save_evaluation_result', return_value=True):
                with patch.object(runner, 'update_evaluation_run_status', return_value=True):
                    result = await runner.run_evaluation_batch(
                        dataset_name="test_dataset",
                        run_name="test_run",
                        model_provider="openrouter",
                        model_name="gpt-4o-mini",
                        max_items=10
                    )
        
        assert result["run_id"] == "run_123"
        assert result["total_items"] == 2
        assert result["successful_items"] == 2
        assert result["failed_items"] == 0
        assert result["overall_score"] == 0.85
        
        # Verify calls
        runner.golden_dataset_manager.list_items.assert_called_once()
        assert runner.bot_evaluator.evaluate_item.call_count == 2
    
    @pytest.mark.asyncio
    async def test_run_evaluation_batch_with_failures(self, runner, sample_items):
        """Test batch evaluation with some failures"""
        # Mock dependencies
        runner.golden_dataset_manager.list_items.return_value = sample_items
        
        # Mock evaluator to return one success, one failure
        async def mock_evaluate_item(*args, **kwargs):
            if args[0] == "test_001":  # item_id
                return {
                    "overall_score": 0.85,
                    "scores": {"answer_correctness": 0.85},
                    "status": "success",
                    "error_message": None
                }
            else:  # test_002
                return {
                    "overall_score": 0.0,
                    "scores": {},
                    "status": "failed",
                    "error_message": "Evaluation error"
                }
        
        runner.bot_evaluator.evaluate_item.side_effect = mock_evaluate_item
        
        # Mock other methods
        with patch.object(runner, 'create_evaluation_run', return_value="run_123"):
            with patch.object(runner, 'save_evaluation_result', return_value=True):
                with patch.object(runner, 'update_evaluation_run_status', return_value=True):
                    result = await runner.run_evaluation_batch(
                        dataset_name="test_dataset",
                        run_name="test_run",
                        model_provider="openrouter",
                        model_name="gpt-4o-mini",
                        max_items=10
                    )
        
        assert result["run_id"] == "run_123"
        assert result["total_items"] == 2
        assert result["successful_items"] == 1
        assert result["failed_items"] == 1
        assert result["overall_score"] == 0.425  # Average of 0.85 and 0.0
    
    @pytest.mark.asyncio
    async def test_run_evaluation_batch_empty_dataset(self, runner):
        """Test batch evaluation with empty dataset"""
        # Mock empty dataset
        runner.golden_dataset_manager.list_items.return_value = []
        
        with patch.object(runner, 'create_evaluation_run', return_value="run_123"):
            with patch.object(runner, 'update_evaluation_run_status', return_value=True):
                result = await runner.run_evaluation_batch(
                    dataset_name="empty_dataset",
                    run_name="test_run",
                    model_provider="openrouter",
                    model_name="gpt-4o-mini",
                    max_items=10
                )
        
        assert result["run_id"] == "run_123"
        assert result["total_items"] == 0
        assert result["successful_items"] == 0
        assert result["failed_items"] == 0
        assert result["overall_score"] == 0.0
    
    @pytest.mark.asyncio
    async def test_run_evaluation_batch_with_max_items_limit(self, runner, sample_items):
        """Test batch evaluation with max_items limit"""
        # Create more items than max_items
        extended_items = sample_items + [
            GoldenDatasetItem(
                item_id="test_003",
                dataset_name="test_dataset",
                category="groups",
                input={"message_text": "Test query 3"},
                query="Test query 3",
                telegram_context=TelegramContext(
                    user_id=12345,
                    channels=["group_news"],
                    context_type=ContextType.SINGLE_CHANNEL
                ),
                expected_output="Expected response 3",
                retrieved_contexts=["Context 3"]
            )
        ]
        
        runner.golden_dataset_manager.list_items.return_value = extended_items
        runner.bot_evaluator.evaluate_item.return_value = {
            "overall_score": 0.85,
            "scores": {"answer_correctness": 0.85},
            "status": "success",
            "error_message": None
        }
        
        with patch.object(runner, 'create_evaluation_run', return_value="run_123"):
            with patch.object(runner, 'save_evaluation_result', return_value=True):
                with patch.object(runner, 'update_evaluation_run_status', return_value=True):
                    result = await runner.run_evaluation_batch(
                        dataset_name="test_dataset",
                        run_name="test_run",
                        model_provider="openrouter",
                        model_name="gpt-4o-mini",
                        max_items=2  # Limit to 2 items
                    )
        
        assert result["total_items"] == 2  # Should be limited to max_items
        assert runner.bot_evaluator.evaluate_item.call_count == 2
    
    @pytest.mark.asyncio
    async def test_run_evaluation_batch_database_error(self, runner, sample_items):
        """Test batch evaluation with database error"""
        runner.golden_dataset_manager.list_items.return_value = sample_items
        runner.bot_evaluator.evaluate_item.return_value = {
            "overall_score": 0.85,
            "scores": {"answer_correctness": 0.85},
            "status": "success",
            "error_message": None
        }
        
        # Mock create_evaluation_run to raise error
        with patch.object(runner, 'create_evaluation_run', side_effect=Exception("Database error")):
            with pytest.raises(Exception, match="Database error"):
                await runner.run_evaluation_batch(
                    dataset_name="test_dataset",
                    run_name="test_run",
                    model_provider="openrouter",
                    model_name="gpt-4o-mini",
                    max_items=10
                )
    
    @pytest.mark.asyncio
    async def test_get_evaluation_run_success(self, runner, mock_pool):
        """Test successful evaluation run retrieval"""
        pool, mock_conn = mock_pool
        mock_run_data = {
            "id": 123,
            "run_id": "run_123",
            "run_name": "test_run",
            "dataset_name": "test_dataset",
            "model_provider": "openrouter",
            "model_name": "gpt-4o-mini",
            "status": "completed",
            "total_items": 10,
            "processed_items": 10,
            "successful_items": 9,
            "failed_items": 1,
            "avg_scores": '{"answer_correctness": 0.85}',
            "overall_score": 0.85,
            "started_at": datetime.now(timezone.utc),
            "completed_at": datetime.now(timezone.utc),
            "duration_seconds": 120.5,
            "metadata": '{"version": "1.0"}'
        }
        mock_conn.fetchrow.return_value = mock_run_data
        
        run = await runner.get_evaluation_run("run_123")
        
        assert run is not None
        assert run.run_id == "run_123"
        assert run.run_name == "test_run"
        assert run.dataset_name == "test_dataset"
        assert run.status == "completed"
        assert run.total_items == 10
        assert run.successful_items == 9
        assert run.failed_items == 1
        assert run.overall_score == 0.85
    
    @pytest.mark.asyncio
    async def test_get_evaluation_run_not_found(self, runner, mock_pool):
        """Test evaluation run retrieval when run doesn't exist"""
        pool, mock_conn = mock_pool
        mock_conn.fetchrow.return_value = None
        
        run = await runner.get_evaluation_run("nonexistent_run")
        
        assert run is None
    
    @pytest.mark.asyncio
    async def test_list_evaluation_results_success(self, runner, mock_pool):
        """Test successful evaluation results listing"""
        pool, mock_conn = mock_pool
        mock_results = [
            {
                "id": 1,
                "item_id": "test_001",
                "model_response": "Response 1",
                "scores": '{"answer_correctness": 0.85}',
                "overall_score": 0.85,
                "status": "success",
                "error_message": None,
                "created_at": datetime.now(timezone.utc)
            },
            {
                "id": 2,
                "item_id": "test_002",
                "model_response": "Response 2",
                "scores": '{"answer_correctness": 0.90}',
                "overall_score": 0.90,
                "status": "success",
                "error_message": None,
                "created_at": datetime.now(timezone.utc)
            }
        ]
        mock_conn.fetch.return_value = mock_results
        
        results = await runner.list_evaluation_results("run_123", limit=10, offset=0)
        
        assert len(results) == 2
        assert results[0]["item_id"] == "test_001"
        assert results[0]["overall_score"] == 0.85
        assert results[1]["item_id"] == "test_002"
        assert results[1]["overall_score"] == 0.90
    
    @pytest.mark.asyncio
    async def test_list_evaluation_results_with_filters(self, runner, mock_pool):
        """Test evaluation results listing with status filter"""
        pool, mock_conn = mock_pool
        mock_conn.fetch.return_value = []
        
        await runner.list_evaluation_results(
            "run_123",
            status="success",
            min_score=0.8,
            limit=5,
            offset=0
        )
        
        # Verify query includes filters
        call_args = mock_conn.fetch.call_args[0][0]
        assert "WHERE run_id = $1" in call_args
        assert "AND status = $2" in call_args
        assert "AND overall_score >= $3" in call_args


class TestEvaluationRunnerMetrics:
    """Tests for metrics integration in EvaluationRunner"""
    
    @pytest.fixture
    def mock_pool(self):
        """Mock asyncpg pool"""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        return mock_pool, mock_conn
    
    @pytest.fixture
    def runner(self, mock_pool):
        """EvaluationRunner with mocked dependencies"""
        pool, _ = mock_pool
        mock_golden_dataset_manager = AsyncMock()
        mock_bot_evaluator = AsyncMock()
        
        return EvaluationRunner(
            db_pool=pool,
            golden_dataset_manager=mock_golden_dataset_manager,
            bot_evaluator=mock_bot_evaluator
        )
    
    @pytest.mark.asyncio
    async def test_update_prometheus_metrics_success(self, runner):
        """Test Prometheus metrics update"""
        with patch('evaluation.evaluation_runner.increment_counter') as mock_increment:
            with patch('evaluation.evaluation_runner.observe_score') as mock_observe:
                with patch('evaluation.evaluation_runner.set_gauge') as mock_set_gauge:
                    await runner._update_prometheus_metrics(
                        dataset_name="test_dataset",
                        model_provider="openrouter",
                        model_name="gpt-4o-mini",
                        total_items=10,
                        successful_items=9,
                        failed_items=1,
                        overall_score=0.85
                    )
                    
                    # Verify metrics calls
                    assert mock_increment.call_count >= 2  # runs_total, items_processed
                    assert mock_observe.call_count >= 1  # duration_seconds
                    assert mock_set_gauge.call_count >= 1  # runs_active
    
    @pytest.mark.asyncio
    async def test_update_prometheus_metrics_with_error(self, runner):
        """Test Prometheus metrics update with error handling"""
        with patch('evaluation.evaluation_runner.increment_counter', side_effect=Exception("Metrics error")):
            # Should not raise exception, just log error
            await runner._update_prometheus_metrics(
                dataset_name="test_dataset",
                model_provider="openrouter",
                model_name="gpt-4o-mini",
                total_items=10,
                successful_items=9,
                failed_items=1,
                overall_score=0.85
            )
            # Test passes if no exception is raised


class TestEvaluationRunnerConcurrency:
    """Tests for concurrency handling in EvaluationRunner"""
    
    @pytest.fixture
    def mock_pool(self):
        """Mock asyncpg pool"""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        return mock_pool, mock_conn
    
    @pytest.fixture
    def runner(self, mock_pool):
        """EvaluationRunner with mocked dependencies"""
        pool, _ = mock_pool
        mock_golden_dataset_manager = AsyncMock()
        mock_bot_evaluator = AsyncMock()
        
        return EvaluationRunner(
            db_pool=pool,
            golden_dataset_manager=mock_golden_dataset_manager,
            bot_evaluator=mock_bot_evaluator
        )
    
    @pytest.mark.asyncio
    async def test_concurrent_evaluation_items(self, runner):
        """Test concurrent evaluation of multiple items"""
        # Create multiple items
        items = []
        for i in range(5):
            telegram_context = TelegramContext(
                user_id=12345,
                channels=["test_channel"],
                context_type=ContextType.SINGLE_CHANNEL
            )
            
            item = GoldenDatasetItem(
                item_id=f"concurrent_test_{i:03d}",
                dataset_name="test_dataset",
                category="test",
                input={"message_text": f"Test query {i}"},
                query=f"Test query {i}",
                telegram_context=telegram_context,
                expected_output=f"Expected response {i}",
                retrieved_contexts=[f"Context {i}"]
            )
            items.append(item)
        
        # Mock dependencies
        runner.golden_dataset_manager.list_items.return_value = items
        
        # Mock evaluator with different response times
        async def mock_evaluate_item(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate processing time
            return {
                "overall_score": 0.85,
                "scores": {"answer_correctness": 0.85},
                "status": "success",
                "error_message": None
            }
        
        runner.bot_evaluator.evaluate_item.side_effect = mock_evaluate_item
        
        # Mock other methods
        with patch.object(runner, 'create_evaluation_run', return_value="run_123"):
            with patch.object(runner, 'save_evaluation_result', return_value=True):
                with patch.object(runner, 'update_evaluation_run_status', return_value=True):
                    start_time = datetime.now()
                    result = await runner.run_evaluation_batch(
                        dataset_name="test_dataset",
                        run_name="concurrent_test",
                        model_provider="openrouter",
                        model_name="gpt-4o-mini",
                        max_items=5
                    )
                    end_time = datetime.now()
        
        # Verify results
        assert result["total_items"] == 5
        assert result["successful_items"] == 5
        assert result["failed_items"] == 0
        
        # Verify all items were evaluated
        assert runner.bot_evaluator.evaluate_item.call_count == 5
        
        # Verify concurrent execution (should be faster than sequential)
        duration = (end_time - start_time).total_seconds()
        assert duration < 0.5  # Should be much faster than 5 * 0.1 = 0.5 seconds
