"""
Unit tests for evaluation schemas
"""
import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from evaluation.schemas import (
    GoldenDatasetItem,
    TelegramContext,
    ContextType,
    DifficultyLevel,
    ToneType,
    EvaluationResult,
    EvaluationMetrics,
    EvaluationRun,
    EvaluationBatchRequest,
    EvaluationBatchResponse,
    EvaluationStatusResponse,
    EvaluationResultsResponse
)


class TestTelegramContext:
    """Tests for TelegramContext schema"""
    
    def test_valid_telegram_context(self):
        """Test creating valid TelegramContext"""
        context = TelegramContext(
            user_id=12345,
            channels=["automotive_news", "tech_news"],
            groups=["python_dev"],
            context_type=ContextType.SINGLE_CHANNEL,
            message_history=["Previous message 1", "Previous message 2"]
        )
        
        assert context.user_id == 12345
        assert context.channels == ["automotive_news", "tech_news"]
        assert context.groups == ["python_dev"]
        assert context.context_type == ContextType.SINGLE_CHANNEL
        assert context.message_history == ["Previous message 1", "Previous message 2"]
    
    def test_telegram_context_minimal(self):
        """Test creating minimal TelegramContext"""
        context = TelegramContext(
            user_id=12345,
            context_type=ContextType.SINGLE_CHANNEL
        )
        
        assert context.user_id == 12345
        assert context.channels == []
        assert context.groups == []
        assert context.context_type == ContextType.SINGLE_CHANNEL
        assert context.message_history == []
    
    def test_telegram_context_invalid_user_id(self):
        """Test TelegramContext with invalid user_id"""
        with pytest.raises(ValidationError):
            TelegramContext(
                user_id="invalid",  # Should be int
                context_type=ContextType.SINGLE_CHANNEL
            )


class TestGoldenDatasetItem:
    """Tests for GoldenDatasetItem schema"""
    
    def test_valid_golden_dataset_item(self):
        """Test creating valid GoldenDatasetItem"""
        telegram_context = TelegramContext(
            user_id=12345,
            channels=["automotive_news"],
            context_type=ContextType.SINGLE_CHANNEL
        )
        
        item = GoldenDatasetItem(
            item_id="test_001",
            dataset_name="test_dataset",
            category="automotive",
            input={"message_text": "Test query"},
            query="Test query",
            telegram_context=telegram_context,
            expected_output="Expected response",
            retrieved_contexts=["Context 1", "Context 2"],
            metadata={"source": "test", "year": "2024"},
            difficulty=DifficultyLevel.BEGINNER,
            tone=ToneType.TECHNICAL,
            requires_multi_source=False
        )
        
        assert item.item_id == "test_001"
        assert item.dataset_name == "test_dataset"
        assert item.category == "automotive"
        assert item.input == {"message_text": "Test query"}
        assert item.query == "Test query"
        assert item.telegram_context.user_id == 12345
        assert item.expected_output == "Expected response"
        assert item.retrieved_contexts == ["Context 1", "Context 2"]
        assert item.metadata == {"source": "test", "year": "2024"}
        assert item.difficulty == DifficultyLevel.BEGINNER
        assert item.tone == ToneType.TECHNICAL
        assert item.requires_multi_source is False
        assert item.created_at.tzinfo is not None  # timezone-aware
    
    def test_golden_dataset_item_minimal(self):
        """Test creating minimal GoldenDatasetItem"""
        telegram_context = TelegramContext(
            user_id=12345,
            context_type=ContextType.SINGLE_CHANNEL
        )
        
        item = GoldenDatasetItem(
            item_id="test_002",
            dataset_name="test_dataset",
            category="tech",
            input={"message_text": "Test"},
            query="Test",
            telegram_context=telegram_context,
            expected_output="Response"
        )
        
        assert item.item_id == "test_002"
        assert item.retrieved_contexts is None
        assert item.metadata == {}
        assert item.difficulty is None
        assert item.tone is None
        assert item.requires_multi_source is False
    
    def test_golden_dataset_item_missing_required_fields(self):
        """Test GoldenDatasetItem with missing required fields"""
        with pytest.raises(ValidationError):
            GoldenDatasetItem(
                # Missing required fields
                dataset_name="test_dataset",
                category="tech"
            )
    
    def test_golden_dataset_item_enum_values(self):
        """Test GoldenDatasetItem with different enum values"""
        telegram_context = TelegramContext(
            user_id=12345,
            context_type=ContextType.MULTI_CHANNEL
        )
        
        item = GoldenDatasetItem(
            item_id="test_003",
            dataset_name="test_dataset",
            category="groups",
            input={"message_text": "Group query"},
            query="Group query",
            telegram_context=telegram_context,
            expected_output="Group response",
            difficulty=DifficultyLevel.ADVANCED,
            tone=ToneType.CASUAL,
            requires_multi_source=True
        )
        
        assert item.telegram_context.context_type == ContextType.MULTI_CHANNEL
        assert item.difficulty == DifficultyLevel.ADVANCED
        assert item.tone == ToneType.CASUAL
        assert item.requires_multi_source is True


