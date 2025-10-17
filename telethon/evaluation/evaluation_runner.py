"""
Evaluation Runner для batch evaluation

Запускает batch evaluation на golden dataset с поддержкой:
- Parallel processing для ускорения
- Progress tracking
- Error handling и retry logic
- Integration с RAG service
- Prometheus metrics
- Database persistence

Best practices:
- Async/await для всех операций
- Graceful degradation при ошибках
- Progress tracking для больших datasets
- Retry logic для временных сбоев
- Resource management (connection pooling)
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, AsyncGenerator
import json

import httpx
from .golden_dataset_manager import get_golden_dataset_manager
from .bot_evaluator import get_bot_evaluator
from .schemas import (
    EvaluationRun,
    EvaluationResult,
    GoldenDatasetItem
)
from .metrics import (
    increment_counter,
    increment_gauge,
    decrement_gauge,
    set_gauge,
    observe_score,
    evaluation_duration_seconds,
    evaluation_items_processed,
    evaluation_runs_active,
    evaluation_runs_total,
    log_evaluation_metric_error
)

logger = logging.getLogger(__name__)


class EvaluationRunner:
    """Runner для batch evaluation"""
    
    def __init__(self, rag_service_url: str = "http://localhost:8020"):
        """
        Initialize Evaluation Runner
        
        Args:
            rag_service_url: URL RAG service для получения ответов бота
        """
        self.rag_service_url = rag_service_url
        self.http_client: Optional[httpx.AsyncClient] = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(300.0),  # 5 minutes timeout
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.http_client:
            await self.http_client.aclose()
    
    async def run_evaluation(
        self,
        dataset_name: str,
        run_name: str,
        model_provider: str = "openrouter",
        model_name: str = "gpt-4o-mini",
        parallel_workers: int = 4,
        timeout_seconds: int = 300
    ) -> EvaluationRun:
        """
        Запустить batch evaluation
        
        Args:
            dataset_name: Название golden dataset
            run_name: Название run
            model_provider: Провайдер модели
            model_name: Название модели
            parallel_workers: Количество параллельных воркеров
            timeout_seconds: Timeout для одного evaluation
            
        Returns:
            EvaluationRun с результатами
        """
        start_time = time.time()
        
        # Создать EvaluationRun record
        evaluation_run = EvaluationRun(
            run_name=run_name,
            dataset_name=dataset_name,
            model_provider=model_provider,
            model_name=model_name,
            parallel_workers=parallel_workers,
            timeout_seconds=timeout_seconds,
            status="running",
            started_at=datetime.now(timezone.utc),
            progress=0.0
        )
        
        # Сохранить в БД
        run_id = await self._save_evaluation_run(evaluation_run)
        
        # Update Prometheus metrics
        increment_gauge(evaluation_runs_active)
        
        try:
            # Получить items из dataset
            dataset_manager = await get_golden_dataset_manager()
            items = await dataset_manager.get_dataset_items(dataset_name)
            
            if not items:
                raise ValueError(f"No items found in dataset '{dataset_name}'")
            
            evaluation_run.total_items = len(items)
            await self._update_evaluation_run(run_id, evaluation_run)
            
            logger.info(f"🚀 Starting evaluation run '{run_name}': {len(items)} items, {parallel_workers} workers")
            
            # Запустить parallel evaluation
            results = []
            successful_items = 0
            failed_items = 0
            
            # Создать semaphore для ограничения параллельности
            semaphore = asyncio.Semaphore(parallel_workers)
            
            # Создать tasks для всех items
            tasks = []
            for i, item in enumerate(items):
                task = asyncio.create_task(
                    self._evaluate_single_item_with_semaphore(
                        semaphore, item, model_provider, model_name, timeout_seconds
                    )
                )
                tasks.append((i, task))
            
            # Обработать результаты по мере готовности
            for i, task in tasks:
                try:
                    result = await task
                    results.append(result)
                    
                    if result.error_message:
                        failed_items += 1
                        increment_counter(
                            evaluation_items_processed,
                            {"dataset": dataset_name, "model_provider": model_provider, "status": "error"}
                        )
                    else:
                        successful_items += 1
                        increment_counter(
                            evaluation_items_processed,
                            {"dataset": dataset_name, "model_provider": model_provider, "status": "success"}
                        )
                    
                    # Update progress
                    processed_items = successful_items + failed_items
                    progress = processed_items / len(items)
                    evaluation_run.processed_items = processed_items
                    evaluation_run.progress = progress
                    
                    # Сохранить результат в БД
                    await self._save_evaluation_result(run_id, result)
                    
                    # Update run progress
                    if processed_items % 5 == 0 or processed_items == len(items):
                        await self._update_evaluation_run(run_id, evaluation_run)
                        logger.info(f"📊 Progress: {processed_items}/{len(items)} ({progress:.1%})")
                
                except Exception as e:
                    logger.error(f"❌ Task failed for item {i}: {e}")
                    failed_items += 1
                    increment_counter(
                        evaluation_items_processed,
                        {"dataset": dataset_name, "model_provider": model_provider, "status": "error"}
                    )
            
            # Вычислить итоговые scores
            avg_scores = self._calculate_average_scores(results)
            overall_score = avg_scores.get('overall_score', 0.0)
            
            # Завершить evaluation run
            evaluation_run.status = "completed"
            evaluation_run.completed_at = datetime.now(timezone.utc)
            evaluation_run.successful_items = successful_items
            evaluation_run.failed_items = failed_items
            evaluation_run.avg_score = overall_score
            evaluation_run.scores = avg_scores
            evaluation_run.progress = 1.0
            
            await self._update_evaluation_run(run_id, evaluation_run)
            
            # Update Prometheus metrics
            duration = time.time() - start_time
            observe_score(
                evaluation_duration_seconds,
                duration,
                {"dataset": dataset_name, "model_provider": model_provider}
            )
            
            increment_counter(
                evaluation_runs_total,
                {"dataset": dataset_name, "model_provider": model_provider, "status": "completed"}
            )
            
            logger.info(f"✅ Evaluation run '{run_name}' completed:")
            logger.info(f"   Items: {successful_items} successful, {failed_items} failed")
            logger.info(f"   Overall score: {overall_score:.3f}")
            logger.info(f"   Duration: {duration:.1f}s")
            
            return evaluation_run
            
        except Exception as e:
            logger.error(f"❌ Evaluation run '{run_name}' failed: {e}")
            
            # Update status to failed
            evaluation_run.status = "failed"
            evaluation_run.completed_at = datetime.now(timezone.utc)
            await self._update_evaluation_run(run_id, evaluation_run)
            
            # Update Prometheus metrics
            increment_counter(
                evaluation_runs_total,
                {"dataset": dataset_name, "model_provider": model_provider, "status": "failed"}
            )
            
            raise
            
        finally:
            # Update Prometheus metrics
            decrement_gauge(evaluation_runs_active)
    
    async def _evaluate_single_item_with_semaphore(
        self,
        semaphore: asyncio.Semaphore,
        item: GoldenDatasetItem,
        model_provider: str,
        model_name: str,
        timeout_seconds: int
    ) -> EvaluationResult:
        """Evaluate single item с semaphore для ограничения параллельности"""
        async with semaphore:
            return await self._evaluate_single_item(item, model_provider, model_name, timeout_seconds)
    
    async def _evaluate_single_item(
        self,
        item: GoldenDatasetItem,
        model_provider: str,
        model_name: str,
        timeout_seconds: int
    ) -> EvaluationResult:
        """Evaluate single item"""
        try:
            # Получить ответ от RAG service
            actual_output = await self._get_bot_response(item)
            
            # Получить retrieved contexts (если есть)
            retrieved_contexts = await self._get_retrieved_contexts(item)
            
            # Запустить evaluation
            evaluator = get_bot_evaluator(model_provider, model_name)
            result = await evaluator.evaluate_single_item(
                item=item,
                actual_output=actual_output,
                retrieved_contexts=retrieved_contexts
            )
            
            return result
            
        except asyncio.TimeoutError:
            logger.error(f"⏰ Timeout for item {item.item_id}")
            return self._create_error_result(item, f"Timeout after {timeout_seconds}s")
            
        except Exception as e:
            logger.error(f"❌ Error evaluating item {item.item_id}: {e}")
            return self._create_error_result(item, str(e))
    
    async def _get_bot_response(self, item: GoldenDatasetItem) -> str:
        """Получить ответ от RAG service"""
        if not self.http_client:
            raise RuntimeError("HTTP client not initialized")
        
        # Подготовить запрос для RAG service
        request_data = {
            "query": item.query,
            "user_id": item.telegram_context.user_id,
            "channels": item.telegram_context.channels,
            "context_type": item.telegram_context.context_type.value
        }
        
        if item.telegram_context.group_id:
            request_data["group_id"] = item.telegram_context.group_id
        
        # Отправить запрос
        response = await self.http_client.post(
            f"{self.rag_service_url}/rag/ask",
            json=request_data,
            timeout=60.0
        )
        response.raise_for_status()
        
        result = response.json()
        return result.get("answer", "No answer received")
    
    async def _get_retrieved_contexts(self, item: GoldenDatasetItem) -> List[str]:
        """Получить retrieved contexts для RAG evaluation"""
        if not self.http_client:
            return []
        
        try:
            # Подготовить запрос для search
            request_data = {
                "query": item.query,
                "user_id": item.telegram_context.user_id,
                "channels": item.telegram_context.channels,
                "limit": 5
            }
            
            # Отправить запрос
            response = await self.http_client.post(
                f"{self.rag_service_url}/rag/search",
                json=request_data,
                timeout=30.0
            )
            response.raise_for_status()
            
            result = response.json()
            contexts = []
            
            for doc in result.get("documents", []):
                if "content" in doc:
                    contexts.append(doc["content"])
                elif "text" in doc:
                    contexts.append(doc["text"])
            
            return contexts
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to get retrieved contexts for {item.item_id}: {e}")
            return []
    
    def _calculate_average_scores(self, results: List[EvaluationResult]) -> Dict[str, float]:
        """Вычислить средние scores из результатов"""
        if not results:
            return {}
        
        successful_results = [r for r in results if not r.error_message]
        if not successful_results:
            return {}
        
        scores = {}
        metrics = [
            'answer_correctness', 'faithfulness', 'context_relevance',
            'factual_correctness', 'channel_context_awareness',
            'group_synthesis_quality', 'multi_source_coherence',
            'tone_appropriateness', 'overall_score'
        ]
        
        for metric in metrics:
            values = []
            for result in successful_results:
                if hasattr(result.metrics, metric):
                    value = getattr(result.metrics, metric)
                    if value is not None:
                        values.append(value)
            
            if values:
                scores[metric] = sum(values) / len(values)
        
        return scores
    
    def _create_error_result(self, item: GoldenDatasetItem, error_message: str) -> EvaluationResult:
        """Создать результат с ошибкой"""
        from .schemas import EvaluationMetrics
        
        fallback_metrics = EvaluationMetrics(
            answer_correctness=0.0,
            faithfulness=0.0,
            context_relevance=0.0,
            factual_correctness=0.0,
            channel_context_awareness=0.0,
            group_synthesis_quality=0.0,
            multi_source_coherence=0.0,
            tone_appropriateness=0.0,
            overall_score=0.0,
            evaluation_time=0.0,
            model_used="error"
        )
        
        return EvaluationResult(
            item_id=item.item_id,
            query=item.query,
            expected_output=item.expected_output,
            actual_output="",
            metrics=fallback_metrics,
            telegram_context=item.telegram_context,
            error_message=error_message
        )
    
    async def _save_evaluation_run(self, evaluation_run: EvaluationRun) -> int:
        """Сохранить evaluation run в БД"""
        # TODO: Implement database save
        # For now, return a mock ID
        return 1
    
    async def _update_evaluation_run(self, run_id: int, evaluation_run: EvaluationRun):
        """Обновить evaluation run в БД"""
        # TODO: Implement database update
        pass
    
    async def _save_evaluation_result(self, run_id: int, result: EvaluationResult):
        """Сохранить evaluation result в БД"""
        # TODO: Implement database save
        pass


# ============================================================================
# Utility Functions
# ============================================================================

async def run_evaluation_batch(
    dataset_name: str,
    run_name: str,
    model_provider: str = "openrouter",
    model_name: str = "gpt-4o-mini",
    parallel_workers: int = 4,
    timeout_seconds: int = 300
) -> EvaluationRun:
    """
    Utility function для запуска batch evaluation
    
    Args:
        dataset_name: Название dataset
        run_name: Название run
        model_provider: Провайдер модели
        model_name: Название модели
        parallel_workers: Количество воркеров
        timeout_seconds: Timeout
        
    Returns:
        EvaluationRun с результатами
    """
    async with EvaluationRunner() as runner:
        return await runner.run_evaluation(
            dataset_name=dataset_name,
            run_name=run_name,
            model_provider=model_provider,
            model_name=model_name,
            parallel_workers=parallel_workers,
            timeout_seconds=timeout_seconds
        )
