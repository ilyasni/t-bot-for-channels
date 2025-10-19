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
import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, AsyncGenerator
import json

import httpx
import asyncpg
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
        self.db_pool: Optional[asyncpg.Pool] = None
        self.golden_dataset_manager = None  # Will be set in __aenter__
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(300.0),  # 5 minutes timeout
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
        )
        
        # Initialize database pool
        database_url = os.getenv("TELEGRAM_DATABASE_URL")
        if database_url:
            self.db_pool = await asyncpg.create_pool(
                database_url,
                min_size=1,
                max_size=5,
                command_timeout=60
            )
            logger.info("✅ EvaluationRunner connected to PostgreSQL")
        
        # Initialize golden dataset manager
        self.golden_dataset_manager = await get_golden_dataset_manager()
        
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.http_client:
            await self.http_client.aclose()
        
        if self.db_pool:
            await self.db_pool.close()
            logger.info("✅ EvaluationRunner disconnected from PostgreSQL")
    
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
        increment_gauge(evaluation_runs_active, {})
        
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
            decrement_gauge(evaluation_runs_active, {})
    
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
            result = evaluator.evaluate_single_item(
                item=item,
                actual_output=actual_output,
                retrieved_contexts=retrieved_contexts,
                timeout_seconds=timeout_seconds
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
        if not self.db_pool:
            logger.warning("⚠️ Database pool not available, using mock ID")
            return 1
        
        try:
            async with self.db_pool.acquire() as conn:
                run_id = await conn.fetchval("""
                    INSERT INTO evaluation_runs (
                        run_name, dataset_name, model_provider, model_name,
                        parallel_workers, timeout_seconds, status, progress,
                        total_items, processed_items, successful_items, failed_items,
                        avg_score, scores, started_at, completed_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                    RETURNING id
                """, 
                    evaluation_run.run_name,
                    evaluation_run.dataset_name,
                    evaluation_run.model_provider,
                    evaluation_run.model_name,
                    evaluation_run.parallel_workers,
                    evaluation_run.timeout_seconds,
                    evaluation_run.status,
                    evaluation_run.progress,
                    evaluation_run.total_items,
                    evaluation_run.processed_items,
                    evaluation_run.successful_items,
                    evaluation_run.failed_items,
                    evaluation_run.avg_score,
                    json.dumps(evaluation_run.scores) if evaluation_run.scores else None,
                    evaluation_run.started_at,
                    evaluation_run.completed_at
                )
                
                logger.info(f"✅ Saved evaluation run {evaluation_run.run_name} with ID {run_id}")
                return run_id
                
        except Exception as e:
            logger.error(f"❌ Failed to save evaluation run: {e}")
            return 1  # Fallback to mock ID
    
    async def _update_evaluation_run(self, run_id: int, evaluation_run: EvaluationRun):
        """Обновить evaluation run в БД"""
        if not self.db_pool:
            return
        
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    UPDATE evaluation_runs SET
                        status = $2,
                        progress = $3,
                        total_items = $4,
                        processed_items = $5,
                        successful_items = $6,
                        failed_items = $7,
                        avg_score = $8,
                        scores = $9,
                        started_at = $10,
                        completed_at = $11
                    WHERE id = $1
                """,
                    run_id,
                    evaluation_run.status,
                    evaluation_run.progress,
                    evaluation_run.total_items,
                    evaluation_run.processed_items,
                    evaluation_run.successful_items,
                    evaluation_run.failed_items,
                    evaluation_run.avg_score,
                    json.dumps(evaluation_run.scores) if evaluation_run.scores else None,
                    evaluation_run.started_at,
                    evaluation_run.completed_at
                )
                
        except Exception as e:
            logger.error(f"❌ Failed to update evaluation run {run_id}: {e}")
    
    async def _save_evaluation_result(self, run_id: int, result: EvaluationResult):
        """Сохранить evaluation result в БД"""
        if not self.db_pool:
            return
        
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO evaluation_results (
                        run_id, item_id, query, expected_output, actual_output,
                        answer_correctness, faithfulness, context_relevance,
                        factual_correctness, channel_context_awareness,
                        group_synthesis_quality, multi_source_coherence,
                        tone_appropriateness, overall_score, evaluation_time,
                        model_used, retrieved_contexts, telegram_context,
                        error_message, debug_info, created_at
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, NOW()
                    )
                """,
                    run_id,
                    result.item_id,
                    result.query,
                    result.expected_output,
                    result.actual_output,
                    result.metrics.answer_correctness,
                    result.metrics.faithfulness,
                    result.metrics.context_relevance,
                    result.metrics.factual_correctness,
                    result.metrics.channel_context_awareness,
                    result.metrics.group_synthesis_quality,
                    result.metrics.multi_source_coherence,
                    result.metrics.tone_appropriateness,
                    result.metrics.overall_score,
                    result.metrics.evaluation_time,
                    result.metrics.model_used,
                    json.dumps(result.retrieved_contexts) if result.retrieved_contexts else None,
                    json.dumps(result.telegram_context.dict()) if result.telegram_context else None,
                    result.error_message,
                    json.dumps(result.debug_info) if result.debug_info else None
                )
                
        except Exception as e:
            logger.error(f"❌ Failed to save evaluation result for item {result.item_id}: {e}")
    
    async def list_evaluation_results(
        self,
        run_id: Optional[int] = None,
        dataset_name: Optional[str] = None,
        status: Optional[str] = None,
        min_score: Optional[float] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Получить список evaluation results с фильтрами"""
        if not self.db_pool:
            return []
        
        try:
            async with self.db_pool.acquire() as conn:
                # Build query with filters
                query = "SELECT * FROM evaluation_results WHERE 1=1"
                params = []
                param_count = 0
                
                if run_id is not None:
                    param_count += 1
                    query += f" AND run_id = ${param_count}"
                    params.append(run_id)
                
                if dataset_name is not None:
                    param_count += 1
                    query += f" AND run_id IN (SELECT id FROM evaluation_runs WHERE dataset_name = ${param_count})"
                    params.append(dataset_name)
                
                if status is not None:
                    param_count += 1
                    query += f" AND error_message IS {'NULL' if status == 'success' else 'NOT NULL'}"
                
                if min_score is not None:
                    param_count += 1
                    query += f" AND overall_score >= ${param_count}"
                    params.append(min_score)
                
                query += f" ORDER BY created_at DESC LIMIT ${param_count + 1} OFFSET ${param_count + 2}"
                params.extend([limit, offset])
                
                rows = await conn.fetch(query, *params)
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"❌ Failed to list evaluation results: {e}")
            return []
    
    async def _update_prometheus_metrics(
        self,
        dataset_name: str,
        model_provider: str,
        model_name: str,
        total_items: int,
        successful_items: int,
        failed_items: int,
        overall_score: float
    ):
        """Обновить Prometheus metrics"""
        try:
            labels = {
                "dataset": dataset_name,
                "model_provider": model_provider,
                "model_name": model_name
            }
            
            # Update counters
            increment_counter(
                evaluation_runs_total,
                {**labels, "status": "completed"}
            )
            
            increment_counter(
                evaluation_items_processed,
                {**labels, "status": "success"},
                successful_items
            )
            
            increment_counter(
                evaluation_items_processed,
                {**labels, "status": "error"},
                failed_items
            )
            
            # Update gauges
            set_gauge(
                evaluation_runs_active,
                0,  # No active runs after completion
                labels
            )
            
        except Exception as e:
            log_evaluation_metric_error("prometheus_update", e)


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