class TestEvaluationResult:
    """Tests for EvaluationResult schema"""
    
    def test_valid_evaluation_result(self):
        """Test creating valid EvaluationResult"""
        metrics = EvaluationMetrics(
            answer_correctness=0.85,
            faithfulness=0.90,
            context_relevance=0.75,
            channel_context_awareness=0.80,
            group_synthesis_quality=0.70,
            multi_source_coherence=0.65,
            tone_appropriateness=0.88
        )
        
        result = EvaluationResult(
            item_id="test_001",
            run_id="run_123",
            model_response="Generated response",
            scores=metrics,
            overall_score=0.80,
            status="success",
            langfuse_trace_id="trace_456"
        )
        
        assert result.item_id == "test_001"
        assert result.run_id == "run_123"
        assert result.model_response == "Generated response"
        assert result.scores.answer_correctness == 0.85
        assert result.overall_score == 0.80
        assert result.status == "success"
        assert result.langfuse_trace_id == "trace_456"
    
    def test_evaluation_result_with_error(self):
        """Test EvaluationResult with error"""
        result = EvaluationResult(
            item_id="test_002",
            run_id="run_123",
            model_response="",
            scores=EvaluationMetrics(),
            overall_score=0.0,
            status="failed",
            error_message="LLM API timeout"
        )
        
        assert result.status == "failed"
        assert result.error_message == "LLM API timeout"
        assert result.overall_score == 0.0


class TestEvaluationRun:
    """Tests for EvaluationRun schema"""
    
    def test_valid_evaluation_run(self):
        """Test creating valid EvaluationRun"""
        run = EvaluationRun(
            run_id="run_123",
            run_name="test_run",
            dataset_name="automotive_qa",
            model_provider="openrouter",
            model_name="gpt-4o-mini",
            status="completed",
            total_items=10,
            processed_items=10,
            successful_items=9,
            failed_items=1,
            avg_scores=EvaluationMetrics(
                answer_correctness=0.85,
                faithfulness=0.90
            ),
            overall_score=0.87,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            duration_seconds=120.5,
            metadata={"version": "1.0"}
        )
        
        assert run.run_id == "run_123"
        assert run.run_name == "test_run"
        assert run.dataset_name == "automotive_qa"
        assert run.model_provider == "openrouter"
        assert run.model_name == "gpt-4o-mini"
        assert run.status == "completed"
        assert run.total_items == 10
        assert run.successful_items == 9
        assert run.failed_items == 1
        assert run.overall_score == 0.87
        assert run.duration_seconds == 120.5


class TestEvaluationBatchRequest:
    """Tests for EvaluationBatchRequest schema"""
    
    def test_valid_batch_request(self):
        """Test creating valid EvaluationBatchRequest"""
        request = EvaluationBatchRequest(
            dataset_name="automotive_qa",
            run_name="test_run_2024",
            model_provider="openrouter",
            model_name="gpt-4o-mini",
            max_items=50,
            timeout_seconds=300
        )
        
        assert request.dataset_name == "automotive_qa"
        assert request.run_name == "test_run_2024"
        assert request.model_provider == "openrouter"
        assert request.model_name == "gpt-4o-mini"
        assert request.max_items == 50
        assert request.timeout_seconds == 300
    
    def test_batch_request_defaults(self):
        """Test EvaluationBatchRequest with defaults"""
        request = EvaluationBatchRequest(
            dataset_name="test_dataset",
            run_name="test_run"
        )
        
        assert request.dataset_name == "test_dataset"
        assert request.run_name == "test_run"
        assert request.model_provider is None
        assert request.model_name is None
        assert request.max_items is None
        assert request.timeout_seconds is None


