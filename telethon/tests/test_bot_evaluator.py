"""
Unit tests for BotEvaluator
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from datetime import datetime, timezone

from evaluation.bot_evaluator import BotEvaluator
from evaluation.schemas import GoldenDatasetItem, TelegramContext, ContextType


class TestBotEvaluator:
    """Tests for BotEvaluator"""
    
    @pytest.fixture
    def mock_llm(self):
        """Mock LLM for testing"""
        mock_llm = AsyncMock()
        mock_llm.invoke.return_value = "Mocked LLM response"
        return mock_llm
    
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
            retrieved_contexts=["Context 1", "Context 2"]
        )
    
    @pytest.mark.asyncio
    async def test_init_with_ragas_available(self, mock_llm):
        """Test BotEvaluator initialization with Ragas available"""
        with patch('evaluation.bot_evaluator.RAGAS_AVAILABLE', True):
            with patch('evaluation.bot_evaluator.AnswerCorrectness') as mock_metric:
                with patch('evaluation.bot_evaluator.FactualCorrectness') as mock_factual:
                    with patch('evaluation.bot_evaluator.Faithfulness') as mock_faithfulness:
                        with patch('evaluation.bot_evaluator.ContextRelevance') as mock_relevance:
                            evaluator = BotEvaluator(
                                model_provider="openrouter",
                                model_name="gpt-4o-mini",
                                evaluator_llm=mock_llm
                            )
                            
                            assert evaluator.model_provider == "openrouter"
                            assert evaluator.model_name == "gpt-4o-mini"
                            assert evaluator.evaluator_llm == mock_llm
                            assert evaluator.ragas_metrics is not None
                            assert len(evaluator.ragas_metrics) > 0
    
    @pytest.mark.asyncio
    async def test_init_without_ragas(self, mock_llm):
        """Test BotEvaluator initialization without Ragas"""
        with patch('evaluation.bot_evaluator.RAGAS_AVAILABLE', False):
            evaluator = BotEvaluator(
                model_provider="openrouter",
                model_name="gpt-4o-mini",
                evaluator_llm=mock_llm
            )
            
            assert evaluator.model_provider == "openrouter"
            assert evaluator.model_name == "gpt-4o-mini"
            assert evaluator.evaluator_llm == mock_llm
            assert evaluator.ragas_metrics == []
    
    @pytest.mark.asyncio
    async def test_init_without_evaluator_llm(self):
        """Test BotEvaluator initialization without evaluator LLM"""
        evaluator = BotEvaluator(
            model_provider="openrouter",
            model_name="gpt-4o-mini",
            evaluator_llm=None
        )
        
        assert evaluator.evaluator_llm is None
        assert evaluator.ragas_metrics == []
    
    @pytest.mark.asyncio
    async def test_evaluate_item_success(self, mock_llm, sample_item):
        """Test successful item evaluation"""
        with patch('evaluation.bot_evaluator.RAGAS_AVAILABLE', True):
            with patch('evaluation.bot_evaluator.AnswerCorrectness') as mock_metric_class:
                # Mock metric instance
                mock_metric = Mock()
                mock_metric.ascore.return_value = 0.85
                mock_metric_class.return_value = mock_metric
                
                evaluator = BotEvaluator(
                    model_provider="openrouter",
                    model_name="gpt-4o-mini",
                    evaluator_llm=mock_llm
                )
                
                result = await evaluator.evaluate_item(
                    item_id="test_001",
                    query="Test query",
                    context=["Context 1", "Context 2"],
                    response="Generated response",
                    reference_answer="Expected response"
                )
                
                assert result["overall_score"] == 0.85
                assert "answer_correctness" in result["scores"]
                assert result["scores"]["answer_correctness"] == 0.85
                assert result["status"] == "success"
                assert result["error_message"] is None
    
    @pytest.mark.asyncio
    async def test_evaluate_item_without_ragas(self, mock_llm, sample_item):
        """Test item evaluation without Ragas"""
        with patch('evaluation.bot_evaluator.RAGAS_AVAILABLE', False):
            evaluator = BotEvaluator(
                model_provider="openrouter",
                model_name="gpt-4o-mini",
                evaluator_llm=mock_llm
            )
            
            result = await evaluator.evaluate_item(
                item_id="test_001",
                query="Test query",
                context=["Context 1"],
                response="Generated response",
                reference_answer="Expected response"
            )
            
            assert result["overall_score"] == 0.0
            assert result["scores"] == {}
            assert result["status"] == "failed"
            assert "Ragas not available" in result["error_message"]
    
    @pytest.mark.asyncio
    async def test_evaluate_item_ragas_error(self, mock_llm, sample_item):
        """Test item evaluation with Ragas error"""
        with patch('evaluation.bot_evaluator.RAGAS_AVAILABLE', True):
            with patch('evaluation.bot_evaluator.AnswerCorrectness') as mock_metric_class:
                # Mock metric that raises error
                mock_metric = Mock()
                mock_metric.ascore.side_effect = Exception("Ragas API error")
                mock_metric_class.return_value = mock_metric
                
                evaluator = BotEvaluator(
                    model_provider="openrouter",
                    model_name="gpt-4o-mini",
                    evaluator_llm=mock_llm
                )
                
                result = await evaluator.evaluate_item(
                    item_id="test_001",
                    query="Test query",
                    context=["Context 1"],
                    response="Generated response",
                    reference_answer="Expected response"
                )
                
                assert result["overall_score"] == 0.0
                assert result["status"] == "failed"
                assert "Ragas API error" in result["error_message"]
    
    @pytest.mark.asyncio
    async def test_evaluate_item_multiple_metrics(self, mock_llm, sample_item):
        """Test item evaluation with multiple metrics"""
        with patch('evaluation.bot_evaluator.RAGAS_AVAILABLE', True):
            with patch('evaluation.bot_evaluator.AnswerCorrectness') as mock_correctness:
                with patch('evaluation.bot_evaluator.Faithfulness') as mock_faithfulness:
                    with patch('evaluation.bot_evaluator.ContextRelevance') as mock_relevance:
                        # Mock different metric instances
                        mock_correctness_metric = Mock()
                        mock_correctness_metric.ascore.return_value = 0.85
                        mock_correctness.return_value = mock_correctness_metric
                        
                        mock_faithfulness_metric = Mock()
                        mock_faithfulness_metric.ascore.return_value = 0.90
                        mock_faithfulness.return_value = mock_faithfulness_metric
                        
                        mock_relevance_metric = Mock()
                        mock_relevance_metric.ascore.return_value = 0.75
                        mock_relevance.return_value = mock_relevance_metric
                        
                        evaluator = BotEvaluator(
                            model_provider="openrouter",
                            model_name="gpt-4o-mini",
                            evaluator_llm=mock_llm
                        )
                        
                        result = await evaluator.evaluate_item(
                            item_id="test_001",
                            query="Test query",
                            context=["Context 1"],
                            response="Generated response",
                            reference_answer="Expected response"
                        )
                        
                        # Verify all metrics were called
                        assert "answer_correctness" in result["scores"]
                        assert "faithfulness" in result["scores"]
                        assert "context_relevance" in result["scores"]
                        
                        assert result["scores"]["answer_correctness"] == 0.85
                        assert result["scores"]["faithfulness"] == 0.90
                        assert result["scores"]["context_relevance"] == 0.75
                        
                        # Overall score should be average
                        expected_overall = (0.85 + 0.90 + 0.75) / 3
                        assert abs(result["overall_score"] - expected_overall) < 0.01
    
    @pytest.mark.asyncio
    async def test_evaluate_item_partial_metric_failure(self, mock_llm, sample_item):
        """Test item evaluation with some metrics failing"""
        with patch('evaluation.bot_evaluator.RAGAS_AVAILABLE', True):
            with patch('evaluation.bot_evaluator.AnswerCorrectness') as mock_correctness:
                with patch('evaluation.bot_evaluator.Faithfulness') as mock_faithfulness:
                    # Mock one metric working, one failing
                    mock_correctness_metric = Mock()
                    mock_correctness_metric.ascore.return_value = 0.85
                    mock_correctness.return_value = mock_correctness_metric
                    
                    mock_faithfulness_metric = Mock()
                    mock_faithfulness_metric.ascore.side_effect = Exception("Faithfulness error")
                    mock_faithfulness.return_value = mock_faithfulness_metric
                    
                    evaluator = BotEvaluator(
                        model_provider="openrouter",
                        model_name="gpt-4o-mini",
                        evaluator_llm=mock_llm
                    )
                    
                    result = await evaluator.evaluate_item(
                        item_id="test_001",
                        query="Test query",
                        context=["Context 1"],
                        response="Generated response",
                        reference_answer="Expected response"
                    )
                    
                    # Should still succeed with partial results
                    assert result["status"] == "success"
                    assert "answer_correctness" in result["scores"]
                    assert result["scores"]["answer_correctness"] == 0.85
                    assert "faithfulness" not in result["scores"]
                    assert result["overall_score"] == 0.85
    
    @pytest.mark.asyncio
    async def test_create_channel_context_awareness_metric(self, mock_llm):
        """Test creation of custom channel context awareness metric"""
        with patch('evaluation.bot_evaluator.RAGAS_AVAILABLE', True):
            with patch('evaluation.bot_evaluator.AspectCritic') as mock_aspect_critic:
                evaluator = BotEvaluator(
                    model_provider="openrouter",
                    model_name="gpt-4o-mini",
                    evaluator_llm=mock_llm
                )
                
                metric = evaluator._create_channel_context_awareness_metric()
                
                assert metric is not None
                mock_aspect_critic.assert_called_once()
                
                # Verify the definition contains relevant keywords
                call_args = mock_aspect_critic.call_args
                definition = call_args[1]["definition"]
                assert "канал" in definition.lower() or "channel" in definition.lower()
                assert "специфик" in definition.lower() or "specific" in definition.lower()
    
    @pytest.mark.asyncio
    async def test_create_group_synthesis_quality_metric(self, mock_llm):
        """Test creation of custom group synthesis quality metric"""
        with patch('evaluation.bot_evaluator.RAGAS_AVAILABLE', True):
            with patch('evaluation.bot_evaluator.AspectCritic') as mock_aspect_critic:
                evaluator = BotEvaluator(
                    model_provider="openrouter",
                    model_name="gpt-4o-mini",
                    evaluator_llm=mock_llm
                )
                
                metric = evaluator._create_group_synthesis_quality_metric()
                
                assert metric is not None
                mock_aspect_critic.assert_called_once()
                
                # Verify the definition contains relevant keywords
                call_args = mock_aspect_critic.call_args
                definition = call_args[1]["definition"]
                assert "групп" in definition.lower() or "group" in definition.lower()
                assert "синтез" in definition.lower() or "synthesis" in definition.lower()
    
    @pytest.mark.asyncio
    async def test_create_multi_source_coherence_metric(self, mock_llm):
        """Test creation of custom multi-source coherence metric"""
        with patch('evaluation.bot_evaluator.RAGAS_AVAILABLE', True):
            with patch('evaluation.bot_evaluator.AspectCritic') as mock_aspect_critic:
                evaluator = BotEvaluator(
                    model_provider="openrouter",
                    model_name="gpt-4o-mini",
                    evaluator_llm=mock_llm
                )
                
                metric = evaluator._create_multi_source_coherence_metric()
                
                assert metric is not None
                mock_aspect_critic.assert_called_once()
                
                # Verify the definition contains relevant keywords
                call_args = mock_aspect_critic.call_args
                definition = call_args[1]["definition"]
                assert "источник" in definition.lower() or "source" in definition.lower()
                assert "связ" in definition.lower() or "coherence" in definition.lower()
    
    @pytest.mark.asyncio
    async def test_create_tone_appropriateness_metric(self, mock_llm):
        """Test creation of custom tone appropriateness metric"""
        with patch('evaluation.bot_evaluator.RAGAS_AVAILABLE', True):
            with patch('evaluation.bot_evaluator.AspectCritic') as mock_aspect_critic:
                evaluator = BotEvaluator(
                    model_provider="openrouter",
                    model_name="gpt-4o-mini",
                    evaluator_llm=mock_llm
                )
                
                metric = evaluator._create_tone_appropriateness_metric()
                
                assert metric is not None
                mock_aspect_critic.assert_called_once()
                
                # Verify the definition contains relevant keywords
                call_args = mock_aspect_critic.call_args
                definition = call_args[1]["definition"]
                assert "тон" in definition.lower() or "tone" in definition.lower()
                assert "умест" in definition.lower() or "appropriate" in definition.lower()
    
    @pytest.mark.asyncio
    async def test_custom_metrics_without_ragas(self, mock_llm):
        """Test custom metrics creation without Ragas"""
        with patch('evaluation.bot_evaluator.RAGAS_AVAILABLE', False):
            evaluator = BotEvaluator(
                model_provider="openrouter",
                model_name="gpt-4o-mini",
                evaluator_llm=mock_llm
            )
            
            # All custom metrics should return None
            assert evaluator._create_channel_context_awareness_metric() is None
            assert evaluator._create_group_synthesis_quality_metric() is None
            assert evaluator._create_multi_source_coherence_metric() is None
            assert evaluator._create_tone_appropriateness_metric() is None
    
    @pytest.mark.asyncio
    async def test_setup_ragas_metrics_filters_none(self, mock_llm):
        """Test that _setup_ragas_metrics filters out None values"""
        with patch('evaluation.bot_evaluator.RAGAS_AVAILABLE', True):
            with patch('evaluation.bot_evaluator.AnswerCorrectness') as mock_correctness:
                # Mock one standard metric and one None custom metric
                mock_correctness_metric = Mock()
                mock_correctness.return_value = mock_correctness_metric
                
                evaluator = BotEvaluator(
                    model_provider="openrouter",
                    model_name="gpt-4o-mini",
                    evaluator_llm=mock_llm
                )
                
                # Mock custom metrics to return None
                evaluator._create_channel_context_awareness_metric = Mock(return_value=None)
                evaluator._create_group_synthesis_quality_metric = Mock(return_value=None)
                evaluator._create_multi_source_coherence_metric = Mock(return_value=None)
                evaluator._create_tone_appropriateness_metric = Mock(return_value=None)
                
                # Setup metrics
                evaluator._setup_ragas_metrics()
                
                # Should have only the standard metrics, no None values
                assert len(evaluator.ragas_metrics) == 4  # 4 standard metrics
                assert all(metric is not None for metric in evaluator.ragas_metrics)


class TestBotEvaluatorIntegration:
    """Integration tests for BotEvaluator"""
    
    @pytest.fixture
    def mock_llm(self):
        """Mock LLM for testing"""
        mock_llm = AsyncMock()
        return mock_llm
    
    @pytest.mark.asyncio
    async def test_evaluate_golden_dataset_item(self, mock_llm):
        """Test evaluation of a complete GoldenDatasetItem"""
        with patch('evaluation.bot_evaluator.RAGAS_AVAILABLE', True):
            with patch('evaluation.bot_evaluator.AnswerCorrectness') as mock_metric_class:
                # Mock metric instance
                mock_metric = Mock()
                mock_metric.ascore.return_value = 0.88
                mock_metric_class.return_value = mock_metric
                
                evaluator = BotEvaluator(
                    model_provider="openrouter",
                    model_name="gpt-4o-mini",
                    evaluator_llm=mock_llm
                )
                
                # Create sample item
                telegram_context = TelegramContext(
                    user_id=12345,
                    channels=["automotive_news"],
                    context_type=ContextType.SINGLE_CHANNEL
                )
                
                item = GoldenDatasetItem(
                    item_id="integration_test_001",
                    dataset_name="test_dataset",
                    category="automotive",
                    input={"message_text": "What are the latest electric cars?"},
                    query="What are the latest electric cars?",
                    telegram_context=telegram_context,
                    expected_output="The latest electric cars include Tesla Model Y, BMW iX, and Audi e-tron.",
                    retrieved_contexts=[
                        "Tesla Model Y specifications and features",
                        "BMW iX electric SUV details",
                        "Audi e-tron luxury electric vehicle"
                    ]
                )
                
                result = await evaluator.evaluate_item(
                    item_id=item.item_id,
                    query=item.query,
                    context=item.retrieved_contexts or [],
                    response="Tesla Model Y, BMW iX, and Audi e-tron are the latest electric cars.",
                    reference_answer=item.expected_output
                )
                
                assert result["overall_score"] == 0.88
                assert result["status"] == "success"
                assert "answer_correctness" in result["scores"]
                assert result["scores"]["answer_correctness"] == 0.88
