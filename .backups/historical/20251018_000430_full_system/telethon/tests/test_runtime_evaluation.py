"""
Тесты для runtime evaluation pipeline

Проверяет:
- Асинхронная evaluation не блокирует ответ пользователю
- Runtime метрики обновляются корректно
- Low quality счетчики работают правильно
- Error handling при сбоях evaluation
"""
import pytest
import asyncio
import time
import os
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone

# Добавляем путь к модулям
import sys
sys.path.append('/home/ilyasni/n8n-server/n8n-installer/telethon')

from rag_service.generator import RAGGenerator
from evaluation.bot_evaluator import BotEvaluator
from evaluation.schemas import EvaluationResult, EvaluationMetrics


class TestRuntimeEvaluation:
    """Тесты для runtime evaluation pipeline"""
    
    @pytest.fixture
    def mock_env_vars(self):
        """Mock environment variables для тестов"""
        with patch.dict(os.environ, {
            'EVALUATION_ENABLED': 'true',
            'RUNTIME_EVALUATION_ENABLED': 'true',
            'EVALUATION_SAMPLE_RATE': '1.0',
            'EVALUATION_TIMEOUT_SECONDS': '60',
            'EVALUATION_MODEL_PROVIDER': 'openrouter',
            'EVALUATION_MODEL_NAME': 'gpt-4o-mini',
            'QUALITY_THRESHOLD_WARNING': '0.5',
            'QUALITY_THRESHOLD_CRITICAL': '0.3'
        }):
            yield
    
    @pytest.fixture
    def rag_generator(self):
        """Создать RAGGenerator для тестов"""
        return RAGGenerator()
    
    @pytest.mark.asyncio
    async def test_async_evaluation_does_not_block_response(self, mock_env_vars, rag_generator):
        """Проверка что evaluation не блокирует ответ пользователю"""
        
        # Mock search service
        with patch('rag_service.generator.search_service.search') as mock_search:
            mock_search.return_value = [
                {
                    "post_id": "test_1",
                    "channel_username": "test_channel",
                    "posted_at": datetime.now(timezone.utc),
                    "url": "https://t.me/test_channel/1",
                    "text": "Test context content",
                    "score": 0.9
                }
            ]
            
            # Mock LLM generation
            with patch.object(rag_generator, '_generate_with_openrouter') as mock_generate:
                mock_generate.return_value = "Test answer from LLM"
                
                # Mock async evaluation
                with patch.object(rag_generator, '_evaluate_response_async') as mock_eval:
                    mock_eval.return_value = None  # Async task
                    
                    start_time = time.time()
                    response = await rag_generator.generate_answer(
                        query="Test query",
                        user_id=123456,
                        channels=[1],
                        context_limit=5
                    )
                    response_time = time.time() - start_time
                    
                    # Response должен быть быстрым (< 5 секунд)
                    assert response_time < 5.0
                    assert "answer" in response
                    assert response["answer"] == "Test answer from LLM"
                    assert "timestamp" in response
                    
                    # Проверить что evaluation task был создан
                    mock_eval.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_low_quality_metrics_incremented(self, mock_env_vars, rag_generator):
        """Проверка что low quality счетчики обновляются"""
        
        # Mock evaluation result с низким score
        mock_result = Mock()
        mock_result.metrics = Mock()
        mock_result.metrics.overall_score = 0.3  # Ниже threshold_warning (0.5)
        
        # Mock BotEvaluator
        with patch('evaluation.bot_evaluator.get_bot_evaluator') as mock_get_evaluator:
            mock_evaluator = Mock()
            mock_evaluator.evaluate_single_item.return_value = mock_result
            mock_get_evaluator.return_value = mock_evaluator
            
            # Mock Prometheus metrics
            with patch('observability.metrics.low_quality_responses_total') as mock_metrics:
                mock_metrics.labels.return_value.inc = Mock()
                
                # Запустить evaluation
                await rag_generator._evaluate_response_async(
                    query="Test query",
                    response="Low quality response",
                    retrieved_contexts=["context"],
                    user_id=123456,
                    channels=["@test_channel"]
                )
                
                # Проверить что метрика была вызвана
                mock_metrics.labels.assert_called()
    
    @pytest.mark.asyncio
    async def test_evaluation_error_handling(self, mock_env_vars, rag_generator):
        """Проверка обработки ошибок evaluation"""
        
        # Mock BotEvaluator с ошибкой
        with patch('evaluation.bot_evaluator.get_bot_evaluator') as mock_get_evaluator:
            mock_evaluator = Mock()
            mock_evaluator.evaluate_single_item.side_effect = Exception("Evaluation failed")
            mock_get_evaluator.return_value = mock_evaluator
            
            # Mock error metrics
            with patch('observability.metrics.evaluation_errors_total') as mock_error_metrics:
                mock_error_metrics.labels.return_value.inc = Mock()
                
                # Запустить evaluation (не должно падать)
                await rag_generator._evaluate_response_async(
                    query="Test query",
                    response="Test response",
                    retrieved_contexts=["context"],
                    user_id=123456,
                    channels=["@test_channel"]
                )
                
                # Проверить что error metric был вызван
                mock_error_metrics.labels.assert_called()
    
    @pytest.mark.asyncio
    async def test_sample_rate_filtering(self, rag_generator):
        """Проверка фильтрации по sample rate"""
        
        # Mock environment с sample rate 0.1 (10%)
        with patch.dict(os.environ, {
            'EVALUATION_ENABLED': 'true',
            'RUNTIME_EVALUATION_ENABLED': 'true',
            'EVALUATION_SAMPLE_RATE': '0.1'
        }):
            
            # Mock BotEvaluator
            with patch('evaluation.bot_evaluator.get_bot_evaluator') as mock_get_evaluator:
                mock_evaluator = Mock()
                mock_get_evaluator.return_value = mock_evaluator
                
                # Тест с user_id который должен попасть в 10% (user_id % 100 < 10)
                await rag_generator._evaluate_response_async(
                    query="Test query",
                    response="Test response",
                    retrieved_contexts=["context"],
                    user_id=5,  # 5 % 100 = 5 < 10, должен пройти
                    channels=["@test_channel"]
                )
                
                # Проверить что evaluation был вызван
                mock_evaluator.evaluate_single_item.assert_called_once()
                
                # Тест с user_id который НЕ должен попасть в 10%
                mock_evaluator.reset_mock()
                await rag_generator._evaluate_response_async(
                    query="Test query",
                    response="Test response",
                    retrieved_contexts=["context"],
                    user_id=50,  # 50 % 100 = 50 > 10, НЕ должен пройти
                    channels=["@test_channel"]
                )
                
                # Проверить что evaluation НЕ был вызван
                mock_evaluator.evaluate_single_item.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_evaluation_disabled(self, rag_generator):
        """Проверка что evaluation отключается через env var"""
        
        # Mock environment с отключенной evaluation
        with patch.dict(os.environ, {
            'EVALUATION_ENABLED': 'false',
            'RUNTIME_EVALUATION_ENABLED': 'false'
        }):
            
            # Mock BotEvaluator
            with patch('evaluation.bot_evaluator.get_bot_evaluator') as mock_get_evaluator:
                mock_evaluator = Mock()
                mock_get_evaluator.return_value = mock_evaluator
                
                # Запустить evaluation
                await rag_generator._evaluate_response_async(
                    query="Test query",
                    response="Test response",
                    retrieved_contexts=["context"],
                    user_id=123456,
                    channels=["@test_channel"]
                )
                
                # Проверить что evaluation НЕ был вызван
                mock_evaluator.evaluate_single_item.assert_not_called()
    
    def test_bot_evaluator_runtime_metrics_update(self, mock_env_vars):
        """Проверка обновления runtime метрик в BotEvaluator"""
        
        # Mock metrics
        with patch('observability.metrics.runtime_evaluation_score') as mock_score_metric, \
             patch('observability.metrics.runtime_evaluation_duration') as mock_duration_metric, \
             patch('observability.metrics.low_quality_responses_total') as mock_low_quality_metric:
            
            mock_score_metric.labels.return_value.observe = Mock()
            mock_duration_metric.labels.return_value.observe = Mock()
            mock_low_quality_metric.labels.return_value.inc = Mock()
            
            # Создать BotEvaluator
            evaluator = BotEvaluator("openrouter", "gpt-4o-mini")
            
            # Создать mock metrics
            metrics = Mock()
            metrics.overall_score = 0.3  # Ниже threshold
            
            # Вызвать _update_runtime_metrics
            evaluator._update_runtime_metrics(
                metrics=metrics,
                user_id=123456,
                channel="@test_channel",
                evaluation_duration=15.5
            )
            
            # Проверить что метрики были обновлены
            mock_score_metric.labels.assert_called_with(
                user_id="123456",
                channel="@test_channel",
                model_provider="openrouter"
            )
            mock_score_metric.labels.return_value.observe.assert_called_with(0.3)
            
            mock_duration_metric.labels.assert_called_with(
                model_provider="openrouter",
                status="success"
            )
            mock_duration_metric.labels.return_value.observe.assert_called_with(15.5)
            
            # Проверить что low quality counter был вызван (score < 0.5)
            mock_low_quality_metric.labels.assert_called_with(
                user_id="123456",
                channel="@test_channel",
                threshold="0.5"
            )
            mock_low_quality_metric.labels.return_value.inc.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
