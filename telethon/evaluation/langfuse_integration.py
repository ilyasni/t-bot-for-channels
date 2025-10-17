"""
Langfuse Integration для Evaluation System

Интегрирует evaluation system с Langfuse для:
- Создания и управления datasets
- Traces для evaluation runs
- Scores tracking и comparison
- A/B testing разных моделей

Best practices:
- Graceful degradation если Langfuse недоступен
- Переиспользование существующего langfuse_client
- Async/await для всех операций
- Proper error handling
"""

import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

# Langfuse imports
try:
    from langfuse import Langfuse
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    logging.warning("⚠️ Langfuse not available - evaluation integration disabled")

from .schemas import (
    GoldenDatasetItem,
    EvaluationResult,
    EvaluationRun,
    TelegramContext
)

logger = logging.getLogger(__name__)


class EvaluationLangfuseClient:
    """Langfuse client для evaluation system"""
    
    def __init__(self):
        """Initialize Langfuse client"""
        self.client = None
        self.enabled = False
        
        if not LANGFUSE_AVAILABLE:
            logger.warning("⚠️ Langfuse not available - evaluation integration disabled")
            return
        
        try:
            # Переиспользуем существующую конфигурацию
            from observability.langfuse_client import langfuse_client
            
            if langfuse_client and langfuse_client.client:
                self.client = langfuse_client.client
                self.enabled = True
                logger.info("✅ Evaluation Langfuse client initialized")
            else:
                logger.warning("⚠️ Langfuse client not available - evaluation integration disabled")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize evaluation Langfuse client: {e}")
            self.enabled = False
    
    async def create_evaluation_dataset(
        self,
        name: str,
        description: str,
        items: List[GoldenDatasetItem]
    ) -> Dict[str, Any]:
        """
        Создать dataset в Langfuse
        
        Args:
            name: Название dataset
            description: Описание dataset
            items: Golden dataset items
            
        Returns:
            Dict с результатами создания
        """
        if not self.enabled or not self.client:
            return {"success": False, "error": "Langfuse not available"}
        
        try:
            # Создать dataset
            dataset = self.client.create_dataset(
                name=name,
                description=description,
                metadata={
                    "source": "telegram_bot_evaluation",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "total_items": len(items)
                }
            )
            
            # Добавить items
            created_items = 0
            errors = []
            
            for item in items:
                try:
                    self.client.create_dataset_item(
                        dataset_name=name,
                        input={
                            "query": item.query,
                            "user_id": item.telegram_context.user_id,
                            "channels": item.telegram_context.channels,
                            "context_type": item.telegram_context.context_type.value,
                            "group_id": item.telegram_context.group_id
                        },
                        expected_output=item.expected_output,
                        metadata={
                            "item_id": item.item_id,
                            "category": item.category,
                            "difficulty": item.difficulty.value if item.difficulty else None,
                            "tone": item.tone.value if item.tone else None,
                            "requires_multi_source": item.requires_multi_source,
                            "retrieved_contexts": item.retrieved_contexts
                        }
                    )
                    created_items += 1
                    
                except Exception as e:
                    error_msg = f"Failed to create item {item.item_id}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            result = {
                "success": True,
                "dataset_name": name,
                "total_items": len(items),
                "created_items": created_items,
                "errors": errors,
                "langfuse_dataset_id": dataset.id if hasattr(dataset, 'id') else None
            }
            
            logger.info(f"✅ Created Langfuse dataset '{name}': {created_items}/{len(items)} items")
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to create Langfuse dataset '{name}': {e}")
            return {"success": False, "error": str(e)}
    
    async def start_evaluation_run(
        self,
        dataset_name: str,
        run_name: str,
        model_provider: str,
        model_name: str
    ) -> Dict[str, Any]:
        """
        Начать evaluation run в Langfuse
        
        Args:
            dataset_name: Название dataset
            run_name: Название run
            model_provider: Провайдер модели
            model_name: Название модели
            
        Returns:
            Dict с результатами
        """
        if not self.enabled or not self.client:
            return {"success": False, "error": "Langfuse not available"}
        
        try:
            # Создать run
            run = self.client.create_dataset_run(
                dataset_name=dataset_name,
                run_name=run_name,
                metadata={
                    "model_provider": model_provider,
                    "model_name": model_name,
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "status": "running"
                }
            )
            
            result = {
                "success": True,
                "run_name": run_name,
                "langfuse_run_id": run.id if hasattr(run, 'id') else None
            }
            
            logger.info(f"✅ Started Langfuse evaluation run '{run_name}'")
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to start Langfuse run '{run_name}': {e}")
            return {"success": False, "error": str(e)}
    
    async def log_evaluation_result(
        self,
        dataset_name: str,
        run_name: str,
        item: GoldenDatasetItem,
        result: EvaluationResult
    ) -> Dict[str, Any]:
        """
        Логировать результат evaluation в Langfuse
        
        Args:
            dataset_name: Название dataset
            run_name: Название run
            item: Golden dataset item
            result: Evaluation result
            
        Returns:
            Dict с результатами
        """
        if not self.enabled or not self.client:
            return {"success": False, "error": "Langfuse not available"}
        
        try:
            # Создать trace для evaluation
            trace = self.client.trace(
                name=f"evaluation_{item.item_id}",
                run_name=run_name,
                input={
                    "query": item.query,
                    "user_id": item.telegram_context.user_id,
                    "channels": item.telegram_context.channels,
                    "context_type": item.telegram_context.context_type.value
                },
                output={
                    "actual_output": result.actual_output,
                    "expected_output": item.expected_output,
                    "overall_score": result.metrics.overall_score
                },
                metadata={
                    "item_id": item.item_id,
                    "category": item.category,
                    "model_used": result.metrics.model_used,
                    "evaluation_time": result.metrics.evaluation_time,
                    "error_message": result.error_message
                }
            )
            
            # Добавить scores как score events
            scores_to_log = [
                ("answer_correctness", result.metrics.answer_correctness),
                ("faithfulness", result.metrics.faithfulness),
                ("context_relevance", result.metrics.context_relevance),
                ("factual_correctness", result.metrics.factual_correctness),
                ("channel_context_awareness", result.metrics.channel_context_awareness),
                ("group_synthesis_quality", result.metrics.group_synthesis_quality),
                ("multi_source_coherence", result.metrics.multi_source_coherence),
                ("tone_appropriateness", result.metrics.tone_appropriateness),
                ("overall_score", result.metrics.overall_score)
            ]
            
            for score_name, score_value in scores_to_log:
                if score_value is not None:
                    self.client.score(
                        trace_id=trace.id,
                        name=score_name,
                        value=score_value,
                        comment=f"Evaluation metric: {score_name}"
                    )
            
            result_data = {
                "success": True,
                "trace_id": trace.id,
                "scores_logged": len([s for s in scores_to_log if s[1] is not None])
            }
            
            logger.debug(f"✅ Logged evaluation result for item {item.item_id}")
            return result_data
            
        except Exception as e:
            logger.error(f"❌ Failed to log evaluation result for {item.item_id}: {e}")
            return {"success": False, "error": str(e)}
    
    async def complete_evaluation_run(
        self,
        dataset_name: str,
        run_name: str,
        evaluation_run: EvaluationRun
    ) -> Dict[str, Any]:
        """
        Завершить evaluation run в Langfuse
        
        Args:
            dataset_name: Название dataset
            run_name: Название run
            evaluation_run: Evaluation run data
            
        Returns:
            Dict с результатами
        """
        if not self.enabled or not self.client:
            return {"success": False, "error": "Langfuse not available"}
        
        try:
            # Update run metadata
            self.client.update_dataset_run(
                dataset_name=dataset_name,
                run_name=run_name,
                metadata={
                    "model_provider": evaluation_run.model_provider,
                    "model_name": evaluation_run.model_name,
                    "started_at": evaluation_run.started_at.isoformat() if evaluation_run.started_at else None,
                    "completed_at": evaluation_run.completed_at.isoformat() if evaluation_run.completed_at else None,
                    "status": evaluation_run.status,
                    "total_items": evaluation_run.total_items,
                    "processed_items": evaluation_run.processed_items,
                    "successful_items": evaluation_run.successful_items,
                    "failed_items": evaluation_run.failed_items,
                    "avg_score": evaluation_run.avg_score,
                    "scores": evaluation_run.scores
                }
            )
            
            result = {
                "success": True,
                "run_name": run_name,
                "status": evaluation_run.status,
                "avg_score": evaluation_run.avg_score
            }
            
            logger.info(f"✅ Completed Langfuse evaluation run '{run_name}': {evaluation_run.avg_score:.3f}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to complete Langfuse run '{run_name}': {e}")
            return {"success": False, "error": str(e)}
    
    async def get_dataset_url(self, dataset_name: str) -> Optional[str]:
        """
        Получить URL для dataset в Langfuse UI
        
        Args:
            dataset_name: Название dataset
            
        Returns:
            URL для dataset или None
        """
        if not self.enabled or not self.client:
            return None
        
        try:
            # Получить base URL из конфигурации
            base_url = os.getenv("LANGFUSE_URL", "http://localhost:3000")
            
            # Создать URL для dataset
            dataset_url = f"{base_url}/datasets/{dataset_name}"
            
            return dataset_url
            
        except Exception as e:
            logger.error(f"❌ Failed to get dataset URL for '{dataset_name}': {e}")
            return None
    
    async def get_run_url(self, dataset_name: str, run_name: str) -> Optional[str]:
        """
        Получить URL для run в Langfuse UI
        
        Args:
            dataset_name: Название dataset
            run_name: Название run
            
        Returns:
            URL для run или None
        """
        if not self.enabled or not self.client:
            return None
        
        try:
            # Получить base URL из конфигурации
            base_url = os.getenv("LANGFUSE_URL", "http://localhost:3000")
            
            # Создать URL для run
            run_url = f"{base_url}/datasets/{dataset_name}/runs/{run_name}"
            
            return run_url
            
        except Exception as e:
            logger.error(f"❌ Failed to get run URL for '{run_name}': {e}")
            return None


# ============================================================================
# Singleton Instance
# ============================================================================

_evaluation_langfuse_client: Optional[EvaluationLangfuseClient] = None


def get_evaluation_langfuse_client() -> EvaluationLangfuseClient:
    """
    Get singleton instance of Evaluation Langfuse Client
    
    Returns:
        EvaluationLangfuseClient instance
    """
    global _evaluation_langfuse_client
    
    if _evaluation_langfuse_client is None:
        _evaluation_langfuse_client = EvaluationLangfuseClient()
    
    return _evaluation_langfuse_client