class TestEvaluationBatchResponse:
    """Tests for EvaluationBatchResponse schema"""
    
    def test_valid_batch_response(self):
        """Test creating valid EvaluationBatchResponse"""
        response = EvaluationBatchResponse(
            run_id="run_123",
            run_name="test_run",
            status="started",
            total_items=10,
            message="Evaluation started successfully"
        )
        
        assert response.run_id == "run_123"
        assert response.run_name == "test_run"
        assert response.status == "started"
        assert response.total_items == 10
        assert response.message == "Evaluation started successfully"


class TestEvaluationStatusResponse:
    """Tests for EvaluationStatusResponse schema"""
    
    def test_valid_status_response(self):
        """Test creating valid EvaluationStatusResponse"""
        response = EvaluationStatusResponse(
            run_id="run_123",
            run_name="test_run",
            status="running",
            progress_percentage=65.0,
            total_items=10,
            processed_items=6,
            successful_items=5,
            failed_items=1,
            estimated_completion_time="2024-01-15T15:30:00Z"
        )
        
        assert response.run_id == "run_123"
        assert response.run_name == "test_run"
        assert response.status == "running"
        assert response.progress_percentage == 65.0
        assert response.processed_items == 6
        assert response.successful_items == 5
        assert response.failed_items == 1


class TestEvaluationResultsResponse:
    """Tests for EvaluationResultsResponse schema"""
    
    def test_valid_results_response(self):
        """Test creating valid EvaluationResultsResponse"""
        metrics = EvaluationMetrics(
            answer_correctness=0.85,
            faithfulness=0.90,
            context_relevance=0.75
        )
        
        response = EvaluationResultsResponse(
            run_id="run_123",
            run_name="test_run",
            status="completed",
            overall_score=0.83,
            avg_scores=metrics,
            total_items=10,
            successful_items=9,
            failed_items=1,
            duration_seconds=120.5,
            langfuse_url="http://localhost:3000/traces/run_123"
        )
        
        assert response.run_id == "run_123"
        assert response.run_name == "test_run"
        assert response.status == "completed"
        assert response.overall_score == 0.83
        assert response.avg_scores.answer_correctness == 0.85
        assert response.successful_items == 9
        assert response.duration_seconds == 120.5
        assert "langfuse" in response.langfuse_url


class TestSchemaSerialization:
    """Tests for schema serialization/deserialization"""
    
    def test_golden_dataset_item_serialization(self):
        """Test GoldenDatasetItem serialization to dict"""
        telegram_context = TelegramContext(
            user_id=12345,
            context_type=ContextType.SINGLE_CHANNEL
        )
        
        item = GoldenDatasetItem(
            item_id="test_001",
            dataset_name="test_dataset",
            category="automotive",
            input={"message_text": "Test"},
            query="Test query",
            telegram_context=telegram_context,
            expected_output="Response",
            difficulty=DifficultyLevel.BEGINNER,
            tone=ToneType.TECHNICAL
        )
        
        # Test serialization
        item_dict = item.dict()
        assert item_dict["item_id"] == "test_001"
        assert item_dict["difficulty"] == "beginner"  # Enum as string
        assert item_dict["tone"] == "technical"  # Enum as string
        
        # Test deserialization
        item_from_dict = GoldenDatasetItem(**item_dict)
        assert item_from_dict.item_id == "test_001"
        assert item_from_dict.difficulty == DifficultyLevel.BEGINNER
        assert item_from_dict.tone == ToneType.TECHNICAL
    
    def test_evaluation_metrics_serialization(self):
        """Test EvaluationMetrics serialization"""
        metrics = EvaluationMetrics(
            answer_correctness=0.85,
            faithfulness=0.90,
            context_relevance=0.75
        )
        
        metrics_dict = metrics.dict()
        assert metrics_dict["answer_correctness"] == 0.85
        assert metrics_dict["faithfulness"] == 0.90
        assert metrics_dict["context_relevance"] == 0.75
        
        # Test with None values
        metrics_dict["answer_correctness"] = None
        metrics_from_dict = EvaluationMetrics(**metrics_dict)
        assert metrics_from_dict.answer_correctness is None
        assert metrics_from_dict.faithfulness == 0.90
